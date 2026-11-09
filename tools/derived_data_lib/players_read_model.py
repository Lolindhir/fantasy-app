"""Players read model: the rows of the published Players file as a pure function (ADR-076, Issue #1226 step 3b).

Contract: ``.ai-context/manual/players-read-model.yaml``. The model is computed, never persisted. It copies; it derives
no league value. Salary, SalaryProjected, Ranking, the Rank grading, the season aggregates, PointHistory, GamesPotential
and the Form basis come from the ``player-valuation`` snapshot (ADR-055); platform, profile and injury fields from the
population export (ADR-043); GameHistory from the league-scoring export (ADR-044); bye weeks from the canonical NFL
schedule; depth chart fields from the canonical Sleeper snapshot. The previously published the Players file is never an
input and there is no wall clock: time enters only through ``as_of`` (the Age reference date).

Layout: ``load_inputs`` reads the canonical facts, ``assemble`` is the pure assembly on prepared inputs (synthetic
inputs are enough to test it). ``resolve`` chains both.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from .player_valuation import bye_week_of, scaled_round
from player_age import age_at as shared_age_at

PUBLISHED_JSON_DEPTH = 7  # write depth of the Players file (Get-PlayersPublishedJsonDepth); nothing is truncated below it
FORM_GRADING_TYPE = "Form"
RANK_GRADING_TYPE = "Rank"
MIN_VALUATION_CONTRACT_VERSION = 2
PROJECTION_MET = "met"
PROJECTION_MISSED = "missed"
DAYS_PER_YEAR = 365.2425


class PlayersReadModelError(RuntimeError):
    """Inputs are missing or inconsistent (fail closed)."""


@dataclass(frozen=True)
class WeekBounds:
    last_league_week: int
    playoff_start_week: int
    final_scored_week: int


@dataclass(frozen=True)
class ReadModelInputs:
    league_id: str
    season: int
    bounds: WeekBounds
    population: Sequence[Mapping[str, Any]]            # players_population.build_population()["Players"]
    valuation_rows: Mapping[str, Mapping[str, Any]]    # PV snapshot rows by Sleeper player ID
    game_histories: Mapping[str, Sequence[Mapping[str, Any]]]  # export GameHistory entries by Sleeper player ID
    depth_charts: Mapping[str, Mapping[str, Any]]      # Sleeper ID -> {"Position", "Order"}
    bye_weeks: Mapping[str, int]                       # canonical team -> bye week
    roster_basis: Mapping[str, Any] = field(default_factory=dict)
    # Issue #1409: PlayerWeekFantasy is only read. Sleeper ID -> CanonicalPlayerID and (CanonicalPlayerID, week) -> reduced record.
    canonical_ids: Mapping[str, str] = field(default_factory=dict)
    projections: Mapping[tuple[str, int], Mapping[str, Any]] = field(default_factory=dict)
    # Issue #1410: the player-valuation snapshots of weeks 0..StatsFinalWeek are only read. week -> row key -> {Salary, SalaryProjected}.
    salary_weeks: Mapping[int, Mapping[str, Mapping[str, Any]]] = field(default_factory=dict)


@dataclass(frozen=True)
class ReadModelResult:
    as_of: date
    players: list[dict[str, Any]]
    warnings: list[str]


def age_at(birth_date: Any, as_of: date) -> float | None:
    """Age in years at ``as_of`` (one decimal, .NET rounding); None for a missing or unparsable birth date."""
    return shared_age_at(birth_date, as_of)


def injury_details(injury: Mapping[str, Any] | None) -> tuple[bool, dict[str, Any]]:
    """Sleeper injury block as the Players file (Injured, InjuryDetails). Text fields stay empty strings without a value;
    description only exists while a designation exists (Sleeper keeps stale notes after recovery)."""
    injury = injury or {}

    def text(value: Any) -> str:
        return "" if value is None else str(value).strip()

    designation = text(injury.get("Status"))
    description = ""
    if designation:
        for candidate in (injury.get("Notes"), injury.get("BodyPart"), injury.get("PracticeDescription")):
            if text(candidate):
                description = text(candidate)
                break
    return bool(designation), {
        "ReturnDate": None,
        "Description": description,
        "Date": text(injury.get("StartDate")),
        "Designation": designation,
    }


def _optional(value: Any, cast: type) -> Any:
    return None if value is None else cast(value)


def game_history_entry(entry: Mapping[str, Any], playoff_start_week: int, last_league_week: int) -> dict[str, Any]:
    """One export GameHistory entry in the published the Players file shape (value types, key order, block presence)."""
    week = int(entry["Week"])
    game: dict[str, Any] = {
        "GameID": str(entry["GameID"]),
        "GameDetails": {
            "Week": week,
            "WeekFinal": bool(entry["WeekFinal"]),
            "WeekPlayoff": week >= playoff_start_week and playoff_start_week > 0,
            "WeekScored": week <= last_league_week,
            "Date": str(entry["Date"]),
            "Home": str(entry["Home"]),
            "HomeID": str(entry["Home"]),
            "Away": str(entry["Away"]),
            "AwayID": str(entry["Away"]),
            "HomePoints": int(entry["HomePoints"]) if entry.get("HomePoints") is not None else 0,
            "AwayPoints": int(entry["AwayPoints"]) if entry.get("AwayPoints") is not None else 0,
        },
        "TeamID": str(entry["TeamID"]),
        "TeamAbv": str(entry["TeamAbv"]),
        "FantasyPoints": float(scaled_round(float(entry["FantasyPoints"]), 2)),
        "Touchdowns": int(entry["Touchdowns"]),
        "SnapCount": int(entry["SnapCount"]),
        "SnapPercentage": float(entry["SnapPercentage"]),
        "Attempts": int(entry["Attempts"]),
    }
    if "Passing" in entry:
        p = entry["Passing"]
        game["Passing"] = {
            "QBRating": _optional(p.get("QBRating"), float), "Rating": float(p["Rating"]),
            "PassAttempts": int(p["PassAttempts"]), "PassAvg": float(p["PassAvg"]), "PassTDs": int(p["PassTDs"]),
            "PassYards": int(p["PassYards"]), "Interceptions": int(p["Interceptions"]),
            "PassCompletions": int(p["PassCompletions"]),
        }
    if "Receiving" in entry:
        r = entry["Receiving"]
        game["Receiving"] = {
            "Receptions": int(r["Receptions"]), "ReceptionTDs": int(r["ReceptionTDs"]),
            "LongReceptions": _optional(r.get("LongReceptions"), int), "Targets": int(r["Targets"]),
            "ReceptionYards": int(r["ReceptionYards"]), "ReceptionAvg": float(r["ReceptionAvg"]),
        }
    if "Rushing" in entry:
        r = entry["Rushing"]
        game["Rushing"] = {
            "RushAvg": float(r["RushAvg"]), "RushYards": int(r["RushYards"]), "Carries": int(r["Carries"]),
            "LongRush": _optional(r.get("LongRush"), int), "RushTDs": int(r["RushTDs"]),
        }
    if "Kicking" in entry:
        k = entry["Kicking"]
        game["Kicking"] = {
            "KickingPts": float(k["KickingPts"]), "FgLong": int(k["FgLong"]), "FgMade": int(k["FgMade"]),
            "FgAttempts": int(k["FgAttempts"]), "FgMissed": int(k["FgMissed"]), "FgPct": float(k["FgPct"]),
            "XpMade": int(k["XpMade"]), "XpAttempts": int(k["XpAttempts"]), "XpMissed": int(k["XpMissed"]),
        }
    return game


def projection_from_record(record: Mapping[str, Any]) -> dict[str, Any] | None:
    """Reduce one PlayerWeekFantasy record to the values the Game Log needs (copied, never recomputed).

    None without a projection point value (for example insufficient history); unknown stays null, never 0.
    """
    points = (record.get("Projection") or {}).get("Points")
    if points is None:
        return None
    return {"Points": float(points), "ActualFinal": (record.get("Actual") or {}).get("State") == "final"}


def projection_result(points: float, projected: float) -> str:
    """Result against the projection: met when the points reach it (equal counts), else missed."""
    return PROJECTION_MET if points >= projected else PROJECTION_MISSED


def attach_projections(
    history: list[dict[str, Any]], canonical_id: str | None, projections: Mapping[tuple[str, int], Mapping[str, Any]],
) -> None:
    """Add Projection {Points, Result} to every game (None without a PlayerWeekFantasy value).

    Result is set only when the week is final and the PlayerWeekFantasy Actual is final, so an unsettled result is never
    classified (null).
    """
    for game in history:
        reduced = projections.get((canonical_id, game["GameDetails"]["Week"])) if canonical_id else None
        if reduced is None:
            game["Projection"] = None
            continue
        result = None
        if game["GameDetails"]["WeekFinal"] and reduced["ActualFinal"]:
            result = projection_result(game["FantasyPoints"], reduced["Points"])
        game["Projection"] = {"Points": reduced["Points"], "Result": result}


def form_value(games: list[dict[str, Any]]) -> Any:
    """Form grading value as published today: null without scored games, the bare game for exactly one, else the list.

    This is the serialization quirk of the PowerShell pipeline (Select-Object unwraps a single object). The the Players file
    contract stays unchanged; a real Form grading (grading-v2) will replace it.
    """
    if not games:
        return None
    return games[0] if len(games) == 1 else games


def valuation_row_key(row: Mapping[str, Any]) -> str:
    """Row key of a player-valuation row: CanonicalPlayerID when present, otherwise the Sleeper PlayerID (player-valuation.yaml)."""
    return str(row.get("CanonicalPlayerID") or row.get("PlayerID"))


def salary_history(
    valuation: Mapping[str, Any], salary_weeks: Mapping[int, Mapping[str, Mapping[str, Any]]], final_week: int
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Salary and SalaryProjected per week 0..final_week plus SalaryProjectedChange, copied from the snapshots (Issue #1410).

    A week without a snapshot or without a row for the player is null, never 0. SalaryProjectedChange is the generator-owned
    difference of the SalaryProjected (SinceSeasonStart against week 0, SinceLastWeek against the previous week); null when
    either value is unknown. Salary itself is derived from the previous seasons only (salary-v1) and constant within a
    season, so only SalaryProjected moves; a change of Salary would always be 0 and is not published. The frontend only sorts and shows these values."""
    key = valuation_row_key(valuation)
    history: list[dict[str, Any]] = []
    for week in range(0, final_week + 1):
        row = (salary_weeks.get(week) or {}).get(key)
        history.append({
            "Week": week,
            "Salary": float(row["Salary"]) if row and row.get("Salary") is not None else None,
            "SalaryProjected": float(row["SalaryProjected"]) if row and row.get("SalaryProjected") is not None else None,
        })

    def change(base_week: int) -> float | None:
        if base_week < 0 or base_week >= final_week:
            return None
        now, before = history[final_week]["SalaryProjected"], history[base_week]["SalaryProjected"]
        return None if now is None or before is None else now - before

    return history, {"SinceSeasonStart": change(0), "SinceLastWeek": change(final_week - 1)}


