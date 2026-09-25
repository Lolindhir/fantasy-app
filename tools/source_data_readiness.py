#!/usr/bin/env python3
"""Build deterministic readiness audits for canonical NFL and League source data."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from league_source_data_lib.coverage import build_season_player_reference_coverage
from nfl_source_data_lib.coverage import build_player_stats_identity_coverage
from nfl_source_data_lib.history import HISTORICAL_BANDS, known_unavailable_reason

LARGE_FILE_BYTES = 5 * 1024 * 1024
SPECIAL_TEAMS_FUMBLE_EVENTS_DATASET_ID = "nflverse.special-teams-fumble-events"


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json_if_changed(path: Path, value: Any) -> bool:
    content = json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def git_last_change(repo_root: Path, relative_path: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%cI", "--", relative_path],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    value = result.stdout.strip()
    return value or None


def current_season(repo_root: Path) -> int:
    schedules = repo_root / "source-data/nfl/schedules"
    values = [int(path.stem) for path in schedules.glob("*.json") if path.stem.isdigit()]
    if not values:
        raise ValueError("Cannot determine source season: no canonical schedule seasons exist")
    return max(values)


def registry_dataset(repo_root: Path, dataset_id: str) -> dict[str, Any]:
    registry = read_json(repo_root / "source-data/registry.json", {})
    for dataset in registry.get("datasets", []):
        if dataset.get("id") == dataset_id:
            return dataset
    raise KeyError(dataset_id)


def render_path(template: str, season: int) -> str:
    return template.replace("{season}", str(season))


def canonical_partition_count(repo_root: Path, canonical: str, season: int) -> int:
    root = repo_root / "source-data/nfl" / canonical
    file_path = root / f"{season}.json"
    if file_path.exists():
        return 1
    season_dir = root / str(season)
    if season_dir.exists():
        return len(list(season_dir.glob("*.json")))
    return 0




def build_special_teams_fumble_historical_coverage(repo_root: Path, season: int) -> dict[str, Any]:
    finality_path = repo_root / "source-data/nfl/game-finality" / f"{season}.json"
    finality = read_json(finality_path)
    contract_errors: list[str] = []
    expected_weeks: set[int] = set()

    if not isinstance(finality, dict):
        contract_errors.append(f"{season}: game-finality evidence missing or invalid")
    elif finality.get("Finalized") is not True:
        contract_errors.append(f"{season}: game-finality evidence is not finalized")
    else:
        weeks = finality.get("Weeks")
        if not isinstance(weeks, list):
            contract_errors.append(f"{season}: game-finality evidence has no Weeks array")
        else:
            for index, row in enumerate(weeks):
                if not isinstance(row, dict):
                    contract_errors.append(f"{season}: game-finality Weeks[{index}] is not an object")
                    continue
                week = row.get("Week")
                week_final = row.get("WeekFinal")
                if not isinstance(week, int) or isinstance(week, bool) or not isinstance(week_final, bool):
                    contract_errors.append(
                        f"{season}: game-finality Weeks[{index}] is missing integer Week / boolean WeekFinal"
                    )
                    continue
                if week_final:
                    expected_weeks.add(week)
            if not expected_weeks and not contract_errors:
                contract_errors.append(f"{season}: game-finality evidence contains no finalized weeks")

    season_dir = repo_root / "source-data/nfl/special-teams-fumble-events" / str(season)
    missing_weeks: list[int] = []
    unresolved_count = 0
    unresolved_gsis: set[str] = set()

    for week in sorted(expected_weeks):
        partition = season_dir / f"{week:02d}.json"
        if not partition.exists():
            missing_weeks.append(week)
            continue

        payload = read_json(partition)
        if not isinstance(payload, dict):
            contract_errors.append(f"{season} week {week}: canonical partition is not an object")
            continue
        if payload.get("Season") != season:
            contract_errors.append(f"{season} week {week}: canonical Season mismatch")
        if payload.get("Week") != week:
            contract_errors.append(f"{season} week {week}: canonical Week mismatch")
        if payload.get("SourceDataset") != SPECIAL_TEAMS_FUMBLE_EVENTS_DATASET_ID:
            contract_errors.append(f"{season} week {week}: canonical SourceDataset mismatch")
        if payload.get("Finalized") is not True:
            contract_errors.append(f"{season} week {week}: canonical partition is not finalized")

        records = payload.get("Records")
        if not isinstance(records, list):
            contract_errors.append(f"{season} week {week}: canonical Records is not a list")
            continue
        for index, record in enumerate(records):
            if not isinstance(record, dict):
                contract_errors.append(f"{season} week {week}: Records[{index}] is not an object")
                continue
            canonical_player_id = record.get("CanonicalPlayerID")
            if isinstance(canonical_player_id, str) and canonical_player_id.strip():
                continue
            unresolved_count += 1
            source_ids = record.get("SourceIDs")
            if isinstance(source_ids, dict):
                gsis = source_ids.get("GSIS")
                if gsis is not None and str(gsis).strip():
                    unresolved_gsis.add(str(gsis).strip())

    return {
        "ExpectedFinalizedWeeks": sorted(expected_weeks),
        "MissingFinalizedWeeks": missing_weeks,
        "UnresolvedCanonicalPlayerRecordCount": unresolved_count,
        "UnresolvedGSISIDs": sorted(unresolved_gsis),
        "ContractErrors": contract_errors,
        "Ready": bool(expected_weeks)
        and not missing_weeks
        and unresolved_count == 0
        and not contract_errors,
    }


def build_nfl_readiness(repo_root: Path) -> dict[str, Any]:
    season_now = current_season(repo_root)
    datasets: dict[str, Any] = {}
    hard_failures: list[str] = []
    known_unavailable_partitions: list[dict[str, Any]] = []
    for dataset_id, policy in HISTORICAL_BANDS.items():
        dataset = registry_dataset(repo_root, dataset_id)
        rows = []
        missing_historical = []
        known_unavailable_historical = []
        missing_finalized_week_partitions: list[dict[str, Any]] = []
        historical_event_unresolved_count = 0
        historical_event_unresolved_gsis: set[str] = set()
        historical_event_contract_errors: list[str] = []

        for season in range(int(policy["start"]), season_now + 1):
            raw_rel = "source-data/" + render_path(dataset["rawPath"], season)
            metadata_rel = "source-data/" + render_path(dataset["metadataPath"], season)
            raw_exists = (repo_root / raw_rel).exists()
            metadata = read_json(repo_root / metadata_rel, {}) or {}
            availability = metadata.get("availabilityStatus") or metadata.get("AvailabilityStatus")
            partitions = canonical_partition_count(repo_root, str(policy["canonical"]), season)
            historical = season < season_now
            unavailable_reason = known_unavailable_reason(dataset_id, season) if historical else None
            required_for_readiness = historical and unavailable_reason is None
            special_coverage = None

            if (
                dataset_id == SPECIAL_TEAMS_FUMBLE_EVENTS_DATASET_ID
                and required_for_readiness
                and raw_exists
            ):
                special_coverage = build_special_teams_fumble_historical_coverage(repo_root, season)
                ready = bool(special_coverage["Ready"])
                if special_coverage["MissingFinalizedWeeks"]:
                    missing_finalized_week_partitions.append(
                        {
                            "Season": season,
                            "Weeks": special_coverage["MissingFinalizedWeeks"],
                        }
                    )
                historical_event_unresolved_count += int(
                    special_coverage["UnresolvedCanonicalPlayerRecordCount"]
                )
                historical_event_unresolved_gsis.update(special_coverage["UnresolvedGSISIDs"])
                historical_event_contract_errors.extend(special_coverage["ContractErrors"])
            else:
                ready = raw_exists and partitions > 0

            if required_for_readiness and not ready:
                missing_historical.append(season)
            if unavailable_reason:
                known_unavailable_historical.append({"Season": season, "Reason": unavailable_reason})
                known_unavailable_partitions.append(
                    {"DatasetID": dataset_id, "Season": season, "Reason": unavailable_reason}
                )

            row = {
                "Season": season,
                "Historical": historical,
                "RawPresent": raw_exists,
                "CanonicalPartitionCount": partitions,
                "AvailabilityStatus": availability,
                "Ready": ready,
                "RequiredForReadiness": required_for_readiness,
                "KnownUnavailable": unavailable_reason is not None,
                "KnownUnavailableReason": unavailable_reason,
            }
            if special_coverage is not None:
                row["SpecialTeamsFumbleEventCoverage"] = special_coverage
            rows.append(row)

        if missing_historical:
            hard_failures.append(f"{dataset_id}: missing historical seasons {missing_historical}")

        nominal_historical_count = max(0, season_now - int(policy["start"]))
        dataset_summary = {
            "HistoryStart": policy["start"],
            "ExpectedThroughSeason": season_now,
            "HistoricalSeasonCountNominal": nominal_historical_count,
            "HistoricalSeasonCountExpected": nominal_historical_count - len(known_unavailable_historical),
            "KnownUnavailableHistoricalSeasons": known_unavailable_historical,
            "MissingHistoricalSeasons": missing_historical,
            "CurrentSeasonMayBeUnavailable": dataset.get("availabilityPolicy") == "current-season-may-be-unavailable",
            "Seasons": rows,
            "RawLastChange": git_last_change(repo_root, str(Path("source-data") / dataset["rawPath"].replace("{season}", "*"))),
            "CanonicalLastChange": git_last_change(repo_root, f"source-data/nfl/{policy['canonical']}"),
        }

        if dataset_id == SPECIAL_TEAMS_FUMBLE_EVENTS_DATASET_ID:
            dataset_summary.update(
                {
                    "HistoricalFinalizedWeekGaps": missing_finalized_week_partitions,
                    "HistoricalUnresolvedCanonicalPlayerRecordCount": historical_event_unresolved_count,
                    "HistoricalUnresolvedGSISIDs": sorted(historical_event_unresolved_gsis),
                    "HistoricalPartitionContractErrors": historical_event_contract_errors,
                }
            )
            if missing_finalized_week_partitions:
                rendered = ", ".join(
                    f"{entry['Season']}:{entry['Weeks']}"
                    for entry in missing_finalized_week_partitions
                )
                hard_failures.append(
                    f"{dataset_id}: missing finalized canonical week partitions {rendered}"
                )
            if historical_event_unresolved_count:
                hard_failures.append(
                    f"{dataset_id}: {historical_event_unresolved_count} historical canonical event records "
                    f"lack CanonicalPlayerID across {len(historical_event_unresolved_gsis)} GSIS player IDs"
                )
            if historical_event_contract_errors:
                hard_failures.append(
                    f"{dataset_id}: historical finality/canonical partition contract errors "
                    f"{historical_event_contract_errors}"
                )

        datasets[dataset_id] = dataset_summary

    player_identity_coverage = build_player_stats_identity_coverage(repo_root, current_season=season_now)
    if player_identity_coverage["HistoricalUnresolvedRecordCount"]:
        hard_failures.append(
            "nflverse.player-stats: "
            f"{player_identity_coverage['HistoricalUnresolvedRecordCount']} historical canonical stat records "
            "lack CanonicalPlayerID across "
            f"{player_identity_coverage['HistoricalUnresolvedUniqueGSISCount']} GSIS player IDs"
        )
    if player_identity_coverage["HistoricalMissingGSISRecordCount"]:
        hard_failures.append(
            "nflverse.player-stats: "
            f"{player_identity_coverage['HistoricalMissingGSISRecordCount']} historical canonical stat records "
            "lack GSIS source identity"
        )
    if player_identity_coverage["HistoricalRawUnclassifiedMissingPlayerIDRecordCount"]:
        hard_failures.append(
            "nflverse.player-stats: "
            f"{player_identity_coverage['HistoricalRawUnclassifiedMissingPlayerIDRecordCount']} historical raw stat rows "
            "lack player_id and are not recognized team aggregates"
        )
    if player_identity_coverage["InvalidNonPlayerCanonicalAssignmentCount"]:
        hard_failures.append(
            "nflverse.player-stats: "
            f"{player_identity_coverage['InvalidNonPlayerCanonicalAssignmentCount']} known non-player aggregate rows "
            "incorrectly carry CanonicalPlayerID"
        )
    if player_identity_coverage["GSISCanonicalConflictCount"]:
        hard_failures.append(
            "nflverse.player-stats: "
            f"{player_identity_coverage['GSISCanonicalConflictCount']} GSIS IDs map to multiple CanonicalPlayerIDs"
        )

    schedule_files = sorted((repo_root / "source-data/nfl/schedules").glob("*.json"))
    finality_files = sorted((repo_root / "source-data/nfl/game-finality").glob("*.json"))
    return {
        "schemaVersion": 1,
        "CurrentSourceSeason": season_now,
        "HistoricalBackfillPolicy": {
            "GeneralStatsBasisStart": 1999,
            "WeeklyRosterStart": 2002,
            "SnapCountStart": 2012,
            "SpecialTeamsFumbleEventStart": 1999,
            "KnownUnavailableHistoricalPartitions": known_unavailable_partitions,
            "MissingIsZero": False,
            "Rule": "Historical seasons in the supported source band must be persisted unless an exact partition is explicitly documented as known upstream-unavailable; current not-yet-available evidence is allowed only by dataset availability policy. Unavailable facts are never zero.",
        },
        "HistoricalPlayerIdentityCoverage": player_identity_coverage,
        "HistoricalPlayerIdentityRule": "Canonical NFL player stats resolve nflverse GSIS player_id directly to stable CanonicalPlayerID. Historical scoring does not depend on Sleeper IDs or archived app Players.json snapshots. Historical unresolved person identity, unclassified raw rows without player_id, invalid person assignment to known team aggregates, and cross-canonical GSIS conflicts fail readiness closed. Explicit team aggregate rows remain non-player facts. Current-season unresolved rows remain diagnostic while the season is in progress.",
        "FixedHistoricalCoverage": {
            "Schedules": {
                "SeasonCount": len(schedule_files),
                "EarliestSeason": int(schedule_files[0].stem) if schedule_files else None,
                "LatestSeason": int(schedule_files[-1].stem) if schedule_files else None,
            },
            "GameFinality": {
                "SeasonCount": len(finality_files),
                "EarliestSeason": int(finality_files[0].stem) if finality_files else None,
                "LatestSeason": int(finality_files[-1].stem) if finality_files else None,
            },
        },
        "Datasets": datasets,
        "ReadyForHistoricalScoring": not hard_failures,
        "HardFailures": hard_failures,
    }


def build_league_readiness(repo_root: Path) -> dict[str, Any]:
    root = repo_root / "source-data/leagues"
    leagues = []
    failures = []
    for bootstrap_path in sorted((root / "_bootstrap").glob("*.json")):
        bootstrap = read_json(bootstrap_path, {}) or {}
        canonical_id = bootstrap.get("CanonicalLeagueID")
        manifest_path = root / str(canonical_id) / "manifest.json"
        manifest = read_json(manifest_path, {}) or {}
        seasons = []
        if not manifest:
            failures.append(f"{canonical_id}: manifest missing")
        for entry in manifest.get("Seasons", []):
            season = int(entry["Season"])
            season_root = root / str(canonical_id) / "seasons" / str(season)
            league = read_json(season_root / "league.json", {}) or {}
            core = {
                name: (season_root / name).exists()
                for name in ("league.json", "members.json", "rosters.json", "drafts.json", "winners-bracket.json", "losers-bracket.json")
            }
            missing_core = [name for name, present in core.items() if not present]
            if missing_core:
                failures.append(f"{canonical_id}/{season}: missing {missing_core}")
            player_coverage = build_season_player_reference_coverage(season_root)
            if player_coverage["UnresolvedReferenceCount"]:
                failures.append(
                    f"{canonical_id}/{season}: "
                    f"{player_coverage['UnresolvedReferenceCount']} unresolved canonical player references "
                    f"across {player_coverage['UnresolvedUniqueSleeperPlayerIDCount']} Sleeper player IDs"
                )
            seasons.append(
                {
                    "Season": season,
                    "CanonicalLeagueSeasonID": entry.get("CanonicalLeagueSeasonID"),
                    "ProviderMappings": entry.get("ProviderMappings", []),
                    "CoreFiles": core,
                    "MatchupPartitionCount": len(list((season_root / "matchups").glob("*.json"))),
                    "TransactionPartitionCount": len(list((season_root / "transactions").glob("*.json"))),
                    "WeekStructure": league.get("WeekStructure"),
                    "ScoringSettingsPresent": isinstance(league.get("ScoringSettings"), dict),
                    "PlayerReferenceCoverage": player_coverage,
                }
            )
        leagues.append(
            {
                "CanonicalLeagueID": canonical_id,
                "Provider": bootstrap.get("Provider"),
                "CurrentProviderLeagueID": bootstrap.get("CurrentProviderLeagueID"),
                "ManifestPresent": bool(manifest),
                "ManifestLastChange": git_last_change(repo_root, str(manifest_path.relative_to(repo_root))) if manifest else None,
                "Seasons": seasons,
            }
        )
    return {
        "schemaVersion": 1,
        "LeagueCount": len(leagues),
        "Leagues": leagues,
        "Ready": not failures,
        "HardFailures": failures,
        "WeekStructureRule": "Sleeper playoff configuration is mutable provider evidence. Expected/projected boundaries and observed historical matchup/bracket reality remain separate; trailing future assignments do not by themselves extend the fantasy season.",
        "PlayerReferenceRule": "Every Sleeper player reference remains evidence-preserving through its ProviderPlayerID, but League Source readiness is false while any such reference lacks a season-valid CanonicalPlayerID. Ambiguous mappings continue to fail closed during materialization.",
    }


def build_storage_audit(repo_root: Path) -> dict[str, Any]:
    source_root = repo_root / "source-data"
    files = []
    total = 0
    for path in source_root.rglob("*"):
        if not path.is_file():
            continue
        size = path.stat().st_size
        total += size
        if size >= LARGE_FILE_BYTES:
            files.append(
                {
                    "Path": str(path.relative_to(repo_root)),
                    "Bytes": size,
                    "LastChange": git_last_change(repo_root, str(path.relative_to(repo_root))),
                }
            )
    files.sort(key=lambda item: (-item["Bytes"], item["Path"]))
    return {
        "schemaVersion": 1,
        "TotalSourceDataBytes": total,
        "LargeFileThresholdBytes": LARGE_FILE_BYTES,
        "LargeFiles": files,
        "LargeFileCount": len(files),
        "Rule": "Git-tracked source data remains accepted for Phase 1, but large-file size is persisted so repository growth is observable before storage architecture is reconsidered.",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--write", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.repo_root.resolve()
    nfl = build_nfl_readiness(root)
    league = build_league_readiness(root)
    storage = build_storage_audit(root)
    payload = {"NFL": nfl, "League": league, "Storage": storage}
    if args.write:
        changed = {
            "nfl": write_json_if_changed(root / "source-data/audits/nfl-source-data-readiness.json", nfl),
            "league": write_json_if_changed(root / "source-data/audits/league-source-data-audit.json", league),
            "storage": write_json_if_changed(root / "source-data/audits/source-data-storage-audit.json", storage),
        }
        payload["Changed"] = changed
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
