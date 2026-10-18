#!/usr/bin/env python3
"""CP3 fail-closed always-present required-check aggregator.

GitHub's skipped jobs may be displayed green. This checker requires every
selected Deep result to be exactly success; only explicitly NOT selected Deep
jobs may be skipped, and the legacy all-suite gate is required whenever the
selector requests full coverage.
"""
from __future__ import annotations

import json
import os
import sys

FAST = ("fast-contracts", "fast-source", "fast-scheduler", "fast-angular", "fast-python")
DEEP = {
    "nfl": "deep-nfl",
    "league": "deep-league",
    "market": "deep-market",
    "consumer": "deep-consumer",
}
GROUPS = {**DEEP, "full": "build"}


def verify(needs: dict) -> list[str]:
    errors = []
    expected = {"selector", *FAST, *DEEP.values(), "build"}
    if set(needs) != expected:
        errors.append(f"Unexpected/Missing CI jobs: missing={sorted(expected-set(needs))}, extra={sorted(set(needs)-expected)}")
    if needs.get("selector", {}).get("result") != "success":
        errors.append("Selector unavailable, cancelled or failed")
    outputs = needs.get("selector", {}).get("outputs") or {}
    flags: dict[str, bool] = {}
    for name in GROUPS:
        raw = outputs.get(name)
        if raw not in {"true", "false"}:
            errors.append(f"Invalid/missing selector output {name}={raw!r}")
        else:
            flags[name] = raw == "true"
    if len(flags) != len(GROUPS):
        return errors
    if flags["full"] != all(flags[name] for name in DEEP):
        errors.append("Invalid full flag: must be equivalent to all four Deep lanes")
    for job in FAST:
        if needs.get(job, {}).get("result") != "success":
            errors.append(f"Mandatory Fast job {job}: {needs.get(job, {}).get('result')!r}")
    for name, job in GROUPS.items():
        wanted = flags[name]
        outcome = needs.get(job, {}).get("result")
        allowed = "success" if wanted else "skipped"
        if outcome != allowed:
            errors.append(f"{job}: selected={wanted}, expected {allowed}, got {outcome!r}")
    return errors


def main() -> int:
    raw = os.environ.get("CI_NEEDS_JSON")
    if not raw:
        print("Missing CI_NEEDS_JSON: fail closed", file=sys.stderr)
        return 1
    try:
        needs = json.loads(raw)
        if not isinstance(needs, dict):
            raise ValueError("needs must be object")
        errors = verify(needs)
    except (ValueError, TypeError) as exc:
        errors = [f"Invalid GitHub needs JSON: {exc}"]
    print("CI / Merge Gate:", "PASS" if not errors else "FAIL")
    for error in errors:
        print(f" - {error}")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fp:
            fp.write("### CI / Merge Gate: " + ("PASS" if not errors else "FAIL") + "\n")
            fp.write("All five Fast lanes must succeed. Deep lanes must succeed when selected, else be skipped.\n")
            if errors:
                fp.write("\n".join("- " + item.replace("|", "/") for item in errors) + "\n")
    return int(bool(errors))


if __name__ == "__main__":
    sys.exit(main())
