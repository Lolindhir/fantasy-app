"""Focused historical injury source-fidelity regressions; no remote asset access."""

import csv
import hashlib
import io
import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
from nfl_source_data_lib.injury_reports import parse_injury_report_csv

BASE = [
    "season", "game_type", "team", "week", "gsis_id", "position",
    "full_name", "first_name", "last_name", "report_primary_injury",
    "report_secondary_injury", "report_status", "practice_primary_injury",
    "practice_secondary_injury", "practice_status",
]


def make_csv(season, rows, *, variant=None):
    header = BASE + (
        ["date_modified"]
        if (variant == "legacy" or (variant is None and season <= 2024))
        else ["season_type"]
    )
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=header, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({field: row[field] for field in header})
    return stream.getvalue().encode("utf-8")


def report(season, **changes):
    default = {
        "season": str(season), "game_type": "REG", "team": "HOU",
        "week": "15", "gsis_id": "00-0039999", "position": "TE",
        "full_name": "Sample Player", "first_name": "Sample", "last_name": "Player",
        "report_primary_injury": "Knee", "report_secondary_injury": "",
        "report_status": "Questionable", "practice_primary_injury": "Knee",
        "practice_secondary_injury": "", "practice_status": "Full Participation in Practice",
        "date_modified": "2024-12-12 15:00:00", "season_type": "REG",
    }
    default.update(changes)
    return default


class InjuryReportSourceTests(unittest.TestCase):
    def test_2024_same_player_week_revisions_are_distinct_and_ordered(self):
        original = make_csv(2024, [
            report(2024, report_status="Questionable", date_modified="2024-12-12 15:00:00"),
            report(2024, report_status="Out", date_modified="2024-12-13 17:00:00"),
        ])
        result = parse_injury_report_csv(original, season=2024)
        self.assertEqual(2, result["RowCount"])
        self.assertEqual(["Questionable", "Out"], [r["Fields"]["report_status"] for r in result["Rows"]])
        self.assertNotEqual(result["Rows"][0]["ObservationKey"], result["Rows"][1]["ObservationKey"])
        self.assertEqual([1, 2], [r["RowOrdinal"] for r in result["Rows"]])
        self.assertEqual(hashlib.sha256(original).hexdigest(), result["AssetSha256"])

    def test_2025_status_dimensions_and_provider_blank_values_are_preserved(self):
        original = make_csv(2025, [
            report(2025, report_status="Questionable", practice_status="Full Participation in Practice"),
            report(2025, report_status="", practice_primary_injury="Not injury related - resting player"),
            report(2025, report_status="", report_primary_injury="", practice_primary_injury="",
                   report_secondary_injury="", practice_secondary_injury="", practice_status=""),
        ])
        result = parse_injury_report_csv(original, season=2025)
        self.assertEqual("season-type", result["SourceSchema"])
        self.assertNotIn("date_modified", result["Header"])
        self.assertEqual("Questionable", result["Rows"][0]["Fields"]["report_status"])
        self.assertEqual("Full Participation in Practice", result["Rows"][0]["Fields"]["practice_status"])
        self.assertEqual("", result["Rows"][1]["Fields"]["report_status"])
        self.assertEqual("Not injury related - resting player", result["Rows"][1]["Fields"]["practice_primary_injury"])
        self.assertEqual("", result["Rows"][2]["Fields"]["report_primary_injury"])
        self.assertEqual(3, result["RowCount"])

    def test_embedded_newlines_and_note_are_not_normalized(self):
        note = 'Not injury related - personal matter\n"Medical note"'
        original = make_csv(2024, [report(2024, report_status="Note", report_primary_injury=note)])
        result = parse_injury_report_csv(original, season=2024)
        self.assertEqual(note, result["Rows"][0]["Fields"]["report_primary_injury"])
        self.assertEqual("Note", result["Rows"][0]["Fields"]["report_status"])

    def test_older_probable_and_practice_out_are_not_game_out(self):
        original = make_csv(2012, [report(2012, report_status="Probable", practice_status="Out (Definitely Will Not Play)")])
        result = parse_injury_report_csv(original, season=2012)
        self.assertEqual("Probable", result["Rows"][0]["Fields"]["report_status"])
        self.assertEqual("Out (Definitely Will Not Play)", result["Rows"][0]["Fields"]["practice_status"])

    def test_identical_rows_get_new_observation_identity_after_asset_revision(self):
        row = report(2024)
        first = make_csv(2024, [row])
        updated = make_csv(2024, [row, report(2024, report_status="Out")])
        a = parse_injury_report_csv(first, season=2024)
        b = parse_injury_report_csv(updated, season=2024)
        self.assertNotEqual(a["Rows"][0]["ObservationKey"], b["Rows"][0]["ObservationKey"])

    def test_wrong_header_width_and_year_are_rejected(self):
        # Profiles are validated against the header, not the year. A mixed
        # profile or unknown column is rejected even in an otherwise valid CSV.
        mixed = make_csv(2024, [report(2024)]).replace(
            b"date_modified\n", b"date_modified,season_type\n", 1)
        with self.assertRaisesRegex(ValueError, "unexpected header"):
            parse_injury_report_csv(mixed, season=2024)
        with self.assertRaisesRegex(ValueError, "wrong season"):
            parse_injury_report_csv(make_csv(2025, [report(2024)]), season=2025)
        with self.assertRaisesRegex(ValueError, "logical data row"):
            parse_injury_report_csv(make_csv(2025, [report(2025)]) + b"2025,REG\n", season=2025)
        with self.assertRaisesRegex(ValueError, "invalid GSIS"):
            parse_injury_report_csv(make_csv(2025, [report(2025, gsis_id="")]), season=2025)

    def test_header_schema_is_detected_independently_of_season(self):
        # Header recognition is NOT approval to import unaudited old assets.
        # Publication still requires verified original bytes and source review.
        for year in (2010, 2024, 2027):
            for variant, expected in (("legacy", "date-modified"),
                                      ("new", "season-type")):
                result = parse_injury_report_csv(
                    make_csv(year, [report(year)], variant=variant), season=year)
                self.assertEqual(expected, result["SourceSchema"])
        bad_profile = make_csv(2027, [report(2027)], variant="new").replace(
            b"season_type", b"not_an_accepted_column", 1)
        with self.assertRaisesRegex(ValueError, "unexpected header"):
            parse_injury_report_csv(bad_profile, season=2027)

    def test_invalid_assets_and_season_identifiers(self):
        from nfl_source_data_lib.injury_reports import valid_injury_season
        for invalid in (-123, 0, 999, 10000, True, "2025"):
            self.assertFalse(valid_injury_season(invalid))
            with self.assertRaisesRegex(ValueError, "four-digit"):
                parse_injury_report_csv(b"", season=invalid)
        self.assertTrue(valid_injury_season(2010))
        self.assertTrue(valid_injury_season(2027))
        with self.assertRaisesRegex(ValueError, "empty"):
            parse_injury_report_csv(b"", season=2027)
        with self.assertRaisesRegex(ValueError, "UTF-8"):
            parse_injury_report_csv(b"\xff", season=2025)
        with self.assertRaisesRegex(ValueError, "empty"):
            parse_injury_report_csv(b"", season=2025)


if __name__ == "__main__":
    unittest.main()
