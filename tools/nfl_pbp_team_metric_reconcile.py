#!/usr/bin/env python3
"""Read-only full-season PBP team-metric vs canonical PlayerStats reconciliation.

Issue #1077: validate the 17 *team-only* experimental NFL Games candidates.
No provider-player mapping, historical player identity, new download, persistence,
publisher, workflow or source mutation. Requires operator-provided ORIGINAL
nflverse play_by_play_<season>.csv.gz bytes and canonical repo source partitions.

A complete gzip read and pinned SHA256 prove only that the specified asset was
read; neither proves that upstream contains every play in every NFL game.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any

from data_roots import DATA_DERIVED_ROOT, DATA_SOURCE_ROOT
from derived_data_lib.nfl_game_detail import build_nfl_game_detail
from nfl_pbp_metric_field_audit import audit as audit_source


BASE_FIELDS = ("attempts", "carries", "passing_yards", "rushing_yards")
# These comparisons are *diagnostics*, not asserted equal: provider PBP flags
# and official player-stat definitions diverge for spikes, kneels, penalties etc.
COMPARISONS = (
    ("pass_attempts_faced", "attempts"),
    ("rush_attempts_faced", "carries"),
)
NULLS = {"", "NA", "N/A", "NaN", "nan", "NULL", "null"}


def _intstat(value: Any, *, field: str) -> int:
    if value is None:
        return 0
    if isinstance(value, bool):
        raise ValueError(f"Invalid PlayerStats {field}: bool")
    try:
        result = float(value)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Invalid PlayerStats {field}: {value!r}") from exc
    if not math.isfinite(result) or result != int(result):
        raise ValueError(f"Invalid PlayerStats {field}: {value!r}")
    return int(result)


def _index(repo: Path, season: int) -> dict[str, Any]:
    path = repo / DATA_DERIVED_ROOT / "nfl-games" / f"{season}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("SchemaVersion") != 1 or data.get("Season") != season:
        raise ValueError("Incompatible canonical NFL Games index")
    games = data.get("Games")
    if not isinstance(games, list) or not games:
        raise ValueError("Canonical index has no games")
    ids = [g.get("GameID") for g in games]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate canonical GameID")
    return data


def _stats_baseline(repo: Path, index: dict[str, Any]) -> tuple[dict, dict]:
    season = index["Season"]
    indexed = {g["GameID"]: g for g in index["Games"]}
    weeks = sorted({g["Week"] for g in index["Games"]})
    baseline = defaultdict(lambda: {key: 0 for key in BASE_FIELDS})
    source_rows, rows_without_game = 0, 0
    partition_digests = {}
    for week in weeks:
        path = repo / DATA_SOURCE_ROOT / "nfl/player-stats" / str(season) / f"{week:02d}.json"
        if not path.is_file():
            raise ValueError(f"Missing canonical PlayerStats partition {season}/{week:02d}")
        blob = path.read_bytes()
        partition_digests[f"{week:02d}"] = hashlib.sha256(blob).hexdigest()
        payload = json.loads(blob)
        if (payload.get("SchemaVersion") != 2 or payload.get("Season") != season
                or payload.get("Week") != week
                or payload.get("SourceDataset") != "nflverse.player-stats"
                or not isinstance(payload.get("Records"), list)):
            raise ValueError(f"Incompatible canonical PlayerStats partition {season}/{week:02d}")
        for record in payload["Records"]:
            source_rows += 1
            stats = record.get("Stats") or {}
            gid = stats.get("game_id")
            if not gid:
                rows_without_game += 1
                continue
            game = indexed.get(gid)
            if game is None or game.get("Week") != week:
                raise ValueError(f"PlayerStats unknown GameID/week {gid}")
            team = record.get("Team")
            if team not in (game["AwayTeam"], game["HomeTeam"]):
                raise ValueError(f"PlayerStats invalid team {team}/{gid}")
            source_type = record.get("SeasonType")
            if (source_type != ("REG" if game["GameType"] == "REG" else "POST")):
                raise ValueError(f"PlayerStats mismatched season type {gid}")
            values = baseline[(gid, team)]
            for field in BASE_FIELDS:
                if field not in stats or stats[field] is None:
                    raise ValueError(f"PlayerStats unknown required baseline field {field}/{gid}")
                values[field] += _intstat(stats[field], field=field)
    return dict(baseline), {
        "PartitionCount": len(weeks),
        "PartitionSHA256": partition_digests,
        "SourcePlayerStatsRows": source_rows,
        "RowsWithoutGameID": rows_without_game,
        "GameTeamBaselines": len(baseline),
    }


def _pinned_sha(path: Path, pin: str) -> str:
    if len(pin) != 64 or any(c not in "0123456789abcdef" for c in pin.lower()):
        raise ValueError("Expected SHA256 must be 64 hex characters")
    with path.open("rb") as handle:
        digest = hashlib.file_digest(handle, "sha256").hexdigest()
    if digest != pin.lower():
        raise ValueError("Original PBP does not match pinned SHA256")
    return digest


def _number(row: dict[str, str], field: str) -> int | None:
    raw = str(row.get(field) or "").strip()
    if raw in NULLS:
        return None
    try:
        number = float(raw)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Invalid original PBP {field}: {raw!r}") from exc
    if not math.isfinite(number) or number != int(number):
        raise ValueError(f"Nonintegral/nonfinite original PBP {field}")
    return int(number)


def _source_yards(rows: list[dict[str, str]], offense: str) -> dict[str, Any]:
    # PBP pass yards on confirmed throws and rush yards on flagged rushes;
    # report missing rows. These are diagnostic totals, not official team stats.
    result = {
        "passing_yards": {"Observed": 0, "Missing": 0, "Value": None},
        "rushing_yards": {"Observed": 0, "Missing": 0, "Value": None},
    }
    sums = {name: 0 for name in result}
    for row in rows:
        if row.get("posteam") != offense or _number(row, "two_point_attempt") != 0:
            continue
        if _number(row, "rush_attempt") == 1:
            yards = _number(row, "rushing_yards")
            if yards is None:
                result["rushing_yards"]["Missing"] += 1
            else:
                sums["rushing_yards"] += yards
                result["rushing_yards"]["Observed"] += 1
        if _number(row, "pass_attempt") == 1:
            sack, spike = _number(row, "sack"), _number(row, "qb_spike")
            if sack is None or spike is None:
                result["passing_yards"]["Missing"] += 1
            elif sack == 0 and spike == 0:
                yards = _number(row, "passing_yards")
                if yards is None:
                    result["passing_yards"]["Missing"] += 1
                else:
                    sums["passing_yards"] += yards
                    result["passing_yards"]["Observed"] += 1
    for name, evidence in result.items():
        evidence["Value"] = sums[name] if evidence["Observed"] else None
    return result



def _unknown_comparison_eligibility(
    rows: list[dict[str, str]], offense: str,
) -> dict[str, int]:
    """Count raw source rows that could affect a team comparison but lack flags.

    A missing two-point, attempt, sack or spike flag must not let a partial
    known-play total appear identical to the canonical PlayerStats total.
    Known sacks/spikes and confirmed two-point plays cannot contribute to
    official throw totals; unrelated non-attempt plays are not made unknown.
    """
    uncertain = {name: 0 for name in BASE_FIELDS}
    for row in rows:
        if row.get("posteam") != offense:
            continue
        two_point = _number(row, "two_point_attempt")
        if two_point == 1:
            continue
        attempt = _number(row, "pass_attempt")
        rush = _number(row, "rush_attempt")
        sack = _number(row, "sack")
        spike = _number(row, "qb_spike")
        possible_throw = (
            sack != 1 and spike != 1
            and (attempt == 1 or (attempt is None and row.get("play_type") == "pass"))
        )
        possible_rush = (
            rush == 1 or (rush is None and row.get("play_type") == "run")
        )
        if possible_throw and (
            two_point is None or attempt is None
            or sack is None or spike is None
        ):
            uncertain["attempts"] += 1
            uncertain["passing_yards"] += 1
        if possible_rush and (two_point is None or rush is None):
            uncertain["carries"] += 1
            uncertain["rushing_yards"] += 1
    return uncertain


def _metric_coverage_add(storage: dict, metric_id: str, metric: dict) -> None:
    """Accumulate research-only observations with observed denominators.

    Sum rounded per-game numerators as an audit diagnostic; not a finalized
    season model or a substitute for summing raw source plays.
    """
    item = storage.setdefault(metric_id, {
        "ObservedTeamGames": 0, "MissingTeamGames": 0, "ValueSum": 0.0,
        "NumeratorFromRoundedGameSummaries": 0.0, "ObservedDenominator": 0,
        "MinGameValue": None, "MaxGameValue": None,
    })
    value = metric.get("Value")
    if value is None:
        item["MissingTeamGames"] += 1
        return
    item["ObservedTeamGames"] += 1
    item["ValueSum"] += float(value)
    item["MinGameValue"] = value if item["MinGameValue"] is None else min(item["MinGameValue"], value)
    item["MaxGameValue"] = value if item["MaxGameValue"] is None else max(item["MaxGameValue"], value)
    if metric.get("Numerator") is not None and metric.get("Denominator"):
        item["NumeratorFromRoundedGameSummaries"] += float(metric["Numerator"])
        item["ObservedDenominator"] += int(metric["Denominator"])


def _metric_coverage_finalize(storage: dict) -> dict:
    for item in storage.values():
        n, denom = item["NumeratorFromRoundedGameSummaries"], item["ObservedDenominator"]
        item["ValueSum"] = round(item["ValueSum"], 3)
        item["NumeratorFromRoundedGameSummaries"] = round(n, 3)
        item["ObservedWeightedMeanApprox"] = round(n / denom, 4) if denom else None
    return dict(sorted(storage.items()))


def _delta_distribution(deltas: list[int]) -> dict[str, Any]:
    """Diagnostic PBP-minus-PlayerStats differences for compared team-games.

    Absolute percentiles use the nearest-rank method. Missing comparisons
    are excluded, not represented as zero-valued differences.
    """
    n = len(deltas)
    result: dict[str, Any] = {
        "Compared": n,
        "Positive": sum(delta > 0 for delta in deltas),
        "Negative": sum(delta < 0 for delta in deltas),
        "Zero": sum(delta == 0 for delta in deltas),
        "Sum": None, "Mean": None, "MeanAbsolute": None,
        "Median": None, "Min": None, "Max": None,
        "AbsoluteP50": None, "AbsoluteP90": None, "AbsoluteP99": None,
        "PercentileMethod": "nearest-rank-absolute-delta",
    }
    if not n:
        return result
    ordered = sorted(deltas)
    absolute = sorted(abs(delta) for delta in deltas)

    def percentile(percent: float) -> int:
        return absolute[math.ceil(percent * n) - 1]

    middle = n // 2
    result.update({
        "Sum": sum(deltas),
        "Mean": round(math.fsum(deltas) / n, 3),
        "MeanAbsolute": round(math.fsum(absolute) / n, 3),
        "Median": ordered[middle] if n % 2
                  else (ordered[middle - 1] + ordered[middle]) / 2,
        "Min": ordered[0],
        "Max": ordered[-1],
        "AbsoluteP50": percentile(0.50),
        "AbsoluteP90": percentile(0.90),
        "AbsoluteP99": percentile(0.99),
    })
    return result


def reconcile(repo: Path, path: Path, season: int, expected_sha256: str) -> dict:
    """Replay every observed original game once; return bounded aggregate JSON.

    No writes and no inference about missing games, success/EPA zero values,
    per-player or positional coverage.
    """
    if not path.is_file():
        raise ValueError(f"Original PBP gzip unavailable: {path}")
    digest = _pinned_sha(path, expected_sha256)
    index = _index(repo, season)
    games = {g["GameID"]: g for g in index["Games"]}
    metadata = (repo / DATA_SOURCE_ROOT / "providers/nflverse/"
                "special-teams-fumble-events" / f"metadata-{season}.json")
    field_audit = audit_source(
        path=path, season=season,
        catalog_path=repo / ".ai-context/manual/nfl-games-pbp-metrics.yaml",
        metadata_path=metadata if metadata.is_file() else None,
        expected_sha256=digest,
        game_index_path=repo / DATA_DERIVED_ROOT / "nfl-games" / f"{season}.json",
    )
    joined = field_audit["CanonicalGameContextReconciliation"]
    if not joined["AllObservedSourceRowsJoinCanonicalGames"]:
        raise ValueError("Original PBP does not reconcile with canonical games")
    if field_audit["BinaryFieldInvalidCounts"]:
        raise ValueError("Original PBP contains invalid binary field values")
    baselines, stat_audit = _stats_baseline(repo, index)

    # A second *full* gzip stream preserves independent audit/stream integrity.
    # Keep rows only for known games, never copy original rows into JSON output.
    by_game = defaultdict(list)
    with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            gid = row.get("game_id")
            if gid not in games:
                raise ValueError(f"Unknown original PBP GameID: {gid}")
            by_game[gid].append(row)
    if _pinned_sha(path, expected_sha256) != digest:
        raise ValueError("Original compressed asset changed during reconciliation")

    counts = {name: {"Compared": 0, "Equal": 0, "Different": 0,
                     "MissingPBP": 0, "MissingPlayerStats": 0,
                     "UnknownSourceEligibilityRows": 0,
                     "UnknownSourceEligibilityTeamGames": 0,
                     "Examples": []} for name in BASE_FIELDS}
    deltas: dict[str, list[int]] = {name: [] for name in BASE_FIELDS}
    mismatches: dict[str, list[dict]] = {name: [] for name in BASE_FIELDS}
    missing_games = []
    game_team_rows = 0
    eligible_plays = 0
    candidate_ids = None
    metric_evidence = {}
    for gid, game in sorted(games.items()):
        rows = by_game.get(gid)
        if not rows:
            missing_games.append(gid)
            continue
        detail = build_nfl_game_detail(index, gid, pbp_rows=rows,
                                       pbp_asset_sha256=digest)
        candidates = detail["PlayByPlay"]["OriginalPlays"]["Analytics"]["CatalogTeamMetricCandidates"]
        if candidate_ids is None:
            candidate_ids = candidates["CandidateIDs"]
        if candidates["CandidateIDs"] != candidate_ids or len(candidate_ids) != 17:
            raise ValueError("Unexpected 17-candidate metric catalog drift")
        eligible_plays += candidates["EligibleScrimmagePlayCount"]
        for defense in candidates["ByDefenseTeam"]:
            defense_team = defense["Team"]
            offense = (game["AwayTeam"] if defense_team == game["HomeTeam"]
                       else game["HomeTeam"])
            truth = baselines.get((gid, offense))
            metrics = defense["Metrics"]
            for metric_id, evidence in metrics.items():
                if "Value" in evidence:
                    _metric_coverage_add(metric_evidence, metric_id, evidence)
                elif metric_id == "red_zone_epa_and_success_allowed":
                    _metric_coverage_add(metric_evidence, metric_id + ".EPA", evidence["EPA"])
                    _metric_coverage_add(metric_evidence, metric_id + ".Success", evidence["Success"])
                elif metric_id == "down_distance_efficiency_allowed":
                    for bin_id, group in evidence["Bins"].items():
                        _metric_coverage_add(metric_evidence, metric_id + "." + bin_id + ".EPA", group["EPA"])
                        _metric_coverage_add(metric_evidence, metric_id + "." + bin_id + ".Success", group["Success"])
                elif metric_id == "drive_start_context":
                    _metric_coverage_add(metric_evidence, metric_id + ".FieldPosition", evidence["FieldPosition"])
            yards = _source_yards(rows, offense)
            uncertain = _unknown_comparison_eligibility(rows, offense)
            observations = {
                "attempts": metrics["pass_attempts_faced"]["Value"]
                    if not uncertain["attempts"]
                    and not metrics["pass_attempts_faced"]["UnknownFlagCount"] else None,
                "carries": metrics["rush_attempts_faced"]["Value"]
                    if not uncertain["carries"]
                    and not metrics["rush_attempts_faced"]["UnknownFlagCount"] else None,
                "passing_yards": yards["passing_yards"]["Value"]
                    if not uncertain["passing_yards"]
                    and yards["passing_yards"]["Missing"] == 0 else None,
                "rushing_yards": yards["rushing_yards"]["Value"]
                    if not uncertain["rushing_yards"]
                    and yards["rushing_yards"]["Missing"] == 0 else None,
            }
            game_team_rows += 1
            for name, value in observations.items():
                c = counts[name]
                c["UnknownSourceEligibilityRows"] += uncertain[name]
                c["UnknownSourceEligibilityTeamGames"] += bool(uncertain[name])
                if truth is None:
                    c["MissingPlayerStats"] += 1
                    continue
                if value is None:
                    c["MissingPBP"] += 1
                    continue
                expected = truth[name]
                delta = value - expected
                deltas[name].append(delta)
                c["Compared"] += 1
                c["Equal" if delta == 0 else "Different"] += 1
                if delta:
                    mismatches[name].append({
                        "GameID": gid, "OffenseTeam": offense,
                        "DefenseTeam": defense_team,
                        "PBP": value, "PlayerStats": expected,
                        "DeltaPBPMinusPlayerStats": delta,
                    })
    for name in BASE_FIELDS:
        counts[name]["DeltaDistribution"] = _delta_distribution(deltas[name])
        # Show largest discrepancies rather than the first 12 alphabetic games.
        counts[name]["Examples"] = sorted(
            mismatches[name],
            key=lambda row: (-abs(row["DeltaPBPMinusPlayerStats"]),
                             row["GameID"], row["OffenseTeam"]),
        )[:12]
    team_fields = [m for m in field_audit["MetricFieldCoverage"]
                   if m["MetricID"] in (candidate_ids or [])]
    return {
        "ReportSchemaVersion": 1,
        "Status": "real-original-asset-observed-not-certified-upstream-complete",
        "Season": season,
        "ReadOnly": True,
        "IdentityOrPositionJoinPerformed": False,
        "PBPAssetSHA256": digest,
        "PBPCompressedBytes": path.stat().st_size,
        "PBPSourceRowsScanned": field_audit["RawSeasonRowCount"],
        "GzipStreamReadToEOF": True,
        "CanonicalGames": len(games),
        "OriginalGamesObserved": len(by_game),
        "MissingOriginalGameIDs": missing_games,
        "GameTeamCandidateRows": game_team_rows,
        "EligibleScrimmagePlays": eligible_plays,
        "TeamOnlyMetricCandidateIDs": candidate_ids or [],
        "TeamMetricResearchCoverage": _metric_coverage_finalize(metric_evidence),
        "PBPFieldAudit": {
            "OriginalColumnCount": field_audit["CsvColumnCount"],
            "MetricFieldStatuses": {
                m["MetricID"]: m["Status"] for m in team_fields
            },
            "OriginalCoverageCertified": False,
        },
        "PlayerStatsBaseline": stat_audit,
        "Reconciliation": counts,
        "ComparisonRule": (
            "Diagnostic only: PBP excludes certain flags (spikes, two-point plays) "
            "and differs from official PlayerStats on sacks, kneels and penalties. "
            "Unknown two-point/attempt/throw-eligibility flags suppress affected "
            "team comparisons rather than silently counting partial totals. "
            "Delta = PBP minus PlayerStats; missing comparisons are excluded, "
            "absolute percentiles use nearest rank, examples show the 12 largest "
            "absolute deviations. Equal does not prove completeness; unequal "
            "does not prove a defect."
        ),
        "ProductionReady": False,
        "FullUpstreamPlayCompletenessVerified": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--pbp-csv-gz", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    args = parser.parse_args()
    try:
        report = reconcile(args.repo_root.resolve(), args.pbp_csv_gz, args.season,
                           args.expected_sha256)
    except (OSError, ValueError, TypeError, KeyError, EOFError, csv.Error,
            json.JSONDecodeError) as exc:
        print(f"nfl_pbp_team_metric_reconcile failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
