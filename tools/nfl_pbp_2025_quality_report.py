#!/usr/bin/env python3
"""Read-only original-2025-PBP quality research (Issue #1077).

Uses the immutable accepted source asset and the existing independent field
and PBP-to-PlayerStats auditors. Emits a compact, reproducible JSON receipt to
stdout for human research; never writes Source, Derived, App or fantasy output.
Observed source-row completeness is not certification of complete NFL plays.
"""
from __future__ import annotations

import json
import statistics
import sys
import tempfile
from pathlib import Path
from typing import Any

from data_roots import DATA_DERIVED_ROOT, DATA_SOURCE_ROOT
from nfl_pbp_metric_field_audit import _catalog, audit
from nfl_pbp_source_archive import EXPECTED_SHA256, EXPECTED_SIZE, MANIFEST_PATH, sha256
from nfl_pbp_team_metric_reconcile import reconcile
from nfl_source_data_lib.common import download

MVP_METRICS = (
    "offensive_dropbacks_faced",
    "pass_attempts_faced",
    "rush_attempts_faced",
    "dropback_epa_per_play_allowed",
    "pass_epa_per_attempt_allowed",
    "rush_epa_per_play_allowed",
    "dropback_success_rate_allowed",
    "rush_success_rate_allowed",
    "pass_explosive_20_rate_allowed",
    "rush_explosive_10_rate_allowed",
)
FIELD_COHORT = {
    "offensive_dropbacks_faced": "QBDropback",
    "pass_attempts_faced": "PassPlayType",
    "rush_attempts_faced": "RunPlayType",
    "dropback_epa_per_play_allowed": "QBDropback",
    "pass_epa_per_attempt_allowed": "PassPlayType",
    "rush_epa_per_play_allowed": "RunPlayType",
    "dropback_success_rate_allowed": "QBDropback",
    "rush_success_rate_allowed": "RunPlayType",
    "pass_explosive_20_rate_allowed": "PassPlayType",
    "rush_explosive_10_rate_allowed": "RunPlayType",
}


def summarize(field: dict[str, Any], metrics: dict[str, Any]) -> dict[str, Any]:
    catalog, _ = _catalog(Path(__file__).resolve().parents[1] /
                          ".ai-context/manual/nfl-games-pbp-metrics.yaml")
    definitions = {x["MetricID"]: x for x in catalog}
    source_field = {x["MetricID"]: x for x in field["MetricFieldCoverage"]}
    research = metrics["TeamMetricResearchCoverage"]
    if not set(MVP_METRICS) <= set(definitions) & set(source_field) & set(research):
        raise ValueError("The ten approved MVP metrics are not all present in real evidence")
    if field["SourceAssetSHA256"] != metrics["PBPAssetSHA256"]:
        raise ValueError("Field and metric audits did not replay the same pinned original")
    observed_games = int(field["DistinctGameIDs"])
    row_counts = [x["RowCount"] for x in field["GameRowCounts"]]
    context = field["CanonicalGameContextReconciliation"]
    per_metric = []
    for metric_id in MVP_METRICS:
        cohort = FIELD_COHORT[metric_id]
        observed = research[metric_id]
        col_evidence = []
        for col in definitions[metric_id]["Fields"]:
            f = field["FieldCoverage"].get(col)
            if f is None:
                col_evidence.append({"Field": col, "HeaderPresent": False})
                continue
            rows = f["Cohorts"][cohort]
            col_evidence.append({
                "Field": col, "HeaderPresent": f["HeaderPresent"],
                "Cohort": cohort, "CohortRows": rows["Rows"],
                "NonNull": rows["NonNull"], "Missing": rows["Missing"],
                "NonNullRate": round(rows["NonNull"] / rows["Rows"], 4)
                if rows["Rows"] else None,
            })
        per_metric.append({
            "MetricID": metric_id,
            "SourceFieldStatus": source_field[metric_id]["Status"],
            "Fields": col_evidence,
            "ObservedTeamGames": observed["ObservedTeamGames"],
            "MissingTeamGames": observed["MissingTeamGames"],
            "UnknownEligibilityFlagRows": observed["UnknownFlagRows"],
            "TeamGamesWithUnknownEligibility": observed["UnknownFlagTeamGames"],
            "EligibleOutcomeRows": observed["EligibleOutcomeRows"],
            "ObservedOutcomeRows": observed["ObservedOutcomeRows"],
            "MissingOutcomeRows": observed["MissingOutcomeRows"],
            "ZeroOutcomeDenominatorTeamGames": observed["ZeroOutcomeDenominatorTeamGames"],
            "ObservedDenominator": observed["ObservedDenominator"],
            "ObservedWeightedMeanApprox": observed["ObservedWeightedMeanApprox"],
            "MinGameValue": observed["MinGameValue"],
            "MaxGameValue": observed["MaxGameValue"],
            "Assessment": "observed-source-candidate-not-production-certified",
        })
    recon = {}
    for name, item in metrics["Reconciliation"].items():
        recon[name] = {
            "Compared": item["Compared"],
            "Equal": item["Equal"],
            "Different": item["Different"],
            "MissingPBP": item["MissingPBP"],
            "MissingPlayerStats": item["MissingPlayerStats"],
            "UnknownSourceEligibilityRows": item["UnknownSourceEligibilityRows"],
            "UnknownSourceEligibilityTeamGames": item["UnknownSourceEligibilityTeamGames"],
            "DeltaDistribution": item["DeltaDistribution"],
            "LargestDeviationExamples": item["Examples"][:5],
        }
    return {
        "ReportSchemaVersion": 1,
        "Status": "real-pbp-2025-research-only-not-production-approved",
        "Season": 2025,
        "SourceSHA256": field["SourceAssetSHA256"],
        "SourceCompressedBytes": field["SourceAssetCompressedBytes"],
        "SourceRows": field["RawSeasonRowCount"],
        "SourceCSVColumns": field["CsvColumnCount"],
        "OriginalGamesObserved": observed_games,
        "CanonicalGames": metrics["CanonicalGames"],
        "MissingOriginalGameIDs": metrics["MissingOriginalGameIDs"],
        "GameTeamCandidates": metrics["GameTeamCandidateRows"],
        "EligibleScrimmagePlays": metrics["EligibleScrimmagePlays"],
        "CanonicalContext": {
            "ExactContextRows": context.get("ExactContextRows"),
            "HistoricalAliasContextRows": context.get("HistoricalAliasContextRows"),
            "UnknownGameIDRows": context.get("UnknownGameIDRows"),
            "MismatchedContextRows": context.get("MismatchedContextRows"),
            "MatchedNonFinalGameRows": context.get("MatchedNonFinalGameRows"),
        },
        "GameSourceRowCounts": {
            "Min": min(row_counts), "Median": statistics.median(row_counts),
            "Max": max(row_counts),
            "ZeroNotObservableInThisCount": True,
        },
        "CohortRowCounts": field["CohortRowCounts"],
        "MonitoredFieldsAbsent": field["MonitoredFieldsAbsent"],
        "BinaryFieldInvalidCounts": field["BinaryFieldInvalidCounts"],
        "DictionarySemanticCrosschecks": field["DictionarySemanticCrosschecks"],
        "ArchivedProjectionComparison": field["ArchivedProjectionComparison"],
        "MVPMetricEvidence": per_metric,
        "PlayerStatsBaseline": metrics["PlayerStatsBaseline"],
        "PlayerStatsReconciliation": recon,
        "Limitations": [
            "Original nflverse rows and sha observed; upstream game/play completeness not independently certified",
            "No player-position joins, cross-season stability or predictive validation",
            "Per-game rates and numerator evidence may be rounded; aggregate mean is diagnostic only",
            "Missing or partial eligibility cannot be interpreted as zero; documented provider semantics may differ from official PlayerStats",
            "No GameDetail-v2 Source/Derived publisher activated by this report",
        ],
        "ProductionReady": False,
    }