def _copy(value: Any) -> Any:
    return json.loads(json.dumps(value))


def assemble(inputs: ReadModelInputs, as_of: date) -> ReadModelResult:
    """the Players file rows (sorted by ID) and run warnings from prepared inputs."""
    warnings: list[str] = []
    bounds = inputs.bounds
    rows: list[dict[str, Any]] = []
    unknown_depth: list[str] = []
    holds_without_values: list[str] = []
    holds_without_history: list[str] = []

    for entry in inputs.population:
        position = str(entry.get("Position") or "")
        if not position:
            continue
        sleeper_id = str(entry["SleeperID"])
        label = f"{entry.get('FullName')} ({sleeper_id})"
        age = age_at(entry.get("BirthDate"), as_of)
        if age is None:
            continue  # a player without a valid age is not published

        valuation = inputs.valuation_rows.get(sleeper_id)
        if valuation is None:
            raise PlayersReadModelError(
                f"PlayerValuation snapshot lacks Sleeper player {label}; population and snapshot diverge."
            )
        values = valuation.get("SeasonValues")
        if valuation.get("Salary") is None or valuation.get("SalaryProjected") is None or values is None:
            holds_without_values.append(label)  # identity hold no snapshot knows: a visible gap, never an old value
            continue
        rank = [g for g in valuation.get("Grading") or [] if g.get("Type") == RANK_GRADING_TYPE]
        if len(rank) != 1:
            raise PlayersReadModelError(f"PlayerValuation row of {label} has {len(rank)} Rank grading rows.")

        if valuation.get("Hold") is not None:
            history: list[dict[str, Any]] = []
            holds_without_history.append(label)
        else:
            history = [
                game_history_entry(item, bounds.playoff_start_week, bounds.last_league_week)
                for item in inputs.game_histories.get(sleeper_id, [])
            ]
        by_game = {game["GameID"]: game for game in history}
        form = [_copy(by_game[game_id]) for game_id in valuation.get("FormGames") or [] if game_id in by_game]
        attach_projections(history, inputs.canonical_ids.get(sleeper_id), inputs.projections)
        salary_weeks, salary_change = salary_history(valuation, inputs.salary_weeks, bounds.final_scored_week)

        team = entry.get("TeamAbbr")
        bye = bye_week_of(team, inputs.bye_weeks)
        injured, injury = injury_details(entry.get("Injury"))
        depth = inputs.depth_charts.get(sleeper_id)
        if depth is None:
            depth = {"Position": None, "Order": None}
            unknown_depth.append(label)
        current = values["Current"]
        number = entry.get("Number")

        rows.append({
            "ID": sleeper_id,
            "Name": entry.get("FullName"),
            "NameFirst": entry.get("FirstName"),
            "NameLast": entry.get("LastName"),
            "NameShort": entry.get("NameShort"),
            "TeamID": entry.get("TeamID"),
            "TeamAbbr": team,
            "ByeWeek": bye,
            "Status": entry.get("Status"),
            "IsFreeAgent": bool(entry.get("IsFreeAgent")),
            "Position": position,
            "Age": age,
            "Year": (entry.get("YearsExp") or 0) + 1,
            "Number": str(number) if number is not None else "",
            "Salary": float(valuation["Salary"]),
            "SalaryProjected": float(valuation["SalaryProjected"]),
            "SalaryHistory": salary_weeks,
            "SalaryProjectedChange": salary_change,
            "Picture": entry.get("Picture"),
            "PictureLarge": entry.get("PictureLarge"),
            "FantasyPros": entry.get("FantasyPros"),
            "ESPN": entry.get("ESPN"),
            "SleeperDepthChartPosition": depth.get("Position"),
            "SleeperDepthChartOrder": depth.get("Order"),
            "College": entry.get("College"),
            "HighSchool": entry.get("HighSchool"),
            "Injured": injured,
            "InjuryDetails": injury,
            "GamesPlayed": current["GamesPlayed"],
            "GamesPotential": current["GamesPotential"],
            "SnapsTotal": current["SnapsTotal"],
            "AttemptsTotal": current["AttemptsTotal"],
            "FantasyPointsTotal": current["FantasyPointsTotal"],
            "FantasyPointsAvgGame": current["FantasyPointsAvgGame"],
            "FantasyPointsAvgPotentialGame": current["FantasyPointsAvgPotentialGame"],
            "FantasyPointsAvgSnap": current["FantasyPointsAvgSnap"],
            "FantasyPointsAvgAttempt": current["FantasyPointsAvgAttempt"],
            "Ranking": [{"Type": str(r["Type"]), "Value": r["Value"]} for r in valuation.get("Ranking") or []],
            "Grading": [
                {"Type": FORM_GRADING_TYPE, "Value": form_value(form)},
                {"Type": RANK_GRADING_TYPE, "Value": rank[0]["Value"], "Rank": rank[0]["Rank"], "Grade": rank[0]["Grade"]},
            ],
            "PointHistory": {name: _copy(values[name]) for name in ("SeasonMinus1", "SeasonMinus2", "SeasonMinus3")},
            "TouchdownsTotal": current["TouchdownsTotal"],
            "TouchdownsPassing": current["TouchdownsPassing"],
            "TouchdownsReceiving": current["TouchdownsReceiving"],
            "TouchdownsRushing": current["TouchdownsRushing"],
            "GameHistory": history,
        })

    rows.sort(key=lambda row: row["ID"])
    if inputs.roster_basis.get("UsedPreviousSeasonRoster"):
        warnings.append(
            f"Season roster {inputs.roster_basis.get('Season')} not yet published; population uses the "
            f"{inputs.roster_basis.get('RosterSeason')} roster."
        )
    if unknown_depth:
        warnings.append(
            f"Depth chart unknown (player not yet in the canonical Sleeper snapshot) for {len(unknown_depth)} players: "
            + ", ".join(unknown_depth)
        )
    if holds_without_history:
        warnings.append(
            f"Identity hold: GameHistory is empty for {len(holds_without_history)} players: "
            + ", ".join(holds_without_history)
        )
    if holds_without_values:
        warnings.append(
            f"Identity hold without values in the PlayerValuation snapshot: {len(holds_without_values)} players left out: "
            + ", ".join(holds_without_values)
        )
    return ReadModelResult(as_of=as_of, players=rows, warnings=warnings)


