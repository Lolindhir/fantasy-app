from __future__ import annotations

import re
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"
CONTRACT = ROOT / ".ai-context" / "manual" / "workflow-publication.yaml"

REBUILD_HELPER = "tools/rebuild_and_publish.py"
REBASE_HELPER = "tools/publish_generated_commit.py"

REBUILD_WRITERS = {
    "update-league.yml",
    "update-players.yml",
    "update-games.yml",
    "update-drafts.yml",
    "update-transactions.yml",
    "update-standings.yml",
    "update-teams.yml",
    "update-past-seasons-index.yml",
    "clean-backups.yml",
}

WORKFLOW_LOCAL_REBUILD_WRITERS = {
    "sync-nfl-source-data.yml",
    "sync-league-source-data.yml",
    "materialize-fantasy-operations-inputs.yml",
}

REBASE_WRITERS = {
    "update-fantasypros-rankings.yml",
    "update-fantasycalc-rankings.yml",
    "update-fantasy-football-calculator-adp.yml",
    "update-fftoday-projections.yml",
    "update-cbs-sports-projections.yml",
    "update-sleeper-trending.yml",
}

BRANCH_PUBLICATION_PATTERNS = (
    re.compile(r"\bgit\s+push\b"),
    re.compile(r"\bgit\s+update-ref\b"),
    re.compile(r"tools/rebuild_and_publish\.py"),
    re.compile(r"tools/publish_generated_commit\.py"),
    re.compile(r"git-auto-commit-action", re.IGNORECASE),
)


def load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise AssertionError(f"Expected mapping in {path}")
    return data


def workflow_paths() -> list[Path]:
    return sorted({*WORKFLOWS.glob("*.yml"), *WORKFLOWS.glob("*.yaml")})


def permission_grants_contents_write(permissions: object) -> bool:
    if permissions == "write-all":
        return True
    return isinstance(permissions, dict) and permissions.get("contents") == "write"


def requests_contents_write(workflow: dict) -> bool:
    if permission_grants_contents_write(workflow.get("permissions")):
        return True

    jobs = workflow.get("jobs") or {}
    if not isinstance(jobs, dict):
        return False

    return any(
        isinstance(job, dict) and permission_grants_contents_write(job.get("permissions"))
        for job in jobs.values()
    )


def contains_branch_publication_behavior(text: str) -> bool:
    return any(pattern.search(text) for pattern in BRANCH_PUBLICATION_PATTERNS)


def workflow_requires_classification(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    workflow = yaml.safe_load(text)
    if not isinstance(workflow, dict):
        raise AssertionError(f"Expected workflow mapping in {path}")
    return requests_contents_write(workflow) or contains_branch_publication_behavior(text)


class WorkflowPublicationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        contract = load_yaml(CONTRACT)
        cls.classes = set((contract.get("classes") or {}).keys())
        cls.classifications = contract.get("writers") or {}
        if not isinstance(cls.classifications, dict):
            raise AssertionError("workflow-publication.yaml writers must be a mapping")

    def read(self, name: str) -> str:
        return (WORKFLOWS / name).read_text(encoding="utf-8")

    def test_all_write_capable_or_publishing_workflows_are_classified(self) -> None:
        required = {
            path.relative_to(ROOT).as_posix()
            for path in workflow_paths()
            if workflow_requires_classification(path)
        }
        classified = set(self.classifications)
        missing = sorted(required - classified)
        self.assertEqual(
            missing,
            [],
            "Workflows with contents write permission or branch-publication behavior "
            "must be classified in .ai-context/manual/workflow-publication.yaml",
        )

    def test_classified_workflow_paths_exist_and_use_declared_classes(self) -> None:
        stale: list[str] = []
        invalid_classes: list[str] = []
        for relative_path, class_name in sorted(self.classifications.items()):
            if not (ROOT / relative_path).is_file():
                stale.append(relative_path)
            if class_name not in self.classes:
                invalid_classes.append(f"{relative_path}: {class_name}")

        self.assertEqual(stale, [], "Publication contract contains stale workflow paths")
        self.assertEqual(
            invalid_classes,
            [],
            "Publication contract contains workflow classifications with unknown classes",
        )

    def test_non_branch_writers_do_not_publish_repository_branches(self) -> None:
        offenders: list[str] = []
        for relative_path, class_name in sorted(self.classifications.items()):
            if class_name != "non-branch-writer":
                continue
            text = (ROOT / relative_path).read_text(encoding="utf-8")
            if contains_branch_publication_behavior(text):
                offenders.append(relative_path)
        self.assertEqual(
            offenders,
            [],
            "Workflows classified non-branch-writer contain branch-publication behavior",
        )

    def test_app_and_maintenance_writers_use_shared_rebuild_helper(self) -> None:
        for name in sorted(REBUILD_WRITERS):
            with self.subTest(workflow=name):
                text = self.read(name)
                self.assertIn(REBUILD_HELPER, text)
                self.assertNotIn("git push", text)
                self.assertIn("contents: write", text)
                self.assertNotIn("pages: write", text)
                self.assertNotIn("id-token: write", text)

    def test_self_contained_fm_writers_use_rebase_helper(self) -> None:
        for name in sorted(REBASE_WRITERS):
            with self.subTest(workflow=name):
                self.assertIn(REBASE_HELPER, self.read(name))

    def test_workflow_local_rebuild_writers_have_retry_and_reset_contract(self) -> None:
        for name in sorted(WORKFLOW_LOCAL_REBUILD_WRITERS):
            with self.subTest(workflow=name):
                text = self.read(name)
                self.assertIn("git fetch", text)
                self.assertIn("git reset --hard", text)
                self.assertTrue(
                    "max_attempts=" in text or "for attempt in 1 2 3" in text,
                    f"{name} must have a bounded rebuild retry loop",
                )

    def test_no_known_app_writer_has_naked_head_main_push(self) -> None:
        for name in sorted(REBUILD_WRITERS):
            with self.subTest(workflow=name):
                self.assertNotIn("HEAD:main", self.read(name))


if __name__ == "__main__":
    unittest.main()
