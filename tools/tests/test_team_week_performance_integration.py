"""Real-source integration gate for #355 (requires pwsh and canonical repo data).

This test runs only on an environment with the production PowerShell bridge.
It must never publish derived data, even for a final historical week.
"""
from __future__ import annotations

import base64
import hashlib
import json
import shutil
import tempfile
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from ci_tier import deep_only  # noqa: E402
from team_week_performance_materialize import materialize, materialize_all_finalized, verify_pwf_actual_parity
from team_week_performance import build_team_week_performance, save_team_week_performance, output_path  # noqa: E402
from team_week_performance_sources import (  # noqa: E402
    load_verified_week_inputs,
    resolve_slots_from_existing_rules,
)

REPO_ROOT = TOOLS.parent


@deep_only("real-source TeamWeekPerformance replay through PowerShell")
@unittest.skipUnless(shutil.which("pwsh"), "PowerShell CLI is required for real-source integration")
class TeamWeekPerformanceIntegrationTests(unittest.TestCase):
    def test_real_2024_slot_bridge_preserves_special_flex(self) -> None:
        league_path = REPO_ROOT / "data-source/leagues/nfl-reise/seasons/2024/league.json"
        slots = resolve_slots_from_existing_rules(
            REPO_ROOT, league_path,
            {"qb": "QB", "rb": "RB", "wr": "WR", "te": "TE", "k": "K"},
        )
        self.assertEqual(len(slots), 12)
        by_name = {slot.slot_id: slot.eligible_positions for slot in slots}
        self.assertEqual(by_name["WRRB_FLEX-1"], frozenset({"RB", "WR"}))
        self.assertEqual(by_name["REC_FLEX-1"], frozenset({"WR", "TE"}))
        self.assertEqual(by_name["FLEX-1"], frozenset({"RB", "WR", "TE"}))
        self.assertEqual(by_name["K-1"], frozenset({"K"}))

    def test_real_final_weeks_match_independent_shadow_audit(self) -> None:
        # Independent full-roster, position-constrained DP audit values.
        cases = [
            (2024, 14, 246.58, 90.9201),
            (2025, 8, 250.38, 90.1538),
            (2026, 3, 258.38, 92.7319),
            (2026, 4, 304.34, 85.5761),
            (2026, 5, 264.50, 93.8913),
        ]
        for season, week, best_potential, coach_percent in cases:
            with self.subTest(season=season, week=week):
                inputs = load_verified_week_inputs(REPO_ROOT, "nfl-reise", season, week)
                result = build_team_week_performance(**inputs)
                self.assertEqual(len(result["Teams"]), inputs["expected_team_count"])
                self.assertEqual(max(t["PotentialPoints"] for t in result["Teams"]), best_potential)
                self.assertEqual(max(t["EfficiencyPercent"] for t in result["Teams"]), coach_percent)
                for team in result["Teams"]:
                    self.assertLessEqual(team["ActualStarterPoints"], team["PotentialPoints"])
                    self.assertAlmostEqual(
                        team["ActualStarterPoints"], team["OfficialMatchupPoints"], places=2
                    )
                self.assertTrue(result["Awards"]["BestManagerRosterIDs"])
                self.assertTrue(result["Awards"]["BestCoachRosterIDs"])


    def test_real_week5_checked_materialization_is_readonly_and_reproducible(self) -> None:
        inputs = load_verified_week_inputs(REPO_ROOT, "nfl-reise", 2026, 5)
        model = build_team_week_performance(**inputs)
        parity = verify_pwf_actual_parity(
            REPO_ROOT, model, inputs["matchup_rows"], require_pwf=True
        )
        self.assertEqual(parity, {
            "State": "verified", "Compared": 191, "MissingZeroPoints": 13,
        })
        check = materialize(
            REPO_ROOT, "nfl-reise", 2026, 5, write=False, require_pwf=True
        )
        self.assertFalse(check["Written"])
        self.assertFalse(check["Changed"])
        self.assertEqual(check["TeamCount"], 6)
        self.assertEqual(check["PlayerWeekFantasyParity"], parity)
        with tempfile.TemporaryDirectory() as temp:
            scratch = Path(temp)
            self.assertTrue(save_team_week_performance(scratch, model))
            self.assertFalse(save_team_week_performance(scratch, model))
            data = output_path(scratch, model).read_bytes()
            self.assertEqual(json.loads(data), model)
            sha = hashlib.sha1(
                b"blob " + str(len(data)).encode("ascii") + b"\0" + data
            ).hexdigest()
            encoded = base64.b64encode(data).decode("ascii")
            print("TWP_WEEK5_META=" + json.dumps({
                "blobSha": sha, "bytes": len(data), "wireChars": len(encoded),
                "teams": len(model["Teams"]), "parity": parity,
                "manager": model["Awards"]["BestManagerRosterIDs"],
                "coach": model["Awards"]["BestCoachRosterIDs"],
            }, sort_keys=True), flush=True)
            for i in range(0, len(encoded), 3000):
                print("TWP_WEEK5_PART=" + encoded[i:i+3000], flush=True)


    def test_real_2026_week3_pwf_backfill_unblocks_awards_without_writing(self) -> None:
        """#697 W03 final Actual backfill enables strict #355 source/parity gate."""
        check = materialize(
            REPO_ROOT, "nfl-reise", 2026, 3, write=False, require_pwf=True
        )
        self.assertEqual(check["TeamCount"], 6)
        self.assertEqual(check["PlayerWeekFantasyParity"], {
            "State": "verified", "Compared": 202, "MissingZeroPoints": 0,
        })
        self.assertFalse(check["Written"])
        self.assertFalse(check["Changed"])
        published = REPO_ROOT / check["Path"]
        self.assertTrue(published.is_file(), "Verified Week 3 snapshot must be persisted in this Draft")
        inputs = load_verified_week_inputs(REPO_ROOT, "nfl-reise", 2026, 3)
        model = build_team_week_performance(**inputs)
        self.assertEqual(json.loads(published.read_text(encoding="utf-8")), model)
        self.assertEqual(max(x["PotentialPoints"] for x in model["Teams"]), 258.38)
        self.assertEqual(max(x["EfficiencyPercent"] for x in model["Teams"]), 92.7319)
        self.assertTrue(model["Awards"]["BestManagerRosterIDs"])
        self.assertTrue(model["Awards"]["BestCoachRosterIDs"])
        print("TWP_W03_PARITY_AUDIT=" + json.dumps({
            "PWF": check["PlayerWeekFantasyParity"],
            "Teams": check["TeamCount"],
            "BestPotential": max(x["PotentialPoints"] for x in model["Teams"]),
            "BestEfficiency": max(x["EfficiencyPercent"] for x in model["Teams"]),
            "Awards": model["Awards"],
            "WroteOutput": check["Written"],
        }, sort_keys=True), flush=True)

    def test_real_week3_verified_materializer_matches_persisted_snapshot(self) -> None:
        """The persisted W03 bytes match production materialization and reruns are no-ops."""
        result = materialize(REPO_ROOT, "nfl-reise", 2026, 3, write=False, require_pwf=True)
        self.assertEqual(result["PlayerWeekFantasyParity"],
                         {"State": "verified", "Compared": 202, "MissingZeroPoints": 0})
        inputs = load_verified_week_inputs(REPO_ROOT, "nfl-reise", 2026, 3)
        model = build_team_week_performance(**inputs)
        self.assertEqual(result["BestManagerRosterIDs"], model["Awards"]["BestManagerRosterIDs"])
        self.assertEqual(result["BestCoachRosterIDs"], model["Awards"]["BestCoachRosterIDs"])
        with tempfile.TemporaryDirectory() as temp:
            scratch = Path(temp)
            self.assertTrue(save_team_week_performance(scratch, model))
            self.assertFalse(save_team_week_performance(scratch, model))
            data = output_path(scratch, model).read_bytes()
            self.assertEqual(json.loads(data), model)
            digest = hashlib.sha1(
                b"blob " + str(len(data)).encode("ascii") + b"\0" + data
            ).hexdigest()
            published = output_path(REPO_ROOT, model)
            self.assertTrue(published.is_file())
            self.assertEqual(published.read_bytes(), data)
            self.assertEqual(
                hashlib.sha1(b"blob " + str(len(published.read_bytes())).encode("ascii")
                             + b"\0" + published.read_bytes()).hexdigest(), digest
            )
            print("TWP_WEEK3_PERSISTED_PARITY=" + json.dumps({
                "blobSha": digest, "bytes": len(data), "teams": len(model["Teams"]),
                "parity": result["PlayerWeekFantasyParity"],
                "manager": model["Awards"]["BestManagerRosterIDs"],
                "coach": model["Awards"]["BestCoachRosterIDs"],
            }, sort_keys=True), flush=True)


    def test_real_all_finalized_weeks_readonly_on_published_pwf(self) -> None:
        """Entire scored history passes when refreshed W03 PWF is present."""
        report = materialize_all_finalized(
            REPO_ROOT, league_id="nfl-reise", write=False
        )
        self.assertGreaterEqual(report["TargetCount"], 39)
        self.assertEqual(report["ReadyCount"], report["TargetCount"],
                         [week for week in report["Weeks"] if week["Status"] != "ready"])
        self.assertEqual(report["BlockedCount"], 0, report["Weeks"])
        self.assertFalse(report["WriteRequested"])
        self.assertFalse(report["WriteAborted"])
        self.assertEqual(report["ChangedCount"], 0)
        self.assertTrue(all(x["Status"] == "ready" for x in report["Weeks"]))
        week3 = next(x for x in report["Weeks"]
                     if x["Season"] == 2026 and x["Week"] == 3)
        self.assertEqual(week3["PlayerWeekFantasyParity"], {
            "State": "verified", "Compared": 202, "MissingZeroPoints": 0,
        })
        print("TWP_FULL_READONLY_AUDIT=" + json.dumps({
            "Targets": report["TargetCount"], "Ready": report["ReadyCount"],
            "Blocked": report["BlockedCount"], "Written": report["ChangedCount"],
            "Week3Parity": week3["PlayerWeekFantasyParity"],
        }, sort_keys=True), flush=True)


    def test_clean_derived_root_rebuilds_all_weeks_and_second_run_is_noop(self) -> None:
        """Use a truly empty isolated derived root while reading real canonical inputs."""
        with tempfile.TemporaryDirectory(prefix=".twp-recovery-", dir=REPO_ROOT) as temp:
            derived_root = Path(temp).relative_to(REPO_ROOT).as_posix()
            with patch("team_week_performance_materialize.DATA_DERIVED_ROOT", derived_root), \
                 patch("team_week_performance.DATA_DERIVED_ROOT", derived_root), \
                 patch("player_scoring_reconciliation.DATA_DERIVED_ROOT", derived_root):
                first = materialize_all_finalized(REPO_ROOT, league_id="nfl-reise", write=True)
                count = first["TargetCount"]
                self.assertGreaterEqual(count, 39)
                self.assertEqual((first["ReadyCount"], first["BlockedCount"],
                                  first["ChangedCount"]), (count, 0, count))
                self.assertTrue(all(w["PlayerWeekFantasyParity"]["State"] == "not-available"
                                    for w in first["Weeks"]))
                for w in first["Weeks"]:
                    self.assertEqual(w["TeamCount"], 6)
                    self.assertTrue((REPO_ROOT / w["Path"]).is_file())
                for week in (3, 4, 5):
                    generated = REPO_ROOT / derived_root / "team-week-performance/nfl-reise/2026" / f"{week:02d}.json"
                    published = REPO_ROOT / "data-derived/team-week-performance/nfl-reise/2026" / f"{week:02d}.json"
                    self.assertEqual(generated.read_bytes(), published.read_bytes())
                second = materialize_all_finalized(REPO_ROOT, league_id="nfl-reise", write=True)
                self.assertEqual((second["ReadyCount"], second["BlockedCount"],
                                  second["ChangedCount"]), (count, 0, 0))

class PersistedTeamWeekPerformanceGuardTests(unittest.TestCase):
    """Fast counterpart of the real-source replay: persisted snapshots keep their identity."""

    def test_persisted_snapshots_match_path_identity_and_are_complete(self) -> None:
        files = sorted((REPO_ROOT / "data-derived/team-week-performance").glob("*/*/*.json"))
        self.assertTrue(files, "no persisted TeamWeekPerformance snapshot found")
        for path in files:
            data = json.loads(path.read_text(encoding="utf-8"))
            league, season, week = path.parts[-3], int(path.parts[-2]), int(path.stem)
            self.assertEqual((data["CanonicalLeagueID"], data["Season"], data["Week"]), (league, season, week), path)
            self.assertTrue(data["Teams"], path)
            self.assertTrue(data["FinalityEvidence"], path)
            self.assertTrue(str(data["LineupDefinitionHash"]).startswith("sha256:"), path)


if __name__ == "__main__":
    unittest.main()
