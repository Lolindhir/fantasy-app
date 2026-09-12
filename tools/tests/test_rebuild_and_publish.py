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


if __name__ == "__main__":
    unittest.main()
