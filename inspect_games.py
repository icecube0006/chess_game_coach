import chess.pgn

with open("games.pgn", encoding="utf-8") as file:
    game_number = 0

    while True:
        game = chess.pgn.read_game(file)

        if game is None:
            break

        game_number += 1

        print(
            game_number,
            game.headers.get("White"),
            "vs",
            game.headers.get("Black"),
            "|",
            game.headers.get("Result"),
            "|",
            game.headers.get("Date")
        )

print(f"\nTotal games: {game_number}")