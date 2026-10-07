import tkinter as tk
from tkinter import messagebox
import json
import chess
import chess.engine
import chess.pgn

STOCKFISH_PATH = r"stockfish\stockfish-windows-x86-64-universal.exe"
JSON_FILE = "clean_analysis.json"
MAX_CONTINUATION_PLIES = 8

with open(JSON_FILE, encoding="utf-8") as file:
    data = json.load(file)

mistakes = data["mistakes"]

games = []
with open("games.pgn", encoding="utf-8") as file:
    while True:
        game = chess.pgn.read_game(file)
        if game is None:
            break
        games.append(game)

engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)

root = tk.Tk()
root.title("Chess Coach")
root.state("zoomed")
root.minsize(1000, 700)

current_index = 0
original_board = None
previous_board = None
previous_move = None
continuation_moves = []
continuation_board = None
continuation_index = 0
last_continuation_move = None
actual_move = None
best_move = None

BOARD_LIGHT = "#F0D9B5"
BOARD_DARK = "#B58863"
ARROW_OPPONENT = "#2471A3"
ARROW_MY_MOVE = "#E67E22"
ARROW_BEST = "#27AE60"
ARROW_CONTINUATION = "#8E44AD"

board_frame = tk.Frame(root)
board_frame.pack(side=tk.LEFT, padx=20, pady=20, fill=tk.BOTH, expand=True)

canvas = tk.Canvas(board_frame, highlightthickness=0)
canvas.pack(fill=tk.BOTH, expand=True)

right_frame = tk.Frame(root, width=430)
right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=20, pady=20)
right_frame.pack_propagate(False)

title_label = tk.Label(right_frame, text="Chess Coach", font=("Arial", 24, "bold"))
title_label.pack(pady=(10, 20))

info_label = tk.Label(right_frame, text="", font=("Arial", 14), justify=tk.LEFT, anchor="w")
info_label.pack(fill=tk.X, pady=10)

move_label = tk.Label(right_frame, text="", font=("Arial", 16, "bold"), justify=tk.LEFT, anchor="w")
move_label.pack(fill=tk.X, pady=10)

explanation_label = tk.Label(
    right_frame, text="", font=("Arial", 12), justify=tk.LEFT,
    wraplength=390, anchor="w"
)
explanation_label.pack(fill=tk.X, pady=10)

button_frame = tk.Frame(right_frame)
button_frame.pack(fill=tk.X, pady=20)

tk.Button(button_frame, text="Reset", font=("Arial", 12),
          command=lambda: reset_position()).pack(fill=tk.X, pady=5)

tk.Button(button_frame, text="Show my move", font=("Arial", 12),
          command=lambda: show_my_move()).pack(fill=tk.X, pady=5)

tk.Button(button_frame, text="Show best move", font=("Arial", 12),
          command=lambda: show_best_move()).pack(fill=tk.X, pady=5)

tk.Button(button_frame, text="Show continuation", font=("Arial", 12),
          command=lambda: show_continuation()).pack(fill=tk.X, pady=5)

tk.Button(button_frame, text="Next engine move", font=("Arial", 12),
          command=lambda: next_engine_move()).pack(fill=tk.X, pady=5)

tk.Button(button_frame, text="Previous", font=("Arial", 12),
          command=lambda: previous_position()).pack(fill=tk.X, pady=5)

tk.Button(button_frame, text="Next", font=("Arial", 12),
          command=lambda: next_position()).pack(fill=tk.X, pady=5)


def get_board_size():
    width = canvas.winfo_width()
    height = canvas.winfo_height()
    size = min(width, height)
    return 600 if size < 100 else size


def get_display_board():
    return continuation_board if continuation_board is not None else original_board


def draw_arrow(move, board, color, width=7):
    if move is None or board is None:
        return

    size = get_board_size()
    square_size = size / 8

    def square_center(square):
        file_index = chess.square_file(square)
        rank_index = chess.square_rank(square)
        return (
            (file_index + 0.5) * square_size,
            (7 - rank_index + 0.5) * square_size
        )

    x1, y1 = square_center(move.from_square)
    x2, y2 = square_center(move.to_square)

    canvas.create_line(
        x1, y1, x2, y2,
        fill=color,
        width=width,
        arrow=tk.LAST,
        arrowshape=(18, 22, 8),
        capstyle=tk.ROUND,
        tags="arrow"
    )


