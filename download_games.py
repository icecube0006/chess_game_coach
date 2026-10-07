import requests

USERNAME = "Icecube06"
NUMBER_OF_GAMES = 100

url = f"https://lichess.org/api/games/user/{USERNAME}"

params = {
    "max": NUMBER_OF_GAMES,
    "clocks": "true",
    "evals": "true",
    "opening": "true"
}

headers = {
    "Accept": "application/x-chess-pgn",
    "User-Agent": "ChessCoach/1.0 (personal chess analysis project)"
}

response = requests.get(
    url,
    params=params,
    headers=headers,
    timeout=30
)

print("HTTP status:", response.status_code)
print("Content type:", response.headers.get("Content-Type"))

response.raise_for_status()

# Make sure we actually received PGN rather than an HTML login/error page.
if "[Event " not in response.text:
    print("\nERROR: Response does not appear to contain PGN.")
    print(response.text[:500])
    raise SystemExit(1)

with open("games.pgn", "w", encoding="utf-8") as file:
    file.write(response.text)

print(f"Successfully downloaded games for {USERNAME}.")