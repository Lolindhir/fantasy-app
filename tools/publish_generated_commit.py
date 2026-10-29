#!/usr/bin/env python3
"""Publish one generated-data commit to a moving branch without losing disjoint writes.

This helper is intended for CI jobs that have already validated, staged, and committed
one generated-data update. It rebases that single local commit onto the latest remote
branch and retries recognized ref races and, separately, a bounded number of transient transport failures. Real content conflicts and unrelated
Git/authentication failures remain hard failures.
"""
from __future__ import annotations

import argparse
import random
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Sequence


RACE_MARKERS = (
    "(fetch first)",
    "(non-fast-forward)",
    "non-fast-forward",
    "cannot lock ref",
    "failed to update ref",
    "stale info",
)
# Transient transport/server failures (compared lowercase). They are neither a branch race nor a
# content conflict: the same git command is repeated a bounded number of times with backoff.
TRANSIENT_MARKERS = (
    "the requested url returned error: 5",  # HTTP 500-504 from the git smart-HTTP endpoint
    "rpc failed",
    "the remote end hung up unexpectedly",
    "early eof",
    "unexpected disconnect",
    "connection reset",
    "connection timed out",
    "operation timed out",
    "could not resolve host",
    "gnutls_handshake",
    "internal server error",
    "bad gateway",
    "service unavailable",
    "gateway timeout",
    "http 429",
    "too many requests",
)
# Auth and server-side policy rejections must stay fail-closed even if a transient marker co-occurs.
NON_TRANSIENT_MARKERS = (
    "403",
    "permission denied",
    "authentication failed",
    "pre-receive hook declined",
    "protected branch",
)
DEFAULT_MAX_TRANSIENT_RETRIES = 3
DEFAULT_TRANSIENT_BACKOFF_SECONDS = 5.0


@dataclass(frozen=True)
class GitResult:
    returncode: int
    stdout: str
    stderr: str

    @property
    def combined(self) -> str:
        return f"{self.stdout}\n{self.stderr}".lower()


