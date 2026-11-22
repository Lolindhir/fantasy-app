"""Neutral App-shaped NFL schedule games from canonical facts (Issue #1263 CP3, finding F8).

Pure conversion of ``data-source/nfl/schedules`` + ``game-finality`` into the game records that Decision Windows, the lifecycle,
the FantasyGameContext and the Weekly Recaps join to (and that ``Schedule.json`` / the Schedule archives deliver). It lives in the
Shared Derived library so no derivation imports a consumer generator; ``tools/schedule_archive.py`` renders the archives from it.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from data_roots import DATA_SOURCE_ROOT
from derived_data_lib.nfl_games import kickoff_epoch as shared_kickoff_epoch

POSTSEASON_TYPES = {"WC", "DIV", "CON", "SB"}

# Games that happened (or were scheduled and cancelled) but are missing in the canonical nflverse schedule.
# Fields are the canonical-row equivalents; the record is built by the same code as every other game.
SUPPLEMENTS: dict[int, list[dict[str, Any]]] = {
    2022: [
        {
            "GameID": "2022_17_BUF_CIN", "GameType": "REG", "Week": 17, "GameDay": "2023-01-02", "GameTime": "20:30",
            "AwayTeam": "BUF", "HomeTeam": "CIN", "Location": "Home", "Overtime": "0",
            "ProviderGameIDs": {"ESPN": "401437947"}, "_Status": "Canceled",
        }
    ]
}


class ScheduleArchiveError(RuntimeError):
    """Raised when a canonical schedule cannot be turned into an archive safely."""


class TeamRegistry:
    def __init__(self, root: Path) -> None:
        payload = json.loads((root / DATA_SOURCE_ROOT / "nfl" / "teams.json").read_text(encoding="utf-8"))
        self.canonical: set[str] = set()
        self.alias: dict[str, tuple[str, int | None]] = {}
        self.provider: dict[str, str] = {}
        for team in payload["Teams"]:
            abbr = team["TeamAbbr"]
            self.canonical.add(abbr)
            for alias in team.get("Aliases", []):
                self.alias[alias["Alias"]] = (abbr, alias.get("LastSeason"))
                if alias.get("Kind") == "provider-spelling" and alias.get("LastSeason") is None:
                    self.provider[abbr] = alias["Alias"]

    def resolve(self, value: str, season: int) -> str:
        value = value.strip()
        if not value:
            raise ScheduleArchiveError("Canonical NFL schedule row has an empty team.")
        if value in self.canonical:
            return value
        hit = self.alias.get(value)
        if hit is None:
            raise ScheduleArchiveError(f"Unknown NFL team '{value}'.")
        team, last_season = hit
        if last_season is not None and season > last_season:
            raise ScheduleArchiveError(f"NFL team alias '{value}' is not valid in season {season}.")
        return team

    def provider_spelling(self, team: str) -> str:
        return self.provider.get(team, team)

    def cbs_spelling(self, team: str) -> str:
        return {"JAX": "JAC", "WSH": "WAS"}.get(self.provider_spelling(team), self.provider_spelling(team))


def kickoff_epoch(game_day: str, game_time: str | None) -> str | None:
    """Kickoff as App epoch text; the conversion is owned by the nfl-games product module (Issue #1572)."""
    if not game_time or not game_time.strip():
        return None
    try:
        return shared_kickoff_epoch("schedule-archive", game_day, game_time)
    except ValueError as exc:
        raise ScheduleArchiveError(str(exc)) from exc


def game_time_text(game_time: str | None) -> str:
    if not game_time or not game_time.strip():
        return "TBD"
    parts = game_time.strip().split(":")
    if len(parts) != 2 or not all(p.isdigit() for p in parts):
        raise ScheduleArchiveError(f"Canonical GameTime '{game_time}' is not HH:mm.")
    hour, minute = int(parts[0]), int(parts[1])
    if hour > 23 or minute > 59:
        raise ScheduleArchiveError(f"Canonical GameTime '{game_time}' is out of range.")
    return f"{hour % 12 or 12}:{parts[1]}{'p' if hour >= 12 else 'a'}"


def season_type(game_type: str) -> str:
    kind = game_type.strip().upper()
    if kind == "REG":
        return "Regular Season"
    if kind in POSTSEASON_TYPES:
        return "Post Season"
    raise ScheduleArchiveError(f"Unsupported canonical NFL GameType '{game_type}'.")


def _score(value: Any) -> int | float | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        number = float(value)
    except ValueError:
        return None
    return int(number) if number == int(number) else number


def app_game(canonical: dict[str, Any], final: bool, season: int, teams: TeamRegistry) -> dict[str, Any]:
    espn = str((canonical.get("ProviderGameIDs") or {}).get("ESPN") or "").strip()
    if not espn:
        raise ScheduleArchiveError(f"Canonical NFL game '{canonical['GameID']}' has no ESPN provider ID.")
    away = teams.resolve(str(canonical["AwayTeam"]), season)
    home = teams.resolve(str(canonical["HomeTeam"]), season)
    game_day = str(canonical["GameDay"])
    date_key = game_day.replace("-", "")
    if len(date_key) != 8 or not date_key.isdigit():
        raise ScheduleArchiveError(f"Canonical NFL game '{canonical['GameID']}' has an invalid GameDay '{game_day}'.")
    game_id = f"{date_key}_{teams.provider_spelling(away)}@{teams.provider_spelling(home)}"
    cbs_id = f"{date_key}_{teams.cbs_spelling(away)}@{teams.cbs_spelling(home)}"
    time_raw = canonical.get("GameTime")
    epoch = kickoff_epoch(game_day, time_raw)
    overtime = str(canonical.get("Overtime") or "")
    has_overtime = overtime.strip() != "" and overtime != "0"
    status_override = canonical.get("_Status")
    if status_override:
        status, code = status_override, "0"
    elif final:
        status, code = ("Final/OT" if has_overtime else "Final"), "2"
    else:
        status, code = "Scheduled", "0"
    record: dict[str, Any] = {
        "gameID": game_id,
        "CanonicalGameID": str(canonical["GameID"]),
        "espnID": espn,
        "season": str(season),
        "seasonType": season_type(str(canonical["GameType"])),
        "gameWeek": f"Week {int(canonical['Week'])}",
        "gameDate": date_key,
        "gameTime": game_time_text(time_raw),
        "gameTime_epoch": "" if epoch is None else epoch,
        "away": away,
        "home": home,
        "teamIDAway": away,
        "teamIDHome": home,
        "neutralSite": "True" if canonical.get("Location") == "Neutral" else "False",
        "gameStatus": status,
        "gameStatusCode": code,
        "espnLink": f"https://www.espn.com/nfl/boxscore/_/gameId/{espn}",
        "cbsLink": f"https://www.cbssports.com/nfl/gametracker/boxscore/NFL_{cbs_id}",
    }
    if final and not status_override:
        away_score, home_score = _score(canonical.get("AwayScore")), _score(canonical.get("HomeScore"))
        if away_score is not None and home_score is not None:
            record["awayPts"] = away_score
            record["homePts"] = home_score
    return record


def build_schedule(root: Path, season: int, game_types: set[str] | None = None) -> list[dict[str, Any]]:
    """App schedule array of one season; game_types None keeps every type. Fails closed on inconsistent inputs."""
    base = root / DATA_SOURCE_ROOT / "nfl"
    try:
        schedule = json.loads((base / "schedules" / f"{season}.json").read_text(encoding="utf-8"))
        finality = json.loads((base / "game-finality" / f"{season}.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise ScheduleArchiveError(f"Canonical NFL schedule/finality for {season} is unreadable: {exc}") from exc
    if schedule.get("Season") != season or finality.get("Season") != season:
        raise ScheduleArchiveError(f"Canonical NFL schedule/finality season mismatch for {season}.")
    if schedule.get("SourceDataset") != "nflverse.schedules" or finality.get("SourceDataset") != "nflverse.game-finality":
        raise ScheduleArchiveError(f"Unexpected canonical NFL source dataset for {season}.")
    final_by_game: dict[str, bool] = {}
    for row in finality.get("Games") or []:
        game_id = str(row.get("GameID") or "")
        if not game_id or game_id in final_by_game:
            raise ScheduleArchiveError(f"Invalid or duplicate canonical game-finality GameID '{game_id}'.")
        final_by_game[game_id] = bool(row.get("Final"))
    games = schedule.get("Games") or []
    if not games:
        raise ScheduleArchiveError(f"Canonical NFL schedule {season} contains no games.")
    ids = [str(g.get("GameID") or "") for g in games]
    if "" in ids or len(set(ids)) != len(ids):
        raise ScheduleArchiveError(f"Canonical NFL schedule {season} has a missing or duplicate GameID.")
    missing = [i for i in ids if i not in final_by_game]
    extra = [i for i in final_by_game if i not in set(ids)]
    if missing or extra:
        raise ScheduleArchiveError(f"Canonical NFL finality does not match the schedule {season}: missing {missing[:3]}, extra {extra[:3]}.")

    teams = TeamRegistry(root)
    records: list[dict[str, Any]] = []
    seen_espn: set[str] = set()
    seen_game: set[str] = set()
    rows = [(g, final_by_game[str(g["GameID"])]) for g in games] + [(s, False) for s in SUPPLEMENTS.get(season, [])]
    for canonical, final in rows:
        if game_types is not None and canonical["GameType"] not in game_types:
            continue
        record = app_game(canonical, final, season, teams)
        if record["espnID"] in seen_espn or record["gameID"] in seen_game:
            raise ScheduleArchiveError(f"Duplicate game '{record['gameID']}' / ESPN ID '{record['espnID']}' in {season}.")
        seen_espn.add(record["espnID"])
        seen_game.add(record["gameID"])
        records.append(record)
    if not records:
        raise ScheduleArchiveError(f"Canonical NFL schedule {season} has no games for the requested types.")

    def sort_key(r: dict[str, Any]) -> tuple[str, float, str]:
        epoch = float(r["gameTime_epoch"]) if r["gameTime_epoch"] else float("inf")
        return (r["gameDate"], epoch, r["gameID"])

    return sorted(records, key=sort_key)
