"""Executable fixtures for the unchanged NFL Source publication checks (#1618)."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest

HELPER = Path(__file__).resolve().parents[1] / "nfl_source_data_lib/publication_legacy.sh"


class LegacyPublicationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.git("init", "-q")
        self.git("config", "user.name", "Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        self.put("data-source/tracked.json", "accepted")
        self.git("add", "-A")
        self.git("commit", "-qm", "fixture")

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.root), *args], text=True)

    def put(self, path, content="fixture"):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target

    def run_helper(self, command, scope="full", *args):
        return subprocess.run(
            ["bash", "-euo", "pipefail", "-c",
             'source "$1"; materialization_scope="$2"; injury_year=2024; '
             'failure_diagnostic_file=data-source/_sync/failure.json; shift 2; ' + command,
             "fixture", str(HELPER), scope, *args],
            cwd=self.root, text=True, capture_output=True,
        )

    def assert_status(self, expected, result):
        self.assertEqual(expected, result.returncode, result.stdout + result.stderr)

    def test_cleanup_removes_only_untracked_source(self):
        source = self.put("data-source/temp/untracked.json")
        canonical = self.put("data-canonical/nfl/combine/2024.json")
        outside = self.put("outside.txt")
        self.assert_status(0, self.run_helper("clean_source_worktree"))
        self.assertFalse(source.exists())
        self.assertTrue(canonical.exists())
        self.assertTrue(outside.exists())
        self.assertEqual("accepted", (self.root / "data-source/tracked.json").read_text())

    def test_general_guard_accepts_only_existing_source_scope(self):
        self.put("data-source/nfl/combine/2024.json")
        self.assert_status(0, self.run_helper("assert_source_data_only"))
        outside = self.put("outside.txt")
        result = self.run_helper("assert_source_data_only")
        self.assert_status(1, result)
        self.assertIn("Unexpected changes outside data-source/", result.stderr)
        outside.unlink()
        self.put("data-canonical/nfl/combine/2024.json")
        self.assert_status(1, self.run_helper("assert_source_data_only"))

    def test_scoped_canonical_guard_all_scopes(self):
        cases = {
            "full": ("data-source/nfl/combine/2024.json", None),
            "game-finality": ("data-source/nfl/game-finality/2024/01.json",
                              "data-source/nfl/schedule-odds/2024.json"),
            "schedule-odds": ("data-source/nfl/schedule-odds/2024.json",
                              "data-source/nfl/schedules/2024.json"),
            "injuries": ("data-source/nfl/injuries/2024/01.json",
                         "data-source/nfl/injuries/2025/01.json"),
        }
        for scope, (allowed, denied) in cases.items():
            with self.subTest(scope=scope):
                path = self.put(allowed)
                diagnostic = self.put("data-source/_sync/failure.json")
                self.assert_status(0, self.run_helper("assert_scoped_canonical_write_set", scope))
                if denied:
                    other = self.put(denied)
                    result = self.run_helper("assert_scoped_canonical_write_set", scope)
                    self.assert_status(1, result)
                    self.assertIn(f"Scoped {scope} materialization touched unexpected paths", result.stderr)
                    other.unlink()
                path.unlink()
                diagnostic.unlink()
        schedule = self.put("data-source/nfl/schedules/2024.json")
        self.assert_status(0, self.run_helper("assert_scoped_canonical_write_set", "game-finality"))
        schedule.unlink()

    def test_raw_guard_only_injury_scope(self):
        raw = self.put("data-source/providers/nflverse/injuries/raw-2024.csv")
        meta = self.put("data-source/providers/nflverse/injuries/metadata-2024.json")
        diagnostic = self.put("data-source/_sync/failure.json")
        self.assert_status(0, self.run_helper("assert_scoped_raw_write_set", "injuries"))
        other = self.put("data-source/providers/nflverse/injuries/raw-2025.csv")
        result = self.run_helper("assert_scoped_raw_write_set", "injuries")
        self.assert_status(1, result)
        self.assertIn("Scoped injury Raw sync touched unexpected paths", result.stderr)
        for scope in ("full", "game-finality", "schedule-odds"):
            self.assert_status(0, self.run_helper("assert_scoped_raw_write_set", scope))
        for path in (raw, meta, diagnostic, other):
            path.unlink()

    def test_legacy_second_pass_counters_and_exit_codes(self):
        expected = {
            "full": {"identityChanged": False, "providerMappingsChanged": False,
                     "draftFilesChanged": 0, "auditChanged": False},
            "game-finality": {"scheduleFilesChanged": 0, "scheduleChangedPaths": [],
                              "gameFinalityFilesChanged": 0, "gameFinalityChangedPaths": []},
            "schedule-odds": {"oddsFilesChanged": 0, "oddsChangedPaths": []},
            "injuries": {"injuryCanonicalFilesChanged": 0, "injuryCanonicalChangedPaths": [],
                         "injuryObsoleteRequiresReview": []},
        }
        for scope, counters in expected.items():
            with self.subTest(scope=scope):
                log = self.put("result.json", json.dumps(counters))
                self.assert_status(0, self.run_helper('assert_semantic_noop "$1" "$materialization_scope"', scope, str(log)))
                for key in counters:
                    changed = dict(counters)
                    changed[key] = ["changed"] if isinstance(counters[key], list) else 1
                    log.write_text(json.dumps(changed))
                    result = self.run_helper('assert_semantic_noop "$1" "$materialization_scope"', scope, str(log))
                    self.assert_status(1, result)
                    self.assertIn("Semantic no-op verification failed", result.stderr)
                    self.assertIn(key, result.stderr)
                    del changed[key]
                    log.write_text(json.dumps(changed))
                    self.assert_status(1, self.run_helper('assert_semantic_noop "$1" "$materialization_scope"', scope, str(log)))
        # H3 counter expansion is deliberately NOT active in M2b.
        log.write_text(json.dumps(dict(expected["full"], combineFilesChanged=1, phase1FilesChanged=1)))
        self.assert_status(0, self.run_helper('assert_semantic_noop "$1" "$materialization_scope"', "full", str(log)))


if __name__ == "__main__":
    unittest.main()
