"""Workflow Health Snapshot: the sparse/blobless checkout hides no input and keeps the state-branch publish working (Issue #1263, G5 E6).

The profile is parsed from the workflow and applied with real git in a throw-away repository. The publish step's
git mechanics (fetch the state branch, switch, copy, add, commit, push) are run in a sparse blobless clone, for an
existing and a not yet existing state branch.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "workflow-health-snapshot.yml"

FILES = [
    "AGENTS.md", "tools/build_workflow_health_snapshot.py", "tools/tests/test_build_workflow_health_snapshot.py",
    ".ai-context/manual/workflow-monitoring.yaml", ".ai-context/manual/domain.yaml",
    ".github/workflow-schedules.json", ".github/workflows/a.yml", ".github/workflows/b.yaml",
    "data-source/nfl/player-stats/2026/1.json", "data-derived/player-valuation/a.json",
    "public/data/League.json", "src/app/a.ts", "fantasy-management/f.md",
]
NEEDED = [
    "tools/build_workflow_health_snapshot.py", "tools/tests/test_build_workflow_health_snapshot.py",
    ".ai-context/manual/workflow-monitoring.yaml", ".github/workflow-schedules.json",
    ".github/workflows/a.yml", ".github/workflows/b.yaml",
]
ABSENT = [
    "data-source/nfl/player-stats/2026/1.json", "data-derived/player-valuation/a.json", "public/data/League.json",
    "src/app/a.ts", "fantasy-management/f.md", ".ai-context/manual/domain.yaml",
]


def steps() -> list[dict]:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]["snapshot"]["steps"]


def sparse_step() -> dict:
    return next(s for s in steps() if "sparse, blobless" in str(s.get("name", "")))


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


class SnapshotSparseProfileTest(unittest.TestCase):
    def test_checkout_binding_and_fallback(self) -> None:
        names = [str(s.get("name")) for s in steps()]
        self.assertNotIn("Checkout main", names)
        step = sparse_step()["with"]
        self.assertEqual("main", step["ref"])
        self.assertEqual(1, step["fetch-depth"])
        verify = next(s for s in steps() if "Verify sparse inputs" in str(s.get("name", "")))
        self.assertIn("git sparse-checkout disable", verify["run"])
        self.assertLess(names.index(sparse_step()["name"]), names.index(verify["name"]))
        self.assertLess(names.index(verify["name"]), names.index("Test snapshot logic"))
        publish = next(s for s in steps() if "Publish snapshot" in str(s.get("name", "")))
        self.assertIn("git add workflow-health.json", publish["run"])
        self.assertIn("workflow-health-state", publish["run"])

    def test_profile_contains_inputs_and_state_file_but_no_data_trees(self) -> None:
        prof = profile()
        for required in ("/.github/", "/tools/", "/.ai-context/manual/workflow-monitoring.yaml", "/workflow-health.json"):
            self.assertIn(required, prof)
        for entry in prof:
            for bad in ("data-source", "data-derived", "public", "src", "fantasy-management"):
                self.assertNotIn(bad, entry)

    def test_profile_applied_by_git_keeps_all_inputs(self) -> None:
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
        for rel in NEEDED:
            self.assertIn(rel, present)
        for rel in ABSENT:
            self.assertNotIn(rel, present)

    def test_publish_mechanics_in_a_sparse_blobless_clone(self) -> None:
        for state_branch_exists in (True, False):
            with self.subTest(state_branch_exists=state_branch_exists), tempfile.TemporaryDirectory() as tmp:
                base = Path(tmp)
                seed = base / "seed"
                seed.mkdir()
                git(seed, "init", "-q", "-b", "main")
                for rel in FILES:
                    (seed / rel).parent.mkdir(parents=True, exist_ok=True)
                    (seed / rel).write_text("x")
                git(seed, "add", "-A")
                git(seed, "commit", "-q", "-m", "seed")
                if state_branch_exists:
                    git(seed, "switch", "-q", "--orphan", "workflow-health-state")
                    git(seed, "rm", "-rfq", ".", check=False)
                    (seed / "workflow-health.json").write_text("{}")
                    git(seed, "add", "workflow-health.json")
                    git(seed, "commit", "-q", "-m", "state")
                    git(seed, "switch", "-q", "main")
                origin = base / "origin.git"
                subprocess.run(["git", "clone", "-q", "--bare", str(seed), str(origin)], check=True)
                for key, value in (("uploadpack.allowFilter", "true"), ("uploadpack.allowAnySHA1InWant", "true")):
                    git(origin, "config", key, value)
                url = f"file://{origin}"
                clone = base / "clone"
                subprocess.run(["git", "clone", "-q", "--filter=blob:none", "--no-checkout", "--depth", "1",
                                "--branch", "main", url, str(clone)], check=True)
                git(clone, "sparse-checkout", "init", "--no-cone")
                (clone / ".git" / "info" / "sparse-checkout").write_text("\n".join(profile()) + "\n")
                git(clone, "checkout", "-q", "main")

                # the publish step of the workflow
                fetched = git(clone, "fetch", "--depth=1", "origin",
                              "workflow-health-state:refs/remotes/origin/workflow-health-state", check=False)
                if fetched.returncode == 0:
                    git(clone, "switch", "-q", "-C", "workflow-health-state", "origin/workflow-health-state")
                else:
                    git(clone, "switch", "-q", "--orphan", "workflow-health-state")
                    git(clone, "rm", "-rfq", ".", check=False)
                self.assertEqual(state_branch_exists, fetched.returncode == 0)
                (clone / "workflow-health.json").write_text('{"v": 1}')
                added = git(clone, "add", "workflow-health.json", check=False)
                self.assertEqual(0, added.returncode, added.stderr)
                git(clone, "commit", "-q", "-m", "snapshot")
                pushed = git(clone, "push", url, "HEAD:workflow-health-state", check=False)
                self.assertEqual(0, pushed.returncode, pushed.stderr)
                shown = git(origin, "show", "workflow-health-state:workflow-health.json").stdout
                self.assertEqual('{"v": 1}', shown)


if __name__ == "__main__":
    unittest.main()
