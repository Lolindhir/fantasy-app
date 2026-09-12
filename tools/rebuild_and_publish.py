#!/usr/bin/env python3
"""Rebuild and publish repository-derived output against a moving target branch.

The generator command is rerun from the latest target branch for every publish
attempt. This is intentionally different from publish_generated_commit.py, which
rebases one already-built self-contained snapshot.
"""
from __future__ import annotations

import argparse
import random
import shlex
import subprocess
import sys
import time
from pathlib import PurePosixPath
from typing import Iterable, Sequence


RACE_MARKERS = (
    "(fetch first)",
    "(non-fast-forward)",
    "non-fast-forward",
    "cannot lock ref",
    "failed to update ref",
    "stale info",
)
GENERATED_COMMIT_USER_NAME = "github-actions"
GENERATED_COMMIT_USER_EMAIL = "github-actions@github.com"


def run(args: Sequence[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        list(args),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and completed.returncode != 0:
        if completed.stdout:
            print(completed.stdout, end="", file=sys.stderr)
        if completed.stderr:
            print(completed.stderr, end="", file=sys.stderr)
        raise RuntimeError(f"command failed ({completed.returncode}): {shlex.join(args)}")
    return completed


def run_git(args: Sequence[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run(["git", *args], check=check)


def is_retryable_race(completed: subprocess.CompletedProcess[str]) -> bool:
    combined = f"{completed.stdout}\n{completed.stderr}".lower()
    return any(marker in combined for marker in RACE_MARKERS)


def reset_to_target(remote: str, branch: str) -> None:
    run_git(["fetch", "--no-tags", remote, branch])
    run_git(["reset", "--hard", "FETCH_HEAD"])
    run_git(["clean", "-fd"])


def changed_paths() -> list[str]:
    result = run_git(["status", "--porcelain=v1"])
    paths: list[str] = []
    for raw_line in result.stdout.splitlines():
        if not raw_line:
            continue
        path = raw_line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        paths.append(path.replace("\\", "/"))
    return paths


def path_allowed(path: str, allowed: Iterable[str]) -> bool:
    normalized = PurePosixPath(path)
    for raw_allowed in allowed:
        allowed_path = PurePosixPath(raw_allowed.rstrip("/"))
        if normalized == allowed_path or allowed_path in normalized.parents:
            return True
    return False


def assert_only_allowed_changes(allowed_paths: Sequence[str]) -> list[str]:
    changed = changed_paths()
    unexpected = [path for path in changed if not path_allowed(path, allowed_paths)]
    if unexpected:
        details = "\n".join(f" - {path}" for path in unexpected)
        raise RuntimeError(
            "Generator changed files outside its publication scope; refusing to publish:\n"
            + details
        )
    return changed


def stage_paths(paths: Sequence[str]) -> None:
    run_git(["add", "-A", "--", *paths])


def has_staged_changes() -> bool:
    return run_git(["diff", "--cached", "--quiet"], check=False).returncode == 1


def configure_generated_commit_identity() -> None:
    run_git(["config", "--local", "user.name", GENERATED_COMMIT_USER_NAME])
    run_git(["config", "--local", "user.email", GENERATED_COMMIT_USER_EMAIL])


def create_generated_commit(scope: str) -> None:
    run(["pwsh", "./.github/scripts/Invoke-GeneratedDataCommit.ps1", "-Scope", scope])


def publish_rebuilt(
    *,
    remote: str,
    branch: str,
    scope: str,
    allowed_paths: Sequence[str],
    command: Sequence[str],
    max_attempts: int,
    backoff_seconds: float,
    jitter_seconds: float,
) -> None:
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")
    if not allowed_paths:
        raise ValueError("at least one --path is required")
    if not command:
        raise ValueError("generator command is required after --")

    for attempt in range(1, max_attempts + 1):
        print(f"Rebuild/publish attempt {attempt}/{max_attempts} for {scope}.")
        reset_to_target(remote, branch)

        generator = run(command, check=False)
        if generator.stdout:
            print(generator.stdout, end="")
        if generator.stderr:
            print(generator.stderr, end="", file=sys.stderr)
        if generator.returncode != 0:
            raise RuntimeError(
                f"generator failed with exit code {generator.returncode}; refusing to publish"
            )

        changed = assert_only_allowed_changes(allowed_paths)
        if not changed:
            print("Generator produced no repository changes. Nothing to publish.")
            return

        stage_paths(allowed_paths)
        if not has_staged_changes():
            print("No staged generated-data changes detected. Nothing to publish.")
            return

        configure_generated_commit_identity()
        create_generated_commit(scope)
        if changed_paths():
            raise RuntimeError("Worktree is dirty after generated-data commit; refusing to push.")

        push = run_git(["push", remote, f"HEAD:{branch}"], check=False)
        if push.returncode == 0:
            if push.stdout:
                print(push.stdout, end="")
            if push.stderr:
                print(push.stderr, end="")
            print(f"Rebuilt generated-data publish succeeded on attempt {attempt}.")
            return

        if not is_retryable_race(push):
            if push.stdout:
                print(push.stdout, end="", file=sys.stderr)
            if push.stderr:
                print(push.stderr, end="", file=sys.stderr)
            raise RuntimeError("git push failed for a non-race reason; refusing automatic retry")

        if attempt == max_attempts:
            raise RuntimeError(f"unable to publish after {max_attempts} recognized branch races")

        delay = backoff_seconds * attempt + random.uniform(0, jitter_seconds)
        print(
            "Target branch advanced during publish. The generated commit will be discarded "
            f"and rebuilt from latest {remote}/{branch} after {delay:.2f}s."
        )
        if delay:
            time.sleep(delay)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", required=True)
    parser.add_argument("--path", action="append", dest="paths", required=True)
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--backoff-seconds", type=float, default=1.0)
    parser.add_argument("--jitter-seconds", type=float, default=0.5)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.command and args.command[0] == "--":
        args.command = args.command[1:]
    return args


def main() -> int:
    args = parse_args()
    try:
        publish_rebuilt(
            remote=args.remote,
            branch=args.branch,
            scope=args.scope,
            allowed_paths=args.paths,
            command=args.command,
            max_attempts=args.max_attempts,
            backoff_seconds=args.backoff_seconds,
            jitter_seconds=args.jitter_seconds,
        )
    except (RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
