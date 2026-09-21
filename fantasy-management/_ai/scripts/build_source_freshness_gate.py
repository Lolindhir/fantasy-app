from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, time, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).resolve().parents[3]
TOOLS_DIR = REPO_ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from nfl_season_context import (  # noqa: E402
    NflSeasonContextError,
    resolve_nfl_season_context,
)

BERLIN = ZoneInfo("Europe/Berlin")
DEFAULT_CONFIG = REPO_ROOT / "fantasy-management/automation/source-freshness-gate.json"
DEFAULT_SEASON_POLICY = REPO_ROOT / "fantasy-management/automation/season-aware-operations-policy.json"
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


def _resolve_phase_policy(
    config: dict[str, Any],
    season_policy: dict[str, Any],
    season_context: dict[str, Any],
) -> tuple[bool, dict[str, str]]:
    if config.get("schema_version") != 3:
        raise ValueError("Unexpected source freshness gate schema version")
    if season_policy.get("schema_version") != 1:
        raise ValueError("Unexpected season-aware Operations policy schema version")
    if season_policy.get("season_context_id") != season_context.get("context_id"):
        raise ValueError("Season-aware Operations policy/context mismatch")

    phase = season_context.get("phase")
    module_phases = (
        ((season_policy.get("modules") or {}).get("free_agent_monitoring") or {})
        .get("phases") or {}
    )
    phase_module = module_phases.get(phase)
    if not isinstance(phase_module, dict) or not isinstance(phase_module.get("active"), bool):
        raise ValueError(f"Missing free-agent monitoring policy for phase {phase!r}")
    monitoring_active = phase_module["active"]

    default_relevance = (
        (season_policy.get("defaults") or {}).get("active_module_signal_relevance")
    )
    if default_relevance not in {"required", "secondary", "inactive"}:
        raise ValueError("Invalid default signal-family relevance")

    all_families = sorted({
        family
        for source in config["sources"]
        for family in source["affected_signal_families"]
    })
    relevance = {
        family: (default_relevance if monitoring_active else "inactive")
        for family in all_families
    }
    for family, definition in (season_policy.get("signal_families") or {}).items():
        if family not in relevance:
            continue
        phase_policy = ((definition or {}).get("phases") or {}).get(phase)
        if not isinstance(phase_policy, dict):
            raise ValueError(f"Missing signal-family policy for {family}/{phase}")
        value = phase_policy.get("relevance")
        if value not in {"required", "secondary", "inactive"}:
            raise ValueError(f"Invalid signal-family relevance for {family}/{phase}")
        relevance[family] = value if monitoring_active else "inactive"

    return monitoring_active, relevance


def evaluate_gate(
    *,
    root: Path,
    config: dict[str, Any],
    now: datetime,
    season_policy: dict[str, Any],
    season_context: dict[str, Any],
) -> dict[str, Any]:
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now = now.astimezone(timezone.utc)
    monitoring_active, signal_family_relevance = _resolve_phase_policy(
        config,
        season_policy,
        season_context,
    )
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
        relevance = {
            family: signal_family_relevance[family]
            for family in result["affected_signal_families"]
        }
        result["signal_family_relevance"] = relevance
        result["effective_block_monitoring_if_unfresh"] = bool(
            result["block_monitoring_if_unfresh"]
            and any(value != "inactive" for value in relevance.values())
        )
        result["effective_required_for_no_event_conclusion"] = bool(
            result["required_for_no_event_conclusion"]
            and any(value == "required" for value in relevance.values())
        )
        sources.append(result)

    unfresh = [source for source in sources if source["status"] != "fresh"]
    blocking = [
        source
        for source in unfresh
        if source["effective_block_monitoring_if_unfresh"]
    ]
    no_event_blockers = [
        source
        for source in unfresh
        if source["effective_required_for_no_event_conclusion"]
    ]
    affected_families = sorted({
        family
        for source in unfresh
        for family in source["affected_signal_families"]
        if signal_family_relevance[family] != "inactive"
    })

    if blocking:
        overall_status = "blocked"
    elif unfresh:
        overall_status = "degraded"
    else:
        overall_status = "ok"

    if not monitoring_active:
        decision = "inactive"
    elif blocking:
        decision = "block"
    elif unfresh:
        decision = "proceed_degraded"
    else:
        decision = "proceed"

    counts = {status: sum(1 for source in sources if source["status"] == status) for status in sorted(VALID_SOURCE_STATUSES)}
    return {
        "schema_version": config["schema_version"],
        "dataset_id": "source-freshness-gate",
        "generated_at": _iso_z(now),
        "berlin_date": now.astimezone(BERLIN).date().isoformat(),
        "timezone": config["timezone"],
        "season_context": {
            "context_id": season_context["context_id"],
            "season": season_context["season"],
            "as_of_date": season_context["as_of_date"],
            "phase": season_context["phase"],
            "regular_season": season_context["regular_season"],
            "source": season_context["source"],
        },
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
            "active": monitoring_active,
            "decision": decision,
            "allowed": bool(monitoring_active and not blocking),
            "no_event_conclusion_allowed": bool(
                monitoring_active and not no_event_blockers
            ),
            "signal_family_relevance": signal_family_relevance,
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
            "consumer_readiness_policy": "technical freshness is evaluated separately from phase-aware signal criticality",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Materialize the Fantasy Operations source freshness gate.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--root", default=str(REPO_ROOT))
    parser.add_argument("--season-policy", default=str(DEFAULT_SEASON_POLICY))
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
    season_policy_path = Path(args.season_policy)
    if not season_policy_path.is_absolute():
        season_policy_path = root / season_policy_path
    season_policy = _load_json(season_policy_path)
    now = _parse_datetime(args.now) if args.now else datetime.now(timezone.utc)
    try:
        season_context = resolve_nfl_season_context(
            root,
            as_of=now.astimezone(BERLIN).date(),
        )
    except NflSeasonContextError as exc:
        raise SystemExit(f"Unable to resolve canonical NFL season context: {exc}") from exc
    report = evaluate_gate(
        root=root,
        config=config,
        now=now,
        season_policy=season_policy,
        season_context=season_context,
    )
    output_path = Path(args.output) if args.output else root / config["output"]
    if not output_path.is_absolute():
        output_path = root / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        "Source freshness gate: phase={}; active={}; status={}; fresh={}/{}; decision={}; no_event_conclusion_allowed={}.".format(
            report["season_context"]["phase"],
            report["monitoring"]["active"],
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