def draw_board():
    canvas.delete("all")
    board = get_display_board()

    if board is None:
        return

    size = get_board_size()
    square_size = size / 8

    for rank in range(8):
        for file_index in range(8):
            x1 = file_index * square_size
            y1 = rank * square_size
            x2 = x1 + square_size
            y2 = y1 + square_size
            color = BOARD_DARK if (rank + file_index) % 2 else BOARD_LIGHT

            canvas.create_rectangle(
                x1, y1, x2, y2, fill=color, outline=color
            )

    for rank in range(8):
        for file_index in range(8):
            x = file_index * square_size
            y = rank * square_size
            coordinate_color = BOARD_DARK if (rank + file_index) % 2 == 0 else BOARD_LIGHT

            if rank == 7:
                canvas.create_text(
                    x + square_size - 5, y + square_size - 5,
                    text=chr(ord("a") + file_index),
                    anchor="se", fill=coordinate_color,
                    font=("Arial", 10, "bold")
                )

            if file_index == 0:
                canvas.create_text(
                    x + 5, y + 5,
                    text=str(8 - rank),
                    anchor="nw", fill=coordinate_color,
                    font=("Arial", 10, "bold")
                )

    if previous_move is not None and continuation_board is None:
        draw_arrow(previous_move, original_board, ARROW_OPPONENT, 6)

    if actual_move is not None:
        draw_arrow(actual_move, original_board, ARROW_MY_MOVE, 7)

    if best_move is not None:
        draw_arrow(best_move, original_board, ARROW_BEST, 7)

    if last_continuation_move is not None:
        draw_arrow(last_continuation_move, board, ARROW_CONTINUATION, 7)

    piece_font = ("Segoe UI Symbol", int(square_size * 0.70))

    piece_symbols = {
        "P": "♙", "N": "♘", "B": "♗", "R": "♖", "Q": "♕", "K": "♔",
        "p": "♟", "n": "♞", "b": "♝", "r": "♜", "q": "♛", "k": "♚"
    }

    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece is None:
            continue

        file_index = chess.square_file(square)
        rank_index = chess.square_rank(square)

        x = (file_index + 0.5) * square_size
        y = (7 - rank_index + 0.5) * square_size

        canvas.create_text(
            x, y,
            text=piece_symbols[piece.symbol()],
            font=piece_font,
            fill="black"
        )


def find_position(mistake):
    target_fen = mistake["fen"]
    white_name = mistake["white"]
    black_name = mistake["black"]
    date = mistake["date"]

    for game in games:
        if game.headers.get("White") != white_name:
            continue
        if game.headers.get("Black") != black_name:
            continue
        if game.headers.get("Date") != date:
            continue

        board = game.board()
        previous_board_for_position = None
        previous_move_for_position = None

        for move in game.mainline_moves():
            if board.fen() == target_fen:
                return board.copy(), previous_board_for_position, previous_move_for_position

            previous_board_for_position = board.copy()
            previous_move_for_position = move
            board.push(move)

        if board.fen() == target_fen:
            return board.copy(), previous_board_for_position, previous_move_for_position

    return None, None, None


def load_position():
    global original_board, previous_board, previous_move
    global continuation_board, continuation_moves, continuation_index
    global last_continuation_move, actual_move, best_move

    mistake = mistakes[current_index]

    original_board, previous_board, previous_move = find_position(mistake)

    if original_board is None:
        messagebox.showerror("Error", "Could not find the chess position for this mistake.")
        return

    continuation_board = None
    continuation_moves = []
    continuation_index = 0
    last_continuation_move = None
    actual_move = None
    best_move = None

    info_label.config(
        text=(
            f"Mistake {current_index + 1} of {len(mistakes)}\n\n"
            f"{mistake['white']} vs {mistake['black']}\n"
            f"Date: {mistake['date']}\n"
            f"Result: {mistake['result']}\n"
            f"Move: {mistake['move_number']}. {mistake['color']}\n"
            f"Classification: {mistake['classification']}\n"
            f"Evaluation loss: {mistake['loss']:.2f}"
        )
    )

    move_label.config(text="Your turn.\nWhat would you play?")

    explanation_label.config(
        text=(
            "First look at the opponent's latest move.\n\n"
            "Ask:\n"
            "• What changed?\n"
            "• What are they threatening?\n"
            "• What checks, captures and threats do I have?\n\n"
            "Then choose your move."
        )
    )

    draw_board()


def reset_position():
    global continuation_board, continuation_moves, continuation_index
    global last_continuation_move, actual_move, best_move

    continuation_board = None
    continuation_moves = []
    continuation_index = 0
    last_continuation_move = None
    actual_move = None
    best_move = None

    move_label.config(text="Your turn.\nWhat would you play?")

    explanation_label.config(
        text=(
            "First look at the opponent's latest move.\n\n"
            "Ask:\n"
            "• What changed?\n"
            "• What are they threatening?\n"
            "• What checks, captures and threats do I have?"
        )
    )

    draw_board()


