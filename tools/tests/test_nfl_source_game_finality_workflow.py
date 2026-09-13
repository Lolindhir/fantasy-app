from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"


class GameFinalityWorkflowContractTests(unittest.TestCase):
    def test_finality_wrapper_selects_scoped_materialization(self) -> None:
        wrapper = (WORKFLOWS / "sync-nfl-game-finality.yml").read_text(encoding="utf-8")
        self.assertIn("dataset: nflverse.game-finality", wrapper)
        self.assertIn("materialization_scope: game-finality", wrapper)
        self.assertIn("actions: read", wrapper)

    def test_source_workflow_keeps_serialization_and_rebuild_retry(self) -> None:
        source = (WORKFLOWS / "sync-nfl-source-data.yml").read_text(encoding="utf-8")
        self.assertIn("group: nfl-source-data-sync", source)
        self.assertIn("cancel-in-progress: false", source)
        self.assertIn("max_attempts=3", source)
        self.assertIn("git fetch origin main", source)
        self.assertIn("git reset --hard origin/main", source)
        self.assertNotIn("--force-with-lease", source)
        self.assertNotIn("git push --force", source)

    def test_scoped_workflow_has_explicit_write_guard_and_no_full_audit(self) -> None:
        source = (WORKFLOWS / "sync-nfl-source-data.yml").read_text(encoding="utf-8")
        self.assertIn("assert_scoped_canonical_write_set", source)
        self.assertIn('source-data/nfl/game-finality/*', source)
        self.assertIn('materialize_args+=(--scope game-finality)', source)
        self.assertIn('if [[ "$materialization_scope" == "full" ]]; then', source)
        self.assertIn("python tools/nfl_source_data.py audit", source)
        self.assertIn("Full NFL audit: read/write disabled for scoped materialization", source)

    def test_scoped_workflow_uses_shallow_checkout_and_targeted_tests(self) -> None:
        source = (WORKFLOWS / "sync-nfl-source-data.yml").read_text(encoding="utf-8")
        self.assertIn("inputs.materialization_scope == 'game-finality' && 1 || 0", source)
        self.assertIn("python -m unittest tools.tests.test_nfl_source_game_finality_scope -v", source)
        self.assertIn('discover -s tools/tests -p "test_nfl_source*.py" -v', source)

    def test_scoped_workflow_emits_requested_observability(self) -> None:
        source = (WORKFLOWS / "sync-nfl-source-data.yml").read_text(encoding="utf-8")
        for marker in (
            "Queue before job start",
            "Checkout:",
            "Tests (",
            "Raw Fetch",
            "Scoped Materialization",
            "Second idempotency check",
            "Publication (attempt",
            "No-op reason",
            "Canonical write-set",
            "Scoped canonical files changed",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, source)


if __name__ == "__main__":
    unittest.main()
