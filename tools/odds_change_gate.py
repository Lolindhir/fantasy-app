"""Pure semantic publication gate for volatile NFL game market lines (#471).

This module performs no polling, state persistence, Git commit, or scheduling.
It decides whether an already-observed change is worth publishing to an NFL
Game consumer. Provider moneyline and price odds are *never* trigger fields.
The executor owns durable observed/published baselines and writer safety.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from math import isfinite
from typing import Any, Mapping

TRIGGER_FIELDS = ("SpreadLine", "TotalLine")


@dataclass(frozen=True)
class OddsGateConfig:
    major_spread_points: Decimal = Decimal("1.0")
    major_total_points: Decimal = Decimal("2.0")
    maximum_delay_minutes: int = 60
    pre_kickoff_flush_minutes: int = 15

    def __post_init__(self) -> None:
        if (self.major_spread_points <= 0 or self.major_total_points <= 0
                or self.maximum_delay_minutes < 1 or self.pre_kickoff_flush_minutes < 0):
            raise ValueError("Invalid semantic odds gate configuration")


@dataclass(frozen=True)
class GameGateDecision:
    game_id: str
    publish: bool
    reason: str
    spread_delta: Decimal | None
    total_delta: Decimal | None


def _decimal(value: Any, label: str) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (float, int, Decimal)):
        raise ValueError(f"{label}: invalid line")
    if isinstance(value, float) and not isfinite(value):
        raise ValueError(f"{label}: non-finite line")
    try:
        val = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(f"{label}: invalid line") from exc
    if not val.is_finite():
        raise ValueError(f"{label}: non-finite line")
    return val


def _aware(t: datetime, label: str) -> datetime:
    if not isinstance(t, datetime) or t.tzinfo is None or t.utcoffset() is None:
        raise ValueError(f"{label}: timezone-aware datetime required")
    return t


def evaluate_game(
    game_id: str,
    *,
    published: Mapping[str, Any] | None,
    observed: Mapping[str, Any],
    published_at: datetime | None,
    observed_at: datetime,
    pending_since: datetime | None = None,
    kickoff_at: datetime | None = None,
    config: OddsGateConfig = OddsGateConfig(),
) -> GameGateDecision:
    """Compare the latest observation to the last *published* game lines.

    published_at is the last published checkpoint for this game. pending_since
    marks when the CURRENT net line difference first arose, so a tiny change
    following hours of inactivity does not immediately publish. The executor
    must persist pending_since across polls, and clear it on reversal/publication.
    """
    _aware(observed_at, "observed_at")
    if published_at is not None:
        _aware(published_at, "published_at")
        if observed_at < published_at:
            raise ValueError("Observation predates the published checkpoint")
    if pending_since is not None:
        _aware(pending_since, "pending_since")
        if pending_since > observed_at or (published_at is not None and pending_since < published_at):
            raise ValueError("Pending start outside published/observed interval")
    if kickoff_at is not None:
        _aware(kickoff_at, "kickoff_at")
    if not game_id:
        raise ValueError("Missing GameID")
    if not isinstance(observed, Mapping):
        raise ValueError(f"{game_id}: missing observed data")

    if published is None:
        return GameGateDecision(game_id, True, "first_observation", None, None)
    if not isinstance(published, Mapping) or published_at is None:
        raise ValueError(f"{game_id}: published baseline lacks durable checkpoint")

    deltas: dict[str, Decimal | None] = {}
    transition = False
    relevant = False
    for field in TRIGGER_FIELDS:
        before = _decimal(published.get(field), f"{game_id}.{field}.published")
        after = _decimal(observed.get(field), f"{game_id}.{field}.observed")
        if before is None or after is None:
            deltas[field] = None
            if before != after:
                transition = True
                relevant = True
        else:
            delta = after - before
            deltas[field] = delta
            relevant |= delta != 0
    spread, total = deltas["SpreadLine"], deltas["TotalLine"]
    if not relevant:
        return GameGateDecision(game_id, False, "no_relevant_change", spread, total)
    if transition:
        return GameGateDecision(game_id, True, "line_availability_changed", spread, total)
    if ((spread is not None and abs(spread) >= config.major_spread_points)
            or (total is not None and abs(total) >= config.major_total_points)):
        return GameGateDecision(game_id, True, "large_cumulative_change", spread, total)
    if kickoff_at is not None and observed_at <= kickoff_at and (
        kickoff_at - observed_at <= timedelta(minutes=config.pre_kickoff_flush_minutes)
    ):
        return GameGateDecision(game_id, True, "pregame_last_flush", spread, total)
    if pending_since is not None and observed_at - pending_since >= timedelta(minutes=config.maximum_delay_minutes):
        return GameGateDecision(game_id, True, "maximum_age_with_pending_change", spread, total)
    return GameGateDecision(game_id, False, "debounce_small_change", spread, total)



def next_pending_since(
    *,
    published: Mapping[str, Any] | None,
    observed: Mapping[str, Any],
    previous_pending_since: datetime | None,
    observed_at: datetime,
) -> datetime | None:
    """Pure pending-buffer transition; persist returned time after observing.

    Net-zero (including reversal to the published line) clears the buffer.
    First nonzero observation starts the clock. Price-only changes are ignored.
    Publishing a changed game must independently reset its pending clock and
    replace its published baseline in the durable state.
    """
    _aware(observed_at, "observed_at")
    if previous_pending_since is not None:
        _aware(previous_pending_since, "previous_pending_since")
        if previous_pending_since > observed_at:
            raise ValueError("Pending change starts after observation")
    if published is None:
        return None
    if not isinstance(published, Mapping) or not isinstance(observed, Mapping):
        raise ValueError("Invalid published or observed line")
    changed = any(
        _decimal(published.get(field), f"{field}.published")
        != _decimal(observed.get(field), f"{field}.observed")
        for field in TRIGGER_FIELDS
    )
    if not changed:
        return None
    return previous_pending_since or observed_at


def evaluate_games(
    *,
    published: Mapping[str, Mapping[str, Any]],
    observed: Mapping[str, Mapping[str, Any]],
    published_at_by_game: Mapping[str, datetime],
    observed_at: datetime,
    pending_since_by_game: Mapping[str, datetime] | None = None,
    kickoff_by_game: Mapping[str, datetime] | None = None,
    config: OddsGateConfig = OddsGateConfig(),
) -> list[GameGateDecision]:
    """Pure multi-game policy; scheduler may coalesce publishable rows in one commit."""
    _aware(observed_at, "observ_at")
    if not isinstance(observed, Mapping) or not isinstance(published, Mapping):
        raise ValueError("Invalid market observation set")
    decisions: list[GameGateDecision] = []
    for game_id in sorted(observed):
        decisions.append(evaluate_game(
            game_id, published=published.get(game_id),
            observed=observed[game_id],
            published_at=published_at_by_game.get(game_id),
            observed_at=observed_at,
            pending_since=(pending_since_by_game or {}).get(game_id),
            kickoff_at=(kickoff_by_game or {}).get(game_id),
            config=config,
        ))
    missing = set(published) - set(observed)
    if missing:
        raise ValueError(f"Observation unexpectedly dropped {len(missing)} published games")
    return decisions
