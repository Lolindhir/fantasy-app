"""Canonical inputs of the PlayerValuation product (ADR-055, .ai-context/manual/player-valuation.yaml).

Reads persisted NFL and League facts and turns them into the prepared inputs that
``derived_data_lib.player_valuation`` needs. Scoring, identity resolution and week bounds are not
re-implemented here: they come from ``players_league_scoring`` (ADR-041) and ``players_population``
(ADR-043), the same code paths RequestPlayers.ps1 uses today.

Population per season:
  current season     players_population.build_population (Sleeper snapshot, ADR-043 rule)
  completed seasons  canonical NFL rosters of that season (season roster plus weekly rosters) with a
                     Sleeper source ID, an app fantasy position and a valid birth date; the same three
                     reasons (roster, draft, league_owned) are evaluated against that season's facts.
                     A league-owned Sleeper ID that no roster record explains cannot be positioned and
                     is counted as skipped (Missing, not zero).
"""
from __future__ import annotations

import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from data_roots import DATA_SOURCE_ROOT  # noqa: E402
from derived_data_lib.player_valuation import GameRef, PlayerBasis  # noqa: E402
from historical_fantasy_scoring import read_json  # noqa: E402
from nfl_source_data_lib.teams import NflTeamRegistry  # noqa: E402
from player_week_fantasy import build_scoring_profile_identity  # noqa: E402
from players_league_scoring import (  # noqa: E402
    build_export,
    league_owned_sleeper_ids,
    league_scoring_settings,
    resolve_league_week_bounds,
)
from players_population import (  # noqa: E402
    APP_FANTASY_POSITIONS,
    REASON_DRAFT,
    REASON_LEAGUE,
    REASON_ROSTER,
    build_population,
    draft_basis,
    valid_birth_date,
)

PRODUCT = "player-valuation"


class SourceError(RuntimeError):
    """Raised when canonical inputs are missing or inconsistent (fail closed)."""


@dataclass(frozen=True)
class SeasonSource:
    league_id: str
    season: int
    scoring_profile: dict[str, Any]
    team_count: int
    last_league_week: int
    final_scored_week: int
    bye_weeks: dict[str, int]
    players: list[PlayerBasis]
    report: dict[str, Any]


def league_manifest(repo_root: Path, league_id: str) -> dict[str, Any]:
    path = repo_root / DATA_SOURCE_ROOT / "leagues" / league_id / "manifest.json"
    if not path.is_file():
        raise SourceError(f"League manifest missing: {path}")
    return read_json(path)


def manifest_seasons(manifest: dict[str, Any]) -> list[int]:
    return sorted(int(item["Season"]) for item in manifest.get("Seasons", []))


def current_season(manifest: dict[str, Any]) -> int:
    return int(str(manifest["CurrentCanonicalLeagueSeasonID"]).rsplit("-", 1)[-1])


def team_count(repo_root: Path, league_id: str, season: int) -> int:
    path = repo_root / DATA_SOURCE_ROOT / "leagues" / league_id / "seasons" / str(season) / "league.json"
    count = (read_json(path).get("Settings") or {}).get("num_teams")
    if isinstance(count, bool) or not isinstance(count, int) or count < 1:
        raise SourceError(f"Settings.num_teams must be a positive integer in {path}")
    return count


def team_bye_weeks(repo_root: Path, season: int) -> dict[str, int]:
    """Canonical team -> bye week (the single REG week without a game); port of Get-CanonicalNflTeamByeWeeks."""
    path = repo_root / DATA_SOURCE_ROOT / "nfl/schedules" / f"{season}.json"
    if not path.is_file():
        raise SourceError(f"Canonical NFL schedule is required for bye weeks: {path}")
    schedule = read_json(path)
    if int(schedule.get("Season", 0)) != season or schedule.get("SourceDataset") != "nflverse.schedules":
        raise SourceError(f"Unexpected canonical NFL schedule in {path}")
    games = [g for g in schedule["Games"] if g.get("GameType") == "REG"]
    if not games:
        raise SourceError(f"Canonical NFL schedule {season} has no REG games")
    max_week = max(int(g["Week"]) for g in games)
    weeks_by_team: dict[str, set[int]] = {}
    for game in games:
        for team in (game.get("HomeTeam"), game.get("AwayTeam")):
            if not team:
                raise SourceError(f"Canonical NFL schedule {season} has a REG game without both teams: {game.get('GameID')}")
            week = int(game["Week"])
            if week in weeks_by_team.setdefault(team, set()):
                raise SourceError(f"Canonical NFL schedule {season} lists {team} twice in week {week}")
            weeks_by_team[team].add(week)
    byes: dict[str, int] = {}
    for team, weeks in weeks_by_team.items():
        missing = [w for w in range(1, max_week + 1) if w not in weeks]
        if len(missing) != 1:
            raise SourceError(f"Canonical NFL schedule {season}: team {team} has {len(missing)} REG weeks without a game (expected one bye)")
        byes[team] = missing[0]
    return byes


def _roster_records(repo_root: Path, season: int) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Season roster records plus each CanonicalPlayerID's team in the latest weekly roster."""
    nfl = repo_root / DATA_SOURCE_ROOT / "nfl"
    path = nfl / "rosters" / f"{season}.json"
    if not path.is_file():
        raise SourceError(f"Canonical NFL roster missing for {season}: {path}")
    records = list(read_json(path)["Records"])
    final_team: dict[str, str] = {}
    weekly_dir = nfl / "weekly-rosters" / str(season)
    for weekly_path in sorted(weekly_dir.glob("*.json"), key=lambda p: int(p.stem)) if weekly_dir.is_dir() else []:
        for record in read_json(weekly_path)["Records"]:
            records.append(record)
            if record.get("GameType", "REG") == "REG" and record.get("Team"):
                final_team[str(record["CanonicalPlayerID"])] = str(record["Team"])
    return records, final_team


