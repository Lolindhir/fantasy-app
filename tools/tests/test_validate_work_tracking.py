import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "validate_work_tracking.py"
SPEC = importlib.util.spec_from_file_location("validate_work_tracking", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

CONTRACT = """\
version: 1
labelPolicy:
  unknownLabels: forbidden
scopePolicy:
  exclusionLabel: tracking:excluded
  excludedIssueAllowedLabels:
    - tracking:excluded
labels:
  tracking:
    cardinality: zero-or-one
    label: tracking:excluded
  priority:
    cardinalityByState:
      open: exactly-one
      closed: zero
    values:
      priority:p0: {}
      priority:p1: {}
      priority:p2: {}
      priority:p3: {}
      priority:p4: {}
  origin:
    cardinality: exactly-one
    values:
      origin:todo-migration: {}
      origin:user-request: {}
      origin:discovered: {}
      origin:automation: {}
  area:
    cardinality: one-or-more
    values:
      area:app: {}
      area:frontend: {}
      area:data: {}
      area:platform: {}
      area:fantasy-management: {}
      area:fantasy-operations: {}
      area:documentation: {}
  type:
    cardinality: exactly-one
    values:
      type:bug: {}
      type:feature: {}
      type:architecture: {}
      type:research: {}
      type:maintenance: {}
      type:migration: {}
  status:
    cardinalityByState:
      open: zero-or-one
      closed: zero
    values:
      status:analysis: {}
      status:ready: {}
      status:in-progress: {}
      status:review: {}
  blocked:
    cardinalityByState:
      open: zero-or-one
      closed: zero
    label: blocked
"""


def issue(number=1, state="open", labels=None, **extra):
    payload = {
        "number": number,
        "state": state,
        "labels": labels
        if labels is not None
        else [
            "priority:p2",
            "origin:discovered",
            "area:platform",
            "type:architecture",
        ],
    }
    payload.update(extra)
    return payload


class WorkTrackingValidatorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.contract_path = Path(self.tmp.name) / "work-tracking.yaml"
        self.contract_path.write_text(CONTRACT, encoding="utf-8")
        self.contract = MODULE.load_contract(self.contract_path)

    def tearDown(self):
        self.tmp.cleanup()

    def codes(self, payload):
        return [v.ruleCode for v in MODULE.validate_issue(payload, self.contract)]

    def test_valid_open_issue(self):
        self.assertEqual([], MODULE.validate_issue(issue(), self.contract))

    def test_missing_priority(self):
        payload = issue(labels=["origin:discovered", "area:platform", "type:architecture"])
        self.assertIn("label.priority.cardinality.open", self.codes(payload))

    def test_duplicate_priority(self):
        payload = issue(labels=["priority:p1", "priority:p2", "origin:discovered", "area:platform", "type:architecture"])
        self.assertIn("label.priority.cardinality.open", self.codes(payload))

    def test_invalid_priority_is_unknown_and_missing_valid_priority(self):
        payload = issue(labels=["priority:p9", "origin:discovered", "area:platform", "type:architecture"])
        codes = self.codes(payload)
        self.assertIn("label.unknown", codes)
        self.assertIn("label.priority.cardinality.open", codes)

    def test_missing_origin(self):
        payload = issue(labels=["priority:p2", "area:platform", "type:architecture"])
        self.assertIn("label.origin.cardinality.open", self.codes(payload))

    def test_duplicate_origin(self):
        payload = issue(labels=["priority:p2", "origin:discovered", "origin:user-request", "area:platform", "type:architecture"])
        self.assertIn("label.origin.cardinality.open", self.codes(payload))

    def test_missing_type(self):
        payload = issue(labels=["priority:p2", "origin:discovered", "area:platform"])
        self.assertIn("label.type.cardinality.open", self.codes(payload))

    def test_duplicate_type(self):
        payload = issue(labels=["priority:p2", "origin:discovered", "area:platform", "type:bug", "type:architecture"])
        self.assertIn("label.type.cardinality.open", self.codes(payload))

    def test_invalid_status_is_unknown(self):
        payload = issue(labels=["priority:p2", "origin:discovered", "area:platform", "type:architecture", "status:done"])
        self.assertIn("label.unknown", self.codes(payload))

    def test_multiple_status(self):
        payload = issue(labels=["priority:p2", "origin:discovered", "area:platform", "type:architecture", "status:analysis", "status:ready"])
        self.assertIn("label.status.cardinality.open", self.codes(payload))

    def test_missing_required_area(self):
        payload = issue(labels=["priority:p2", "origin:discovered", "type:architecture"])
        self.assertIn("label.area.cardinality.open", self.codes(payload))

    def test_multiple_areas_are_allowed(self):
        payload = issue(labels=["priority:p2", "origin:discovered", "area:data", "area:platform", "type:architecture"])
        self.assertEqual([], MODULE.validate_issue(payload, self.contract))

    def test_unknown_label(self):
        payload = issue(labels=["priority:p2", "origin:discovered", "area:platform", "type:architecture", "custom:surprise"])
        self.assertIn("label.unknown", self.codes(payload))

    def test_excluded_issue_is_valid_without_work_labels(self):
        payload = issue(state="closed", labels=["tracking:excluded"])
        self.assertEqual([], MODULE.validate_issue(payload, self.contract))

    def test_excluded_issue_with_work_label_is_rejected(self):
        payload = issue(state="closed", labels=["tracking:excluded", "area:platform"])
        violations = MODULE.validate_issue(payload, self.contract)
        self.assertEqual(["scope.excluded.labels"], [v.ruleCode for v in violations])
        self.assertEqual(["area:platform", "tracking:excluded"], violations[0].observed)

    def test_excluded_issue_with_unknown_label_is_rejected_by_scope(self):
        payload = issue(state="closed", labels=["tracking:excluded", "custom:surprise"])
        self.assertEqual(["scope.excluded.labels"], self.codes(payload))

    def test_closed_issue_requires_no_priority_and_keeps_durable_classification(self):
        payload = issue(state="closed", labels=["origin:todo-migration", "area:data", "type:architecture"])
        self.assertEqual([], MODULE.validate_issue(payload, self.contract))

    def test_closed_issue_with_stale_priority_status_and_blocked(self):
        payload = issue(state="closed", labels=["priority:p2", "origin:discovered", "area:platform", "type:architecture", "status:review", "blocked"])
        codes = self.codes(payload)
        self.assertIn("label.priority.cardinality.closed", codes)
        self.assertIn("label.status.cardinality.closed", codes)
        self.assertIn("label.blocked.cardinality.closed", codes)

    def test_closed_issue_still_requires_area(self):
        payload = issue(state="closed", labels=["origin:discovered", "type:architecture"])
        self.assertIn("label.area.cardinality.closed", self.codes(payload))

    def test_realistic_current_contract_shape(self):
        self.assertEqual(
            [],
            MODULE.validate_issue(
                issue(
                    labels=[
                        "priority:p1",
                        "origin:automation",
                        "area:fantasy-operations",
                        "area:data",
                        "type:maintenance",
                        "status:in-progress",
                        "blocked",
                    ]
                ),
                self.contract,
            ),
        )

    def test_machine_readable_violation_shape(self):
        checked, violations = MODULE.validate_issues([issue(labels=[])], self.contract)
        result = MODULE.result_payload(checked, violations)
        self.assertEqual(1, result["issuesChecked"])
        self.assertGreater(result["violationCount"], 0)
        violation = result["violations"][0]
        self.assertEqual(1, violation["issueNumber"])
        self.assertIn("ruleCode", violation)
        self.assertIn("rule", violation)
        self.assertIn("observed", violation)
        self.assertIn("expected", violation)

    def test_excluded_issue_is_still_counted_as_checked(self):
        checked, violations = MODULE.validate_issues(
            [issue(number=1, state="closed", labels=["tracking:excluded"])], self.contract
        )
        self.assertEqual(1, checked)
        self.assertEqual([], violations)

    def test_github_label_object_shape(self):
        payload = issue(labels=[
            {"name": "priority:p2"},
            {"name": "origin:discovered"},
            {"name": "area:platform"},
            {"name": "type:architecture"},
        ])
        self.assertEqual([], MODULE.validate_issue(payload, self.contract))

    def test_pull_requests_are_ignored(self):
        checked, violations = MODULE.validate_issues(
            [issue(number=1), issue(number=2, pull_request={"url": "example"})], self.contract
        )
        self.assertEqual(1, checked)
        self.assertEqual([], violations)

    def test_json_file_wrapper_shape(self):
        path = Path(self.tmp.name) / "issues.json"
        path.write_text(json.dumps({"issues": [issue()]}), encoding="utf-8")
        loaded = MODULE.load_issues_file(path)
        self.assertEqual(1, len(loaded))

    def test_contract_rejects_undocumented_exclusion_label(self):
        bad_contract = CONTRACT.replace("  tracking:\n    cardinality: zero-or-one\n    label: tracking:excluded\n", "")
        path = Path(self.tmp.name) / "bad-work-tracking.yaml"
        path.write_text(bad_contract, encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "exclusionLabel must also be documented"):
            MODULE.load_contract(path)


if __name__ == "__main__":
    unittest.main()
