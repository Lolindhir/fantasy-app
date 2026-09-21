from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "operations_consumer_activity.py"
spec = importlib.util.spec_from_file_location("operations_consumer_activity", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


class OperationsConsumerActivityTests(unittest.TestCase):
    @staticmethod
    def policy():
        return {
            "modules": [
                {
                    "id": "free-agent-daily-monitoring",
                    "default_relevance": "required",
                    "phase_policy": {
                        "pre_regular_season": "required",
                        "regular_season": "required",
                        "postseason": "inactive",
                        "post_regular_season": "inactive",
                    },
                },
                {
                    "id": "kicker-daily-monitoring",
                    "default_relevance": "secondary",
                    "phase_policy": {
                        "pre_regular_season": "secondary",
                        "regular_season": "required",
                        "postseason": "inactive",
                        "post_regular_season": "inactive",
                    },
                },
            ]
        }

    def test_regular_season_requires_both_daily_modules(self):
        result = module.resolve_consumer_activity(
            self.policy(),
            phase="regular_season",
        )
        self.assertEqual(
            ["free-agent-daily-monitoring", "kicker-daily-monitoring"],
            result["required_module_ids"],
        )
        self.assertEqual([], result["inactive_module_ids"])

    def test_pre_regular_kicker_is_secondary_without_disabling_free_agent_monitoring(self):
        result = module.resolve_consumer_activity(
            self.policy(),
            phase="pre_regular_season",
        )
        self.assertEqual(["free-agent-daily-monitoring"], result["required_module_ids"])
        self.assertEqual(["kicker-daily-monitoring"], result["secondary_module_ids"])

    def test_postseason_daily_modules_are_inactive(self):
        result = module.resolve_consumer_activity(
            self.policy(),
            phase="postseason",
        )
        self.assertEqual(
            ["free-agent-daily-monitoring", "kicker-daily-monitoring"],
            result["inactive_module_ids"],
        )
        self.assertTrue(all(not item["active"] for item in result["modules"]))

    def test_inactive_module_becomes_explicit_inactive_by_policy(self):
        resolved = module.resolve_consumer_activity(
            self.policy(),
            phase="postseason",
        )
        runtime = module.apply_freshness_readiness(
            resolved,
            freshness_status="degraded",
            monitoring_allowed=True,
            no_event_conclusion_allowed=False,
        )
        for item in runtime["modules"]:
            self.assertEqual("inactive_by_policy", item["runtime_status"])
            self.assertFalse(item["execution_allowed"])
            self.assertIsNone(item["no_event_conclusion_allowed"])

    def test_active_module_keeps_degraded_freshness_semantics(self):
        resolved = module.resolve_consumer_activity(
            self.policy(),
            phase="regular_season",
        )
        runtime = module.apply_freshness_readiness(
            resolved,
            freshness_status="degraded",
            monitoring_allowed=True,
            no_event_conclusion_allowed=False,
        )
        self.assertTrue(all(item["execution_allowed"] for item in runtime["modules"]))
        self.assertTrue(all(item["runtime_status"] == "active_degraded" for item in runtime["modules"]))
        self.assertTrue(all(item["no_event_conclusion_allowed"] is False for item in runtime["modules"]))

    def test_unknown_phase_policy_fails_closed(self):
        policy = self.policy()
        policy["modules"][0]["phase_policy"]["training_camp"] = "required"
        with self.assertRaises(module.ConsumerActivityPolicyError):
            module.resolve_consumer_activity(policy, phase="regular_season")


if __name__ == "__main__":
    unittest.main()
