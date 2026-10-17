#!/usr/bin/env python3
"""CP1 read-only CI impact inventory and conservative shadow Deep-Gate router.

No test is executed or skipped by this program. Never use its output as a
required check before a separately reviewed CP3 activation (Issue #1095).
"""
from __future__ import annotations

import argparse
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
VALID_TIERS = {"fast", "deep", "audit"}
VALID_COVERAGE = {"build", "build-indirect", "fm-validation", "shadow", "not-in-current-pr-ci"}
VALID_STATES = {"added", "modified", "changed", "renamed", "removed", "deleted", "copied"}


def is_test(path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    return (bool(re.fullmatch(r"test_[\w-]+\.py", name))
            or name.endswith(".spec.ts") or name.endswith(".test.cjs")
            or bool(re.fullmatch(r"[\w-]+Regression(?:Legacy)?Test\.ps1", name)))


def discover(root: Path) -> set[str]:
    # Git tracked content only; ignored dependencies and generated checkout files
    # must not result in a false unknown-test alarm.
    import subprocess
    result = subprocess.run(["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True)
    paths = (p.decode("utf-8") for p in result.stdout.split(b"\0") if p)
    return {p for p in paths if is_test(p)}


def read_inventory(path: Path = INVENTORY) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def baseline_coverage(root: Path, paths: set[str]) -> dict[str, str]:
    """Derived from ACTUAL existing PR workflows, not from aspirational classes."""
    build = (root / ".github/workflows/build.yml").read_text(encoding="utf-8")
    fm = (root / ".github/workflows/fantasy-management-validation.yml").read_text(encoding="utf-8")
    bridge_path = root / "tools/tests/test_league_source_team_week_performance_ci.py"
    bridge = bridge_path.read_text(encoding="utf-8")
    if not all(s in build for s in (
        'test_nfl_source*.py', 'test_league_source*.py',
        'run-workflow-scheduler*.test.cjs', 'Run full Angular unit test suite',
    )):
        raise ValueError("Existing build discovery changed: re-audit baseline before classification")
    if "unittest discover" not in fm or "fantasy-management/_ai/scripts/tests" not in fm:
        raise ValueError("Fantasy Management validation discovery changed")
    python_refs = set(re.findall(r"tools[./]tests[./](test_[a-zA-Z0-9_]+)", build))
    discover_patterns = set(re.findall(r'-p "([^"]+\\.py)"', build))
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
        elif path.startswith("tools/tests/") and (fnmatch.fnmatch(name, "test_nfl_source*")
              or fnmatch.fnmatch(name, "test_league_source*") or name in python_refs
              or any(fnmatch.fnmatch(Path(path).name, pat) for pat in discover_patterns)):
            coverage[path] = "build"
        elif path.startswith("tools/tests/") and name in indirect:
            coverage[path] = "build-indirect"
        elif path.startswith("public/requests/") and ("./" + path) in build:
            coverage[path] = "build"
        elif path == "tools/tests/test_ci_test_impact.py" and "test_ci_test_impact" in build:
            coverage[path] = "shadow"
        else:
            coverage[path] = "not-in-current-pr-ci"
    return coverage


def validate(root: Path, inventory: dict) -> dict[str, int]:
    if inventory.get("schemaVersion") != 1 or not isinstance(inventory.get("tests"), list):
        raise ValueError("Unknown CI inventory schema")
    indexed = {}
    for entry in inventory["tests"]:
        if not isinstance(entry, dict) or set(entry) != {"path", "tier", "deepGroups", "currentPrCoverage"}:
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
        indexed[path] = entry
    tracked = discover(root)
    absent = sorted(tracked - set(indexed))
    stale = sorted(set(indexed) - tracked)
    if absent or stale:
        raise ValueError(f"Inventory drift: unclassified={absent[:20]}; removed={stale[:20]}")
    current = baseline_coverage(root, tracked)
    mismatches = [
        (path, indexed[path]["currentPrCoverage"], current[path])
        for path in sorted(tracked) if indexed[path]["currentPrCoverage"] != current[path]
    ]
    if mismatches:
        raise ValueError(f"Current CI coverage drift: {mismatches[:12]}")
    return {
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
        return set(entry["deepGroups"]), "registered-test:" + entry["tier"]
    if is_test(path):
        return ALL.copy(), "unclassified-test:fail-closed"
    if path.startswith((".github/workflows/", ".github/ci-test-", "tools/ci_test_impact.py",
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
                        "tools/historical_fantasy_scoring", "tools/players_league_scoring")):
        return {"nfl-identity-replay", "league-pwf-twp", "consumer-restore"}, "Scoring-PWF-TWP-implementation"
    if path.startswith(("tools/external_source/", "tools/market_observations",
                        "tools/odds_change_gate")):
        return {"market-restore", "consumer-restore"}, "Market-source-implementation"
    if path.startswith(("tools/nfl_games", "tools/derived_data", "tools/player_valuation",
                        "tools/league_history", "tools/schedule_archive")):
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


def select(changes: list[dict], inventory: dict) -> dict:
    tests = {entry["path"]: entry for entry in inventory["tests"]}
    selected: set[str] = set()
    reasons: list[dict] = []
    uncertain = False
    if not changes:
        return {"selected": list(GROUPS), "uncertain": True, "reasons": [
            {"path": "(none)", "rule": "missing-or-empty-diff:fail-closed", "groups": list(GROUPS)}]}
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
        selected.update(groups)
        reasons.append({"path": path, "rule": rule, "groups": sorted(groups)})
    return {"selected": sorted(selected), "uncertain": uncertain, "reasons": reasons}


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
        raise ValueError("Incomplete/truncated PR diff; route all Deep Groups")
    return result


def write_summary(result: dict, counts: dict | None, error: str | None) -> None:
    print(json.dumps({"mode": "shadow-only", "inventory": counts, "selection": result,
                      "error": error}, ensure_ascii=False, sort_keys=True))
    target = os.environ.get("GITHUB_STEP_SUMMARY")
    if target:
        with open(target, "a", encoding="utf-8") as out:
            out.write("\n### CI impact — CP1 shadow only (no tests skipped)\n")
            if counts:
                out.write(f"- Inventory: {counts['total']} registered; {counts['currentlyInPr']} already in PR suites; {counts['currentlyNotInPr']} outside present PR suites.\n")
            out.write(f"- Proposed Deep groups: {', '.join(result['selected']) or 'none'}\n")
            out.write(f"- Confidence: {'FAIL-CLOSED / UNCERTAIN' if result['uncertain'] else 'rules matched'}\n")
            if error:
                out.write(f"- Shadow warning: {error}\n")
            out.write("| File | Rule | Groups |\n| --- | --- | --- |\n")
            for x in result["reasons"][:120]:
                out.write(f"| {x['path'].replace('|', '/')} | {x['rule']} | {', '.join(x['groups'])} |\n")
            if len(result["reasons"]) > 120:
                out.write(f"\n{len(result['reasons']) - 120} additional files omitted from summary; full JSON in log.\n")
            out.write("\n**This is advisory only. The pre-existing entire build CI remains mandatory.**\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("validate", "shadow", "select"))
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
        else:
            if options.mode == "select":
                raise ValueError("select requires --changes-json")
            event_path = os.environ.get("GITHUB_EVENT_PATH", "")
            event = json.loads(Path(event_path).read_text(encoding="utf-8"))
            changes = pr_changes(event)
        result = select(changes, inventory)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        if options.mode == "select":
            raise
        error = f"{type(exc).__name__}: {exc}"
        result = select([], inventory)
    write_summary(result, counts, error)
    # shadow-only MUST NOT alter the current mandatory build result.
    return 0 if options.mode == "shadow" else int(result["uncertain"])


if __name__ == "__main__":
    sys.exit(main())
