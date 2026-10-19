#!/usr/bin/env python3
"""Fail-closed permanent result gate for PR validation and manual full audit.

On pull requests, every Fast and selected Deep job must succeed, while the
legacy build MUST be skipped. Only workflow_dispatch authorizes the complete
legacy build and requires its success in addition to every Fast and Deep job.
Never mistake a GitHub skipped result for success of a selected job.
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


def verify(needs: dict, event_name: str = "pull_request") -> list[str]:
    errors = []
    if event_name not in {"pull_request", "workflow_dispatch"}:
        return [f"Unsupported CI event {event_name!r}: fail closed"]
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
    if event_name == "workflow_dispatch" and not flags["full"]:
        errors.append("Manual full audit must select all four Deep lanes")
    for job in FAST:
        if needs.get(job, {}).get("result") != "success":
            errors.append(f"Mandatory Fast job {job}: {needs.get(job, {}).get('result')!r}")
    for name, job in DEEP.items():
        wanted = flags[name]
        outcome = needs.get(job, {}).get("result")
        allowed = "success" if wanted else "skipped"
        if outcome != allowed:
            errors.append(f"{job}: selected={wanted}, expected {allowed}, got {outcome!r}")
    legacy_expected = "success" if event_name == "workflow_dispatch" else "skipped"
    legacy_actual = needs.get("build", {}).get("result")
    if legacy_actual != legacy_expected:
        errors.append(
            f"Legacy build on {event_name}: expected {legacy_expected}, got {legacy_actual!r}")
    return errors


def main() -> int:
    raw = os.environ.get("CI_NEEDS_JSON")
    if not raw or not os.environ.get("CI_EVENT_NAME"):
        print("Missing CI_NEEDS_JSON or CI_EVENT_NAME: fail closed", file=sys.stderr)
        return 1
    try:
        needs = json.loads(raw)
        if not isinstance(needs, dict):
            raise ValueError("needs must be object")
        errors = verify(needs, os.environ["CI_EVENT_NAME"])
    except (ValueError, TypeError) as exc:
        errors = [f"Invalid GitHub needs JSON: {exc}"]
    print("CI / Merge Gate:", "PASS" if not errors else "FAIL")
    for error in errors:
        print(f" - {error}")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fp:
            fp.write("### CI / Merge Gate: " + ("PASS" if not errors else "FAIL") + "\n")
            fp.write("All Fast and selected Deep lanes must succeed; PR legacy build must be skipped; manual audit requires legacy success.\n")
            if errors:
                fp.write("\n".join("- " + item.replace("|", "/") for item in errors) + "\n")
    return int(bool(errors))


if __name__ == "__main__":
    sys.exit(main())
