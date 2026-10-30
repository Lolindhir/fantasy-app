"""lifecycle-v1: league Status, Phase, trade and waiver state for one instant (ADR-073, Issue #1199).

Exact port of the lifecycle code of RequestLeague.ps1, LeagueUtils.psm1 (Resolve-LeagueStatusState and the draft
helpers), WaiverUtils.psm1 (Resolve-LeagueNextWaiverRunUtc) and LeagueOverviewUtils.psm1; no new rule. A model is a pure
function of its explicit inputs: it reads no files and no league configuration, and it never reads the clock. The
instant to judge (``at_utc``) is an input; the instants at which the clock-dependent part may change are part of the
result (``Boundaries``).

Rules in short (league-lifecycle.yaml has the full chain): provider ``complete`` -> Completed; provider ``playoffs`` or a
scored playoff start week -> Playoffs; drafts of the season decide Draft-Season / Off-Season phases (Pre Draft, In Draft,
Between Drafts, Cap Deadline Open, Cap Check, Post Cap Check); otherwise Pre-Season until 7 days before the first
regular-season kickoff and In-Season afterwards. Known v1 quirks stay (CutsAllowed constant, trade deadline against
CurrentWeek, cap window in UTC calendar days) and are candidates for ``lifecycle-v2``.
Immutable after its first productive use; any change is ``lifecycle-v2``.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from types import MappingProxyType
from typing import Any, Mapping, Sequence
from zoneinfo import ZoneInfo

MODEL_ID = "lifecycle-v1"
KIND = "lifecycle"

PARAMS = MappingProxyType({
    "SeasonStartLeadDays": 7,
    "OpenDraftStatuses": ("Virtual", "PreDraft", "Drafting"),
    "LiveDraftStatus": "Drafting",
    "CompletedDraftStatus": "Complete",
    "WaiverTimeZone": "America/Los_Angeles",
    "ValidatedWaiverModes": (1, 2),
    "WaiverLookaheadDays": 7,
    "TradeDeadlineDisabledWeek": 99,
})

UTC = timezone.utc
_INT_TEXT = re.compile(r"^[+-]?[0-9]+$")


@dataclass(frozen=True)
class Game:
    """One regular-season NFL game. ``key`` is the App game ID (date prefix first) used to find the first open game."""

    week: int
    key: str
    kickoff_utc: datetime | None
    final: bool


@dataclass(frozen=True)
class Facts:
    """Explicit inputs of the model; the caller reads them from canonical facts, products and data-meta."""

    season: int
    provider_status: str
    settings: Mapping[str, Any]
    final_scored_week: int
    last_league_week: int
    drafts: Sequence[Mapping[str, Any]]
    games: Sequence[Game]
    cap_deadline: datetime | None
    cap_buffer_days: int


def _int0(value: Any, name: str) -> int:
    """[int]$value of the PowerShell version: absent -> 0, integers and integer text pass, anything else is an error."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return 0
    if isinstance(value, bool):
        raise ValueError(f"{name} must be an integer, got {value!r}")
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value == int(value):
        return int(value)
    if isinstance(value, str) and _INT_TEXT.fullmatch(value.strip()):
        return int(value.strip())
    raise ValueError(f"{name} must be an integer, got {value!r}")


def _iso(moment: datetime | None) -> str | None:
    return None if moment is None else moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _same(left: Any, right: str) -> bool:
    """PowerShell -eq / -in on strings ignores case; the status comparisons keep that."""
    return str(left).casefold() == right.casefold()


def _text_set(value: Any) -> bool:
    return value is not None and bool(str(value).strip())


def trade_deadline_week(trade_deadline: Any) -> int | None:
    """Resolve-LeagueTradeDeadlineWeek: null for absent, non-numeric, non-positive or the Sleeper disabled marker 99."""
    if trade_deadline is None or not str(trade_deadline).strip():
        return None
    text = str(trade_deadline).strip()
    if not _INT_TEXT.fullmatch(text):
        return None
    week = int(text)
    if week <= 0 or week == PARAMS["TradeDeadlineDisabledWeek"]:
        return None
    return week


def season_kickoff(games: Sequence[Game]) -> datetime | None:
    """Get-LeagueSeasonKickoffUtc: the earliest regular-season kickoff."""
    kickoffs = [game.kickoff_utc for game in games if game.kickoff_utc is not None]
    return min(kickoffs) if kickoffs else None


