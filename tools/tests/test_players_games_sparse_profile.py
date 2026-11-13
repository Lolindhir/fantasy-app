"""Games workflow (Players profile reverted, no measured gain): the sparse/blobless checkout hides no input (Issue #1263, G5 AP5 candidates).

The profile is parsed from each workflow and applied with real git in a throw-away repository; the Verify step must
list inputs that the profile keeps and must fall back to a complete checkout. Read paths were proven by running the
real generators in a sparse worktree against a complete one (identical output).
"""
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"

COMMON = ["package.json", "package-lock.json", "tools/rebuild_and_publish.py", ".github/workflows/x.yml",
          "data-meta/l/metadata.json", "data-source/leagues/l/a.json", "data-source/nfl/schedules/2026.json",
          "data-source/nfl/game-finality/2026.json", "data-source/nfl/teams.json", "public/data/Timestamps.json",
          "public/data/backup/a.json"]
ABSENT_BOTH = ["src/app/a.ts", "fantasy-management/f.md", "research/r.md", "data-source/market/m.json",
               "data-source/providers/nflverse/raw.json", "data-source/nfl/player-stats/2019/1.json",
               "public/assets/a.png"]
PLAYERS_ONLY = ["tools/players_app_publish.py", "data-derived/player-valuation/l/2026/week-01.json",
                "data-source/nfl/identities/players.json", "data-source/nfl/platform/sleeper/players.json",
                "data-source/nfl/player-stats/2025/1.json", "data-source/nfl/snap-counts/2026/1.json", "data-source/nfl/snap-counts/2025/1.json",
                "data-source/nfl/weekly-rosters/2026/1.json", "data-source/nfl/special-teams-fumble-events/2024/1.json",
                "data-source/nfl/qbr-week/2026.json", "data-source/nfl/rosters/2026.json", "data-source/nfl/draft/2026.json",
                "data-source/nfl/player-profiles/nflverse.json", "data-source/nfl/player-game-long-gains/2026.json",
                "public/data/Players.json"]
GAMES_ONLY = ["public/requests/RequestSchedule.ps1", "public/requests/utils/ConfigUtils.psm1", "public/data/Schedule.json"]


def steps(name: str) -> list[dict]:
    return yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))["jobs"]["update"]["steps"]


def sparse_step(name: str) -> dict:
    return next(s for s in steps(name) if "sparse, blobless" in str(s.get("name", "")))


def profile(name: str) -> list[str]:
    step = sparse_step(name)["with"]
    assert step["sparse-checkout-cone-mode"] is False and step["filter"] == "blob:none" and step["fetch-depth"] == 1
    return [p.strip() for p in step["sparse-checkout"].splitlines() if p.strip()]


def git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True,
                   env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"})


def apply(name: str, files: list[str]) -> set[str]:
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        git(repo, "init", "-q", "-b", "main")
        for rel in files:
            (repo / rel).parent.mkdir(parents=True, exist_ok=True)
            (repo / rel).write_text("x")
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "seed")
        git(repo, "sparse-checkout", "init", "--no-cone")
        (repo / ".git" / "info" / "sparse-checkout").write_text("\n".join(profile(name)) + "\n")
        git(repo, "checkout", "-q", "main")
        return {rel for rel in files if (repo / rel).exists()}


class PlayersGamesSparseProfileTest(unittest.TestCase):
    CASES = {"update-games.yml": GAMES_ONLY}

    def test_binding_verify_and_fallback(self) -> None:
        for name in self.CASES:
            with self.subTest(workflow=name):
                names = [str(s.get("name")) for s in steps(name)]
                self.assertNotIn("Checkout repository", names)
                verify = next(s for s in steps(name) if "Verify sparse inputs" in str(s.get("name", "")))
                self.assertIn("git sparse-checkout disable", verify["run"])
                self.assertEqual(names.index(sparse_step(name)["name"]) + 1, names.index(verify["name"]))
                self.assertIn("secrets.PAT_PUSH", sparse_step(name)["with"]["token"])
                self.assertIn("package-lock.json", verify["run"])

    def test_profile_keeps_inputs_and_drops_unrelated_trees(self) -> None:
        for name, only in self.CASES.items():
            with self.subTest(workflow=name):
                present = apply(name, COMMON + only + ABSENT_BOTH)
                for rel in COMMON + only:
                    self.assertIn(rel, present)
                for rel in ABSENT_BOTH:
                    self.assertNotIn(rel, present)

    def test_games_profile_has_no_player_data(self) -> None:
        present = apply("update-games.yml", COMMON + PLAYERS_ONLY)
        self.assertNotIn("data-source/nfl/player-stats/2025/1.json", present)
        self.assertNotIn("data-derived/player-valuation/l/2026/week-01.json", present)

    def test_verify_paths_exist_in_profile(self) -> None:
        for name, only in self.CASES.items():
            with self.subTest(workflow=name):
                verify = next(s for s in steps(name) if "Verify sparse inputs" in str(s.get("name", "")))
                present = apply(name, COMMON + only + ABSENT_BOTH)
                line = next(l for l in verify["run"].splitlines() if l.strip().startswith("for path in"))
                paths = line.split(" in ", 1)[1].split("; do")[0].split()
                for p in paths:
                    self.assertTrue(any(f == p or f.startswith(p + "/") for f in present), p)


if __name__ == "__main__":
    unittest.main()
