#!/usr/bin/env python3
"""Build a deterministic GitHub Actions health snapshot from workflow-monitoring.yaml."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


JsonDict = dict[str, Any]
ApiGet = Callable[[str], JsonDict]


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def iso_time(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


TRANSIENT_HTTP_STATUSES = frozenset({429, 500, 502, 503, 504})
DEFAULT_RETRY_DELAYS_SECONDS = (2.0, 5.0, 10.0)
MAX_RETRY_AFTER_SECONDS = 30.0
JITTER_MAX_SECONDS = 1.0


def retry_after_seconds(headers: Any) -> float:
    try:
        value = float(headers.get("Retry-After")) if headers is not None else 0.0
    except (TypeError, ValueError):
        return 0.0
    return min(max(value, 0.0), MAX_RETRY_AFTER_SECONDS)


def github_getter(
    repository: str,
    token: str,
    *,
    opener: Callable[..., Any] = urlopen,
    sleep: Callable[[float], None] = time.sleep,
    jitter: Callable[[], float] = lambda: random.uniform(0.0, JITTER_MAX_SECONDS),
    retry_delays: tuple[float, ...] = DEFAULT_RETRY_DELAYS_SECONDS,
) -> ApiGet:
    """Read-only GitHub API getter. Transient failures (5xx, 429, network aborts, timeouts) are retried with
    backoff; 401/403/404/422 and other client errors fail immediately."""
    base = f"https://api.github.com/repos/{repository}"

    def get(path: str) -> JsonDict:
        request = Request(
            f"{base}{path}",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "fantasy-app-workflow-health-snapshot",
            },
        )
        for attempt in range(len(retry_delays) + 1):
            wait = 0.0
            try:
                with opener(request, timeout=30) as response:
                    return json.loads(response.read().decode("utf-8"))
            except HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")
                error = RuntimeError(f"GitHub API {exc.code} for {path}: {body}")
                if exc.code not in TRANSIENT_HTTP_STATUSES or attempt >= len(retry_delays):
                    raise error from exc
                reason = f"HTTP {exc.code}"
                wait = retry_after_seconds(exc.headers)
            except (URLError, TimeoutError, ConnectionError) as exc:
                error = RuntimeError(f"GitHub API request failed for {path}: {exc}")
                if attempt >= len(retry_delays):
                    raise error from exc
                reason = type(exc).__name__
            delay = max(retry_delays[attempt], wait) + jitter()
            print(
                f"::warning::GitHub API read {path} failed transiently ({reason}); "
                f"retrying in {delay:.1f} s (attempt {attempt + 2}/{len(retry_delays) + 1}).",
                file=sys.stderr,
            )
            sleep(delay)
        raise AssertionError("unreachable")  # pragma: no cover

    return get


def load_policy(path: Path) -> JsonDict:
    try:
        import yaml  # type: ignore
    except ImportError as exc:
        raise RuntimeError("PyYAML is required to read workflow-monitoring.yaml") from exc
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise RuntimeError("Monitoring policy must be a YAML object")
    return loaded


def workflow_files(root: Path) -> set[str]:
    directory = root / ".github" / "workflows"
    result: set[str] = set()
    for suffix in ("*.yml", "*.yaml"):
        for path in directory.glob(suffix):
            if path.is_file():
                result.add(path.relative_to(root).as_posix())
    return result


def incident_key(workflow_path: str, incident_type: str, onset: str) -> str:
    raw = f"{workflow_path}|{incident_type}|{onset}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:24]


def _cron_field(spec: str, low: int, high: int) -> set[int]:
    values: set[int] = set()
    for part in spec.split(","):
        base, _, step_text = part.partition("/")
        step = int(step_text) if step_text else 1
        if base == "*":
            start, end = low, high
        elif "-" in base:
            first, last = base.split("-", 1)
            start, end = int(first), int(last)
        else:
            start = int(base)
            end = high if step_text else start
        values.update(range(start, end + 1, step))
    return values


def parse_cron(expression: str) -> tuple[set[int], set[int], set[int], set[int], set[int], bool, bool]:
    fields = expression.split()
    if len(fields) != 5:
        raise ValueError(f"Unsupported cron expression: {expression!r}")
    minutes = _cron_field(fields[0], 0, 59)
    hours = _cron_field(fields[1], 0, 23)
    days = _cron_field(fields[2], 1, 31)
    months = _cron_field(fields[3], 1, 12)
    weekdays = {value % 7 for value in _cron_field(fields[4], 0, 7)}
    return minutes, hours, days, months, weekdays, fields[2] != "*", fields[4] != "*"


def count_cron_slots(expressions: list[str], timezone_name: str, start: datetime, end: datetime) -> int:
    """Count distinct minutes in (start, end] matching any expression, evaluated in the target timezone."""
    zone = ZoneInfo(timezone_name)
    parsed = [parse_cron(item) for item in expressions]
    count = 0
    cursor = start.replace(second=0, microsecond=0) + timedelta(minutes=1)
    while cursor <= end:
        local = cursor.astimezone(zone)
        weekday = (local.weekday() + 1) % 7
        for minutes, hours, days, months, weekdays, day_restricted, weekday_restricted in parsed:
            if local.minute not in minutes or local.hour not in hours or local.month not in months:
                continue
            if day_restricted and weekday_restricted:
                day_ok = local.day in days or weekday in weekdays
            else:
                day_ok = local.day in days and weekday in weekdays
            if day_ok:
                count += 1
                break
        cursor += timedelta(minutes=1)
    return count


def load_scheduler_targets(root: Path, config_path: str) -> dict[str, JsonDict]:
    path = root / config_path
    if not path.is_file():
        return {}
    config = json.loads(path.read_text(encoding="utf-8"))
    return {item["path"]: item for item in config.get("targets", []) if item.get("path")}


def evaluate_run_volume(target: JsonDict, runs: list[JsonDict], settings: JsonDict, evaluation: JsonDict, now: datetime) -> JsonDict | None:
    """Compare scheduler-dispatched runs of the last window with the planned slots (informational, never paging)."""
    window_hours = int(settings.get("windowHours", 24))
    factor = float(settings.get("warningFactor", 2))
    offset = int(settings.get("warningOffset", 2))
    cancelled_min = int(settings.get("cancelledWarningMinimum", 5))
    start = now - timedelta(hours=window_hours)
    default_branch = evaluation.get("defaultBranch", "main")

    observed = 0
    cancelled = 0
    for item in runs:
        if item.get("event") != "repository_dispatch":
            continue
        head_branch = item.get("head_branch")
        if head_branch and head_branch != default_branch:
            continue
        created = parse_time(item.get("created_at"))
        if not created or created < start:
            continue
        observed += 1
        if item.get("conclusion") == "cancelled":
            cancelled += 1

    # A game-window target is bounded by its dense cron; the idle cron is never denser.
    expected = count_cron_slots(target.get("cron") or [], target.get("timezone", "UTC"), start, now)
    ratio = round(observed / expected, 2) if expected else None
    warning = observed > factor * expected + offset
    cancelled_warning = cancelled >= cancelled_min and cancelled > expected
    return {
        "windowHours": window_hours,
        "observed24h": observed,
        "expected24h": expected,
        "ratio": ratio,
        "warning": warning,
        "cancelled24h": cancelled,
        "cancelledWarning": cancelled_warning,
        "warningThreshold": factor * expected + offset,
        "truncated": len(runs) >= 100 and bool(runs) and (parse_time(runs[-1].get("created_at")) or now) >= start,
    }


def run_summary(run: JsonDict | None) -> JsonDict | None:
    if not run:
        return None
    return {
        "id": run.get("id"),
        "event": run.get("event"),
        "headBranch": run.get("head_branch"),
        "headSha": run.get("head_sha"),
        "status": run.get("status"),
        "conclusion": run.get("conclusion"),
        "createdAt": run.get("created_at"),
        "updatedAt": run.get("updated_at"),
        "url": run.get("html_url"),
    }


def relevant_completed_runs(runs: list[JsonDict], entry: JsonDict, evaluation: JsonDict) -> tuple[list[JsonDict], list[str]]:
    relevant_events = set(entry.get("relevantEvents") or [])
    default_branch = evaluation.get("defaultBranch", "main")
    healthy = set(evaluation.get("healthyConclusions") or ["success"])
    unhealthy = set(evaluation.get("unhealthyConclusions") or ["failure"])
    ignored = set(evaluation.get("ignoredConclusions") or [])
    accepted = healthy | unhealthy
    unknown: list[str] = []
    filtered: list[JsonDict] = []

    for run in runs:
        if run.get("event") not in relevant_events:
            continue
        head_branch = run.get("head_branch")
        if head_branch and head_branch != default_branch:
            continue
        if run.get("status") != "completed":
            continue
        conclusion = run.get("conclusion")
        if conclusion in ignored:
            continue
        if conclusion not in accepted:
            unknown.append(str(conclusion))
            continue
        filtered.append(run)

    filtered.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    return filtered, unknown


def relevant_inflight_runs(runs: list[JsonDict], entry: JsonDict, evaluation: JsonDict) -> list[JsonDict]:
    relevant_events = set(entry.get("relevantEvents") or [])
    default_branch = evaluation.get("defaultBranch", "main")
    filtered: list[JsonDict] = []

    for run in runs:
        if run.get("event") not in relevant_events:
            continue
        head_branch = run.get("head_branch")
        if head_branch and head_branch != default_branch:
            continue
        status = run.get("status")
        if not status or status == "completed":
            continue
        filtered.append(run)

    filtered.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    return filtered


def evaluate_workflow(
    path: str,
    entry: JsonDict,
    category: JsonDict,
    api_workflow: JsonDict,
    runs: list[JsonDict],
    evaluation: JsonDict,
    now: datetime,
) -> tuple[JsonDict, list[JsonDict]]:
    notify = bool(category.get("notify", False))
    threshold = entry.get("consecutiveFailures", category.get("consecutiveFailures"))
    stale_after = entry.get("staleAfterMinutes")
    api_state = api_workflow.get("state")

    result: JsonDict = {
        "category": entry.get("category"),
        "apiState": api_state,
        "notify": notify,
        "consecutiveFailureThreshold": threshold,
        "staleAfterMinutes": stale_after,
        "status": "disabled" if api_state != "active" else "healthy",
        "failureStreak": 0,
        "latestRelevantRun": None,
        "latestRelevantInFlightRun": None,
        "lastSuccess": None,
        "incidentKeys": [],
    }
    incidents: list[JsonDict] = []

    if api_state != "active" or not (entry.get("relevantEvents") or []):
        return result, incidents

    filtered, unknown = relevant_completed_runs(runs, entry, evaluation)
    inflight = relevant_inflight_runs(runs, entry, evaluation)
    healthy = set(evaluation.get("healthyConclusions") or ["success"])
    unhealthy = set(evaluation.get("unhealthyConclusions") or ["failure"])

    if unknown:
        onset = filtered[0].get("created_at") if filtered else iso_time(now)
        key = incident_key(path, "unknown-conclusion", onset or iso_time(now))
        incidents.append({
            "incidentKey": key,
            "type": "unknown-conclusion",
            "workflow": path,
            "category": entry.get("category"),
            "onset": onset,
            "details": {"conclusions": sorted(set(unknown))},
        })
        result["incidentKeys"].append(key)

    if filtered:
        result["latestRelevantRun"] = run_summary(filtered[0])
    if inflight:
        result["latestRelevantInFlightRun"] = run_summary(inflight[0])

    failure_runs: list[JsonDict] = []
    last_success: JsonDict | None = None
    for run in filtered:
        conclusion = run.get("conclusion")
        if conclusion in healthy:
            last_success = run
            break
        if conclusion in unhealthy:
            failure_runs.append(run)

    if not last_success:
        for run in filtered:
            if run.get("conclusion") in healthy:
                last_success = run
                break

    result["failureStreak"] = len(failure_runs)
    result["lastSuccess"] = run_summary(last_success)

    if notify and isinstance(threshold, int) and threshold > 0 and len(failure_runs) >= threshold:
        oldest_failure = failure_runs[-1]
        onset = oldest_failure.get("created_at") or iso_time(now)
        key = incident_key(path, "failure-streak", onset)
        incidents.append({
            "incidentKey": key,
            "type": "failure-streak",
            "workflow": path,
            "category": entry.get("category"),
            "onset": onset,
            "failureStreak": len(failure_runs),
            "threshold": threshold,
            "latestRun": run_summary(failure_runs[0]),
            "lastSuccess": run_summary(last_success),
        })
        result["incidentKeys"].append(key)

    if notify and isinstance(stale_after, int) and stale_after > 0:
        if last_success:
            success_time = parse_time(last_success.get("updated_at") or last_success.get("created_at"))
            if success_time:
                age_minutes = int((now - success_time).total_seconds() // 60)
                result["successAgeMinutes"] = age_minutes
                if age_minutes > stale_after:
                    onset = last_success.get("updated_at") or last_success.get("created_at") or iso_time(now)
                    key = incident_key(path, "stale-success", onset)
                    incidents.append({
                        "incidentKey": key,
                        "type": "stale-success",
                        "workflow": path,
                        "category": entry.get("category"),
                        "onset": onset,
                        "successAgeMinutes": age_minutes,
                        "staleAfterMinutes": stale_after,
                        "lastSuccess": run_summary(last_success),
                        "latestRun": run_summary(filtered[0]) if filtered else None,
                    })
                    result["incidentKeys"].append(key)
        else:
            # A newly activated weekly audit has no success before the first
            # scheduled due slot; don't page until that slot can finish.
            first_due = parse_time(entry.get("firstDueAt"))
            grace = int(entry.get("firstDueGraceMinutes", 0))
            if first_due is None or now >= first_due + timedelta(minutes=grace):
                onset = "no-success-in-run-window"
                key = incident_key(path, "missing-success-evidence", onset)
                incidents.append({
                    "incidentKey": key,
                    "type": "missing-success-evidence",
                    "workflow": path,
                    "category": entry.get("category"),
                    "onset": onset,
                    "staleAfterMinutes": stale_after,
                    "details": "No successful relevant completed run was found in the configured run window.",
                })
                result["incidentKeys"].append(key)
            else:
                result["awaitingFirstScheduledAudit"] = True

    if incidents:
        result["status"] = "incident"
    return result, incidents


def carry_incident_observation_state(incidents: list[JsonDict], previous: JsonDict | None, now: datetime, renotify_hours: int) -> None:
    previous_by_key = {
        item.get("incidentKey"): item
        for item in (previous or {}).get("incidents", [])
        if item.get("incidentKey")
    }
    previous_generated = parse_time((previous or {}).get("generatedAt"))

    for item in incidents:
        prior = previous_by_key.get(item["incidentKey"])
        if prior:
            first_observed = prior.get("firstObservedAt") or (previous or {}).get("generatedAt") or iso_time(now)
        else:
            first_observed = iso_time(now)
        item["firstObservedAt"] = first_observed
        item["lastObservedAt"] = iso_time(now)

        first_dt = parse_time(first_observed) or now
        current_epoch = int(max(0, (now - first_dt).total_seconds()) // (renotify_hours * 3600)) if renotify_hours > 0 else 0
        previous_epoch = -1
        if prior and previous_generated and renotify_hours > 0:
            previous_epoch = int(max(0, (previous_generated - first_dt).total_seconds()) // (renotify_hours * 3600))
        materially_changed = False
        if prior:
            if item.get("category") != prior.get("category"):
                materially_changed = True
            elif item.get("type") == "failure-streak":
                materially_changed = int(item.get("failureStreak") or 0) > int(prior.get("failureStreak") or 0)
        item["notificationDue"] = prior is None or current_epoch > previous_epoch or materially_changed


def build_snapshot(
    policy: JsonDict,
    repository: str,
    root: Path,
    api_get: ApiGet,
    now: datetime,
    source_sha: str | None = None,
    previous: JsonDict | None = None,
) -> JsonDict:
    evaluation = policy.get("runEvaluation") or {}
    categories = policy.get("categories") or {}
    configured = policy.get("workflows") or {}
    local_files = workflow_files(root)
    configured_files = set(configured)

    incidents: list[JsonDict] = []
    drift: list[JsonDict] = []
    warnings: list[JsonDict] = []
    volume_settings = evaluation.get("runVolume") or {}
    scheduler_targets = (
        load_scheduler_targets(root, volume_settings["scheduleConfig"])
        if volume_settings.get("scheduleConfig")
        else {}
    )

    for path in sorted(local_files - configured_files):
        key = incident_key(path, "unclassified-workflow", path)
        drift.append({"incidentKey": key, "type": "unclassified-workflow", "workflow": path, "onset": path})
    for path in sorted(configured_files - local_files):
        key = incident_key(path, "configured-workflow-missing", path)
        drift.append({"incidentKey": key, "type": "configured-workflow-missing", "workflow": path, "onset": path})

    api_data = api_get("/actions/workflows?per_page=100")
    api_by_path = {item.get("path"): item for item in api_data.get("workflows", []) if item.get("path")}

    workflow_results: JsonDict = {}
    run_limit = max(20, min(100, int(evaluation.get("recentRunsToInspect", 20))))

    for path, entry in configured.items():
        if path not in local_files:
            continue
        api_workflow = api_by_path.get(path)
        if not api_workflow:
            key = incident_key(path, "workflow-not-in-actions-api", path)
            drift.append({"incidentKey": key, "type": "workflow-not-in-actions-api", "workflow": path, "onset": path})
            workflow_results[path] = {"category": entry.get("category"), "status": "configuration-drift", "incidentKeys": [key]}
            continue
        category_name = entry.get("category")
        category = categories.get(category_name)
        if not isinstance(category, dict):
            key = incident_key(path, "unknown-category", str(category_name))
            drift.append({"incidentKey": key, "type": "unknown-category", "workflow": path, "onset": str(category_name)})
            workflow_results[path] = {"category": category_name, "status": "configuration-drift", "incidentKeys": [key]}
            continue

        runs: list[JsonDict] = []
        if api_workflow.get("state") == "active" and (entry.get("relevantEvents") or []):
            event_filter = entry.get("runListEvent")
            if event_filter and event_filter not in (entry.get("relevantEvents") or []):
                raise ValueError(f"Invalid runListEvent for {path}: {event_filter!r}")
            query = f"/actions/workflows/{api_workflow['id']}/runs?per_page={run_limit}"
            if event_filter:
                from urllib.parse import quote
                query += f"&event={quote(event_filter, safe='')}"
            runs_data = api_get(query)
            runs = runs_data.get("workflow_runs", [])
        result, workflow_incidents = evaluate_workflow(path, entry, category, api_workflow, runs, evaluation, now)
        workflow_results[path] = result
        incidents.extend(workflow_incidents)

        target = scheduler_targets.get(path)
        if target and runs and api_workflow.get("state") == "active":
            volume = evaluate_run_volume(target, runs, volume_settings, evaluation, now)
            if volume:
                result["runVolume"] = volume
                for kind, flag in (("multiple-starts", "warning"), ("many-cancelled-runs", "cancelledWarning")):
                    if volume[flag]:
                        warnings.append({
                            "type": kind,
                            "workflow": path,
                            "targetId": target.get("id"),
                            "observed24h": volume["observed24h"],
                            "expected24h": volume["expected24h"],
                            "cancelled24h": volume["cancelled24h"],
                        })

    incidents = drift + incidents
    renotify = int((evaluation.get("notificationDeduplication") or {}).get("reNotifyAfterHours", 24))
    carry_incident_observation_state(incidents, previous, now, renotify)

    return {
        "schemaVersion": 1,
        "generatedAt": iso_time(now),
        "repository": repository,
        "sourceRef": evaluation.get("defaultBranch", "main"),
        "sourceSha": source_sha,
        "policyPath": (policy.get("ownership") or {}).get("canonicalFile"),
        "overall": "incident" if incidents else "healthy",
        "configurationDrift": [item for item in incidents if item.get("type") in {"unclassified-workflow", "configured-workflow-missing", "workflow-not-in-actions-api", "unknown-category"}],
        "incidents": incidents,
        "warnings": warnings,
        "workflows": workflow_results,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--token", default=os.getenv("GITHUB_TOKEN"))
    parser.add_argument("--policy", type=Path, default=Path(".ai-context/manual/workflow-monitoring.yaml"))
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-sha", default=os.getenv("GITHUB_SHA"))
    parser.add_argument("--previous-snapshot", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.token:
        raise RuntimeError("GitHub token is required")
    policy = load_policy(args.policy)
    previous = None
    if args.previous_snapshot and args.previous_snapshot.exists():
        previous = json.loads(args.previous_snapshot.read_text(encoding="utf-8"))
    snapshot = build_snapshot(
        policy=policy,
        repository=args.repository,
        root=args.root,
        api_get=github_getter(args.repository, args.token),
        now=datetime.now(timezone.utc),
        source_sha=args.source_sha,
        previous=previous,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"overall": snapshot["overall"], "incidentCount": len(snapshot["incidents"]), "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
