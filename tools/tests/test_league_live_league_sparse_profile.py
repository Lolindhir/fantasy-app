"""League Live League job: the exclusion sparse profile hides no input of the generator chain (Issue #1263, G5 E2).

The profile is parsed from the workflow and applied with real git in a throw-away repository that mirrors the data
layout. Included: every recent season (also future ones), the sleeper provider, tools, derived data and App data.
Excluded: only old seasons and folders the chain never reads. The one-time full-versus-sparse output parity run of the
actual chain (strace of the exact commands, byte-identical outputs) is documented in the pull request.
"""
from __future__ import annotations

import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "league-live.yml"

def job() -> dict:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]["league"]


def profile() -> list[str]:
    step = next(s for s in job()["steps"] if str(s.get("uses", "")).startswith("actions/checkout@"))
    assert step["with"]["sparse-checkout-cone-mode"] is False
    assert step["with"]["filter"] == "blob:none"
    return [p.strip() for p in step["with"]["sparse-checkout"].splitlines() if p.strip()]


def git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True,
        env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
             "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"},
    )


class LeagueSparseProfileTest(unittest.TestCase):
    def test_profile_is_an_exclusion_profile_with_the_expected_exclusions(self) -> None:
        entries = profile()
        self.assertEqual("/*", entries[0])
        excluded = {e[1:] for e in entries if e.startswith("!")}
        for required in (
            "/fantasy-management/", "/research/", "/src/", "/public/assets/", "/public/docs/",
            "/data-source/market/", "/data-source/providers/*/",
        ):
            self.assertIn(required, excluded)
        self.assertIn("/data-source/providers/sleeper/", entries)
        # only seasons before 2021 are excluded: the PWF model reads target season minus five onward
        for entry in excluded:
            if "player-stats" in entry or "weekly-rosters" in entry:
                self.assertRegex(entry, r"/(19\*|200\*|201\*|2020)/$")
        for dependency in ("/tools/", "/data-meta/", "/data-derived/", "/public/data/", "/public/requests/", "/.github/"):
            self.assertFalse(any(dependency.startswith(e) for e in excluded), dependency)
            self.assertNotIn(dependency, excluded)
        self.assertNotIn("/public/data/backup/", excluded)  # RequestLeague writes League backups there

    def test_publication_scope_and_fallback_are_unchanged(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        block = text.split("Rebuild and publish League, PlayerWeekFantasy", 1)[1].split("\n\n", 1)[0]
        for fragment in (
            "--scope league", "--path public/data", "--path data-derived/player-week-fantasy",
            "--path data-derived/team-week-performance", "--path data-derived/league-transactions",
            "--path data-derived/league-drafts",
        ):
            self.assertIn(fragment, block)
        self.assertEqual(7, block.count("--path "))
        verify = next(s for s in job()["steps"] if "Verify League sparse inputs" in str(s.get("name", "")))
        self.assertIn("git sparse-checkout disable", verify["run"])
        self.assertIn("player-stats/2025", verify["run"])

    def test_profile_applied_by_git_includes_future_seasons_and_drops_only_old_ones(self) -> None:
        files = [
            "AGENTS.md", "tools/x.py", "data-meta/m.json", "data-derived/player-valuation/a.json",
            "public/data/League.json", "public/requests/R.ps1", ".github/scripts/s.ps1",
            "data-source/registry.json", "data-source/leagues/l/manifest.json",
            "data-source/providers/sleeper/leagues/1/league.json", "data-source/providers/espn/x.json",
            "data-source/providers/nflverse/y.csv", "data-source/market/m.json", "data-source/nfl/identities/i.json",
            "data-source/nfl/schedules/2026.json", "public/data/backup/b.json", "fantasy-management/f.md",
            "src/app/a.ts", "research/r.md", "public/assets/a.png", "public/docs/d.md",
        ] + [
            f"data-source/nfl/{kind}/{year}/1.json"
            for kind in ("player-stats", "weekly-rosters")
            for year in (1999, 2002, 2019, 2020, 2021, 2025, 2026, 2030, 2041)
        ]
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            git(repo, "init", "-q", "-b", "main")
            for rel in files:
                (repo / rel).parent.mkdir(parents=True, exist_ok=True)
                (repo / rel).write_text("x")
            git(repo, "add", "-A")
            git(repo, "commit", "-q", "-m", "seed")
            git(repo, "sparse-checkout", "init", "--no-cone")
            (repo / ".git" / "info" / "sparse-checkout").write_text("\n".join(profile()) + "\n")
            git(repo, "checkout", "-q", "main")
            present = {rel for rel in files if (repo / rel).exists()}
            # regression: a new untracked League backup must be addable like rebuild_and_publish does
            (repo / "public" / "data" / "backup").mkdir(parents=True, exist_ok=True)
            (repo / "public" / "data" / "backup" / "League_new.json").write_text("n")
            add = subprocess.run(["git", "add", "-A", "--", "public/data"], cwd=repo, capture_output=True, text=True)
            self.assertEqual(0, add.returncode, add.stderr)
        absent = {
            "fantasy-management/f.md", "src/app/a.ts", "research/r.md",
            "public/assets/a.png", "public/docs/d.md", "data-source/market/m.json",
            "data-source/providers/espn/x.json", "data-source/providers/nflverse/y.csv",
        } | {
            f"data-source/nfl/{kind}/{year}/1.json"
            for kind in ("player-stats", "weekly-rosters") for year in (1999, 2002, 2019, 2020)
        }
        self.assertEqual(set(files) - absent, present)
        self.assertTrue(re.search(r"2041", " ".join(sorted(present))))  # future seasons stay included


if __name__ == "__main__":
    unittest.main()