# --- Published-form comparison (Compare-Players semantics of PlayerUtils.psm1) --------------------------------------

def validate_unique_ids(players: Sequence[Mapping[str, Any]]) -> None:
    """Every record needs a non-empty ID and IDs must be globally unique (fail closed)."""
    seen: set[str] = set()
    problems: list[str] = []
    for player in players:
        player_id = str(player.get("ID") or "").strip()
        if not player_id:
            problems.append(f"missing ID: Name={player.get('Name')!r}")
        elif player_id in seen:
            problems.append(f"duplicate ID {player_id}: Name={player.get('Name')!r}")
        seen.add(player_id)
    if problems:
        raise PlayersReadModelError("Player data validation failed: " + "; ".join(problems))


def published_form(players: Sequence[Mapping[str, Any]]) -> str:
    """Players serialized like the published file (sorted by ID); equal strings mean no change."""
    ordered = sorted(players, key=lambda p: str(p["ID"]))
    return json.dumps(ordered, ensure_ascii=False, separators=(",", ":"))


def players_differ(old: Sequence[Mapping[str, Any]] | None, new: Sequence[Mapping[str, Any]]) -> bool:
    """True when the new rows differ from the published ones (order does not matter; no old file counts as changed)."""
    validate_unique_ids(new)
    if not old:
        return True
    validate_unique_ids(old)
    return len(old) != len(new) or published_form(old) != published_form(new)


