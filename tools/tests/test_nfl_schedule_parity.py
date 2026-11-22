from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import nfl_schedule_parity as parity
from data_roots import DATA_SOURCE_ROOT


def game(game_id, day, time_, espn, away=None, home=None):
    return {"GameID": game_id, "Week": 11, "GameDay": day, "GameTime": time_, "AwayScore": away, "HomeScore": home,
            "ProviderGameIDs": {"ESPN": espn}}


def scoreboard(*events):
    return {"events": [{"id": i, "date": d} for i, d in events]}


class SchedulePariyTest(unittest.TestCase):
    def test_changed_kickoff_of_same_game_is_reported_with_utc_instants(self):
        games = [game("G1", "2026-11-22", "13:00", "1"), game("G2", "2026-11-22", "16:25", "2")]
        board = scoreboard(("1", "2026-11-22T21:25Z"), ("2", "2026-11-22T21:25Z"))
        result = parity.compare(games, lambda day: board)
        self.assertEqual([m["GameID"] for m in result["Mismatches"]], ["G1"])
        self.assertEqual(result["Mismatches"][0]["CanonicalKickoffUtc"], "2026-11-22T18:00:00Z")
        self.assertEqual(result["Mismatches"][0]["EspnKickoffUtc"], "2026-11-22T21:25:00Z")
        self.assertEqual(result["Matches"], 1)

    def test_unchanged_data_is_clean_and_deterministic(self):
        games = [game("G1", "2026-11-22", "13:00", "1")]
        board = scoreboard(("1", "2026-11-22T18:00Z"))
        first = parity.compare(games, lambda day: board)
        self.assertEqual(first, parity.compare(games, lambda day: board))
        self.assertEqual((first["Mismatches"], first["Unverifiable"], first["Errors"]), ([], [], []))

    def test_unknown_time_missing_event_and_missing_id_are_unverifiable_not_matches(self):
        games = [game("G1", "2026-11-22", None, "1"), game("G2", "2026-11-22", "13:00", "9"),
                 game("G3", "2026-11-22", "13:00", None)]
        result = parity.compare(games, lambda day: scoreboard(("1", "2026-11-22T18:00Z")))
        reasons = {u["GameID"]: u["Reason"] for u in result["Unverifiable"]}
        self.assertEqual(reasons, {"G1": "kickoff-unknown", "G2": "no-espn-event", "G3": "no-espn-id"})
        self.assertEqual(result["Matches"], 0)

    def test_provider_outage_is_reported_and_never_raises_or_matches(self):
        def boom(day):
            raise OSError("down")
        result = parity.compare([game("G1", "2026-11-22", "13:00", "1")], boom)
        self.assertEqual(result["Matches"], 0)
        self.assertEqual(len(result["Errors"]), 1)
        self.assertEqual(result["Unverifiable"][0]["Reason"], "espn-unavailable")

    def test_only_unscored_games_inside_the_window_are_checked(self):
        games = [game("old", "2026-11-01", "13:00", "1"), game("scored", "2026-11-22", "13:00", "2", 3, 7),
                 game("soon", "2026-11-23", "13:00", "3"), game("far", "2026-12-20", "13:00", "4")]
        picked = parity.upcoming_games(games, date(2026, 11, 22), 7)
        self.assertEqual([g["GameID"] for g in picked], ["soon"])

    def test_run_reads_canonical_schedule_and_exit_code_follows_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / DATA_SOURCE_ROOT / "nfl" / "schedules" / "2030.json"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({"Games": [game("G1", "2030-11-24", "13:00", "1")]}), encoding="utf-8")
            result = parity.run(root, 2030, date(2030, 11, 22), 7, lambda day: scoreboard(("1", "2030-11-24T21:25Z")))
            self.assertEqual(len(result["Mismatches"]), 1)
            self.assertIn("G1", parity.render_summary(result))


if __name__ == "__main__":
    unittest.main()
