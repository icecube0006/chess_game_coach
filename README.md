# Chess Coach

Review mistakes from your own Lichess games in a browser. The web app reads the
existing `games.pgn` and `clean_analysis.json`; the original Tkinter app remains
available as `chess_gui.py`.

## Run the web app

Requires Python 3.10 or newer. From the repository directory:

```sh
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows Command Prompt: .venv\Scripts\activate
python -m pip install -r requirements.txt
python web_app.py
```

Open **http://127.0.0.1:5000** in your own computer's browser. The interface works
without a desktop display, external JavaScript libraries, or third-party assets.

Choose a game, then click a piece and its destination, or enter a move in standard
chess notation. Reveal your actual move and the saved best move, flip the board,
reset, and move between training positions. Keyboard users can focus board squares
and press Enter or use the notation field.

### Stockfish continuations

Saved positions and move comparisons work without Stockfish. Install Stockfish
separately to generate and step through fresh continuations. The app searches your
PATH, `/usr/games/stockfish`, and the existing Windows `stockfish` directory. For
other locations, set the executable path **before** starting the app:

```sh
# macOS / Linux
export STOCKFISH_PATH=/path/to/stockfish
python web_app.py
```

```bat
REM Windows Command Prompt
set STOCKFISH_PATH=C:\path\to\stockfish.exe
python web_app.py
```

Each continuation uses one Stockfish search capped at depth 18 or two seconds,
then displays up to eight half-moves. A fresh line can differ from an older saved
recommendation. Analysis requests are serialized and results cached; separate
browser sessions keep their own navigation and board state.

The saved scores are approximate. Entries where the played move equals the saved
best move are excluded from practice because the original analyzer can assign
them a nonzero loss. Other scores are displayed as recorded, not recalculated.

## Remote use

For a machine with supported port forwarding, start with
`python web_app.py --host 0.0.0.0 --port 5000`, forward port 5000 using that
platform, and open its forwarded address. This onboarding chat does not provide
a browser preview or an interactive desktop. Running the app here does not
automatically make it accessible from your browser.

The included server is for personal development. It has no login and should not
be published directly on the public Internet. A shared deployment needs an
appropriate production server and authentication.

## Refresh the training data

The existing scripts implement the pipeline:
`download_games.py` → `analyse_all_games.py` → `clean_analysis.py`.
They still use their original username and Windows engine paths. The web app
does not modify your PGN or analysis files. Restart it after regenerating data.

## Tests

```sh
python -m unittest discover -s tests -v
```
