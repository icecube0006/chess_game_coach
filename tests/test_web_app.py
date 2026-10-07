import json
from pathlib import Path
import tempfile
import unittest

import chess

from web_app import ROOT, create_app


class SavedGameReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app(engine_path="/nonexistent/stockfish")
        cls.app.testing = True

    def setUp(self):
        self.client = self.app.test_client()

    def test_catalog_excludes_score_artifacts_and_covers_all_positions(self):
        data = self.client.get("/api/positions").get_json()
        raw = json.loads((ROOT / "clean_analysis.json").read_text())["mistakes"]
        self.assertEqual(data["count"] + data["excluded_identical_moves"], len(raw))
        ids = [index for game in data["games"] for index in game["positions"]]
        self.assertEqual(sorted(ids), list(range(data["count"])))
        self.assertGreater(data["count"], 0)

    def test_all_saved_recommendations_are_legal_and_positions_render(self):
        data = self.client.get("/api/positions").get_json()
        for index in range(data["count"]):
            with self.subTest(index=index):
                response = self.client.get(f"/api/positions/{index}")
                self.assertEqual(response.status_code, 200)
                p = response.get_json()
                board = chess.Board(p["fen"])
                self.assertIn(board.parse_san(p["best"]).uci(), p["legal_moves"])
                self.assertIn(board.parse_san(p["played"]).uci(), p["legal_moves"])
                self.assertIn("<svg", p["board"])

    def test_candidate_move_and_reveal_do_not_modify_starting_position(self):
        p = self.client.get("/api/positions/1").get_json()
        answer = self.client.post("/api/positions/1/try", json={"move": p["best"]})
        self.assertTrue(answer.get_json()["matches_best"])
        answer = self.client.post("/api/positions/1/try", json={"move": p["played"]})
        self.assertTrue(answer.get_json()["matches_played"])
        self.assertFalse(answer.get_json()["matches_best"])
        reveal = self.client.get("/api/positions/1/board?view=both&flip=1").get_json()
        self.assertEqual(reveal["fen"], p["fen"])
        self.assertEqual(self.client.get("/api/positions/1").get_json()["fen"], p["fen"])

    def test_invalid_input_and_missing_positions_have_useful_errors(self):
        for body in [{"move": "e9"}, {"move": 123}, [], None]:
            with self.subTest(body=body):
                response = self.client.post("/api/positions/1/try", json=body)
                self.assertEqual(response.status_code, 400)
                self.assertIn("error", response.get_json())
        self.assertEqual(self.client.get("/api/positions/999999").status_code, 404)
        self.assertEqual(self.client.get("/api/positions/1/board?view=unknown").status_code, 400)

    def test_missing_engine_does_not_break_saved_review(self):
        response = self.client.post("/api/positions/1/continuation")
        self.assertEqual(response.status_code, 503)
        self.assertIn("STOCKFISH_PATH", response.get_json()["error"])
        self.assertEqual(self.client.get("/api/positions/1/board?view=best").status_code, 200)

    def test_clients_do_not_share_navigation(self):
        other = self.app.test_client()
        before = other.get("/api/positions/1").get_json()
        self.client.get("/api/positions/2")
        self.assertEqual(other.get("/api/positions/1").get_json(), before)


class PromotionTests(unittest.TestCase):
    def test_underpromotion_and_black_to_move(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            root.joinpath("games.pgn").write_text("")
            root.joinpath("clean_analysis.json").write_text(json.dumps({
                "player": "Test", "mistakes": [{
                    "white": "White", "black": "Test", "date": "2026.01.01", "result": "*",
                    "fen": "7k/8/8/8/8/8/p7/7K b - - 0 1", "color": "Black",
                    "move_number": 1, "played": "a1=Q+", "best": "a1=N", "loss": 1,
                    "classification": "MISTAKE",
                }],
            }))
            client = create_app(root, engine_path="/nonexistent/stockfish").test_client()
            p = client.get("/api/positions/0?flip=1").get_json()
            self.assertEqual(p["color"], "Black")
            self.assertIn("a2a1n", p["legal_moves"])
            response = client.post("/api/positions/0/try", json={"move": "a2a1n"})
            self.assertTrue(response.get_json()["matches_best"])
            self.assertEqual(response.get_json()["san"], "a1=N")


if __name__ == "__main__":
    unittest.main()
