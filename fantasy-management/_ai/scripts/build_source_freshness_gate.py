from __future__ import annotations

import argparse
import json
from datetime import datetime, time, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

BERLIN = ZoneInfo("Europe/Berlin")
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG = REPO_ROOT / "fantasy-management/automation/source-freshness-gate.json"
VALID_SOURCE_STATUSES = {"fresh", "stale", "missing", "failed", "invalid"}


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _iso_z(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _age_minutes(now: datetime, observed: datetime) -> float:
    return round((now - observed).total_seconds() / 60.0, 2)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _evaluate_timestamp_source(root: Path, source: dict[str, Any], now: datetime) -> dict[str, Any]:
    path = root / source["path"]
    base = {
        "id": source["id"],
        "label": source["label"],
        "kind": source["kind"],
        "path": source["path"],
        "block_monitoring_if_unfresh": source["block_monitoring_if_unfresh"],
        "required_for_no_event_conclusion": source["required_for_no_event_conclusion"],
        "affected_signal_families": source["affected_signal_families"],
    }
    if not path.exists():
        return {**base, "status": "missing", "reason": "timestamp_file_missing", "checked_at": None, "age_minutes": None}
    try:
        payload = _load_json(path)
        raw = payload.get(source["timestamp_field"])
        if not raw:
            return {**base, "status": "missing", "reason": "timestamp_field_missing", "checked_at": None, "age_minutes": None}
        observed = _parse_datetime(str(raw))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return {**base, "status": "invalid", "reason": "timestamp_unreadable", "checked_at": None, "age_minutes": None}

    age = _age_minutes(now, observed)
    if age < -5:
        status, reason = "invalid", "timestamp_in_future"
    elif age <= float(source["max_age_minutes"]):
        status, reason = "fresh", "timestamp_within_max_age"
    else:
        status, reason = "stale", "timestamp_exceeds_max_age"
    return {**base, "status": status, "reason": reason, "checked_at": _iso_z(observed), "age_minutes": age}


def _evaluate_heartbeat_source(root: Path, source: dict[str, Any], now: datetime) -> dict[str, Any]:
    path = root / source["path"]
    base = {
        "id": source["id"],
        "label": source["label"],
        "kind": source["kind"],
        "path": source["path"],
        "block_monitoring_if_unfresh": source["block_monitoring_if_unfresh"],
        "required_for_no_event_conclusion": source["required_for_no_event_conclusion"],
        "affected_signal_families": source["affected_signal_families"],
    }
    if not path.exists():
        return {**base, "status": "missing", "reason": "heartbeat_missing", "checked_at": None, "age_minutes": None, "content_changed": None}
    try:
        heartbeat = _load_json(path)
        observed = _parse_datetime(str(heartbeat["checked_at"]))
    except (OSError, KeyError, ValueError, TypeError, json.JSONDecodeError):
        return {**base, "status": "invalid", "reason": "heartbeat_unreadable", "checked_at": None, "age_minutes": None, "content_changed": None}

    age = _age_minutes(now, observed)
    observed_berlin = observed.astimezone(BERLIN)
    now_berlin = now.astimezone(BERLIN)
    required_after = time.fromisoformat(source["required_after_local_time"])

    if heartbeat.get("source_id") != source["id"]:
        status, reason = "invalid", "heartbeat_source_id_mismatch"
    elif heartbeat.get("status") != "success":
        status, reason = "failed", "latest_heartbeat_not_successful"
    elif age < -5:
        status, reason = "invalid", "heartbeat_in_future"
    elif age > float(source["max_age_minutes"]):
        status, reason = "stale", "heartbeat_exceeds_max_age"
    elif observed_berlin.date() != now_berlin.date():
        status, reason = "stale", "heartbeat_not_from_current_berlin_date"
    elif observed_berlin.timetz().replace(tzinfo=None) < required_after:
        status, reason = "stale", "heartbeat_before_required_morning_window"
    else:
        status, reason = "fresh", "successful_refresh_confirmed_for_current_morning_cycle"

    return {
        **base,
        "status": status,
        "reason": reason,
        "checked_at": _iso_z(observed),
        "age_minutes": age,
        "content_changed": heartbeat.get("content_changed"),
        "trigger": heartbeat.get("trigger"),
    }


def evaluate_gate(*, root: Path, config: dict[str, Any], now: datetime) -> dict[str, Any]:
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now = now.astimezone(timezone.utc)
    sources: list[dict[str, Any]] = []
    for source in config["sources"]:
        if source["kind"] == "timestamp":
            result = _evaluate_timestamp_source(root, source, now)
        elif source["kind"] == "heartbeat":
            result = _evaluate_heartbeat_source(root, source, now)
        else:
            raise ValueError(f"Unsupported freshness source kind: {source['kind']}")
        if result["status"] not in VALID_SOURCE_STATUSES:
            raise ValueError(f"Unsupported source status: {result['status']}")
        sources.append(result)

    unfresh = [source for source in sources if source["status"] != "fresh"]
    blocking = [source for source in unfresh if source["block_monitoring_if_unfresh"]]
    no_event_blockers = [source for source in unfresh if source["required_for_no_event_conclusion"]]
    affected_families = sorted({family for source in unfresh for family in source["affected_signal_families"]})

    if blocking:
        overall_status = "blocked"
        decision = "block"
    elif unfresh:
        overall_status = "degraded"
        decision = "proceed_degraded"
    else:
        overall_status = "ok"
        decision = "proceed"

    counts = {status: sum(1 for source in sources if source["status"] == status) for status in sorted(VALID_SOURCE_STATUSES)}
    return {
        "schema_version": config["schema_version"],
        "dataset_id": "source-freshness-gate",
        "generated_at": _iso_z(now),
        "berlin_date": now.astimezone(BERLIN).date().isoformat(),
        "timezone": config["timezone"],
        "morning_cycle": config["morning_cycle"],
        "population": {
            "source_count": len(sources),
            "fresh_count": counts["fresh"],
            "stale_count": counts["stale"],
            "missing_count": counts["missing"],
            "failed_count": counts["failed"],
            "invalid_count": counts["invalid"],
        },
        "overall_status": overall_status,
        "monitoring": {
            "decision": decision,
            "allowed": not blocking,
            "no_event_conclusion_allowed": not no_event_blockers,
            "unfresh_source_ids": [source["id"] for source in unfresh],
            "blocking_source_ids": [source["id"] for source in blocking],
            "no_event_blocking_source_ids": [source["id"] for source in no_event_blockers],
            "affected_signal_families": affected_families,
        },
        "sources": sources,
        "quality": {
            "status": overall_status,
            "freshness_basis": "successful current-cycle refresh heartbeats for all monitored morning sources",
            "unchanged_content_policy": "a successful current-cycle heartbeat is fresh even when content_changed is false",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Materialize the Fantasy Operations source freshness gate.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--root", default=str(REPO_ROOT))
    parser.add_argument("--output")
    parser.add_argument("--now", help="Optional ISO timestamp for deterministic tests/debugging.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = root / config_path
    config = _load_json(config_path)
    now = _parse_datetime(args.now) if args.now else datetime.now(timezone.utc)
    report = evaluate_gate(root=root, config=config, now=now)
    output_path = Path(args.output) if args.output else root / config["output"]
    if not output_path.is_absolute():
        output_path = root / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        "Source freshness gate: status={}; fresh={}/{}; decision={}; no_event_conclusion_allowed={}.".format(
            report["overall_status"],
            report["population"]["fresh_count"],
            report["population"]["source_count"],
            report["monitoring"]["decision"],
            report["monitoring"]["no_event_conclusion_allowed"],
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
