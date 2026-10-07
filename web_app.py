"""Browser interface for reviewing the existing Chess Coach dataset."""
import argparse
from functools import lru_cache
import json
import os
from pathlib import Path
import shutil
import threading

import chess
import chess.engine
import chess.pgn
import chess.svg
from flask import Flask, jsonify, render_template, request

ROOT = Path(__file__).resolve().parent


def find_stockfish():
    configured = os.environ.get("STOCKFISH_PATH")
    if configured:
        return configured
    candidates = [
        shutil.which("stockfish"),
        "/usr/games/stockfish",
        ROOT / "stockfish" / "stockfish-windows-x86-64-universal.exe",
    ]
    return next((str(p) for p in candidates if p and Path(p).is_file()), None)


def create_app(data_dir=ROOT, engine_path=None):
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 4096
    data_dir = Path(data_dir)
    data = json.loads((data_dir / "clean_analysis.json").read_text(encoding="utf-8"))
    # These entries in the existing dataset are search-score artifacts, not lessons.
    raw = data["mistakes"]
    positions = [dict(m) for m in raw if m["played"] != m["best"]]
    history = {}
    with (data_dir / "games.pgn").open(encoding="utf-8") as stream:
        while (game := chess.pgn.read_game(stream)) is not None:
            board = game.board()
            previous = None
            identity = tuple(game.headers.get(k) for k in ("White", "Black", "Date"))
            for move in game.mainline_moves():
                history[(*identity, board.fen())] = (previous, game.headers.get("Site", ""))
                previous = move.uci()
                board.push(move)
    groups = {}
    for index, m in enumerate(positions):
        m["id"] = index
        identity = (m["white"], m["black"], m["date"], m["fen"])
        m["previous_move"], m["site"] = history.get(identity, (None, ""))
        # A game URL disambiguates rematches on the same date.
        key = m["site"] or "|".join(identity[:3])
        m["game_id"] = key
        groups.setdefault(key, {"id": key, "white": m["white"], "black": m["black"],
                                "date": m["date"], "result": m["result"], "positions": []})["positions"].append(index)
    engine_path = engine_path or find_stockfish()
    engine_lock = threading.Lock()

    def position(index):
        if index < 0 or index >= len(positions):
            return None
        return positions[index]

    def svg(board, arrows=(), flip=False):
        return chess.svg.board(board, arrows=arrows, orientation=chess.BLACK if flip else chess.WHITE,
                               coordinates=True, size=640,
                               colors={"square light": "#f1e5cc", "square dark": "#879e86"})

    @lru_cache(maxsize=128)
    def continuation(index):
        if not engine_path:
            raise FileNotFoundError("Stockfish is not installed. Set STOCKFISH_PATH to its executable and restart the app.")
        board = chess.Board(positions[index]["fen"])
        # A single coherent PV, with bounded work; no engine is shared between users.
        with engine_lock:
            with chess.engine.SimpleEngine.popen_uci(engine_path, timeout=10) as engine:
                result = engine.analyse(board, chess.engine.Limit(depth=18, time=2))
        line = []
        for move in result.get("pv", [])[:8]:
            if move not in board.legal_moves:
                break
            san = board.san(move)
            board.push(move)
            line.append({"san": san, "uci": move.uci(), "fen": board.fen()})
        return {"moves": line, "depth": result.get("depth"), "engine": "Stockfish",
                "starting_fen": positions[index]["fen"]}

    @app.get("/")
    def home():
        return render_template("index.html")

    @app.get("/api/positions")
    def catalog():
        return jsonify(player=data.get("player", "Chess player"), count=len(positions),
                       excluded_identical_moves=len(raw)-len(positions), games=list(groups.values()),
                       engine_available=bool(engine_path))

    @app.get("/api/positions/<int:index>")
    def get_position(index):
        m = position(index)
        if m is None:
            return jsonify(error="Position not found."), 404
        board = chess.Board(m["fen"])
        arrows = []
        if m["previous_move"]:
            arrows.append(chess.svg.Arrow.from_pgn(m["previous_move"]))
            arrows[-1].color = "#5683a5"
        return jsonify(**m, board=svg(board, arrows, request.args.get("flip") == "1"),
                       legal_moves=[move.uci() for move in board.legal_moves])

    @app.get("/api/positions/<int:index>/board")
    def get_board(index):
        m = position(index)
        if m is None:
            return jsonify(error="Position not found."), 404
        board = chess.Board(m["fen"])
        view = request.args.get("view", "original")
        arrows = []
        if view != "continuation" and m["previous_move"]:
            arrows = [chess.svg.Arrow.from_pgn(m["previous_move"])]
            arrows[0].color = "#5683a5"
        if view in ("played", "best", "both"):
            for key, color in (("played", "#d38c38"), ("best", "#2f8054")):
                if view in (key, "both"):
                    arrows.append(chess.svg.Arrow.from_pgn(board.parse_san(m[key]).uci()))
                    arrows[-1].color = color
        elif view == "continuation":
            try:
                step = int(request.args.get("step", "0"))
                line = continuation(index)["moves"]
                if not 0 <= step <= len(line):
                    raise ValueError("Invalid continuation step.")
                for item in line[:step]:
                    move = chess.Move.from_uci(item["uci"])
                    board.push(move)
                if step:
                    arrows = [chess.svg.Arrow.from_pgn(line[step-1]["uci"])]
                    arrows[0].color = "#8664ae"
            except ValueError as error:
                return jsonify(error=str(error)), 400
            except (OSError, chess.engine.EngineError, TimeoutError):
                return jsonify(error="Unable to start Stockfish. Check STOCKFISH_PATH and restart the app."), 503
        elif view != "original":
            return jsonify(error="Unknown board view."), 400
        return jsonify(board=svg(board, arrows, request.args.get("flip") == "1"), fen=board.fen(),
                       turn="White" if board.turn else "Black")

    @app.post("/api/positions/<int:index>/try")
    def try_move(index):
        m = position(index)
        if m is None:
            return jsonify(error="Position not found."), 404
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or not isinstance(body.get("move"), str):
            return jsonify(error="Choose a move on the board or enter chess notation."), 400
        board = chess.Board(m["fen"])
        try:
            text = body["move"].strip()
            try:
                move = board.parse_uci(text)
            except ValueError:
                move = board.parse_san(text)
        except ValueError:
            return jsonify(error="That move is not legal in this position. Try again."), 400
        return jsonify(san=board.san(move), matches_best=move == board.parse_san(m["best"]),
                       matches_played=move == board.parse_san(m["played"]))

    @app.post("/api/positions/<int:index>/continuation")
    def get_continuation(index):
        if position(index) is None:
            return jsonify(error="Position not found."), 404
        try:
            return jsonify(continuation(index))
        except (OSError, chess.engine.EngineError, TimeoutError):
            return jsonify(error="Unable to start Stockfish. Set STOCKFISH_PATH to its executable and restart the app."), 503

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()
    create_app().run(host=args.host, port=args.port, debug=False, threaded=True)
