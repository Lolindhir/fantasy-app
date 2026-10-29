from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import git_transient  # noqa: E402


def completed(returncode: int, stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess([], returncode, stdout="", stderr=stderr)


class GitTransientTests(unittest.TestCase):
    def _push(self, *results):
        with mock.patch.object(git_transient.helper, "run_git", side_effect=list(results)) as run_git, \
                mock.patch.object(git_transient.helper.time, "sleep"):
            code = git_transient.push("origin", "HEAD:main", max_transient_retries=2, transient_backoff_seconds=0)
        return code, run_git.call_count

    def test_success(self) -> None:
        self.assertEqual(self._push(completed(0)), (git_transient.EXIT_OK, 1))

    def test_race_is_reported_without_retry(self) -> None:
        code, calls = self._push(completed(1, "! [rejected] main -> main (fetch first)"))
        self.assertEqual((code, calls), (git_transient.EXIT_RACE, 1))

    def test_transient_failure_is_repeated_then_succeeds(self) -> None:
        code, calls = self._push(completed(1, "fatal: RPC failed; HTTP 503"), completed(0))
        self.assertEqual((code, calls), (git_transient.EXIT_OK, 2))

    def test_exhausted_transient_retries_fail_closed(self) -> None:
        failure = completed(1, "error: The requested URL returned error: 502")
        code, calls = self._push(failure, failure, failure)
        self.assertEqual((code, calls), (git_transient.EXIT_FAILED, 3))

    def test_auth_failure_is_not_retried(self) -> None:
        code, calls = self._push(completed(1, "remote: Permission denied (403)"))
        self.assertEqual((code, calls), (git_transient.EXIT_FAILED, 1))

    def test_fetch_retries_transient(self) -> None:
        with mock.patch.object(
            git_transient.helper, "run_git",
            side_effect=[completed(1, "Connection reset by peer"), completed(0)],
        ), mock.patch.object(git_transient.helper.time, "sleep"):
            self.assertEqual(
                git_transient.fetch("origin", "main", max_transient_retries=2, transient_backoff_seconds=0),
                git_transient.EXIT_OK,
            )


if __name__ == "__main__":
    unittest.main()
