#!/usr/bin/env python3
"""Execute registered Python test lanes, one fresh process per module (Issues #1095, #1122).

Lanes: ``core`` (always on pull requests), ``fast <family>`` (selected Fast
family; Deep modules contribute their cheap cases, the expensive ones are
skipped through ``ci_tier.deep_only``) and ``deep <group>`` (periodic audit or
manual dispatch only). The registry is the only module list. Unregistered test
files and coverage drift block the suite before ANY test can be omitted.
Non-Python safety tests are retained in their own Fast jobs.
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
LANES = ("core", "fast", "deep")


def modules_for_lane(inventory: dict, lane: str, group: str | None = None) -> list[str]:
    if lane not in LANES or (lane == "core") != (group is None) or (
            group is not None and group not in ci.GROUPS):
        raise ValueError(f"Unknown CI suite: {lane} {group}")
    modules = []
    for item in inventory["tests"]:
        path = item["path"]
        if not (path.startswith("tools/tests/test_") and path.endswith(".py")
                and item["currentPrCoverage"] in COVERED):
            continue
        if lane == "core":
            chosen = item["tier"] == "fast" and not item["fastGroups"]
        elif lane == "fast":
            chosen = group in item["fastGroups"]
        else:
            chosen = item["tier"] == "deep" and group in item["deepGroups"]
        if chosen:
            modules.append(path)
    if not modules:
        raise ValueError(f"Empty selected lane: {lane} {group}")
    return sorted(set(modules))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("lane", choices=LANES)
    parser.add_argument("group", nargs="?", choices=ci.GROUPS)
    args = parser.parse_args()
    inventory = ci.read_inventory()
    ci.validate(ci.ROOT, inventory)
    selected = modules_for_lane(inventory, args.lane, args.group)
    label = " ".join(x for x in (args.lane, args.group) if x)
    print(f"{label}: executing {len(selected)} registered test files", flush=True)
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
        if args.lane == "fast":
            env["CI_TEST_TIER"] = "fast"  # deep_only cases are skipped, see tools/ci_tier.py
        else:
            env.pop("CI_TEST_TIER", None)
        env["PYTHONPATH"] = os.pathsep.join(
            [str(ci.ROOT / "tools"), str(ci.ROOT), env.get("PYTHONPATH", "")]
        )
        result = subprocess.run(cmd, cwd=ci.ROOT, env=env, check=False)
        if result.returncode:
            failed.append((path, result.returncode))
    if failed:
        print(f"FAIL-CLOSED: {len(failed)} modules failed: {failed}", file=sys.stderr)
        return 1
    print(f"{label}: PASS {len(selected)} modules", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
