"""Kickoff overlay for the canonical NFL schedule (Issue #1627, ADR-097).

nflverse stays the only schedule source. When an independent ESPN observation (a Source Evidence snapshot,
joined by ProviderGameIDs.ESPN) proves a different kickoff of a game that is not scored yet, the materialized
canonical game carries the ESPN kickoff (GameDay, GameTime, WeekDay) plus its origin. Everything else is kept.
The function is pure and deterministic; it is applied to the nflverse-derived games on every materialization, so
the override disappears by itself as soon as nflverse delivers the same time. Unknown, ambiguous or implausible
evidence never changes a game (fail closed towards nflverse).
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from data_roots import DATA_SOURCE_ROOT
from derived_data_lib.nfl_games import SOURCE_TIME_ZONE, kickoff_utc

# Versioned method parameters (never league data). A flex move stays inside its NFL week, which spans at most
# Thursday to Monday plus a holiday offset; one week is a conservative bound that still rejects wrong-week data.
PARAMS = {"id": "espn-kickoff-overlay-v1", "maxShiftDays": 7}

APPLIED = "applied"
UNCHANGED = "unchanged"
KEPT = "kept-nflverse"

_INSTANT = "%Y-%m-%dT%H:%M:%SZ"


def _eastern(instant: str) -> tuple[str, str, str]:
    moment = datetime.strptime(instant, _INSTANT).replace(tzinfo=timezone.utc).astimezone(SOURCE_TIME_ZONE)
    return moment.strftime("%Y-%m-%d"), moment.strftime("%H:%M"), moment.strftime("%A")


def _decision(game: Mapping[str, Any], outcome: str, reason: str, **extra: Any) -> dict[str, Any]:
    return {"GameID": game["GameID"], "Outcome": outcome, "Reason": reason, **extra}


def apply_overlay(
    games: Iterable[Mapping[str, Any]],
    observations: Iterable[Mapping[str, Any]],
    params: Mapping[str, Any] = PARAMS,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (games with applied overlay, one decision per game).

    observations: items with EspnGameID and KickoffUtc (yyyy-MM-ddTHH:mm:ssZ) from the ESPN snapshot.
    """
    games = [dict(game) for game in games]
    by_espn: dict[str, list[str]] = {}
    for obs in observations:
        by_espn.setdefault(str(obs["EspnGameID"]), []).append(str(obs.get("KickoffUtc") or ""))
    canonical_owners: dict[str, int] = {}
    for game in games:
        espn_id = (game.get("ProviderGameIDs") or {}).get("ESPN")
        if espn_id:
            canonical_owners[str(espn_id)] = canonical_owners.get(str(espn_id), 0) + 1
    max_shift = timedelta(days=int(params["maxShiftDays"]))

    decisions: list[dict[str, Any]] = []
    for game in games:
        espn_id = (game.get("ProviderGameIDs") or {}).get("ESPN")
        if not espn_id:
            decisions.append(_decision(game, KEPT, "no-espn-id"))
            continue
        espn_id = str(espn_id)
        seen = by_espn.get(espn_id)
        if not seen:
            decisions.append(_decision(game, KEPT, "no-observation"))
            continue
        if len(set(seen)) != 1 or canonical_owners[espn_id] != 1:
            decisions.append(_decision(game, KEPT, "ambiguous"))
            continue
        if game.get("AwayScore") is not None or game.get("HomeScore") is not None:
            decisions.append(_decision(game, KEPT, "already-scored"))
            continue
        observed = seen[0]
        try:
            datetime.strptime(observed, _INSTANT)
            canonical = kickoff_utc(game["GameID"], game["GameDay"], game.get("GameTime") or None)
        except ValueError:
            decisions.append(_decision(game, KEPT, "kickoff-unknown"))
            continue
        if canonical is None:
            decisions.append(_decision(game, KEPT, "kickoff-unknown"))
            continue
        if observed == canonical:
            decisions.append(_decision(game, UNCHANGED, "same-kickoff"))
            continue
        shift = abs(datetime.strptime(observed, _INSTANT) - datetime.strptime(canonical, _INSTANT))
        if shift > max_shift:
            decisions.append(_decision(game, KEPT, "implausible-shift", NflverseKickoffUtc=canonical, EspnKickoffUtc=observed))
            continue
        day, time_, weekday = _eastern(observed)
        original = {"GameDay": game["GameDay"], "GameTime": game["GameTime"]}
        game.update(
            {
                "GameDay": day,
                "GameTime": time_,
                "WeekDay": weekday,
                "TimeSource": "espn",
                "TimeSourceNflverse": original,
            }
        )
        decisions.append(_decision(game, APPLIED, "espn-differs", NflverseKickoffUtc=canonical, EspnKickoffUtc=observed))
    return games, decisions



def load_espn_observations(repo_root: Path, season: int) -> list[dict[str, str]]:
    """Observations of data-source/providers/espn/schedule/<season>.json; missing or unreadable means none."""
    path = repo_root / DATA_SOURCE_ROOT / "providers" / "espn" / "schedule" / f"{season}.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        return [
            {"EspnGameID": str(o["EspnGameID"]), "KickoffUtc": str(o["KickoffUtc"])} for o in payload["Observations"]
        ]
    except (OSError, ValueError, KeyError, TypeError):
        return []


def apply_espn_kickoff_overlay(
    repo_root: Path, season: int, games: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Overlay the persisted ESPN observations of one season onto the nflverse-derived games."""
    observations = load_espn_observations(repo_root, season)
    if not observations:
        return games, []
    return apply_overlay(games, observations)
