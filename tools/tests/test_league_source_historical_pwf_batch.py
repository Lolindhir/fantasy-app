"""Issue #471 regression tests for the source-owned historical PWF batch."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from historical_pwf_batch import discover_scored_weeks, materialize_historical  # noqa: E402

REPO_ROOT = TOOLS.parent


class HistoricalPWFBatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        league_dir = self.root / "data-source/leagues/nfl-reise"
        season_dir = league_dir / "seasons/2026"
        season_dir.mkdir(parents=True)
        (league_dir / "manifest.json").write_text(json.dumps({
            "Seasons": [{"Season": 2026}],
        }), encoding="utf-8")
        (season_dir / "league.json").write_text(json.dumps({
            "WeekStructure": {
                "Season": 2026, "StartWeek": 1,
                "ExpectedLastLeagueWeek": 17, "LastScoredLeg": 2,
            }
        }), encoding="utf-8")
        self.output = self.root / "isolated-derived"
        self.patches = [
            patch("historical_pwf_batch.list_league_ids", return_value=["nfl-reise"]),
            patch("historical_pwf_batch.load_league_metadata", return_value={}),
            patch("historical_pwf_batch.validate_against_manifest"),
            patch("historical_pwf_batch._week_finality", return_value=(True, {"game1"})),
            patch("historical_pwf_batch.build_player_week_fantasy_dataset",
                  side_effect=self.build_payload),
        ]
        self.mocks = [p.start() for p in self.patches]
        for p in self.patches:
            self.addCleanup(p.stop)

    @staticmethod
    def build_payload(root, *, league_id, season, week):
        return {
            "CanonicalLeagueID": league_id,
            "Season": season, "Week": week,
            "Records": [{"CanonicalPlayerID": "abc",
                         "Actual": {"State": "final", "Points": 4.5}}],
            "Materialization": {
                "ActualScoringEvidenceFinalized": True,
                "TargetRosterProvisional": False,
                "ActualStateCounts": {"final": 1},
            },
        }

    def test_source_discovery_ignores_derived_inventory(self):
        self.assertEqual(discover_scored_weeks(self.root),
                         [("nfl-reise", 2026, 1), ("nfl-reise", 2026, 2)])
        self.assertEqual(discover_scored_weeks(self.root, weeks=[2]),
                         [("nfl-reise", 2026, 2)])
        self.assertFalse(self.output.exists())

    def test_check_does_not_write_and_is_deterministic(self):
        first = materialize_historical(self.root, out_root=self.output)
        second = materialize_historical(self.root, out_root=self.output)
        self.assertEqual((first["TargetCount"], first["ReadyCount"], first["BlockedCount"]),
                         (2, 2, 0))
        self.assertEqual(first["WouldChangeCount"], 2)
        self.assertEqual(first, second)
        self.assertFalse(self.output.exists())

    def test_write_then_rerun_has_zero_changes(self):
        first = materialize_historical(self.root, out_root=self.output, write=True)
        self.assertEqual(first["ChangedCount"], 2)
        self.assertTrue((self.output / "player-week-fantasy/nfl-reise/2026/01.json").is_file())
        second = materialize_historical(self.root, out_root=self.output, write=True)
        self.assertEqual(second["ChangedCount"], 0)
        self.assertEqual(second["BlockedCount"], 0)

    def test_blocked_later_week_aborts_all_writes(self):
        self.mocks[3].side_effect = lambda root, *, season, week: (
            (True, {"game1"}) if week == 1 else (False, set())
        )
        report = materialize_historical(self.root, out_root=self.output, write=True)
        self.assertEqual((report["ReadyCount"], report["BlockedCount"]), (1, 1))
        self.assertTrue(report["WriteAborted"])
        self.assertFalse(self.output.exists())

    def test_nonfinal_scoring_evidence_fails_closed(self):
        def unavailable(*args, **kwargs):
            payload = self.build_payload(*args, **kwargs)
            payload["Materialization"]["ActualScoringEvidenceFinalized"] = False
            return payload
        self.mocks[4].side_effect = unavailable
        result = materialize_historical(self.root, out_root=self.output, write=True)
        self.assertEqual(result["BlockedCount"], 2)
        self.assertFalse(self.output.exists())

    def test_invalid_or_out_of_range_selection_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "positive"):
            discover_scored_weeks(self.root, weeks=[0])
        with self.assertRaisesRegex(ValueError, "Unknown requested seasons"):
            discover_scored_weeks(self.root, seasons=[2025])
        with self.assertRaisesRegex(ValueError, "No scored league weeks"):
            discover_scored_weeks(self.root, weeks=[6])


@unittest.skipUnless((REPO_ROOT / "data-source/leagues/nfl-reise/manifest.json").is_file(),
                     "Canonical league sources are required for historical PWF smoke tests")
class RealHistoricalPWFBatchTests(unittest.TestCase):
    def test_real_missing_2026_weeks_1_and_2_are_reconstructible(self):
        with tempfile.TemporaryDirectory() as output:
            report = materialize_historical(
                REPO_ROOT, league_id="nfl-reise", seasons=[2026],
                weeks=[1, 2], out_root=Path(output),
            )
            self.assertEqual((report["TargetCount"], report["ReadyCount"],
                              report["BlockedCount"]), (2, 2, 0), report["Weeks"])
            self.assertEqual(report["WouldChangeCount"], 2)
            self.assertFalse(list(Path(output).rglob("*.json")))

    def test_real_2024_and_2025_sample_weeks_are_reconstructible(self):
        with tempfile.TemporaryDirectory() as output:
            report = materialize_historical(
                REPO_ROOT, league_id="nfl-reise", seasons=[2024, 2025],
                weeks=[8], out_root=Path(output),
            )
            self.assertEqual((report["TargetCount"], report["ReadyCount"],
                              report["BlockedCount"]), (2, 2, 0), report["Weeks"])


    def test_every_canonically_scored_historical_week_preflights_without_writes(self):
        """Real source-only inventory: a missing or stale historical partition must not hide."""
        expected = discover_scored_weeks(REPO_ROOT, league_id="nfl-reise")
        self.assertGreaterEqual(len(expected), 39)
        with tempfile.TemporaryDirectory() as output:
            report = materialize_historical(
                REPO_ROOT, league_id="nfl-reise", out_root=Path(output),
            )
            blocked = [week for week in report["Weeks"] if week["Status"] == "blocked"]
            self.assertEqual(report["TargetCount"], len(expected))
            self.assertEqual(report["BlockedCount"], 0, blocked)
            self.assertEqual(report["ReadyCount"], len(expected))
            self.assertFalse(list(Path(output).rglob("*.json")))



if __name__ == "__main__":
    unittest.main()
