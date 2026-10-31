"""PlayerValuation snapshot computation (ADR-055, .ai-context/manual/player-valuation.yaml).

Pure functions: the caller (tools/player_valuation_sources.py) reads canonical facts and hands in
prepared per-player weekly rows; this module turns them into the snapshot of one league season at
one AsOfFinalScoredWeek using the models the league selected. It reads no files, no network, no
clock and no environment.

The numeric behaviour reproduces RequestPlayers.ps1 / PlayerLeagueScoringUtils.psm1 exactly:
  * current season: played games up to the as-of week, exact (unrounded) point sum, averages rounded
    half-to-even to two decimals; potential games are the as-of week minus the team bye week when the
    bye lies within the as-of weeks (a player without a team has bye week 0, as today);
  * previous seasons: played games up to LastLeagueWeek, total rounded to two decimals first, then the
    averages from the rounded total; potential games are LastLeagueWeek - 1.

ContractVersion 2 (ADR-076, Issue #1226 step 3a) adds, additively, the season values the Players consumer used to
derive itself: SeasonValues (the Players.json aggregates of the current season and the PointHistory of the three
previous seasons) and FormGames (the last four scored games, the basis of a Form grading). They follow the same
as-of rule as Inputs: only games of weeks up to AsOfFinalScoredWeek count, so an older snapshot never changes
when later weeks arrive.
"""
from __future__ import annotations

import copy
import math
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

from .models._common import require_finite
from .models.registry import get_model
from .ranking import RankingInput, compute_rankings

CONTRACT_VERSION = 2
STATUS_RESOLVED = "resolved"
HISTORY_KEYS = ("SeasonMinus1", "SeasonMinus2", "SeasonMinus3")
MODEL_KINDS = {"Salary": "salary", "SalaryCap": "salary-cap", "Grading": "grading"}

# week -> {"Points": float, "Snaps": float, "KickAttempts": float} (+ optional Attempts, TdPass, TdRec, TdRush)
WeekRows = Mapping[int, Mapping[str, float]]
# key -> (held Inputs or None, source week or None); the same shape serves the held SeasonValues
HoldLookup = Callable[[str], "tuple[Mapping[str, Any] | None, int | None]"]


@dataclass(frozen=True)
class GameRef:
    """One game of the player's GameHistory (newest first in PlayerBasis.games)."""

    game_id: str
    week: int
    week_final: bool


@dataclass(frozen=True)
class PlayerBasis:
    """One population row with the league-scored weekly rows of the snapshot and history seasons."""

    sleeper_id: str | None
    canonical_id: str | None
    position: str
    team: str | None
    population: tuple[str, ...]
    identity_status: str
    weeks: Mapping[int, WeekRows] = field(default_factory=dict)  # season -> week rows
    games: tuple[GameRef, ...] = ()  # current-season GameHistory, newest first

    @property
    def key(self) -> str:
        key = self.canonical_id or self.sleeper_id
        if not key:
            raise ValueError("Population row without CanonicalPlayerID and Sleeper PlayerID")
        return key


@dataclass(frozen=True)
class SnapshotContext:
    league_id: str
    season: int
    as_of_final_scored_week: int
    scoring_profile: Mapping[str, Any]
    model_ids: Mapping[str, str]  # Salary / SalaryCap / Grading -> model ID
    team_count: int
    last_league_week: int
    bye_weeks: Mapping[str, int]  # canonical team -> bye week


def scaled_round(value: float, digits: int) -> float:
    """[math]::Round(value, digits) as PowerShell/.NET does it: scale, then round half to even."""
    factor = 10.0 ** digits
    result = round(value * factor) / factor
    # .NET keeps the sign of a negative value that rounds to zero (-0.0); Python's int rounding loses it
    return math.copysign(0.0, value) if result == 0 else result


def played_points(weeks: WeekRows, position: str, max_week: int) -> list[float]:
    """Points of the played games with week <= max_week in ascending week order."""
    points: list[float] = []
    for week in sorted(weeks):
        if week > max_week:
            continue
        row = weeks[week]
        played = row["KickAttempts"] > 0 if position == "K" else row["Snaps"] > 0
        if played:
            points.append(require_finite(row["Points"], "Points"))
    return points


def _sequential_sum(values: Sequence[float]) -> float:
    # Sequential accumulation like PowerShell; the built-in sum() is compensated for floats since 3.12.
    total = 0.0
    for value in values:
        total += value
    return total


def bye_week_of(team: str | None, bye_weeks: Mapping[str, int]) -> int:
    """Bye week of the canonical team; 0 without a team or without a bye entry (RequestPlayers.ps1 parity)."""
    return int(bye_weeks[team]) if team and team in bye_weeks else 0


