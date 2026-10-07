from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "publish_generated_commit.py"
spec = importlib.util.spec_from_file_location("publish_generated_commit", MODULE_PATH)
assert spec and spec.loader
publisher = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = publisher
spec.loader.exec_module(publisher)


def git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


class PublishGeneratedCommitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.remote = self.root / "remote.git"
        git(self.root, "init", "--bare", str(self.remote))

        self.seed = self.root / "seed"
        git(self.root, "init", "-b", "main", str(self.seed))
        git(self.seed, "config", "user.name", "Test")
        git(self.seed, "config", "user.email", "test@example.com")
        (self.seed / "base.txt").write_text("base\n", encoding="utf-8")
        git(self.seed, "add", "base.txt")
        git(self.seed, "commit", "-m", "base")
        git(self.seed, "remote", "add", "origin", str(self.remote))
        git(self.seed, "push", "-u", "origin", "main")
        git(self.remote, "symbolic-ref", "HEAD", "refs/heads/main")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def clone(self, name: str) -> Path:
        path = self.root / name
        git(self.root, "clone", str(self.remote), str(path))
        git(path, "config", "user.name", "Test")
        git(path, "config", "user.email", "test@example.com")
        return path

    def commit_file(self, repo: Path, path: str, text: str, message: str) -> None:
        target = repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        git(repo, "add", path)
        git(repo, "commit", "-m", message)

    def publish(self, repo: Path, **kwargs: object) -> None:
        old = Path.cwd()
        try:
            import os
            os.chdir(repo)
            publisher.publish(
                remote="origin",
                branch="main",
                max_attempts=int(kwargs.get("max_attempts", 5)),
                backoff_seconds=0,
                jitter_seconds=0,
            )
        finally:
            os.chdir(old)

    def test_publishes_single_commit(self) -> None:
        writer = self.clone("writer")
        self.commit_file(writer, "source-a.txt", "a\n", "source a")
        self.publish(writer)
        verify = self.clone("verify")
        self.assertEqual((verify / "source-a.txt").read_text(encoding="utf-8"), "a\n")

    def test_rebases_disjoint_remote_advance(self) -> None:
        first = self.clone("first")
        second = self.clone("second")
        self.commit_file(first, "first.txt", "first\n", "first")
        self.commit_file(second, "second.txt", "second\n", "second")
        git(first, "push", "origin", "HEAD:main")
        self.publish(second)
        verify = self.clone("verify")
        self.assertTrue((verify / "first.txt").exists())
        self.assertTrue((verify / "second.txt").exists())

    def test_retries_when_remote_advances_during_push(self) -> None:
        writer = self.clone("writer")
        racer = self.clone("racer")
        self.commit_file(writer, "writer.txt", "writer\n", "writer")
        self.commit_file(racer, "racer.txt", "racer\n", "racer")

        original_run_git = publisher.run_git
        race_injected = False

        def run_git_with_race(args, *, check=True):
            nonlocal race_injected
            if list(args[:2]) == ["push", "origin"] and not race_injected:
                race_injected = True
                git(racer, "push", "origin", "HEAD:main")
            return original_run_git(args, check=check)

        publisher.run_git = run_git_with_race
        try:
            self.publish(writer)
        finally:
            publisher.run_git = original_run_git

        self.assertTrue(race_injected)
        verify = self.clone("verify")
        self.assertTrue((verify / "writer.txt").exists())
        self.assertTrue((verify / "racer.txt").exists())

    def test_same_path_remote_advance_fails_closed(self) -> None:
        first = self.clone("first")
        second = self.clone("second")
        self.commit_file(first, "base.txt", "remote\n", "remote change")
        self.commit_file(second, "base.txt", "local\n", "local change")
        git(first, "push", "origin", "HEAD:main")
        with self.assertRaisesRegex(RuntimeError, "conflicts with current remote branch"):
            self.publish(second)
        self.assertFalse((second / ".git" / "rebase-merge").exists())

    def test_dirty_tracked_worktree_is_rejected(self) -> None:
        writer = self.clone("writer")
        self.commit_file(writer, "source.txt", "committed\n", "source")
        (writer / "source.txt").write_text("dirty\n", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "dirty worktree") as context:
            self.publish(writer)
        self.assertIn("source.txt", str(context.exception))

    def test_untracked_file_is_rejected(self) -> None:
        writer = self.clone("writer")
        self.commit_file(writer, "source.txt", "committed\n", "source")
        (writer / "untracked.txt").write_text("dirty\n", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "dirty worktree") as context:
            self.publish(writer)
        self.assertIn("untracked.txt", str(context.exception))

    def test_multiple_local_commits_are_rejected(self) -> None:
        writer = self.clone("writer")
        self.commit_file(writer, "one.txt", "1\n", "one")
        self.commit_file(writer, "two.txt", "2\n", "two")
        with self.assertRaisesRegex(RuntimeError, "exactly one unpublished local commit"):
            self.publish(writer)

    def test_no_local_commit_is_noop(self) -> None:
        writer = self.clone("writer")
        self.publish(writer)
        self.assertEqual(git(writer, "status", "--porcelain").stdout, "")

    def test_race_classifier_covers_non_fast_forward_and_lock_ref(self) -> None:
        for stderr in (
            "! [rejected] HEAD -> main (fetch first)",
            "! [rejected] HEAD -> main (non-fast-forward)",
            "remote: error: cannot lock ref 'refs/heads/main': is at abc but expected def",
            "remote: error: failed to update ref",
        ):
            with self.subTest(stderr=stderr):
                result = publisher.GitResult(1, "", stderr)
                self.assertTrue(publisher.is_retryable_race(result))
        self.assertFalse(publisher.is_retryable_race(publisher.GitResult(1, "", "Authentication failed")))

    def test_transient_classifier(self) -> None:
        for stderr in (
            "fatal: unable to access: The requested URL returned error: 502",
            "error: RPC failed; curl 56",
            "fatal: the remote end hung up unexpectedly",
        ):
            with self.subTest(stderr=stderr):
                self.assertTrue(publisher.is_transient_failure(publisher.GitResult(1, "", stderr)))
        for stderr in (
            "rejected (fetch first)",
            "The requested URL returned error: 403",
            "Authentication failed",
            "pre-receive hook declined",
        ):
            with self.subTest(stderr=stderr):
                self.assertFalse(publisher.is_transient_failure(publisher.GitResult(1, "", stderr)))

    def _with_injected_failures(self, writer: Path, failures: dict, **kwargs: object) -> list:
        """Run publish with run_git failing the first N matching git commands."""
        original_run_git = publisher.run_git
        original_sleep = publisher.time.sleep
        sleeps: list = []
        remaining = dict(failures)

        def run_git_with_failure(args, *, check=True):
            key = args[0]
            if remaining.get(key):
                remaining[key] -= 1
                return publisher.GitResult(128, "", failures_text[key])
            return original_run_git(args, check=check)

        failures_text = kwargs.pop("texts")
        publisher.run_git = run_git_with_failure
        publisher.time.sleep = sleeps.append
        try:
            self.publish_transient(writer, **kwargs)
        finally:
            publisher.run_git = original_run_git
            publisher.time.sleep = original_sleep
        return sleeps

    def publish_transient(self, repo: Path, **kwargs: object) -> None:
        import os
        old = Path.cwd()
        try:
            os.chdir(repo)
            publisher.publish(
                remote="origin",
                branch="main",
                max_attempts=3,
                backoff_seconds=0,
                jitter_seconds=0,
                transient_backoff_seconds=5.0,
                **kwargs,
            )
        finally:
            os.chdir(old)

    def test_transient_push_failure_is_retried_then_succeeds(self) -> None:
        writer = self.clone("writer")
        self.commit_file(writer, "writer.txt", "w\n", "writer")
        sleeps = self._with_injected_failures(
            writer, {"push": 2}, texts={"push": "error: RPC failed; HTTP 502"}
        )
        self.assertEqual(sleeps, [5.0, 15.0])
        self.assertTrue((self.clone("verify") / "writer.txt").exists())

    def test_transient_fetch_failure_is_retried_then_succeeds(self) -> None:
        writer = self.clone("writer")
        self.commit_file(writer, "writer.txt", "w\n", "writer")
        sleeps = self._with_injected_failures(
            writer, {"fetch": 1}, texts={"fetch": "fatal: the remote end hung up unexpectedly"}
        )
        self.assertEqual(sleeps, [5.0])
        self.assertTrue((self.clone("verify") / "writer.txt").exists())

    def test_transient_push_failure_exhausts_with_clear_error(self) -> None:
        writer = self.clone("writer")
        self.commit_file(writer, "writer.txt", "w\n", "writer")
        with self.assertRaisesRegex(RuntimeError, "transient error after 3 retries"):
            self._with_injected_failures(
                writer, {"push": 99}, texts={"push": "The requested URL returned error: 503"}
            )

    def test_auth_push_failure_fails_closed_without_retry(self) -> None:
        writer = self.clone("writer")
        self.commit_file(writer, "writer.txt", "w\n", "writer")
        with self.assertRaisesRegex(RuntimeError, "non-race reason"):
            sleeps = self._with_injected_failures(
                writer, {"push": 99}, texts={"push": "remote: Permission denied\nreturned error: 403"}
            )


if __name__ == "__main__":
    unittest.main()
