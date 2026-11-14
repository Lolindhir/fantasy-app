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


    def test_release_plan_contains_exact_scoped_raw_canonical_derived_outputs(self):
        from nfl_source_data_lib.injury_product_plan import build_injury_artifacts
        import json
        original = asset(2025, [report(2025)])
        plan = build_injury_artifacts(
            season=2025, source_csv=original, players=identities(),
        )
        self.assertEqual({
            "data-source/providers/nflverse/injuries/raw-2025.csv",
            "data-source/providers/nflverse/injuries/metadata-2025.json",
            "data-source/nfl/injuries/2025/05.json",
            "data-source/nfl/injuries/2025/manifest.json",
            "data-derived/nfl-injuries/2025.json",
        }, set(plan))
        self.assertEqual(original, plan["data-source/providers/nflverse/injuries/raw-2025.csv"])
        product_payload = json.loads(plan["data-derived/nfl-injuries/2025.json"])
        self.assertEqual(1, product_payload["Quality"]["SourceObservationCount"])
        self.assertFalse(any("player-availability" in p or "public/data/" in p for p in plan))
        self.assertEqual("nfl-injuries-v1", product_payload["ProductVersion"])

    def test_release_noop_and_changed_asset_are_distinguished(self):
        from nfl_source_data_lib.injury_product_plan import build_injury_artifacts, classify_injury_artifacts
        original = build_injury_artifacts(
            season=2025, source_csv=asset(2025, [report(2025)]), players=identities(),
        )
        fresh = classify_injury_artifacts(original, {}, season=2025)
        self.assertEqual(len(original), len(fresh["New"]))
        self.assertFalse(fresh["PublicationPerformed"])
        replay = classify_injury_artifacts(original, dict(original), season=2025)
        self.assertFalse(replay["RequiresWrites"])
        self.assertEqual(len(original), len(replay["Unchanged"]))
        correction = build_injury_artifacts(
            season=2025,
            source_csv=asset(2025, [report(2025, report_status="Out")]),
            players=identities(),
        )
        diff = classify_injury_artifacts(correction, dict(original), season=2025)
        self.assertTrue(diff["RequiresWrites"])
        self.assertEqual([], diff["ObsoleteRequiresReview"])
        self.assertIn("data-derived/nfl-injuries/2025.json", diff["Changed"])

    def test_missing_previous_week_must_be_reviewed_not_deleted(self):
        from nfl_source_data_lib.injury_product_plan import build_injury_artifacts, classify_injury_artifacts
        original = build_injury_artifacts(
            season=2025, source_csv=asset(2025, [
                report(2025, week="5"), report(2025, week="7")
            ]), players=identities(),
        )
        revised = build_injury_artifacts(
            season=2025, source_csv=asset(2025, [report(2025, week="5")]),
            players=identities(),
        )
        planned = classify_injury_artifacts(revised, dict(original), season=2025)
        self.assertEqual(["data-source/nfl/injuries/2025/07.json"], planned["ObsoleteRequiresReview"])
        self.assertFalse(planned["CanAutoApply"])

    def test_bad_expected_digest_or_empty_report_fails_before_plan(self):
        from nfl_source_data_lib.injury_product_plan import build_injury_artifacts
        source = asset(2025, [report(2025)])
        with self.assertRaisesRegex(ValueError, "does not match"):
            build_injury_artifacts(season=2025, source_csv=source,
                                   players=identities(), expected_source_sha256="f" * 64)
        with self.assertRaisesRegex(ValueError, "Empty injury report"):
            build_injury_artifacts(season=2025, source_csv=asset(2025, []), players=identities())

    def test_plan_path_is_exact_and_cannot_escape_scope(self):
        from nfl_source_data_lib.injury_product_plan import build_injury_artifacts, classify_injury_artifacts
        plan = build_injury_artifacts(
            season=2025, source_csv=asset(2025, [report(2025)]), players=identities(),
        )
        with self.assertRaisesRegex(ValueError, "Outside"):
            classify_injury_artifacts({
                **plan,
                "data-source/nfl/injuries/2025/../../data-meta/secret.json": b"bad",
            }, {}, season=2025)
        with self.assertRaisesRegex(ValueError, "Incomplete"):
            classify_injury_artifacts({
                p: v for p, v in plan.items()
                if not p.endswith("manifest.json")
            }, {}, season=2025)


    def test_read_only_plan_preview_detects_prior_output_without_writer(self):
        from nfl_injuries_preview import plan_preview
        from nfl_source_data_lib.injury_product_plan import build_injury_artifacts
        import tempfile
        source = asset(2025, [report(2025)])
        with tempfile.TemporaryDirectory() as location:
            root = Path(location)
            planned = plan_preview(
                csv_bytes=source, season=2025, identities=identities(), compare_root=root
            )
            self.assertTrue(planned["PreviewOnly"])
            self.assertFalse(planned["PublicationEnabled"])
            self.assertTrue(planned["ChangeSet"]["RequiresWrites"])
            self.assertEqual("empty-preview-baseline", plan_preview(
                csv_bytes=source, season=2025, identities=identities()
            )["ComparisonBasis"])
            self.assertEqual([], list(root.rglob("*")))
            expected = build_injury_artifacts(
                season=2025, source_csv=source, players=identities()
            )
            for path, value in expected.items():
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(value)
            delta = plan_preview(
                csv_bytes=source, season=2025, identities=identities(), compare_root=root
            )
            self.assertFalse(delta["ChangeSet"]["RequiresWrites"])
            self.assertEqual([], delta["ChangeSet"]["New"])
            self.assertEqual(len(expected), len(delta["ChangeSet"]["Unchanged"]))

    def test_schedule_provenance_in_plan_changes_without_source_change(self):
        from nfl_source_data_lib.injury_product_plan import build_injury_artifacts, classify_injury_artifacts
        import json
        raw = asset(2025, [report(2025)])
        a = {"Season": 2025, "Games": [
            {"GameID": "2025_05_X_HOU", "GameType": "REG", "Week": 5,
             "HomeTeam": "HOU", "AwayTeam": "NYG"}
        ]}
        b = {"Season": 2025, "Games": [
            {"GameID": "2025_05_NYG_HOU_CORRECTED", "GameType": "REG", "Week": 5,
             "HomeTeam": "HOU", "AwayTeam": "NYG"}
        ]}
        first = build_injury_artifacts(
            season=2025, source_csv=raw, players=identities(), schedule=a
        )
        second = build_injury_artifacts(
            season=2025, source_csv=raw, players=identities(), schedule=b
        )
        manifest_path = "data-source/nfl/injuries/2025/manifest.json"
        self.assertNotEqual(
            json.loads(first[manifest_path])["ScheduleGraphFingerprint"],
            json.loads(second[manifest_path])["ScheduleGraphFingerprint"],
        )
        delta = classify_injury_artifacts(second, first, season=2025)
        self.assertIn(manifest_path, delta["Changed"])
        self.assertIn("data-source/nfl/injuries/2025/05.json", delta["Changed"])
        self.assertIn("data-derived/nfl-injuries/2025.json", delta["Changed"])


    def test_official_release_digest_drives_daily_noop_or_refresh(self):
        from nfl_source_data_lib.injury_product_plan import plan_release_refresh
        import hashlib
        source = asset(2025, [report(2025)])
        digest = hashlib.sha256(source).hexdigest()
        upstream = {"assets": [{
            "name": "injuries_2025.csv", "id": 1234,
            "updated_at": "2026-11-14T07:11:00Z", "size": len(source),
            "digest": "sha256:" + digest,
            "browser_download_url":
                "https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_2025.csv",
        }]}
        metadata = {
            "SourceDataset": "nflverse.injuries", "Season": 2025,
            "AssetSha256": digest, "AssetByteSize": len(source),
        }
        decision = plan_release_refresh(upstream, season=2025, stored_metadata=metadata)
        self.assertEqual("no-op", decision["Action"])
        self.assertTrue(decision["FullSourceDigestAvailable"])
        changed = copy.deepcopy(upstream)
        changed["assets"][0]["digest"] = "sha256:" + ("f" * 64)
        self.assertEqual("download-and-validate", plan_release_refresh(
            changed, season=2025, stored_metadata=metadata,
        )["Action"])

    def test_release_missing_asset_is_retry_not_empty_product(self):
        from nfl_source_data_lib.injury_product_plan import plan_release_refresh
        decision = plan_release_refresh({"assets": []}, season=2026)
        self.assertEqual("retry-later", decision["Action"])
        self.assertIsNone(decision["SourceAsset"])

    def test_release_missing_digest_reuses_only_same_observed_revision(self):
        from nfl_source_data_lib.injury_product_plan import plan_release_refresh
        release = {"assets": [{
            "name": "injuries_2024.csv", "id": 993,
            "updated_at": "2025-02-11T07:08:00Z", "size": 62000,
            "digest": None,
            "browser_download_url":
                "https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_2024.csv",
        }]}
        known = {
            "SourceDataset": "nflverse.injuries", "Season": 2024,
            "AssetByteSize": 62000, "ReleaseAssetId": 993,
            "ReleaseAssetUpdatedAt": "2025-02-11T07:08:00Z",
        }
        self.assertEqual("no-op", plan_release_refresh(
            release, season=2024, stored_metadata=known,
        )["Action"])
        modified = copy.deepcopy(release)
        modified["assets"][0]["updated_at"] = "2025-02-12T07:08:00Z"
        self.assertEqual("download-and-validate", plan_release_refresh(
            modified, season=2024, stored_metadata=known,
        )["Action"])

    def test_release_duplicate_assets_or_wrong_source_url_fails_closed(self):
        from nfl_source_data_lib.injury_product_plan import plan_release_refresh
        row = {
            "name": "injuries_2026.csv", "id": 123, "size": 100,
            "updated_at": "2026-11-14T07:10:00Z", "digest": None,
            "browser_download_url": "https://example.com/untrusted.csv",
        }
        with self.assertRaisesRegex(ValueError, "official URL"):
            plan_release_refresh({"assets": [row]}, season=2026)
        with self.assertRaisesRegex(ValueError, "Multiple"):
            plan_release_refresh({"assets": [row, dict(row)]}, season=2026)


    def test_release_asset_metadata_is_attested_by_actual_downloaded_bytes(self):
        from nfl_source_data_lib.injury_product_plan import (
            build_injury_artifacts, plan_release_refresh,
        )
        import hashlib
        import json
        source = asset(2025, [report(2025)])
        digest = hashlib.sha256(source).hexdigest()
        upstream = {"assets": [{
            "name": "injuries_2025.csv", "id": 1234,
            "updated_at": "2026-11-14T07:11:00Z", "size": len(source),
            "digest": "sha256:" + digest,
            "browser_download_url":
                "https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_2025.csv",
        }]}
        release_asset = plan_release_refresh(upstream, season=2025)["SourceAsset"]
        artifacts = build_injury_artifacts(
            season=2025, source_csv=source, players=identities(),
            release_asset=release_asset,
        )
        metadata = json.loads(artifacts[
            "data-source/providers/nflverse/injuries/metadata-2025.json"
        ])
        self.assertEqual("matched-provided-release-digest", metadata["AssetDigestVerification"])
        self.assertEqual(1234, metadata["ReleaseAssetId"])
        self.assertEqual("2026-11-14T07:11:00Z", metadata["ReleaseAssetUpdatedAt"])
        changed = dict(release_asset)
        changed["ByteSize"] += 1
        with self.assertRaisesRegex(ValueError, "mismatch"):
            build_injury_artifacts(
                season=2025, source_csv=source, players=identities(),
                release_asset=changed,
            )


if __name__ == "__main__":
    unittest.main()
