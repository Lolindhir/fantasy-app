"""Every rebuild_and_publish scope used in a workflow must exist in the commit helper ValidateSet."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class CommitHelperScopeTest(unittest.TestCase):
    def test_workflow_scopes_are_accepted_by_commit_helper(self):
        helper = (ROOT / ".github/scripts/Invoke-GeneratedDataCommit.ps1").read_text(encoding="utf-8")
        match = re.search(r"\[ValidateSet\((.*?)\)\]", helper, re.DOTALL)
        self.assertIsNotNone(match)
        allowed = set(re.findall(r'"([^"]+)"', match.group(1)))
        used = set()
        for wf in (ROOT / ".github/workflows").glob("*.y*ml"):
            for m in re.finditer(r"rebuild_and_publish\.py[^\n]*(?:\\\s*\n\s*)?(?:[^\n]*\n){0,3}?[^\n]*?--scope\s+([A-Za-z0-9_.-]+)", wf.read_text(encoding="utf-8")):
                used.add(m.group(1))
        self.assertIn("nfl-espn-schedule", used)
        missing = {s for s in used if s not in allowed and not s.startswith("$")}
        self.assertFalse(missing, f"scopes missing in commit helper: {sorted(missing)}")


if __name__ == "__main__":
    unittest.main()
