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


    def test_schedule_fingerprint_tracks_only_observed_report_game_links(self):
        from nfl_source_data_lib.injury_product_plan import (
            build_injury_artifacts, classify_injury_artifacts,
        )
        import json
        raw = asset(2025, [report(2025)])
        observed = {"GameID": "2025_05_NYG_HOU", "GameType": "REG", "Week": 5,
                    "HomeTeam": "HOU", "AwayTeam": "NYG", "KickoffUtc": "earlier",
                    "HomeScore": 0}
        unrelated = {"GameID": "2025_07_NYJ_BUF", "GameType": "REG", "Week": 7,
                     "HomeTeam": "NYJ", "AwayTeam": "BUF"}
        base = {"Season": 2025, "Games": [observed, unrelated]}
        first = build_injury_artifacts(
            season=2025, source_csv=raw, players=identities(), schedule=base,
        )
        irrelevant = copy.deepcopy(base)
        irrelevant["GeneratedAtUtc"] = "new-fetched-time"
        irrelevant["Games"][0]["KickoffUtc"] = "later"
        irrelevant["Games"][0]["HomeScore"] = 42
        irrelevant["Games"][1]["GameID"] = "2025_07_NYJ_BUF_CORRECTED"
        irrelevant["Games"].reverse()
        same = build_injury_artifacts(
            season=2025, source_csv=raw, players=identities(), schedule=irrelevant,
        )
        self.assertEqual(first, same)
        self.assertFalse(classify_injury_artifacts(same, first, season=2025)["RequiresWrites"])
        manifest = json.loads(first["data-source/nfl/injuries/2025/manifest.json"])
        self.assertIsInstance(manifest["ScheduleGraphFingerprint"], str)
        # Adding an extra candidate for a reported team-week is not harmless:
        # the previously linked GameID becomes ambiguous and must be reattested.
        conflicting = copy.deepcopy(base)
        conflicting["Games"].append({
            "GameID": "2025_05_NYG_HOU_DUP", "GameType": "REG", "Week": 5,
            "HomeTeam": "HOU", "AwayTeam": "NYG",
        })
        changed = build_injury_artifacts(
            season=2025, source_csv=raw, players=identities(), schedule=conflicting,
        )
        delta = classify_injury_artifacts(changed, first, season=2025)
        self.assertIn("data-source/nfl/injuries/2025/manifest.json", delta["Changed"])
        self.assertIn("data-source/nfl/injuries/2025/05.json", delta["Changed"])
        self.assertIn("data-derived/nfl-injuries/2025.json", delta["Changed"])
        observation = json.loads(changed["data-source/nfl/injuries/2025/05.json"])[
            "Observations"][0]
        self.assertEqual("ambiguous", observation["GameLinkState"])
        self.assertIsNone(observation["GameID"])

    def test_historical_pilot_binds_preflight_digest_before_raw_commit(self):
        import yaml
        root = Path(__file__).resolve().parents[2]
        wrapper = yaml.safe_load((root / ".github/workflows/sync-nfl-injuries.yml").read_text(encoding="utf-8"))
        publisher = yaml.safe_load((root / ".github/workflows/sync-nfl-source-data.yml").read_text(encoding="utf-8"))
        self.assertIn("source_sha256", wrapper["jobs"]["historical_pilot_preflight"]["outputs"])
        self.assertIn("expected_injury_sha256", wrapper["jobs"]["historical_pilot_publish"]["with"])
        self.assertIn("expected_injury_sha256", publisher.get("on", publisher.get(True))["workflow_call"]["inputs"])
        script = next(s["run"] for s in publisher["jobs"]["sync"]["steps"] if s.get("name") == "Sync, validate and publish NFL source data")
        self.assertIn('actual_injury_sha="$(sha256sum', script)
        self.assertIn("no Raw commit", script)
        self.assertLess(script.index('actual_injury_sha="$(sha256sum'), script.index("git add -- data-source/providers"))

    def test_readonly_historical_pilot_selects_latest_verified_missing_season(self):
        from nfl_injuries_refresh import preflight_next_injury_history
        import tempfile
        import hashlib
        import json
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            league = root / "data-source/leagues/test/manifest.json"
            league.parent.mkdir(parents=True)
            league.write_text(json.dumps({
                "CurrentCanonicalLeagueSeasonID": "current",
                "Seasons": [{"CanonicalLeagueSeasonID": "current", "Season": 2026}],
            }), encoding="utf-8")
            players = root / "data-source/nfl/identities/players.json"
            players.parent.mkdir(parents=True)
            players.write_text(json.dumps(identities()), encoding="utf-8")
            for season in (2010, 2025):
                schedule = root / f"data-source/nfl/schedules/{season}.json"
                schedule.parent.mkdir(parents=True, exist_ok=True)
                schedule.write_text(json.dumps({"Season": season, "Games": [{
                    "Week": 5, "GameType": "REG", "GameID": f"{season}_05_X_HOU",
                    "HomeTeam": "HOU", "AwayTeam": "X",
                }]}), encoding="utf-8")
            original = asset(2025, [report(2025)])
            def release_item(season, *, with_digest):
                return {
                    "name": f"injuries_{season}.csv", "size": len(original),
                    "id": season, "updated_at": "2026-01-01T00:00:00Z",
                    "digest": "sha256:" + hashlib.sha256(original).hexdigest() if with_digest else None,
                    "browser_download_url":
                        f"https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_{season}.csv",
                }
            release = {"assets": [
                release_item(2010, with_digest=False),
                release_item(2025, with_digest=True),
            ]}
            result = preflight_next_injury_history(
                repo_root=root, fetch_release=lambda: release,
                fetch_asset=lambda _: original)
            self.assertEqual("verified-single-season-pilot", result["Status"])
            self.assertEqual(2025, result["Season"])
            self.assertEqual(1, result["SourceRowCount"])
            self.assertFalse(result["PublicationPerformed"])
            self.assertFalse((root / "data-source/providers/nflverse/injuries").exists())
            (root / "data-derived/nfl-injuries").mkdir(parents=True)
            (root / "data-derived/nfl-injuries/2025.json").write_text("{}", encoding="utf-8")
            noop = preflight_next_injury_history(
                repo_root=root, fetch_release=lambda: release,
                fetch_asset=lambda _: (_ for _ in ()).throw(AssertionError("Unexpected download")))
            self.assertIsNone(noop["Season"])
            self.assertEqual("no-verified-history-missing", noop["Status"])
            self.assertEqual([2010], noop["BlockedSeasons"])

    def test_historical_pilot_blocks_bad_source_and_unresolved_identity(self):
        from nfl_injuries_refresh import preflight_next_injury_history
        import hashlib
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            league = root / "data-source/leagues/test/manifest.json"
            league.parent.mkdir(parents=True)
            league.write_text(json.dumps({
                "CurrentCanonicalLeagueSeasonID": "current",
                "Seasons": [{"CanonicalLeagueSeasonID": "current", "Season": 2026}],
            }), encoding="utf-8")
            sched = root / "data-source/nfl/schedules/2025.json"
            sched.parent.mkdir(parents=True)
            sched.write_text(json.dumps({"Season": 2025, "Games": [{
                "Week": 5, "GameType": "REG", "GameID": "2025_05_X_HOU",
                "HomeTeam": "HOU", "AwayTeam": "X",
            }]}), encoding="utf-8")
            players = root / "data-source/nfl/identities/players.json"
            players.parent.mkdir(parents=True)
            players.write_text(json.dumps({"Players": []}), encoding="utf-8")
            original = asset(2025, [report(2025)])
            metadata = {"assets": [{
                "name": "injuries_2025.csv", "size": len(original),
                "id": 5, "updated_at": "2026-01-01T00:00:00Z",
                "digest": "sha256:" + hashlib.sha256(original).hexdigest(),
                "browser_download_url": "https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_2025.csv",
            }]}
            with self.assertRaisesRegex(ValueError, "SHA-256/size"):
                preflight_next_injury_history(
                    repo_root=root, fetch_release=lambda: metadata,
                    fetch_asset=lambda _: b"wrong")
            with self.assertRaisesRegex(ValueError, "needs identity/game-link review"):
                preflight_next_injury_history(
                    repo_root=root, fetch_release=lambda: metadata,
                    fetch_asset=lambda _: original)
            self.assertFalse((root / "data-source/providers/nflverse/injuries").exists())

    def test_release_inventory_discovers_years_without_cutoffs_and_gates_missing_digests(self):
        from nfl_source_data_lib.injury_product_plan import plan_injury_history_inventory
        import hashlib
        seed = asset(2025, [report(2025)])
        digest = hashlib.sha256(seed).hexdigest()
        def entry(year, asset_id, digest_or_none):
            return {"name": f"injuries_{year}.csv", "id": asset_id,
                "updated_at": "2026-11-16T08:00:00Z", "size": len(seed),
                "digest": "sha256:" + digest_or_none if digest_or_none else None,
                "browser_download_url":
                    f"https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_{year}.csv"}
        release = {"assets": [
            entry(2026, 60, digest),
            entry(2010, 10, None),
            entry(2024, 40, None),
            entry(2025, 50, digest),
            entry(2027, 70, digest),
            {"name": "injuries_2025.parquet", "id": 1},
        ]}
        result = plan_injury_history_inventory(
            release, current_season=2026, persisted_seasons=[2026],
            schedule_seasons=[2010, 2024, 2025, 2026, 2027],
        )
        self.assertEqual([2010, 2024, 2025, 2026, 2027], result["DiscoveredSeasons"])
        self.assertEqual([], result["PersistedMissingUpstream"])
        self.assertEqual([2025], result["CandidateSeasons"])
        orphan = plan_injury_history_inventory(
            release, current_season=2026, persisted_seasons=[2026, 2015],
        )
        self.assertEqual([2015], orphan["PersistedMissingUpstream"])
        self.assertEqual([2010, 2024], result["BlockedSeasons"])
        self.assertEqual([
            "blocked-unverified-original-revision",
            "blocked-unverified-original-revision",
            "candidate-requires-schema-and-identity-audit",
            "current-season",
            "future-not-imported",
        ], [row["State"] for row in result["SeasonStates"]])
        self.assertFalse(result["PublicationPerformed"])
        self.assertFalse(result["HistoricalImportAuthorized"])
        with self.assertRaisesRegex(ValueError, "Multiple upstream injury release assets"):
            plan_injury_history_inventory(
                {"assets": release["assets"] + [entry(2025, 999, digest)]},
                current_season=2026,
            )
        with self.assertRaisesRegex(ValueError, "official URL"):
            forged = copy.deepcopy(release)
            forged["assets"][3]["browser_download_url"] = "https://other.example.com/x"
            plan_injury_history_inventory(forged, current_season=2026)

    def test_discovery_validates_existing_raw_and_uses_canonical_current_season(self):
        from nfl_injuries_refresh import discover_injury_history
        import hashlib
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            league = root / "data-source/leagues/sample/manifest.json"
            league.parent.mkdir(parents=True)
            league.write_text(json.dumps({
                "CurrentCanonicalLeagueSeasonID": "sample-current",
                "Seasons": [{"CanonicalLeagueSeasonID": "sample-current",
                             "Season": 2026}],
            }), encoding="utf-8")
            sched = root / "data-source/nfl/schedules/2025.json"
            sched.parent.mkdir(parents=True)
            sched.write_text("{}", encoding="utf-8")
            source = asset(2025, [report(2025)])
            release = {"assets": [{
                "name": "injuries_2025.csv", "id": 7,
                "updated_at": "2026-11-16T08:00:00Z",
                "size": len(source), "digest": "sha256:" + hashlib.sha256(source).hexdigest(),
                "browser_download_url":
                    "https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_2025.csv",
            }]}
            first = discover_injury_history(repo_root=root, fetch_release=lambda: release)
            self.assertEqual([2025], first["CandidateSeasons"])
            data_root = root / "data-source/providers/nflverse/injuries"
            data_root.mkdir(parents=True)
            (data_root / "raw-2025.csv").write_bytes(source)
            (data_root / "metadata-2025.json").write_text(json.dumps({
                "SourceDataset": "nflverse.injuries", "Season": 2025,
                "AssetByteSize": len(source), "AssetSha256": hashlib.sha256(source).hexdigest(),
            }), encoding="utf-8")
            existing = discover_injury_history(repo_root=root, fetch_release=lambda: release)
            self.assertEqual([], existing["CandidateSeasons"])
            self.assertEqual("persisted-historical-reconciliation-required",
                             existing["SeasonStates"][0]["State"])
            (data_root / "raw-2025.csv").write_bytes(b"corrupt")
            with self.assertRaisesRegex(ValueError, "provenance failed"):
                discover_injury_history(repo_root=root, fetch_release=lambda: release)

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


    def test_offline_materializer_explicit_write_noop_and_plan(self):
        from nfl_injuries_materialize import stage_injury_season
        import hashlib
        import tempfile
        import json
        original = asset(2025, [report(2025)])
        digest = hashlib.sha256(original).hexdigest()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            kwargs = dict(repo_root=root, season=2025, csv_bytes=original,
                          players=identities(), expected_source_sha256=digest)
            planned = stage_injury_season(**kwargs)
            self.assertEqual("changes-planned", planned["Status"])
            self.assertFalse(planned["WritePerformed"])
            self.assertEqual([], list(root.rglob("*")))
            written = stage_injury_season(**kwargs, write=True)
            self.assertTrue(written["WritePerformed"])
            self.assertEqual("staged-local-worktree", written["Status"])
            self.assertEqual(5, len(written["ChangeSet"]["New"]))
            outputs = [p for p in root.rglob("*") if p.is_file()]
            self.assertEqual(5, len(outputs))
            self.assertEqual(original,
                (root / "data-source/providers/nflverse/injuries/raw-2025.csv").read_bytes())
            product = json.loads(
                (root / "data-derived/nfl-injuries/2025.json").read_text(encoding="utf-8"))
            self.assertEqual("nfl-injuries-v1", product["ProductVersion"])
            again = stage_injury_season(**kwargs, write=True)
            self.assertEqual("no-op", again["Status"])
            self.assertFalse(again["WritePerformed"])

    def test_offline_materializer_correction_without_removing_weeks(self):
        from nfl_injuries_materialize import stage_injury_season
        import hashlib
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            before = asset(2025, [report(2025, week="5"), report(2025, week="7")])
            after = asset(2025, [report(2025, week="5", report_status="Out"),
                                  report(2025, week="7")])
            basic = dict(repo_root=root, season=2025, players=identities())
            stage_injury_season(**basic, csv_bytes=before,
                expected_source_sha256=hashlib.sha256(before).hexdigest(), write=True)
            changed = stage_injury_season(**basic, csv_bytes=after,
                expected_source_sha256=hashlib.sha256(after).hexdigest(), write=True)
            self.assertTrue(changed["WritePerformed"])
            self.assertEqual([], changed["ChangeSet"]["ObsoleteRequiresReview"])
            self.assertIn("data-source/nfl/injuries/2025/05.json", changed["ChangeSet"]["Changed"])
            # SourceAssetSha256 and ObservationKey attest the entire upstream file,\n            # so a revised asset intentionally re-attests even unchanged weeks.\n            self.assertIn("data-source/nfl/injuries/2025/07.json", changed["ChangeSet"]["Changed"])

    def test_offline_materializer_obsolete_week_blocks_all_writes(self):
        from nfl_injuries_materialize import stage_injury_season
        import hashlib
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            before = asset(2025, [report(2025, week="5"), report(2025, week="7")])
            after = asset(2025, [report(2025, week="5", report_status="Out")])
            args = dict(repo_root=root, season=2025, players=identities(), write=True)
            stage_injury_season(**args, csv_bytes=before,
                expected_source_sha256=hashlib.sha256(before).hexdigest())
            original = {str(path.relative_to(root)): path.read_bytes()
                for path in root.rglob("*") if path.is_file()}
            with self.assertRaisesRegex(ValueError, "removed observed injury weeks"):
                stage_injury_season(**args, csv_bytes=after,
                    expected_source_sha256=hashlib.sha256(after).hexdigest())
            same = {str(path.relative_to(root)): path.read_bytes()
                for path in root.rglob("*") if path.is_file()}
            self.assertEqual(original, same)

    def test_offline_materializer_rejects_unverified_or_missing_asset(self):
        from nfl_injuries_materialize import stage_injury_season
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = asset(2025, [report(2025)])
            with self.assertRaisesRegex(ValueError, "requires an explicit expected digest"):
                stage_injury_season(repo_root=root, season=2025,
                    csv_bytes=source, players=identities(), write=True)
            decision = stage_injury_season(repo_root=root, season=2025,
                csv_bytes=source, players=identities(), write=True,
                release_json={"assets": []})
            self.assertEqual("upstream-not-ready", decision["Status"])
            self.assertFalse(decision["WritePerformed"])
            self.assertEqual([], list(root.rglob("*")))


    def test_offline_materializer_rejects_symlinked_source_parent(self):
        from nfl_injuries_materialize import stage_injury_season
        import hashlib
        import tempfile
        with tempfile.TemporaryDirectory() as root_folder, tempfile.TemporaryDirectory() as outside:
            root = Path(root_folder)
            (root / "data-source").symlink_to(Path(outside), target_is_directory=True)
            original = asset(2025, [report(2025)])
            with self.assertRaisesRegex(ValueError, "Symlink"):
                stage_injury_season(
                    repo_root=root, season=2025, csv_bytes=original,
                    players=identities(),
                    expected_source_sha256=hashlib.sha256(original).hexdigest(),
                    write=True,
                )
            self.assertEqual([], list(Path(outside).rglob("*")))


    def test_source_refresh_download_once_then_cached_noop(self):
        from nfl_injuries_refresh import refresh_injury_season
        import hashlib
        import tempfile
        source = asset(2025, [report(2025)])
        release = {"assets": [{
            "name": "injuries_2025.csv", "id": 321,
            "updated_at": "2026-11-14T07:10:00Z", "size": len(source),
            "digest": "sha256:" + hashlib.sha256(source).hexdigest(),
            "browser_download_url":
                "https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_2025.csv",
        }]}
        fetched = []
        def download(url):
            fetched.append(url)
            return source
        with tempfile.TemporaryDirectory() as folder:
            args = dict(repo_root=Path(folder), season=2025, players=identities(),
                fetch_release=lambda: release, fetch_asset=download, write=True)
            first = refresh_injury_season(**args)
            self.assertTrue(first["Downloaded"])
            self.assertTrue(first["WritePerformed"])
            second = refresh_injury_season(**args)
            self.assertFalse(second["Downloaded"])
            self.assertFalse(second["WritePerformed"])
            self.assertEqual("no-op", second["Status"])
            self.assertEqual(1, len(fetched))

    def test_source_refresh_rederives_from_cache_after_identity_change(self):
        from nfl_injuries_refresh import refresh_injury_season
        import hashlib
        import tempfile
        source = asset(2025, [report(2025)])
        release = {"assets": [{
            "name": "injuries_2025.csv", "id": 321,
            "updated_at": "2026-11-14T07:10:00Z", "size": len(source),
            "digest": "sha256:" + hashlib.sha256(source).hexdigest(),
            "browser_download_url":
                "https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_2025.csv",
        }]}
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            opts = dict(repo_root=root, season=2025, write=True,
                fetch_release=lambda: release,
                fetch_asset=lambda url: source)
            refresh_injury_season(**opts, players=identities())
            updated = identities()
            updated["Players"][0]["CanonicalPlayerID"] = "NFLP-REVISED"
            def should_not_download(url):
                raise AssertionError("Unchanged release must reuse saved raw CSV")
            changed = refresh_injury_season(**{**opts, "fetch_asset": should_not_download},
                players=updated)
            self.assertFalse(changed["Downloaded"])
            self.assertTrue(changed["WritePerformed"])
            self.assertIn("data-derived/nfl-injuries/2025.json",
                          changed["ChangeSet"]["Changed"])

    def test_source_refresh_digest_failure_keeps_previous_revision(self):
        from nfl_injuries_refresh import refresh_injury_season
        import hashlib
        import tempfile
        source = asset(2025, [report(2025)])
        digest = hashlib.sha256(source).hexdigest()
        release = {"assets": [{
            "name": "injuries_2025.csv", "id": 321,
            "updated_at": "2026-11-14T07:10:00Z", "size": len(source),
            "digest": "sha256:" + digest,
            "browser_download_url":
                "https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_2025.csv",
        }]}
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            args = dict(repo_root=root, season=2025, players=identities(), write=True)
            refresh_injury_season(**args, fetch_release=lambda: release,
                                  fetch_asset=lambda url: source)
            before = {str(p.relative_to(root)): p.read_bytes()
                for p in root.rglob("*") if p.is_file()}
            later = copy.deepcopy(release)
            later["assets"][0]["id"] = 322
            later["assets"][0]["digest"] = "sha256:" + "f" * 64
            with self.assertRaisesRegex(ValueError, "SHA-256 differs"):
                refresh_injury_season(**args, fetch_release=lambda: later,
                                      fetch_asset=lambda url: source)
            after = {str(p.relative_to(root)): p.read_bytes()
                for p in root.rglob("*") if p.is_file()}
            self.assertEqual(before, after)

    def test_source_refresh_read_only_and_missing_release_never_write(self):
        from nfl_injuries_refresh import refresh_injury_season
        import hashlib
        import tempfile
        source = asset(2025, [report(2025)])
        release = {"assets": [{
            "name": "injuries_2025.csv", "id": 321,
            "updated_at": "2026-11-14T07:10:00Z", "size": len(source),
            "digest": "sha256:" + hashlib.sha256(source).hexdigest(),
            "browser_download_url":
                "https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_2025.csv",
        }]}
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            args = dict(repo_root=root, season=2025, players=identities())
            dry = refresh_injury_season(**args, fetch_release=lambda: release,
                fetch_asset=lambda url: source)
            self.assertTrue(dry["Downloaded"])
            self.assertFalse(dry["WritePerformed"])
            missing = refresh_injury_season(**args, write=True,
                fetch_release=lambda: {"assets": []},
                fetch_asset=lambda url: (_ for _ in ()).throw(
                    AssertionError("Missing asset must never download")))
            self.assertEqual("upstream-not-ready", missing["Status"])
            self.assertEqual([], list(root.rglob("*")))


    def test_source_refresh_rejects_cached_source_path_symlink(self):
        from nfl_injuries_refresh import refresh_injury_season
        import hashlib
        import tempfile
        source = asset(2025, [report(2025)])
        release = {"assets": [{
            "name": "injuries_2025.csv", "id": 12,
            "updated_at": "2026-11-14T07:10:00Z", "size": len(source),
            "digest": "sha256:" + hashlib.sha256(source).hexdigest(),
            "browser_download_url":
                "https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_2025.csv",
        }]}
        with tempfile.TemporaryDirectory() as folder, tempfile.TemporaryDirectory() as other:
            root = Path(folder)
            (root / "data-source").symlink_to(Path(other), target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "Symlink"):
                refresh_injury_season(
                    repo_root=root, season=2025, players=identities(),
                    fetch_release=lambda: release,
                    fetch_asset=lambda url: source,
                )
            self.assertEqual([], list(Path(other).rglob("*")))


    def test_independent_raw_canonical_derived_phases_match_full_plan(self):
        from nfl_injuries_phase import run_injury_phase
        from nfl_source_data_lib.injury_product_plan import build_injury_artifacts
        import hashlib
        import tempfile
        raw = asset(2025, [report(2025, week="5"), report(2025, week="7")])
        source_digest = hashlib.sha256(raw).hexdigest()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            before = run_injury_phase(root, 2025, "raw",
                source_csv=raw, expected_source_sha256=source_digest)
            self.assertFalse(before["Written"])
            self.assertEqual([], list(root.rglob("*")))
            for phase, params in (
                ("raw", dict(source_csv=raw, expected_source_sha256=source_digest)),
                ("canonical", dict(players=identities())),
                ("derived", {}),
            ):
                result = run_injury_phase(root, 2025, phase, write=True, **params)
                self.assertTrue(result["Written"], phase)
                self.assertEqual("staged-local-worktree", result["Status"])
                replay = run_injury_phase(root, 2025, phase, write=True, **params)
                self.assertEqual("no-op", replay["Status"])
                self.assertFalse(replay["Written"])
            all_files = {str(p.relative_to(root)): p.read_bytes()
                         for p in root.rglob("*") if p.is_file()}
            full = build_injury_artifacts(
                season=2025, source_csv=raw, players=identities(),
                expected_source_sha256=source_digest,
            )
            self.assertEqual(full, all_files)

    def test_derived_phase_refuses_partial_or_corrupt_canonical_snapshot(self):
        from nfl_injuries_phase import run_injury_phase
        import hashlib
        import tempfile
        raw = asset(2025, [report(2025, week="5"), report(2025, week="7")])
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            run_injury_phase(root, 2025, "raw", write=True,
                source_csv=raw, expected_source_sha256=hashlib.sha256(raw).hexdigest())
            run_injury_phase(root, 2025, "canonical", write=True, players=identities())
            damaged = root / "data-source/nfl/injuries/2025/07.json"
            damaged.unlink()
            with self.assertRaisesRegex(ValueError, "week inventory differs"):
                run_injury_phase(root, 2025, "derived", write=True)
            self.assertFalse((root / "data-derived/nfl-injuries/2025.json").exists())

    def test_canonical_stage_fails_closed_if_raw_metadata_has_drifted(self):
        from nfl_injuries_phase import run_injury_phase
        import hashlib
        import json
        import tempfile
        raw = asset(2025, [report(2025)])
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with self.assertRaisesRegex(ValueError, "Required injury input is missing"):
                run_injury_phase(root, 2025, "canonical", players=identities())
            run_injury_phase(root, 2025, "raw", write=True,
                source_csv=raw, expected_source_sha256=hashlib.sha256(raw).hexdigest())
            meta_path = root / "data-source/providers/nflverse/injuries/metadata-2025.json"
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            meta["AssetSha256"] = "f" * 64
            meta_path.write_text(json.dumps(meta), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "not coherent"):
                run_injury_phase(root, 2025, "canonical", players=identities(), write=True)
            self.assertFalse((root / "data-source/nfl/injuries/2025").exists())

    def test_phase_recalculation_after_identity_change_preserves_raw(self):
        from nfl_injuries_phase import run_injury_phase
        import hashlib
        import tempfile
        raw = asset(2025, [report(2025)])
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            run_injury_phase(root, 2025, "raw", write=True, source_csv=raw,
                expected_source_sha256=hashlib.sha256(raw).hexdigest())
            original_path = root / "data-source/providers/nflverse/injuries/raw-2025.csv"
            original_bytes = original_path.read_bytes()
            run_injury_phase(root, 2025, "canonical", write=True, players=identities())
            run_injury_phase(root, 2025, "derived", write=True)
            changed_ids = identities()
            changed_ids["Players"][0]["CanonicalPlayerID"] = "NFLP-CHANGED"
            rewritten = run_injury_phase(root, 2025, "canonical", write=True,
                                         players=changed_ids)
            self.assertIn("data-source/nfl/injuries/2025/05.json", rewritten["Changed"])
            new_derived = run_injury_phase(root, 2025, "derived", write=True)
            self.assertIn("data-derived/nfl-injuries/2025.json", new_derived["Changed"])
            self.assertEqual(original_bytes, original_path.read_bytes())

    def test_raw_canonical_derived_do_not_cross_write_scope(self):
        from nfl_injuries_phase import run_injury_phase
        import hashlib
        import tempfile
        raw = asset(2025, [report(2025)])
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with self.assertRaisesRegex(ValueError, "requires an expected verified digest"):
                run_injury_phase(root, 2025, "raw", source_csv=raw, write=True)
            with self.assertRaisesRegex(ValueError, "must not depend on"):
                run_injury_phase(root, 2025, "raw", source_csv=raw,
                                 players=identities())
            with self.assertRaisesRegex(ValueError, "must read their persisted Source inputs"):
                run_injury_phase(root, 2025, "canonical", source_csv=raw,
                                 players=identities())
            with self.assertRaisesRegex(ValueError, "only canonical Injury product"):
                run_injury_phase(root, 2025, "derived", players=identities())
            self.assertEqual([], list(root.rglob("*")))

    def test_canonical_phase_obsolete_week_requires_manual_review(self):
        from nfl_injuries_phase import run_injury_phase
        import hashlib
        import tempfile
        older = asset(2025, [report(2025, week="5"), report(2025, week="7")])
        newer = asset(2025, [report(2025, week="5")])
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            run_injury_phase(root, 2025, "raw", write=True,
                source_csv=older, expected_source_sha256=hashlib.sha256(older).hexdigest())
            run_injury_phase(root, 2025, "canonical", write=True, players=identities())
            canonical_path = root / "data-source/nfl/injuries/2025/"
            old_canonical = {p.name: p.read_bytes()
                             for p in canonical_path.iterdir() if p.is_file()}
            run_injury_phase(root, 2025, "raw", write=True,
                source_csv=newer, expected_source_sha256=hashlib.sha256(newer).hexdigest())
            delta = run_injury_phase(root, 2025, "canonical", players=identities())
            self.assertEqual(["data-source/nfl/injuries/2025/07.json"],
                             delta["ObsoleteRequiresReview"])
            with self.assertRaisesRegex(ValueError, "manual review required"):
                run_injury_phase(root, 2025, "canonical", players=identities(), write=True)
            self.assertEqual(old_canonical, {p.name: p.read_bytes()
                           for p in canonical_path.iterdir() if p.is_file()})


    def test_raw_phase_verifies_official_release_and_preserves_asset_provenance(self):
        from nfl_injuries_phase import run_injury_phase
        import hashlib
        import json
        import tempfile
        raw = asset(2025, [report(2025)])
        sha = hashlib.sha256(raw).hexdigest()
        release = {"assets": [{
            "name": "injuries_2025.csv", "id": 8877,
            "updated_at": "2026-11-14T07:07:00Z",
            "size": len(raw), "digest": "sha256:" + sha,
            "browser_download_url":
                "https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_2025.csv"
        }]}
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            result = run_injury_phase(root, 2025, "raw", source_csv=raw,
                                      release_json=release, write=True)
            self.assertTrue(result["Written"])
            meta = json.loads((root /
                "data-source/providers/nflverse/injuries/metadata-2025.json"
            ).read_text(encoding="utf-8"))
            self.assertEqual("matched-provided-release-digest", meta["AssetDigestVerification"])
            self.assertEqual(8877, meta["ReleaseAssetId"])
            failed = copy.deepcopy(release)
            failed["assets"][0]["digest"] = "sha256:" + ("f" * 64)
            before = {str(p.relative_to(root)): p.read_bytes()
                for p in root.rglob("*") if p.is_file()}
            with self.assertRaisesRegex(ValueError, "differs from release asset"):
                run_injury_phase(root, 2025, "raw", source_csv=raw,
                                 release_json=failed, write=True)
            after = {str(p.relative_to(root)): p.read_bytes()
                for p in root.rglob("*") if p.is_file()}
            self.assertEqual(before, after)

    def test_raw_phase_requires_digest_for_live_release_without_hash(self):
        from nfl_injuries_phase import run_injury_phase
        import tempfile
        raw = asset(2024, [report(2024)])
        release = {"assets": [{
            "name": "injuries_2024.csv", "id": 8877,
            "updated_at": "2025-02-14T07:07:00Z",
            "size": len(raw), "digest": None,
            "browser_download_url":
                "https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_2024.csv"
        }]}
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with self.assertRaisesRegex(ValueError, "official or independently verified digest"):
                run_injury_phase(root, 2024, "raw", source_csv=raw,
                                 release_json=release, write=True)
            self.assertEqual([], list(root.rglob("*")))


    def test_canonical_manifest_detects_same_row_count_changed_week_bytes(self):
        from nfl_injuries_phase import run_injury_phase
        import hashlib
        import json
        import tempfile
        raw = asset(2025, [report(2025)])
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            run_injury_phase(root, 2025, "raw", write=True,
                source_csv=raw, expected_source_sha256=hashlib.sha256(raw).hexdigest())
            run_injury_phase(root, 2025, "canonical", write=True,
                players=identities())
            manifest = json.loads((root / "data-source/nfl/injuries/2025/manifest.json"
                ).read_text(encoding="utf-8"))
            proof = manifest["ObservedWeekArtifacts"][0]
            week_file = root / proof["Path"]
            self.assertEqual(proof["Sha256"],
                hashlib.sha256(week_file.read_bytes()).hexdigest())
            partition = json.loads(week_file.read_text(encoding="utf-8"))
            partition["Observations"][0]["GameLinkState"] = "linked"
            week_file.write_text(json.dumps(partition, sort_keys=True, indent=2) + "\n",
                                 encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "bytes differ from published manifest"):
                run_injury_phase(root, 2025, "derived", write=True)
            self.assertFalse((root / "data-derived/nfl-injuries/2025.json").exists())


    def test_production_raw_fetch_is_digest_gated_and_reuses_cached_csv(self):
        from nfl_injuries_refresh import refresh_injury_raw
        import hashlib
        import tempfile
        from pathlib import Path
        source = asset(2025, [report(2025)])
        digest = hashlib.sha256(source).hexdigest()
        release = {"assets": [{
            "name": "injuries_2025.csv", "id": 172,
            "updated_at": "2026-11-14T07:10:00Z", "size": len(source),
            "digest": "sha256:" + digest,
            "browser_download_url":
                "https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_2025.csv",
        }]}
        downloaded = []
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            params = dict(repo_root=root, season=2025, write=True,
                          fetch_release=lambda: release)
            first = refresh_injury_raw(**params, fetch_asset=lambda url: (downloaded.append(url), source)[1])
            self.assertTrue(first["Written"])
            self.assertTrue(first["Downloaded"])
            self.assertEqual(2, len(first["New"]))
            second = refresh_injury_raw(**params, fetch_asset=lambda url: (
                _ for _ in ()).throw(AssertionError("unchanged source cannot redownload")))
            self.assertEqual("no-op", second["Status"])
            self.assertFalse(second["Downloaded"])
            self.assertFalse(second["Written"])
            self.assertEqual(1, len(downloaded))

    def test_reuploaded_identical_release_is_true_raw_noop_with_original_provenance(self):
        from nfl_injuries_refresh import refresh_injury_raw
        from nfl_injuries_phase import run_injury_phase
        import hashlib
        import json
        import tempfile
        original = asset(2025, [report(2025)])
        sha = hashlib.sha256(original).hexdigest()
        official = {"assets": [{
            "name": "injuries_2025.csv", "id": 101,
            "updated_at": "2026-11-15T07:00:00Z", "size": len(original),
            "digest": "sha256:" + sha,
            "browser_download_url":
                "https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_2025.csv",
        }]}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = refresh_injury_raw(
                repo_root=root, season=2025, write=True,
                fetch_release=lambda: official, fetch_asset=lambda _: original,
            )
            self.assertEqual("staged-local-worktree", first["Status"])
            before = {str(p.relative_to(root)): p.read_bytes()
                      for p in root.rglob("*") if p.is_file()}
            revised = copy.deepcopy(official)
            revised["assets"][0]["id"] = 202
            revised["assets"][0]["updated_at"] = "2026-11-16T07:00:00Z"
            def cannot_download(_):
                raise AssertionError("Identical official digest must reuse persisted CSV")
            second = refresh_injury_raw(
                repo_root=root, season=2025, write=True,
                fetch_release=lambda: revised, fetch_asset=cannot_download,
            )
            self.assertEqual("no-op", second["Status"])
            self.assertEqual("no-op", second["ReleaseDecision"])
            self.assertFalse(second["Downloaded"])
            self.assertFalse(second["Written"])
            self.assertEqual([], second["Changed"])
            self.assertEqual([], second["New"])
            # The explicit raw phase must make the same decision as the producer.
            direct = run_injury_phase(
                root, 2025, "raw", source_csv=original, release_json=revised, write=True,
            )
            self.assertEqual("no-op", direct["Status"])
            self.assertFalse(direct["Written"])
            self.assertEqual(before, {str(p.relative_to(root)): p.read_bytes()
                                      for p in root.rglob("*") if p.is_file()})
            metadata = json.loads((root /
                "data-source/providers/nflverse/injuries/metadata-2025.json"
            ).read_text(encoding="utf-8"))
            self.assertEqual(101, metadata["ReleaseAssetId"])
            self.assertEqual("2026-11-15T07:00:00Z", metadata["ReleaseAssetUpdatedAt"])
            self.assertEqual(sha, metadata["AssetSha256"])

    def test_production_raw_fetch_preserves_previous_good_on_corrupt_release(self):
        from nfl_injuries_refresh import refresh_injury_raw
        import tempfile
        import hashlib
        from pathlib import Path
        source = asset(2025, [report(2025)])
        release = {"assets": [{
            "name": "injuries_2025.csv", "id": 17,
            "updated_at": "2026-11-14T07:10:00Z", "size": len(source),
            "digest": "sha256:" + hashlib.sha256(source).hexdigest(),
            "browser_download_url":
                "https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_2025.csv",
        }]}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            options = dict(repo_root=root, season=2025, write=True)
            refresh_injury_raw(**options, fetch_release=lambda: release,
                               fetch_asset=lambda url: source)
            previous = {str(p.relative_to(root)):p.read_bytes()
                        for p in root.rglob("*") if p.is_file()}
            changed = copy.deepcopy(release)
            changed["assets"][0]["digest"] = "sha256:" + "f"*64
            with self.assertRaisesRegex(ValueError, "SHA-256 and size verification"):
                refresh_injury_raw(**options, fetch_release=lambda: changed,
                                   fetch_asset=lambda url: source)
            self.assertEqual(previous, {str(p.relative_to(root)):p.read_bytes()
                             for p in root.rglob("*") if p.is_file()})

    def test_production_raw_fetch_rejects_missing_digest_and_unavailable_release(self):
        from nfl_injuries_refresh import refresh_injury_raw
        import tempfile
        from pathlib import Path
        raw = asset(2025, [report(2025)])
        release = {"assets": [{
            "name": "injuries_2025.csv", "id": 17,
            "updated_at": "2026-11-14T07:10:00Z", "size": len(raw),
            "digest": None,
            "browser_download_url":
                "https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_2025.csv",
        }]}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaisesRegex(ValueError, "lacks verified SHA-256"):
                refresh_injury_raw(repo_root=root, season=2025, write=True,
                                   fetch_release=lambda: release)
            with self.assertRaisesRegex(ValueError, "retry later"):
                refresh_injury_raw(repo_root=root, season=2025, write=True,
                                   fetch_release=lambda: {"assets": []})
            self.assertEqual([], list(root.rglob("*")))

    def test_injury_source_registry_is_explicit_and_excluded_from_full_sync(self):
        import json
        from pathlib import Path
        root = Path(__file__).resolve().parents[2]
        registry = json.loads((root / "data-source/registry.json").read_text(encoding="utf-8"))
        matches = [x for x in registry["datasets"] if x.get("id") == "nflverse.injuries"]
        self.assertEqual(1, len(matches))
        self.assertFalse(matches[0]["materialize"])
        self.assertEqual("season-partitioned", matches[0]["sourceMode"])
        source_cli = (root / "tools/nfl_source_data.py").read_text(encoding="utf-8")
        self.assertIn("if dataset.id != INJURIES_DATASET_ID", source_cli)
        self.assertIn("requested != {INJURIES_DATASET_ID}", source_cli)

    def test_injury_scheduler_isolated_delegation_and_publication_contract(self):
        import json
        import yaml
        root = Path(__file__).resolve().parents[2]
        config = json.loads((root / ".github/workflow-schedules.json").read_text(encoding="utf-8"))
        target, = [x for x in config["targets"] if x["id"] == "nfl-injuries"]
        self.assertEqual("30 9 * 9-12,1-2 *", target["cron"][0])
        self.assertEqual(["repository_dispatch"], target["satisfyingEvents"])
        self.assertEqual("sync-nfl-injuries.yml", target["workflow"])
        wrapper = yaml.safe_load((root / target["path"]).read_text(encoding="utf-8"))
        workflow = wrapper["jobs"]["source_and_derived"]
        self.assertEqual("./.github/workflows/sync-nfl-source-data.yml", workflow["uses"])
        self.assertEqual("injuries", workflow["with"]["materialization_scope"])
        self.assertEqual("nflverse.injuries", workflow["with"]["dataset"])
        source = (root / ".github/workflows/sync-nfl-source-data.yml").read_text(encoding="utf-8")
        self.assertIn("nfl_injuries_derived:", source)
        self.assertIn("--path data-derived/nfl-injuries", source)
        self.assertIn("elif scope == \"injuries\"", source)
        self.assertIn('data-source/nfl/injuries/"$injury_year"/*', source)
        self.assertIn("assert_scoped_raw_write_set", source)
        self.assertIn('materialize_args+=(--scope injuries --season "$injury_year")', source)

    def test_injury_workflow_resolves_season_with_importable_package(self):
        import os
        import subprocess
        import yaml
        from nfl_source_data_lib.common import current_source_season

        root = Path(__file__).resolve().parents[2]
        workflow = yaml.safe_load(
            (root / ".github/workflows/sync-nfl-source-data.yml").read_text(encoding="utf-8")
        )
        sync_step = next(
            step for step in workflow["jobs"]["sync"]["steps"]
            if step.get("name") == "Sync, validate and publish NFL source data"
        )
        derived_step = next(
            step for step in workflow["jobs"]["nfl_injuries_derived"]["steps"]
            if step.get("name") == "Rebuild and publish isolated Injury Derived product"
        )
        season_command = (
            "PYTHONPATH=tools python3 -c "
            "'from nfl_source_data_lib.common import current_source_season; "
            "from pathlib import Path; print(current_source_season(Path.cwd()))'"
        )
        self.assertIn('injury_year="$(' + season_command + ')"', sync_step["run"])
        self.assertIn('season="$(' + season_command + ')"', derived_step["run"])

        # Run the actual inline shell command with no inherited PYTHONPATH:
        # CI must not pass only because the unittest runner adds tools/ to sys.path.
        result = subprocess.run(
            ["bash", "-c", season_command],
            cwd=root,
            env={**os.environ, "PYTHONPATH": ""},
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(str(current_source_season(root)), result.stdout.strip())


    def test_release_api_uses_actions_token_for_metadata_only(self):
        import os
        from unittest.mock import patch
        import urllib.request
        from nfl_injuries_refresh import release_api, source_asset, _read_https

        requests = []

        class StubOpener:
            def open(self, request, timeout):
                requests.append(request)
                return io.BytesIO(b'{"assets": []}')

        with patch.dict(os.environ, {"NFLVERSE_RELEASE_API_TOKEN": "test-actions-token"}):
            with patch("urllib.request.build_opener", return_value=StubOpener()) as factory:
                self.assertEqual({"assets": []}, release_api())
                factory.assert_called_once()
        metadata_headers = {k.lower(): v for k, v in requests[0].header_items()}
        self.assertEqual("Bearer test-actions-token", metadata_headers["authorization"])
        self.assertEqual("2022-11-28", metadata_headers["x-github-api-version"])
        self.assertEqual(
            "https://api.github.com/repos/nflverse/nflverse-data/releases/tags/injuries",
            requests[0].full_url,
        )

        asset_url = (
            "https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_2026.csv"
        )
        with patch.dict(os.environ, {"NFLVERSE_RELEASE_API_TOKEN": "test-actions-token"}):
            with patch("urllib.request.urlopen", return_value=io.BytesIO(b"original-csv")) as opened:
                self.assertEqual(b"original-csv", source_asset(asset_url))
                requested_asset = opened.call_args.args[0]
        self.assertNotIn(
            "authorization", {key.lower() for key, value in requested_asset.header_items()}
        )
        with self.assertRaisesRegex(ValueError, "official GitHub API"):
            _read_https(asset_url, 100, accept="text/csv", token="test-actions-token")

    def test_release_api_unauthenticated_fallback_and_redirect_guard(self):
        import os
        from unittest.mock import patch
        from nfl_injuries_refresh import release_api, _RejectAuthenticatedRedirects

        with patch.dict(os.environ, {"NFLVERSE_RELEASE_API_TOKEN": ""}):
            with patch("urllib.request.urlopen", return_value=io.BytesIO(b'{"assets": []}')) as opened:
                self.assertEqual({"assets": []}, release_api())
                self.assertNotIn(
                    "authorization",
                    {key.lower() for key, value in opened.call_args.args[0].header_items()},
                )
        with self.assertRaisesRegex(ValueError, "may not redirect"):
            _RejectAuthenticatedRedirects().redirect_request(
                None, None, 302, "redirect", {}, "https://untrusted.example/"
            )

    def test_injury_release_workflow_uses_existing_scoped_github_token(self):
        import yaml

        root = Path(__file__).resolve().parents[2]
        workflow = yaml.safe_load(
            (root / ".github/workflows/sync-nfl-source-data.yml").read_text(encoding="utf-8")
        )
        step, = [
            s for s in workflow["jobs"]["sync"]["steps"]
            if s.get("name") == "Sync, validate and publish NFL source data"
        ]
        self.assertEqual(
            "${{ inputs.materialization_scope == 'injuries' && github.token || '' }}",
            step["env"]["NFLVERSE_RELEASE_API_TOKEN"],
        )
        self.assertNotIn("NFLVERSE_RELEASE_API_TOKEN", workflow["jobs"]["sync"].get("env", {}))

    def test_future_season_can_use_2025_plus_header_without_silent_format_fallback(self):
        from nfl_source_data_lib.injury_reports import parse_injury_report_csv
        from nfl_source_data_lib.injury_product_plan import build_injury_artifacts
        from nfl_injuries_phase import run_injury_phase
        import tempfile
        import hashlib
        source = asset(2027, [report(2027)])
        parsed = parse_injury_report_csv(source, season=2027)
        self.assertEqual(2027, parsed["Season"])
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            run_injury_phase(root, 2027, "raw", write=True, source_csv=source,
                expected_source_sha256=hashlib.sha256(source).hexdigest())
            run_injury_phase(root, 2027, "canonical", write=True,
                players=identities())
            derived = run_injury_phase(root, 2027, "derived", write=True)
            self.assertTrue(derived["Written"])
            import json
            product = json.loads(
                (root / "data-derived/nfl-injuries/2027.json").read_text(encoding="utf-8")
            )
            self.assertEqual(2027, product["Season"])
            self.assertEqual("nfl-injuries-v1", product["ProductVersion"])

    def test_imported_historical_injuries_are_frozen_without_approved_repair(self):
        from nfl_injuries_refresh import refresh_injury_raw
        import tempfile
        import hashlib
        from pathlib import Path
        raw = asset(2025, [report(2025)])
        release = {"assets": [{
            "name": "injuries_2025.csv", "id": 32,
            "updated_at": "2026-11-14T07:10:00Z", "size": len(raw),
            "digest": "sha256:" + hashlib.sha256(raw).hexdigest(),
            "browser_download_url":
                "https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_2025.csv",
        }]}
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            args = dict(repo_root=root, season=2025, current_season=2026,
                        write=True)
            fresh = refresh_injury_raw(**args, fetch_release=lambda: release,
                                      fetch_asset=lambda url: raw)
            self.assertTrue(fresh["Written"])
            later = copy.deepcopy(release)
            later["assets"][0]["id"] = 33
            later["assets"][0]["digest"] = "sha256:" + ("f" * 64)
            before = {str(p.relative_to(root)):p.read_bytes() for p in root.rglob("*") if p.is_file()}
            with self.assertRaisesRegex(ValueError, "Historical Injury Source revision is frozen"):
                refresh_injury_raw(**args, fetch_release=lambda: later,
                                   fetch_asset=lambda url: (_ for _ in ()).throw(
                                       AssertionError("Must never download frozen revisions")))
            self.assertEqual(before, {str(p.relative_to(root)):p.read_bytes()
                                     for p in root.rglob("*") if p.is_file()})


if __name__ == "__main__":
    unittest.main()
