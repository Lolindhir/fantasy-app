#!/usr/bin/env python3
"""Fail-closed permanent result gate for pull requests and audits (Issues #1095, #1122).

Pull requests require Core and exactly the Fast blocks the selector chose;
Deep jobs and the legacy build must be skipped. A full audit (weekly scheduler
event or a "full" operator dispatch) must select and pass every Fast block,
every Deep category, the restore gate and the legacy build. A Deep-scope dispatch runs Core plus
exactly one Deep category. Unknown events fail. A block that was not selected is
"not required", never "passed": only the exact expected outcome is accepted.
"""
from __future__ import annotations

import json
import os
import sys

CORE = "fast-contracts"
FAST = {
    "nfl": "fast-nfl",
    "league": "fast-league",
    "market": "fast-market",
    "consumer": "fast-consumer",
    "powershell": "fast-powershell",
    "scheduler": "fast-scheduler",
    "angular": "fast-angular",
}
DEEP = {
    "deep_nfl": "deep-nfl",
    "deep_league": "deep-league",
    "deep_market": "deep-market",
    "deep_consumer": "deep-consumer",
}
# Audit-only jobs: required in a full audit, skipped everywhere else.
AUDIT_JOBS = ("restore-gate", "build")
MODES = ("pr", "full", "deep")


def verify(needs: dict, event_name: str = "pull_request",
           event_action: str | None = None) -> list[str]:
    errors = []
    scheduled_audit = event_name == "repository_dispatch" and event_action == "scheduler-ci-full-audit"
    allowed_modes = {"pull_request": ("pr",), "workflow_dispatch": ("full", "deep")}.get(
        event_name, ("full",) if scheduled_audit else ())
    if not allowed_modes:
        return [f"Unsupported CI event/action {event_name!r}/{event_action!r}: fail closed"]
    expected = {"selector", CORE, *FAST.values(), *DEEP.values(), *AUDIT_JOBS}
    if set(needs) != expected:
        errors.append(f"Unexpected/Missing CI jobs: missing={sorted(expected-set(needs))}, extra={sorted(set(needs)-expected)}")
    if needs.get("selector", {}).get("result") != "success":
        errors.append("Selector unavailable, cancelled or failed")
    outputs = needs.get("selector", {}).get("outputs") or {}
    mode = outputs.get("mode")
    if mode not in allowed_modes:
        errors.append(f"Selector mode {mode!r} is not valid for event {event_name!r}")
    flags: dict[str, bool] = {}
    for name in (*FAST, *DEEP):
        raw = outputs.get(name)
        if raw not in {"true", "false"}:
            errors.append(f"Invalid/missing selector output {name}={raw!r}")
        else:
            flags[name] = raw == "true"
    if errors and (mode not in allowed_modes or len(flags) != len(FAST) + len(DEEP)):
        return errors
    if mode == "pr" and any(flags[name] for name in DEEP):
        errors.append("A pull request must never select a Deep job")
    if mode == "full" and not all(flags.values()):
        errors.append("A full audit must select every Fast block and every Deep category")
    if mode == "deep":
        if any(flags[name] for name in FAST):
            errors.append("A Deep-scope dispatch must not select Fast blocks")
        if sum(flags[name] for name in DEEP) != 1:
            errors.append("A Deep-scope dispatch must select exactly one Deep category")
    if needs.get(CORE, {}).get("result") != "success":
        errors.append(f"Mandatory Core job {CORE}: {needs.get(CORE, {}).get('result')!r}")
    for name, job in {**FAST, **DEEP}.items():
        if name not in flags:
            continue
        wanted = flags[name]
        outcome = needs.get(job, {}).get("result")
        allowed = "success" if wanted else "skipped"
        if outcome != allowed:
            errors.append(f"{job}: selected={wanted}, expected {allowed}, got {outcome!r}")
    audit_expected = "success" if mode == "full" else "skipped"
    for job in AUDIT_JOBS:
        actual = needs.get(job, {}).get("result")
        if actual != audit_expected:
            errors.append(f"Audit job {job} in mode {mode!r}: expected {audit_expected}, got {actual!r}")
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
            fp.write("Core and every selected Fast block must succeed; unselected blocks are 'not required'. Pull requests run no Deep job and no legacy build; a full audit requires every Fast block, every Deep category, the restore gate and the legacy build.\n")
            if errors:
                fp.write("\n".join("- " + item.replace("|", "/") for item in errors) + "\n")
    return int(bool(errors))


if __name__ == "__main__":
    sys.exit(main())
