from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from .canonical_identity import identity_lookup
from .common import CANONICAL_SCHEMA_VERSION, Dataset, as_float, as_int, clean, load_json
from .lifecycle import effective_partition_payload


_PHASE1_DATASET_IDS = {
    "nflverse.schedules",
    "nflverse.game-finality",
    "nflverse.rosters",
    "nflverse.weekly-rosters",
    "nflverse.player-stats",
    "nflverse.snap-counts",
    "sleeper.players",
}


def _iter_csv_path(path: Path) -> Iterable[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        yield from csv.DictReader(handle)


def _persisted_season_paths(dataset: Dataset) -> list[tuple[int, Path]]:
    if not dataset.is_season_partitioned:
        return []
    name = dataset.raw_path.name
    if "{season}" not in name:
        raise ValueError(
            f"Phase-1 season-partitioned dataset {dataset.id} must keep {{season}} in the raw filename"
        )
    prefix, suffix = name.split("{season}", 1)
    result: list[tuple[int, Path]] = []
    for path in sorted(dataset.raw_path.parent.glob(f"{prefix}*{suffix}")):
        middle = path.name[len(prefix):]
        if suffix:
            middle = middle[:-len(suffix)]
        if not re.fullmatch(r"\d{4}", middle):
            continue
        result.append((int(middle), path))
    return result


def _finalized_for_season(season: int, observation_season: int) -> bool:
    return season < observation_season


def _scalar(value: Any) -> int | float | str | bool | None:
    if isinstance(value, bool):
        return value
    text = clean(value)
    if text is None:
        return None
    if re.fullmatch(r"-?(?:0|[1-9]\d*)", text):
        return int(text)
    try:
        return float(text)
    except ValueError:
        return text


def _canonical_partition(
    repo_root: Path,
    dataset: Dataset,
    *,
    relative_path: str,
    season: int,
    observation_season: int,
    payload: dict[str, Any],
    force: bool,
) -> tuple[Path, dict[str, Any], bool]:
    path = repo_root / "source-data/nfl" / relative_path
    effective, preserved = effective_partition_payload(
        dataset,
        path=path,
        candidate=payload,
        partition_season=season,
        observation_season=observation_season,
        force=force,
    )
    return path, effective, preserved


def _build_schedules(
    repo_root: Path,
    dataset: Dataset,
    observation_season: int,
    *,
    force: bool,
) -> tuple[list[tuple[Path, dict[str, Any]]], dict[str, Any], int, dict[str, dict[str, Any]]]:
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    game_index: dict[str, dict[str, Any]] = {}
    for row in _iter_csv_path(dataset.raw_path):
        game_id = clean(row.get("game_id"))
        season = as_int(row.get("season"))
        week = as_int(row.get("week"))
        game_type = clean(row.get("game_type"))
        away_team = clean(row.get("away_team"))
        home_team = clean(row.get("home_team"))
        if not game_id or season is None or week is None or not game_type or not away_team or not home_team:
            raise ValueError("Schedule row is missing canonical game identity fields")
        if game_id in game_index:
            raise ValueError(f"Duplicate nflverse schedule game_id: {game_id}")
        game = {
            "GameID": game_id,
            "GameType": game_type,
            "Week": week,
            "GameDay": clean(row.get("gameday")),
            "WeekDay": clean(row.get("weekday")),
            "GameTime": clean(row.get("gametime")),
            "AwayTeam": away_team,
            "HomeTeam": home_team,
            "AwayScore": as_int(row.get("away_score")),
            "HomeScore": as_int(row.get("home_score")),
            "Overtime": clean(row.get("overtime")),
            "Stadium": clean(row.get("stadium")),
            "Location": clean(row.get("location")),
            "Roof": clean(row.get("roof")),
            "Surface": clean(row.get("surface")),
            "AwayRest": as_int(row.get("away_rest")),
            "HomeRest": as_int(row.get("home_rest")),
            "ProviderGameIDs": {
                key: value
                for key, value in {
                    "OldGameID": clean(row.get("old_game_id")),
                    "GSIS": clean(row.get("gsis")),
                    "NFLDetail": clean(row.get("nfl_detail_id")),
                    "PFR": clean(row.get("pfr")),
                    "PFF": clean(row.get("pff")),
                    "ESPN": clean(row.get("espn")),
                }.items()
                if value
            },
        }
        grouped[season].append(game)
        game_index[game_id] = {"Season": season, **game}

    outputs: list[tuple[Path, dict[str, Any]]] = []
    preserved = 0
    for season, games in sorted(grouped.items()):
        games.sort(key=lambda item: (item["Week"], item["GameType"], item["GameDay"] or "", item["GameID"]))
        payload = {
            "SchemaVersion": CANONICAL_SCHEMA_VERSION,
            "Season": season,
            "SourceDataset": dataset.id,
            "Finalized": _finalized_for_season(season, observation_season),
            "Games": games,
        }
        path, effective, was_preserved = _canonical_partition(
            repo_root,
            dataset,
            relative_path=f"schedules/{season}.json",
            season=season,
            observation_season=observation_season,
            payload=payload,
            force=force,
        )
        outputs.append((path, effective))
        preserved += int(was_preserved)
    audit = {
        "seasonCount": len(grouped),
        "gameCount": len(game_index),
        "earliestSeason": min(grouped) if grouped else None,
        "latestSeason": max(grouped) if grouped else None,
    }
    return outputs, audit, preserved, game_index


def _build_game_finality(
    repo_root: Path,
    dataset: Dataset,
    schedule_index: dict[str, dict[str, Any]],
    observation_season: int,
    *,
    force: bool,
) -> tuple[list[tuple[Path, dict[str, Any]]], dict[str, Any], int]:
    released: set[str] = set()
    for row in _iter_csv_path(dataset.raw_path):
        game_id = clean(row.get("game_id"))
        if not game_id:
            raise ValueError("Released-games evidence contains an empty game_id")
        if game_id in released:
            raise ValueError(f"Duplicate released-games game_id: {game_id}")
        released.add(game_id)

    unknown = sorted(released - set(schedule_index))
    if unknown:
        sample = ", ".join(unknown[:10])
        raise ValueError(f"Released-games evidence references unknown schedule game_id(s): {sample}")

    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for game_id, schedule in schedule_index.items():
        grouped[int(schedule["Season"])].append({
            "GameID": game_id,
            "GameType": schedule["GameType"],
            "Week": schedule["Week"],
            "Final": game_id in released,
        })

    outputs: list[tuple[Path, dict[str, Any]]] = []
    preserved = 0
    final_count = 0
    week_final_count = 0
    for season, games in sorted(grouped.items()):
        games.sort(key=lambda item: (item["Week"], item["GameType"], item["GameID"]))
        final_count += sum(1 for game in games if game["Final"])
        weeks: list[dict[str, Any]] = []
        by_week: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
        for game in games:
            by_week[(game["GameType"], int(game["Week"]))].append(game)
        for (game_type, week), week_games in sorted(by_week.items(), key=lambda item: (item[0][1], item[0][0])):
            final_games = sum(1 for game in week_games if game["Final"])
            week_final = final_games == len(week_games)
            week_final_count += int(week_final)
            weeks.append({
                "GameType": game_type,
                "Week": week,
                "ApplicableGameCount": len(week_games),
                "FinalGameCount": final_games,
                "WeekFinal": week_final,
            })
        payload = {
            "SchemaVersion": CANONICAL_SCHEMA_VERSION,
            "Season": season,
            "SourceDataset": dataset.id,
            "ScheduleDataset": "nflverse.schedules",
            "Finalized": _finalized_for_season(season, observation_season),
            "Games": games,
            "Weeks": weeks,
        }
        path, effective, was_preserved = _canonical_partition(
            repo_root,
            dataset,
            relative_path=f"game-finality/{season}.json",
            season=season,
            observation_season=observation_season,
            payload=payload,
            force=force,
        )
        outputs.append((path, effective))
        preserved += int(was_preserved)
    audit = {
        "releasedEvidenceCount": len(released),
        "scheduleGameCount": len(schedule_index),
        "finalGameCount": final_count,
        "weekFinalCount": week_final_count,
        "unknownReleasedGameIDs": [],
    }
    return outputs, audit, preserved


def _build_rosters(
    repo_root: Path,
    dataset: Dataset,
    canonical: list[dict[str, Any]],
    observation_season: int,
    *,
    weekly: bool,
    force: bool,
) -> tuple[list[tuple[Path, dict[str, Any]]], dict[str, Any], int]:
    lookup = identity_lookup(canonical)
    outputs: list[tuple[Path, dict[str, Any]]] = []
    preserved = 0
    record_count = 0
    resolved_count = 0
    unresolved_count = 0
    missing_provider_id_count = 0

    for season, raw_path in _persisted_season_paths(dataset):
        if weekly:
            grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
            seen: set[tuple[int, str, str]] = set()
        else:
            records: list[dict[str, Any]] = []
            seen = set()

        for row in _iter_csv_path(raw_path):
            row_season = as_int(row.get("season"))
            if row_season is not None and row_season != season:
                raise ValueError(f"{dataset.id} partition {season} contains row for season {row_season}")
            gsis = clean(row.get("gsis_id"))
            team = clean(row.get("team"))
            if not gsis:
                missing_provider_id_count += 1
                continue
            if not team:
                raise ValueError(f"{dataset.id} row {gsis} is missing team")
            week = as_int(row.get("week"))
            if weekly and week is None:
                raise ValueError(f"{dataset.id} row {gsis} is missing week")
            key = (week or 0, team, gsis)
            if key in seen:
                raise ValueError(f"Duplicate {dataset.id} roster identity: season={season} week={week} team={team} gsis={gsis}")
            seen.add(key)
            canonical_player_id = lookup.get(("GSIS", gsis))
            resolved_count += int(canonical_player_id is not None)
            unresolved_count += int(canonical_player_id is None)
            record = {
                "CanonicalPlayerID": canonical_player_id,
                "SourceIDs": {"GSIS": gsis},
                "Team": team,
                "Position": clean(row.get("position")),
                "DepthChartPosition": clean(row.get("depth_chart_position")),
                "JerseyNumber": as_int(row.get("jersey_number")),
                "Status": clean(row.get("status")),
                "StatusDescription": clean(row.get("status_description_abbr")),
                "PlayerName": clean(row.get("full_name")),
                "BirthDate": clean(row.get("birth_date")),
                "Height": as_float(row.get("height")),
                "Weight": as_int(row.get("weight")),
                "College": clean(row.get("college")),
            }
            extra_ids = {
                "ESPN": clean(row.get("espn_id")),
                "PFR": clean(row.get("pfr_id")),
                "PFF": clean(row.get("pff_id")),
                "Sleeper": clean(row.get("sleeper_id")),
                "ESB": clean(row.get("esb_id")),
                "Sportradar": clean(row.get("sportradar_id")),
                "Yahoo": clean(row.get("yahoo_id")),
                "Rotowire": clean(row.get("rotowire_id")),
                "FantasyData": clean(row.get("fantasy_data_id")),
            }
            record["SourceIDs"].update({key: value for key, value in extra_ids.items() if value})
            if weekly:
                record["Week"] = week
                record["GameType"] = clean(row.get("game_type"))
                grouped[week].append(record)
            else:
                records.append(record)
            record_count += 1

        if weekly:
            for week, records_for_week in sorted(grouped.items()):
                records_for_week.sort(key=lambda item: (item["Team"], item["SourceIDs"]["GSIS"]))
                payload = {
                    "SchemaVersion": CANONICAL_SCHEMA_VERSION,
                    "Season": season,
                    "Week": week,
                    "SourceDataset": dataset.id,
                    "Finalized": _finalized_for_season(season, observation_season),
                    "Records": records_for_week,
                }
                path, effective, was_preserved = _canonical_partition(
                    repo_root,
                    dataset,
                    relative_path=f"weekly-rosters/{season}/{week:02d}.json",
                    season=season,
                    observation_season=observation_season,
                    payload=payload,
                    force=force,
                )
                outputs.append((path, effective))
                preserved += int(was_preserved)
        else:
            records.sort(key=lambda item: (item["Team"], item["SourceIDs"]["GSIS"]))
            payload = {
                "SchemaVersion": CANONICAL_SCHEMA_VERSION,
                "Season": season,
                "SourceDataset": dataset.id,
                "Finalized": _finalized_for_season(season, observation_season),
                "Records": records,
            }
            path, effective, was_preserved = _canonical_partition(
                repo_root,
                dataset,
                relative_path=f"rosters/{season}.json",
                season=season,
                observation_season=observation_season,
                payload=payload,
                force=force,
            )
            outputs.append((path, effective))
            preserved += int(was_preserved)

    audit = {
        "partitionCount": len(outputs),
        "recordCount": record_count,
        "resolvedIdentityCount": resolved_count,
        "unresolvedIdentityCount": unresolved_count,
        "missingProviderIDRowCount": missing_provider_id_count,
    }
    return outputs, audit, preserved


_STATS_CONTEXT_FIELDS = {
    "player_id",
    "player_name",
    "player_display_name",
    "position",
    "position_group",
    "headshot_url",
    "season",
    "week",
    "season_type",
    "team",
    "opponent_team",
}


def _build_player_stats(
    repo_root: Path,
    dataset: Dataset,
    canonical: list[dict[str, Any]],
    observation_season: int,
    *,
    force: bool,
) -> tuple[list[tuple[Path, dict[str, Any]]], dict[str, Any], int]:
    lookup = identity_lookup(canonical)
    outputs: list[tuple[Path, dict[str, Any]]] = []
    preserved = 0
    record_count = 0
    resolved_count = 0
    unresolved_count = 0
    missing_provider_id_count = 0

    for season, raw_path in _persisted_season_paths(dataset):
        grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
        seen: set[tuple[str, int, str, str]] = set()
        for row in _iter_csv_path(raw_path):
            row_season = as_int(row.get("season"))
            if row_season is not None and row_season != season:
                raise ValueError(f"{dataset.id} partition {season} contains row for season {row_season}")
            gsis = clean(row.get("player_id"))
            week = as_int(row.get("week"))
            season_type = clean(row.get("season_type"))
            team = clean(row.get("team"))
            if not gsis:
                missing_provider_id_count += 1
                continue
            if week is None or not season_type:
                raise ValueError(f"{dataset.id} row {gsis} is missing week/season_type")
            key = (season_type, week, gsis, team or "")
            if key in seen:
                raise ValueError(
                    f"Duplicate {dataset.id} player/week identity: season={season} type={season_type} week={week} gsis={gsis} team={team}"
                )
            seen.add(key)
            canonical_player_id = lookup.get(("GSIS", gsis))
            resolved_count += int(canonical_player_id is not None)
            unresolved_count += int(canonical_player_id is None)
            stats = {key: _scalar(value) for key, value in row.items() if key not in _STATS_CONTEXT_FIELDS}
            record = {
                "CanonicalPlayerID": canonical_player_id,
                "SourceIDs": {"GSIS": gsis},
                "PlayerName": clean(row.get("player_display_name")) or clean(row.get("player_name")),
                "Position": clean(row.get("position")),
                "PositionGroup": clean(row.get("position_group")),
                "SeasonType": season_type,
                "Week": week,
                "Team": team,
                "OpponentTeam": clean(row.get("opponent_team")),
                "Stats": stats,
            }
            grouped[week].append(record)
            record_count += 1

        for week, records in sorted(grouped.items()):
            records.sort(key=lambda item: (item["SeasonType"], item["Team"] or "", item["SourceIDs"]["GSIS"]))
            payload = {
                "SchemaVersion": CANONICAL_SCHEMA_VERSION,
                "Season": season,
                "Week": week,
                "SourceDataset": dataset.id,
                "Finalized": _finalized_for_season(season, observation_season),
                "Records": records,
            }
            path, effective, was_preserved = _canonical_partition(
                repo_root,
                dataset,
                relative_path=f"player-stats/{season}/{week:02d}.json",
                season=season,
                observation_season=observation_season,
                payload=payload,
                force=force,
            )
            outputs.append((path, effective))
            preserved += int(was_preserved)

    audit = {
        "partitionCount": len(outputs),
        "recordCount": record_count,
        "resolvedIdentityCount": resolved_count,
        "unresolvedIdentityCount": unresolved_count,
        "missingProviderIDRowCount": missing_provider_id_count,
    }
    return outputs, audit, preserved


def _build_snap_counts(
    repo_root: Path,
    dataset: Dataset,
    canonical: list[dict[str, Any]],
    observation_season: int,
    *,
    force: bool,
) -> tuple[list[tuple[Path, dict[str, Any]]], dict[str, Any], int]:
    lookup = identity_lookup(canonical)
    outputs: list[tuple[Path, dict[str, Any]]] = []
    preserved = 0
    record_count = 0
    resolved_count = 0
    unresolved_count = 0
    missing_provider_id_count = 0

    for season, raw_path in _persisted_season_paths(dataset):
        grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
        seen: set[tuple[str, str]] = set()
        for row in _iter_csv_path(raw_path):
            row_season = as_int(row.get("season"))
            if row_season is not None and row_season != season:
                raise ValueError(f"{dataset.id} partition {season} contains row for season {row_season}")
            pfr = clean(row.get("pfr_player_id"))
            game_id = clean(row.get("game_id"))
            week = as_int(row.get("week"))
            if not pfr:
                missing_provider_id_count += 1
                continue
            if not game_id or week is None:
                raise ValueError(f"{dataset.id} row {pfr} is missing game_id/week")
            key = (game_id, pfr)
            if key in seen:
                raise ValueError(f"Duplicate {dataset.id} game/player identity: game={game_id} pfr={pfr}")
            seen.add(key)
            canonical_player_id = lookup.get(("PFR", pfr))
            resolved_count += int(canonical_player_id is not None)
            unresolved_count += int(canonical_player_id is None)
            grouped[week].append({
                "CanonicalPlayerID": canonical_player_id,
                "SourceIDs": {"PFR": pfr},
                "GameID": game_id,
                "PFRGameID": clean(row.get("pfr_game_id")),
                "GameType": clean(row.get("game_type")),
                "Week": week,
                "PlayerName": clean(row.get("player")),
                "Position": clean(row.get("position")),
                "Team": clean(row.get("team")),
                "OpponentTeam": clean(row.get("opponent")),
                "OffenseSnaps": as_int(row.get("offense_snaps")),
                "OffensePct": as_float(row.get("offense_pct")),
                "DefenseSnaps": as_int(row.get("defense_snaps")),
                "DefensePct": as_float(row.get("defense_pct")),
                "SpecialTeamsSnaps": as_int(row.get("st_snaps")),
                "SpecialTeamsPct": as_float(row.get("st_pct")),
            })
            record_count += 1

        for week, records in sorted(grouped.items()):
            records.sort(key=lambda item: (item["GameID"], item["SourceIDs"]["PFR"]))
            payload = {
                "SchemaVersion": CANONICAL_SCHEMA_VERSION,
                "Season": season,
                "Week": week,
                "SourceDataset": dataset.id,
                "Finalized": _finalized_for_season(season, observation_season),
                "Records": records,
            }
            path, effective, was_preserved = _canonical_partition(
                repo_root,
                dataset,
                relative_path=f"snap-counts/{season}/{week:02d}.json",
                season=season,
                observation_season=observation_season,
                payload=payload,
                force=force,
            )
            outputs.append((path, effective))
            preserved += int(was_preserved)

    audit = {
        "partitionCount": len(outputs),
        "recordCount": record_count,
        "resolvedIdentityCount": resolved_count,
        "unresolvedIdentityCount": unresolved_count,
        "missingProviderIDRowCount": missing_provider_id_count,
    }
    return outputs, audit, preserved


def _build_sleeper_players(
    repo_root: Path,
    dataset: Dataset,
    canonical: list[dict[str, Any]],
) -> tuple[list[tuple[Path, dict[str, Any]]], dict[str, Any], int]:
    lookup = identity_lookup(canonical)
    raw = load_json(dataset.raw_path)
    if not isinstance(raw, dict):
        raise ValueError("Sleeper players source must be an object keyed by player_id")
    records: list[dict[str, Any]] = []
    resolved_count = 0
    unresolved_count = 0
    seen: set[str] = set()
    for object_key, row in raw.items():
        if not isinstance(row, dict):
            continue
        key_id = clean(object_key)
        row_id = clean(row.get("player_id"))
        if key_id and row_id and key_id != row_id:
            raise ValueError(
                f"Sleeper player object key {key_id} disagrees with record player_id {row_id}"
            )
        sleeper_id = row_id or key_id
        if not sleeper_id:
            continue
        if sleeper_id in seen:
            raise ValueError(f"Duplicate Sleeper player_id: {sleeper_id}")
        seen.add(sleeper_id)
        canonical_player_id = lookup.get(("Sleeper", sleeper_id))
        resolved_count += int(canonical_player_id is not None)
        unresolved_count += int(canonical_player_id is None)
        records.append({
            "CanonicalPlayerID": canonical_player_id,
            "SleeperPlayerID": sleeper_id,
            "Status": clean(row.get("status")),
            "Team": clean(row.get("team")),
            "Position": clean(row.get("position")),
            "FantasyPositions": row.get("fantasy_positions") if isinstance(row.get("fantasy_positions"), list) else [],
            "InjuryStatus": clean(row.get("injury_status")),
            "InjuryStartDate": clean(row.get("injury_start_date")),
            "PracticeParticipation": clean(row.get("practice_participation")),
            "DepthChartPosition": clean(row.get("depth_chart_position")),
            "DepthChartOrder": as_int(row.get("depth_chart_order")),
        })
    records.sort(key=lambda item: item["SleeperPlayerID"])
    payload = {
        "SchemaVersion": CANONICAL_SCHEMA_VERSION,
        "SourceDataset": dataset.id,
        "Records": records,
    }
    path = repo_root / "source-data/nfl/platform/sleeper/players.json"
    audit = {
        "recordCount": len(records),
        "resolvedIdentityCount": resolved_count,
        "unresolvedIdentityCount": unresolved_count,
    }
    return [(path, payload)], audit, 0


def build_phase1_outputs(
    repo_root: Path,
    datasets: dict[str, Dataset],
    canonical: list[dict[str, Any]],
    observation_season: int,
    *,
    force: bool = False,
) -> tuple[list[tuple[Path, dict[str, Any]]], dict[str, Any], int]:
    """Build all activated Phase-1 canonical source-data outputs before publication."""
    outputs: list[tuple[Path, dict[str, Any]]] = []
    audit: dict[str, Any] = {}
    preserved = 0

    schedule_index: dict[str, dict[str, Any]] = {}
    schedule_dataset = datasets.get("nflverse.schedules")
    if schedule_dataset is not None:
        built, coverage, count, schedule_index = _build_schedules(
            repo_root, schedule_dataset, observation_season, force=force
        )
        outputs.extend(built)
        audit["schedules"] = coverage
        preserved += count

    finality_dataset = datasets.get("nflverse.game-finality")
    if finality_dataset is not None:
        if not schedule_index:
            raise ValueError("nflverse.game-finality materialization requires nflverse.schedules")
        built, coverage, count = _build_game_finality(
            repo_root,
            finality_dataset,
            schedule_index,
            observation_season,
            force=force,
        )
        outputs.extend(built)
        audit["gameFinality"] = coverage
        preserved += count

    rosters_dataset = datasets.get("nflverse.rosters")
    if rosters_dataset is not None:
        built, coverage, count = _build_rosters(
            repo_root, rosters_dataset, canonical, observation_season, weekly=False, force=force
        )
        outputs.extend(built)
        audit["rosters"] = coverage
        preserved += count

    weekly_rosters_dataset = datasets.get("nflverse.weekly-rosters")
    if weekly_rosters_dataset is not None:
        built, coverage, count = _build_rosters(
            repo_root,
            weekly_rosters_dataset,
            canonical,
            observation_season,
            weekly=True,
            force=force,
        )
        outputs.extend(built)
        audit["weeklyRosters"] = coverage
        preserved += count

    stats_dataset = datasets.get("nflverse.player-stats")
    if stats_dataset is not None:
        built, coverage, count = _build_player_stats(
            repo_root, stats_dataset, canonical, observation_season, force=force
        )
        outputs.extend(built)
        audit["playerStats"] = coverage
        preserved += count

    snaps_dataset = datasets.get("nflverse.snap-counts")
    if snaps_dataset is not None:
        built, coverage, count = _build_snap_counts(
            repo_root, snaps_dataset, canonical, observation_season, force=force
        )
        outputs.extend(built)
        audit["snapCounts"] = coverage
        preserved += count

    sleeper_dataset = datasets.get("sleeper.players")
    if sleeper_dataset is not None:
        built, coverage, count = _build_sleeper_players(repo_root, sleeper_dataset, canonical)
        outputs.extend(built)
        audit["sleeperPlayers"] = coverage
        preserved += count

    duplicate_paths = [path for path, count in Counter(path for path, _ in outputs).items() if count > 1]
    if duplicate_paths:
        raise ValueError(f"Phase-1 materializers produced duplicate output paths: {duplicate_paths}")

    audit["activeDatasetIDs"] = sorted(set(datasets) & _PHASE1_DATASET_IDS)
    audit["canonicalOutputFileCount"] = len(outputs)
    audit["frozenPartitionsPreserved"] = preserved
    return outputs, audit, preserved
