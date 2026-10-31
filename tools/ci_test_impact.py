#!/usr/bin/env python3
"""Fail-closed PR impact selection for Core + Fast blocks (Issues #1095, #1122).

Pull requests always run Core and only the Fast blocks the change can affect:
the four Fast families (named like the Deep groups they mirror) plus the
Angular, Scheduler and PowerShell blocks. Deep suites never run on a pull
request; they run in the periodic full audit or through a manual dispatch.

Selection requires a complete PR changed-file inventory and a validated test
registry. Unknown/ambiguous inputs select every Fast block, never zero. No
dependency on untrusted PR code authorizes publication.
"""
from __future__ import annotations

import argparse
import base64
import fnmatch
import json
import os
from pathlib import Path
import re
import sys
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / ".github/ci-test-inventory.json"
GROUPS = ("nfl-identity-replay", "league-pwf-twp", "market-restore", "consumer-restore")
ALL = set(GROUPS)
BLOCKS = ("angular", "scheduler", "powershell")
VALID_TIERS = {"fast", "deep", "audit"}
VALID_COVERAGE = {"build", "build-indirect", "fm-validation", "shadow", "not-in-current-pr-ci"}
VALID_STATES = {"added", "modified", "changed", "renamed", "removed", "deleted", "copied"}
# Frozen 2026-10-20; retired #1199 Matchup/FGC/WeeklyRecaps PowerShell tests and #1238 DecisionWindowRegressionLegacyTest on 2026-10-31. Remaining debt: #1113.
# This is a drift detector, not a security hash. To retire legacy debt or replace
# it with actual PR coverage, review the inventory change and update this anchor.
LEGACY_UNCOVERED_FNV32 = "4a038e26"


def uncovered_baseline_fingerprint(paths: list[str]) -> str:
    """Stable compact fingerprint so new tests cannot silently become 'legacy'."""
    value = 2166136261
    for ch in "\n".join(paths):
        value = (value ^ ord(ch)) * 16777619 & 0xffffffff
    return f"{value:08x}"


def validate_coverage_policy(inventory: dict, indexed: dict[str, dict]) -> tuple[int, int]:
    policy = inventory.get("coveragePolicy")
    if not isinstance(policy, dict) or set(policy) != {"legacyUncoveredTests", "exceptions"}:
        raise ValueError("Missing/invalid CI uncovered-test policy")
    legacy, exceptions = policy["legacyUncoveredTests"], policy["exceptions"]
    if (not isinstance(legacy, list) or not all(isinstance(p, str) for p in legacy)
            or legacy != sorted(set(legacy))
            or uncovered_baseline_fingerprint(legacy) != LEGACY_UNCOVERED_FNV32):
        raise ValueError("Legacy uncovered-test baseline drift: explicit CI review required")
    if not isinstance(exceptions, dict):
        raise ValueError("CI uncovered-test exceptions must be a path-keyed object")
    for path, exception in exceptions.items():
        if (not isinstance(path, str) or not isinstance(exception, dict)
                or set(exception) != {"issue", "reason"}
                or not isinstance(exception["issue"], str)
                or not re.fullmatch(r"#[1-9][0-9]*", exception["issue"])
                or not isinstance(exception["reason"], str)
                or len(exception["reason"].strip()) < 30):
            raise ValueError(f"Invalid uncovered-test exception (issue + concrete reason required): {path}")
    legacy_set = set(legacy)
    exceptions_set = set(exceptions)
    if legacy_set & exceptions_set:
        raise ValueError("Legacy uncovered tests cannot also have new exceptions")
    uncovered = {path for path, entry in indexed.items()
                 if entry["currentPrCoverage"] == "not-in-current-pr-ci"}
    if uncovered != legacy_set | exceptions_set:
        raise ValueError(
            f"Unreviewed PR-CI coverage gap: added={sorted(uncovered - legacy_set - exceptions_set)}; "
            f"stale={sorted((legacy_set | exceptions_set) - uncovered)}")
    return len(legacy), len(exceptions)


