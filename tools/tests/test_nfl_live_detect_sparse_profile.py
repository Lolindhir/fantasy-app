"""NFL Live detect job: sparse checkout gives the same decisions as a full checkout (Issue #1263, G5 AP3c).

The detect script is extracted from nfl-live.yml and executed against a local origin in a sparse/blobless
clone and in a complete clone for every decision branch (finality change, schedule change, no change, forced,
no base, unfetchable base). Outputs must be identical.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "nfl-live.yml"


def job() -> dict:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]["detect"]


def script() -> str:
    return next(s for s in job()["steps"] if s.get("id") == "detect")["run"]


def git(cwd: Path, *args: str) -> str:
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True, env=env).stdout.strip()


def commit(repo: Path, files: dict[str, str], message: str) -> str:
    for rel, content in files.items():
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message)
    return git(repo, "rev-parse", "HEAD")


def run_detect(clone: Path, base: str, force: str, out: Path) -> dict[str, str]:
    env = {**os.environ, "BASE": base, "FORCE": force, "GITHUB_OUTPUT": str(out), "GITHUB_STEP_SUMMARY": str(out) + ".summary"}
    subprocess.run(["bash", "-c", script()], cwd=clone, check=True, capture_output=True, text=True, env=env)
    return dict(line.split("=", 1) for line in out.read_text().splitlines() if "=" in line)


class NflLiveDetectSparseTest(unittest.TestCase):
    def test_profile_materializes_no_nfl_data(self) -> None:
        step = next(s for s in job()["steps"] if str(s.get("uses", "")).startswith("actions/checkout@"))
        self.assertEqual("blob:none", step["with"]["filter"])
        self.assertIs(False, step["with"]["sparse-checkout-cone-mode"])
        self.assertEqual("/.github/", step["with"]["sparse-checkout"].strip())

    def test_detection_is_identical_in_sparse_and_full_clones(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            origin = tmp_path / "origin"
            origin.mkdir()
            git(origin, "init", "-q", "-b", "main")
            git(origin, "config", "uploadpack.allowFilter", "true")
            git(origin, "config", "uploadpack.allowAnySHA1InWant", "true")
            base = commit(origin, {".github/x.yml": "a", "data-source/nfl/game-finality/2026.json": "1", "data-source/nfl/schedules/2026.json": "1", "data-source/nfl/other/a.json": "1"}, "base")
            commit(origin, {"data-source/nfl/game-finality/2026.json": "2"}, "finality")
            commit(origin, {"data-source/nfl/schedules/2026.json": "2"}, "schedule")
            other = commit(origin, {"data-source/nfl/other/a.json": "2"}, "other")
            head = other
            cases = {
                "both-changed": (base, "", None),
                "no-change": (head, "", None),
                "forced": (base, "true", None),
                "no-base": ("", "", None),
                "unfetchable-base": ("0" * 40, "", None),
            }
            for name, (case_base, force, _) in cases.items():
                results = {}
                for mode in ("sparse", "full"):
                    clone = tmp_path / f"{name}-{mode}"
                    args = ["clone", "-q", "--depth=1", "--no-tags", f"file://{origin}", str(clone)]
                    if mode == "sparse":
                        args[2:2] = ["--filter=blob:none", "--sparse", "--no-checkout"]
                    subprocess.run(["git", *args], check=True, capture_output=True)
                    if mode == "sparse":
                        git(clone, "sparse-checkout", "init", "--no-cone")
                        git(clone, "sparse-checkout", "set", "--no-cone", "/.github/")
                        git(clone, "checkout", "-q", "main")
                        self.assertFalse((clone / "data-source").exists())
                    else:
                        self.assertTrue((clone / "data-source").exists())
                    results[mode] = run_detect(clone, case_base, force, tmp_path / f"out-{name}-{mode}")
                self.assertEqual(results["full"], results["sparse"], name)
            def read(name: str) -> dict[str, str]:
                lines = (tmp_path / f"out-{name}-full").read_text().splitlines()
                return dict(line.split("=", 1) for line in lines if "=" in line)

            self.assertEqual({"finality_changed": "false", "schedule_changed": "false", "run_schedule": "false"}, read("no-change"))
            # base precedes finality and schedule commits: both are detected
            self.assertEqual({"finality_changed": "true", "schedule_changed": "true", "run_schedule": "true"}, read("both-changed"))


if __name__ == "__main__":
    unittest.main()