def serialize_players(players: Sequence[Mapping[str, Any]]) -> str:
    """Text of the Players file: indent 2, no BOM, non-ASCII kept, one trailing newline."""
    return json.dumps(list(players), ensure_ascii=False, indent=2) + "\n"


# --- Canonical loading ---------------------------------------------------------------------------------------------

def load_projections(repo_root: Path, league_id: str, season: int) -> dict[tuple[str, int], dict[str, Any]]:
    """Read the PlayerWeekFantasy snapshots of the season (read only, Issue #1409); (CanonicalPlayerID, week) -> reduced record.

    A missing week file simply gives no projection for that week. A duplicate player record in one week fails closed."""
    from data_roots import data_derived_dir

    folder = data_derived_dir(repo_root) / "player-week-fantasy" / league_id / str(season)
    result: dict[tuple[str, int], dict[str, Any]] = {}
    if not folder.is_dir():
        return result
    for path in sorted(folder.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if (payload.get("CanonicalLeagueID"), payload.get("Season")) != (league_id, season):
            raise PlayersReadModelError(f"PlayerWeekFantasy snapshot {path} does not match {league_id} {season}")
        week = int(payload["Week"])
        for record in payload.get("Records") or []:
            key = (str(record["CanonicalPlayerID"]), week)
            if key in result:
                raise PlayersReadModelError(f"PlayerWeekFantasy snapshot {path} lists {key[0]} twice")
            reduced = projection_from_record(record)
            if reduced is not None:
                result[key] = reduced
    return result


def load_salary_weeks(
    derived_root: Path, league_id: str, season: int, final_week: int
) -> dict[int, dict[str, dict[str, Any]]]:
    """Read the player-valuation snapshots of weeks 0..final_week (read only, Issue #1410); a missing week file gives no entry."""
    from derived_data import snapshot_path

    weeks: dict[int, dict[str, dict[str, Any]]] = {}
    for week in range(0, final_week + 1):
        path = snapshot_path(derived_root, league_id, season, week)
        if not path.is_file():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if (payload.get("CanonicalLeagueID"), payload.get("Season"), payload.get("AsOfFinalScoredWeek")) != (league_id, season, week):
            raise PlayersReadModelError(f"PlayerValuation snapshot {path} does not match {league_id} {season} week {week}")
        rows: dict[str, dict[str, Any]] = {}
        for row in payload.get("Players") or []:
            key = valuation_row_key(row)
            if key in rows:
                raise PlayersReadModelError(f"PlayerValuation snapshot {path} lists {key} twice")
            rows[key] = {"Salary": row.get("Salary"), "SalaryProjected": row.get("SalaryProjected")}
        weeks[week] = rows
    return weeks


def load_inputs(repo_root: Path, league_id: str, season: int, derived_root: Path | None = None) -> ReadModelInputs:
    """Read the canonical facts and the player-valuation snapshot of the StatsFinalWeek (fail closed).

    ``derived_root`` replaces the repository data-derived root, e.g. a scratch directory of the shadow comparison."""
    import sys

    tools = Path(__file__).resolve().parents[1]
    if str(tools) not in sys.path:
        sys.path.insert(0, str(tools))
    import player_valuation_sources as sources
    from data_roots import DATA_SOURCE_ROOT, data_derived_dir
    from derived_data import snapshot_path
    from players_league_scoring import build_export, resolve_league_week_bounds
    from players_population import build_population

    raw_bounds = resolve_league_week_bounds(repo_root, league_id, season)
    bounds = WeekBounds(
        last_league_week=int(raw_bounds["LastLeagueWeek"]),
        playoff_start_week=int(raw_bounds["PlayoffStartWeek"]),
        final_scored_week=int(raw_bounds["FinalScoredWeek"]),
    )
    population = build_population(repo_root, league_id, season)
    players = population["Players"]

    path = snapshot_path(derived_root or data_derived_dir(repo_root), league_id, season, bounds.final_scored_week)
    if not path.is_file():
        raise PlayersReadModelError(f"PlayerValuation snapshot missing at {path}")
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    if (snapshot.get("CanonicalLeagueID"), snapshot.get("Season"), snapshot.get("AsOfFinalScoredWeek")) != (
        league_id, season, bounds.final_scored_week
    ):
        raise PlayersReadModelError(f"PlayerValuation snapshot {path} does not match {league_id} {season} week {bounds.final_scored_week}")
    if int(snapshot.get("ContractVersion", 0)) < MIN_VALUATION_CONTRACT_VERSION:
        raise PlayersReadModelError(f"PlayerValuation snapshot {path} predates ContractVersion {MIN_VALUATION_CONTRACT_VERSION}")
    valuation_rows: dict[str, Mapping[str, Any]] = {}
    for row in snapshot["Players"]:
        key = str(row["PlayerID"])
        if key in valuation_rows:
            raise PlayersReadModelError(f"PlayerValuation snapshot {path} lists Sleeper player {key} twice")
        valuation_rows[key] = row

    export = build_export(repo_root, league_id, season, [str(p["SleeperID"]) for p in players])
    game_histories = {
        sleeper_id: entry.get("GameHistory") or []
        for sleeper_id, entry in export["Players"].items()
        if entry.get("Status") == "resolved"
    }

    canonical_ids = {
        sleeper_id: str(entry["CanonicalPlayerID"])
        for sleeper_id, entry in export["Players"].items()
        if entry.get("Status") == "resolved" and entry.get("CanonicalPlayerID")
    }
    projections = load_projections(repo_root, league_id, season)
    salary_weeks = load_salary_weeks(derived_root or data_derived_dir(repo_root), league_id, season, bounds.final_scored_week)

    sleeper_path = repo_root / DATA_SOURCE_ROOT / "nfl" / "platform" / "sleeper" / "players.json"
    if not sleeper_path.is_file():
        raise PlayersReadModelError(f"Canonical Sleeper players snapshot is required for depth charts: {sleeper_path}")
    sleeper = json.loads(sleeper_path.read_text(encoding="utf-8"))
    if sleeper.get("SourceDataset") != "sleeper.players" or int(sleeper.get("SchemaVersion", 0)) != 2:
        raise PlayersReadModelError("Unexpected canonical Sleeper players snapshot source or schema version")
    depth_charts: dict[str, Mapping[str, Any]] = {}
    for record in sleeper.get("Records") or []:
        key = str(record.get("SleeperPlayerID") or "").strip()
        if not key:
            raise PlayersReadModelError("Canonical Sleeper players snapshot has a record without SleeperPlayerID")
        if key in depth_charts:
            raise PlayersReadModelError(f"Canonical Sleeper players snapshot lists SleeperPlayerID {key} twice")
        depth_charts[key] = {"Position": record.get("DepthChartPosition"), "Order": record.get("DepthChartOrder")}
    if not depth_charts:
        raise PlayersReadModelError("Canonical Sleeper players snapshot has no records")

    return ReadModelInputs(
        league_id=league_id,
        season=season,
        bounds=bounds,
        population=players,
        valuation_rows=valuation_rows,
        game_histories=game_histories,
        depth_charts=depth_charts,
        bye_weeks=sources.team_bye_weeks(repo_root, season),
        roster_basis=population.get("RosterBasis") or {},
        canonical_ids=canonical_ids,
        projections=projections,
        salary_weeks=salary_weeks,
    )


def resolve(repo_root: Path, league_id: str, season: int, as_of: date, derived_root: Path | None = None) -> ReadModelResult:
    return assemble(load_inputs(repo_root, league_id, season, derived_root), as_of)
