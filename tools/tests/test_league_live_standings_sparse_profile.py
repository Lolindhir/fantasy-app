"""League Live Standings job: the sparse/blobless checkout profile hides no input (Issue #1263, G5 AP2c).

The profile is parsed from the workflow. The Standings writer is run twice with a forced regeneration:
once in a tree that contains only the sparse profile and once in a tree that additionally exposes the
complete data roots. Both must produce identical outputs, so a future new input read outside the profile
fails here instead of silently changing the published Standings.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "league-live.yml"
OUTPUTS_COPIED = ("public/data/Standings.json", "public/data/Timestamps.json", "data-derived/league-standings")
HASHED = ("public/data/Standings.json", "data-derived/league-standings")


def standings_profile() -> list[str]:
    data = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    step = next(s for s in data["jobs"]["standings"]["steps"] if str(s.get("uses", "")).startswith("actions/checkout@"))
    return [p.strip() for p in step["with"]["sparse-checkout"].splitlines() if p.strip()]


def link(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    os.symlink(src, dst)


def expand(rel: str) -> list[str]:
    """Replace a directory that contains writer outputs by its children so no symlinked dir is written into."""
    if not any(out == rel or out.startswith(rel + "/") for out in OUTPUTS_COPIED) or not (ROOT / rel).is_dir():
        return [rel]
    if rel in OUTPUTS_COPIED:
        return [rel]
    found: list[str] = []
    for child in sorted((ROOT / rel).iterdir()):
        found.extend(expand(f"{rel}/{child.name}"))
    return found


def build_tree(base: Path, entries: list[str]) -> Path:
    """Symlink the given repo entries; outputs of the writer are real copies so the repo is never touched."""
    base.mkdir(parents=True)
    for entry in entries:
        for rel in expand(entry.strip("/")):
            if rel in OUTPUTS_COPIED or not (ROOT / rel).exists():
                continue
            link(ROOT / rel, base / rel)
    for rel in OUTPUTS_COPIED:
        source = ROOT / rel
        target = base / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target)
        elif source.exists():
            shutil.copy2(source, target)
    return base


def regenerate(tree: Path) -> dict[str, str]:
    for rel in HASHED:
        path = tree / rel
        shutil.rmtree(path) if path.is_dir() else path.unlink(missing_ok=True)
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "league_standings_app_publish.py"), "--repo-root", str(tree), "write"],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr[-1500:])
    digests = {}
    for rel in HASHED:
        path = tree / rel
        for file in sorted(path.rglob("*")) if path.is_dir() else [path]:
            if file.is_file():
                digests[str(file.relative_to(tree))] = hashlib.sha256(file.read_bytes()).hexdigest()
    return digests


class StandingsSparseProfileTest(unittest.TestCase):
    def test_profile_contains_the_publication_helpers_and_outputs(self) -> None:
        profile = standings_profile()
        for required in (
            "/.github/scripts/", "/tools/", "/data-meta/", "/data-source/leagues/",
            "/data-source/nfl/schedules/", "/data-source/nfl/game-finality/",
            "/public/data/League.json", "/public/data/Standings.json", "/public/data/Timestamps.json",
            "/data-derived/league-standings/", "/data-derived/season-statistics/",
        ):
            self.assertIn(required, profile)
        # historical player-stats feed NflStatsComplete only, never LeagueScoredWeek used by Standings
        self.assertFalse([p for p in profile if "player-stats" in p])

    def test_publication_scope_is_unchanged(self) -> None:
        source = WORKFLOW.read_text(encoding="utf-8")
        block = source.split("Rebuild and publish Standings data", 1)[1].split("league:", 1)[0]
        for fragment in ("--scope standings", "--path public/data", "--path data-derived/league-standings",
                         "python3 tools/league_standings_app_publish.py write"):
            self.assertIn(fragment, block)

    def test_forced_regeneration_is_identical_without_the_excluded_data(self) -> None:
        profile = standings_profile()
        everything = ["/tools/", "/data-meta/", "/data-source/", "/data-derived/", "/public/data/", "/.github/"]
        with tempfile.TemporaryDirectory() as tmp:
            sparse = build_tree(Path(tmp) / "sparse", profile)
            full = build_tree(Path(tmp) / "full", everything)
            self.assertFalse((sparse / "data-source" / "nfl" / "player-stats").exists())
            self.assertTrue((full / "data-source" / "nfl" / "player-stats").exists())
            self.assertEqual(regenerate(full), regenerate(sparse))


if __name__ == "__main__":
    unittest.main()
