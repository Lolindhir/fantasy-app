"""Strict synthetic Golden cases for the Injury Source→Canonical→Derived v1 path."""
from __future__ import annotations

import copy
import csv
import io
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nfl_source_data_lib.injury_reports import parse_injury_report_csv
from nfl_source_data_lib.injury_canonical import canonicalize_injury_reports
from derived_data_lib.nfl_injuries import derive_nfl_injuries

COMMON = [
    "season", "game_type", "team", "week", "gsis_id", "position", "full_name",
    "first_name", "last_name", "report_primary_injury", "report_secondary_injury",
    "report_status", "practice_primary_injury", "practice_secondary_injury",
    "practice_status",
]
GSIS = "00-0039999"


def report(season=2025, **changes):
    row = {
        "season": str(season), "game_type": "REG", "team": "HOU", "week": "5",
        "gsis_id": GSIS, "position": "TE", "full_name": "Sample Player",
        "first_name": "Sample", "last_name": "Player",
        "report_primary_injury": "Knee", "report_secondary_injury": "",
        "report_status": "Questionable", "practice_primary_injury": "Knee",
        "practice_secondary_injury": "", "practice_status": "Full Participation in Practice",
        "date_modified": "2024-10-09 17:30:00", "season_type": "REG",
    }
    row.update(changes)
    return row


def asset(season, reports):
    header = COMMON + (["date_modified"] if season <= 2024 else ["season_type"])
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=header, lineterminator="\n")
    writer.writeheader()
    writer.writerows([{field: row[field] for field in header} for row in reports])
    return output.getvalue().encode("utf-8")


def identities(*, ambiguous=False):
    rows = [{"CanonicalPlayerID": "NFLP-1", "IDs": {"GSIS": GSIS}, "IDAliases": {"GSIS": ["00-0000001"]}}]
    if ambiguous:
        rows.append({"CanonicalPlayerID": "NFLP-2", "IDs": {"GSIS": GSIS}})
    return {"Players": rows}


def product(season=2025, reports=None, *, identity=None, schedule=None):
    raw = asset(season, reports or [report(season)])
    parsed = parse_injury_report_csv(raw, season=season)
    canonical = canonicalize_injury_reports(parsed, identity if identity is not None else identities(), schedule=schedule)
    return canonical, derive_nfl_injuries(canonical)


