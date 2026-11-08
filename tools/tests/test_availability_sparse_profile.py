"""Player-availability writer checkout profile hides no input (Issue #1263, G5 AP3b).

The profile is parsed from sync-nfl-player-availability.yml. The sync runs once in a tree containing only the
sparse profile and once in a tree with the complete data roots; both must produce identical outputs, and the
publication scope stays exactly the two availability prefixes.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import espn_player_availability as availability  # noqa: E402

WORKFLOW = ROOT / ".github" / "workflows" / "sync-nfl-player-availability.yml"


def doc() -> dict:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def profile() -> list[str]:
    step = next(s for s in doc()["jobs"]["sync-availability"]["steps"] if str(s.get("uses", "")).startswith("actions/checkout@"))
    assert step["with"]["filter"] == "blob:none"
    assert step["with"]["sparse-checkout-cone-mode"] is False
    return [p.strip() for p in step["with"]["sparse-checkout"].splitlines() if p.strip()]


def materialize(base: Path, patterns: list[str]) -> Path:
    """Copy the files a gitignore-style (non-cone) profile selects; only what the profile names is present."""
    base.mkdir(parents=True)
    for pattern in patterns:
        rel = pattern.lstrip("/")
        for match in glob.glob(str(ROOT / rel), recursive=True):
            source = Path(match)
            target = base / source.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            if source.is_dir():
                shutil.copytree(source, target, dirs_exist_ok=True)
            else:
                shutil.copy2(source, target)
    return base


def digest(tree: Path) -> dict[str, str]:
    out = {}
    for rel in ("data-source/nfl/player-availability/espn.json", "data-source/providers/espn/player-availability/metadata.json"):
        path = tree / rel
        out[rel] = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""
    return out


def payload() -> dict:
    return {"players": [{"id": 1000 + i, "player": {"id": 1000 + i, "injuryStatus": "OUT" if i % 7 == 0 else "ACTIVE"}} for i in range(400)]}


class AvailabilitySparseProfileTest(unittest.TestCase):
    def test_profile_is_exactly_the_writer_inputs(self) -> None:
        self.assertEqual(
            [
                "/.github/scripts/",
                "/tools/",
                "/data-source/leagues/*/manifest.json",
                "/data-source/nfl/player-availability/",
                "/data-source/providers/espn/",
            ],
            profile(),
        )

    def test_publication_scope_is_unchanged(self) -> None:
        run = next(s for s in doc()["jobs"]["sync-availability"]["steps"] if "python3 tools/rebuild_and_publish.py" in str(s.get("run", "")))["run"]
        self.assertIn("--scope nfl-player-availability", run)
        self.assertIn("--path data-source/nfl/player-availability", run)
        self.assertIn("--path data-source/providers/espn", run)
        self.assertEqual(2, run.count("--path "))

    def test_fallback_to_complete_checkout_exists(self) -> None:
        self.assertIn("git sparse-checkout disable", WORKFLOW.read_text(encoding="utf-8"))

    def test_sync_output_is_identical_with_sparse_and_full_tree(self) -> None:
        observed_at = "2026-01-01T00:00:00Z"
        with tempfile.TemporaryDirectory() as tmp:
            sparse = materialize(Path(tmp) / "sparse", profile())
            full = materialize(Path(tmp) / "full", ["/tools/", "/data-source/", "/data-meta/"])
            self.assertFalse((sparse / "data-source" / "nfl" / "player-stats").exists())
            self.assertTrue((full / "data-source" / "nfl" / "player-stats").exists())
            results = {}
            for name, tree in (("sparse", sparse), ("full", full)):
                season = availability.current_source_season(tree)
                availability.sync(tree, season, payload(), observed_at)
                results[name] = (season, digest(tree))
            self.assertEqual(results["full"], results["sparse"])
            self.assertTrue(all(results["sparse"][1].values()))


if __name__ == "__main__":
    unittest.main()