def run(repo: Path) -> dict[str, Any]:
    manifest = json.loads((repo / MANIFEST_PATH).read_text(encoding="utf-8"))
    if (
        manifest.get("Status") != "accepted-original-byte-identity"
        or manifest.get("UpstreamSHA256") != EXPECTED_SHA256
        or manifest.get("CompressedBytes") != EXPECTED_SIZE
        or manifest.get("Season") != 2025
        or manifest.get("SourceCompletenessCertified") is not False
    ):
        raise ValueError("Missing or invalid accepted 2025 original-Source manifest")
    url = manifest.get("ArchiveURL")
    if not isinstance(url, str) or not url.startswith(
        "https://github.com/Lolindhir/fantasy-app/releases/download/"
    ) or not url.endswith("/play_by_play_2025.csv.gz"):
        raise ValueError("Unexpected original-PBP release download origin")
    with tempfile.TemporaryDirectory(prefix="pbp-2025-quality-") as directory:
        original = Path(directory) / "play_by_play_2025.csv.gz"
        download(url, original)
        if original.stat().st_size != EXPECTED_SIZE or sha256(original) != EXPECTED_SHA256:
            raise ValueError("Accepted 2025 release download failed original byte identity")
        catalog = repo / ".ai-context/manual/nfl-games-pbp-metrics.yaml"
        archived = repo / f"{DATA_SOURCE_ROOT}/providers/nflverse/special-teams-fumble-events/metadata-2025.json"
        field = audit(
            path=original, season=2025, catalog_path=catalog,
            metadata_path=archived if archived.is_file() else None,
            expected_sha256=EXPECTED_SHA256,
            game_index_path=repo / f"{DATA_DERIVED_ROOT}/nfl-games/2025.json",
        )
        metrics = reconcile(repo, original, 2025, EXPECTED_SHA256)
        return summarize(field, metrics)


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    try:
        report = run(repo)
    except (OSError, ValueError, TypeError, KeyError, EOFError) as error:
        print(f"PBP_2025_QUALITY_ERROR={error}", file=sys.stderr)
        return 1
    # Parseable in existing GitHub Actions log and human-copyable. Never print
    # source play rows or write an analysis result through Source's branch writer.
    print("PBP_2025_QUALITY_REPORT_JSON=" + json.dumps(
        report, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
