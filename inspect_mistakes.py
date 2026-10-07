import json
from collections import Counter, defaultdict

# ---------------------------------------------------------
# Load analysis
# ---------------------------------------------------------

with open("analysis.json", encoding="utf-8") as file:
    data = json.load(file)

games = data["games"]

# ---------------------------------------------------------
# Collect mistakes
# ---------------------------------------------------------

all_mistakes = []

for game in games:

    for mistake in game["mistakes"]:

        mistake_copy = mistake.copy()

        mistake_copy["white"] = game["white"]
        mistake_copy["black"] = game["black"]
        mistake_copy["result"] = game["result"]
        mistake_copy["date"] = game["date"]

        all_mistakes.append(mistake_copy)


# ---------------------------------------------------------
# Basic statistics
# ---------------------------------------------------------

total_games = len(games)
total_mistakes = len(all_mistakes)

print("=" * 50)
print("ICECUBE06 CHESS ANALYSIS")
print("=" * 50)

print(f"\nGames analyzed: {total_games}")
print(f"Total significant mistakes: {total_mistakes}")

if total_games > 0:

    print(
        f"Average significant mistakes per game: "
        f"{total_mistakes / total_games:.2f}"
    )


# ---------------------------------------------------------
# Mistake classification
# ---------------------------------------------------------

classification_counts = Counter(
    mistake["classification"]
    for mistake in all_mistakes
)

print("\n" + "=" * 50)
print("MISTAKE TYPES")
print("=" * 50)

for classification in [
    "INACCURACY",
    "MISTAKE",
    "MAJOR MISTAKE",
    "BLUNDER"
]:

    count = classification_counts[classification]

    percentage = (
        count / total_mistakes * 100
        if total_mistakes
        else 0
    )

    print(
        f"{classification:15} "
        f"{count:3} "
        f"({percentage:.1f}%)"
    )


# ---------------------------------------------------------
# Mistakes by move number
# ---------------------------------------------------------

move_buckets = {
    "1-10": 0,
    "11-20": 0,
    "21-30": 0,
    "31-40": 0,
    "41-50": 0,
    "51-60": 0,
    "61-70": 0,
    "71-80": 0,
    "81+": 0
}

for mistake in all_mistakes:

    move = mistake["move_number"]

    if move <= 10:
        bucket = "1-10"
    elif move <= 20:
        bucket = "11-20"
    elif move <= 30:
        bucket = "21-30"
    elif move <= 40:
        bucket = "31-40"
    elif move <= 50:
        bucket = "41-50"
    elif move <= 60:
        bucket = "51-60"
    elif move <= 70:
        bucket = "61-70"
    elif move <= 80:
        bucket = "71-80"
    else:
        bucket = "81+"

    move_buckets[bucket] += 1


print("\n" + "=" * 50)
print("MISTAKES BY MOVE NUMBER")
print("=" * 50)

for bucket, count in move_buckets.items():

    print(
        f"{bucket:8} {count:3}"
    )


# ---------------------------------------------------------
# Mistakes by exact move number
# ---------------------------------------------------------

exact_move_counts = Counter(
    mistake["move_number"]
    for mistake in all_mistakes
)

print("\n" + "=" * 50)
print("MOST COMMON MOVE NUMBERS FOR MISTAKES")
print("=" * 50)

for move, count in exact_move_counts.most_common(15):

    print(
        f"Move {move:2}: {count}"
    )


# ---------------------------------------------------------
# Games with most mistakes
# ---------------------------------------------------------

game_mistakes = []

for game in games:

    game_mistakes.append({
        "white": game["white"],
        "black": game["black"],
        "date": game["date"],
        "result": game["result"],
        "mistakes": len(game["mistakes"])
    })

game_mistakes.sort(
    key=lambda x: x["mistakes"],
    reverse=True
)

print("\n" + "=" * 50)
print("GAMES WITH MOST MISTAKES")
print("=" * 50)

for game in game_mistakes[:10]:

    print(
        f"{game['mistakes']:2} mistakes | "
        f"{game['date']} | "
        f"{game['white']} vs {game['black']} | "
        f"{game['result']}"
    )


# ---------------------------------------------------------
# Biggest individual mistakes
# ---------------------------------------------------------

biggest_mistakes = sorted(
    all_mistakes,
    key=lambda x: x["loss"],
    reverse=True
)

print("\n" + "=" * 50)
print("BIGGEST INDIVIDUAL MISTAKES")
print("=" * 50)

for mistake in biggest_mistakes[:15]:

    print(
        f"{mistake['loss']:5.2f} pawns | "
        f"{mistake['classification']:15} | "
        f"{mistake['date']} | "
        f"{mistake['move_number']}"
        f"{'.' if mistake['color'] == 'White' else '...'}"
        f"{mistake['played']} "
        f"(best {mistake['best']}) | "
        f"{mistake['white']} vs {mistake['black']}"
    )


# ---------------------------------------------------------
# Average loss
# ---------------------------------------------------------

if all_mistakes:

    average_loss = sum(
        mistake["loss"]
        for mistake in all_mistakes
    ) / len(all_mistakes)

    print("\n" + "=" * 50)
    print("EVALUATION LOSS")
    print("=" * 50)

    print(
        f"Average loss among significant mistakes: "
        f"{average_loss:.2f} pawns"
    )

    print(
        f"Largest single loss: "
        f"{biggest_mistakes[0]['loss']:.2f} pawns"
    )


print("\n" + "=" * 50)
print("ANALYSIS COMPLETE")
print("=" * 50)