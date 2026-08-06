#!/usr/bin/env python3
"""Fetch Sleeper platform-wide NFL add/drop activity for Fantasy Management.

The public Sleeper trending endpoint returns a rolling top-N list. This module
stores the latest raw response and a normalized union of add/drop activity. It
never interprets the signal as a ranking, player value, or league-specific fact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

API_BASE_URL = "https://api.sleeper.app/v1/players/nfl/trending"
SOURCE_ID = "sleeper"
SOURCE_KIND = "external_signal"
SIGNAL_KIND = "roster_activity"
SCOPE = "platform_wide"
SPORT = "nfl"
SCHEMA_VERSION = 1
DEFAULT_LOOKBACK_HOURS = 24
DEFAULT_LIMIT = 100
DEFAULT_TIMEOUT = 30
DEFAULT_ATTEMPTS = 3
ACTIVITY_TYPES = ("add", "drop")
ATTRIBUTION = "Trending data provided by Sleeper"
SOURCE_ROOT = Path(
    "fantasy-management/sources/external-signals/roster-activity/sleeper"
)
USER_AGENT = "fantasy-app-fantasy-management/1.0 (+https://github.com/Lolindhir/fantasy-app)"


class SleeperTrendingFetchError(RuntimeError):
    """Raised when Sleeper trending data cannot be fetched or validated safely."""


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def isoformat_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def build_source_url(
    activity_type: str,
    *,
    lookback_hours: int = DEFAULT_LOOKBACK_HOURS,
    limit: int = DEFAULT_LIMIT,
    base_url: str = API_BASE_URL,
) -> str:
    if activity_type not in ACTIVITY_TYPES:
        raise ValueError(f"Unsupported activity type: {activity_type!r}")
    if lookback_hours < 1:
        raise ValueError("lookback_hours must be at least 1")
    if limit < 1:
        raise ValueError("limit must be at least 1")
    query = urllib.parse.urlencode(
        {"lookback_hours": lookback_hours, "limit": limit}
    )
    return f"{base_url.rstrip('/')}/{activity_type}?{query}"


def _response_headers(response: Any) -> dict[str, str]:
    headers = getattr(response, "headers", None)
    if headers is None:
        return {}
    return {
        "etag": headers.get("ETag") or "",
        "last_modified": headers.get("Last-Modified") or "",
        "content_type": headers.get("Content-Type") or "",
    }


def fetch_activity(
    activity_type: str,
    *,
    lookback_hours: int = DEFAULT_LOOKBACK_HOURS,
    limit: int = DEFAULT_LIMIT,
    timeout: int = DEFAULT_TIMEOUT,
    attempts: int = DEFAULT_ATTEMPTS,
    base_url: str = API_BASE_URL,
    opener: Callable[..., Any] = urllib.request.urlopen,
    sleep: Callable[[float], None] = time.sleep,
) -> tuple[list[dict[str, Any]], dict[str, str], str]:
    if attempts < 1:
        raise ValueError("attempts must be at least 1")

    source_url = build_source_url(
        activity_type,
        lookback_hours=lookback_hours,
        limit=limit,
        base_url=base_url,
    )
    request = urllib.request.Request(
        source_url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
    )

    last_error: BaseException | None = None
    for attempt in range(1, attempts + 1):
        try:
            with opener(request, timeout=timeout) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                body = response.read().decode(charset, errors="strict")
                headers = _response_headers(response)
            if not body.strip():
                raise SleeperTrendingFetchError(
                    f"Sleeper {activity_type} response is empty"
                )
            try:
                payload = json.loads(body)
            except json.JSONDecodeError as exc:
                raise SleeperTrendingFetchError(
                    f"Sleeper {activity_type} response is not valid JSON: {exc}"
                ) from exc
            normalized = validate_activity_payload(
                payload, activity_type=activity_type, limit=limit
            )
            return normalized, headers, source_url
        except urllib.error.HTTPError as exc:
            last_error = exc
            retryable = exc.code in {429, 500, 502, 503, 504}
            if not retryable or attempt == attempts:
                raise SleeperTrendingFetchError(
                    f"Sleeper {activity_type} fetch failed with HTTP {exc.code}"
                ) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt == attempts:
                raise SleeperTrendingFetchError(
                    f"Sleeper {activity_type} fetch failed: {exc}"
                ) from exc
        except SleeperTrendingFetchError:
            raise

        sleep(float(2 ** (attempt - 1)))

    raise SleeperTrendingFetchError(
        f"Sleeper {activity_type} fetch failed: {last_error}"
    )


def _parse_count(value: Any, *, player_id: str, activity_type: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SleeperTrendingFetchError(
            f"Sleeper {activity_type} count for {player_id} is not an integer"
        )
    if value < 0:
        raise SleeperTrendingFetchError(
            f"Sleeper {activity_type} count for {player_id} is negative"
        )
    return value


def validate_activity_payload(
    payload: Any, *, activity_type: str, limit: int
) -> list[dict[str, Any]]:
    if activity_type not in ACTIVITY_TYPES:
        raise ValueError(f"Unsupported activity type: {activity_type!r}")
    if not isinstance(payload, list):
        raise SleeperTrendingFetchError(
            f"Sleeper {activity_type} response is not an array"
        )
    if not payload:
        raise SleeperTrendingFetchError(
            f"Sleeper {activity_type} response contains no players"
        )
    if len(payload) > limit:
        raise SleeperTrendingFetchError(
            f"Sleeper {activity_type} response contains {len(payload)} rows, above limit {limit}"
        )

    seen: set[str] = set()
    rows: list[dict[str, Any]] = []
    for rank, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            raise SleeperTrendingFetchError(
                f"Sleeper {activity_type} row {rank} is not an object"
            )
        player_id = str(item.get("player_id") or "").strip()
        if not player_id:
            raise SleeperTrendingFetchError(
                f"Sleeper {activity_type} row {rank} has no player_id"
            )
        if player_id in seen:
            raise SleeperTrendingFetchError(
                f"Duplicate Sleeper {activity_type} player_id: {player_id}"
            )
        seen.add(player_id)
        rows.append(
            {
                "player_id": player_id,
                "count": _parse_count(
                    item.get("count"),
                    player_id=player_id,
                    activity_type=activity_type,
                ),
                "rank": rank,
            }
        )
    return rows


def semantic_fingerprint(
    activity_rows: dict[str, list[dict[str, Any]]],
    *,
    lookback_hours: int,
    limit: int,
) -> str:
    canonical = {
        "lookback_hours": lookback_hours,
        "limit": limit,
        "activity": {
            activity_type: [
                {
                    "player_id": row["player_id"],
                    "count": row["count"],
                    "rank": row["rank"],
                }
                for row in activity_rows[activity_type]
            ]
            for activity_type in ACTIVITY_TYPES
        },
    }
    encoded = json.dumps(
        canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _listed_map(rows: Iterable[dict[str, Any]]) -> dict[str, dict[str, int]]:
    return {
        str(row["player_id"]): {
            "rank": int(row["rank"]),
            "count": int(row["count"]),
        }
        for row in rows
    }


def normalize_players(
    activity_rows: dict[str, list[dict[str, Any]]]
) -> list[dict[str, Any]]:
    maps = {
        activity_type: _listed_map(activity_rows[activity_type])
        for activity_type in ACTIVITY_TYPES
    }
    player_ids = sorted(set(maps["add"]) | set(maps["drop"]))
    players: list[dict[str, Any]] = []
    for player_id in player_ids:
        row: dict[str, Any] = {"sleeper_player_id": player_id}
        for activity_type in ACTIVITY_TYPES:
            listed = maps[activity_type].get(player_id)
            row[activity_type] = (
                {
                    "status": "listed",
                    "rank": listed["rank"],
                    "count": listed["count"],
                }
                if listed
                else {"status": "not_listed", "rank": None, "count": None}
            )
        players.append(row)
    return players


def _previous_activity_map(
    previous: dict[str, Any], activity_type: str
) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}
    players = previous.get("players")
    if not isinstance(players, list):
        return result
    for player in players:
        if not isinstance(player, dict):
            continue
        player_id = str(player.get("sleeper_player_id") or "").strip()
        signal = player.get(activity_type)
        if (
            player_id
            and isinstance(signal, dict)
            and signal.get("status") == "listed"
            and isinstance(signal.get("rank"), int)
            and isinstance(signal.get("count"), int)
        ):
            result[player_id] = {
                "rank": int(signal["rank"]),
                "count": int(signal["count"]),
            }
    return result


def build_comparison(
    previous: dict[str, Any] | None,
    current_activity_rows: dict[str, list[dict[str, Any]]],
    *,
    lookback_hours: int,
    limit: int,
) -> dict[str, Any]:
    if not previous:
        return {
            "baseline": True,
            "comparable": False,
            "reason": "no_previous_successful_snapshot",
            "previous_generated_at": None,
            "material_event_eligible": False,
            "activity": {},
        }

    compatible = (
        previous.get("schema_version") == SCHEMA_VERSION
        and previous.get("provider") == SOURCE_ID
        and previous.get("lookback_hours") == lookback_hours
        and previous.get("limit") == limit
    )
    if not compatible:
        return {
            "baseline": True,
            "comparable": False,
            "reason": "previous_snapshot_configuration_mismatch",
            "previous_generated_at": previous.get("generated_at"),
            "material_event_eligible": False,
            "activity": {},
        }

    activity_changes: dict[str, Any] = {}
    for activity_type in ACTIVITY_TYPES:
        old_map = _previous_activity_map(previous, activity_type)
        new_map = _listed_map(current_activity_rows[activity_type])
        old_ids = set(old_map)
        new_ids = set(new_map)
        entered = sorted(
            new_ids - old_ids, key=lambda player_id: new_map[player_id]["rank"]
        )
        left = sorted(
            old_ids - new_ids, key=lambda player_id: old_map[player_id]["rank"]
        )
        shared = old_ids & new_ids
        rank_changed = [
            {
                "sleeper_player_id": player_id,
                "old_rank": old_map[player_id]["rank"],
                "new_rank": new_map[player_id]["rank"],
                "rank_delta": old_map[player_id]["rank"]
                - new_map[player_id]["rank"],
            }
            for player_id in shared
            if old_map[player_id]["rank"] != new_map[player_id]["rank"]
        ]
        rank_changed.sort(
            key=lambda item: (-abs(item["rank_delta"]), item["sleeper_player_id"])
        )
        count_changed = [
            {
                "sleeper_player_id": player_id,
                "old_count": old_map[player_id]["count"],
                "new_count": new_map[player_id]["count"],
                "count_delta": new_map[player_id]["count"]
                - old_map[player_id]["count"],
            }
            for player_id in shared
            if old_map[player_id]["count"] != new_map[player_id]["count"]
        ]
        count_changed.sort(
            key=lambda item: (-abs(item["count_delta"]), item["sleeper_player_id"])
        )
        activity_changes[activity_type] = {
            "entered_top_n": entered,
            "left_top_n": left,
            "rank_changed": rank_changed,
            "count_changed": count_changed,
        }

    return {
        "baseline": False,
        "comparable": True,
        "reason": "same_configuration_previous_snapshot_available",
        "previous_generated_at": previous.get("generated_at"),
        "material_event_eligible": True,
        "rolling_window_warning": (
            "Count deltas compare two overlapping rolling windows and are not the number "
            "of new transactions since the previous fetch."
        ),
        "activity": activity_changes,
    }


def build_raw_document(
    activity_rows: dict[str, list[dict[str, Any]]],
    response_headers: dict[str, dict[str, str]],
    source_urls: dict[str, str],
    *,
    fetched_at: datetime,
    lookback_hours: int,
    limit: int,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "provider": SOURCE_ID,
        "source_kind": SOURCE_KIND,
        "signal_kind": SIGNAL_KIND,
        "scope": SCOPE,
        "sport": SPORT,
        "fetched_at": isoformat_utc(fetched_at),
        "attribution": ATTRIBUTION,
        "queries": {
            f"{activity_type}_{lookback_hours}h": {
                "activity_type": activity_type,
                "lookback_hours": lookback_hours,
                "limit": limit,
                "source_url": source_urls[activity_type],
                "response_headers": response_headers[activity_type],
                "players": [
                    {"player_id": row["player_id"], "count": row["count"]}
                    for row in activity_rows[activity_type]
                ],
            }
            for activity_type in ACTIVITY_TYPES
        },
    }


def build_latest_document(
    activity_rows: dict[str, list[dict[str, Any]]],
    *,
    fetched_at: datetime,
    lookback_hours: int,
    limit: int,
    previous: dict[str, Any] | None,
) -> dict[str, Any]:
    players = normalize_players(activity_rows)
    add_ids = {row["player_id"] for row in activity_rows["add"]}
    drop_ids = {row["player_id"] for row in activity_rows["drop"]}
    return {
        "schema_version": SCHEMA_VERSION,
        "provider": SOURCE_ID,
        "source_kind": SOURCE_KIND,
        "signal_kind": SIGNAL_KIND,
        "scope": SCOPE,
        "sport": SPORT,
        "generated_at": isoformat_utc(fetched_at),
        "lookback_hours": lookback_hours,
        "limit": limit,
        "attribution": ATTRIBUTION,
        "semantic_fingerprint": semantic_fingerprint(
            activity_rows, lookback_hours=lookback_hours, limit=limit
        ),
        "interpretation": {
            "ranking": False,
            "league_specific": False,
            "top_n_only": True,
            "not_listed_means": "outside_returned_top_n_not_zero_activity",
            "count_window": "rolling",
        },
        "summary": {
            "add_listed": len(activity_rows["add"]),
            "drop_listed": len(activity_rows["drop"]),
            "unique_players": len(players),
            "listed_in_both": len(add_ids & drop_ids),
        },
        "comparison": build_comparison(
            previous,
            activity_rows,
            lookback_hours=lookback_hours,
            limit=limit,
        ),
        "players": players,
    }


def load_previous_latest(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def render_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=False) + "\n"


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def write_documents(
    output_root: Path,
    *,
    raw_document: dict[str, Any],
    latest_document: dict[str, Any],
) -> list[Path]:
    raw_path = output_root / "raw-latest.json"
    latest_path = output_root / "latest.json"
    raw_content = render_json(raw_document)
    latest_content = render_json(latest_document)
    atomic_write_text(raw_path, raw_content)
    atomic_write_text(latest_path, latest_content)
    return [raw_path, latest_path]


def default_repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def run_refresh(
    *,
    repo_root: Path,
    lookback_hours: int = DEFAULT_LOOKBACK_HOURS,
    limit: int = DEFAULT_LIMIT,
    timeout: int = DEFAULT_TIMEOUT,
    attempts: int = DEFAULT_ATTEMPTS,
    base_url: str = API_BASE_URL,
    fetched_at: datetime | None = None,
    output_root: Path | None = None,
    fetcher: Callable[
        ..., tuple[list[dict[str, Any]], dict[str, str], str]
    ] = fetch_activity,
) -> tuple[list[Path], dict[str, Any]]:
    fetched_at = fetched_at or utc_now()
    destination = output_root or (repo_root / SOURCE_ROOT)
    previous = load_previous_latest(destination / "latest.json")

    activity_rows: dict[str, list[dict[str, Any]]] = {}
    response_headers: dict[str, dict[str, str]] = {}
    source_urls: dict[str, str] = {}
    for activity_type in ACTIVITY_TYPES:
        rows, headers, source_url = fetcher(
            activity_type,
            lookback_hours=lookback_hours,
            limit=limit,
            timeout=timeout,
            attempts=attempts,
            base_url=base_url,
        )
        activity_rows[activity_type] = rows
        response_headers[activity_type] = headers
        source_urls[activity_type] = source_url

    raw_document = build_raw_document(
        activity_rows,
        response_headers,
        source_urls,
        fetched_at=fetched_at,
        lookback_hours=lookback_hours,
        limit=limit,
    )
    latest_document = build_latest_document(
        activity_rows,
        fetched_at=fetched_at,
        lookback_hours=lookback_hours,
        limit=limit,
        previous=previous,
    )
    paths = write_documents(
        destination,
        raw_document=raw_document,
        latest_document=latest_document,
    )
    return paths, latest_document


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=default_repo_root())
    parser.add_argument("--lookback-hours", type=int, default=DEFAULT_LOOKBACK_HOURS)
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("--attempts", type=int, default=DEFAULT_ATTEMPTS)
    parser.add_argument("--base-url", default=API_BASE_URL)
    parser.add_argument("--output-root", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        paths, latest = run_refresh(
            repo_root=args.repo_root.resolve(),
            lookback_hours=args.lookback_hours,
            limit=args.limit,
            timeout=args.timeout,
            attempts=args.attempts,
            base_url=args.base_url,
            output_root=args.output_root,
        )
    except (SleeperTrendingFetchError, ValueError, OSError) as exc:
        print(f"Sleeper trending refresh failed: {exc}", file=os.sys.stderr)
        return 1

    for path in paths:
        print(path)
    comparison = latest["comparison"]
    if comparison["baseline"]:
        print("Stored silent Sleeper trending baseline; no material event is eligible.")
    else:
        print("Stored comparable Sleeper trending snapshot and technical deltas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