def playoff_start(games: Sequence[Game], playoff_start_week: int) -> datetime | None:
    """Get-LeaguePlayoffStartUtc: the earliest regular-season kickoff of the fantasy playoff start week."""
    if playoff_start_week <= 0:
        return None
    kickoffs = [game.kickoff_utc for game in games if game.week == playoff_start_week and game.kickoff_utc is not None]
    return min(kickoffs) if kickoffs else None


def current_week(games: Sequence[Game]) -> int:
    """Week of the first non-final regular-season game in game ID order (date first); 0 when every game is final."""
    for game in sorted(games, key=lambda g: g.key):
        if not game.final:
            return game.week
    return 0


def cap_window_end(cap_deadline: datetime | None, buffer_days: int) -> datetime | None:
    """First instant after the Cap Deadline buffer: 00:00 UTC of the day after (deadline UTC date + buffer days)."""
    if cap_deadline is None:
        return None
    last_day = cap_deadline.astimezone(UTC).date() + timedelta(days=buffer_days + 1)
    return datetime(last_day.year, last_day.month, last_day.day, tzinfo=UTC)


def _drafts_of_season(facts: Facts) -> list[Mapping[str, Any]]:
    return [draft for draft in facts.drafts if int(str(draft.get("Season"))) == facts.season]


def _daily_waiver_modes(encoded: int) -> list[int] | None:
    """ConvertFrom-SleeperDailyWaiverDays: seven base-4 digits, Monday to Sunday; null when out of range."""
    if encoded < 0:
        return None
    remaining, modes = encoded, [0] * 7
    for index in range(6, -1, -1):
        modes[index] = remaining % 4
        remaining //= 4
    return None if remaining != 0 else modes


def _local_time_state(local: datetime, zone: ZoneInfo) -> str:
    """ok, invalid (skipped by daylight saving) or ambiguous (repeated) for a naive wall-clock time."""
    first, second = local.replace(tzinfo=zone, fold=0), local.replace(tzinfo=zone, fold=1)
    if first.utcoffset() == second.utcoffset():
        return "ok"
    round_trip = first.astimezone(UTC).astimezone(zone).replace(tzinfo=None)
    return "invalid" if round_trip != local else "ambiguous"


def next_waiver_run(settings: Mapping[str, Any], at_utc: datetime, warnings: list[str]) -> datetime | None:
    """Resolve-LeagueNextWaiverRunUtc: the first daily waiver run strictly after ``at_utc``, else None (with a warning if undecidable)."""
    if _int0(settings.get("disable_adds"), "disable_adds") != 0:
        return None
    if _int0(settings.get("daily_waivers"), "daily_waivers") != 1:
        return None
    days, hour = settings.get("daily_waivers_days"), settings.get("daily_waivers_hour")
    if days is None or hour is None:
        return None
    hour = _int0(hour, "daily_waivers_hour")
    if hour < 0 or hour > 23:
        return None
    modes = _daily_waiver_modes(_int0(days, "daily_waivers_days"))
    if modes is None:
        return None
    unsupported = [mode for mode in modes if mode not in PARAMS["ValidatedWaiverModes"]]
    if unsupported:
        warnings.append("Cannot derive next waiver run: daily waiver schedule contains unvalidated Sleeper mode(s): "
                        + ", ".join(str(mode) for mode in unsupported) + ".")
        return None
    if 1 not in modes:
        return None
    zone = ZoneInfo(PARAMS["WaiverTimeZone"])
    now_local = at_utc.astimezone(zone)
    for offset in range(PARAMS["WaiverLookaheadDays"] + 1):
        day = now_local.date() + timedelta(days=offset)
        if modes[day.weekday()] != 1:
            continue
        local = datetime(day.year, day.month, day.day, hour)
        if _local_time_state(local, zone) != "ok":
            warnings.append(f"Cannot derive next waiver run safely across a DST transition at {local.isoformat(sep=' ')}.")
            return None
        candidate = local.replace(tzinfo=zone).astimezone(UTC)
        if candidate > at_utc:
            return candidate
    return None