def show_my_move():
    global actual_move, continuation_board

    if original_board is None:
        return

    mistake = mistakes[current_index]
    played_san = mistake["played"]

    board_for_move = original_board.copy()

    try:
        actual_move = board_for_move.parse_san(played_san)
    except Exception as error:
        actual_move = None
        messagebox.showerror(
            "Move error",
            f"Could not parse your move:\n\n{played_san}\n\n"
            f"Position:\n{original_board.fen()}\n\nError:\n{error}"
        )
        return

    continuation_board = None

    move_label.config(text=f"Your move: {played_san}")

    explanation_label.config(
        text=(
            f"You played {played_san}.\n\n"
            f"Evaluation loss: {mistake['loss']:.2f} pawns\n\n"
            "Now compare this with the engine's best move."
        )
    )

    draw_board()


def show_best_move():
    global best_move, continuation_board

    if original_board is None:
        return

    mistake = mistakes[current_index]
    best_san = mistake["best"]
    board_for_move = original_board.copy()

    try:
        best_move = board_for_move.parse_san(best_san)
    except Exception as error:
        best_move = None
        messagebox.showerror(
            "Move error",
            f"Could not parse engine move:\n\n{best_san}\n\n"
            f"Position:\n{original_board.fen()}\n\nError:\n{error}"
        )
        return

    continuation_board = None

    move_label.config(text=f"Engine best move: {best_san}")

    explanation_label.config(
        text=(
            f"The engine prefers {best_san}.\n\n"
            "The next step is to understand WHY this move is stronger."
        )
    )

    draw_board()


def show_continuation():
    global continuation_moves, continuation_board, continuation_index
    global last_continuation_move, actual_move, best_move

    if original_board is None:
        return

    actual_move = None
    best_move = None
    last_continuation_move = None

    analysis_board = original_board.copy()
    continuation_moves = []

    try:
        for _ in range(MAX_CONTINUATION_PLIES):
            result = engine.analyse(
                analysis_board,
                chess.engine.Limit(depth=18)
            )

            pv = result.get("pv")
            if not pv:
                break

            move = pv[0]

            if move not in analysis_board.legal_moves:
                break

            continuation_moves.append(move)
            analysis_board.push(move)

    except Exception as error:
        messagebox.showerror("Engine error", str(error))
        return

    if not continuation_moves:
        messagebox.showinfo("Continuation", "No continuation could be generated.")
        return

    continuation_index = 0
    continuation_board = original_board.copy()
    last_continuation_move = None

    move_label.config(
        text="Engine continuation ready.\nClick 'Next engine move'."
    )

    explanation_label.config(
        text=(
            f"Stockfish calculated up to {len(continuation_moves)} moves ahead.\n\n"
            "Step through the line one move at a time."
        )
    )

    draw_board()


def next_engine_move():
    global continuation_index, continuation_board, last_continuation_move

    if not continuation_moves:
        messagebox.showinfo("Continuation", "Click 'Show continuation' first.")
        return

    if continuation_index >= len(continuation_moves):
        move_label.config(text="End of continuation.")
        return

    if continuation_board is None:
        continuation_board = original_board.copy()

    move = continuation_moves[continuation_index]

    if move not in continuation_board.legal_moves:
        messagebox.showerror(
            "Continuation error",
            "The next engine move is no longer legal on the current board."
        )
        return

    san = continuation_board.san(move)
    continuation_board.push(move)

    last_continuation_move = move
    continuation_index += 1

    move_label.config(
        text=f"Engine move {continuation_index}: {san}"
    )

    if continuation_index < len(continuation_moves):
        explanation_label.config(
            text=(
                "The board has now been updated.\n\n"
                "Look at what changed after this move.\n"
                "Then click 'Next engine move' to continue."
            )
        )
    else:
        explanation_label.config(
            text=(
                "End of the engine continuation.\n\n"
                "Compare the resulting position with your original decision."
            )
        )

    draw_board()


def previous_position():
    global current_index

    if current_index <= 0:
        return

    current_index -= 1
    load_position()


def next_position():
    global current_index

    if current_index >= len(mistakes) - 1:
        return

    current_index += 1
    load_position()


def on_resize(event):
    draw_board()


canvas.bind("<Configure>", on_resize)


def close_application():
    try:
        engine.quit()
    except Exception:
        pass

    root.destroy()


root.protocol("WM_DELETE_WINDOW", close_application)

load_position()
root.mainloop()
