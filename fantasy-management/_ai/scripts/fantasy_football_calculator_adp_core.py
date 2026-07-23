"""Core parsing and validation for Fantasy Football Calculator ADP."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

API_BASE = "https://fantasyfootballcalculator.com/api/v1/adp"
WEBSITE = "https://fantasyfootballcalculator.com/"
SOURCE_ID = "fantasy-football-calculator"
SOURCE_NAME = "Fantasy Football Calculator"
SCHEMA_VERSION = 1
ACTUAL_TEAMS = 6
MIN_ROWS = 80
DEFAULT_MAX_STALE_DAYS = 45
POSITIONS = {"QB", "RB", "WR", "TE", "DEF", "PK"}
OFFENSE = {"QB", "RB", "WR", "TE"}
SOURCE_ROOT = (
    "fantasy-management/sources/external-rankings/adp/"
    "fantasy-football-calculator"
)
ANALYSIS_METADATA = f"{SOURCE_ROOT}/analysis-metadata.json"
DIRECT_FETCHER = (
    "fantasy-management/_ai/scripts/fetch_fantasy_football_calculator_adp.py"
)
USER_AGENT = "Mozilla/5.0 (compatible; MightyGiantsFantasy/1.0)"

FORMAT_CONFIGS: dict[str, dict[str, Any]] = {
    "ppr-8-team": {
        "ranking_id": "redraft-ppr-8-team",
        "ranking_name": "Fantasy Football Calculator Redraft PPR 8-Team ADP",
        "api_format": "ppr",
        "type_aliases": {"ppr"},
        "teams": 8,
        "source_team_count": 8,
        "scoring": "ppr",
        "two_qb": False,
        "role": "small_league_full_ppr_draft_cost",
    },
    "2qb-10-team": {
        "ranking_id": "redraft-2qb-10-team",
        "ranking_name": "Fantasy Football Calculator Redraft 2-QB 10-Team ADP",
        "api_format": "2qb",
        "type_aliases": {"2qb", "twoqb"},
        "teams": 10,
        "source_team_count": 10,
        "scoring": "source_default_not_combined_with_ppr",
        "two_qb": True,
        "role": "two_qb_draft_cost_and_quarterback_scarcity",
    },
}

CSV_FIELDS = [
    "name", "Rank", "source_rank", "position", "team", "source_player_id",
    "adp", "adp_formatted", "times_drafted", "high", "low", "stdev", "bye",
    "source_format", "source_team_count", "actual_league_team_count",
    "sample_total_drafts", "sample_start_date", "sample_end_date",
]


class FantasyFootballCalculatorFetchError(RuntimeError):
    """Raised when an FFC response cannot be trusted or normalized safely."""


def token(value: Any) -> str:
    return "".join(c for c in str(value or "").casefold() if c.isalnum())


def parse_timestamp(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _date(value: Any, field: str) -> date:
    try:
        return date.fromisoformat(str(value).strip())
    except (TypeError, ValueError, AttributeError) as exc:
        raise FantasyFootballCalculatorFetchError(
            f"Invalid FFC {field}: {value!r}"
        ) from exc


def _number(
    value: Any,
    field: str,
    name: str,
    minimum: Decimal = Decimal("0"),
) -> Decimal:
    if isinstance(value, bool):
        raise FantasyFootballCalculatorFetchError(
            f"Invalid FFC {field} for {name}: {value!r}"
        )
    try:
        parsed = Decimal(str(value).strip())
    except (InvalidOperation, ValueError, AttributeError) as exc:
        raise FantasyFootballCalculatorFetchError(
            f"Invalid FFC {field} for {name}: {value!r}"
        ) from exc
    if not parsed.is_finite() or parsed < minimum:
        raise FantasyFootballCalculatorFetchError(
            f"Invalid FFC {field} for {name}: {value!r}"
        )
    return parsed


def _integer(value: Any, field: str, name: str, minimum: int = 0) -> int:
    parsed = _number(value, field, name, Decimal(minimum))
    if parsed != parsed.to_integral_value():
        raise FantasyFootballCalculatorFetchError(
            f"FFC {field} for {name} must be an integer: {value!r}"
        )
    return int(parsed)


def _csv_number(value: Decimal) -> int | str:
    if value == value.to_integral_value():
        return int(value)
    return format(value.normalize(), "f")


def _position(value: Any, name: str) -> str:
    raw = token(value).upper()
    aliases = {
        "DST": "DEF", "DEFENSE": "DEF", "D": "DEF",
        "K": "PK", "KICKER": "PK",
    }
    normalized = aliases.get(raw, raw)
    if normalized not in POSITIONS:
        raise FantasyFootballCalculatorFetchError(
            f"Unexpected FFC position for {name}: {value!r}"
        )
    return normalized


def _bye(value: Any, name: str) -> int | str:
    if value is None or str(value).strip() in {"", "-"}:
        return ""
    result = _integer(value, "bye", name)
    if result > 18:
        raise FantasyFootballCalculatorFetchError(
            f"Invalid FFC bye for {name}: {result}"
        )
    return result


def request_parameters(config: dict[str, Any], season: int) -> dict[str, str]:
    return {
        "teams": str(config["teams"]),
        "year": str(season),
        "position": "all",
    }


def build_source_url(
    config: dict[str, Any],
    season: int,
    base_url: str = API_BASE,
) -> str:
    path = f"{base_url.rstrip('/')}/{config['api_format']}"
    return f"{path}?{urllib.parse.urlencode(request_parameters(config, season))}"


def fetch_payload(
    config: dict[str, Any],
    season: int,
    timeout: int,
) -> tuple[dict[str, Any], dict[str, str], str]:
    url = build_source_url(config, season)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            body = response.read().decode(charset, errors="replace")
            headers = {
                "etag": response.headers.get("ETag") or "",
                "last_modified": response.headers.get("Last-Modified") or "",
                "content_type": response.headers.get("Content-Type") or "",
            }
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise FantasyFootballCalculatorFetchError(
            f"FFC fetch failed for {config['ranking_id']}: {exc}"
        ) from exc
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise FantasyFootballCalculatorFetchError(
            f"FFC response is not JSON for {config['ranking_id']}: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise FantasyFootballCalculatorFetchError(
            f"FFC response is not an object for {config['ranking_id']}"
        )
    return payload, headers, url


def sample_quality(total: int) -> str:
    if total >= 250:
        return "high_sample"
    if total >= 50:
        return "medium_sample"
    if total >= 10:
        return "low_sample"
    return "insufficient_sample"


def validate_payload(
    payload: dict[str, Any],
    config: dict[str, Any],
    *,
    season: int,
    fetched_at: datetime,
    max_stale_days: int = DEFAULT_MAX_STALE_DAYS,
) -> dict[str, Any]:
    if token(payload.get("status")) != "success":
        raise FantasyFootballCalculatorFetchError(
            f"Unexpected FFC status for {config['ranking_id']}: "
            f"{payload.get('status')!r}"
        )
    meta, players = payload.get("meta"), payload.get("players")
    if not isinstance(meta, dict) or not isinstance(players, list) or not players:
        raise FantasyFootballCalculatorFetchError(
            f"FFC payload is missing meta or players for {config['ranking_id']}"
        )
    if not all(isinstance(item, dict) for item in players):
        raise FantasyFootballCalculatorFetchError(
            f"FFC players contain non-object entries for {config['ranking_id']}"
        )
    if token(meta.get("type")) not in config["type_aliases"]:
        raise FantasyFootballCalculatorFetchError(
            f"Unexpected FFC type for {config['ranking_id']}: {meta.get('type')!r}"
        )
    teams = _integer(meta.get("teams"), "meta.teams", config["ranking_id"], 1)
    if teams != config["teams"]:
        raise FantasyFootballCalculatorFetchError(
            f"Unexpected FFC team count for {config['ranking_id']}: {teams}"
        )
    if meta.get("year") not in (None, ""):
        observed_year = _integer(
            meta.get("year"), "meta.year", config["ranking_id"], 2000
        )
        if observed_year != season:
            raise FantasyFootballCalculatorFetchError(
                f"Unexpected FFC season for {config['ranking_id']}: {observed_year}"
            )
    total = _integer(
        meta.get("total_drafts"),
        "meta.total_drafts",
        config["ranking_id"],
        1,
    )
    rounds = _integer(meta.get("rounds"), "meta.rounds", config["ranking_id"], 1)
    start = _date(meta.get("start_date"), "meta.start_date")
    end = _date(meta.get("end_date"), "meta.end_date")
    if start > end or end > fetched_at.date():
        raise FantasyFootballCalculatorFetchError(
            f"Invalid FFC sample dates for {config['ranking_id']}: {start}..{end}"
        )
    age_days = (fetched_at.date() - end).days
    if age_days > max_stale_days:
        raise FantasyFootballCalculatorFetchError(
            f"stale FFC sample for {config['ranking_id']}: {age_days} days old"
        )
    return {
        "type": str(meta.get("type") or ""),
        "teams": teams,
        "rounds": rounds,
        "total_drafts": total,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "age_days": age_days,
        "quality": sample_quality(total),
    }


def parse_players(
    payload: dict[str, Any],
    config: dict[str, Any],
    sample: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    identifiers: set[str] = set()
    source_counts: Counter[str] = Counter()
    excluded: Counter[str] = Counter()
    tolerance = Decimal("0.11")
    for source_rank, player in enumerate(payload["players"], start=1):
        name = str(player.get("name") or "").strip()
        player_id = str(player.get("player_id") or "").strip()
        if not name or not player_id:
            raise FantasyFootballCalculatorFetchError(
                "FFC player is missing name or player_id"
            )
        if player_id in identifiers:
            raise FantasyFootballCalculatorFetchError(
                f"Duplicate FFC player_id: {player_id}"
            )
        identifiers.add(player_id)
        pos = _position(player.get("position"), name)
        source_counts[pos] += 1
        adp = _number(player.get("adp"), "adp", name, Decimal("0.01"))
        high = _number(player.get("high"), "high", name, Decimal("0.01"))
        low = _number(player.get("low"), "low", name, Decimal("0.01"))
        stdev = _number(player.get("stdev"), "stdev", name)
        drafted = _integer(player.get("times_drafted"), "times_drafted", name, 1)
        if high > low or adp + tolerance < high or adp - tolerance > low:
            raise FantasyFootballCalculatorFetchError(
                f"FFC ADP outside high/low for {name}: "
                f"high={high}, adp={adp}, low={low}"
            )
        if pos not in OFFENSE:
            excluded[pos] += 1
            continue
        rows.append({
            "name": name,
            "Rank": 0,
            "source_rank": source_rank,
            "position": pos,
            "team": str(player.get("team") or "").strip().upper(),
            "source_player_id": player_id,
            "adp": _csv_number(adp),
            "adp_formatted": str(player.get("adp_formatted") or "").strip(),
            "times_drafted": drafted,
            "high": _csv_number(high),
            "low": _csv_number(low),
            "stdev": _csv_number(stdev),
            "bye": _bye(player.get("bye"), name),
            "source_format": config["api_format"],
            "source_team_count": config["teams"],
            "actual_league_team_count": ACTUAL_TEAMS,
            "sample_total_drafts": sample["total_drafts"],
            "sample_start_date": sample["start_date"],
            "sample_end_date": sample["end_date"],
            "_adp": adp,
        })
    rows.sort(
        key=lambda row: (
            row["_adp"],
            -row["times_drafted"],
            row["source_player_id"],
        )
    )
    for rank, row in enumerate(rows, start=1):
        row["Rank"] = rank
        row.pop("_adp")
    if len(rows) < MIN_ROWS:
        raise FantasyFootballCalculatorFetchError(
            f"Too few offensive FFC rows for {config['ranking_id']}: {len(rows)}"
        )
    return rows, {
        "source_player_count": len(payload["players"]),
        "normalized_player_count": len(rows),
        "source_position_counts": dict(sorted(source_counts.items())),
        "excluded_position_counts": dict(sorted(excluded.items())),
        "normalized_rank_unique": len(rows) == len({row["Rank"] for row in rows}),
    }
