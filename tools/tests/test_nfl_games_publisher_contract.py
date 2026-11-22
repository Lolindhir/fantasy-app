"""Regression guard for conditional full-Source/scoped-Odds NFL Game publishing (#1077)."""
from __future__ import annotations

import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


class NflGamesPublisherContractTests(unittest.TestCase):
    def test_full_source_and_scoped_odds_wake_derived_publisher(self) -> None:
        workflow = yaml.safe_load(
            (ROOT / ".github/workflows/sync-nfl-source-data.yml").read_text(encoding="utf-8")
        )
        job = workflow["jobs"]["nfl_games_derived"]
        self.assertEqual(job["needs"], "sync")
        condition = job["if"]
        self.assertIn("needs.sync.result == 'success'", condition)
        self.assertIn("inputs.materialization_scope != 'game-finality'", condition)
        self.assertIn("!inputs.dataset", condition)
        self.assertIn("inputs.dataset == 'nflverse.schedule-odds'", condition)
        self.assertEqual(job["timeout-minutes"], 90)

        odds = yaml.safe_load(
            (ROOT / ".github/workflows/odds-refresh.yml").read_text(encoding="utf-8")
        )
        delegated = odds["jobs"]["publish_source"]
        self.assertEqual("./.github/workflows/sync-nfl-source-data.yml", delegated["uses"])
        self.assertEqual("nflverse.schedule-odds", delegated["with"]["dataset"])
        self.assertEqual("schedule-odds", delegated["with"]["materialization_scope"])

    def test_contract_and_operator_summary_match_conditional_scope(self) -> None:
        contract = yaml.safe_load(
            (ROOT / ".ai-context/manual/nfl-games.yaml").read_text(encoding="utf-8")
        )
        self.assertIn("finality", contract["invalidation"])
        self.assertIn("Moneyline", contract["ignoreForThisProduct"])
        operation = contract["operation"]
        self.assertEqual("full-source-or-scoped-schedule-odds", operation["sourceTrigger"])
        self.assertIn("unrelated-targeted-NFL-source-dataset-refresh", operation["excludedTriggers"])
        self.assertIn("nfl-live-game-finality", operation["excludedTriggers"])
        self.assertIn("targeted", operation["publication"])
        self.assertIn("nflverse.schedule-odds", operation["publication"])
        workflow = (ROOT / ".github/workflows/sync-nfl-source-data.yml").read_text(encoding="utf-8")
        self.assertIn("full NFL Source sync or scoped schedule-odds refresh", workflow)
        self.assertNotIn("successful full NFL Source sync only", workflow)
        producer = (ROOT / "tools/nfl_games_materialize.py").read_text(encoding="utf-8")
        self.assertIn("Read-only by default; --write is a deliberate opt-in used by the dependent", producer)
        self.assertNotIn("NOT wired into a", producer)

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

    def test_approved_detail_publisher_reuses_owner_and_weekly_full_source(self) -> None:
        workflow = yaml.safe_load(
            (ROOT / ".github/workflows/sync-nfl-source-data.yml").read_text(encoding="utf-8")
        )
        steps = workflow["jobs"]["nfl_games_derived"]["steps"]
        current = next(step for step in steps
                       if step["name"] == "Rebuild and publish current-season NFL GameDetails")
        historical = next(step for step in steps
                          if step["name"] == "Reconcile and publish historical NFL GameDetails")
        decision = next(step for step in steps
                        if step["name"] == "Decide historical NFL GameDetail replay")
        cache = next(step for step in steps
                     if step["name"] == "Restore reusable historical original-PBP archive cache")
        for step in (current, historical):
            self.assertIn("tools/rebuild_and_publish.py", step["run"])
            self.assertIn("--scope nfl-games", step["run"])
            self.assertIn("--path data-derived/nfl-games/details", step["run"])
            self.assertNotIn("--path public/data", step["run"])
            self.assertNotIn("--path data-source", step["run"])
            self.assertIn("--write", step["run"])
        self.assertIn("tools/nfl_game_details_materialize.py --current-season --write",
                      current["run"])
        self.assertIn("--historical-seasons --write", historical["run"])
        self.assertIn("steps.historical_pbp_due.outputs.run", historical["if"])
        self.assertIn("!inputs.dataset", decision["if"])
        self.assertIn("inputs.materialization_scope == 'full'", decision["if"])
        self.assertIn("TZ=Europe/Berlin date +%u", decision["run"])
        self.assertIn("--historical-rebuild-needed", decision["run"])
        self.assertIn("weekly-Monday", decision["run"])
        self.assertIn("actions/cache@v4", cache["uses"])
        self.assertIn("nfl-pbp-history-original-v1-", cache["with"]["key"])
        self.assertIn("tools/nfl_game_details_materialize.py",
                      workflow[True]["push"]["paths"])
        self.assertEqual(workflow["jobs"]["nfl_games_derived"]["timeout-minutes"], 90)
        contract = yaml.safe_load(
            (ROOT / ".ai-context/manual/nfl-games.yaml").read_text(encoding="utf-8")
        )
        detail = contract["futureGameDetailDirection"]["coreDetailV1"]
        self.assertEqual(detail["publication"]["writeScope"],
                         "data-derived/nfl-games/details/**")
        self.assertEqual(detail["publication"]["historicalAuditDay"], "Monday")
        self.assertEqual(detail["publication"]["noSeparateScheduler"], True)
        v2 = contract["futureGameDetailDirection"]["gameDetailV2DynamicPublication"]
        self.assertEqual(v2["targetScope"], "all-canonical-indexed-seasons-no-hardcoded-years")
        self.assertEqual(v2["owner"], "existing-nfl-games")
        self.assertIn("metadata-<season>.json", v2["sourceDiscovery"])

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
