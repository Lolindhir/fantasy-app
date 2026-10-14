from __future__ import annotations

import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
DEPLOY = ROOT / ".github" / "workflows" / "deploy.yml"

REQUIRED_PATHS = {"src/**", "public/**", "angular.json", "package.json", "package-lock.json", "deploy_action.ps1"}


def push_trigger() -> dict:
    data = yaml.safe_load(DEPLOY.read_text(encoding="utf-8"))
    triggers = data.get("on", data.get(True))
    return triggers["push"]


class DeployWorkflowPathFilterTests(unittest.TestCase):
    def test_push_uses_positive_path_filter(self) -> None:
        push = push_trigger()
        self.assertIn("paths", push, "deploy.yml needs a positive paths filter (Issue #944)")
        self.assertNotIn("paths-ignore", push)

    def test_build_inputs_and_data_trigger_deploy(self) -> None:
        paths = set(push_trigger()["paths"])
        self.assertTrue(REQUIRED_PATHS <= paths, f"missing: {sorted(REQUIRED_PATHS - paths)}")

    def test_source_data_roots_do_not_trigger_deploy(self) -> None:
        paths = push_trigger()["paths"]
        for root in ("data-source", "data-derived", "fantasy-management"):
            self.assertFalse(any(p.startswith(root) for p in paths), root)


if __name__ == "__main__":
    unittest.main()
