#!/usr/bin/env python3
"""Deterministically validate GitHub Issue labels against work-tracking.yaml.

This tool is intentionally read-only. It validates mechanical metadata rules only;
it does not judge semantic correctness such as whether a chosen priority is wise.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml

DEFAULT_CONTRACT = Path(".ai-context/manual/work-tracking.yaml")
USER_AGENT = "fantasy-app-work-tracking-validator/1"


@dataclass(frozen=True)
class Violation:
    issueNumber: int
    ruleCode: str
    rule: str
    observed: list[str]
    expected: str
    message: str


@dataclass(frozen=True)
class LabelGroup:
    name: str
    allowed: frozenset[str]
    cardinality: str | None
    cardinality_by_state: Mapping[str, str]

    def expected_for(self, state: str) -> str | None:
        if self.cardinality_by_state:
            return self.cardinality_by_state.get(state)
        return self.cardinality


@dataclass(frozen=True)
class ContractModel:
    groups: tuple[LabelGroup, ...]
    allowed_labels: frozenset[str]
    unknown_labels_forbidden: bool


def _load_yaml(path: Path) -> Mapping[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, Mapping):
        raise ValueError(f"Contract must be a YAML mapping: {path}")
    return data


def load_contract(path: Path) -> ContractModel:
    data = _load_yaml(path)
    labels = data.get("labels")
    if not isinstance(labels, Mapping):
        raise ValueError("Contract must define a 'labels' mapping")

    groups: list[LabelGroup] = []
    allowed: set[str] = set()

    for group_name, raw_spec in labels.items():
        if not isinstance(raw_spec, Mapping):
            raise ValueError(f"labels.{group_name} must be a mapping")

        values = raw_spec.get("values")
        exact_label = raw_spec.get("label")
        group_allowed: set[str] = set()

        if isinstance(values, Mapping):
            group_allowed.update(str(value) for value in values.keys())
        if exact_label is not None:
            group_allowed.add(str(exact_label))
        if not group_allowed:
            raise ValueError(
                f"labels.{group_name} must document allowed labels via 'values' or 'label'"
            )

        cardinality_by_state = raw_spec.get("cardinalityByState") or {}
        if not isinstance(cardinality_by_state, Mapping):
            raise ValueError(f"labels.{group_name}.cardinalityByState must be a mapping")

        groups.append(
            LabelGroup(
                name=str(group_name),
                allowed=frozenset(group_allowed),
                cardinality=(
                    str(raw_spec["cardinality"])
                    if raw_spec.get("cardinality") is not None
                    else None
                ),
                cardinality_by_state={
                    str(state): str(cardinality)
                    for state, cardinality in cardinality_by_state.items()
                },
            )
        )
        allowed.update(group_allowed)

    label_policy = data.get("labelPolicy") or {}
    if not isinstance(label_policy, Mapping):
        raise ValueError("labelPolicy must be a mapping")
    unknown_policy = label_policy.get("unknownLabels", "allowed")

    return ContractModel(
        groups=tuple(groups),
        allowed_labels=frozenset(allowed),
        unknown_labels_forbidden=(unknown_policy == "forbidden"),
    )


def _label_names(issue: Mapping[str, Any]) -> list[str]:
    result: list[str] = []
    for raw_label in issue.get("labels") or []:
        if isinstance(raw_label, str):
            result.append(raw_label)
        elif isinstance(raw_label, Mapping) and raw_label.get("name") is not None:
            result.append(str(raw_label["name"]))
        else:
            raise ValueError(f"Unsupported label shape on issue {issue.get('number')}: {raw_label!r}")
    return result


def _issue_number(issue: Mapping[str, Any]) -> int:
    value = issue.get("number", issue.get("issue_number"))
    if value is None:
        raise ValueError("Issue payload is missing number/issue_number")
    return int(value)


def _issue_state(issue: Mapping[str, Any]) -> str:
    state = str(issue.get("state", "")).lower()
    if state not in {"open", "closed"}:
        raise ValueError(f"Issue {_issue_number(issue)} has unsupported state {state!r}")
    return state


def _cardinality_ok(cardinality: str, count: int) -> bool:
    checks = {
        "exactly-one": count == 1,
        "zero-or-one": count <= 1,
        "one-or-more": count >= 1,
        "zero": count == 0,
    }
    if cardinality not in checks:
        raise ValueError(f"Unsupported cardinality in contract: {cardinality}")
    return checks[cardinality]


def validate_issue(issue: Mapping[str, Any], contract: ContractModel) -> list[Violation]:
    number = _issue_number(issue)
    state = _issue_state(issue)
    labels = _label_names(issue)
    violations: list[Violation] = []

    if contract.unknown_labels_forbidden:
        for label in sorted(set(labels) - contract.allowed_labels):
            violations.append(
                Violation(
                    issueNumber=number,
                    ruleCode="label.unknown",
                    rule="Every Issue label must be documented by work-tracking.yaml",
                    observed=[label],
                    expected="documented label",
                    message=f"Issue #{number} uses undocumented label {label!r}.",
                )
            )

    for group in contract.groups:
        expected = group.expected_for(state)
        if expected is None:
            continue
        observed = [label for label in labels if label in group.allowed]
        if _cardinality_ok(expected, len(observed)):
            continue
        violations.append(
            Violation(
                issueNumber=number,
                ruleCode=f"label.{group.name}.cardinality.{state}",
                rule=f"labels.{group.name} cardinality for {state} Issues",
                observed=observed,
                expected=expected,
                message=(
                    f"Issue #{number} violates {group.name} cardinality for {state} Issues: "
                    f"observed {observed or 'none'}, expected {expected}."
                ),
            )
        )

    return violations


def validate_issues(issues: Iterable[Mapping[str, Any]], contract: ContractModel) -> tuple[int, list[Violation]]:
    checked = 0
    violations: list[Violation] = []
    for issue in issues:
        # GitHub's Issues API also returns pull requests. They are not GitHub Issues
        # for purposes of this Issue work-tracking contract.
        if issue.get("pull_request") is not None:
            continue
        checked += 1
        violations.extend(validate_issue(issue, contract))
    return checked, violations


def _github_request(url: str, token: str | None) -> tuple[Any, Mapping[str, str]]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(request) as response:  # noqa: S310 - fixed GitHub API host
        payload = json.loads(response.read().decode("utf-8"))
        response_headers = dict(response.headers.items())
    return payload, response_headers


def fetch_github_issues(repository: str, token: str | None = None) -> list[Mapping[str, Any]]:
    if repository.count("/") != 1:
        raise ValueError("Repository must be in owner/name form")
    owner, name = repository.split("/", 1)
    url = (
        "https://api.github.com/repos/"
        f"{urllib.parse.quote(owner)}/{urllib.parse.quote(name)}/issues?state=all&per_page=100"
    )
    issues: list[Mapping[str, Any]] = []

    while url:
        payload, headers = _github_request(url, token)
        if not isinstance(payload, list):
            raise ValueError("GitHub Issues API returned a non-list payload")
        issues.extend(item for item in payload if isinstance(item, Mapping))
        url = _next_link(headers.get("Link"))

    return issues


def _next_link(link_header: str | None) -> str | None:
    if not link_header:
        return None
    for part in link_header.split(","):
        section = part.strip().split(";")
        if len(section) < 2:
            continue
        url = section[0].strip()
        rel = ";".join(section[1:])
        if 'rel="next"' in rel and url.startswith("<") and url.endswith(">"):
            return url[1:-1]
    return None


def load_issues_file(path: Path) -> list[Mapping[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if isinstance(payload, Mapping) and isinstance(payload.get("issues"), list):
        payload = payload["issues"]
    if not isinstance(payload, list):
        raise ValueError("Issues file must contain a JSON array or an object with an 'issues' array")
    return [item for item in payload if isinstance(item, Mapping)]


def result_payload(checked: int, violations: list[Violation]) -> dict[str, Any]:
    issue_numbers = sorted({violation.issueNumber for violation in violations})
    return {
        "schemaVersion": 1,
        "valid": not violations,
        "issuesChecked": checked,
        "issuesWithViolations": len(issue_numbers),
        "violationCount": len(violations),
        "violations": [asdict(violation) for violation in violations],
    }


def render_text(checked: int, violations: list[Violation]) -> str:
    if not violations:
        return f"Work-tracking validation passed: {checked} Issue(s), 0 violation(s)."
    lines = [
        f"Work-tracking validation failed: {checked} Issue(s), {len(violations)} violation(s)."
    ]
    for violation in violations:
        lines.append(
            f"- #{violation.issueNumber} [{violation.ruleCode}] {violation.message} "
            f"Expected: {violation.expected}; observed: {violation.observed or ['<none>']}"
        )
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--repository", help="GitHub repository in owner/name form")
    source.add_argument("--issues-file", type=Path, help="Local JSON issue payload for offline validation")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--output", type=Path, help="Optional output file; stdout is always written")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        contract = load_contract(args.contract)
        if args.repository:
            issues = fetch_github_issues(args.repository, os.environ.get("GITHUB_TOKEN"))
        else:
            issues = load_issues_file(args.issues_file)
        checked, violations = validate_issues(issues, contract)
        output = (
            json.dumps(result_payload(checked, violations), indent=2, sort_keys=True)
            if args.format == "json"
            else render_text(checked, violations)
        )
        print(output)
        if args.output:
            args.output.write_text(output + "\n", encoding="utf-8")
        return 1 if violations else 0
    except Exception as exc:  # CLI boundary: report deterministic configuration/input errors cleanly.
        print(f"work-tracking validator error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
