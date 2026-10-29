"""Read-only, restart-safe NFL betting-line observation planner (#471).

No network, Git commits, state-branch writes or workflow scheduling here.
A caller obtains the upstream CSV through an explicit trusted Source reader.
This module compares *only* spread and total against the canonical published
NFL Source partition. Its JSON state belongs on a durable isolated technical
branch, NOT in data-source / data-derived or an Actions cache.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import date, datetime, time, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping
from zoneinfo import ZoneInfo

from odds_change_gate import evaluate_game, next_pending_since

SCHEMA_VERSION = 1
LINE_FIELDS = ("SpreadLine", "TotalLine")
UPSTREAM_FIELDS = {"SpreadLine": "spread_line", "TotalLine": "total_line"}
ET = ZoneInfo("America/New_York")


def _timestamp(value: str | None, name: str) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{name}: not an ISO timestamp")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{name}: invalid ISO timestamp") from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError(f"{name}: missing timezone")
    return result.astimezone(timezone.utc)


def _stamp(t: datetime) -> str:
    if not isinstance(t, datetime) or t.tzinfo is None or t.utcoffset() is None:
        raise ValueError("Observation requires a timezone-aware timestamp")
    return t.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _number(value: Any, label: str) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise ValueError(f"{label}: boolean is not a line")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{label}: not numeric") from exc
    if not number.is_finite() or not math.isfinite(float(number)):
        raise ValueError(f"{label}: nonfinite")
    return float(number)


def _lines(row: Mapping[str, Any], game_id: str) -> dict[str, float | None]:
    result = {field: _number(row.get(field), f"{game_id}.{field}") for field in LINE_FIELDS}
    if result["TotalLine"] is not None and result["TotalLine"] <= 0:
        raise ValueError(f"{game_id}: TotalLine must be positive")
    if (result["SpreadLine"] is not None and result["TotalLine"] is not None
            and abs(result["SpreadLine"]) > result["TotalLine"]):
        raise ValueError(f"{game_id}: impossible SpreadLine/TotalLine")
    return result


def _index(payload: Mapping[str, Any], season: int, label: str) -> dict[str, dict]:
    if payload.get("Season") != season or not isinstance(payload.get("Games"), list):
        raise ValueError(f"{label}: incorrect season or Games")
    result = {}
    for game in payload["Games"]:
        if not isinstance(game, dict):
            raise ValueError(f"{label}: invalid game")
        game_id = game.get("GameID")
        if not isinstance(game_id, str) or not game_id.startswith(f"{season}_") or game_id in result:
            raise ValueError(f"{label}: invalid or duplicate GameID")
        result[game_id] = game
    if not result:
        raise ValueError(f"{label}: empty season")
    return result


def read_upstream_lines(path: Path, season: int, expected_ids: set[str]) -> dict[str, dict]:
    """Parse ONLY spread/total from original nflverse games.csv (never prices).

    A partial, malformed or duplicated upstream feed is NOT accepted as a change
    to canonical truth. This function neither downloads nor writes the feed.
    """
    rows = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not {"game_id", *UPSTREAM_FIELDS.values()} <= set(reader.fieldnames):
            raise ValueError("Upstream games.csv lacks required odds columns")
        for row in reader:
            game_id = (row.get("game_id") or "").strip()
            if not game_id.startswith(f"{season}_"):
                continue
            if game_id in rows:
                raise ValueError(f"Duplicate upstream GameID: {game_id}")
            rows[game_id] = _lines({
                field: row.get(upstream) for field, upstream in UPSTREAM_FIELDS.items()
            }, game_id)
    if set(rows) != expected_ids:
        raise ValueError(
            f"Upstream season GameIDs differ from canonical: missing={len(expected_ids - set(rows))}, "
            f"extra={len(set(rows) - expected_ids)}"
        )
    return rows


def _kickoff(game: Mapping[str, Any]) -> datetime | None:
    if not game.get("GameDay"):
        raise ValueError(f"{game.get('GameID')}: missing GameDay")
    if game.get("GameTime") is None:
        return None
    try:
        d = date.fromisoformat(game["GameDay"])
        t = time.fromisoformat(game["GameTime"])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{game.get('GameID')}: invalid kickoff") from exc
    return datetime.combine(d, t, tzinfo=ET).astimezone(timezone.utc)


def _fingerprint(lines: Mapping[str, float | None]) -> str:
    serial = json.dumps(lines, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(serial.encode()).hexdigest()


def plan_observation(
    *,
    season: int,
    schedule: Mapping[str, Any],
    canonical_odds: Mapping[str, Any],
    observed_lines: Mapping[str, Mapping[str, Any]],
    previous_state: Mapping[str, Any] | None,
    observed_at: datetime,
) -> tuple[dict, dict]:
    """Return a publication proposal and next durable state; no side effects.

    The actual main-branch publisher must independently revalidate the Source
    evidence and the latest canonical baseline before writing anything. A
    proposal here is NEVER proof of a successful publication.
    """
    stamp = _stamp(observed_at)
    now = _timestamp(stamp, "observedAt")
    assert now is not None
    if type(season) is not int or season < 1999:
        raise ValueError("Invalid season")
    games = _index(schedule, season, "schedule")
    odds = _index(canonical_odds, season, "canonical odds")
    if set(games) != set(odds) or set(games) != set(observed_lines):
        raise ValueError("Schedule, canonical and upstream season GameID sets differ")
    if previous_state is not None:
        if (previous_state.get("SchemaVersion") != SCHEMA_VERSION
                or previous_state.get("Season") != season
                or not isinstance(previous_state.get("Games"), dict)
                or set(previous_state["Games"]) != set(games)):
            raise ValueError("Invalid or incomplete persisted odds-buffer state")

    next_games = {}
    publish_ids = []
    reasons = {}
    changed = 0
    for game_id in sorted(games):
        published = _lines(odds[game_id], game_id)
        observed = _lines(observed_lines[game_id], game_id)
        fingerprint = _fingerprint(published)
        old = previous_state["Games"][game_id] if previous_state is not None else None
        if old is not None and not isinstance(old, dict):
            raise ValueError(f"{game_id}: invalid persisted state record")
        if old is not None:
            last_seen = _timestamp(old.get("ObservedAt"), f"{game_id}.ObservedAt")
            if last_seen is None or now < last_seen:
                raise ValueError(f"{game_id}: observation went backward")
            checkpoint = _timestamp(old.get("PublishedAt"), f"{game_id}.PublishedAt")
            if checkpoint is None or checkpoint > now:
                raise ValueError(f"{game_id}: invalid PublishedAt checkpoint")
        else:
            checkpoint = None
        # Source may update externally in the daily full sync or another writer.
        # Detect it by semantic line fingerprint and reset stale pending timers.
        baseline_changed = old is None or old.get("PublishedFingerprint") != fingerprint
        published_at = now if baseline_changed else checkpoint
        pending = None if baseline_changed else _timestamp(old.get("PendingSince"), f"{game_id}.PendingSince")
        pending = next_pending_since(
            published=published, observed=observed,
            previous_pending_since=pending, observed_at=now,
        )
        kickoff = _kickoff(games[game_id])
        if published != observed:
            changed += 1
        # Started games are not eligible for fast pregame odds publication.
        if kickoff is None or now >= kickoff:
            reason = "kickoff_unavailable_or_passed"
            should_publish = False
            pending = None
        else:
            decision = evaluate_game(
                game_id, published=published, observed=observed,
                published_at=published_at, pending_since=pending,
                observed_at=now, kickoff_at=kickoff,
            )
            reason = decision.reason
            should_publish = decision.publish
        if should_publish:
            publish_ids.append(game_id)
        reasons[game_id] = reason
        pending_stamp = _stamp(pending) if pending else None
        # An unchanged *semantic* observation must produce identical state
        # bytes. Otherwise a 10-minute observer would cause ~144 technical
        # branch commits/day even when Spread/Total have not changed.
        state_unchanged = bool(
            old and not baseline_changed
            and old.get("ObservedSpreadLine") == observed["SpreadLine"]
            and old.get("ObservedTotalLine") == observed["TotalLine"]
            and old.get("PendingSince") == pending_stamp
            and old.get("PublishedAt") == _stamp(published_at)
        )
        next_games[game_id] = {
            "PublishedFingerprint": fingerprint,
            "PublishedAt": _stamp(published_at),
            "ObservedSpreadLine": observed["SpreadLine"],
            "ObservedTotalLine": observed["TotalLine"],
            "ObservedAt": old["ObservedAt"] if state_unchanged else stamp,
            "PendingSince": pending_stamp,
        }
    plan = {
        "SchemaVersion": SCHEMA_VERSION,
        "Season": season,
        "ObservedAt": stamp,
        "TotalGames": len(games),
        "RelevantNetChanges": changed,
        "PublishableGameIDs": publish_ids,
        "PublicationReasons": {game_id: reasons[game_id] for game_id in publish_ids},
    }
    state = {"SchemaVersion": SCHEMA_VERSION, "Season": season, "Games": next_games}
    return plan, state


def serialize_state(state: Mapping[str, Any]) -> str:
    """Stable bytes for an isolated-branch state writer using optimistic locking."""
    return json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n"
