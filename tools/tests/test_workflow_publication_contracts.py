from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"

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


class WorkflowPublicationContractTests(unittest.TestCase):
    def read(self, name: str) -> str:
        return (WORKFLOWS / name).read_text(encoding="utf-8")

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
                self.assertRegex(text, r"max_attempts=\d+")

    def test_no_known_app_writer_has_naked_head_main_push(self) -> None:
        for name in sorted(REBUILD_WRITERS):
            with self.subTest(workflow=name):
                self.assertNotIn("HEAD:main", self.read(name))


if __name__ == "__main__":
    unittest.main()
