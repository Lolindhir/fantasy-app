#!/usr/bin/env python3
"""Fail-closed permanent result gate for PR and full test audits.

Pull requests require all Fast and selected Deep lanes and skipped legacy build.
Operator workflow_dispatch or the single scheduler-ci-full-audit event must
select and pass ALL Fast, Deep, and historical legacy jobs; unknown events fail.
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


def verify(needs: dict, event_name: str = "pull_request",
           event_action: str | None = None) -> list[str]:
    errors = []
    full_audit = (event_name == "workflow_dispatch" or
                  (event_name == "repository_dispatch" and
                   event_action == "scheduler-ci-full-audit"))
    if event_name != "pull_request" and not full_audit:
        return [f"Unsupported CI event/action {event_name!r}/{event_action!r}: fail closed"]
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
    if full_audit and not flags["full"]:
        errors.append("Full audit must select all four Deep lanes")
    for job in FAST:
        if needs.get(job, {}).get("result") != "success":
            errors.append(f"Mandatory Fast job {job}: {needs.get(job, {}).get('result')!r}")
    for name, job in DEEP.items():
        wanted = flags[name]
        outcome = needs.get(job, {}).get("result")
        allowed = "success" if wanted else "skipped"
        if outcome != allowed:
            errors.append(f"{job}: selected={wanted}, expected {allowed}, got {outcome!r}")
    legacy_expected = "success" if full_audit else "skipped"
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
        errors = verify(needs, os.environ["CI_EVENT_NAME"],
                        os.environ.get("CI_EVENT_ACTION"))
    except (ValueError, TypeError) as exc:
        errors = [f"Invalid GitHub needs JSON: {exc}"]
    print("CI / Merge Gate:", "PASS" if not errors else "FAIL")
    for error in errors:
        print(f" - {error}")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fp:
            fp.write("### CI / Merge Gate: " + ("PASS" if not errors else "FAIL") + "\n")
            fp.write("All Fast/selected Deep must succeed. PR legacy=skipped; operator/scheduled full audit requires all Deep plus legacy=success.\n")
            if errors:
                fp.write("\n".join("- " + item.replace("|", "/") for item in errors) + "\n")
    return int(bool(errors))


if __name__ == "__main__":
    sys.exit(main())