class NflInjuriesProductTests(unittest.TestCase):
    def test_original_field_fidelity_and_independent_statuses(self):
        raw_row = report(2025, report_status="", practice_status="Full Participation in Practice",
                         report_primary_injury="", report_secondary_injury="",
                         practice_primary_injury="Not injury related - resting player",
                         practice_secondary_injury="")
        canonical, derived = product(reports=[raw_row])
        observation = canonical["Partitions"][0]["Observations"][0]
        self.assertEqual("", observation["OriginalFields"]["report_status"])
        self.assertEqual("Full Participation in Practice", observation["OriginalFields"]["practice_status"])
        self.assertEqual("Not injury related - resting player",
                         derived["ObservedPlayerWeeks"][0]["Observations"][0]["Reasons"]["practice_primary_injury"])
        self.assertEqual("unknown-not-healthy-or-available", derived["MissingReportMeaning"])
        self.assertEqual([{"Week": 5, "GameType": "REG", "SourceTeam": "HOU", "ReportCount": 1}],
                         derived["ObservedTeamWeeks"])
        self.assertEqual(1, derived["Quality"]["ObservedTeamWeekCount"])
        self.assertEqual("retrospective-source-snapshot-not-point-in-time", derived["TemporalEvidence"])

    def test_same_week_status_revision_kept_not_deduplicated_or_ordered(self):
        rows = [report(2024, report_status="Questionable", week="15"),
                report(2024, report_status="Out", week="15", date_modified="2024-12-14 17:00")]
        canonical, derived = product(2024, rows)
        observed = canonical["Partitions"][0]["Observations"]
        self.assertEqual(2, len(observed))
        self.assertEqual(["Questionable", "Out"], [r["OriginalFields"]["report_status"] for r in observed])
        self.assertEqual([1, 2], [r["RowOrdinal"] for r in observed])
        self.assertEqual([None, None], [r["SourceModifiedAtUtc"] for r in observed])
        self.assertEqual(1, derived["Quality"]["MultipleObservationPlayerWeeks"])
        self.assertEqual("not-inferred-from-row-order", derived["ObservedPlayerWeeks"][0]["StatusOrdering"])

    def test_trajectory_has_observed_weeks_and_gaps_not_duration(self):
        rows = [report(2025, week="5", report_primary_injury="Toe"),
                report(2025, week="7", report_primary_injury="Toe")]
        _, derived = product(2025, rows)
        report_trajectories = [row for row in derived["ObservedReasonTrajectories"]
                               if row["ReasonField"] == "report_primary_injury"]
        self.assertEqual(1, len(report_trajectories))
        trajectory = report_trajectories[0]
        self.assertEqual([5, 7], trajectory["ObservedWeeks"])
        self.assertEqual([6], trajectory["GapWeeks"])
        self.assertEqual(2, trajectory["CountObservedWeeks"])
        self.assertNotIn("GamesMissed", trajectory)
        self.assertNotIn("ReturnDate", trajectory)

    def test_ambiguous_identity_never_selects_first_by_name(self):
        canonical, derived = product(reports=[report(2025)], identity=identities(ambiguous=True))
        row = canonical["Partitions"][0]["Observations"][0]
        self.assertEqual("ambiguous", row["IdentityResolution"])
        self.assertIsNone(row["CanonicalPlayerID"])
        self.assertIsNone(derived["ObservedPlayerWeeks"][0]["CanonicalPlayerID"])
        self.assertEqual(1, derived["Quality"]["RowsWithoutUniformCurrentIdentity"])

    def test_unresolved_source_report_kept(self):
        canonical, derived = product(reports=[report(2025)], identity={"Players": []})
        self.assertEqual(1, canonical["Quality"]["IdentityResolutionCounts"]["unresolved"])
        self.assertEqual(1, derived["Quality"]["SourceObservationCount"])
        self.assertIsNone(canonical["Partitions"][0]["Observations"][0]["CanonicalPlayerID"])

    def test_unmatched_cancelled_game_evidence_not_lost(self):
        schedule = {"Season": 2022, "Games": [
            {"Week": 17, "GameType": "REG", "GameID": "2022_17_OTHER", "HomeTeam": "NYG", "AwayTeam": "PHI"}
        ]}
        canonical, derived = product(2022, [report(2022, team="BUF", week="17")], schedule=schedule)
        row = canonical["Partitions"][0]["Observations"][0]
        self.assertEqual("not-found", row["GameLinkState"])
        self.assertIsNone(row["GameID"])
        self.assertEqual(1, derived["Quality"]["SourceObservationCount"])

    def test_explicit_game_link_and_source_team_preservation(self):
        schedule = {"Season": 2025, "Games": [
            {"Week": 5, "GameType": "REG", "GameID": "2025_05_X_HOU", "HomeTeam": "HOU", "AwayTeam": "X"}
        ]}
        canonical, _ = product(schedule=schedule)
        row = canonical["Partitions"][0]["Observations"][0]
        self.assertEqual("2025_05_X_HOU", row["GameID"])
        self.assertEqual("HOU", row["SourceTeam"])
        self.assertEqual("linked", row["GameLinkState"])
        self.assertEqual("current-graph-not-historical-point-in-time",
                         canonical["Partitions"][0]["IdentityTimeBasis"])

    def test_blank_reason_and_status_remain_unknown_not_injury(self):
        blank = report(2025, **{field: "" for field in (
            "report_primary_injury", "report_secondary_injury", "report_status",
            "practice_primary_injury", "practice_secondary_injury", "practice_status"
        )})
        _, derived = product(reports=[blank])
        self.assertEqual(1, derived["Quality"]["RowsWithoutReasonsOrStatuses"])
        self.assertEqual([], derived["ObservedReasonTrajectories"])
        self.assertEqual(1, derived["Quality"]["ObservedPlayerWeekCount"])

    def test_deterministic_replay_and_failed_partial_input(self):
        c1, d1 = product()
        c2, d2 = product()
        self.assertEqual(c1, c2)
        self.assertEqual(d1, d2)
        corrupted = copy.deepcopy(c1)
        corrupted["Partitions"][0]["Observations"].append(corrupted["Partitions"][0]["Observations"][0])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            derive_nfl_injuries(corrupted)

    def test_offline_preview_digest_gate_and_no_publisher(self):
        from nfl_injuries_preview import preview
        csv_data = asset(2025, [report(2025)])
        sample = preview(csv_bytes=csv_data, season=2025, identities=identities())
        self.assertTrue(sample["PreviewOnly"])
        self.assertFalse(sample["Provenance"]["PublicationEnabled"])
        self.assertEqual("not-independently-verified", sample["Provenance"]["InputVerification"])
        self.assertEqual(1, sample["DerivedQuality"]["SourceObservationCount"])
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            preview(csv_bytes=csv_data, season=2025, identities=identities(), expected_sha256="f" * 64)

    def test_header_digest_and_no_later_provider_status_leakage(self):
        canonical, derived = product(2025)
        self.assertEqual(canonical["SourceAssetSha256"], derived["SourceAssetSha256"])
        self.assertEqual(canonical["IdentityGraphFingerprint"], derived["IdentityGraphFingerprint"])
        self.assertNotIn("Healthy", derived)
        self.assertNotIn("ScoringAvailability", derived)
        self.assertEqual(1, derived["Quality"]["ObservedWeekCount"])


if __name__ == "__main__":
    unittest.main()
