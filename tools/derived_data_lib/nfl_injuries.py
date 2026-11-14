"""Consumer-neutral observed NFL injury report product, not availability.

Pure, deterministic derivation from canonical Injury Report partitions.
This product does NOT claim diagnosis, time of injury, medical episodes,
games missed, healed/healthy states, or historical pre-kickoff snapshots.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

_REASON_FIELDS = (
    "report_primary_injury",
    "report_secondary_injury",
    "practice_primary_injury",
    "practice_secondary_injury",
)
_STATUS_FIELDS = ("report_status", "practice_status")


def derive_nfl_injuries(canonical: dict[str, Any]) -> dict[str, Any]:
    """Return a season-wide, replayable v1 view of observed reports only."""
    if canonical.get("SchemaVersion") != 1 or canonical.get("SourceDataset") != "nflverse.injuries":
        raise ValueError("Incompatible canonical NFL injury source")
    season = canonical.get("Season")
    source_digest = canonical.get("SourceAssetSha256")
    identity_digest = canonical.get("IdentityGraphFingerprint")
    partitions = canonical.get("Partitions")
    if not isinstance(season, int) or not source_digest or not identity_digest or not isinstance(partitions, list):
        raise ValueError("Incomplete canonical NFL injury product input")

    by_player_week: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    by_reason: dict[tuple[str, str, str], set[int]] = defaultdict(set)
    observed_team_weeks: dict[tuple[int, str, str], int] = defaultdict(int)
    all_observations: set[str] = set()
    seen_weeks: set[int] = set()
    unreported = 0
    unassigned = 0
    count = 0

    for partition in partitions:
        week = partition.get("Week")
        if (partition.get("SchemaVersion") != 1 or partition.get("Season") != season
                or partition.get("SourceDataset") != "nflverse.injuries"
                or partition.get("SourceAssetSha256") != source_digest
                or partition.get("IdentityGraphFingerprint") != identity_digest):
            raise ValueError("Inconsistent injury partition provenance")
        if not isinstance(week, int) or week < 1 or week > 22 or week in seen_weeks:
            raise ValueError("Missing, invalid or duplicate injury partition week")
        seen_weeks.add(week)
        observations = partition.get("Observations")
        if not isinstance(observations, list):
            raise ValueError("Injury partition must contain Observations")
        for row in observations:
            key, source = row.get("ObservationKey"), row.get("OriginalFields")
            if (not isinstance(key, str) or not isinstance(source, dict)
                    or key in all_observations or row.get("Week") != week
                    or row.get("Season") != season):
                raise ValueError("Duplicate, incomplete or inconsistent report observation")
            all_observations.add(key)
            gsis = (row.get("SourceIDs") or {}).get("GSIS")
            if not isinstance(gsis, str) or not gsis:
                raise ValueError("Missing GSIS in canonical report")
            if row.get("IdentityResolution") != "resolved-current-graph":
                unassigned += 1
            if not any(source.get(field) for field in _REASON_FIELDS + _STATUS_FIELDS):
                unreported += 1
            count += 1
            observed_team_weeks[(week, str(row["GameType"]), str(row["SourceTeam"]))] += 1
            view = {
                "ObservationKey": key,
                "RowOrdinal": row["RowOrdinal"],
                "GameType": row["GameType"],
                "SeasonType": row.get("SeasonType"),
                "SourceTeam": row["SourceTeam"],
                "CanonicalPlayerID": row.get("CanonicalPlayerID"),
                "IdentityResolution": row["IdentityResolution"],
                "GameID": row.get("GameID"),
                "GameLinkState": row["GameLinkState"],
                "SourceModifiedRaw": row.get("SourceModifiedRaw"),
                "ReportStatus": source.get("report_status"),
                "PracticeStatus": source.get("practice_status"),
                "Reasons": {field: source.get(field) for field in _REASON_FIELDS},
            }
            by_player_week[(gsis, week)].append(view)
            for field in _REASON_FIELDS:
                reason = source.get(field)
                if reason:
                    # A label repeated in multiple weeks is an observed report
                    # trajectory, NEVER a proven single medical injury episode.
                    by_reason[(gsis, field, reason)].add(week)

    if canonical.get("Quality", {}).get("SourceRowCount") != count:
        raise ValueError("Canonical source row count disagrees with derived observations")
    player_weeks = []
    multiple_observation_weeks = 0
    for (gsis, week), reports in sorted(by_player_week.items(), key=lambda item: (item[0][1], item[0][0])):
        reports.sort(key=lambda r: r["RowOrdinal"])
        owners = {r["CanonicalPlayerID"] for r in reports if r["CanonicalPlayerID"]}
        resolved = len(owners) == 1 and all(r["IdentityResolution"] == "resolved-current-graph" for r in reports)
        if len(reports) > 1:
            multiple_observation_weeks += 1
        player_weeks.append({
            "Season": season,
            "Week": week,
            "SourceIDs": {"GSIS": gsis},
            "CanonicalPlayerID": next(iter(owners)) if resolved else None,
            "IdentityResolution": "resolved-current-graph" if resolved else "not-uniformly-resolved",
            "SourceTeams": sorted({r["SourceTeam"] for r in reports}),
            "ObservedReportCount": len(reports),
            "Observations": reports,
            "StatusOrdering": "not-inferred-from-row-order",
        })

    trajectories = []
    for (gsis, field, reason), observed in sorted(by_reason.items()):
        weeks = sorted(observed)
        first, last = weeks[0], weeks[-1]
        trajectories.append({
            "SourceIDs": {"GSIS": gsis},
            "ReasonField": field,
            "ObservedReason": reason,
            "FirstObservedWeek": first,
            "LastObservedWeek": last,
            "CountObservedWeeks": len(weeks),
            "ObservedWeeks": weeks,
            "GapWeeks": [week for week in range(first, last + 1) if week not in observed],
            "Semantics": "report-observation-trajectory-not-clinical-episode",
        })
    return {
        "SchemaVersion": 1,
        "Product": "nfl-injuries",
        "ProductVersion": "nfl-injuries-v1",
        "Season": season,
        "SourceDataset": "nflverse.injuries",
        "SourceAssetSha256": source_digest,
        "IdentityGraphFingerprint": identity_digest,
        "TemporalEvidence": "retrospective-source-snapshot-not-point-in-time",
        "MissingReportMeaning": "unknown-not-healthy-or-available",
        "ObservedPlayerWeeks": player_weeks,
        "ObservedTeamWeeks": [
            {"Week": week, "GameType": game_type, "SourceTeam": team, "ReportCount": count}
            for (week, game_type, team), count in sorted(observed_team_weeks.items())
        ],
        "ObservedReasonTrajectories": trajectories,
        "Quality": {
            "SourceObservationCount": count,
            "ObservedPlayerWeekCount": len(player_weeks),
            "ObservedTeamWeekCount": len(observed_team_weeks),
            "ObservedTrajectoryCount": len(trajectories),
            "MultipleObservationPlayerWeeks": multiple_observation_weeks,
            "RowsWithoutReasonsOrStatuses": unreported,
            "RowsWithoutUniformCurrentIdentity": unassigned,
            "ObservedWeekCount": len(seen_weeks),
        },
    }
