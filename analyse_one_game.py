import chess
import chess.pgn
import chess.engine

STOCKFISH_PATH = r"stockfish\stockfish-windows-x86-64-universal.exe"
USERNAME = "Icecube06"

# Stockfish analysis depth.
DEPTH = 18

# Only report moves that lose at least this many pawns.
MIN_LOSS = 0.50


def find_game():
    """Find the first game involving our player."""

    with open("games.pgn", encoding="utf-8") as file:

        while True:
            game = chess.pgn.read_game(file)

            if game is None:
                return None

            if (
                game.headers.get("White") == USERNAME
                or game.headers.get("Black") == USERNAME
            ):
                return game


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
    """
    Convert a Stockfish score into centipawns.

    Mate scores are converted to a large number so
    decisive tactical mistakes can be measured.
    """

    return score.score(mate_score=10000)


def pv_to_san(board, pv, max_moves=5):
    """
    Convert a Stockfish principal variation to SAN.

    If Stockfish's PV becomes illegal while replaying,
    stop gracefully instead of crashing the program.
    """

    temp_board = board.copy()
    moves = []

    for move in pv[:max_moves]:

        if move not in temp_board.legal_moves:
            break

        try:
            san = temp_board.san(move)

        except AssertionError:
            break

        moves.append(san)
        temp_board.push(move)

    return " ".join(moves)


# ---------------------------------------------------------
# Find the game
# ---------------------------------------------------------

game = find_game()

if game is None:
    print("Could not find a game involving", USERNAME)
    raise SystemExit()

print("Game found:")
print(
    game.headers.get("White"),
    "vs",
    game.headers.get("Black")
)
print("Result:", game.headers.get("Result"))
print("Date:", game.headers.get("Date"))

# ---------------------------------------------------------
# Start Stockfish
# ---------------------------------------------------------

engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)

board = game.board()

mistakes = []

# ---------------------------------------------------------
# Analyze every move
# ---------------------------------------------------------

for ply, move in enumerate(game.mainline_moves(), start=1):

    player_to_move = board.turn

    # Determine whether this is our move.
    is_our_move = (
        (player_to_move == chess.WHITE
         and game.headers.get("White") == USERNAME)
        or
        (player_to_move == chess.BLACK
         and game.headers.get("Black") == USERNAME)
    )

    if is_our_move:

        # -------------------------------------------------
        # 1. Find Stockfish's best move
        # -------------------------------------------------

        best_analysis = engine.analyse(
            board,
            chess.engine.Limit(depth=DEPTH)
        )

        best_move = best_analysis["pv"][0]

        # -------------------------------------------------
        # 2. Analyze position after BEST move
        # -------------------------------------------------

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

        # -------------------------------------------------
        # 3. Analyze position after ACTUAL move
        # -------------------------------------------------

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

        # -------------------------------------------------
        # 4. Calculate move loss
        # -------------------------------------------------

        loss = (best_cp - actual_cp) / 100.0

        classification = classify_loss(loss)

        # -------------------------------------------------
        # 5. Convert moves to SAN
        # -------------------------------------------------

        played_san = board.san(move)
        best_san = board.san(best_move)

        # -------------------------------------------------
        # 6. Save significant mistakes
        # -------------------------------------------------

        if loss >= MIN_LOSS:

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
                "loss": loss,
                "classification": classification,
                "fen": board.fen(),
                "best_line": best_result["pv"],
                "actual_line": actual_result["pv"]
            })

        # Make the actual move.
        board.push(move)

    else:

        # Opponent's move.
        board.push(move)


# ---------------------------------------------------------
# Print results
# ---------------------------------------------------------

print("\nSignificant mistakes:\n")

if not mistakes:

    print("No significant mistakes found.")

else:

    for mistake in mistakes:

        move_label = (
            f"{mistake['move_number']}."
            if mistake["color"] == "White"
            else f"{mistake['move_number']}..."
        )

        print(
            f"{move_label} {mistake['played']}"
        )

        print(
            f"   Best:           {mistake['best']}"
        )

        print(
            f"   Loss:           "
            f"{mistake['loss']:.2f} pawns"
        )

        print(
            f"   Classification: "
            f"{mistake['classification']}"
        )

        print(
            f"   FEN:            "
            f"{mistake['fen']}"
        )

        # -------------------------------------------------
        # Best Stockfish continuation
        # -------------------------------------------------

        best_board = chess.Board(mistake["fen"])

        best_line = pv_to_san(
            best_board,
            mistake["best_line"],
            max_moves=5
        )

        print(
            f"   Best line:      "
            f"{best_line}"
        )

        # -------------------------------------------------
        # Actual Stockfish continuation
        # -------------------------------------------------

        actual_board = chess.Board(mistake["fen"])

        actual_line = pv_to_san(
            actual_board,
            mistake["actual_line"],
            max_moves=5
        )

        print(
            f"   Your line:      "
            f"{actual_line}"
        )

        print()


print(f"Found {len(mistakes)} significant mistakes.")

engine.quit()

print("\nAnalysis complete.")