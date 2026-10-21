#!/usr/bin/env python3
"""Execute every CP3-classified existing PR Python suite, with one fresh process per module.

The registry is the only module list. Unregistered test files and coverage drift
block the suite before ANY test can be omitted. Existing non-Python safety tests
are retained in their original Fast jobs and publication workflows.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import ci_test_impact as ci

COVERED = {"build", "build-indirect"}


def modules_for_lane(inventory: dict, lane: str) -> list[str]:
    if lane != "fast" and lane not in ci.GROUPS:
        raise ValueError(f"Unknown CI suite: {lane}")
    modules = []
    for item in inventory["tests"]:
        path = item["path"]
        if not (path.startswith("tools/tests/test_") and path.endswith(".py")
                and item["currentPrCoverage"] in COVERED):
            continue
        if lane == "fast":
            chosen = item["tier"] == "fast"
        else:
            chosen = item["tier"] == "deep" and lane in item["deepGroups"]
        if chosen:
            modules.append(path)
    if not modules:
        raise ValueError(f"Empty selected lane: {lane}")
    return sorted(set(modules))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("lane", choices=["fast", *ci.GROUPS])
    args = parser.parse_args()
    inventory = ci.read_inventory()
    ci.validate(ci.ROOT, inventory)
    selected = modules_for_lane(inventory, args.lane)
    print(f"CP3 {args.lane}: executing {len(selected)} registered PR test files", flush=True)
    failed = []
    for index, path in enumerate(selected, 1):
        print(f"[{index}/{len(selected)}] {path}", flush=True)
        # Discover like the historical build's unittest discover entry; unlike
        # one monolithic process, module imports and temporary global state are
        # isolated. No shell interpolation or source data writes.
        cmd = [sys.executable, "-m", "unittest", "discover", "-s",
               "tools/tests", "-p", path.rsplit("/", 1)[1], "-v"]
        # Existing repository modules historically rely on the tools package
        # directory appearing on sys.path because earlier unittest modules
        # modified it as a global side-effect. Make that prerequisite explicit
        # for every isolated subprocess, irrespective of execution order.
        env = os.environ.copy()
        env["PYTHONPATH"] = os.pathsep.join(
            [str(ci.ROOT / "tools"), str(ci.ROOT), env.get("PYTHONPATH", "")]
        )
        result = subprocess.run(cmd, cwd=ci.ROOT, env=env, check=False)
        if result.returncode:
            failed.append((path, result.returncode))
    if failed:
        print(f"FAIL-CLOSED: {len(failed)} modules failed: {failed}", file=sys.stderr)
        return 1
    print(f"CP3 {args.lane}: PASS {len(selected)} modules", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