def _status(facts: Facts, trades_open: bool, window_started: bool, window_open: bool) -> tuple[str, str]:
    """Resolve-LeagueStatusState: the first matching of the twelve rules."""
    provider = str(facts.provider_status)
    if _same(provider, "complete"):
        return "Completed", ""
    playoff_week = _int0(facts.settings.get("playoff_week_start"), "playoff_week_start")
    if _same(provider, "playoffs") or (playoff_week > 0 and facts.final_scored_week >= playoff_week):
        return "Playoffs", ""
    drafts = _drafts_of_season(facts)
    open_statuses = {status.casefold() for status in PARAMS["OpenDraftStatuses"]}
    open_drafts = [d for d in drafts if str(d.get("Status")).casefold() in open_statuses]
    has_open = bool(open_drafts)
    all_complete = bool(drafts) and all(_same(d.get("Status"), PARAMS["CompletedDraftStatus"]) for d in drafts)
    has_live = any(_same(d.get("Status"), PARAMS["LiveDraftStatus"]) for d in drafts)
    has_completed = any(_same(d.get("Status"), PARAMS["CompletedDraftStatus"]) for d in drafts)
    start_time_set = any(_text_set(d.get("DraftStartTimeUtc")) or _text_set(d.get("SleeperStartTime")) for d in open_drafts)

    if all_complete:
        return ("In-Season", "") if window_started else ("Pre-Season", "")
    if has_live:
        return "Draft-Season", "In Draft"
    if has_completed and has_open and start_time_set:
        return "Draft-Season", "Pre Draft"
    if has_completed and has_open:
        return "Draft-Season", "Between Drafts"
    if trades_open and window_open:
        return "Off-Season", "Cap Deadline Open"
    if has_open and not trades_open:
        return "Off-Season", "Cap Check"
    if has_open and trades_open and not start_time_set:
        return "Off-Season", "Post Cap Check"
    if has_open and trades_open and start_time_set:
        return "Draft-Season", "Pre Draft"
    return ("In-Season", "") if window_started else ("Pre-Season", "")


def resolve(facts: Facts, at_utc: datetime) -> dict[str, Any]:
    """Lifecycle of the league season at ``at_utc`` (timezone-aware). Pure; the result carries its own clock boundaries."""
    if not isinstance(at_utc, datetime) or at_utc.tzinfo is None:
        raise ValueError("at_utc must be a timezone-aware datetime")
    at = at_utc.astimezone(UTC)
    warnings: list[str] = []
    settings = facts.settings

    kickoff = season_kickoff(facts.games)
    window_start = None if kickoff is None else kickoff - timedelta(days=PARAMS["SeasonStartLeadDays"])
    window_started = window_start is not None and at >= window_start
    cap_end = cap_window_end(facts.cap_deadline, facts.cap_buffer_days)
    window_open = cap_end is not None and at < cap_end

    week = current_week(facts.games)
    leg_raw = settings.get("leg")
    lineup_week = None if leg_raw is None else _int0(leg_raw, "leg")
    playoff_week_raw = settings.get("playoff_week_start")
    playoff_week = _int0(playoff_week_raw, "playoff_week_start")

    review_days = _int0(settings.get("trade_review_days"), "trade_review_days")
    trades_open = _int0(settings.get("disable_trades"), "disable_trades") == 0
    closed_by: list[str] = []
    if not trades_open:
        closed_by.append("DisabledInProvider")
    if review_days > 0:
        trades_open = False
        closed_by.append("CommissionerReview")
    deadline_week = trade_deadline_week(settings.get("trade_deadline"))
    week_reached = week if week > 0 else facts.final_scored_week
    if deadline_week is not None and week_reached >= deadline_week:
        trades_open = False
        closed_by.append("TradeDeadlineReached")

    waivers_open = _int0(settings.get("disable_adds"), "disable_adds") == 0
    waiver_run = next_waiver_run(settings, at, warnings)
    status, phase = _status(facts, trades_open, window_started, window_open)
    cuts_allowed = True
    if status == "Completed":
        cuts_allowed, waivers_open, waiver_run, trades_open = False, False, None, False

    return {
        "Status": status,
        "Phase": phase,
        "CurrentWeek": week,
        "LineupWeek": lineup_week,
        "FinalScoredWeek": facts.final_scored_week,
        "LastLeagueWeek": facts.last_league_week,
        "PlayoffStartWeek": None if playoff_week_raw is None else playoff_week,
        "PlayoffStart": _iso(playoff_start(facts.games, playoff_week)),
        "SeasonKickoff": _iso(kickoff),
        "TradesOpen": trades_open,
        "TradesClosedBy": closed_by,
        "TradeReviewDays": review_days,
        "TradeDeadlineWeek": deadline_week,
        "WaiversOpen": waivers_open,
        "NextWaiverRun": _iso(waiver_run),
        "CutsAllowed": cuts_allowed,
        "Boundaries": {
            "CapWindowEnd": _iso(cap_end),
            "SeasonWindowStart": _iso(window_start),
            "NextWaiverRun": _iso(waiver_run),
        },
        "Warnings": warnings,
    }
