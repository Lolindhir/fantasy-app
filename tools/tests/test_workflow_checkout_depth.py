"""Full-history checkouts (fetch-depth: 0) in workflows must be listed with a reason (Issue #1156).

A depth-0 checkout costs 4 to 5 minutes per job. The race-safe publishers
(tools/rebuild_and_publish.py) fetch the branch tip themselves and need no history, so a full
history is only justified where a step really reads it. Every remaining depth-0 checkout is
listed below; a new one fails this test until it is converted or listed with a reason.
Stale entries fail too, so the list shrinks as workflows are converted.
"""
from __future__ import annotations

import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"

# (workflow file, job id) -> reason
FULL_HISTORY_ALLOWED = {
    ("source-data-readiness.yml", "audit"): "tools/source_data_readiness.py reads git log per file (group D)",
    ("sync-nfl-source-data.yml", "sync"): "full scope uses HEAD~1, git diff and rebase (group D); schedule-odds/game-finality are shallow",
}


def _is_full_history(step: dict) -> bool:
    if not str(step.get("uses", "")).startswith("actions/checkout@"):
        return False
    depth = (step.get("with") or {}).get("fetch-depth")
    if depth is None:
        return False  # action default is depth 1
    text = str(depth).strip()
    if text == "0":
        return True
    # expression such as "${{ cond && 1 || 0 }}": the 0 branch is a full-history case
    return text.startswith("${{") and text.rstrip("}").strip().endswith("|| 0")


def full_history_jobs() -> set[tuple[str, str]]:
    found = set()
    for path in sorted(WORKFLOWS.glob("*.y*ml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for job_id, job in (data.get("jobs") or {}).items():
            if any(_is_full_history(step) for step in (job or {}).get("steps") or []):
                found.add((path.name, job_id))
    return found


class WorkflowCheckoutDepthTest(unittest.TestCase):
    def test_full_history_checkouts_are_listed_with_reason(self) -> None:
        unlisted = full_history_jobs() - set(FULL_HISTORY_ALLOWED)
        self.assertEqual(
            set(), unlisted,
            "fetch-depth: 0 needs a reason in FULL_HISTORY_ALLOWED or a shallow checkout (Issue #1156)",
        )

    def test_allow_list_has_no_stale_entries(self) -> None:
        stale = set(FULL_HISTORY_ALLOWED) - full_history_jobs()
        self.assertEqual(set(), stale, "converted or removed checkouts must leave the allow list")

    def test_reasons_are_not_empty(self) -> None:
        for key, reason in FULL_HISTORY_ALLOWED.items():
            self.assertTrue(reason.strip(), key)

    def test_detector_flags_expression_and_zero(self) -> None:
        checkout = "actions/checkout@v4"
        self.assertTrue(_is_full_history({"uses": checkout, "with": {"fetch-depth": 0}}))
        self.assertTrue(_is_full_history({"uses": checkout, "with": {"fetch-depth": "${{ x == 'a' && 1 || 0 }}"}}))
        self.assertFalse(_is_full_history({"uses": checkout, "with": {"fetch-depth": 1}}))
        self.assertFalse(_is_full_history({"uses": checkout}))
        self.assertFalse(_is_full_history({"uses": "actions/setup-python@v7", "with": {"fetch-depth": 0}}))


if __name__ == "__main__":
    unittest.main()
