"""Static activation contracts for the classified Odds observer/Source delegation (#471)."""
import json
from pathlib import Path
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[2]


class OddsRefreshActivationContractTests(unittest.TestCase):
    def test_workflow_only_writes_isolated_state_and_delegates_source(self):
        text = (ROOT / ".github/workflows/odds-refresh.yml").read_text(encoding="utf-8")
        doc = yaml.safe_load(text)
        self.assertEqual({"observe", "publish_source"}, set(doc["jobs"]))
        self.assertIn("scheduler-nfl-odds-refresh", text)
        self.assertNotIn("schedule:", text)
        self.assertIn("cancel-in-progress: false", text)
        observer = doc["jobs"]["observe"]
        self.assertEqual("main", observer["steps"][0]["with"]["ref"])
        self.assertEqual("false", str(observer["steps"][0]["with"]["persist-credentials"]).lower())
        run = observer["steps"][-1]["run"]
        self.assertIn("odds_observation.py", run)
        self.assertIn("odds_state_publish.py", run)
        self.assertIn("odds-refresh-state", run)
        self.assertIn("--state-input", run)
        self.assertIn("--bootstrap", run)
        self.assertNotIn("git push", text)
        self.assertNotIn("rebuild_and_publish.py", text)
        source = doc["jobs"]["publish_source"]
        self.assertEqual("./.github/workflows/sync-nfl-source-data.yml", source["uses"])
        self.assertEqual("nflverse.schedule-odds", source["with"]["dataset"])
        # The registry declares this as one fixed games.csv origin: passing a
        # Source --season filter would fail closed before acquisition.
        self.assertNotIn("season", source["with"])
        self.assertEqual("schedule-odds", source["with"]["materialization_scope"])
        self.assertIn("needs.observe.outputs.publish == 'true'", source["if"])

    def test_producer_writer_guard_and_derived_after_success(self):
        text = (ROOT / ".github/workflows/sync-nfl-source-data.yml").read_text()
        derived = text.split("  nfl_games_derived:", 1)[1]
        self.assertIn("needs.sync.result == 'success'", derived)
        self.assertIn("inputs.dataset == 'nflverse.schedule-odds'", derived)
        self.assertIn("inputs.materialization_scope != 'game-finality'", derived)
        self.assertIn("tools/rebuild_and_publish.py", derived)
        self.assertIn("--path data-derived/nfl-games", derived)

    def test_scheduler_window_and_monitoring_classification(self):
        config = json.loads((ROOT / ".github/workflow-schedules.json").read_text())
        matches = [t for t in config["targets"] if t["id"] == "nfl-odds-refresh"]
        self.assertEqual(1, len(matches))
        target = matches[0]
        self.assertEqual("odds-refresh.yml", target["workflow"])
        self.assertEqual("productive", target["profile"])
        self.assertEqual("game-window", target["mode"])
        self.assertEqual(["*/10 * * * *"], target["cron"])
        self.assertEqual(2880, target["gameWindow"]["preKickoffMinutes"])
        publication = (ROOT / ".ai-context/manual/workflow-publication.yaml").read_text()
        monitoring = (ROOT / ".ai-context/manual/workflow-monitoring.yaml").read_text()
        self.assertIn(".github/workflows/odds-refresh.yml: isolated-branch", publication)
        self.assertIn(".github/workflows/odds-refresh.yml:", monitoring)

    def test_registered_fast_market_suite(self):
        inventory = json.loads((ROOT / ".github/ci-test-inventory.json").read_text())
        records = [r for r in inventory["tests"] if r["path"] == "tools/tests/test_odds_refresh_activation.py"]
        self.assertEqual(1, len(records))
        self.assertEqual("fast", records[0]["tier"])
        self.assertEqual(["market-restore"], records[0]["fastGroups"])
        self.assertEqual("build", records[0]["currentPrCoverage"])


if __name__ == "__main__":
    unittest.main()
