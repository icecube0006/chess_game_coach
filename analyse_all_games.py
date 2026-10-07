import chess
import chess.pgn
import chess.engine
import json
import os
import time

STOCKFISH_PATH = r"stockfish\stockfish-windows-x86-64-universal.exe"
USERNAME = "Icecube06"

# Stockfish depth.
DEPTH = 18

# Only record mistakes losing at least this many pawns.
MIN_LOSS = 0.50

OUTPUT_FILE = "analysis.json"


def classify_loss(loss):
    """Classify the size of a mistake."""

    if loss >= 3.0:
        return "BLUNDER"
    elif loss >= 1.5:
        return "MAJOR MISTAKE"
    elif loss >= 1.0:
        return "MISTAKE"
    elif loss >= 0.5:
        return "INACCURACY"
    else:
        return "OK"


def score_to_cp(score):
    """Convert Stockfish score to centipawns."""

    return score.score(mate_score=10000)


# ---------------------------------------------------------
# Load games
# ---------------------------------------------------------

games = []

with open("games.pgn", encoding="utf-8") as file:

    while True:

        game = chess.pgn.read_game(file)

        if game is None:
            break

        if (
            game.headers.get("White") == USERNAME
            or game.headers.get("Black") == USERNAME
        ):
            games.append(game)


print(f"Found {len(games)} games involving {USERNAME}.")

# ---------------------------------------------------------
# Start Stockfish
# ---------------------------------------------------------

engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)

all_results = []

start_time = time.time()

# ---------------------------------------------------------
# Analyze games
# ---------------------------------------------------------

for game_number, game in enumerate(games, start=1):

    white = game.headers.get("White")
    black = game.headers.get("Black")
    result = game.headers.get("Result")
    date = game.headers.get("Date")

    print(
        f"\n[{game_number}/{len(games)}] "
        f"{white} vs {black} "
        f"({result})"
    )

    board = game.board()

    mistakes = []

    for ply, move in enumerate(
        game.mainline_moves(),
        start=1
    ):

        player_to_move = board.turn

        # Is this our move?
        is_our_move = (
            (
                player_to_move == chess.WHITE
                and white == USERNAME
            )
            or
            (
                player_to_move == chess.BLACK
                and black == USERNAME
            )
        )

        if is_our_move:

            # ---------------------------------------------
            # Find best move
            # ---------------------------------------------

            best_analysis = engine.analyse(
                board,
                chess.engine.Limit(depth=DEPTH)
            )

            best_move = best_analysis["pv"][0]

            # ---------------------------------------------
            # Position after best move
            # ---------------------------------------------

            best_board = board.copy()
            best_board.push(best_move)

            best_result = engine.analyse(
                best_board,
                chess.engine.Limit(depth=DEPTH)
            )

            best_score = best_result["score"].pov(
                player_to_move
            )

            best_cp = score_to_cp(best_score)

            # ---------------------------------------------
            # Position after actual move
            # ---------------------------------------------

            actual_board = board.copy()
            actual_board.push(move)

            actual_result = engine.analyse(
                actual_board,
                chess.engine.Limit(depth=DEPTH)
            )

            actual_score = actual_result["score"].pov(
                player_to_move
            )

            actual_cp = score_to_cp(actual_score)

            # ---------------------------------------------
            # Calculate loss
            # ---------------------------------------------

            loss = (best_cp - actual_cp) / 100.0

            if loss >= MIN_LOSS:

                played_san = board.san(move)
                best_san = board.san(best_move)

                mistakes.append({
                    "ply": ply,
                    "move_number": (ply + 1) // 2,
                    "color": (
                        "White"
                        if player_to_move == chess.WHITE
                        else "Black"
                    ),
                    "played": played_san,
                    "best": best_san,
                    "loss": round(loss, 2),
                    "classification": classify_loss(loss),
                    "fen": board.fen()
                })

                print(
                    f"    {played_san} -> {best_san} "
                    f"({loss:.2f}) "
                    f"{classify_loss(loss)}"
                )

            board.push(move)

        else:

            board.push(move)

    # -----------------------------------------------------
    # Save result for this game
    # -----------------------------------------------------

    game_result = {
        "game_number": game_number,
        "white": white,
        "black": black,
        "result": result,
        "date": date,
        "mistakes": mistakes
    }

    all_results.append(game_result)

# ---------------------------------------------------------
# Save everything
# ---------------------------------------------------------

output = {
    "player": USERNAME,
    "games_analyzed": len(all_results),
    "depth": DEPTH,
    "minimum_loss": MIN_LOSS,
    "games": all_results
}

with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        output,
        file,
        indent=2
    )

engine.quit()

elapsed = time.time() - start_time

# ---------------------------------------------------------
# Summary
# ---------------------------------------------------------

total_mistakes = sum(
    len(game["mistakes"])
    for game in all_results
)

print("\n================================")
print("ANALYSIS COMPLETE")
print("================================")

print(
    f"Games analyzed: {len(all_results)}"
)

print(
    f"Significant mistakes: {total_mistakes}"
)

print(
    f"Time taken: {elapsed / 60:.1f} minutes"
)

print(
    f"Results saved to: {OUTPUT_FILE}"
)