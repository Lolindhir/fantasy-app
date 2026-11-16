#!/usr/bin/env python3
"""Read-only source-field and coverage audit for the NFL Games PBP metric catalog.

Consumes a locally available original nflverse seasonal CSV.GZ; no downloads,
writes, scheduled triggers, per-play publication or source-registry changes.
A complete GZIP read is NOT proof of upstream game/play completeness.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from decimal import Decimal, InvalidOperation
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys

import yaml

from derived_data_lib.nfl_franchise_aliases import franchise_equal as _franchise_equal


NULL_VALUES = frozenset(("", "NA", "N/A", "NaN", "nan", "NULL", "null"))
CORE_COLUMNS = frozenset((
    "game_id", "play_id", "season", "week", "season_type",
    "home_team", "away_team", "posteam", "defteam", "play_type",
))
GSIS_COLUMNS = ("rusher_player_id", "receiver_player_id", "passer_player_id")
BINARY_FIELDS = (
    "pass_attempt", "sack", "qb_spike", "qb_dropback", "qb_scramble",
    "rush_attempt", "two_point_attempt", "complete_pass", "success",
    "third_down_converted",
)
COHORTS = ("AllRows", "PassPlayType", "RunPlayType", "QBDropback", "ThirdDown")
GSIS_PATTERN = re.compile(r"^00-\d{7}$")
SHA_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _digest(path: Path) -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def _number(value: str | None, *, field: str) -> int:
    try:
        parsed = Decimal(str(value or "").strip())
    except InvalidOperation as exc:
        raise ValueError(f"Invalid {field} in original PBP: {value!r}") from exc
    if not parsed.is_finite() or parsed != parsed.to_integral_value():
        raise ValueError(f"Invalid {field} in original PBP: {value!r}")
    return int(parsed)


def _nonnull(value: str | None) -> bool:
    return value is not None and value.strip() not in NULL_VALUES


def _is_one(value: str | None) -> bool:
    if not _nonnull(value):
        return False
    try:
        return Decimal(value.strip()) == 1
    except InvalidOperation:
        return False


def _catalog(path: Path) -> tuple[list[dict], set[str]]:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or document.get("catalogVersion") != 1:
        raise ValueError("Expected nfl-games PBP metric catalogVersion 1")
    families = document.get("metricFamilies")
    if not isinstance(families, list) or not families:
        raise ValueError("PBP catalog has no metric families")
    found: list[dict] = []
    ids: set[str] = set()
    fields = set(CORE_COLUMNS) | set(GSIS_COLUMNS) | set(BINARY_FIELDS)
    for family in families:
        if not isinstance(family, dict) or not isinstance(family.get("candidates"), list):
            raise ValueError("Invalid PBP metric family")
        for item in family["candidates"]:
            if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                raise ValueError("Invalid PBP metric candidate")
            metric_id = item["id"]
            required = item.get("sourceFields")
            if metric_id in ids or not isinstance(required, list) or not required or any(
                not isinstance(key, str) or not key for key in required
            ):
                raise ValueError(f"Duplicate or malformed PBP metric: {metric_id}")
            ids.add(metric_id)
            fields.update(required)
            found.append({
                "MetricID": metric_id,
                "Family": family.get("family"),
                "Priority": family.get("priority"),
                "Fields": sorted(set(required)),
                "PositionJoinRequired": bool(item.get("requiredJoin") or family.get("sharedJoin")),
            })
    return found, fields


def _metadata(path: Path | None, season: int) -> dict | None:
    if path is None or not path.is_file():
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    partition = value.get("partition", {})
    if value.get("provider") != "nflverse" or partition.get("season") != season:
        raise ValueError("Upstream projection metadata provider/season mismatch")
    return value



# Era-restricted franchise context matching is shared with NFL GameDetail.

def _game_index(path: Path | None, season: int) -> dict[str, dict] | None:
    if path is None:
        return None
    source = json.loads(path.read_text(encoding="utf-8"))
    if (source.get("SchemaVersion") != 1 or source.get("Season") != season
            or not isinstance(source.get("Games"), list)):
        raise ValueError("Incompatible canonical nfl-games season index")
    indexed: dict[str, dict] = {}
    for game in source["Games"]:
        if (not isinstance(game, dict)
                or not isinstance(game.get("GameID"), str)
                or type(game.get("Week")) is not int
                or game.get("GameType") not in ("REG", "WC", "DIV", "CON", "SB")
                or not isinstance(game.get("AwayTeam"), str)
                or not isinstance(game.get("HomeTeam"), str)
                or type(game.get("Final")) is not bool):
            raise ValueError("Invalid canonical nfl-games index game row")
        if game["GameID"] in indexed:
            raise ValueError("Duplicate canonical nfl-games GameID")
        indexed[game["GameID"]] = game
    return indexed



def reconcile_original_game_row(
    row: dict, indexed: dict[str, dict], season: int,
) -> tuple[str, bool | None]:
    """Classify source→canonical game context; never assert completeness.

    Also applicable to *actual persisted PBP subset projection* rows; any
    such evidence remains limited to the projected rows, not full upstream.
    """
    game = indexed.get(row.get("game_id"))
    if game is None:
        return "unknown-game-id", None
    try:
        week = _number(row.get("week"), field="week")
    except ValueError:
        return "mismatched-context", game["Final"]
    source_type = row.get("season_type")
    expected_type = (
        source_type == "REG" if game["GameType"] == "REG" else
        source_type == "POST"
    )
    if not expected_type or week != game["Week"]:
        return "mismatched-context", game["Final"]
    away = row.get("away_team")
    home = row.get("home_team")
    if away == game["AwayTeam"] and home == game["HomeTeam"]:
        return "exact-context", game["Final"]
    if (isinstance(away, str) and isinstance(home, str)
            and _franchise_equal(away, game["AwayTeam"], season)
            and _franchise_equal(home, game["HomeTeam"], season)):
        return "historical-franchise-alias", game["Final"]
    return "mismatched-context", game["Final"]


def audit(
    *,
    path: Path,
    season: int,
    catalog_path: Path,
    metadata_path: Path | None = None,
    expected_sha256: str | None = None,
    game_index_path: Path | None = None,
) -> dict:
    """Scan ALL original compressed source rows and report catalog field evidence."""
    if not path.is_file():
        raise ValueError(f"Original PBP asset unavailable: {path}")
    if type(season) is not int or not 1999 <= season <= 2100:
        raise ValueError("Invalid requested season")
    metrics, monitored = _catalog(catalog_path)
    metadata = _metadata(metadata_path, season)
    indexed = _game_index(game_index_path, season)
    context_counts = Counter()
    context_examples: list[dict] = []
    observed_digest = _digest(path)
    if expected_sha256 is not None:
        pin = expected_sha256.lower()
        if not SHA_PATTERN.fullmatch(pin) or pin != observed_digest:
            raise ValueError("Original PBP asset does not match expected SHA256")

    cohorts = Counter({key: 0 for key in COHORTS})
    nonnull = {field: Counter({key: 0 for key in COHORTS}) for field in monitored}
    binary_invalid = Counter()
    dictionary_checks = Counter()
    invalid_numeric_epa = 0
    ids = {field: set() for field in GSIS_COLUMNS}
    non_gsis = Counter()
    game_counts = Counter()
    game_contexts: dict[str, tuple] = {}
    play_keys: set[tuple[str, int]] = set()
    rows = 0

    with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        header = reader.fieldnames or []
        if not header or any(not field for field in header) or len(header) != len(set(header)):
            raise ValueError("Invalid or duplicate original PBP CSV headers")
        missing_core = sorted(CORE_COLUMNS - set(header))
        if missing_core:
            raise ValueError("Missing original PBP identity columns: " + ", ".join(missing_core))
        present = sorted(monitored & set(header))
        absent = sorted(monitored - set(header))
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError("Malformed original PBP CSV row width")
            rows += 1
            game_id = (row["game_id"] or "").strip()
            if not game_id or _number(row["season"], field="season") != season:
                raise ValueError(f"Original PBP missing GameID or wrong season at row {rows}")
            play_id = _number(row["play_id"], field="play_id")
            week = _number(row["week"], field="week")
            if play_id < 1 or not 1 <= week <= 25:
                raise ValueError(f"Original PBP invalid play/week at row {rows}")
            context = (
                week, row["season_type"], row["home_team"], row["away_team"],
            )
            if row["season_type"] not in ("REG", "POST") or any(
                not value for value in context[1:]
            ):
                raise ValueError(f"Original PBP invalid game context at row {rows}")
            if game_id in game_contexts and game_contexts[game_id] != context:
                raise ValueError(f"Original PBP conflicting game context: {game_id}")
            game_contexts[game_id] = context
            key = (game_id, play_id)
            if key in play_keys:
                raise ValueError(f"Duplicate original PBP GameID/PlayID: {game_id}/{play_id}")
            play_keys.add(key)
            game_counts[game_id] += 1
            if indexed is not None:
                status, final = reconcile_original_game_row(row, indexed, season)
                context_counts[status] += 1
                if status in ("exact-context", "historical-franchise-alias") and not final:
                    context_counts["matched-non-final-game"] += 1
                if status != "exact-context" and len(context_examples) < 20:
                    context_examples.append({
                        "GameID": game_id,
                        "PlayID": play_id,
                        "Status": status,
                        "SourceWeek": week,
                        "SourceGameType": row["season_type"],
                        "SourceAway": row["away_team"],
                        "SourceHome": row["home_team"],
                    })

            active = ["AllRows"]
            if row.get("play_type") == "pass":
                active.append("PassPlayType")
            elif row.get("play_type") == "run":
                active.append("RunPlayType")
            if _is_one(row.get("qb_dropback")):
                active.append("QBDropback")
            if row.get("down") is not None and _nonnull(row.get("down")) and _number(
                row["down"], field="down"
            ) == 3:
                active.append("ThirdDown")
            for cohort in active:
                cohorts[cohort] += 1
            for field in present:
                if _nonnull(row[field]):
                    for cohort in active:
                        nonnull[field][cohort] += 1
            for field in BINARY_FIELDS:
                if field in row and _nonnull(row[field]):
                    try:
                        binary = Decimal(row[field].strip())
                        valid = binary.is_finite() and binary in (0, 1)
                    except InvalidOperation:
                        valid = False
                    if not valid:
                        binary_invalid[field] += 1
            if _is_one(row.get("pass_attempt")) and _is_one(row.get("sack")):
                dictionary_checks["PassAttemptAndSackRows"] += 1
            if _is_one(row.get("qb_dropback")) and _is_one(row.get("qb_scramble")):
                dictionary_checks["QBDropbackAndScrambleRows"] += 1
            if _nonnull(row.get("success")) and _nonnull(row.get("epa")):
                try:
                    value = Decimal(row["epa"].strip())
                    success = Decimal(row["success"].strip())
                    if value.is_finite() and success in (0, 1):
                        dictionary_checks["SuccessEPAComparableRows"] += 1
                        if (value > 0) != (success == 1):
                            dictionary_checks["SuccessPositiveEPAMismatches"] += 1
                    elif not value.is_finite():
                        invalid_numeric_epa += 1
                except InvalidOperation:
                    invalid_numeric_epa += 1
            for field in GSIS_COLUMNS:
                if field in row and _nonnull(row[field]):
                    ident = row[field].strip()
                    ids[field].add(ident)
                    if not GSIS_PATTERN.fullmatch(ident):
                        non_gsis[field] += 1

    if rows == 0:
        raise ValueError("Original PBP asset contains no source rows")
    if _digest(path) != observed_digest:
        raise ValueError("Original PBP asset changed while being audited")

    field_coverage = {}
    for field in sorted(monitored):
        field_coverage[field] = {
            "HeaderPresent": field in header,
            "Cohorts": {
                name: {
                    "Rows": cohorts[name],
                    "NonNull": nonnull[field][name],
                    "Missing": cohorts[name] - nonnull[field][name],
                }
                for name in COHORTS
            },
        }
    metric_coverage = []
    for item in metrics:
        missing = [field for field in item["Fields"] if field not in header]
        all_empty = [
            field for field in item["Fields"]
            if field in header and nonnull[field]["AllRows"] == 0
        ]
        metric_coverage.append({
            "MetricID": item["MetricID"],
            "Family": item["Family"],
            "Priority": item["Priority"],
            "MissingSourceColumns": missing,
            "ColumnsWithNoNonNullEvidence": all_empty,
            "PositionJoinRequired": item["PositionJoinRequired"],
            "Status": (
                "source-fields-missing" if missing else
                "source-fields-present-but-empty" if all_empty else
                "fields-observed-in-gzip-unverified-eligibility-and-completeness"
            ),
            "ReadyToPublish": False,
        })

    archived = None
    if metadata is not None:
        recorded_hash = metadata.get("upstreamContentHashSha256")
        recorded_bytes = metadata.get("upstreamByteSize")
        recorded_rows = (metadata.get("projectionStats") or {}).get("sourceRowCount")
        archived = {
            "MetadataPath": str(metadata_path),
            "ArchivedSHA256Matches": observed_digest == recorded_hash if recorded_hash else None,
            "ArchivedByteCountMatches": path.stat().st_size == recorded_bytes if recorded_bytes is not None else None,
            "ArchivedRowCountMatches": rows == recorded_rows if recorded_rows is not None else None,
            "RecordedRows": recorded_rows,
            "SnapshotDriftIsNotProofOfCorruptData": True,
        }
    return {
        "AuditSchemaVersion": 1,
        "Status": "observed-source-asset-not-certified-full-pbp",
        "Season": season,
        "SourceAssetSHA256": observed_digest,
        "SourceAssetCompressedBytes": path.stat().st_size,
        "GzipStreamReadToEOF": True,
        "RawSeasonRowCount": rows,
        "DistinctGameIDs": len(game_counts),
        "DistinctGamePlayKeys": len(play_keys),
        "CanonicalGameContextReconciliation": (
            {
                "IndexProvided": True,
                "CanonicalGameCount": len(indexed),
                "SourceRowsCompared": rows,
                "ExactContextRows": context_counts["exact-context"],
                "HistoricalAliasContextRows": context_counts["historical-franchise-alias"],
                "UnknownGameIDRows": context_counts["unknown-game-id"],
                "MismatchedContextRows": context_counts["mismatched-context"],
                "MatchedNonFinalGameRows": context_counts["matched-non-final-game"],
                "AllObservedSourceRowsJoinCanonicalGames": (
                    context_counts["unknown-game-id"] == 0
                    and context_counts["mismatched-context"] == 0
                ),
                "Examples": context_examples,
                "OriginalSeasonPlayCoverageVerified": False,
            } if indexed is not None else {
                "IndexProvided": False,
                "OriginalSeasonPlayCoverageVerified": False,
            }
        ),
        "GameRowCounts": [
            {"GameID": game_id, "RowCount": game_counts[game_id], "Week": game_contexts[game_id][0],
             "SeasonType": game_contexts[game_id][1]}
            for game_id in sorted(game_counts)
        ],
        "CohortDefinitions": {
            "AllRows": "all original PBP rows",
            "PassPlayType": "play_type=pass (nflverse includes sacks)",
            "RunPlayType": "play_type=run (nflverse includes scrambles)",
            "QBDropback": "qb_dropback=1 (if supplied)",
            "ThirdDown": "down=3 (if supplied)",
        },
        "CohortRowCounts": dict(cohorts),
        "CsvColumnCount": len(header),
        "MonitoredFieldsPresent": present,
        "MonitoredFieldsAbsent": absent,
        "FieldCoverage": field_coverage,
        "BinaryFieldInvalidCounts": dict(sorted(binary_invalid.items())),
        "DictionarySemanticCrosschecks": {
            "PassAttemptAndSackRows": dictionary_checks["PassAttemptAndSackRows"],
            "QBDropbackAndScrambleRows": dictionary_checks["QBDropbackAndScrambleRows"],
            "SuccessEPAComparableRows": dictionary_checks["SuccessEPAComparableRows"],
            "SuccessPositiveEPAMismatches": dictionary_checks["SuccessPositiveEPAMismatches"],
            "InvalidNumericEPARowsInComparison": invalid_numeric_epa,
            "ObservedCrosschecksAreNotEvidenceOfProviderWideCompleteness": True,
        },
        "ProviderPlayerIDCoverage": {
            field: {
                "HeaderPresent": field in header,
                "DistinctObservedIDs": len(ids[field]),
                "NonGSISFormatOccurrences": non_gsis[field],
                "HistoricalCanonicalPlayerIDJoinVerified": False,
            } for field in GSIS_COLUMNS
        },
        "MetricCatalogVersion": 1,
        "MetricCandidateCount": len(metrics),
        "MetricFieldCoverage": metric_coverage,
        "ArchivedProjectionComparison": archived,
        "UpstreamFullGameCompletenessVerified": False,
        "PlayerPositionHistoricalJoinVerified": False,
        "NoProductionWritersOrSourceRetentionActivated": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--pbp-csv-gz", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, default=None)
    parser.add_argument("--metadata-json", type=Path, default=None)
    parser.add_argument(
        "--game-index-json", type=Path, default=None,
        help="Optional canonical data-derived/nfl-games/<season>.json schedule/finality join",
    )
    parser.add_argument("--expected-sha256", default=None)
    args = parser.parse_args()
    repo = args.repo_root.resolve()
    catalog = args.catalog or repo / ".ai-context/manual/nfl-games-pbp-metrics.yaml"
    archived = args.metadata_json or (
        repo / "data-source/providers/nflverse/special-teams-fumble-events"
        / f"metadata-{args.season}.json"
    )
    try:
        result = audit(
            path=args.pbp_csv_gz,
            season=args.season,
            catalog_path=catalog,
            metadata_path=archived,
            expected_sha256=args.expected_sha256,
            game_index_path=args.game_index_json,
        )
    except (OSError, ValueError, TypeError, KeyError, EOFError, csv.Error, yaml.YAMLError) as error:
        print(f"nfl_pbp_metric_field_audit failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
