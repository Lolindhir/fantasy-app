from __future__ import annotations

import subprocess
import unittest
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

    @patch("tools.rebuild_and_publish.time.sleep")
    @patch("tools.rebuild_and_publish.random.uniform", return_value=0.0)
    @patch("tools.rebuild_and_publish.changed_paths", return_value=[])
    @patch("tools.rebuild_and_publish.create_generated_commit")
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
