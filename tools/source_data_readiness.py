#!/usr/bin/env python3
"""Build deterministic readiness audits for canonical NFL and League source data."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

HISTORICAL_BANDS = {
    "nflverse.rosters": {"start": 1999, "canonical": "rosters"},
    "nflverse.weekly-rosters": {"start": 2002, "canonical": "weekly-rosters"},
    "nflverse.player-stats": {"start": 1999, "canonical": "player-stats"},
    "nflverse.snap-counts": {"start": 2012, "canonical": "snap-counts"},
}
LARGE_FILE_BYTES = 5 * 1024 * 1024


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


def build_nfl_readiness(repo_root: Path) -> dict[str, Any]:
    season_now = current_season(repo_root)
    datasets: dict[str, Any] = {}
    hard_failures: list[str] = []
    for dataset_id, policy in HISTORICAL_BANDS.items():
        dataset = registry_dataset(repo_root, dataset_id)
        rows = []
        missing_historical = []
        for season in range(policy["start"], season_now + 1):
            raw_rel = "source-data/" + render_path(dataset["rawPath"], season)
            metadata_rel = "source-data/" + render_path(dataset["metadataPath"], season)
            raw_exists = (repo_root / raw_rel).exists()
            metadata = read_json(repo_root / metadata_rel, {}) or {}
            availability = metadata.get("availabilityStatus") or metadata.get("AvailabilityStatus")
            partitions = canonical_partition_count(repo_root, policy["canonical"], season)
            historical = season < season_now
            ready = raw_exists and partitions > 0
            if historical and not ready:
                missing_historical.append(season)
            rows.append(
                {
                    "Season": season,
                    "Historical": historical,
                    "RawPresent": raw_exists,
                    "CanonicalPartitionCount": partitions,
                    "AvailabilityStatus": availability,
                    "Ready": ready,
                }
            )
        if missing_historical:
            hard_failures.append(f"{dataset_id}: missing historical seasons {missing_historical}")
        datasets[dataset_id] = {
            "HistoryStart": policy["start"],
            "ExpectedThroughSeason": season_now,
            "HistoricalSeasonCountExpected": max(0, season_now - policy["start"]),
            "MissingHistoricalSeasons": missing_historical,
            "CurrentSeasonMayBeUnavailable": dataset.get("availabilityPolicy") == "current-season-may-be-unavailable",
            "Seasons": rows,
            "RawLastChange": git_last_change(repo_root, str(Path("source-data") / dataset["rawPath"].replace("{season}", "*"))),
            "CanonicalLastChange": git_last_change(repo_root, f"source-data/nfl/{policy['canonical']}"),
        }

    schedule_files = sorted((repo_root / "source-data/nfl/schedules").glob("*.json"))
    finality_files = sorted((repo_root / "source-data/nfl/game-finality").glob("*.json"))
    return {
        "schemaVersion": 1,
        "CurrentSourceSeason": season_now,
        "HistoricalBackfillPolicy": {
            "GeneralStatsBasisStart": 1999,
            "WeeklyRosterStart": 2002,
            "SnapCountStart": 2012,
            "MissingIsZero": False,
            "Rule": "Historical seasons in the supported source band must be persisted; current not-yet-available evidence is allowed only by dataset availability policy.",
        },
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
