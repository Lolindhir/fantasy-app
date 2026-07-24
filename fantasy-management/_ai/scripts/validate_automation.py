#!/usr/bin/env python3
"""Validate the repo-driven Fantasy Management automation configuration.

The validator checks JSON schemas plus cross-file invariants that schemas alone
cannot express: job/state pairing, configuration references, profile bindings,
target identity consistency, managed-team neutrality and write safety.

Default usage:

  python fantasy-management/_ai/scripts/validate_automation.py
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


class DuplicateKeyError(ValueError):
    pass


@dataclass
class Issue:
    severity: str
    path: str
    message: str


@dataclass
class Report:
    errors: list[Issue] = field(default_factory=list)
    warnings: list[Issue] = field(default_factory=list)

    def error(self, path: Path | str, message: str) -> None:
        self.errors.append(Issue("error", str(path), message))

    def warn(self, path: Path | str, message: str) -> None:
        self.warnings.append(Issue("warning", str(path), message))

    def has_errors(self) -> bool:
        return bool(self.errors)

    def print_text(self) -> None:
        for issue in self.errors + self.warnings:
            prefix = "ERROR" if issue.severity == "error" else "WARN"
            print(f"[{prefix}] {issue.path}: {issue.message}")

        if not self.errors and not self.warnings:
            print("OK: automation configuration is valid.")
        else:
            print(
                f"Summary: {len(self.errors)} error(s), "
                f"{len(self.warnings)} warning(s)."
            )

    def to_json(self) -> dict[str, Any]:
        return {
            "errors": [issue.__dict__ for issue in self.errors],
            "warnings": [issue.__dict__ for issue in self.warnings],
            "summary": {
                "errors": len(self.errors),
                "warnings": len(self.warnings),
            },
        }


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[3]


def rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def object_pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path, report: Report) -> Any | None:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle, object_pairs_hook=object_pairs_no_duplicates)
    except FileNotFoundError:
        report.error(path, "Missing JSON file.")
    except DuplicateKeyError as exc:
        report.error(path, str(exc))
    except json.JSONDecodeError as exc:
        report.error(path, f"Invalid JSON: {exc}")
    except UnicodeDecodeError as exc:
        report.error(path, f"File is not valid UTF-8: {exc}")
    return None


def format_json_path(path: Iterable[Any]) -> str:
    parts = list(path)
    return ".".join(str(part) for part in parts) if parts else "<root>"


def validate_against_schema(
    data: Any,
    schema_path: Path,
    report: Report,
    data_path: Path,
) -> None:
    schema = load_json(schema_path, report)
    if schema is None:
        return

    try:
        from jsonschema import Draft202012Validator
        from jsonschema.exceptions import SchemaError
    except ImportError:
        report.error(
            schema_path,
            "Python package 'jsonschema' is required for automation validation.",
        )
        return

    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        report.error(schema_path, f"Invalid JSON schema: {exc.message}")
        return

    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda err: list(err.path))
    for error in errors:
        report.error(
            data_path,
            f"Schema violation at {format_json_path(error.path)}: {error.message}",
        )


def identifier_sort_key(name: str) -> tuple[int, str]:
    preferred = {
        "sleeper_id": 0,
        "team_id": 1,
        "league_team_id": 2,
        "nfl_team": 3,
    }
    return preferred.get(name, 100), name


def entity_fingerprint(entity: dict[str, Any]) -> str:
    entity_type = str(entity.get("type", "")).strip()
    identifiers = entity.get("identifiers") or {}
    if not entity_type or not isinstance(identifiers, dict) or not identifiers:
        return ""

    identifier_name = sorted(identifiers, key=identifier_sort_key)[0]
    identifier_value = identifiers[identifier_name]
    return f"{entity_type}:{identifier_name}:{identifier_value}"


def merged_profile_refs(
    defaults: list[dict[str, Any]],
    target_bindings: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for binding in defaults + target_bindings:
        profile_ref = str(binding.get("profile_ref", "")).strip()
        if profile_ref:
            merged[profile_ref] = binding
    return merged


def validate_target_sets(
    target_sets: dict[str, tuple[Path, dict[str, Any]]],
    profiles: dict[str, tuple[Path, dict[str, Any]]],
    report: Report,
) -> dict[str, dict[str, Any]]:
    targets: dict[str, dict[str, Any]] = {}

    for target_set_id, (path, target_set) in target_sets.items():
        defaults = target_set.get("defaults") or {}
        default_bindings = defaults.get("profile_bindings") or []

        for selector in target_set.get("selectors") or []:
            for binding in selector.get("profile_bindings") or []:
                profile_ref = binding.get("profile_ref")
                if profile_ref not in profiles:
                    report.error(
                        path,
                        f"Selector {selector.get('id')} references unknown profile "
                        f"{profile_ref!r}.",
                    )

        for target in target_set.get("manual_targets") or []:
            target_id = str(target.get("id", "")).strip()
            entity = target.get("entity") or {}
            fingerprint = entity_fingerprint(entity)
            if not fingerprint:
                report.error(path, f"Target {target_id!r} has no stable entity fingerprint.")
                continue

            previous = targets.get(target_id)
            if previous and previous["fingerprint"] != fingerprint:
                report.error(
                    path,
                    f"Target ID {target_id!r} resolves to both "
                    f"{previous['fingerprint']!r} and {fingerprint!r}.",
                )
            else:
                target_info = targets.setdefault(
                    target_id,
                    {
                        "fingerprint": fingerprint,
                        "entity_type": entity.get("type"),
                        "target_set_ids": set(),
                        "profile_refs": set(),
                    },
                )
                target_info["target_set_ids"].add(target_set_id)

            bindings = merged_profile_refs(
                default_bindings,
                target.get("profile_bindings") or [],
            )
            for profile_ref, binding in bindings.items():
                if not binding.get("enabled", True):
                    continue
                if profile_ref not in profiles:
                    report.error(
                        path,
                        f"Target {target_id!r} references unknown profile "
                        f"{profile_ref!r}.",
                    )
                    continue

                profile = profiles[profile_ref][1]
                applicable = profile.get("applicable_entity_types") or []
                entity_type = entity.get("type")
                if entity_type not in applicable:
                    report.error(
                        path,
                        f"Profile {profile_ref!r} does not support entity type "
                        f"{entity_type!r} for target {target_id!r}.",
                    )
                    continue

                targets[target_id]["profile_refs"].add(profile_ref)

    return targets


def validate_write_scope(job_path: Path, job: dict[str, Any], report: Report) -> None:
    allowed_prefixes = (
        "fantasy-management/automation/state/",
        "fantasy-management/analyses/",
    )
    forbidden_fragments = (
        "public/data/",
        "fantasy-management/automation/jobs/",
        "fantasy-management/automation/target-sets/",
        "fantasy-management/automation/profiles/",
        ".github/workflows/",
    )

    for configured_path in (job.get("execution") or {}).get("write_scope") or []:
        normalized = str(configured_path)
        if not normalized.startswith(allowed_prefixes):
            report.error(
                job_path,
                f"Write scope {normalized!r} is outside approved automation outputs.",
            )
        if any(fragment in normalized for fragment in forbidden_fragments):
            report.error(job_path, f"Write scope {normalized!r} is forbidden.")


def validate_neutral_naming(automation_root: Path, report: Report) -> None:
    forbidden = ("mighty_giants", "mighty giants", "mighty-giants")
    for path in automation_root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".json", ".md"}:
            continue
        try:
            content = path.read_text(encoding="utf-8").casefold()
        except UnicodeDecodeError as exc:
            report.error(path, f"File is not valid UTF-8: {exc}")
            continue
        for token in forbidden:
            if token in content:
                report.error(
                    path,
                    f"Automation must use managed_team instead of franchise token "
                    f"{token!r}.",
                )


def discover_json_by_id(
    directory: Path,
    schema_path: Path,
    report: Report,
) -> dict[str, tuple[Path, dict[str, Any]]]:
    result: dict[str, tuple[Path, dict[str, Any]]] = {}
    if not directory.is_dir():
        report.error(directory, "Missing required configuration directory.")
        return result

    for path in sorted(directory.glob("*.json")):
        data = load_json(path, report)
        if not isinstance(data, dict):
            continue
        validate_against_schema(data, schema_path, report, path)
        item_id = str(data.get("id", "")).strip()
        if not item_id:
            continue
        if path.stem != item_id:
            report.error(path, f"Filename must match id {item_id!r}.")
        if item_id in result:
            report.error(path, f"Duplicate configuration id {item_id!r}.")
        else:
            result[item_id] = (path, data)
    return result


def validate_automation(root: Path | None = None) -> Report:
    root = (root or repo_root_from_script()).resolve()
    report = Report()
    automation_root = root / "fantasy-management/automation"
    schema_root = root / "fantasy-management/_ai/schemas"

    runner_path = automation_root / "runner-config.json"
    runner = load_json(runner_path, report)
    if isinstance(runner, dict):
        validate_against_schema(
            runner,
            schema_root / "automation-runner-config.schema.json",
            report,
            runner_path,
        )
        managed_team = runner.get("managed_team") or {}
        source = root / str(managed_team.get("source", ""))
        if not source.is_file():
            report.error(
                runner_path,
                f"managed_team source does not exist: {rel(source, root)}",
            )

    profiles = discover_json_by_id(
        automation_root / "profiles",
        schema_root / "automation-observation-profile.schema.json",
        report,
    )
    target_sets = discover_json_by_id(
        automation_root / "target-sets",
        schema_root / "automation-target-set.schema.json",
        report,
    )
    targets = validate_target_sets(target_sets, profiles, report)

    jobs = discover_json_by_id(
        automation_root / "jobs",
        schema_root / "automation-job.schema.json",
        report,
    )

    state_directory = automation_root / "state"
    if not state_directory.is_dir():
        report.error(state_directory, "Missing automation state directory.")

    for job_id, (job_path, job) in jobs.items():
        state_path = state_directory / f"{job_id}.json"
        state = load_json(state_path, report)
        if not isinstance(state, dict):
            continue

        schema_name = (
            "automation-observation-state.schema.json"
            if job_id == "entity-observation"
            else "automation-state.schema.json"
        )
        validate_against_schema(state, schema_root / schema_name, report, state_path)

        if state.get("job_id") != job_id:
            report.error(
                state_path,
                f"State job_id {state.get('job_id')!r} does not match job {job_id!r}.",
            )

        for ref in job.get("configuration_refs") or []:
            ref_path = root / str(ref.get("path", ""))
            if ref.get("required") and not ref_path.is_file():
                report.error(
                    job_path,
                    f"Required configuration reference does not exist: "
                    f"{rel(ref_path, root)}",
                )

        validate_write_scope(job_path, job, report)

    known_state_files = {f"{job_id}.json" for job_id in jobs}
    if state_directory.is_dir():
        for state_path in state_directory.glob("*.json"):
            if state_path.name not in known_state_files:
                report.warn(state_path, "State file has no matching job definition.")

    observation_state_path = state_directory / "entity-observation.json"
    observation_state = (
        load_json(observation_state_path, report)
        if observation_state_path.is_file()
        else None
    )
    if isinstance(observation_state, dict):
        state_targets = ((observation_state.get("job_state") or {}).get("targets") or {})
        for target_id, state_target in state_targets.items():
            configured = targets.get(target_id)
            if configured is None:
                report.error(
                    observation_state_path,
                    f"State contains unknown target {target_id!r}.",
                )
                continue
            if state_target.get("entity_fingerprint") != configured["fingerprint"]:
                report.error(
                    observation_state_path,
                    f"State fingerprint for {target_id!r} does not match configuration.",
                )
            state_profiles = set((state_target.get("observations") or {}).keys())
            if state_profiles != configured["profile_refs"]:
                report.error(
                    observation_state_path,
                    f"State profiles for {target_id!r} are {sorted(state_profiles)}, "
                    f"expected {sorted(configured['profile_refs'])}.",
                )

    validate_neutral_naming(automation_root, report)
    return report


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Repository root. Defaults to the root inferred from this script.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the report as JSON.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    report = validate_automation(args.root)
    if args.json:
        print(json.dumps(report.to_json(), ensure_ascii=False, indent=2))
    else:
        report.print_text()
    return 1 if report.has_errors() else 0


if __name__ == "__main__":
    raise SystemExit(main())
