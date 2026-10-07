import chess
import chess.engine

STOCKFISH_PATH = r"stockfish\stockfish-windows-x86-64-universal.exe"

engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)

board = chess.Board()

result = engine.analyse(
    board,
    chess.engine.Limit(depth=18)
)

print("Evaluation:", result["score"])
print("Best line:", result["pv"])

engine.quit()