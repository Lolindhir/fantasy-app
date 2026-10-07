from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import tools.rebuild_and_publish as publisher


class RebuildAndPublishTests(unittest.TestCase):
    def test_path_scope_accepts_file_and_descendant(self) -> None:
        self.assertTrue(publisher.path_allowed("public/data/League.json", ["public/data"]))
        self.assertTrue(
            publisher.path_allowed(
                "public/data/PastSeasonsIndex.json",
                ["public/data/PastSeasonsIndex.json"],
            )
        )
        self.assertFalse(publisher.path_allowed("source-data/nfl/test.json", ["public/data"]))

    def test_recognizes_only_known_ref_races(self) -> None:
        race = subprocess.CompletedProcess(["git"], 1, "", "rejected (fetch first)")
        auth = subprocess.CompletedProcess(["git"], 1, "", "Authentication failed")
        self.assertTrue(publisher.is_retryable_race(race))
        self.assertFalse(publisher.is_retryable_race(auth))

    def test_fresh_repository_without_git_identity_can_create_generated_commit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            remote = root / "remote.git"
            worktree = root / "worktree"
            isolated_home = root / "home"
            isolated_home.mkdir()

            subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True, text=True)
            subprocess.run(["git", "init", "-b", "main", str(worktree)], check=True, capture_output=True, text=True)
            (worktree / "public" / "data").mkdir(parents=True)
            (worktree / "public" / "data" / "League.json").write_text("seed\n", encoding="utf-8")

            subprocess.run(["git", "add", "."], cwd=worktree, check=True, capture_output=True, text=True)
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.name=seed",
                    "-c",
                    "user.email=seed@example.invalid",
                    "commit",
                    "-m",
                    "seed",
                ],
                cwd=worktree,
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=worktree, check=True)
            subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=worktree, check=True, capture_output=True, text=True)

            self.assertNotEqual(
                subprocess.run(
                    ["git", "config", "--local", "--get", "user.name"],
                    cwd=worktree,
                    capture_output=True,
                    text=True,
                ).returncode,
                0,
            )
            self.assertNotEqual(
                subprocess.run(
                    ["git", "config", "--local", "--get", "user.email"],
                    cwd=worktree,
                    capture_output=True,
                    text=True,
                ).returncode,
                0,
            )

            original_cwd = Path.cwd()
            git_env = {
                "HOME": str(isolated_home),
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CONFIG_GLOBAL": os.devnull,
            }

            def commit_generated(_scope: str) -> None:
                publisher.run_git(["commit", "-m", "data(league): integration test"])

            try:
                os.chdir(worktree)
                with patch.dict(os.environ, git_env, clear=False), patch.object(
                    publisher,
                    "create_generated_commit",
                    side_effect=commit_generated,
                ):
                    publisher.publish_rebuilt(
                        remote="origin",
                        branch="main",
                        scope="league",
                        allowed_paths=["public/data"],
                        command=[
                            sys.executable,
                            "-c",
                            "from pathlib import Path; Path('public/data/League.json').write_text('changed\\n', encoding='utf-8')",
                        ],
                        max_attempts=1,
                        backoff_seconds=0,
                        jitter_seconds=0,
                    )
            finally:
                os.chdir(original_cwd)

            author = subprocess.run(
                ["git", "log", "-1", "--format=%an%n%ae"],
                cwd=worktree,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.splitlines()
            self.assertEqual(
                author,
                [publisher.GENERATED_COMMIT_USER_NAME, publisher.GENERATED_COMMIT_USER_EMAIL],
            )
            remote_head = subprocess.run(
                ["git", "--git-dir", str(remote), "rev-parse", "refs/heads/main"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            local_head = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=worktree,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            self.assertEqual(remote_head, local_head)

    @patch("tools.rebuild_and_publish.time.sleep")
    @patch("tools.rebuild_and_publish.random.uniform", return_value=0.0)
    @patch("tools.rebuild_and_publish.changed_paths", return_value=[])
    @patch("tools.rebuild_and_publish.create_generated_commit")
    @patch("tools.rebuild_and_publish.configure_generated_commit_identity")
    @patch("tools.rebuild_and_publish.has_staged_changes", return_value=True)
    @patch("tools.rebuild_and_publish.stage_paths")
    @patch("tools.rebuild_and_publish.assert_only_allowed_changes", return_value=["public/data/League.json"])
    @patch("tools.rebuild_and_publish.reset_to_target")
    @patch("tools.rebuild_and_publish.run")
    @patch("tools.rebuild_and_publish.run_git")
    def test_race_discards_stale_commit_and_rebuilds_from_latest_target(
        self,
        run_git,
        run_command,
        reset_to_target,
        _assert_scope,
        _stage,
        _has_staged,
        _configure_identity,
        _commit,
        _changed_paths,
        _jitter,
        _sleep,
    ) -> None:
        run_command.return_value = subprocess.CompletedProcess(["generator"], 0, "", "")
        run_git.side_effect = [
            subprocess.CompletedProcess(["git", "push"], 1, "", "rejected (fetch first)"),
            subprocess.CompletedProcess(["git", "push"], 0, "", ""),
        ]

        publisher.publish_rebuilt(
            remote="origin",
            branch="main",
            scope="league",
            allowed_paths=["public/data"],
            command=["generator"],
            max_attempts=3,
            backoff_seconds=0,
            jitter_seconds=0,
        )

        self.assertEqual(reset_to_target.call_count, 2)
        self.assertEqual(run_command.call_count, 2)
        self.assertEqual(run_git.call_count, 2)

    @patch("tools.rebuild_and_publish.changed_paths", return_value=[])
    @patch("tools.rebuild_and_publish.create_generated_commit")
    @patch("tools.rebuild_and_publish.configure_generated_commit_identity")
    @patch("tools.rebuild_and_publish.has_staged_changes", return_value=True)
    @patch("tools.rebuild_and_publish.stage_paths")
    @patch("tools.rebuild_and_publish.assert_only_allowed_changes", return_value=["public/data/League.json"])
    @patch("tools.rebuild_and_publish.reset_to_target")
    @patch("tools.rebuild_and_publish.run")
    @patch("tools.rebuild_and_publish.run_git")
    def test_non_race_push_failure_fails_closed_without_retry(
        self,
        run_git,
        run_command,
        reset_to_target,
        _assert_scope,
        _stage,
        _has_staged,
        _configure_identity,
        _commit,
        _changed_paths,
    ) -> None:
        run_command.return_value = subprocess.CompletedProcess(["generator"], 0, "", "")
        run_git.return_value = subprocess.CompletedProcess(
            ["git", "push"],
            1,
            "",
            "Authentication failed",
        )

        with self.assertRaisesRegex(RuntimeError, "non-race reason"):
            publisher.publish_rebuilt(
                remote="origin",
                branch="main",
                scope="league",
                allowed_paths=["public/data"],
                command=["generator"],
                max_attempts=3,
                backoff_seconds=0,
                jitter_seconds=0,
            )

        reset_to_target.assert_called_once()
        run_command.assert_called_once()
        run_git.assert_called_once()

    @patch("tools.rebuild_and_publish.reset_to_target")
    @patch("tools.rebuild_and_publish.run")
    def test_generator_failure_fails_closed_without_push(self, run_command, reset_to_target) -> None:
        run_command.return_value = subprocess.CompletedProcess(["generator"], 7, "", "boom")
        with self.assertRaises(RuntimeError):
            publisher.publish_rebuilt(
                remote="origin",
                branch="main",
                scope="league",
                allowed_paths=["public/data"],
                command=["generator"],
                max_attempts=3,
                backoff_seconds=0,
                jitter_seconds=0,
            )
        reset_to_target.assert_called_once()

    def test_transient_classifier_separates_transient_race_and_auth(self) -> None:
        def result(stderr: str) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(["git"], 1, "", stderr)

        for stderr in (
            "fatal: unable to access 'x': The requested URL returned error: 502",
            "error: RPC failed; HTTP 500 curl 22",
            "fatal: the remote end hung up unexpectedly",
            "fatal: unable to access: Could not resolve host: github.com",
        ):
            with self.subTest(stderr=stderr):
                self.assertTrue(publisher.is_transient_failure(result(stderr)))
        for stderr in (
            "rejected (fetch first)",
            "The requested URL returned error: 403",
            "remote: Permission denied",
            "Authentication failed",
            "! [remote rejected] main (pre-receive hook declined)",
            "protected branch update failed",
        ):
            with self.subTest(stderr=stderr):
                self.assertFalse(publisher.is_transient_failure(result(stderr)))

    def _patch_publish_stack(self):
        names = [
            "changed_paths",
            "create_generated_commit",
            "configure_generated_commit_identity",
            "has_staged_changes",
            "stage_paths",
            "assert_only_allowed_changes",
            "reset_to_target",
            "run",
            "run_git",
        ]
        patchers = {n: patch(f"tools.rebuild_and_publish.{n}") for n in names}
        mocks = {n: p.start() for n, p in patchers.items()}
        for p in patchers.values():
            self.addCleanup(p.stop)
        sleep = patch("tools.rebuild_and_publish.time.sleep")
        self.sleep = sleep.start()
        self.addCleanup(sleep.stop)
        jitter = patch("tools.rebuild_and_publish.random.uniform", return_value=0.0)
        jitter.start()
        self.addCleanup(jitter.stop)
        mocks["changed_paths"].return_value = []
        mocks["has_staged_changes"].return_value = True
        mocks["assert_only_allowed_changes"].return_value = ["public/data/League.json"]
        mocks["run"].return_value = subprocess.CompletedProcess(["generator"], 0, "", "")
        return mocks

    def _publish(self, **kwargs) -> None:
        publisher.publish_rebuilt(
            remote="origin",
            branch="main",
            scope="league",
            allowed_paths=["public/data"],
            command=["generator"],
            max_attempts=3,
            backoff_seconds=0,
            jitter_seconds=0,
            transient_backoff_seconds=5.0,
            **kwargs,
        )

    def test_transient_push_failure_retries_same_commit_without_rebuild(self) -> None:
        mocks = self._patch_publish_stack()
        transient = subprocess.CompletedProcess(["git", "push"], 1, "", "error: RPC failed; HTTP 502")
        mocks["run_git"].side_effect = [transient, transient, subprocess.CompletedProcess(["git", "push"], 0, "", "")]

        self._publish()

        self.assertEqual(mocks["run_git"].call_count, 3)
        mocks["reset_to_target"].assert_called_once()
        mocks["run"].assert_called_once()
        self.assertEqual([c.args[0] for c in self.sleep.call_args_list], [5.0, 15.0])

    def test_transient_then_race_uses_race_path_with_rebuild(self) -> None:
        mocks = self._patch_publish_stack()
        mocks["run_git"].side_effect = [
            subprocess.CompletedProcess(["git", "push"], 1, "", "The requested URL returned error: 503"),
            subprocess.CompletedProcess(["git", "push"], 1, "", "rejected (fetch first)"),
            subprocess.CompletedProcess(["git", "push"], 0, "", ""),
        ]

        self._publish()

        self.assertEqual(mocks["reset_to_target"].call_count, 2)
        self.assertEqual(mocks["run"].call_count, 2)
        self.assertEqual(mocks["run_git"].call_count, 3)

    def test_transient_push_failure_exhausts_with_clear_error(self) -> None:
        mocks = self._patch_publish_stack()
        mocks["run_git"].return_value = subprocess.CompletedProcess(
            ["git", "push"], 1, "", "fatal: the remote end hung up unexpectedly"
        )

        with self.assertRaisesRegex(RuntimeError, "transient error after 3 retries"):
            self._publish()

        self.assertEqual(mocks["run_git"].call_count, 4)
        mocks["reset_to_target"].assert_called_once()

    def test_auth_and_hook_push_failures_do_not_retry_even_with_transient_text(self) -> None:
        for stderr in (
            "remote: Permission denied\nThe requested URL returned error: 403",
            "remote rejected (pre-receive hook declined) after RPC failed",
        ):
            with self.subTest(stderr=stderr):
                mocks = self._patch_publish_stack()
                mocks["run_git"].return_value = subprocess.CompletedProcess(["git", "push"], 1, "", stderr)
                with self.assertRaisesRegex(RuntimeError, "non-race reason"):
                    self._publish()
                mocks["run_git"].assert_called_once()
                self.sleep.assert_not_called()

    @patch("tools.rebuild_and_publish.time.sleep")
    @patch("tools.rebuild_and_publish.random.uniform", return_value=0.0)
    @patch("tools.rebuild_and_publish.run_git")
    def test_fetch_retries_transient_failure_then_resets(self, run_git, _jitter, sleep) -> None:
        ok = subprocess.CompletedProcess(["git"], 0, "", "")
        run_git.side_effect = [
            subprocess.CompletedProcess(["git", "fetch"], 128, "", "fatal: early EOF"),
            ok,
            ok,
            ok,
        ]

        publisher.reset_to_target("origin", "main", transient_backoff_seconds=5.0)

        self.assertEqual(run_git.call_args_list[0].args[0][0], "fetch")
        self.assertEqual(run_git.call_args_list[1].args[0][0], "fetch")
        self.assertEqual(run_git.call_count, 4)
        sleep.assert_called_once_with(5.0)

    @patch("tools.rebuild_and_publish.time.sleep")
    @patch("tools.rebuild_and_publish.run_git")
    def test_fetch_auth_failure_fails_without_retry(self, run_git, sleep) -> None:
        run_git.return_value = subprocess.CompletedProcess(["git", "fetch"], 128, "", "Authentication failed")

        with self.assertRaisesRegex(RuntimeError, "git fetch failed"):
            publisher.reset_to_target("origin", "main")

        run_git.assert_called_once()
        sleep.assert_not_called()


if __name__ == "__main__":
    unittest.main()