def run_git(args: Sequence[str], *, check: bool = True) -> GitResult:
    completed = subprocess.run(
        ["git", *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    result = GitResult(completed.returncode, completed.stdout, completed.stderr)
    if check and completed.returncode != 0:
        if completed.stdout:
            print(completed.stdout, end="", file=sys.stderr)
        if completed.stderr:
            print(completed.stderr, end="", file=sys.stderr)
        raise RuntimeError(f"git {' '.join(args)} failed with exit code {completed.returncode}")
    return result


def require_clean_worktree() -> None:
    status = run_git(["status", "--porcelain=v1"]).stdout
    if status.strip():
        dirty_entries = "\n".join(f"  {line}" for line in status.rstrip().splitlines())
        raise RuntimeError(
            "Refusing to publish with a dirty worktree; commit only the intended generated-data changes first.\n"
            f"Dirty worktree entries:\n{dirty_entries}"
        )


def is_transient_failure(result: GitResult) -> bool:
    if any(marker in result.combined for marker in NON_TRANSIENT_MARKERS):
        return False
    if is_retryable_race(result):
        return False
    return any(marker in result.combined for marker in TRANSIENT_MARKERS)


def run_git_with_transient_retry(
    args: Sequence[str],
    *,
    max_transient_retries: int = DEFAULT_MAX_TRANSIENT_RETRIES,
    transient_backoff_seconds: float = DEFAULT_TRANSIENT_BACKOFF_SECONDS,
    jitter_seconds: float = 0.5,
) -> GitResult:
    """Run one git command, repeating it only after recognized transient failures.

    Backoff grows 1x, 3x, 9x of the base (5s, 15s, 45s by default). The last result is returned
    unchanged so callers keep their own handling for races and real failures.
    """
    retry = 0
    while True:
        result = run_git(args, check=False)
        if result.returncode == 0 or not is_transient_failure(result):
            return result
        if retry >= max_transient_retries:
            return result
        retry += 1
        delay = transient_backoff_seconds * (3 ** (retry - 1)) + random.uniform(0, jitter_seconds)
        print(
            f"transient git {args[0]} failure, retry {retry}/{max_transient_retries} in {delay:.1f}s",
            file=sys.stderr,
        )
        if delay:
            time.sleep(delay)


def fetch_target(
    remote: str,
    branch: str,
    *,
    max_transient_retries: int = DEFAULT_MAX_TRANSIENT_RETRIES,
    transient_backoff_seconds: float = DEFAULT_TRANSIENT_BACKOFF_SECONDS,
    jitter_seconds: float = 0.5,
) -> str:
    fetch = run_git_with_transient_retry(
        ["fetch", "--no-tags", remote, branch],
        max_transient_retries=max_transient_retries,
        transient_backoff_seconds=transient_backoff_seconds,
        jitter_seconds=jitter_seconds,
    )
    if fetch.returncode != 0:
        if fetch.stdout:
            print(fetch.stdout, end="", file=sys.stderr)
        if fetch.stderr:
            print(fetch.stderr, end="", file=sys.stderr)
        raise RuntimeError(f"git fetch failed with exit code {fetch.returncode}")
    # A fetch of an arbitrary branch does not necessarily refresh a configured remote-tracking ref.
    # FETCH_HEAD is always the exact branch tip just fetched, so pin a private local ref to it.
    fetched_sha = run_git(["rev-parse", "FETCH_HEAD"]).stdout.strip()
    private_ref = f"refs/publish-generated/{remote}/{branch}"
    run_git(["update-ref", private_ref, fetched_sha])
    return private_ref


def local_commit_count(remote_ref: str) -> int:
    count = run_git(["rev-list", "--count", f"{remote_ref}..HEAD"]).stdout.strip()
    return int(count)


def has_common_history(remote_ref: str) -> bool:
    return run_git(["merge-base", "HEAD", remote_ref], check=False).returncode == 0


def rebase_single_commit(remote_ref: str) -> None:
    if run_git(["merge-base", "--is-ancestor", remote_ref, "HEAD"], check=False).returncode == 0:
        return

    result = run_git(["rebase", remote_ref], check=False)
    if result.returncode == 0:
        return

    # Preserve the repository in a usable state for logs/debugging.
    run_git(["rebase", "--abort"], check=False)
    if result.stdout:
        print(result.stdout, end="", file=sys.stderr)
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    raise RuntimeError("Generated-data commit conflicts with current remote branch; refusing automatic resolution.")


def is_retryable_race(result: GitResult) -> bool:
    return any(marker in result.combined for marker in RACE_MARKERS)


def publish(
    *,
    remote: str,
    branch: str,
    max_attempts: int,
    backoff_seconds: float,
    jitter_seconds: float,
    max_transient_retries: int = DEFAULT_MAX_TRANSIENT_RETRIES,
    transient_backoff_seconds: float = DEFAULT_TRANSIENT_BACKOFF_SECONDS,
) -> None:
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")
    if backoff_seconds < 0 or jitter_seconds < 0:
        raise ValueError("backoff and jitter must be non-negative")

    require_clean_worktree()

    for attempt in range(1, max_attempts + 1):
        remote_ref = fetch_target(
            remote,
            branch,
            max_transient_retries=max_transient_retries,
            transient_backoff_seconds=transient_backoff_seconds,
            jitter_seconds=jitter_seconds,
        )

        if not has_common_history(remote_ref):
            raise RuntimeError("Local HEAD and target branch do not share Git history; refusing to publish.")

        local_count = local_commit_count(remote_ref)
        if local_count == 0:
            print(f"No unpublished local commit remains for {remote}/{branch}; nothing to publish.")
            return
        if local_count != 1:
            raise RuntimeError(
                f"Expected exactly one unpublished local commit, found {local_count}; refusing to publish unrelated history."
            )

        rebase_single_commit(remote_ref)
        require_clean_worktree()

        print(f"Publish attempt {attempt}/{max_attempts} to {remote}/{branch}.")
        # A transient push failure repeats the same rebased commit.
        push = run_git_with_transient_retry(
            ["push", remote, f"HEAD:{branch}"],
            max_transient_retries=max_transient_retries,
            transient_backoff_seconds=transient_backoff_seconds,
            jitter_seconds=jitter_seconds,
        )
        if push.returncode == 0:
            if push.stdout:
                print(push.stdout, end="")
            if push.stderr:
                print(push.stderr, end="")
            print(f"Generated-data publish succeeded on attempt {attempt}.")
            return

        if not is_retryable_race(push):
            if push.stdout:
                print(push.stdout, end="", file=sys.stderr)
            if push.stderr:
                print(push.stderr, end="", file=sys.stderr)
            if is_transient_failure(push):
                raise RuntimeError(
                    f"Git push still failing with a transient error after {max_transient_retries} retries."
                )
            raise RuntimeError("Git push failed for a non-race reason; refusing automatic retry.")

        if attempt == max_attempts:
            if push.stdout:
                print(push.stdout, end="", file=sys.stderr)
            if push.stderr:
                print(push.stderr, end="", file=sys.stderr)
            raise RuntimeError(f"Unable to publish after {max_attempts} recognized branch races.")

        delay = backoff_seconds * attempt + random.uniform(0, jitter_seconds)
        print(f"Target branch advanced during publish attempt {attempt}; retrying after {delay:.2f}s.")
        if delay:
            time.sleep(delay)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--max-attempts", type=int, default=5)
    parser.add_argument("--backoff-seconds", type=float, default=1.0)
    parser.add_argument("--jitter-seconds", type=float, default=0.5)
    parser.add_argument("--max-transient-retries", type=int, default=DEFAULT_MAX_TRANSIENT_RETRIES)
    parser.add_argument("--transient-backoff-seconds", type=float, default=DEFAULT_TRANSIENT_BACKOFF_SECONDS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        publish(
            remote=args.remote,
            branch=args.branch,
            max_attempts=args.max_attempts,
            backoff_seconds=args.backoff_seconds,
            jitter_seconds=args.jitter_seconds,
            max_transient_retries=args.max_transient_retries,
            transient_backoff_seconds=args.transient_backoff_seconds,
        )
    except (RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
