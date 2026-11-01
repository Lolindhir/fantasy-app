from __future__ import annotations

import json
import sys
import unittest
from datetime import date
from pathlib import Path

SCRIPT_DIRECTORY = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIRECTORY))

import canonical_player_inputs as module  # noqa: E402

ROOT = Path(__file__).resolve().parents[4]
LEAGUE_ID = "nfl-reise"


class CanonicalPlayerInputsTests(unittest.TestCase):
    def test_age_is_deterministic_from_birth_date_and_reference_date(self) -> None:
        self.assertEqual(module.age_at("2000-01-01", date(2026, 1, 1)), round(9497 / 365.2425, 1))
        self.assertEqual(module.age_at("2000-01-01", date(2026, 1, 1)), module.age_at("2000-01-01", date(2026, 1, 1)))

    def test_age_is_none_for_missing_or_invalid_birth_date(self) -> None:
        self.assertIsNone(module.age_at(None, date(2026, 1, 1)))
        self.assertIsNone(module.age_at("not-a-date", date(2026, 1, 1)))

    def test_age_matches_app_shared_rounding_at_boundaries(self) -> None:
        from derived_data_lib.players_read_model import age_at as app_age
        for birth in ("2000-01-01", "2000-02-29", "1998-12-31", None, "bad-date"):
            for as_of in (date(2026, 1, 1), date(2026, 8, 8), date(2026, 11, 2)):
                self.assertEqual(app_age(birth, as_of), module.age_at(birth, as_of))

    def test_operations_age_date_is_explicit_or_league_local(self) -> None:
        import os
        from unittest import mock
        import operations_age_reference as ref
        # Explicit replay bypasses App timestamps and must be stable.
        with mock.patch.dict(os.environ, {"FM_OPERATIONS_AS_OF_DATE": "2026-08-08"}, clear=True):
            self.assertEqual(date(2026, 8, 8), ref.age_reference_date(ROOT, LEAGUE_ID))
        # Same instant is a different local date when the league is west of UTC.
        with mock.patch.dict(os.environ, {"FM_OPERATIONS_RUN_AT_UTC": "2026-11-02T00:30:00Z"}, clear=True):
            with mock.patch.object(ref, "load_league_metadata", return_value={"LeagueTimeZone": "America/Los_Angeles"}):
                self.assertEqual(date(2026, 11, 1), ref.age_reference_date(ROOT, LEAGUE_ID))
            with mock.patch.object(ref, "load_league_metadata", return_value={"LeagueTimeZone": "UTC"}):
                self.assertEqual(date(2026, 11, 2), ref.age_reference_date(ROOT, LEAGUE_ID))
        with mock.patch.dict(os.environ, {"FM_OPERATIONS_RUN_AT_UTC": "2026-11-02T00:30:00"}, clear=True):
            with mock.patch.object(ref, "load_league_metadata", return_value={"LeagueTimeZone": "UTC"}):
                with self.assertRaisesRegex(ref.OperationsAgeReferenceError, "UTC-aware"):
                    ref.age_reference_date(ROOT, LEAGUE_ID)
        with mock.patch.dict(os.environ, {"FM_OPERATIONS_AS_OF_DATE": "invalid"}, clear=True):
            with self.assertRaisesRegex(ref.OperationsAgeReferenceError, "YYYY-MM-DD"):
                ref.age_reference_date(ROOT, LEAGUE_ID)

    def test_injury_description_only_exists_with_a_designation(self) -> None:
        injured, details = module._injury_fields({"Status": "", "Notes": "ignored"})
        self.assertFalse(injured)
        self.assertEqual(details["Description"], "")
        injured, details = module._injury_fields(
            {"Status": "Out", "Notes": "", "BodyPart": "Knee", "StartDate": "2026-10-01"}
        )
        self.assertTrue(injured)
        self.assertEqual(details["Designation"], "Out")
        self.assertEqual(details["Description"], "Knee")
        self.assertEqual(details["Date"], "2026-10-01")
        self.assertIsNone(details["ReturnDate"])

    def test_repository_players_carry_valuation_without_players_json(self) -> None:
        manifest = json.loads(
            (ROOT / "data-source" / "leagues" / LEAGUE_ID / "manifest.json").read_text(encoding="utf-8")
        )
        season = int(str(manifest["CurrentCanonicalLeagueSeasonID"]).rsplit("-", 1)[-1])
        players = module.load_players(ROOT, LEAGUE_ID, season, date(2026, 10, 15))
        self.assertTrue(players)
        ids = [player["ID"] for player in players]
        self.assertEqual(len(ids), len(set(ids)))
        snapshot = module.latest_valuation_snapshot(ROOT, LEAGUE_ID, season)
        by_id = {str(row["PlayerID"]): row for row in snapshot["Players"] if row.get("PlayerID")}
        valued = [player for player in players if player["ID"] in by_id]
        self.assertTrue(valued)
        for player in valued:
            self.assertEqual(player["Salary"], by_id[player["ID"]]["Salary"])
            self.assertEqual(player["SalaryProjected"], by_id[player["ID"]]["SalaryProjected"])
        for player in players:
            self.assertIn(player["Position"], {"QB", "RB", "WR", "TE", "K"})
            self.assertIsInstance(player["IsFreeAgent"], bool)

    def test_current_repository_age_shadow_at_published_players_date(self) -> None:
        from datetime import datetime
        from zoneinfo import ZoneInfo
        from league_metadata import load_league_metadata, data_meta_root
        metadata = load_league_metadata(LEAGUE_ID, data_meta_root(ROOT))
        timestamps = json.loads((ROOT / "public/data/Timestamps.json").read_text(encoding="utf-8"))
        published_date = datetime.fromisoformat(timestamps["Players"].replace("Z", "+00:00")).astimezone(
            ZoneInfo(metadata["LeagueTimeZone"])
        ).date()
        manifest = json.loads(
            (ROOT / "data-source/leagues" / LEAGUE_ID / "manifest.json").read_text(encoding="utf-8")
        )
        season = int(str(manifest["CurrentCanonicalLeagueSeasonID"]).rsplit("-", 1)[-1])
        canonical = module.load_players(ROOT, LEAGUE_ID, season, published_date)
        published = {
            str(player["ID"]): player
            for player in json.loads((ROOT / "public/data/Players.json").read_text(encoding="utf-8"))
        }
        matched = [(row["ID"], row["Age"], published[row["ID"]].get("Age"))
                   for row in canonical if row["ID"] in published and row["Age"] is not None]
        self.assertTrue(matched, "No common players for Age shadow")
        self.assertEqual([], [(pid, actual, expected) for pid, actual, expected in matched if actual != expected])

    def test_source_files_name_the_newest_valuation_snapshot(self) -> None:
        manifest = json.loads(
            (ROOT / "data-source" / "leagues" / LEAGUE_ID / "manifest.json").read_text(encoding="utf-8")
        )
        season = int(str(manifest["CurrentCanonicalLeagueSeasonID"]).rsplit("-", 1)[-1])
        files = dict(module.source_files(ROOT, LEAGUE_ID, season))
        self.assertIn("player_valuation", files)
        self.assertTrue(all(path.is_file() for path in files.values()))


if __name__ == "__main__":
    unittest.main()