def is_test(path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    return (bool(re.fullmatch(r"test_[\w-]+\.py", name))
            or name.endswith("_test.py")
            or any(name.endswith(suffix) for suffix in (
                ".spec.ts", ".test.ts", ".spec.tsx", ".test.tsx",
                ".spec.js", ".test.js", ".spec.mjs", ".test.mjs",
                ".spec.cjs", ".test.cjs"))
            or bool(re.fullmatch(r"[\w-]+(?:Test|Tests)\.ps1", name)))


def discover(root: Path) -> set[str]:
    # Git tracked content only; ignored dependencies and generated checkout files
    # must not result in a false unknown-test alarm.
    import subprocess
    result = subprocess.run(["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True)
    paths = (p.decode("utf-8") for p in result.stdout.split(b"\0") if p)
    return {p for p in paths if is_test(p)}


def read_inventory(path: Path = INVENTORY) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def baseline_coverage(root: Path, paths: set[str], inventory: dict | None = None) -> dict[str, str]:
    """Derive actual CI coverage from Core/Fast/Deep jobs, not the retired monolithic job.

    Python tests are registered in Core, selected Fast or audit-only Deep lanes.
    Other commands are covered by the existing Fast Angular, Scheduler and
    PowerShell jobs; the frozen legacy-uncovered baseline remains separate.
    """
    workflow = (root / ".github/workflows/build.yml").read_text(encoding="utf-8")
    fm = (root / ".github/workflows/fantasy-management-validation.yml").read_text(encoding="utf-8")
    bridge = (root / "tools/tests/test_league_source_team_week_performance_ci.py").read_text(encoding="utf-8")
    commands = (
        "ci_suite_runner.py core",
        "run-workflow-scheduler*.test.cjs",
        "Run full Angular unit test suite",
        "./deploy_action.ps1",
        "./public/requests/ProviderJoinInvariantRegressionTest.ps1",
        "python -m unittest tools.tests.test_ci_test_impact",
    ) + tuple(f"ci_suite_runner.py {lane} {group}"
              for lane in ("fast", "deep") for group in GROUPS)
    if not all(command in workflow for command in commands):
        raise ValueError("Current Core/Fast/Deep workflow coverage changed: re-audit before classification")
    if "unittest discover" not in fm or "fantasy-management/_ai/scripts/tests" not in fm:
        raise ValueError("Fantasy Management validation discovery changed")
    runner_covered = {
        entry["path"]: entry["currentPrCoverage"]
        for entry in (inventory or {}).get("tests", [])
        if entry["path"].startswith("tools/tests/test_") and entry["path"].endswith(".py")
        and entry["tier"] in {"fast", "deep"}
        and entry["currentPrCoverage"] in {"build", "build-indirect"}
    }
    indirect = set(re.findall(r"tools\.tests\.(test_[a-zA-Z0-9_]+)", bridge))
    coverage = {}
    for path in paths:
        name = Path(path).stem
        if path.startswith("fantasy-management/_ai/scripts/tests/"):
            coverage[path] = "fm-validation"
        elif path.startswith("src/") and path.endswith(".spec.ts"):
            coverage[path] = "build"
        elif path.endswith(".test.cjs") and path.startswith("tools/tests/run-workflow-scheduler"):
            coverage[path] = "build"
        elif path == "tools/tests/test_ci_test_impact.py":
            coverage[path] = "shadow"  # direct mandatory Core harness; historical class retained
        elif path in runner_covered:
            coverage[path] = runner_covered[path]
        elif path.startswith("tools/tests/") and name in indirect:
            coverage[path] = "build-indirect"
        elif path.startswith("public/requests/") and ("./" + path) in workflow:
            coverage[path] = "build"
        else:
            coverage[path] = "not-in-current-pr-ci"
    return coverage


def validate(root: Path, inventory: dict) -> dict[str, int]:
    if inventory.get("schemaVersion") != 1 or not isinstance(inventory.get("tests"), list):
        raise ValueError("Unknown CI inventory schema")
    indexed = {}
    for entry in inventory["tests"]:
        if not isinstance(entry, dict) or set(entry) != {"path", "tier", "deepGroups", "fastGroups", "currentPrCoverage"}:
            raise ValueError(f"Malformed test entry: {entry}")
        path = entry["path"]
        if not isinstance(path, str) or not is_test(path) or path in indexed:
            raise ValueError(f"Duplicate/invalid test path: {path}")
        if entry["tier"] not in VALID_TIERS or entry["currentPrCoverage"] not in VALID_COVERAGE:
            raise ValueError(f"Invalid classification or coverage: {path}")
        groups = entry["deepGroups"]
        if not isinstance(groups, list) or len(groups) != len(set(groups)) or not set(groups) <= ALL:
            raise ValueError(f"Invalid deep groups: {path}")
        if (entry["tier"] == "deep") != bool(groups):
            raise ValueError(f"Deep tests require a group; fast/audit tests must not claim one: {path}")
        fast_groups = entry["fastGroups"]
        if (not isinstance(fast_groups, list) or len(fast_groups) != len(set(fast_groups))
                or not set(fast_groups) <= ALL):
            raise ValueError(f"Invalid fast groups: {path}")
        if fast_groups and not (path.startswith("tools/tests/test_") and path.endswith(".py")
                                and entry["tier"] in {"fast", "deep"}):
            raise ValueError(f"Only Python fast/deep modules may claim a Fast family: {path}")
        indexed[path] = entry
    # Inventory the real PR-triggered workflow surface and direct non-test
    # guards; otherwise a future CI refactor could silently omit one.
    actual_workflows = sorted(
        p.relative_to(root).as_posix()
        for p in (root / ".github/workflows").glob("*.yml")
        if re.search(r"(?m)^  pull_request:", p.read_text(encoding="utf-8"))
    )
    if inventory.get("prWorkflows") != actual_workflows:
        raise ValueError(f"PR workflow inventory drift: actual={actual_workflows}")
    commands = inventory.get("mandatoryCommands")
    if not isinstance(commands, list) or not commands:
        raise ValueError("Mandatory non-test command inventory missing")
    for item in commands:
        if not isinstance(item, dict) or set(item) != {"workflow", "snippet", "reason"}:
            raise ValueError(f"Invalid mandatory command record: {item}")
        target = root / item["workflow"]
        if not item["snippet"] or not target.is_file() or item["snippet"] not in target.read_text(encoding="utf-8"):
            raise ValueError(f"Existing mandatory CI command changed: {item['workflow']}: {item['snippet']}")
    tracked = discover(root)
    absent = sorted(tracked - set(indexed))
    stale = sorted(set(indexed) - tracked)
    if absent or stale:
        raise ValueError(f"Inventory drift: unclassified={absent[:20]}; removed={stale[:20]}")
    current = baseline_coverage(root, tracked, inventory)
    mismatches = [
        (path, indexed[path]["currentPrCoverage"], current[path])
        for path in sorted(tracked) if indexed[path]["currentPrCoverage"] != current[path]
    ]
    if mismatches:
        raise ValueError(f"Current CI coverage drift: {mismatches[:12]}")
    legacy_uncovered, explicitly_excepted = validate_coverage_policy(inventory, indexed)
    return {
        "legacyUncovered": legacy_uncovered,
        "explicitlyExceptedUncovered": explicitly_excepted,
        "total": len(indexed),
        "fast": sum(e["tier"] == "fast" for e in indexed.values()),
        "deep": sum(e["tier"] == "deep" for e in indexed.values()),
        "audit": sum(e["tier"] == "audit" for e in indexed.values()),
        "currentlyInPr": sum(e["currentPrCoverage"] in {"build", "build-indirect", "fm-validation"}
                             for e in indexed.values()),
        "currentlyNotInPr": sum(e["currentPrCoverage"] == "not-in-current-pr-ci"
                                for e in indexed.values()),
    }


def affected(path: str, tests: dict[str, dict]) -> tuple[set[str], str]:
    """Return conservative transitive group closure and matching rule."""
    if path in tests:
        entry = tests[path]
        return set(entry["deepGroups"]) | set(entry["fastGroups"]), "registered-test:" + entry["tier"]
    if is_test(path):
        return ALL.copy(), "unclassified-test:fail-closed"
    if path.startswith(SCHEDULER_PATHS[:3]) and path != ".github/workflow-schedules.json":
        return set(), "Scheduler-implementation"
    if path.startswith((".github/workflows/", ".github/ci-test-", "tools/ci_",
                        ".github/workflow-schedules.json", "AGENTS.md", "CHAT_START.md")):
        return ALL.copy(), "CI-or-policy:fail-closed"
    if path.startswith((".ai-context/manual/", ".ai-context/ai-context.yaml")):
        return ALL.copy(), "canonical-contract:fail-closed"
    if path.startswith(("data-meta/", "tools/data_roots.py", "tools/derived_data_lib/")):
        return ALL.copy(), "shared-state-or-model"
    if path.startswith(("data-source/nfl/identities/", "data-source/nfl/providers/",
                        "data-source/providers/")):
        return ALL.copy(), "cross-provider-identity"
    if path.startswith("data-source/nfl/"):
        return {"nfl-identity-replay", "league-pwf-twp", "consumer-restore"}, "NFL-canonical-source"
    if path.startswith("data-source/leagues/"):
        return {"league-pwf-twp", "consumer-restore"}, "League-canonical-source"
    if path.startswith(("data-source/market/", "data-source/external-registry.json")):
        return {"market-restore", "consumer-restore"}, "Market-source"
    if path.startswith("data-source/"):
        return ALL.copy(), "shared-source:unknown-subtype"
    if path.startswith("data-derived/"):
        return {"league-pwf-twp", "consumer-restore"}, "Shared-Derived"
    if path.startswith(("tools/nfl_source_data_lib/", "tools/nfl_source_data.py")):
        return ALL.copy(), "NFL-source-implementation"
    if path.startswith(("tools/league_source_data", "tools/league_source_data_lib/")):
        return {"nfl-identity-replay", "league-pwf-twp", "consumer-restore"}, "League-source-implementation"
    if path.startswith(("tools/player_week_fantasy", "tools/team_week_performance",
                        "tools/historical_fantasy_scoring", "tools/historical_derived_orchestrate",
                        "tools/players_league_scoring", "tools/week_finality")):
        return {"nfl-identity-replay", "league-pwf-twp", "consumer-restore"}, "Scoring-PWF-TWP-implementation"
    if path.startswith(("tools/external_source/", "tools/market_observations",
                        "tools/odds_")):
        return {"market-restore", "consumer-restore"}, "Market-source-implementation"
    if path.startswith(("tools/nfl_games", "tools/derived_data", "tools/derived_clean_root_audit", "tools/player_valuation",
                        "tools/decision_windows", "tools/matchup_context", "tools/league_history", "tools/league_lifecycle", "tools/league_standings", "tools/league_live_derived",
                        "tools/schedule_archive", "tools/weekly_recaps", "tools/players_read_model", "tools/players_app_publish")):
        return {"league-pwf-twp", "consumer-restore"}, "Derived-consumer-implementation"
    if path.startswith("public/requests/") and path.endswith((".ps1", ".psm1")):
        return ALL.copy(), "PowerShell-generator-shared"
    if path.startswith("public/data/"):
        return {"league-pwf-twp", "consumer-restore"}, "App-generated-readmodel"
    if path.startswith(("fantasy-management/_ai/scripts/", "fantasy-management/automation/",
                        "fantasy-management/_ai/schemas/")):
        return {"market-restore"}, "Fantasy-provider-or-operations-conservative"
    if path.startswith(("fantasy-management/", "src/", "public/assets/", "public/images/")):
        return set(), "Consumer-only"
    if path in {"package.json", "package-lock.json", "angular.json", "tsconfig.json",
                ".gitignore", ".prettierrc"} or path.startswith(("src/", "docs/")):
        return set(), "Frontend-or-docs"
    if path.endswith(".md") and path not in {"AGENTS.md", "CHAT_START.md"}:
        return set(), "Documentation-only"
    return ALL.copy(), "unknown-path:fail-closed"


ANGULAR_PATHS = ("src/", "public/assets/", "public/images/", "angular.json", "tsconfig",
                 "package.json", "package-lock.json", "deploy_action.ps1", ".prettierrc")
SCHEDULER_PATHS = ("tools/run-workflow-scheduler", "tools/run-project-field-sync-scheduler",
                   "tools/nfl-game-window.cjs", "tools/tests/run-workflow-scheduler",
                   ".github/workflow-schedules.json")


def blocks_for(path: str, groups: set[str], rule: str) -> set[str]:
    """Non-family Fast blocks (Angular, Scheduler, PowerShell) a change can affect.

    Anything fail-closed selects every block; only documented, narrow
    path families select fewer. Core always runs and is not a block.
    """
    if rule.startswith("registered-test"):
        if path.startswith("src/"):
            return {"angular"}
        if path.startswith("tools/tests/run-workflow-scheduler"):
            return {"scheduler"}
        if path.startswith("public/requests/"):
            return {"powershell"}
        return set()
    if rule.startswith("canonical-contract"):
        return set()
    if path == ".github/workflow-schedules.json":
        return {"scheduler"}
    if "fail-closed" in rule:
        return set(BLOCKS)
    if path.startswith(SCHEDULER_PATHS):
        return {"scheduler"}
    if path.startswith(ANGULAR_PATHS):
        return {"angular"}
    if path.startswith("public/data/"):
        return {"angular", "powershell"}
    if path.startswith(("public/requests/", "data-meta/")) or groups:
        return {"powershell"}
    return set()


def select(changes: list[dict], inventory: dict) -> dict:
    tests = {entry["path"]: entry for entry in inventory["tests"]}
    selected: set[str] = set()
    blocks: set[str] = set()
    reasons: list[dict] = []
    uncertain = False
    if not changes:
        return {"selected": list(GROUPS), "blocks": list(BLOCKS), "uncertain": True, "reasons": [
            {"path": "(none)", "rule": "missing-or-empty-diff:fail-closed", "groups": list(GROUPS),
             "blocks": list(BLOCKS)}]}
    for item in changes:
        path = item.get("filename")
        status = item.get("status")
        if (not isinstance(path, str) or not path or path.startswith("/")
                or ".." in Path(path).parts or status not in VALID_STATES):
            groups, rule = ALL.copy(), "invalid-diff-record:fail-closed"
            path = str(path)
        elif status in {"renamed", "removed", "deleted", "copied"}:
            groups, rule = ALL.copy(), f"{status}-cannot-assume-equivalence:fail-closed"
        else:
            groups, rule = affected(path, tests)
        if "fail-closed" in rule:
            uncertain = True
        chosen_blocks = blocks_for(path, groups, rule)
        selected.update(groups)
        blocks.update(chosen_blocks)
        reasons.append({"path": path, "rule": rule, "groups": sorted(groups),
                        "blocks": sorted(chosen_blocks)})
    return {"selected": sorted(selected), "blocks": sorted(blocks),
            "uncertain": uncertain, "reasons": reasons}


def pr_changes(event: dict) -> list[dict]:
    """Paginate ALL PR files; incomplete API results are a conservative error."""
    pr = event["pull_request"]
    number = int(pr["number"])
    repo = event["repository"]["full_name"]
    token = os.environ["GITHUB_TOKEN"]
    api = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
    result = []
    for page in range(1, 32):
        url = f"{api}/repos/{repo}/pulls/{number}/files?per_page=100&page={page}"
        req = Request(url, headers={"Authorization": f"Bearer {token}",
                                    "Accept": "application/vnd.github+json",
                                    "X-GitHub-Api-Version": "2022-11-28"})
        with urlopen(req, timeout=20) as response:
            files = json.load(response)
        if not isinstance(files, list):
            raise ValueError("Unexpected GitHub changed-file response")
        result.extend({"filename": x["filename"], "status": x["status"],
                       "previous_filename": x.get("previous_filename")} for x in files)
        if len(files) < 100:
            break
    if not result or len(result) != int(pr["changed_files"]) or len(result) > 3000:
        raise ValueError("Incomplete/truncated PR diff; select every Fast block")
    return result



TIMEOUT_ALLOWLIST = {".github/workflows/sync-nfl-source-data.yml"}


def _repo_file_at(repo: str, path: str, sha: str, token: str) -> str:
    """Read exact immutable version from GitHub, not a mutable checkout ref."""
    from urllib.parse import quote
    api = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
    url = f"{api}/repos/{repo}/contents/{quote(path, safe='/')}?ref={sha}"
    req = Request(url, headers={"Authorization": f"Bearer {token}",
                                "Accept": "application/vnd.github+json",
                                "X-GitHub-Api-Version": "2022-11-28"})
    with urlopen(req, timeout=20) as response:
        payload = json.load(response)
    if (not isinstance(payload, dict) or payload.get("encoding") != "base64"
            or not isinstance(payload.get("content"), str)):
        raise ValueError("Unverifiable workflow blob")
    return base64.b64decode(payload["content"], validate=False).decode("utf-8")


def timeout_only_yaml(before: str, after: str) -> bool:
    """Allow ONLY an existing job-level numeric timeout to change.

    YAML semantic comparison also detects permissions, events, env, commands,
    concurrency, job additions and nested timeout-like properties.
    """
    import yaml
    old, new = yaml.safe_load(before), yaml.safe_load(after)
    if not isinstance(old, dict) or not isinstance(new, dict):
        return False
    if not isinstance(old.get("jobs"), dict) or not isinstance(new.get("jobs"), dict):
        return False
    old_copy = json.loads(json.dumps(old))
    new_copy = json.loads(json.dumps(new))
    # json dict keys force YAML 1.1 bool coercion of 'on' into strings; both
    # sides transform identically and all non-timeout fields remain compared.
    old_jobs, new_jobs = old_copy["jobs"], new_copy["jobs"]
    if set(old_jobs) != set(new_jobs):
        return False
    changes = 0
    for name in old_jobs:
        old_job, new_job = old_jobs[name], new_jobs[name]
        if not isinstance(old_job, dict) or not isinstance(new_job, dict):
            return False
        if "timeout-minutes" in old_job and "timeout-minutes" in new_job:
            a, b = old_job["timeout-minutes"], new_job["timeout-minutes"]
            if type(a) is not int or type(b) is not int or not (1 <= a <= 360 and 1 <= b <= 360):
                return False
            if a != b:
                changes += 1
                old_job["timeout-minutes"] = b
    return changes > 0 and old_copy == new_copy


DISPATCH_SCOPES = ("full", *GROUPS)


def dispatch_scope(event: dict) -> str:
    """Manual dispatch scope; scheduled audits and unknown input mean the full audit."""
    scope = (event.get("inputs") or {}).get("scope") or "full"
    if scope not in DISPATCH_SCOPES:
        raise ValueError(f"Unknown dispatch scope {scope!r}")
    return scope


def select_from_event(event: dict, inventory: dict) -> dict:
    if "pull_request" not in event:
        scope = dispatch_scope(event)
        if scope == "full":
            return {"mode": "full", "selected": list(GROUPS), "blocks": list(BLOCKS),
                    "deep": list(GROUPS), "uncertain": False, "reasons": [
                        {"path": "(full audit)", "rule": "full-audit", "groups": list(GROUPS),
                         "blocks": list(BLOCKS)}]}
        return {"mode": "deep", "selected": [], "blocks": [], "deep": [scope],
                "uncertain": False, "reasons": [
                    {"path": f"(manual Deep: {scope})", "rule": "manual-deep",
                     "groups": [scope], "blocks": []}]}
    changes = pr_changes(event)
    result = select(changes, inventory)
    result.update(mode="pr", deep=[])
    if (len(changes) == 1 and changes[0].get("status") == "modified"
            and changes[0]["filename"] in TIMEOUT_ALLOWLIST):
        path = changes[0]["filename"]
        pr = event["pull_request"]
        repo = event["repository"]["full_name"]
        try:
            before = _repo_file_at(repo, path, pr["base"]["sha"], os.environ["GITHUB_TOKEN"])
            after = _repo_file_at(repo, path, pr["head"]["sha"], os.environ["GITHUB_TOKEN"])
            if timeout_only_yaml(before, after):
                return {"mode": "pr", "selected": [], "blocks": [], "deep": [],
                        "uncertain": False, "reasons": [
                            {"path": path, "rule": "verified-job-timeout-only",
                             "groups": [], "blocks": []}]}
        except (OSError, ValueError, KeyError, TypeError, UnicodeError):
            # Never accept an unverified timeout exception.
            pass
    return result


def emit_route_outputs(result: dict) -> None:
    mode = result.get("mode", "pr")
    selected, blocks, deep = set(result["selected"]), set(result["blocks"]), set(result.get("deep", []))
    flags = {
        "mode": mode,
        "nfl": "true" if "nfl-identity-replay" in selected else "false",
        "league": "true" if "league-pwf-twp" in selected else "false",
        "market": "true" if "market-restore" in selected else "false",
        "consumer": "true" if "consumer-restore" in selected else "false",
        "angular": "true" if "angular" in blocks else "false",
        "scheduler": "true" if "scheduler" in blocks else "false",
        "powershell": "true" if "powershell" in blocks else "false",
        "deep_nfl": "true" if "nfl-identity-replay" in deep else "false",
        "deep_league": "true" if "league-pwf-twp" in deep else "false",
        "deep_market": "true" if "market-restore" in deep else "false",
        "deep_consumer": "true" if "consumer-restore" in deep else "false",
    }
    dest = os.environ.get("GITHUB_OUTPUT")
    if not dest:
        raise ValueError("Missing GITHUB_OUTPUT; cannot publish safe routing")
    with open(dest, "a", encoding="utf-8") as out:
        for key, value in flags.items():
            out.write(f"{key}={value}\n")
    print("Selected job flags:", flags, flush=True)


def write_summary(result: dict, counts: dict | None, error: str | None) -> None:
    print(json.dumps({"mode": "ci-impact", "inventory": counts, "selection": result,
                      "error": error}, ensure_ascii=False, sort_keys=True))
    target = os.environ.get("GITHUB_STEP_SUMMARY")
    if target:
        with open(target, "a", encoding="utf-8") as out:
            out.write(f"\n### CI impact — {result.get('mode', 'pr')} decision (fail closed)\n")
            if counts:
                out.write(f"- Inventory: {counts['total']} registered; {counts['currentlyInPr']} already in PR suites; {counts['currentlyNotInPr']} outside present PR suites (legacy baseline: {counts['legacyUncovered']}; issue-backed exceptions: {counts['explicitlyExceptedUncovered']}).\n")
            out.write(f"- Core: always. Fast families: {', '.join(result['selected']) or 'none'}\n")
            out.write(f"- Fast blocks: {', '.join(result.get('blocks', [])) or 'none'}\n")
            out.write(f"- Deep (never automatic on pull requests): {', '.join(result.get('deep', [])) or 'none'}\n")
            out.write(f"- Confidence: {'FAIL-CLOSED / UNCERTAIN' if result['uncertain'] else 'rules matched'}\n")
            if error:
                out.write(f"- Shadow warning: {error}\n")
            out.write("| File | Rule | Families | Blocks |\n| --- | --- | --- | --- |\n")
            for x in result["reasons"][:120]:
                out.write(f"| {x['path'].replace('|', '/')} | {x['rule']} | {', '.join(x['groups'])} | {', '.join(x.get('blocks', []))} |\n")
            if len(result["reasons"]) > 120:
                out.write(f"\n{len(result['reasons']) - 120} additional files omitted from summary; full JSON in log.\n")
            out.write("\n**Core and the selected Fast blocks are enforced by the Merge Gate; a block that was not selected is 'not required', not 'passed'.**\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("validate", "shadow", "select", "route"))
    parser.add_argument("--changes-json", type=Path, help="Local changed-file JSON for a dry run")
    parser.add_argument("--root", type=Path, default=ROOT)
    options = parser.parse_args()
    inventory = read_inventory(options.root / ".github/ci-test-inventory.json")
    if options.mode == "validate":
        print(json.dumps(validate(options.root, inventory), sort_keys=True))
        return 0
    counts, error = None, None
    try:
        counts = validate(options.root, inventory)
        if options.changes_json:
            changes = json.loads(options.changes_json.read_text(encoding="utf-8"))
            result = select(changes, inventory)
        else:
            if options.mode == "select":
                raise ValueError("select requires --changes-json")
            event_path = os.environ.get("GITHUB_EVENT_PATH", "")
            event = json.loads(Path(event_path).read_text(encoding="utf-8"))
            result = select_from_event(event, inventory)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        if options.mode in {"select", "route"}:
            # Unknown input selects every Fast block (never zero);
            # invalid inventory itself is NOT acceptable and failed above.
            if options.mode == "route":
                error = f"{type(exc).__name__}: {exc}"
                result = select([], inventory)
                if os.environ.get("GITHUB_EVENT_NAME") == "pull_request":
                    result.update(mode="pr", deep=[])
                else:
                    result.update(mode="full", deep=list(GROUPS))
            else:
                raise
        else:
            error = f"{type(exc).__name__}: {exc}"
            result = select([], inventory)
    write_summary(result, counts, error)
    if options.mode == "route":
        emit_route_outputs(result)
        return 0
    return 0 if options.mode == "shadow" else int(result["uncertain"])


if __name__ == "__main__":
    sys.exit(main())
