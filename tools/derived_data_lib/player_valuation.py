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
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

from .models._common import require_finite
from .models.registry import get_model
from .ranking import RankingInput, compute_rankings

CONTRACT_VERSION = 1
STATUS_RESOLVED = "resolved"
HISTORY_KEYS = ("SeasonMinus1", "SeasonMinus2", "SeasonMinus3")
MODEL_KINDS = {"Salary": "salary", "SalaryCap": "salary-cap", "Grading": "grading"}

# week -> {"Points": float, "Snaps": float, "KickAttempts": float}
WeekRows = Mapping[int, Mapping[str, float]]
# key -> (held Inputs or None, source week or None)
HoldLookup = Callable[[str], "tuple[Mapping[str, Any] | None, int | None]"]


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
    return round(value * factor) / factor


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


def history_inputs(weeks: WeekRows, position: str, last_league_week: int) -> dict[str, float]:
    points = played_points(weeks, position, last_league_week)
    total = scaled_round(_sequential_sum(points), 2)
    potential = last_league_week - 1
    return {
        "AvgPotentialGame": scaled_round(total / potential, 2) if potential > 0 else 0.0,
        "AvgGame": scaled_round(total / len(points), 2) if points else 0.0,
    }


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


def build_snapshot(context: SnapshotContext, players: Sequence[PlayerBasis], hold_lookup: HoldLookup) -> dict[str, Any]:
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
            hold = None
        else:
            held, source_week = hold_lookup(basis.key)
            inputs = copy.deepcopy(dict(held)) if held else None
            hold = {"Reason": basis.identity_status, "SourceWeek": source_week if inputs else None}
        row: dict[str, Any] = {
            "CanonicalPlayerID": basis.canonical_id,
            "PlayerID": basis.sleeper_id,
            "Position": basis.position,
            "Population": list(basis.population),
            "Hold": hold,
            "Inputs": inputs,
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
