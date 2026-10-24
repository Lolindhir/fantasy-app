from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"


class GameFinalityWorkflowContractTests(unittest.TestCase):
    def test_finality_wrapper_selects_scoped_materialization(self) -> None:
        wrapper = (WORKFLOWS / "nfl-live.yml").read_text(encoding="utf-8")
        self.assertIn("dataset: nflverse.game-finality", wrapper)
        self.assertIn("materialization_scope: game-finality", wrapper)
        self.assertIn("actions: read", wrapper)

    def test_detect_and_schedule_jobs_use_shallow_checkout(self) -> None:
        live = (WORKFLOWS / "nfl-live.yml").read_text(encoding="utf-8")
        games = (WORKFLOWS / "update-games.yml").read_text(encoding="utf-8")
        self.assertNotIn("fetch-depth: 0", live)
        self.assertNotIn("fetch-depth: 0", games)
        # the shallow detect checkout must fetch the base commit explicitly and fall back conservatively
        self.assertIn('git fetch --no-tags --depth=1 origin "$BASE"', live)
        self.assertIn("could not be fetched; running conservatively", live)

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
            "data-source/registry.json",
            "data-source/providers/dynastyprocess",
            "data-source/providers/nflverse",
            "data-source/providers/sleeper/players",
            "data-source/nfl",
            "'data-source/leagues/*/manifest.json'",
            "tools",
        ):
            self.assertIn(f"            {path}\n", source)
        inputs = source.split("materialize_input_pathspecs=(")[1].split(")")[0]
        self.assertNotIn("public/data/Players.json", inputs)
        self.assertNotIn("public/data/Players_Relevant.json", inputs)
        self.assertNotIn("public/data/Metadata.json", inputs)
        self.assertNotIn("public/data/League.json", inputs)
        self.assertIn('git diff --quiet "$base_sha" origin/main -- "${materialize_input_pathspecs[@]}"', source)
        self.assertIn("git rebase origin/main", source)
        self.assertNotIn("            data-source/providers\n", source)
        self.assertNotIn("sleeper/leagues\n", source.split("materialize_input_pathspecs=(")[1].split(")")[0])
        self.assertIn("if publish_canonical_commit; then", source)
        self.assertNotIn("--force-with-lease", source)
        self.assertNotIn("git push --force", source)

    def test_scoped_workflow_has_explicit_write_guard_and_no_full_audit(self) -> None:
        source = (WORKFLOWS / "sync-nfl-source-data.yml").read_text(encoding="utf-8")
        self.assertIn("assert_scoped_canonical_write_set", source)
        self.assertIn('data-source/nfl/game-finality/*', source)
        self.assertIn('materialize_args+=(--scope game-finality)', source)
        self.assertIn('if [[ "$materialization_scope" == "full" ]]; then', source)
        self.assertIn("python tools/nfl_source_data.py audit", source)
        self.assertIn("Full NFL audit: read/write disabled for scoped materialization", source)

    def test_schedule_odds_scope_uses_existing_safe_publisher(self) -> None:
        source = (WORKFLOWS / "sync-nfl-source-data.yml").read_text(encoding="utf-8")
        odds = (WORKFLOWS / "odds-refresh.yml").read_text(encoding="utf-8")
        self.assertIn("materialization_scope: schedule-odds", odds)
        self.assertIn('if [[ "${DATASET:-}" != "nflverse.schedule-odds" ]]', source)
        self.assertIn("schedule-odds scope does not accept a season filter", source)
        self.assertIn("materialize_args+=(--scope schedule-odds)", source)
        self.assertIn('data-source/nfl/schedule-odds/*', source)
        self.assertIn('"oddsFilesChanged": 0', source)
        self.assertIn('"oddsChangedPaths": []', source)
        self.assertIn("data-source/providers/nflverse/schedules", source)
        self.assertIn("data-source/providers/nflverse/schedule-odds", source)
        self.assertIn("data-source/nfl/schedules", source)
        self.assertIn("data-source/nfl/schedule-odds", source)
        self.assertIn("inputs.materialization_scope != 'game-finality'", source)
        self.assertIn("data-derived/nfl-games", source)

    def test_schedule_odds_checkout_depth_is_an_isolated_pilot(self) -> None:
        source = (WORKFLOWS / "sync-nfl-source-data.yml").read_text(encoding="utf-8")
        checkout = source.split("      - name: Checkout main\n", 1)[1].split(
            "\n      - name:", 1
        )[0]
        self.assertIn(
            "(inputs.materialization_scope == 'game-finality' || "
            "inputs.materialization_scope == 'schedule-odds') && 1 || 0",
            checkout,
        )
        self.assertIn("ref: main", checkout)
        self.assertIn("token:", checkout)

    def test_schedule_odds_rejected_push_unshallows_before_diff_and_rebase(self) -> None:
        source = (WORKFLOWS / "sync-nfl-source-data.yml").read_text(encoding="utf-8")
        publisher = source.split("          publish_canonical_commit() {\n", 1)[1].split(
            "\n          }\n", 1
        )[0]
        self.assertIn(
            'if [[ "$materialization_scope" == "schedule-odds" ]] '
            '&& [[ "$(git rev-parse --is-shallow-repository)" == "true" ]]; then',
            publisher,
        )
        self.assertIn("if ! git fetch --unshallow origin main; then", publisher)
        self.assertIn("Cannot restore complete schedule-odds ancestry; failing closed.", publisher)
        self.assertIn("Schedule-odds history remains shallow after fetch; failing closed.", publisher)
        self.assertIn("else\n                git fetch origin main\n              fi", publisher)
        self.assertLess(
            publisher.index("git fetch --unshallow origin main"),
            publisher.index('git diff --quiet "$base_sha" origin/main'),
        )
        self.assertLess(
            publisher.index('git diff --quiet "$base_sha" origin/main'),
            publisher.index("git rebase origin/main"),
        )

    def test_schedule_odds_real_git_shallow_race_classification(self) -> None:
        """Exercise no-race, two writer races, and a failed ancestry fetch."""
        import subprocess
        import tempfile

        source = (WORKFLOWS / "sync-nfl-source-data.yml").read_text(encoding="utf-8")
        publisher = source.split("          publish_canonical_commit() {\n", 1)[1].split(
            "\n          }\n", 1
        )[0]

        def git(cwd: Path, *args: str) -> str:
            result = subprocess.run(
                ["git", *args], cwd=cwd, check=True, capture_output=True,
                text=True, timeout=30,
            )
            return result.stdout.strip()

        for race in ("none", "outside-inputs", "inside-inputs", "fetch-failure"):
            with self.subTest(race=race), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                remote = root / "remote.git"
                git(root, "init", "--bare", "--initial-branch=main", str(remote))
                writer = root / "writer"
                git(root, "clone", str(remote), str(writer))
                git(writer, "config", "user.name", "Workflow Test")
                git(writer, "config", "user.email", "workflow-test@example.invalid")
                odds_path = Path("data-source/nfl/schedule-odds/2026.json")
                (writer / odds_path).parent.mkdir(parents=True)
                (writer / odds_path).write_text("original\n", encoding="utf-8")
                (writer / "other.txt").write_text("original\n", encoding="utf-8")
                git(writer, "add", ".")
                git(writer, "commit", "-m", "initial state")
                git(writer, "push", "origin", "HEAD:main")

                shallow = root / "shallow"
                git(root, "clone", "--depth=1", remote.as_uri(), str(shallow))
                self.assertEqual("true", git(shallow, "rev-parse", "--is-shallow-repository"))
                git(shallow, "config", "user.name", "Workflow Test")
                git(shallow, "config", "user.email", "workflow-test@example.invalid")
                (shallow / odds_path).write_text("published odds\n", encoding="utf-8")
                git(shallow, "add", str(odds_path))
                git(shallow, "commit", "-m", "validated odds materialization")

                if race != "none":
                    if race == "inside-inputs":
                        (writer / odds_path).write_text("changed upstream\n", encoding="utf-8")
                    else:
                        (writer / "other.txt").write_text("changed elsewhere\n", encoding="utf-8")
                    git(writer, "add", ".")
                    git(writer, "commit", "-m", "concurrent writer")
                    git(writer, "push", "origin", "HEAD:main")
                if race == "fetch-failure":
                    git(shallow, "remote", "set-url", "origin", str(root / "missing.git"))

                script = (
                    "set -euo pipefail\n"
                    "push_url=origin\n"
                    "materialization_scope=schedule-odds\n"
                    "materialize_input_pathspecs=(data-source/nfl/schedule-odds)\n"
                    "publish_canonical_commit() {\n" + publisher + "\n}\n"
                    "if publish_canonical_commit; then echo PUBLISHED; else echo REBUILD; fi\n"
                )
                result = subprocess.run(
                    ["bash", "-c", script], cwd=shallow,
                    capture_output=True, text=True, timeout=30,
                )
                if race == "fetch-failure":
                    self.assertNotEqual(0, result.returncode)
                    self.assertIn("failing closed", result.stderr)
                    continue
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertEqual(
                    "true" if race == "none" else "false",
                    git(shallow, "rev-parse", "--is-shallow-repository"),
                )
                git(writer, "fetch", "origin", "main")
                actual_odds = git(writer, "show", f"origin/main:{odds_path}")
                if race == "inside-inputs":
                    self.assertIn("REBUILD", result.stdout)
                    self.assertEqual("changed upstream", actual_odds)
                else:
                    self.assertIn("PUBLISHED", result.stdout)
                    self.assertEqual("published odds", actual_odds)
                    self.assertEqual(
                        "original" if race == "none" else "changed elsewhere",
                        git(writer, "show", "origin/main:other.txt"),
                    )

    def test_production_source_sync_skips_regressions_but_keeps_data_guards(self) -> None:
        source = (WORKFLOWS / "sync-nfl-source-data.yml").read_text(encoding="utf-8")
        self.assertIn("inputs.materialization_scope == 'schedule-odds') && 1 || 0", source)
        self.assertIn("- name: Report production validation boundary", source)
        self.assertNotIn("- name: Test NFL data-source tooling", source)
        self.assertNotIn('discover -s tools/tests -p "test_nfl_source*.py" -v', source)
        self.assertNotIn("python -m unittest tools.tests.test_nfl_source_game_finality_scope -v", source)
        self.assertIn('python tools/nfl_source_data.py "${raw_sync_args[@]}"', source)
        self.assertIn('python tools/nfl_source_data.py "${materialize_args[@]}"', source)
        self.assertIn("Second idempotency check (attempt", source)
        self.assertIn("assert_scoped_canonical_write_set", source)

    def test_repo_state_audit_runs_after_materialization_without_pre_gate(self) -> None:
        # The real-data identity audit belongs after materialization (ADR-039).
        source = (WORKFLOWS / "sync-nfl-source-data.yml").read_text(encoding="utf-8")
        self.assertNotIn("NFL_SOURCE_SYNC_SKIP_REPO_STATE_AUDIT", source)
        self.assertEqual(source.count("python -m unittest "), 1)

        audit_cmd = (
            "python -m unittest "
            "tools.tests.test_nfl_source_app_espn_identity_bridge_repository -v"
        )
        self.assertEqual(source.count(audit_cmd), 1)
        audit_at = source.index(audit_cmd)
        self.assertGreater(audit_at, source.index("Second idempotency check (attempt"))
        self.assertLess(audit_at, source.index("python tools/nfl_source_data.py audit"))
        self.assertLess(audit_at, source.index("git add -- data-source\n"))
        section = source[source.rindex('if [[ "$materialization_scope" == "full" ]]; then', 0, audit_at):audit_at]
        self.assertIn("post_audit_log", section)
        self.assertIn('write_failure_diagnostic "post-materialize-audit"', source)
        self.assertIn("Post-materialization repo-state audit (attempt", source)

    def test_scoped_workflow_emits_requested_observability(self) -> None:
        source = (WORKFLOWS / "sync-nfl-source-data.yml").read_text(encoding="utf-8")
        for marker in (
            "Queue before job start",
            "Checkout:",
            "Regression suites: PR Fast / periodic full audit",
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

