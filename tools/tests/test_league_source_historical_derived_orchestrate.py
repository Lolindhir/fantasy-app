"""Bounded isolated historical Shared-Derived audit regression (#471)."""
from __future__ import annotations

import io
import json
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import historical_derived_orchestrate as pipeline
from tools.ci_tier import deep_only


class HistoricalDerivedSelectionTests(unittest.TestCase):
    targets = [("nfl-reise", 2024, 1), ("nfl-reise", 2024, 2),
               ("nfl-reise", 2026, 1), ("nfl-reise", 2026, 2)]

    def test_full_and_target_week(self):
        self.assertEqual(pipeline.select_targets(self.targets, mode="full"), self.targets)
        self.assertEqual(pipeline.select_targets(
            self.targets, mode="week", season=2024, week=2), [self.targets[1]])
        with self.assertRaisesRegex(ValueError, "not canonically scored"):
            pipeline.select_targets(self.targets, mode="week", season=2026, week=8)
        with self.assertRaises(ValueError):
            pipeline.select_targets(self.targets, mode="full", season=2026)

    def test_incremental_exact_week_season_and_unknown_full_fallback(self):
        self.assertEqual(pipeline.select_targets(
            self.targets, mode="incremental",
            changed_paths=["data-source/nfl/player-stats/2024/01.json"]), self.targets)
        self.assertEqual(pipeline.select_targets(
            self.targets, mode="incremental",
            changed_paths=["data-source/leagues/nfl-reise/seasons/2026/matchups/week-2.json"]),
            [self.targets[3]])
        self.assertEqual(pipeline.select_targets(
            self.targets, mode="incremental",
            changed_paths=["data-source/nfl/game-finality/2024.json"]), self.targets)
        self.assertEqual(pipeline.select_targets(
            self.targets, mode="incremental",
            changed_paths=["data-meta/nfl-reise/metadata.json"]), self.targets)
        self.assertEqual(pipeline.select_targets(
            self.targets, mode="incremental",
            changed_paths=["data-source/nfl/weekly-rosters/2030/01.json"]), [])
        with self.assertRaisesRegex(ValueError, "Invalid changed path"):
            pipeline.select_targets(self.targets, mode="incremental",
                                    changed_paths=["../data-source/nfl/foo.json"])


class HistoricalDerivedWorkflowSafetyTests(unittest.TestCase):
    def test_manual_audit_skips_every_live_writer_and_cannot_push(self):
        text = (TOOLS.parent / ".github/workflows/league-live.yml").read_text(encoding="utf-8")
        self.assertIn("historical_preflight:", text)
        self.assertIn("if: ${{ inputs.historical_preflight == true }}", text)
        self.assertIn("if: ${{ !inputs.historical_preflight }}", text)
        self.assertEqual(text.count("if: ${{ !cancelled() && !inputs.historical_preflight }}"), 2)
        self.assertIn("contents: read", text)
        self.assertIn("persist-credentials: false", text)
        self.assertIn("args=(--mode", text)
        self.assertNotIn("--league nfl-reise", text)
        self.assertIn("python3 tools/historical_derived_orchestrate.py", text)

    def test_cli_defaults_to_source_discovery_without_a_fixed_league(self):
        with patch.object(pipeline, "preflight", return_value={"Targets": []}) as audit:
            with redirect_stdout(io.StringIO()):
                self.assertEqual(pipeline.main(["--mode", "full"]), 0)
            self.assertIsNone(audit.call_args.kwargs["league_id"])
            with redirect_stdout(io.StringIO()):
                self.assertEqual(pipeline.main(
                    ["--league", "alpha", "--mode", "week", "--season", "2024", "--week", "1"]
                ), 0)
            self.assertEqual(audit.call_args.kwargs["league_id"], "alpha")


class HistoricalDerivedIsolatedTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / "data-source").mkdir()
        (self.root / "data-meta").mkdir()
        (self.root / "public/data").mkdir(parents=True)
        (self.root / "public/data/FantasyGameContext.json").write_text(
            json.dumps({"Season": "2026", "Week": 7}), encoding="utf-8",
        )
        self.targets = [("nfl-reise", 2024, 1), ("nfl-reise", 2026, 5)]
        self.calls = []
        patches = [
            patch.object(pipeline, "discover_scored_weeks", return_value=self.targets),
            patch.object(pipeline, "materialize_historical", side_effect=self.fake_pwf),
            patch.object(pipeline, "materialize_twp", side_effect=self.fake_twp),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def fake_pwf(self, stage, *, league_id, seasons, weeks, write):
        self.assertTrue(write)
        self.assertNotEqual(stage.resolve(), self.root.resolve())
        target = stage / "data-derived/player-week-fantasy" / league_id / str(seasons[0]) / f"{weeks[0]:02d}.json"
        content = '{"points": 12}\n'
        different = not target.is_file() or target.read_text() != content
        if different:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        self.calls.append(("pwf", seasons[0], weeks[0]))
        return {"TargetCount": 1, "ReadyCount": 1, "BlockedCount": 0,
                "ChangedCount": int(different), "Weeks": [{"Status": "ready"}]}

    def fake_twp(self, stage, league_id, season, week, *, write, require_pwf):
        self.assertTrue(require_pwf)
        self.assertTrue(write)
        upstream = stage / "data-derived/player-week-fantasy" / league_id / str(season) / f"{week:02d}.json"
        self.assertTrue(upstream.is_file())
        target = stage / "data-derived/team-week-performance" / league_id / str(season) / f"{week:02d}.json"
        content = '{"award": "stable"}\n'
        changed = not target.is_file() or target.read_text() != content
        if changed:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        self.calls.append(("twp", season, week))
        return {"Changed": changed, "PlayerWeekFantasyParity": {
            "State": "accepted-divergence" if season == 2024 else "verified",
            "AcceptedDivergences": 1 if season == 2024 else 0,
        }}

    def test_full_preflight_isolated_idempotent_no_production_writes(self):
        result = pipeline.preflight(self.root)
        self.assertEqual(result["TargetCount"], 2)
        self.assertEqual(result["PWFWouldChange"], 2)
        self.assertEqual(result["TWPWouldChange"], 2)
        self.assertEqual(result["AcceptedDivergences"], 1)
        self.assertTrue(result["SecondPassNoop"])
        self.assertFalse(result["Published"])
        self.assertEqual(len(self.calls), 8)
        self.assertFalse((self.root / "data-derived").exists())

    def test_live_target_is_rejected_before_any_writes(self):
        (self.root / "public/data/FantasyGameContext.json").write_text(
            json.dumps({"Season": 2026, "Week": 5}), encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "overlaps current App week"):
            pipeline.preflight(self.root)
        self.assertEqual(self.calls, [])

    def test_existing_published_awards_drift_fails_closed(self):
        old = self.root / "data-derived/team-week-performance/nfl-reise/2026/05.json"
        old.parent.mkdir(parents=True)
        old.write_text('{"award": "old"}\n', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Existing published Team Awards would change"):
            pipeline.preflight(self.root)
        self.assertEqual(old.read_text(), '{"award": "old"}\n')

    def test_incremental_target_does_not_touch_other_week(self):
        result = pipeline.preflight(
            self.root, mode="incremental",
            changed_paths=["data-source/leagues/nfl-reise/seasons/2024/matchups/week-1.json"],
        )
        self.assertEqual(result["TargetCount"], 1)
        self.assertEqual({call[1:] for call in self.calls}, {(2024, 1)})

    def test_invalid_live_context_is_fail_closed(self):
        (self.root / "public/data/FantasyGameContext.json").write_text("{}")
        with self.assertRaisesRegex(ValueError, "Invalid current App week"):
            pipeline.preflight(self.root)
        self.assertEqual(self.calls, [])

    def test_non_idempotent_second_pass_fails_closed(self):
        original = self.fake_twp
        count = 0

        def drifting(*args, **kwargs):
            nonlocal count
            count += 1
            result = original(*args, **kwargs)
            if count > len(self.targets):
                result["Changed"] = True
            return result

        with patch.object(pipeline, "materialize_twp", side_effect=drifting):
            with self.assertRaisesRegex(ValueError, "not idempotent"):
                pipeline.preflight(self.root)
        self.assertFalse((self.root / "data-derived").exists())


@deep_only("Real historical TWP rebuild belongs to Deep audit, not Fast PR CI")
@unittest.skipUnless(shutil.which("pwsh"), "Real historical TWP requires PowerShell")
class HistoricalDerivedRealSourceSmokeTests(unittest.TestCase):
    def test_completed_week_rebuild_is_read_only_and_idempotent(self):
        root = TOOLS.parent
        original = root / "data-derived/team-week-performance/nfl-reise/2026/03.json"
        self.assertTrue(original.is_file(), "Existing W03 Awards must be published")
        before = original.read_bytes()
        report = pipeline.preflight(
            root, mode="week", season=2026, week=3, league_id="nfl-reise",
        )
        self.assertEqual(report["TargetCount"], 1)
        self.assertTrue(report["SecondPassNoop"])
        self.assertEqual(report["TWPWouldChange"], 0)
        self.assertFalse(report["Published"])
        self.assertEqual(before, original.read_bytes())


if __name__ == "__main__":
    unittest.main()
