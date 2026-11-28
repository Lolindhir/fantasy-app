"""Isolated Git worktree contracts for the dormant Canonical locator."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from canonical_routing import (COMBINE_DATASET, COMBINE_ROUTING, FamilyRouting,
                               RouteMode, preflight_accepted_combine)
from data_roots import DATA_CANONICAL_ROOT, DATA_SOURCE_ROOT


class CanonicalRoutingTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.git("init", "-q")
        self.git("config", "user.name", "Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        self.legacy = self.root / DATA_SOURCE_ROOT / "nfl/combine/2024.json"
        self.canonical = self.root / DATA_CANONICAL_ROOT / "nfl/combine/2024.json"
        self.write(self.legacy, 2024)
        self.write(self.legacy.with_name("2025.json"), 2025)
        self.base = self.commit()

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.root), *args]).decode().strip()

    def commit(self):
        self.git("add", "-A")
        self.git("commit", "-qm", "fixture")
        return self.git("rev-parse", "HEAD")

    def write(self, path, season):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"Season": season, "Finalized": True, "Records": []}))

    def preflight(self, routing=COMBINE_ROUTING):
        return preflight_accepted_combine(self.root, self.base, routing)

    def test_default_dormant_legacy_and_complete_inventory(self):
        self.assertEqual(RouteMode.LEGACY, COMBINE_ROUTING.mode)
        self.assertEqual(frozenset(), COMBINE_ROUTING.legacy_exceptions)
        snapshot = self.preflight()
        self.assertEqual({2024, 2025}, set(snapshot.partitions))
        self.assertEqual(self.legacy, snapshot.path_for(2024))
        self.assertEqual(self.git("rev-parse", f"HEAD:{self.legacy.relative_to(self.root).as_posix()}"),
                         snapshot.partitions[2024].blob)
        snapshot.require_existing_candidates({2024, 2025})
        for candidates in ({2025}, {2024, 2025, 2027}):
            with self.assertRaises(ValueError):
                snapshot.require_existing_candidates(candidates)
        with self.assertRaises(ValueError):
            snapshot.path_for(2027)

    def test_deleted_and_staged_deleted_partition(self):
        self.legacy.unlink()
        with self.assertRaises(FileNotFoundError):
            self.preflight()
        self.git("add", "-u")
        with self.assertRaises(FileNotFoundError):
            self.preflight()
        self.assertFalse(self.legacy.exists())

    def test_changed_bytes_and_duplicate(self):
        original = self.legacy.read_bytes()
        self.legacy.write_bytes(original + b" ")
        with self.assertRaises(ValueError):
            self.preflight()
        self.legacy.write_bytes(original)
        self.write(self.canonical, 2024)
        with self.assertRaises(ValueError):
            self.preflight()

    def test_transition_route_and_no_fallback(self):
        policy = FamilyRouting(RouteMode.TRANSITION, frozenset({2025}))
        self.assertEqual(self.canonical, self.root / policy.relative_path(COMBINE_DATASET, 2024))
        self.assertEqual(self.canonical.with_name("2027.json"),
                         self.root / policy.relative_path(COMBINE_DATASET, 2027))
        with self.assertRaises(ValueError):
            self.preflight(policy)
        self.canonical.parent.mkdir(parents=True)
        self.legacy.rename(self.canonical)
        self.base = self.commit()
        snapshot = self.preflight(policy)
        self.assertEqual(self.canonical, snapshot.path_for(2024))
        self.assertEqual(self.legacy.with_name("2025.json"), snapshot.path_for(2025))
        self.canonical.unlink()
        with self.assertRaises(FileNotFoundError):
            self.preflight(policy)
        self.write(self.legacy, 2024)
        with self.assertRaises(FileNotFoundError):
            self.preflight(policy)

    def test_reviewed_deletion_boundary_and_retry_repin(self):
        self.legacy.unlink()
        new_commit = self.commit()
        with self.assertRaises(ValueError):
            self.preflight()
        self.base = new_commit
        self.assertEqual({2025}, set(self.preflight().partitions))
        self.base = "0" * 40
        with self.assertRaises(ValueError):
            self.preflight()

    def test_untracked_file_and_symlink_fail_closed(self):
        self.write(self.legacy.with_name("2027.json"), 2027)
        with self.assertRaises(ValueError):
            self.preflight()
        self.legacy.with_name("2027.json").unlink()
        self.canonical.parent.mkdir(parents=True)
        self.canonical.symlink_to(self.legacy)
        with self.assertRaises(ValueError):
            self.preflight()

    def test_invalid_key_or_policy(self):
        for dataset, season in (("nflverse.combine", 2024), (COMBINE_DATASET, True),
                                (COMBINE_DATASET, 10000), ("../providers", 2024)):
            with self.assertRaises(ValueError):
                COMBINE_ROUTING.relative_path(dataset, season)
        with self.assertRaises(ValueError):
            FamilyRouting(RouteMode.LEGACY, frozenset({2024}))
        self.assertEqual(self.canonical, self.root / FamilyRouting(RouteMode.CANONICAL)
                         .relative_path(COMBINE_DATASET, 2024))


if __name__ == "__main__":
    unittest.main()
