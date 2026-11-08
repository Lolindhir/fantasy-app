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


class LeagueJobHasNoNodeDependencyTest(unittest.TestCase):
    """G5 AP4 (Issue #1263): the League Live league job needs no Node.js setup."""

    CHAIN_TOOLS = (
        "tools/rebuild_and_publish.py",
        "tools/league_live_derived_refresh.py",
        "tools/player_week_fantasy_refresh.py",
        "tools/matchup_context_app_publish.py",
        "tools/league_history_app_publish.py",
        "tools/weekly_recaps_app_publish.py",
        "tools/team_cap_outlook_app_publish.py",
        ".github/scripts/Invoke-GeneratedDataCommit.ps1",
    )

    def test_league_job_has_no_setup_node_and_chain_never_invokes_node(self) -> None:
        import re

        workflow = yaml.safe_load((ROOT / ".github" / "workflows" / "league-live.yml").read_text(encoding="utf-8"))
        uses = [str(step.get("uses", "")) for step in workflow["jobs"]["league"]["steps"]]
        self.assertFalse([item for item in uses if item.startswith("actions/setup-node")])
        sources = [ROOT / rel for rel in self.CHAIN_TOOLS]
        sources += [path for path in sorted((ROOT / "tools").rglob("*.py")) if "tests" not in path.parts]
        sources += sorted((ROOT / "public" / "requests").rglob("*.ps*1"))
        pattern = re.compile(r"\b(node|npm|npx)\b")
        offenders = [str(path.relative_to(ROOT)) for path in sources if pattern.search(path.read_text(encoding="utf-8"))]
        self.assertEqual([], offenders)


if __name__ == "__main__":
    unittest.main()


class SchedulerSparseCheckoutTest(unittest.TestCase):
    """G5 AP1 (Issue #1263): the scheduler job checks out only what it reads.

    The scheduler reads the scheduler modules, the schedule config and the canonical NFL
    schedule/finality partitions; state goes through the GitHub API. Every static require()
    of the scheduler module tree and every data root of nfl-game-window.cjs must be covered
    by the sparse profile, otherwise a later change would break the critical scheduler.
    """

    SCHEDULER_MODULES = (
        "run-workflow-scheduler-entry.cjs",
        "run-workflow-scheduler-runtime.cjs",
        "run-workflow-scheduler.cjs",
        "run-project-field-sync-scheduler.cjs",
        "run-workflow-scheduler-summary.cjs",
        "nfl-game-window.cjs",
    )

    def _checkout_step(self) -> dict:
        data = yaml.safe_load((WORKFLOWS / "scheduler.yml").read_text(encoding="utf-8"))
        steps = data["jobs"]["dispatch"]["steps"]
        return next(s for s in steps if str(s.get("uses", "")).startswith("actions/checkout@"))

    def test_checkout_is_sparse_and_blobless(self) -> None:
        with_ = self._checkout_step()["with"]
        self.assertEqual("blob:none", with_["filter"])
        self.assertIs(False, with_["sparse-checkout-cone-mode"])
        patterns = [p.strip() for p in with_["sparse-checkout"].splitlines() if p.strip()]
        self.assertEqual(
            [
                "/.github/workflow-schedules.json",
                "/tools/*.cjs",
                "/data-source/nfl/schedules/",
                "/data-source/nfl/game-finality/",
            ],
            patterns,
        )

    def test_scheduler_requires_stay_inside_sparse_profile(self) -> None:
        import re

        for name in self.SCHEDULER_MODULES:
            source = (ROOT / "tools" / name).read_text(encoding="utf-8")
            for target in re.findall(r"require\(\s*['\"]([^'\"]+)['\"]\s*\)", source):
                if target.startswith("node:"):
                    continue  # built-in module
                self.assertTrue(target.startswith("./") and target.endswith(".cjs"), f"{name} requires {target}")
                self.assertTrue((ROOT / "tools" / target[2:]).is_file(), f"{name}: {target} missing")
            # only the documented data roots and config may be read from the checkout
            for forbidden in ("data-meta", "data-derived", "public/data", "fantasy-management"):
                self.assertNotIn(forbidden, source, f"{name} reads {forbidden}, not in the sparse profile")
        window = (ROOT / "tools" / "nfl-game-window.cjs").read_text(encoding="utf-8")
        self.assertIn("scheduleDir: 'data-source/nfl'", window)
        self.assertIn("'schedules'", window)
        self.assertIn("'game-finality'", window)
        # no other scheduler module may read data-source
        for name in self.SCHEDULER_MODULES:
            if name != "nfl-game-window.cjs":
                self.assertNotIn("data-source", (ROOT / "tools" / name).read_text(encoding="utf-8"))

    def test_incomplete_sparse_profile_falls_back_to_complete_checkout(self) -> None:
        source = (WORKFLOWS / "scheduler.yml").read_text(encoding="utf-8")
        self.assertIn("git sparse-checkout disable", source)
        for module in self.SCHEDULER_MODULES:
            self.assertIn(f"tools/{module}", source)
