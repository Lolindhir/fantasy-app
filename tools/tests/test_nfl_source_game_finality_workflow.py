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

    def test_canonical_publish_rebases_only_when_materialization_inputs_unchanged(self) -> None:
        source = (WORKFLOWS / "sync-nfl-source-data.yml").read_text(encoding="utf-8")
        self.assertIn("publish_canonical_commit()", source)
        self.assertIn("materialize_input_pathspecs=(", source)
        for path in (
            "source-data/providers",
            "source-data/nfl",
            "public/data/Players.json",
            "public/data/Metadata.json",
            "public/data/League.json",
            "tools",
        ):
            self.assertIn(f"            {path}\n", source)
        self.assertIn('git diff --quiet "$base_sha" origin/main -- "${materialize_input_pathspecs[@]}"', source)
        self.assertIn("git rebase origin/main", source)
        self.assertIn("if publish_canonical_commit; then", source)
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

    def test_repo_state_audit_runs_after_materialization_not_in_pre_gate(self) -> None:
        # Issue #814 / ADR-039: the repo-state identity audit fails closed while
        # persisted identities lag behind Players.json, which the sync repairs.
        source = (WORKFLOWS / "sync-nfl-source-data.yml").read_text(encoding="utf-8")
        skip = "NFL_SOURCE_SYNC_SKIP_REPO_STATE_AUDIT=1"
        self.assertEqual(source.count(skip), 1)
        self.assertLess(
            source.index(skip),
            source.index("- name: Sync, validate and publish NFL source data"),
        )
        self.assertNotIn("NFL_SOURCE_SYNC_SKIP_REPO_STATE_AUDIT:", source)

        audit_cmd = (
            "python -m unittest "
            "tools.tests.test_nfl_source_app_espn_identity_bridge_repository -v"
        )
        self.assertEqual(source.count(audit_cmd), 1)
        audit_at = source.index(audit_cmd)
        self.assertGreater(audit_at, source.index("Second idempotency check (attempt"))
        self.assertLess(audit_at, source.index("python tools/nfl_source_data.py audit"))
        self.assertLess(audit_at, source.index("git add -- source-data\n"))
        section = source[source.rindex('if [[ "$materialization_scope" == "full" ]]; then', 0, audit_at):audit_at]
        self.assertIn("post_audit_log", section)
        self.assertIn('write_failure_diagnostic "post-materialize-audit"', source)
        self.assertIn("Post-materialization repo-state audit (attempt", source)

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
