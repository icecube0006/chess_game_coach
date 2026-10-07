import json

with open("analysis.json", encoding="utf-8") as file:
    data = json.load(file)

print("Player:", data["player"])
print("Games analyzed:", data["games_analyzed"])
print("Stockfish depth:", data["depth"])
print("Minimum loss:", data["minimum_loss"])

total_mistakes = 0

classification_counts = {
    "INACCURACY": 0,
    "MISTAKE": 0,
    "MAJOR MISTAKE": 0,
    "BLUNDER": 0
}

for game in data["games"]:

    for mistake in game["mistakes"]:

        total_mistakes += 1

        classification = mistake["classification"]

        if classification in classification_counts:
            classification_counts[classification] += 1


print("\nTotal significant mistakes:", total_mistakes)

print("\nMistake breakdown:")

for classification, count in classification_counts.items():

    print(
        f"{classification}: {count}"
    )