from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from derived_data_lib.nfl_games import kickoff_utc
from nfl_source_data_lib import schedule_kickoff_overlay as overlay


def game(game_id, day, time_, espn, away=None, home=None):
    return {"GameID": game_id, "GameDay": day, "GameTime": time_, "WeekDay": "Sunday", "AwayScore": away,
            "HomeScore": home, "Stadium": "X", "ProviderGameIDs": {"ESPN": espn}}


def obs(espn, instant):
    return {"EspnGameID": espn, "KickoffUtc": instant}


class KickoffOverlayTest(unittest.TestCase):
    def test_changed_kickoff_is_applied_with_origin_and_stable_id(self):
        games = [game("G1", "2026-11-22", "13:00", "1")]
        result, decisions = overlay.apply_overlay(games, [obs("1", "2026-11-22T21:25:00Z")])
        self.assertEqual(result[0]["GameID"], "G1")
        self.assertEqual((result[0]["GameDay"], result[0]["GameTime"]), ("2026-11-22", "16:25"))
        self.assertEqual(result[0]["TimeSource"], "espn")
        self.assertEqual(result[0]["TimeSourceNflverse"], {"GameDay": "2026-11-22", "GameTime": "13:00"})
        self.assertEqual(result[0]["Stadium"], "X")
        self.assertEqual(kickoff_utc("G1", result[0]["GameDay"], result[0]["GameTime"]), "2026-11-22T21:25:00Z")
        self.assertEqual(decisions[0]["Outcome"], overlay.APPLIED)

    def test_day_change_updates_game_day_and_weekday(self):
        result, _ = overlay.apply_overlay([game("G1", "2026-11-22", "13:00", "1")], [obs("1", "2026-11-24T01:15:00Z")])
        self.assertEqual((result[0]["GameDay"], result[0]["GameTime"], result[0]["WeekDay"]), ("2026-11-23", "20:15", "Monday"))

    def test_same_kickoff_writes_nothing_and_is_idempotent(self):
        games = [game("G1", "2026-11-22", "13:00", "1")]
        same = [obs("1", "2026-11-22T18:00:00Z")]
        result, decisions = overlay.apply_overlay(games, same)
        self.assertEqual(result, games)
        self.assertEqual(decisions[0]["Outcome"], overlay.UNCHANGED)
        changed = [obs("1", "2026-11-22T21:25:00Z")]
        first, _ = overlay.apply_overlay(games, changed)
        # applying to the nflverse input twice gives the identical result (no feedback on the overlay output)
        self.assertEqual(first, overlay.apply_overlay(games, changed)[0])

    def test_override_disappears_when_nflverse_catches_up(self):
        caught_up = [game("G1", "2026-11-22", "16:25", "1")]
        result, decisions = overlay.apply_overlay(caught_up, [obs("1", "2026-11-22T21:25:00Z")])
        self.assertNotIn("TimeSource", result[0])
        self.assertEqual(decisions[0]["Outcome"], overlay.UNCHANGED)

    def test_fail_closed_cases_keep_nflverse(self):
        base = game("G1", "2026-11-22", "13:00", "1")
        cases = {
            "no-observation": ([base], []),
            "no-espn-id": ([{**base, "ProviderGameIDs": {}}], [obs("1", "2026-11-22T21:25:00Z")]),
            "already-scored": ([{**base, "AwayScore": 3, "HomeScore": 7}], [obs("1", "2026-11-22T21:25:00Z")]),
            "ambiguous": ([base], [obs("1", "2026-11-22T21:25:00Z"), obs("1", "2026-11-22T22:00:00Z")]),
            "kickoff-unknown": ([base], [obs("1", "not-a-time")]),
            "implausible-shift": ([base], [obs("1", "2026-12-25T21:25:00Z")]),
        }
        for reason, (games, observations) in cases.items():
            with self.subTest(reason):
                before = copy.deepcopy(games)
                result, decisions = overlay.apply_overlay(games, observations)
                self.assertEqual(result, before)
                self.assertEqual((decisions[0]["Outcome"], decisions[0]["Reason"]), (overlay.KEPT, reason))

    def test_two_canonical_games_with_same_espn_id_are_ambiguous(self):
        games = [game("G1", "2026-11-22", "13:00", "1"), game("G2", "2026-11-22", "16:25", "1")]
        result, decisions = overlay.apply_overlay(games, [obs("1", "2026-11-22T21:25:00Z")])
        self.assertEqual(result, games)
        self.assertEqual({d["Reason"] for d in decisions}, {"ambiguous"})

    def test_unknown_game_time_is_never_invented(self):
        result, decisions = overlay.apply_overlay([game("G1", "2026-11-22", None, "1")], [obs("1", "2026-11-22T21:25:00Z")])
        self.assertIsNone(result[0]["GameTime"])
        self.assertEqual(decisions[0]["Reason"], "kickoff-unknown")


if __name__ == "__main__":
    unittest.main()