def current_inputs(weeks: WeekRows, position: str, as_of: int, bye_week: int) -> dict[str, float]:
    points = played_points(weeks, position, as_of)
    total = _sequential_sum(points)
    potential = as_of - (1 if bye_week <= as_of else 0)
    return {
        "AvgPotentialGame": scaled_round(total / potential, 2) if potential > 0 else 0.0,
        "AvgGame": scaled_round(total / len(points), 2) if points else 0.0,
    }


def history_values(weeks: WeekRows, position: str, last_league_week: int) -> dict[str, float]:
    """PointHistory block of a previous season (Players.json shape and field names)."""
    points = played_points(weeks, position, last_league_week)
    total = scaled_round(_sequential_sum(points), 2)
    potential = last_league_week - 1
    return {
        "Total": total,
        "AvgGame": scaled_round(total / len(points), 2) if points else 0.0,
        "AvgPotentialGame": scaled_round(total / potential, 2) if potential > 0 else 0.0,
        "GamesPlayed": len(points),
        "PotentialGames": potential,
    }


def history_inputs(weeks: WeekRows, position: str, last_league_week: int) -> dict[str, float]:
    values = history_values(weeks, position, last_league_week)
    return {"AvgPotentialGame": values["AvgPotentialGame"], "AvgGame": values["AvgGame"]}


def games_potential(as_of: int, bye_week: int, has_games: bool) -> int:
    """Potential games of the current season: as-of week minus a passed bye week; 0 without any game."""
    return as_of - (1 if bye_week <= as_of else 0) if has_games else 0


def current_values(weeks: WeekRows, position: str, as_of: int, bye_week: int, has_games: bool) -> dict[str, Any]:
    """Current-season aggregates in the Players.json field names (exact point sum, rounded once per field)."""
    rows = [weeks[w] for w in sorted(weeks) if w <= as_of
            and (weeks[w]["KickAttempts"] > 0 if position == "K" else weeks[w]["Snaps"] > 0)]
    points = _sequential_sum([require_finite(row["Points"], "Points") for row in rows])
    snaps = int(round(_sequential_sum([row["KickAttempts"] if position == "K" else row["Snaps"] for row in rows])))
    attempts = int(round(_sequential_sum([row.get("Attempts", 0.0) for row in rows])))
    td_pass = sum(int(round(row.get("TdPass", 0.0))) for row in rows)
    td_rec = sum(int(round(row.get("TdRec", 0.0))) for row in rows)
    td_rush = sum(int(round(row.get("TdRush", 0.0))) for row in rows)
    potential = games_potential(as_of, bye_week, has_games)
    return {
        "GamesPlayed": len(rows),
        "GamesPotential": potential,
        "SnapsTotal": snaps,
        "AttemptsTotal": attempts,
        "FantasyPointsTotal": scaled_round(points, 2),
        "FantasyPointsAvgGame": scaled_round(points / len(rows), 2) if rows else 0,
        "FantasyPointsAvgPotentialGame": scaled_round(points / potential, 2) if potential > 0 else 0,
        "FantasyPointsAvgSnap": scaled_round(points / snaps, 5) if snaps > 0 else 0,
        "FantasyPointsAvgAttempt": scaled_round(points / attempts, 5) if attempts > 0 else 0,
        "TouchdownsTotal": td_pass + td_rec + td_rush,
        "TouchdownsPassing": td_pass,
        "TouchdownsReceiving": td_rec,
        "TouchdownsRushing": td_rush,
    }


FORM_GAME_COUNT = 4


def form_games(games: Sequence[GameRef], as_of: int, last_league_week: int) -> list[str]:
    """IDs of the last four scored games (final, within the league weeks, up to the as-of week), newest first."""
    selected = [g.game_id for g in games if g.week_final and g.week <= last_league_week and g.week <= as_of]
    return selected[:FORM_GAME_COUNT]


def season_values(context: "SnapshotContext", basis: PlayerBasis) -> dict[str, Any]:
    """SeasonValues block: Current aggregates plus the PointHistory blocks of the three previous seasons."""
    bye = bye_week_of(basis.team, context.bye_weeks)
    has_games = any(g.week <= context.as_of_final_scored_week for g in basis.games)
    values: dict[str, Any] = {"Current": current_values(
        basis.weeks.get(context.season, {}), basis.position, context.as_of_final_scored_week, bye, has_games)}
    for offset, name in enumerate(HISTORY_KEYS, start=1):
        values[name] = history_values(basis.weeks.get(context.season - offset, {}), basis.position, context.last_league_week)
    return values


def player_inputs(context: SnapshotContext, basis: PlayerBasis) -> dict[str, dict[str, float]]:
    """The Inputs block of a resolved player (league-scored averages, no further rounding)."""
    bye = bye_week_of(basis.team, context.bye_weeks)
    inputs = {"Current": current_inputs(
        basis.weeks.get(context.season, {}), basis.position, context.as_of_final_scored_week, bye)}
    for offset, name in enumerate(HISTORY_KEYS, start=1):
        inputs[name] = history_inputs(basis.weeks.get(context.season - offset, {}), basis.position, context.last_league_week)
    return inputs


