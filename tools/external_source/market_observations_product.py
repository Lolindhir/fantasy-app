"""#988 4D: read-only product adapter for #471's Shared-Derived coordinator.

Declares one dataset/observation-season partition at a time and compares the
exact candidate bytes from the existing Source-only market renderer. It can
report new/dirty/unchanged/orphaned partitions, but cannot write, delete,
schedule, publish, or mutate canonical Source. The orchestration owner is #471.

Note: candidate rendering reads all persisted ranking evidence; the planner is
an audit/check interface, not a cheap 10-minute provider refresh trigger.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Mapping

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from data_roots import data_source_dir  # noqa: E402
from external_source.identity import MappingIndex, PROVIDER_MAPPINGS_RELATIVE  # noqa: E402
from external_source import market_observations as market  # noqa: E402
from external_source.registry import get_dataset, load_registry  # noqa: E402

PLAN_SCHEMA_VERSION = 1
PRODUCT_ADAPTER_VERSION = 1
_SHA = re.compile(r"^[0-9a-f]{64}$")


class ProductPlanError(ValueError):
    """Invalid prior plan or inconsistent candidate product contract."""


def _key(dataset_id: str, season: int) -> str:
    # Dataset IDs can contain dashes but no ':'; stable partition locator.
    return f"{dataset_id}:{season}"


def _previous_records(
    previous: Mapping[str, Any] | None,
    *,
    selected: set[str] | None = None,
) -> dict[str, dict[str, Any]]:
    if previous is None:
        return {}
    if not isinstance(previous, dict) or previous.get("PlanSchemaVersion") != PLAN_SCHEMA_VERSION:
        raise ProductPlanError("Previous market plan has unsupported PlanSchemaVersion")
    if previous.get("Product") != market.PRODUCT or not isinstance(previous.get("Partitions"), list):
        raise ProductPlanError("Previous market plan has invalid product/partitions")
    result: dict[str, dict[str, Any]] = {}
    for entry in previous["Partitions"]:
        if not isinstance(entry, dict):
            raise ProductPlanError("Previous market plan partition must be an object")
        dataset = entry.get("DatasetID")
        season = entry.get("ObservationSeason")
        sha = entry.get("CandidateSHA256")
        if (
            not isinstance(dataset, str) or not dataset
            or type(season) is not int or season < 2000
            or not isinstance(sha, str) or _SHA.fullmatch(sha) is None
        ):
            raise ProductPlanError("Previous market plan contains an invalid partition identity/hash")
        key = _key(dataset, season)
        if key in result:
            raise ProductPlanError(f"Duplicate previous market partition: {key}")
        result[key] = entry
    if selected is None:
        return result
    return {key: val for key, val in result.items() if val["DatasetID"] in selected}


def plan_partitions(
    repo_root: Path,
    *,
    previous: Mapping[str, Any] | None = None,
    dataset_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Read existing Source to plan dirty partitions; never change any output.

    Dependency declaration includes the registry contract, immutable ranked
    Source evidence (or Sleeper latest), canonical provider identity mappings,
    renderer/adapter code versions, and schema version. Candidate SHA-256
    covers their rendered semantic effect; heartbeat/latest ranked pointers are
    intentionally absent because the renderer never uses them as history.

    Missing partitions are *reported* as orphaned and never deleted.
    """
    registry = load_registry(repo_root)
    selected: set[str] | None = None
    if dataset_ids is not None:
        selected = set(dataset_ids)
        if not selected:
            raise ProductPlanError("Dataset selection cannot be empty")
        for dataset_id in selected:
            get_dataset(registry, dataset_id)

    prior = _previous_records(previous, selected=selected)
    mapping = MappingIndex.load(repo_root)
    entries = [
        entry for entry in market.inventory(repo_root)
        if selected is None or entry["DatasetID"] in selected
    ]
    records: list[dict[str, Any]] = []
    current_keys: set[str] = set()
    for item in entries:
        dataset_id = item["DatasetID"]
        season = item["ObservationSeason"]
        key = _key(dataset_id, season)
        if key in current_keys:
            raise ProductPlanError(f"Duplicate current market partition: {key}")
        current_keys.add(key)

        dataset = get_dataset(registry, dataset_id)
        candidate = market.render_partition(
            repo_root, dataset_id, season, mapping_index=mapping
        )
        sha = market.digest(candidate)
        dependencies = {
            "RegistryDatasetID": dataset_id,
            "RegistrySeasonPolicy": dict(dataset["seasonPolicy"]),
            "CanonicalMappingFile": (
                data_source_dir(repo_root) / PROVIDER_MAPPINGS_RELATIVE
            ).relative_to(repo_root).as_posix(),
            "ObservationSchemaVersion": candidate["SchemaVersion"],
            "RendererVersion": candidate["RendererVersion"],
            "ProductAdapterVersion": PRODUCT_ADAPTER_VERSION,
            "SeasonScheduleFile": (
                data_source_dir(repo_root) / "nfl" / "schedules" / f"{season}.json"
            ).relative_to(repo_root).as_posix(),
            "IdentityProviderKey": dataset["identity"]["providerKey"],
            "SourceEvidenceMode": candidate["HistoryMode"],
        }
        original = prior.get(key)
        change = (
            "new" if original is None
            else "unchanged" if (
                original["CandidateSHA256"] == sha
                and isinstance(original.get("Dependencies"), dict)
                and original["Dependencies"] == dependencies
            )
            else "changed"
        )
        sources = candidate["Observations"]
        row_count = sum(len(obs["Rows"]) for obs in sources)
        records.append({
            "DatasetID": dataset_id,
            "ObservationSeason": season,
            "CandidateSHA256": sha,
            "Change": change,
            "CandidatePath": market.candidate_path(repo_root, dataset_id, season).relative_to(repo_root).as_posix(),
            "HistoryMode": candidate["HistoryMode"],
            "ObservationCount": len(sources),
            "RowCount": row_count,
            "SourceEvidence": [
                {
                    "SnapshotID": obs["SnapshotID"],
                    "SourcePath": obs["SourcePath"],
                    "MetadataPath": obs["MetadataPath"],
                    "SourceHash": obs["SourceHash"],
                    "SourceSchemaVersion": obs["SourceSchemaVersion"],
                }
                for obs in sources
            ],
            "Dependencies": dependencies,
            "Rights": {
                "Storage": dataset["rights"]["storage"],
                "Publication": dataset["rights"]["publication"],
                # No writer exists in this adapter even when rights are allowed.
                "WriterEnabled": False,
            },
        })
    # A previous partition may no longer be discoverable. Report only; deleting
    # a persistent product is a separate authorized/reviewed operation.
    for key, original in prior.items():
        if key not in current_keys:
            records.append({
                "DatasetID": original["DatasetID"],
                "ObservationSeason": original["ObservationSeason"],
                "CandidateSHA256": original["CandidateSHA256"],
                "Change": "orphaned",
                "DeletionAuthorized": False,
            })
    records.sort(key=lambda p: (p["DatasetID"], p["ObservationSeason"]))
    counts = {kind: sum(p["Change"] == kind for p in records) for kind in (
        "new", "changed", "unchanged", "orphaned",
    )}
    return {
        "PlanSchemaVersion": PLAN_SCHEMA_VERSION,
        "Product": market.PRODUCT,
        "Mode": "read-only; no writes, scheduler, or provider fetch",
        "Counts": counts,
        "Partitions": records,
    }


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--dataset-id", action="append", help="optional DatasetID selection")
    parser.add_argument("--previous-plan", type=Path, help="read previous plan from file (never modify it)")
    return parser.parse_args(args)


def main(args: list[str] | None = None) -> int:
    opts = parse_args(args)
    try:
        previous = json.loads(opts.previous_plan.read_text(encoding="utf-8")) if opts.previous_plan else None
        output = plan_partitions(opts.repo_root, previous=previous, dataset_ids=opts.dataset_id)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"[market-product-plan] {exc}", file=sys.stderr)
        return 1
    print(json.dumps(output, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
