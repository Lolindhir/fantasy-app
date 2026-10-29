#!/usr/bin/env python3
"""Fetch/push one git ref with the transient-failure retry of rebuild_and_publish.py.

For workflow-local publication loops that cannot hand their whole generator to
rebuild_and_publish.py (two-phase raw -> canonical publication with failure
diagnostics). The race handling (rebuild from the latest target) stays with the
caller; this CLI only adds the shared bounded retry for transient transport and
server failures (HTTP 5xx, RPC failed, reset connections, 429, ...).

Exit codes: 0 success, 10 recognized branch race on push (caller rebuilds),
1 any other failure (auth, hook rejection, exhausted transient retries).
"""
from __future__ import annotations

import argparse
import sys
from typing import Sequence

import rebuild_and_publish as helper

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_RACE = 10


def _emit(completed) -> None:
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)


def fetch(remote: str, branch: str, **retry) -> int:
    completed = helper.run_git_with_transient_retry(["fetch", "--no-tags", remote, branch], **retry)
    _emit(completed)
    return EXIT_OK if completed.returncode == 0 else EXIT_FAILED


def push(remote: str, refspec: str, **retry) -> int:
    completed = helper.run_git_with_transient_retry(["push", remote, refspec], **retry)
    _emit(completed)
    if completed.returncode == 0:
        return EXIT_OK
    if helper.is_retryable_race(completed):
        return EXIT_RACE
    return EXIT_FAILED


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("fetch", "push"))
    parser.add_argument("remote", help="Remote name or URL")
    parser.add_argument("ref", help="Branch (fetch) or refspec such as HEAD:main (push)")
    parser.add_argument("--max-transient-retries", type=int, default=helper.DEFAULT_MAX_TRANSIENT_RETRIES)
    parser.add_argument("--transient-backoff-seconds", type=float, default=helper.DEFAULT_TRANSIENT_BACKOFF_SECONDS)
    args = parser.parse_args(argv)
    retry = {
        "max_transient_retries": args.max_transient_retries,
        "transient_backoff_seconds": args.transient_backoff_seconds,
    }
    if args.action == "fetch":
        return fetch(args.remote, args.ref, **retry)
    return push(args.remote, args.ref, **retry)


if __name__ == "__main__":
    raise SystemExit(main())