def _models(context: SnapshotContext) -> dict[str, Any]:
    if set(context.model_ids) != set(MODEL_KINDS):
        raise ValueError(f"model_ids must name exactly {sorted(MODEL_KINDS)}")
    return {name: get_model(context.model_ids[name], kind) for name, kind in MODEL_KINDS.items()}


def _season_input(salary_model: Any, values: Mapping[str, float]) -> Any:
    return salary_model.SeasonInput(avg_potential_game=values["AvgPotentialGame"], avg_game=values["AvgGame"])


def build_snapshot(
    context: SnapshotContext, players: Sequence[PlayerBasis], hold_lookup: HoldLookup,
    hold_values_lookup: HoldLookup | None = None,
) -> dict[str, Any]:
    """Snapshot of ``context.season`` at ``context.as_of_final_scored_week`` in the contract shape."""
    models = _models(context)
    salary_model, cap_model, grading_model = models["Salary"], models["SalaryCap"], models["Grading"]

    ordered = sorted(players, key=lambda p: p.key)
    keys = [p.key for p in ordered]
    if len(set(keys)) != len(keys):
        duplicates = sorted({k for k in keys if keys.count(k) > 1})
        raise ValueError(f"Duplicate player row key(s): {', '.join(duplicates[:5])}")

    rows: list[dict[str, Any]] = []
    for basis in ordered:
        if basis.identity_status == STATUS_RESOLVED:
            inputs: dict[str, Any] | None = player_inputs(context, basis)
            values: dict[str, Any] | None = season_values(context, basis)
            form = form_games(basis.games, context.as_of_final_scored_week, context.last_league_week)
            hold = None
        else:
            held, source_week = hold_lookup(basis.key)
            inputs = copy.deepcopy(dict(held)) if held else None
            held_values = hold_values_lookup(basis.key)[0] if hold_values_lookup and inputs else None
            values = copy.deepcopy(dict(held_values)) if held_values else None
            form = []  # a hold player has no GameHistory (Issue #1226, Q3)
            hold = {"Reason": basis.identity_status, "SourceWeek": source_week if inputs else None}
        row: dict[str, Any] = {
            "CanonicalPlayerID": basis.canonical_id,
            "PlayerID": basis.sleeper_id,
            "Position": basis.position,
            "Population": list(basis.population),
            "Hold": hold,
            "Inputs": inputs,
            "SeasonValues": values,
            "FormGames": form,
            "Salary": None,
            "SalaryProjected": None,
            "Ranking": [],
            "Grading": [],
        }
        if inputs is not None:
            result = salary_model.compute(
                _season_input(salary_model, inputs["Current"]),
                *(_season_input(salary_model, inputs[name]) for name in HISTORY_KEYS),
                context.as_of_final_scored_week,
            )
            row["Salary"], row["SalaryProjected"] = result.salary, result.salary_projected
        rows.append(row)

    valued = [(basis, row) for basis, row in zip(ordered, rows) if row["Inputs"] is not None]
    rankings = compute_rankings([
        RankingInput(
            key=basis.key,
            position=basis.position,
            avg_potential_game=row["Inputs"]["Current"]["AvgPotentialGame"],
            avg_game=row["Inputs"]["Current"]["AvgGame"],
            previous_avg_potential_game=row["Inputs"]["SeasonMinus1"]["AvgPotentialGame"],
            previous_avg_game=row["Inputs"]["SeasonMinus1"]["AvgGame"],
        )
        for basis, row in valued
    ])
    for basis, row in valued:
        row["Ranking"] = rankings[basis.key]
        combined_pos = next((r["Value"] for r in row["Ranking"] if r["Type"] == "Combined_Pos"), None)
        row["Grading"] = [grading_model.rank_row(combined_pos, basis.position)]

    if not valued:
        raise ValueError(f"No valued players for {context.league_id} {context.season} week {context.as_of_final_scored_week}")
    cap = cap_model.compute([row["Salary"] for _, row in valued], context.team_count)
    cap_projected = cap_model.compute([row["SalaryProjected"] for _, row in valued], context.team_count)
    return {
        "ContractVersion": CONTRACT_VERSION,
        "CanonicalLeagueID": context.league_id,
        "Season": context.season,
        "AsOfFinalScoredWeek": context.as_of_final_scored_week,
        "ScoringProfile": dict(context.scoring_profile),
        "Models": {name: context.model_ids[name] for name in MODEL_KINDS},
        "League": {
            "TeamCount": context.team_count,
            "SalaryRelevantTeamSize": cap_model.PARAMS["SalaryRelevantTeamSize"],
            "TopN": cap.top_n,
            "SalaryCap": cap.cap,
            "SalaryCapProjected": cap_projected.cap,
        },
        "Players": rows,
    }
