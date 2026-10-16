"""Loader and validator of data-source/external-registry.json (contract: external-source-data.yaml).

Fail-closed: a missing file, an unknown or missing key, a duplicate dataset ID, an unknown identity
provider key or an invalid season policy raises ExternalRegistryError.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from data_roots import data_source_dir

REGISTRY_FILE_NAME = "external-registry.json"
MARKET_DIR_NAME = "market"
SCHEMA_VERSION = 1
DOMAINS = {"market", "media"}
KINDS = {"expert-consensus", "market-value", "adp", "projection", "roster-activity"}
ACQUISITION_MODES = {"html-embedded-json", "html-table", "json-api"}
RETENTION_POLICIES = {"latest-with-git-history"}
LIFECYCLES = {"active", "retired"}
PHASES = ("pre_regular_season", "regular_season", "postseason", "post_regular_season")
PHASE_EXPECTATIONS = {"expected", "optional", "inactive"}
# Provider keys that exist in data-source/nfl/identities/provider-mappings.json and are used here.
IDENTITY_PROVIDER_KEYS = {"FantasyPros", "CBS", "Sleeper"}
RIGHTS_KEYS = {"license", "attribution", "storage", "publication", "evidence"}
RIGHTS_STATES = {"unknown", "allowed", "restricted", "forbidden"}
DATASET_KEYS = {
    "id", "domain", "provider", "kind", "acquisition", "format", "identity", "retentionPolicy",
    "quality", "seasonPolicy", "rights", "lifecycle",
}
FORMAT_KEYS = {"horizon", "scoring", "quarterbackMode", "providerTeamCount", "positions", "window"}
ID_PATTERN = re.compile(r"^[a-z0-9-]+\.[a-z0-9-]+\.[a-z0-9-]+$")


class ExternalRegistryError(ValueError):
    """Raised when the external source registry is missing, malformed or inconsistent."""


def registry_path(repo_root: Path) -> Path:
    return data_source_dir(repo_root) / REGISTRY_FILE_NAME


def market_root(repo_root: Path) -> Path:
    return data_source_dir(repo_root) / MARKET_DIR_NAME


def format_id(dataset: dict[str, Any]) -> str:
    """The format part of the dataset ID, also the directory name below the provider."""
    return dataset["id"].split(".", 2)[2]


def dataset_dir(repo_root: Path, dataset: dict[str, Any]) -> Path:
    return market_root(repo_root) / dataset["kind"] / dataset["provider"] / format_id(dataset)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ExternalRegistryError(message)


def _check_keys(obj: Any, expected: set[str], where: str) -> None:
    _require(isinstance(obj, dict), f"{where} must be an object")
    missing = expected - set(obj)
    extra = set(obj) - expected
    _require(not missing, f"{where} is missing keys: {sorted(missing)}")
    _require(not extra, f"{where} has unknown keys: {sorted(extra)}")


def validate_dataset(dataset: dict[str, Any]) -> None:
    ident = dataset.get("id", "<no id>")
    where = f"dataset {ident}"
    _check_keys(dataset, DATASET_KEYS, where)
    _require(isinstance(ident, str) and ID_PATTERN.match(ident) is not None, f"{where}: id must be <provider>.<name>.<format>")
    _require(ident.startswith(dataset["provider"] + "."), f"{where}: id must start with the provider")
    _require(dataset["domain"] in DOMAINS, f"{where}: unknown domain {dataset['domain']!r}")
    _require(dataset["kind"] in KINDS, f"{where}: unknown kind {dataset['kind']!r}")
    _require(dataset["retentionPolicy"] in RETENTION_POLICIES, f"{where}: unknown retentionPolicy")
    _require(dataset["lifecycle"] in LIFECYCLES, f"{where}: unknown lifecycle")

    acquisition = dataset["acquisition"]
    _check_keys(acquisition, {"mode", "fetcher"}, f"{where}: acquisition")
    _require(acquisition["mode"] in ACQUISITION_MODES, f"{where}: unknown acquisition mode")

    _check_keys(dataset["format"], FORMAT_KEYS, f"{where}: format")
    _require(isinstance(dataset["format"]["positions"], list) and dataset["format"]["positions"], f"{where}: format.positions must be a non-empty list")

    identity = dataset["identity"]
    _check_keys(identity, {"providerKey", "column"}, f"{where}: identity")
    _require(identity["providerKey"] is None or identity["providerKey"] in IDENTITY_PROVIDER_KEYS, f"{where}: unknown identity providerKey {identity['providerKey']!r}")
    _require(isinstance(identity["column"], str) and identity["column"], f"{where}: identity.column is required")

    quality = dataset["quality"]
    _check_keys(quality, {"minimumRows"}, f"{where}: quality")
    rows = quality["minimumRows"]
    _require(rows is None or (isinstance(rows, int) and not isinstance(rows, bool) and rows >= 1), f"{where}: quality.minimumRows must be null or a positive integer")

    policy = dataset["seasonPolicy"]
    _check_keys(policy, set(PHASES), f"{where}: seasonPolicy")
    for phase, expectation in policy.items():
        _require(expectation in PHASE_EXPECTATIONS, f"{where}: seasonPolicy.{phase} must be one of {sorted(PHASE_EXPECTATIONS)}")

    rights = dataset["rights"]
    _check_keys(rights, RIGHTS_KEYS, f"{where}: rights")
    for key in ("storage", "publication"):
        _require(rights[key] in RIGHTS_STATES, f"{where}: rights.{key} must be one of {sorted(RIGHTS_STATES)}")
    _require(isinstance(rights["license"], str) and rights["license"], f"{where}: rights.license is required (use 'unknown')")
    _require(isinstance(rights["attribution"], str) and rights["attribution"], f"{where}: rights.attribution is required")


def validate_registry(registry: dict[str, Any]) -> None:
    _check_keys(registry, {"schemaVersion", "datasets"}, "registry")
    _require(registry["schemaVersion"] == SCHEMA_VERSION, f"unsupported registry schemaVersion {registry['schemaVersion']!r}")
    _require(isinstance(registry["datasets"], list) and registry["datasets"], "registry.datasets must be a non-empty list")
    seen: set[str] = set()
    paths: set[tuple[str, str, str]] = set()
    for dataset in registry["datasets"]:
        validate_dataset(dataset)
        _require(dataset["id"] not in seen, f"duplicate dataset id {dataset['id']}")
        seen.add(dataset["id"])
        path_key = (dataset["kind"], dataset["provider"], format_id(dataset))
        _require(path_key not in paths, f"duplicate dataset directory for {dataset['id']}")
        paths.add(path_key)


def load_registry(repo_root: Path) -> dict[str, Any]:
    path = registry_path(repo_root)
    if not path.is_file():
        raise ExternalRegistryError(f"external source registry not found: {path}")
    try:
        registry = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ExternalRegistryError(f"external source registry is not valid JSON: {exc}") from exc
    validate_registry(registry)
    return registry


def get_dataset(registry: dict[str, Any], dataset_id: str) -> dict[str, Any]:
    for dataset in registry["datasets"]:
        if dataset["id"] == dataset_id:
            return dataset
    raise ExternalRegistryError(f"unknown dataset id {dataset_id!r}")
