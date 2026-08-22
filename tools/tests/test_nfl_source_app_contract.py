import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

from nfl_source_data_lib.identity import app_player_candidates


class NflSourceAppContractTests(unittest.TestCase):
    def test_app_candidates_and_audit_population_use_players_without_relevant_helper(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = root / "public/data"
            data.mkdir(parents=True)
            players = [
                {
                    "ID": "1000",
                    "TankID": "T1000",
                    "Name": "Current Player",
                    "Position": "WR",
                }
            ]
            (data / "Players.json").write_text(json.dumps(players), encoding="utf-8")

            candidates, audit_population = app_player_candidates(root)

            self.assertFalse((data / "Players_Relevant.json").exists())
            self.assertEqual(players, audit_population)
            self.assertEqual(1, len(candidates))
            self.assertEqual("1000", candidates[0].ids["Sleeper"])
            self.assertEqual("T1000", candidates[0].ids["Tank01"])


if __name__ == "__main__":
    unittest.main()
