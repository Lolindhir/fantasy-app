"""Fast contract checks for the pure Schedule Outlook V1 product document (#1519 I5b)."""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
from derived_data_lib import league_schedule_outlook as product  # noqa: E402
import league_schedule_outlook_preview as source_preview  # noqa: E402


def sample(week: int = 6):
    rating_week = None if week == 0 else week
    return {
        "PreviewOnly": True,
        "CanonicalLeagueID": "test-league",
        "CanonicalLeagueSeasonID": "test-season",
        "Season": 2025,
        "Models": {"ScheduleOutlook": "schedule-outlook-v1",
                   "SeasonStats": None if week == 0 else "season-stats-v1"},
        "AsOf": {"AfterWeek": week, "RatingWeek": rating_week},
        "RegularSeason": {"AfterWeek": week, "RatingWeek": rating_week,
                          "UpcomingMatchups": [], "Teams": []},
        "Playoffs": {"Format": {"PlayoffStartWeek": 14}, "Paths": []},
    }


class ScheduleOutlookV1DocumentTests(unittest.TestCase):
    def test_document_has_versioned_shared_derived_contract_without_preview_flag(self):
        row = product.assemble(sample(), selected_model_id="schedule-outlook-v1")
        self.assertEqual(1, row["SchemaVersion"])
        self.assertEqual("league-schedule-outlook", row["Product"])
        self.assertEqual("test-league", row["CanonicalLeagueID"])
        self.assertEqual("test-season", row["CanonicalLeagueSeasonID"])
        self.assertEqual({"AfterWeek": 6, "RatingWeek": 6}, row["AsOf"])
        self.assertEqual({"ScheduleOutlook": "schedule-outlook-v1", "SeasonStats": "season-stats-v1"}, row["Models"])
        self.assertEqual({"Reconstruction": "reconstructed-from-accepted-sources"}, row["Provenance"])
        self.assertNotIn("PreviewOnly", row)
        self.assertNotIn("ObservedAt", row)
        self.assertNotIn("GeneratedAt", row)

    def test_week_zero_has_no_fake_historical_team_strength(self):
        row = product.assemble(sample(0), selected_model_id="schedule-outlook-v1")
        self.assertIsNone(row["AsOf"]["RatingWeek"])
        self.assertIsNone(row["Models"]["SeasonStats"])

    def test_model_selection_never_falls_back(self):
        for model_id in ("season-stats-v1", "schedule-outlook-v2", "", None):
            with self.subTest(model=model_id), self.assertRaises(ValueError):
                product.assemble(sample(), selected_model_id=model_id)
        bad = sample()
        bad["Models"]["ScheduleOutlook"] = "other"
        with self.assertRaisesRegex(product.LeagueScheduleOutlookError, "Selected model"):
            product.assemble(bad, selected_model_id="schedule-outlook-v1")

    def test_cutoff_identity_and_upstream_evidence_fail_closed(self):
        for path, value in (
            (("CanonicalLeagueID",), ""),
            (("Season",), True),
            (("AsOf", "AfterWeek"), -1),
            (("AsOf", "RatingWeek"), 9),
            (("RegularSeason", "AfterWeek"), 7),
            (("Models", "SeasonStats"), None),
            (("Playoffs", "Paths"), None),
        ):
            bad = copy.deepcopy(sample())
            target = bad
            for segment in path[:-1]:
                target = target[segment]
            target[path[-1]] = value
            with self.subTest(path=path), self.assertRaises(product.LeagueScheduleOutlookError):
                product.assemble(bad, selected_model_id="schedule-outlook-v1")
        with self.assertRaisesRegex(product.LeagueScheduleOutlookError, "validated read-only"):
            product.assemble({"PreviewOnly": False}, selected_model_id="schedule-outlook-v1")

    def test_no_volatile_clocks_and_deterministic_json(self):
        first = product.assemble(sample(), selected_model_id="schedule-outlook-v1")
        second = product.assemble(copy.deepcopy(sample()), selected_model_id="schedule-outlook-v1")
        encode = lambda x: json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        self.assertEqual(encode(first), encode(second))
        bad = sample()
        bad["GeneratedAt"] = "2025-12-31T23:59:59Z"
        with self.assertRaisesRegex(product.LeagueScheduleOutlookError, "Volatile"):
            product.assemble(bad, selected_model_id="schedule-outlook-v1")

    def test_real_2025_after_week_six_builds_from_source_preview_without_new_writer(self):
        preview = source_preview.preview(TOOLS.parent, "nfl-reise", 2025, 6)
        document = product.assemble(preview, selected_model_id="schedule-outlook-v1")
        self.assertEqual(2025, document["Season"])
        self.assertEqual(6, document["AsOf"]["AfterWeek"])
        self.assertEqual(21, len(document["RegularSeason"]["UpcomingMatchups"]))
        self.assertTrue(document["Playoffs"]["Paths"])
        self.assertTrue(all(x["WinnerCanonicalLeagueRosterID"] is None
                            for x in document["Playoffs"]["Paths"]))
        self.assertEqual("reconstructed-from-accepted-sources", document["Provenance"]["Reconstruction"])


if __name__ == "__main__":
    unittest.main()
