import json
from collections import Counter


INPUT_FILE = "analysis.json"


with open(INPUT_FILE, encoding="utf-8") as file:
    data = json.load(file)


games = data["games"]

all_mistakes = []

for game in games:
    for mistake in game["mistakes"]:

        item = mistake.copy()

        item["white"] = game["white"]
        item["black"] = game["black"]
        item["result"] = game["result"]
        item["date"] = game["date"]

        all_mistakes.append(item)


print("=" * 60)
print("CLEANED ICECUBE06 ANALYSIS")
print("=" * 60)

print(f"\nGames: {len(games)}")
print(f"Raw significant mistakes: {len(all_mistakes)}")


# ---------------------------------------------------------
# Remove obviously corrupted / mate-score loss values
# ---------------------------------------------------------

NORMAL_MAX_LOSS = 15.0

normal_mistakes = [
    m for m in all_mistakes
    if m["loss"] <= NORMAL_MAX_LOSS
]

extreme_mistakes = [
    m for m in all_mistakes
    if m["loss"] > NORMAL_MAX_LOSS
]


print("\n" + "=" * 60)
print("MATE / EXTREME SCORE FILTER")
print("=" * 60)

print(
    f"Normal mistakes: {len(normal_mistakes)}"
)

print(
    f"Extreme/mate-score positions excluded: "
    f"{len(extreme_mistakes)}"
)


# ---------------------------------------------------------
# Mistake classifications
# ---------------------------------------------------------

classification_counts = Counter(
    m["classification"]
    for m in normal_mistakes
)


print("\n" + "=" * 60)
print("NORMAL MISTAKE TYPES")
print("=" * 60)


for classification in [
    "INACCURACY",
    "MISTAKE",
    "MAJOR MISTAKE",
    "BLUNDER"
]:

    count = classification_counts[classification]

    percentage = (
        count / len(normal_mistakes) * 100
        if normal_mistakes
        else 0
    )

    print(
        f"{classification:15}"
        f"{count:4}"
        f"  ({percentage:5.1f}%)"
    )


# ---------------------------------------------------------
# Mistakes by phase
# ---------------------------------------------------------

phase_counts = Counter()


for mistake in normal_mistakes:

    move = mistake["move_number"]

    if move <= 10:
        phase = "OPENING (1-10)"

    elif move <= 20:
        phase = "EARLY MIDDLEGAME (11-20)"

    elif move <= 30:
        phase = "MIDDLEGAME (21-30)"

    elif move <= 40:
        phase = "LATE MIDDLEGAME (31-40)"

    else:
        phase = "ENDGAME (41+)"

    phase_counts[phase] += 1


print("\n" + "=" * 60)
print("MISTAKES BY GAME PHASE")
print("=" * 60)


phase_order = [
    "OPENING (1-10)",
    "EARLY MIDDLEGAME (11-20)",
    "MIDDLEGAME (21-30)",
    "LATE MIDDLEGAME (31-40)",
    "ENDGAME (41+)"
]


for phase in phase_order:

    count = phase_counts[phase]

    percentage = (
        count / len(normal_mistakes) * 100
        if normal_mistakes
        else 0
    )

    print(
        f"{phase:25}"
        f"{count:4}"
        f"  ({percentage:5.1f}%)"
    )


# ---------------------------------------------------------
# Average loss
# ---------------------------------------------------------

if normal_mistakes:

    average_loss = sum(
        m["loss"]
        for m in normal_mistakes
    ) / len(normal_mistakes)

    print("\n" + "=" * 60)
    print("NORMAL EVALUATION LOSS")
    print("=" * 60)

    print(
        f"Average loss: {average_loss:.2f} pawns"
    )


# ---------------------------------------------------------
# Biggest NORMAL mistakes
# ---------------------------------------------------------

biggest = sorted(
    normal_mistakes,
    key=lambda x: x["loss"],
    reverse=True
)


print("\n" + "=" * 60)
print("BIGGEST NORMAL MISTAKES")
print("=" * 60)


for mistake in biggest[:30]:

    move_number = mistake["move_number"]

    move_text = (
        f"{move_number}."
        if mistake["color"] == "White"
        else f"{move_number}..."
    )

    print(
        f"{mistake['loss']:5.2f} | "
        f"{mistake['classification']:15} | "
        f"{mistake['date']} | "
        f"{move_text}{mistake['played']} "
        f"-> {mistake['best']} | "
        f"{mistake['white']} vs "
        f"{mistake['black']}"
    )


# ---------------------------------------------------------
# Most common played moves among mistakes
# ---------------------------------------------------------

played_moves = Counter(
    m["played"]
    for m in normal_mistakes
)


print("\n" + "=" * 60)
print("MOST COMMON MOVES APPEARING IN MISTAKES")
print("=" * 60)


for move, count in played_moves.most_common(30):

    print(
        f"{move:8} {count:3}"
    )


# ---------------------------------------------------------
# Save cleaned dataset
# ---------------------------------------------------------

cleaned_output = {
    "player": data["player"],
    "games_analyzed": data["games_analyzed"],
    "depth": data["depth"],
    "raw_mistakes": len(all_mistakes),
    "normal_mistakes": len(normal_mistakes),
    "extreme_mistakes_excluded": len(extreme_mistakes),
    "mistakes": normal_mistakes
}


with open(
    "clean_analysis.json",
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        cleaned_output,
        file,
        indent=2
    )


print("\n" + "=" * 60)
print("DONE")
print("=" * 60)

print(
    "\nSaved cleaned data to:"
    "\nclean_analysis.json"
)