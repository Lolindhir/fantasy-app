#!/usr/bin/env python3
"""Consumer generator: past-season Schedule archives public/data/past_seasons/Schedule_<season>.json (Issue #999 step 7b).

The files are no static archives: they are rebuilt from the canonical NFL facts
(data-source/nfl/schedules/<season>.json + game-finality/<season>.json) and rewritten only on a semantic difference,
so a change of the derivation logic or a corrected canonical fact reaches them with the next weekly run.

The record shape, the field order and every conversion repeat public/requests/utils/general/CanonicalScheduleUtils.psm1
(New-AppScheduleGame, Get-CanonicalAppSchedule), which builds the current Schedule.json. `compare-current` proves that
parity against the published Schedule.json. Unlike the current file the archives keep all game types (the records carry
seasonType), so postseason games are part of them.

One game is not part of the canonical schedule: the cancelled 2022 week-17 game BUF@CIN. It is added from SUPPLEMENTS
(hand-maintained NFL fact, explicit and visible) because the archive has always listed it.

Usage:
  schedule_archive.py compare-current            parity of the generator with public/data/Schedule.json
  schedule_archive.py write [--season N ...]     write the archives (default: first needed season up to the season before the current league season)
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))

from data_roots import DATA_SOURCE_ROOT  # noqa: E402
from derived_data_lib.models.registry import get_model  # noqa: E402
from league_metadata import data_meta_root, load_all_league_metadata, model_for  # noqa: E402

EASTERN = ZoneInfo("America/New_York")
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
    if not game_time or not game_time.strip():
        return None
    text = f"{game_day.strip()} {game_time.strip()}"
    try:
        local = datetime.strptime(text, "%Y-%m-%d %H:%M")
    except ValueError as exc:
        raise ScheduleArchiveError(f"Canonical kickoff '{text}' is not a valid yyyy-MM-dd HH:mm value.") from exc
    first = local.replace(tzinfo=EASTERN, fold=0)
    second = local.replace(tzinfo=EASTERN, fold=1)
    if first.utcoffset() != second.utcoffset():
        raise ScheduleArchiveError(f"Canonical kickoff '{text}' is ambiguous or does not exist in Eastern time.")
    return f"{int(first.timestamp())}.0"


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


def _dump(payload: Any) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _current_season(root: Path) -> int:
    """Latest current season over all league manifests (the NFL schedule is league-independent)."""
    seasons = []
    for manifest_path in sorted((root / DATA_SOURCE_ROOT / "leagues").glob("*/manifest.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        seasons.append(int(str(manifest["CurrentCanonicalLeagueSeasonID"]).rsplit("-", 1)[-1]))
    if not seasons:
        raise ScheduleArchiveError("No league manifest found; the current season is unknown.")
    return max(seasons)


def write_archives(root: Path, seasons: list[int]) -> list[str]:
    """Write Schedule_<season>.json only where the content differs semantically; returns the changed paths."""
    changed: list[str] = []
    target = root / "public" / "data" / "past_seasons"
    for season in seasons:
        records = build_schedule(root, season)
        path = target / f"Schedule_{season}.json"
        if path.is_file() and _load(path) == records:
            continue
        path.write_text(_dump(records), encoding="utf-8")
        changed.append(f"public/data/past_seasons/Schedule_{season}.json")
    return changed


def first_needed_season(root: Path) -> int:
    """Oldest season any league needs: its first season minus the history its Salary model reads (salary-v1: 3)."""
    firsts = []
    for metadata in load_all_league_metadata(data_meta_root(root)).values():
        for season in metadata["Seasons"]:
            model = get_model(model_for(metadata, season, "Salary"), "salary")
            firsts.append(int(season) - int(getattr(model, "HISTORY_SEASONS", 0)))
    if not firsts:
        raise ScheduleArchiveError("No league season found; the first needed archive season is unknown.")
    return min(firsts)


def default_seasons(root: Path) -> list[int]:
    return list(range(first_needed_season(root), _current_season(root)))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parent.parent))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("compare-current", help="generator parity with the published public/data/Schedule.json")
    write = sub.add_parser("write", help="write the past-season archives (semantic no-op)")
    write.add_argument("--season", type=int, action="append", help="limit to season(s); default all archive seasons")
    write.add_argument("--fail-on-error", action="store_true", help="exit 1 when a season cannot be built")
    args = parser.parse_args(argv)
    root = Path(args.repo_root)

    if args.command == "compare-current":
        season = _current_season(root)
        built = build_schedule(root, season, {"REG"})
        published = _load(root / "public" / "data" / "Schedule.json")
        if built == published and [list(r) for r in built] == [list(r) for r in published]:
            print(f"OK: generator equals public/data/Schedule.json ({len(built)} games, season {season}).")
            return 0
        diffs = [(a, b) for a, b in zip(built, published) if a != b][:3]
        print(f"MISMATCH: built {len(built)} vs published {len(published)} games; first differences: {diffs}")
        return 1

    failures = 0
    for season in args.season or default_seasons(root):
        try:
            changed = write_archives(root, [season])
        except ScheduleArchiveError as exc:
            failures += 1
            print(f"::warning::Schedule archive {season} kept as is: {exc}")
            continue
        print(f"Schedule_{season}.json: {'written' if changed else 'unchanged'}")
    return 1 if failures and args.fail_on_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