def historical_population(repo_root: Path, league_id: str, season: int) -> tuple[list[dict[str, Any]], Counter]:
    registry = NflTeamRegistry.load(repo_root)
    records, final_team = _roster_records(repo_root, season)
    draft_ids = draft_basis(repo_root, season)
    owned = league_owned_sleeper_ids(repo_root, league_id, season)
    skipped: Counter = Counter()
    by_sleeper: dict[str, dict[str, Any]] = {}
    for record in records:
        sleeper_id = (record.get("SourceIDs") or {}).get("Sleeper")
        if not sleeper_id:
            skipped["no_sleeper_id"] += 1
            continue
        position = str(record.get("Position") or "").upper()
        if position not in APP_FANTASY_POSITIONS:
            skipped["no_app_position"] += 1
            continue
        if not valid_birth_date(record.get("BirthDate")):
            skipped["no_valid_birth_date"] += 1
            continue
        cid = str(record["CanonicalPlayerID"])
        team = final_team.get(cid) or record.get("Team")
        by_sleeper[str(sleeper_id)] = {
            "SleeperID": str(sleeper_id),
            "CanonicalHint": cid,
            "Position": position,
            "TeamID": registry.resolve(str(team), season) if team else None,
        }
    population: list[dict[str, Any]] = []
    for sleeper_id, row in sorted(by_sleeper.items()):
        reasons = [REASON_ROSTER]
        if row["CanonicalHint"] in draft_ids:
            reasons.append(REASON_DRAFT)
        if sleeper_id in owned:
            reasons.append(REASON_LEAGUE)
        population.append({**row, "Reasons": reasons})
    unexplained = owned - set(by_sleeper)
    if unexplained:
        skipped["league_owned_without_roster_record"] += len(unexplained)
    return population, skipped


def current_population(repo_root: Path, league_id: str, season: int) -> tuple[list[dict[str, Any]], Counter]:
    export = build_population(repo_root, league_id, season)
    population = [
        {"SleeperID": p["SleeperID"], "Position": p["Position"], "TeamID": p["TeamID"], "Reasons": list(p["Reasons"])}
        for p in export["Players"]
    ]
    return population, Counter(export["Counts"].get("Skipped", {}))


WEEK_ROW_KEYS = ("Points", "Snaps", "KickAttempts", "Attempts", "TdPass", "TdRec", "TdRush")


def _games_of(history: list[dict[str, Any]] | None) -> tuple[GameRef, ...]:
    """GameHistory entries (newest first) reduced to what the Form basis needs."""
    return tuple(
        GameRef(game_id=str(entry["GameID"]), week=int(entry["Week"]), week_final=bool(entry["WeekFinal"]))
        for entry in history or []
    )


def _weeks_of(entry_seasons: dict[str, dict[str, dict[str, Any]]]) -> dict[int, dict[int, dict[str, float]]]:
    return {
        int(season): {
            int(week): {key: row[key] for key in WEEK_ROW_KEYS}
            for week, row in weeks.items()
        }
        for season, weeks in entry_seasons.items()
    }


def load_season_source(repo_root: Path, league_id: str, season: int, manifest: dict[str, Any]) -> SeasonSource:
    scoring = league_scoring_settings(repo_root, league_id, season)
    profile = build_scoring_profile_identity(league_id, season, scoring)
    bounds = resolve_league_week_bounds(repo_root, league_id, season)
    is_current = season == current_season(manifest)
    population, skipped = (current_population if is_current else historical_population)(repo_root, league_id, season)
    if not population:
        raise SourceError(f"Empty population for {league_id} {season}")

    export = build_export(repo_root, league_id, season, [row["SleeperID"] for row in population])
    players: list[PlayerBasis] = []
    for row in population:
        entry = export["Players"][row["SleeperID"]]
        players.append(PlayerBasis(
            sleeper_id=row["SleeperID"],
            canonical_id=entry.get("CanonicalPlayerID"),
            position=row["Position"],
            team=row["TeamID"],
            population=tuple(row["Reasons"]),
            identity_status=entry["Status"],
            weeks=_weeks_of(entry.get("Seasons") or {}),
            games=_games_of(entry.get("GameHistory")),
        ))
    statuses = Counter(p.identity_status for p in players)
    report = {
        "Season": season,
        "PopulationBasis": "sleeper-snapshot" if is_current else "canonical-rosters",
        "Players": len(players),
        "IdentityStatus": dict(sorted(statuses.items())),
        "Skipped": dict(sorted(skipped.items())),
        "UnresolvedHistory": len(export.get("UnresolvedHistory") or []),
        "LastLeagueWeek": bounds["LastLeagueWeek"],
        "FinalScoredWeek": bounds["FinalScoredWeek"],
    }
    return SeasonSource(
        league_id=league_id,
        season=season,
        scoring_profile=profile,
        team_count=team_count(repo_root, league_id, season),
        last_league_week=bounds["LastLeagueWeek"],
        final_scored_week=bounds["FinalScoredWeek"],
        bye_weeks=team_bye_weeks(repo_root, season),
        players=players,
        report=report,
    )
