"""Weekly Recaps (KeyPlayers, KeyGames, TeamAwards projection) as a pure function of canonical facts (ADR-063, Issue #1199 section 4).

Port of public/requests/utils/league/WeeklyRecapUtils.psm1 and RequestWeeklyRecaps.ps1. ``resolve_weekly_recaps`` returns the season
model (``SchemaVersion`` 1, ``Season`` text, ``Weeks``) for every week up to ``LeagueScoredWeek`` (ADR-071, decision R2). It is
computed and never persisted; tools/weekly_recaps_app_publish.py writes the App files. Nothing is read from public/data and no clock
is involved. Selection rules, tiebreaks and fail-closed behaviour are those of the PowerShell generator (contract weekly-recaps.yaml).
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from data_roots import DATA_DERIVED_ROOT, DATA_SOURCE_ROOT

from .fantasy_game_context import canonical_matchup_facts
from .matchup_context import (
    MatchupContextError,
    canonical_pairings,
    collection,
    participant_order_from_standings,
    standings_product,
    to_int,
    value_of,
)
from .week_finality import WeekFinalityError, resolve_week_finality

TeamKey = Callable[[Any], "str | None"]
DEFENSE_ID = re.compile(r"^[A-Z]{2,3}$")
KEY_PLAYER_COUNT = 3
KEY_GAME_COUNT = 2


class WeeklyRecapsError(ValueError):
    """Incomplete or contradicting evidence (fail closed)."""


class EvidenceGap(WeeklyRecapsError):
    """A week lacks the starter, identity or game evidence the recap needs (the week is left out of the season model)."""


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _num(value: float) -> int | float:
    """Whole numbers as integers, like the PowerShell JSON output."""
    value = float(value)
    return int(value) if value.is_integer() else value


def _read(path: Path, what: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise WeeklyRecapsError(f"{what} is missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise WeeklyRecapsError(f"{what} is unreadable: {path}: {exc}") from exc


# ---------------------------------------------------------------------------------------------------------------------
# Identity and schedule helpers


def _canon(team_key: TeamKey, value: Any) -> str:
    text = _text(value).upper()
    if text == "":
        return text
    return (team_key(text) or "").upper()


def schedule_week_number(game: Any) -> int:
    match = re.fullmatch(r"(?:Week\s+)?(\d+)", _text(value_of(game, "Week", "gameWeek")))
    return int(match.group(1)) if match else 0


def _away(game: Any, team_key: TeamKey) -> str:
    return _canon(team_key, value_of(game, "away", "teamAbvAway", "AwayTeamAbbr", "AwayTeam"))


def _home(game: Any, team_key: TeamKey) -> str:
    return _canon(team_key, value_of(game, "home", "teamAbvHome", "HomeTeamAbbr", "HomeTeam"))


def kickoff_utc(game: Any) -> str:
    epoch = value_of(game, "gameTime_epoch", "GameTimeEpoch")
    if epoch is not None and _text(epoch) != "":
        try:
            return datetime.fromtimestamp(int(float(epoch)), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except (ValueError, OverflowError, OSError):
            pass
    utc = value_of(game, "KickoffUtc", "StartsAtUtc", "GameTimeUtc")
    if utc is not None and _text(utc) != "":
        try:
            parsed = datetime.fromisoformat(_text(utc).replace("Z", "+00:00"))
            return parsed.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            pass
    raise EvidenceGap(f"WeeklyRecaps cannot resolve kickoff for game '{_text(value_of(game, 'gameID', 'GameID'))}'.")


def roster_identity_map(rows: list[Any]) -> dict[str, dict[str, dict[str, str]]]:
    """Canonical player ID and Sleeper player ID to the week-specific team and position (New-WrRosterIdentityMap)."""
    by_canonical: dict[str, dict[str, str]] = {}
    by_player: dict[str, dict[str, str]] = {}
    for row in rows:
        canonical_id = _text(value_of(row, "CanonicalPlayerID"))
        team_ref = value_of(row, "Team")
        team = _text(value_of(row, "TeamAbbr", "TeamAbv")).upper()
        if team == "" and isinstance(team_ref, str):
            team = team_ref.strip().upper()
        position = _text(value_of(row, "Position")).upper()
        player_id = _text(value_of(value_of(row, "SourceIDs"), "Sleeper"))
        identity = {"CanonicalPlayerID": canonical_id, "PlayerID": player_id, "TeamAbbr": team, "Position": position}
        if canonical_id:
            by_canonical[canonical_id] = identity
        if player_id:
            by_player[player_id] = identity
    return {"ByCanonical": by_canonical, "ByPlayer": by_player}


def _nfl_team_id(team_abbr: str, schedule: list[Any], team_key: TeamKey) -> str:
    key = _canon(team_key, team_abbr)
    ids: set[str] = set()
    for game in schedule:
        if _away(game, team_key) == key:
            ids.add(_text(value_of(game, "teamIDAway", "AwayTeamID")))
        if _home(game, team_key) == key:
            ids.add(_text(value_of(game, "teamIDHome", "HomeTeamID")))
    ids.discard("")
    # Differing key forms of the same team (abbreviation, provider spelling, legacy numeric ID) are one stable team.
    if len({team_key(i) for i in ids}) == 1:
        ids = {sorted(ids)[0]}
    if len(ids) != 1:
        raise EvidenceGap(f"WeeklyRecaps cannot resolve one stable NFLTeamID for '{team_abbr}'.")
    return next(iter(ids))


def _week_game_for_team(team_abbr: str, week: int, schedule: list[Any], team_key: TeamKey) -> Any:
    key = _canon(team_key, team_abbr)
    games = [g for g in schedule if schedule_week_number(g) == week and key in (_away(g, team_key), _home(g, team_key))]
    if len(games) > 1:
        raise EvidenceGap(f"WeeklyRecaps found multiple NFL games for '{team_abbr}' in Week {week}.")
    return games[0] if games else None


def _canonical_game(identity_game: Any, week: int, canonical_schedule: list[Any], team_key: TeamKey) -> Any:
    away, home = _away(identity_game, team_key), _home(identity_game, team_key)
    games = [
        g
        for g in canonical_schedule
        if to_int(value_of(g, "Week")) == week and _away(g, team_key) == away and _home(g, team_key) == home
    ]
    if len(games) != 1:
        raise EvidenceGap(f"WeeklyRecaps cannot match app game '{away}@{home}' Week {week} to exactly one canonical NFL schedule row.")
    return games[0]


# ---------------------------------------------------------------------------------------------------------------------
# One week (New-WeeklyRecapWeekReadModel)


def build_week_recap(
    week: int,
    matchup_ids: set[str],
    team_values: dict[str, Any],
    facts: list[dict[str, Any]],
    schedule: list[Any],
    canonical_schedule: list[Any],
    identity_map: dict[str, dict[str, dict[str, str]]],
    team_order: dict[str, int],
    team_key: TeamKey,
) -> dict[str, Any]:
    """KeyGames and KeyPlayers of one final week from the paired matchup facts of that week."""
    starters: list[dict[str, Any]] = []
    for matchup in facts:
        matchup_id = _text(matchup["FantasyMatchupID"])
        if matchup_id not in matchup_ids:
            raise WeeklyRecapsError(f"WeeklyRecaps canonical matchup '{matchup_id}' is not present in final Matchups Week {week}.")
        for team in matchup["Teams"]:
            key = _text(team["FantasyTeamID"])
            if key not in team_values:
                raise WeeklyRecapsError(f"WeeklyRecaps cannot map FantasyTeamID '{key}' to Matchups Week {week}.")
            if key not in team_order:
                raise WeeklyRecapsError(f"WeeklyRecaps neutral team order is missing FantasyTeamID '{key}'.")
            for player in team["Players"]:
                if not player["IsStarter"]:
                    continue
                if not player["HasPoints"]:
                    raise EvidenceGap(f"WeeklyRecaps final Week {week} has an actual starter without realized point evidence.")
                player_id = _text(player["PlayerID"])
                canonical_id = _text(player.get("CanonicalPlayerID"))
                identity = None
                if canonical_id and canonical_id in identity_map["ByCanonical"]:
                    identity = identity_map["ByCanonical"][canonical_id]
                elif player_id and player_id in identity_map["ByPlayer"]:
                    identity = identity_map["ByPlayer"][player_id]
                if identity is not None:
                    team_abbr, position = identity["TeamAbbr"], identity["Position"]
                elif DEFENSE_ID.fullmatch(player_id.upper()):
                    team_abbr, position = player_id.upper(), "DEF"
                else:
                    raise EvidenceGap(f"WeeklyRecaps cannot resolve week-specific NFL identity for PlayerID '{player_id}' in Week {week}.")
                if team_abbr == "" or position == "":
                    raise EvidenceGap(f"WeeklyRecaps incomplete weekly-roster identity for PlayerID '{player_id}' in Week {week}.")
                starters.append(
                    {
                        "PlayerID": player_id,
                        "FantasyTeamID": team_values[key],
                        "FantasyTeamKey": key,
                        "FantasyMatchupID": matchup_id,
                        "NFLTeamID": _nfl_team_id(team_abbr, schedule, team_key),
                        "Position": position,
                        "Points": float(player["Points"]),
                        "TeamOrder": team_order[key],
                        "Game": _week_game_for_team(team_abbr, week, schedule, team_key),
                    }
                )
    if len(starters) < KEY_PLAYER_COUNT:
        raise EvidenceGap(f"WeeklyRecaps final Week {week} has fewer than three actual starters with complete scoring identity.")

    ranked = sorted(starters, key=lambda s: (-s["Points"], s["TeamOrder"], s["PlayerID"]))[:KEY_PLAYER_COUNT]
    key_players = [
        {
            "PlayerID": s["PlayerID"],
            "FantasyTeamID": s["FantasyTeamID"],
            "NFLTeamID": s["NFLTeamID"],
            "Position": s["Position"],
            "Points": _num(round(s["Points"], 4)),
        }
        for s in ranked
    ]

    groups: dict[str, dict[str, Any]] = {}
    for starter in starters:
        game = starter["Game"]
        if game is None:
            continue
        game_id = _text(value_of(game, "gameID", "GameID"))
        if game_id == "":
            raise EvidenceGap(f"WeeklyRecaps encountered a scheduled starter without GameID in Week {week}.")
        group = groups.setdefault(game_id, {"Game": game, "StarterPoints": 0.0, "StarterCount": 0, "TeamValues": {}, "MatchupIDs": set()})
        group["StarterPoints"] += starter["Points"]
        group["StarterCount"] += 1
        group["TeamValues"][_text(starter["FantasyTeamID"])] = starter["FantasyTeamID"]
        group["MatchupIDs"].add(starter["FantasyMatchupID"])
    if len(groups) < KEY_GAME_COUNT:
        raise EvidenceGap(f"WeeklyRecaps final Week {week} has fewer than two NFL games with actual starter production.")

    candidates: list[dict[str, Any]] = []
    for game_id, group in groups.items():
        identity_game = group["Game"]
        canonical = _canonical_game(identity_game, week, canonical_schedule, team_key)
        away_score, home_score = value_of(canonical, "AwayScore"), value_of(canonical, "HomeScore")
        if away_score is None or home_score is None:
            raise EvidenceGap(f"WeeklyRecaps final Week {week} game '{game_id}' is missing canonical final score evidence.")
        teams = sorted(group["TeamValues"].values(), key=lambda v: (team_order.get(_text(v), 2**31 - 1), _text(v)))
        matchups = sorted(group["MatchupIDs"])
        candidates.append(
            {
                "GameID": game_id,
                "KickoffUtc": kickoff_utc(identity_game),
                "AwayNFLTeamID": _text(value_of(identity_game, "teamIDAway", "AwayTeamID")),
                "HomeNFLTeamID": _text(value_of(identity_game, "teamIDHome", "HomeTeamID")),
                "AwayScore": _num(away_score),
                "HomeScore": _num(home_score),
                "StarterPoints": round(group["StarterPoints"], 4),
                "StarterCount": group["StarterCount"],
                "FantasyTeamIDs": teams,
                "FantasyMatchupIDs": matchups,
            }
        )
    candidates.sort(
        key=lambda c: (-c["StarterPoints"], -len(c["FantasyMatchupIDs"]), -len(c["FantasyTeamIDs"]), -c["StarterCount"], c["KickoffUtc"], c["GameID"])
    )
    key_games = [{**c, "StarterPoints": _num(c["StarterPoints"])} for c in candidates[:KEY_GAME_COUNT]]
    return {"Week": week, "KeyGames": key_games, "KeyPlayers": key_players}


# ---------------------------------------------------------------------------------------------------------------------
# TeamAwards projection (Get-WrTeamAwards)


def team_awards(
    repo_root: Path, league_id: str, season: int, week: int, matchup_rows: list[Any], participants: set[str]
) -> dict[str, Any]:
    """Best Manager and Best Coach of the team-week-performance partition; a missing partition is unavailable, never zero."""
    path = repo_root / DATA_DERIVED_ROOT / "team-week-performance" / league_id / str(season) / f"{week:02d}.json"
    if not path.is_file():
        return {"State": "unavailable", "BestManager": [], "BestCoach": []}
    derived = _read(path, "TeamWeekPerformance partition")
    where = f"{season}/W{week}"
    if (
        to_int(value_of(derived, "ContractVersion")) != 1
        or value_of(derived, "CanonicalLeagueID") != league_id
        or to_int(value_of(derived, "Season")) != season
        or to_int(value_of(derived, "Week")) != week
    ):
        raise WeeklyRecapsError(f"WeeklyRecaps TeamAwards derived partition identity/version mismatch: {path}")
    finality = f"data-source/nfl/game-finality/{season}.json:REG-W{week};league:scored-week-confirmed"
    if (
        value_of(derived, "FinalityEvidence") != finality
        or _text(value_of(derived, "LineupDefinitionHash")) == ""
        or _text(value_of(value_of(derived, "ScoringProfile"), "SettingsHash")) == ""
    ):
        raise WeeklyRecapsError(f"WeeklyRecaps TeamAwards derived finality/scoring provenance is missing or invalid: {path}")

    roster_to_team: dict[str, int] = {}
    team_ids: set[str] = set()
    for row in matchup_rows:
        if to_int(value_of(row, "Week")) != week:
            raise WeeklyRecapsError(f"WeeklyRecaps TeamAwards canonical matchup row week mismatch: {where}")
        roster_id = _text(value_of(row, "CanonicalLeagueRosterID"))
        sleeper = [m for m in collection(value_of(row, "ProviderMappings")) if value_of(m, "Provider") == "Sleeper"]
        if roster_id == "" or roster_id in roster_to_team or len(sleeper) != 1:
            raise WeeklyRecapsError(f"WeeklyRecaps TeamAwards missing/duplicate canonical roster identity: {where}")
        try:
            team_id = int(_text(value_of(sleeper[0], "ProviderRosterID")))
        except ValueError:
            team_id = 0
        if team_id <= 0 or str(team_id) not in participants or str(team_id) in team_ids:
            raise WeeklyRecapsError(f"WeeklyRecaps TeamAwards roster-to-final-Matchups team join failed: {where}")
        roster_to_team[roster_id] = team_id
        team_ids.add(str(team_id))
    if len(roster_to_team) != len(participants) or not roster_to_team:
        raise WeeklyRecapsError(f"WeeklyRecaps TeamAwards historical team population differs from final Matchups: {where}")
    teams: dict[str, Any] = {}
    for team in collection(value_of(derived, "Teams")):
        roster_id = _text(value_of(team, "CanonicalLeagueRosterID"))
        if roster_id not in roster_to_team or roster_id in teams:
            raise WeeklyRecapsError(f"WeeklyRecaps TeamAwards derived team identity disagrees with source: {where}")
        teams[roster_id] = team
    if len(teams) != len(roster_to_team):
        raise WeeklyRecapsError(f"WeeklyRecaps TeamAwards incomplete derived team population: {where}")
    awards = value_of(derived, "Awards")
    # An empty winner array is valid (for example zero potential), absent fields are not.
    if not isinstance(awards, dict) or "BestManagerRosterIDs" not in awards or "BestCoachRosterIDs" not in awards:
        raise WeeklyRecapsError(f"WeeklyRecaps TeamAwards derived winner evidence is missing: {where}")
    result: dict[str, Any] = {"State": "available", "BestManager": [], "BestCoach": []}
    for name in ("BestManager", "BestCoach"):
        seen: set[str] = set()
        winners: list[dict[str, Any]] = []
        for roster in collection(awards[f"{name}RosterIDs"]):
            roster_id = str(roster)
            if roster_id not in teams or roster_id in seen:
                raise WeeklyRecapsError(f"WeeklyRecaps TeamAwards winner has invalid/duplicate roster ID: {where}")
            seen.add(roster_id)
            team = teams[roster_id]
            if name == "BestManager":
                winners.append(
                    {
                        "CanonicalLeagueRosterID": roster_id,
                        "FantasyTeamID": roster_to_team[roster_id],
                        "PotentialPoints": _num(value_of(team, "PotentialPoints") or 0),
                    }
                )
            else:
                efficiency = value_of(team, "EfficiencyPercent")
                if efficiency is None:
                    raise WeeklyRecapsError(f"WeeklyRecaps TeamAwards coach winner lacks efficiency: {where}")
                winners.append(
                    {
                        "CanonicalLeagueRosterID": roster_id,
                        "FantasyTeamID": roster_to_team[roster_id],
                        "EfficiencyPercent": _num(efficiency),
                        "ActualStarterPoints": _num(value_of(team, "ActualStarterPoints") or 0),
                        "PotentialPoints": _num(value_of(team, "PotentialPoints") or 0),
                        "MissedPoints": _num(value_of(team, "MissedPoints") or 0),
                    }
                )
        result[name] = sorted(winners, key=lambda w: w["CanonicalLeagueRosterID"])
    return result


# ---------------------------------------------------------------------------------------------------------------------
# Season model


def _load_matchup_rows(season_dir: Path, week: int) -> list[Any] | None:
    path = season_dir / "matchups" / f"week-{week}.json"
    if not path.is_file():
        return None
    payload = _read(path, f"Canonical matchups week {week}")
    return payload if isinstance(payload, list) else [payload]


def _weekly_roster_rows(repo_root: Path, season: int, week: int) -> list[Any]:
    path = repo_root / DATA_SOURCE_ROOT / "nfl" / "weekly-rosters" / str(season) / f"{week:02d}.json"
    try:
        document = _read(path, f"WeeklyRecaps canonical weekly-roster evidence for {season} Week {week}")
    except WeeklyRecapsError as exc:
        raise EvidenceGap(str(exc)) from exc
    return collection(value_of(document, "Records", "Rows", "Players", "Data"))


def resolve_weekly_recaps(repo_root: Path, league_id: str, season: int) -> dict[str, Any]:
    """The season model of the Weekly Recaps for every league week up to LeagueScoredWeek; raises WeeklyRecapsError on bad evidence."""
    return resolve_with_skips(repo_root, league_id, season)[0]


def resolve_with_skips(repo_root: Path, league_id: str, season: int) -> tuple[dict[str, Any], list[tuple[int, str]]]:
    """The season model plus the weeks left out because their starter or game evidence is incomplete (week and reason).

    The PowerShell generator only recapped weeks whose Matchups completion was final, which needs exactly that evidence, so a week
    without it is absent (not an error); evidence that contradicts itself (TeamAwards, matchup facts) still fails the season.
    """
    from nfl_source_data_lib.teams import NflTeamRegistry
    from schedule_archive import ScheduleArchiveError, build_schedule

    from .decision_windows import make_team_key

    try:
        finality = resolve_week_finality(repo_root, league_id, season)
    except WeekFinalityError as exc:
        raise WeeklyRecapsError(str(exc)) from exc
    empty = {"SchemaVersion": 1, "Season": str(season), "Weeks": []}
    scored = int(finality["LeagueScoredWeek"])
    if scored <= 0:
        return empty, []
    try:
        order = participant_order_from_standings(standings_product(repo_root, league_id, season))
    except MatchupContextError as exc:
        raise WeeklyRecapsError(str(exc)) from exc

    season_dir = repo_root / DATA_SOURCE_ROOT / "leagues" / league_id / "seasons" / str(season)
    pending: list[tuple[int, list[Any], list[dict[str, Any]]]] = []
    for week in range(int(finality["StartWeek"]), scored + 1):
        rows = _load_matchup_rows(season_dir, week)
        if not rows:
            continue
        try:
            pairings, malformed = canonical_pairings(season, week, rows, order)
        except MatchupContextError as exc:
            raise WeeklyRecapsError(str(exc)) from exc
        if not pairings or malformed:
            continue
        pending.append((week, rows, pairings))
    if not pending:
        return empty, []

    try:
        schedule = build_schedule(repo_root, season)
    except ScheduleArchiveError as exc:
        raise WeeklyRecapsError(str(exc)) from exc
    schedule_document = _read(repo_root / DATA_SOURCE_ROOT / "nfl" / "schedules" / f"{season}.json", "WeeklyRecaps canonical NFL schedule")
    canonical_schedule = collection(value_of(schedule_document, "Games"))
    team_key = make_team_key(NflTeamRegistry.load(repo_root))

    weeks: list[dict[str, Any]] = []
    skipped: list[tuple[int, str]] = []
    for week, rows, pairings in pending:
        team_values = {str(p["TeamID"]): p["TeamID"] for pairing in pairings for p in pairing["Participants"]}
        matchup_ids = {pairing["FantasyMatchupID"] for pairing in pairings}
        try:
            facts = canonical_matchup_facts(str(season), week, rows)
        except MatchupContextError as exc:
            raise WeeklyRecapsError(str(exc)) from exc
        try:
            recap = build_week_recap(
                week,
                matchup_ids,
                team_values,
                facts,
                schedule,
                canonical_schedule,
                roster_identity_map(_weekly_roster_rows(repo_root, season, week)),
                order,
                team_key,
            )
        except EvidenceGap as exc:
            skipped.append((week, str(exc)))
            continue
        recap["TeamAwards"] = team_awards(repo_root, league_id, season, week, rows, set(team_values))
        weeks.append(recap)
    return {"SchemaVersion": 1, "Season": str(season), "Weeks": weeks}, skipped
