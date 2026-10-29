"""Regression guard for the scoped NFL Game Derived daily publisher (#1077)."""
from __future__ import annotations

import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


class NflGamesPublisherContractTests(unittest.TestCase):
    def test_only_full_source_sync_wakes_derived_publisher(self) -> None:
        workflow = yaml.safe_load(
            (ROOT / ".github/workflows/sync-nfl-source-data.yml").read_text(encoding="utf-8")
        )
        job = workflow["jobs"]["nfl_games_derived"]
        self.assertEqual(job["needs"], "sync")
        condition = job["if"]
        self.assertIn("needs.sync.result == 'success'", condition)
        self.assertIn("inputs.materialization_scope != 'game-finality'", condition)
        self.assertIn("!inputs.dataset", condition)
        self.assertEqual(job["timeout-minutes"], 20)

    def test_writer_uses_classified_rebuild_and_retry_and_only_nfl_games(self) -> None:
        workflow = yaml.safe_load(
            (ROOT / ".github/workflows/sync-nfl-source-data.yml").read_text(encoding="utf-8")
        )
        steps = workflow["jobs"]["nfl_games_derived"]["steps"]
        publisher = next(step["run"] for step in steps if step["name"].startswith("Rebuild and publish"))
        self.assertIn("tools/rebuild_and_publish.py", publisher)
        self.assertIn("--scope nfl-games", publisher)
        self.assertIn("--path data-derived/nfl-games", publisher)
        self.assertNotIn("--path data-source", publisher)
        self.assertNotIn("--path public/data", publisher)
        self.assertIn("tools/nfl_games_materialize.py --all-seasons --write", publisher)

        contract = yaml.safe_load(
            (ROOT / ".ai-context/manual/workflow-publication.yaml").read_text(encoding="utf-8")
        )
        self.assertEqual(contract["writers"][".github/workflows/sync-nfl-source-data.yml"],
                         "rebuild-and-retry")

    def test_existing_shared_scheduler_keeps_original_cadence(self) -> None:
        import json
        config = json.loads(
            (ROOT / ".github/workflow-schedules.json").read_text(encoding="utf-8")
        )
        targets = {target["id"]: target for target in config["targets"]}
        self.assertEqual(targets["nfl-source"]["cron"], ["0 4 * * *"])
        self.assertEqual(targets["nfl-live"]["mode"], "game-window")
        self.assertNotIn("nfl-games", targets)

    def test_scope_is_recognized_by_generated_commit_helper(self) -> None:
        helper = (ROOT / ".github/scripts/Invoke-GeneratedDataCommit.ps1").read_text(encoding="utf-8")
        self.assertIn('"nfl-games"', helper)
        self.assertIn('^data-derived/nfl-games/', helper)


if __name__ == "__main__":
    unittest.main()
