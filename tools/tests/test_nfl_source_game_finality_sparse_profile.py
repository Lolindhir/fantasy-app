"""NFL Live finality job: the sparse/blobless profile of the game-finality scope hides no input or write path (Issue #1263, G5 E5).

The profile is parsed from the workflow and applied with real git in a throw-away repository that mirrors the data
layout. The publication loop's git mechanics (reset, clean, add, diff, push) are run in a sparse blobless clone. The
one-time full-versus-sparse output parity run of the actual commands is documented in the pull request.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "sync-nfl-source-data.yml"

FILES = [
    "AGENTS.md", "tools/nfl_source_data.py", "tools/git_transient.py", ".github/scripts/s.sh",
    "data-source/registry.json", "data-source/league-registry.json", "data-source/nfl/teams.json",
    "data-source/leagues/nfl-reise/manifest.json", "data-source/leagues/nfl-reise/seasons/2026/league.json",
    "data-source/nfl/schedules/2026.json", "data-source/nfl/game-finality/2026.json",
    "data-source/providers/nflverse/schedules/raw-latest.csv", "data-source/providers/nflverse/schedules/metadata.json",
    "data-source/providers/nflverse/game-finality/raw-latest.csv", "data-source/providers/nflverse/game-finality/metadata.json",
    "data-source/providers/nflverse/player-stats/2026/raw.csv", "data-source/providers/sleeper/players/p.json",
    "data-source/nfl/player-stats/2026/1.json", "data-source/nfl/weekly-rosters/2026/1.json",
    "data-source/nfl/identities/i.json", "data-source/_sync/keep.json",
    "data-derived/player-valuation/a.json", "public/data/League.json", "public/data/past_seasons/p.json",
    "fantasy-management/f.md", "src/app/a.ts",
]
READ_OR_WRITTEN = [
    "tools/nfl_source_data.py", "tools/git_transient.py", "data-source/registry.json", "data-source/nfl/teams.json",
    "data-source/leagues/nfl-reise/manifest.json", "data-source/nfl/schedules/2026.json",
    "data-source/nfl/game-finality/2026.json",
    "data-source/providers/nflverse/schedules/raw-latest.csv", "data-source/providers/nflverse/schedules/metadata.json",
    "data-source/providers/nflverse/game-finality/raw-latest.csv", "data-source/providers/nflverse/game-finality/metadata.json",
    "data-source/_sync/keep.json",
]
ABSENT = [
    "data-source/providers/nflverse/player-stats/2026/raw.csv", "data-source/providers/sleeper/players/p.json",
    "data-source/nfl/player-stats/2026/1.json", "data-source/nfl/weekly-rosters/2026/1.json",
    "data-source/nfl/identities/i.json", "data-source/leagues/nfl-reise/seasons/2026/league.json",
    "data-derived/player-valuation/a.json", "public/data/League.json", "fantasy-management/f.md", "src/app/a.ts",
]


def steps() -> list[dict]:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]["sync"]["steps"]


def sparse_step() -> dict:
    return next(s for s in steps() if "game-finality sparse" in str(s.get("name", "")))


def profile() -> list[str]:
    step = sparse_step()
    assert step["with"]["sparse-checkout-cone-mode"] is False
    assert step["with"]["filter"] == "blob:none"
    return [p.strip() for p in step["with"]["sparse-checkout"].splitlines() if p.strip()]


def git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=check, capture_output=True, text=True,
        env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
             "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"},
    )


class GameFinalitySparseProfileTest(unittest.TestCase):
    def test_only_the_game_finality_scope_is_sparse_and_the_fallback_exists(self) -> None:
        self.assertEqual("inputs.materialization_scope == 'game-finality'", sparse_step()["if"])
        full = next(s for s in steps() if s.get("name") == "Checkout main")
        self.assertEqual("inputs.materialization_scope != 'game-finality'", full["if"])
        self.assertNotIn("sparse-checkout", full["with"])
        verify = next(s for s in steps() if "Verify game-finality sparse inputs" in str(s.get("name", "")))
        self.assertEqual("inputs.materialization_scope == 'game-finality'", verify["if"])
        self.assertIn("git sparse-checkout disable", verify["run"])
        step = sparse_step()["with"]
        self.assertEqual("main", step["ref"])
        self.assertEqual(1, step["fetch-depth"])
        self.assertEqual("${{ secrets.PAT_PUSH }}", step["token"])

    def test_profile_includes_every_read_and_written_path_and_nothing_else_large(self) -> None:
        prof = profile()
        for required in (
            "/tools/", "/data-source/*.json", "/data-source/nfl/schedules/", "/data-source/nfl/game-finality/",
            "/data-source/providers/nflverse/schedules/", "/data-source/providers/nflverse/game-finality/",
            "/data-source/_sync/",
        ):
            self.assertIn(required, prof)
        for entry in prof:
            self.assertNotIn("player-stats", entry)
            self.assertNotIn("weekly-rosters", entry)
            self.assertNotIn("/data-derived", entry)
            self.assertNotIn("/public", entry)
            self.assertNotEqual("/data-source/providers/", entry)
            self.assertNotEqual("/data-source/providers/nflverse/", entry)

    def test_profile_applied_by_git_keeps_all_inputs_and_drops_the_rest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            git(repo, "init", "-q", "-b", "main")
            for rel in FILES:
                (repo / rel).parent.mkdir(parents=True, exist_ok=True)
                (repo / rel).write_text("x")
            git(repo, "add", "-A")
            git(repo, "commit", "-q", "-m", "seed")
            git(repo, "sparse-checkout", "init", "--no-cone")
            (repo / ".git" / "info" / "sparse-checkout").write_text("\n".join(profile()) + "\n")
            git(repo, "checkout", "-q", "main")
            present = {rel for rel in FILES if (repo / rel).exists()}
        for rel in READ_OR_WRITTEN:
            self.assertIn(rel, present)
        for rel in ABSENT:
            self.assertNotIn(rel, present)

    def test_publication_loop_git_mechanics_in_a_sparse_blobless_clone(self) -> None:
        """reset --hard, clean -fd -- data-source, add -- data-source/providers, add -- data-source, diff pathspecs, push, race."""
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            seed = base / "seed"
            seed.mkdir()
            git(seed, "init", "-q", "-b", "main")
            for rel in FILES:
                (seed / rel).parent.mkdir(parents=True, exist_ok=True)
                (seed / rel).write_text("x")
            git(seed, "add", "-A")
            git(seed, "commit", "-q", "-m", "seed")
            origin = base / "origin.git"
            subprocess.run(["git", "clone", "-q", "--bare", str(seed), str(origin)], check=True)
            for key, value in (("uploadpack.allowFilter", "true"), ("uploadpack.allowAnySHA1InWant", "true"),
                               ("receive.denyCurrentBranch", "ignore")):
                git(origin, "config", key, value)
            url = f"file://{origin}"

            def clone(name: str) -> Path:
                c = base / name
                subprocess.run(["git", "clone", "-q", "--filter=blob:none", "--no-checkout", "--depth", "1",
                                "--branch", "main", url, str(c)], check=True)
                git(c, "sparse-checkout", "init", "--no-cone")
                (c / ".git" / "info" / "sparse-checkout").write_text("\n".join(profile()) + "\n")
                git(c, "checkout", "-q", "main")
                return c

            a, b = clone("a"), clone("b")
            # a competing writer outside the materialization inputs and one inside the profile
            (b / "data-source/_sync/other.json").write_text("b")
            git(b, "add", "-A", "--", "data-source/_sync")
            git(b, "commit", "-q", "-m", "b")
            git(b, "push", "-q", url, "HEAD:main")

            # reset_to_main equivalent: no error, nothing outside the profile appears
            git(a, "fetch", "-q", "origin", "main")
            git(a, "reset", "-q", "--hard", "origin/main")
            clean = git(a, "clean", "-fd", "--", "data-source", check=False)
            self.assertEqual(0, clean.returncode, clean.stderr)
            self.assertTrue((a / "data-source/_sync/other.json").exists())
            self.assertFalse((a / "data-source/nfl/player-stats").exists())
            self.assertEqual("", git(a, "status", "--porcelain=v1").stdout)

            # raw write -> git add -- data-source/providers must stage the changed raw files with rc 0
            for rel in ("data-source/providers/nflverse/schedules/raw-latest.csv",
                        "data-source/providers/nflverse/game-finality/metadata.json"):
                (a / rel).write_text("changed")
            added = git(a, "add", "--", "data-source/providers", check=False)
            self.assertEqual(0, added.returncode, added.stderr)
            staged = git(a, "diff", "--cached", "--name-only").stdout.split()
            self.assertEqual(sorted(["data-source/providers/nflverse/schedules/raw-latest.csv",
                                     "data-source/providers/nflverse/game-finality/metadata.json"]), sorted(staged))
            git(a, "commit", "-q", "-m", "raw")
            self.assertEqual(0, git(a, "push", "-q", url, "HEAD:main", check=False).returncode)

            # canonical write incl. new files and a failure diagnostic -> git add -- data-source with rc 0
            (a / "data-source/nfl/game-finality/2027.json").write_text("new")
            (a / "data-source/nfl/schedules/2026.json").write_text("changed")
            (a / "data-source/_sync").mkdir(parents=True, exist_ok=True)
            (a / "data-source/_sync/last-failure.game-finality.json").write_text("{}")
            status = git(a, "status", "--porcelain=v1").stdout
            for rel in ("data-source/nfl/game-finality/2027.json", "data-source/nfl/schedules/2026.json",
                        "data-source/_sync/last-failure.game-finality.json"):
                self.assertIn(rel, status)
            added = git(a, "add", "--", "data-source", check=False)
            self.assertEqual(0, added.returncode, added.stderr)
            added = git(a, "add", "--", "data-source/_sync/last-failure.game-finality.json", check=False)
            self.assertEqual(0, added.returncode, added.stderr)
            git(a, "commit", "-q", "-m", "canonical")

            # a competing writer advances main again while a publishes
            git(b, "fetch", "-q", "origin", "main")
            git(b, "reset", "-q", "--hard", "origin/main")
            (b / "data-source/_sync/other2.json").write_text("b2")
            git(b, "add", "-A", "--", "data-source/_sync")
            git(b, "commit", "-q", "-m", "b2")
            git(b, "push", "-q", url, "HEAD:main")

            # publish race: rejected push, tree diff of the input pathspecs on objects, rebase and push
            rejected = git(a, "push", url, "HEAD:main", check=False)
            self.assertNotEqual(0, rejected.returncode)
            git(a, "fetch", "-q", "origin", "main")
            base_sha = git(a, "rev-parse", "HEAD~1").stdout.strip()
            diff = git(a, "diff", "--quiet", base_sha, "origin/main", "--",
                       "data-source/registry.json", "data-source/providers/nflverse", "data-source/nfl", "tools",
                       "public/data/past_seasons", check=False)
            self.assertEqual(0, diff.returncode, diff.stderr)
            rebase = git(a, "rebase", "origin/main", check=False)
            self.assertEqual(0, rebase.returncode, rebase.stderr)
            push = git(a, "push", url, "HEAD:main", check=False)
            self.assertEqual(0, push.returncode, push.stderr)
            self.assertFalse((a / "data-source/nfl/player-stats").exists())


if __name__ == "__main__":
    unittest.main()
