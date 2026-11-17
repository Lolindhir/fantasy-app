"""Read-only candidate for the existing nfl-games per-GameID Derived product.

Issue #1077. This *does not* persist or publish game details. It combines the
existing canonical game index, canonical weekly PlayerStats and SnapCounts,
reusing the approved pure game-stat and team-snap calculations. Group-level
identity holds remain visible: a missing player identity blocks player-based
team stats, but cannot erase independently supported team snap totals.
"""
from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping

from .nfl_game_detail import (
    build_nfl_game_detail,
    _PLAYER_COUNT_FIELDS,
    _SNAP_FIELDS,
    _SNAPS_SOURCE,
    _STATS_SOURCE,
    _group_status,
    _player_stat_rows,
    _season_index,
    _team_totals,
    _valid_type,
    _week_source,
)
from .nfl_franchise_aliases import reconcile_game_team
from .nfl_team_snap_usage import infer_team_snap_volumes

_DEFINITION_VERSION = 1


def _selected_stats(
    payload: Mapping[str, Any] | None, season: int, game: Mapping[str, Any],
) -> tuple[list[dict[str, Any]] | None, bool | None, list[Mapping[str, Any]], int, str, int, int]:
    rows, finalized = _week_source(payload, season, game, _STATS_SOURCE)
    if rows is None:
        return None, None, [], 0, "unavailable", 0, 0
    selected: list[Mapping[str, Any]] = []
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    unresolved = 0
    aliases = 0
    missing_context = 0
    for row in rows:
        stats = row.get("Stats")
        if not isinstance(stats, dict) or not isinstance(stats.get("game_id"), str):
            raise ValueError("player-stats: missing Stats.game_id")
        if stats["game_id"] != game["GameID"]:
            continue
        team, opponent = row.get("Team"), row.get("OpponentTeam")
        canonical = reconcile_game_team(
            team, opponent, game["AwayTeam"], game["HomeTeam"], season,
        )
        if (row.get("Week") != game["Week"]
                or not _valid_type(row.get("SeasonType"), game["GameType"])
                or (canonical is None and team is not None and opponent is not None)):
            raise ValueError(
                f"player-stats: invalid game/team/week/type for {game['GameID']}: "
                f"team={team!r}, opp={opponent!r}, "
                f"week={row.get('Week')!r}, type={row.get('SeasonType')!r}, "
                f"expected {game['AwayTeam']}/{game['HomeTeam']} {game['Week']} {game['GameType']}"
            )
        # A genuinely missing team/opponent context blocks the entire
        # player-sum group, but must not suppress independent team snaps.
        if canonical is None:
            missing_context += 1
            other = None
        else:
            other = game["HomeTeam"] if canonical == game["AwayTeam"] else game["AwayTeam"]
            if team != canonical or opponent != other:
                aliases += 1
        cid = row.get("CanonicalPlayerID")
        if not isinstance(cid, str) or not cid:
            unresolved += 1
        elif cid in seen:
            raise ValueError("player-stats: duplicated canonical player in game")
        else:
            seen.add(cid)
        for field in _PLAYER_COUNT_FIELDS:
            value = stats.get(field)
            if value is not None and (
                type(value) is not int or
                (value < 0 and not field.endswith("_yards"))
            ):
                raise ValueError(f"player-stats: invalid counting field {field}")
        # The versioned fingerprint only depends on fields actually consumed by
        # the v1 team-stats model. Raw provider records may contain unrelated
        # nonfinite floats (e.g. historical EPA) and must not force a rebuild.
        selected.append({
            "CanonicalPlayerID": cid,
            "Team": team,
            "OpponentTeam": opponent,
            "Week": row.get("Week"),
            "SeasonType": row.get("SeasonType"),
            "Stats": {field: stats.get(field) for field in _PLAYER_COUNT_FIELDS},
        })
        normalized.append({**row, "Team": canonical, "OpponentTeam": other})
    if missing_context:
        return (None, finalized, selected, unresolved,
                "blocked-missing-team-context", aliases, missing_context)
    if unresolved:
        return (None, finalized, selected, unresolved,
                "blocked-unresolved-player-identity", aliases, 0)
    # Reuse the canonical player validator and additive team totals, now with
    # narrowly validated era-specific franchise spelling in a temporary copy.
    sanitized = {**payload, "Records": normalized}
    validated, _ = _player_stat_rows(sanitized, season, game)
    return validated, finalized, selected, 0, _group_status(validated, game), aliases, 0


def _selected_snap_counts(
    payload: Mapping[str, Any] | None, season: int, game: Mapping[str, Any],
) -> tuple[
    list[dict[str, Any]] | None, bool | None, list[Mapping[str, Any]],
    int, str, int, dict[str, dict[str, int]],
]:
    rows, finalized = _week_source(payload, season, game, _SNAPS_SOURCE)
    if rows is None:
        return None, None, [], 0, "unavailable", 0, {}
    selected: list[Mapping[str, Any]] = []
    team_rows: list[dict[str, Any]] = []
    invalid_shares: dict[str, dict[str, int]] = {}
    seen: set[str] = set()
    unresolved = 0
    aliases = 0
    for row in rows:
        if row.get("GameID") != game["GameID"]:
            continue
        team, opponent = row.get("Team"), row.get("OpponentTeam")
        canonical = reconcile_game_team(
            team, opponent, game["AwayTeam"], game["HomeTeam"], season,
        )
        if (canonical is None
                or row.get("Week") != game["Week"]
                or row.get("GameType") != game["GameType"]):
            raise ValueError(
                f"snap-counts: invalid game/team/week/type for {game['GameID']}: "
                f"team={team!r}, opp={opponent!r}"
            )
        other = game["HomeTeam"] if canonical == game["AwayTeam"] else game["AwayTeam"]
        if team != canonical or opponent != other:
            aliases += 1
        cid = row.get("CanonicalPlayerID")
        if not isinstance(cid, str) or not cid:
            unresolved += 1
        elif cid in seen:
            raise ValueError("snap-counts: duplicated canonical player in game")
        else:
            seen.add(cid)
        snaps: dict[str, int | float | None] = {}
        digest_snaps: dict[str, Any] = {}
        for field in _SNAP_FIELDS:
            value = row.get(field)
            if field.endswith("Pct") and value is not None and (
                type(value) not in (int, float)
                or not math.isfinite(value)
                or not 0 <= value <= 1
            ):
                # A faulty source share blocks only this team's affected unit;
                # it must never be clipped or used in denominator inference.
                unit = field[:-3]
                counts = invalid_shares.setdefault(canonical, {})
                counts[unit] = counts.get(unit, 0) + 1
                snaps[field] = None
                # Preserve typed invalid input evidence in the fingerprint.
                # repr() is JSON-safe even for NaN and Infinity.
                digest_snaps[field] = {
                    "InvalidShareType": type(value).__name__,
                    "InvalidShareValue": repr(value),
                }
            else:
                if not field.endswith("Pct") and value is not None and (
                    type(value) is not int or value < 0
                ):
                    raise ValueError(
                        f"snap-counts: invalid count {field} for "
                        f"{game['GameID']} player={cid!r}"
                    )
                snaps[field] = value
                digest_snaps[field] = value
        selected.append({
            "CanonicalPlayerID": cid,
            "Team": team,
            "OpponentTeam": opponent,
            "Week": row.get("Week"),
            "GameType": row.get("GameType"),
            "Snaps": digest_snaps,
        })
        team_rows.append({"Team": canonical, "Snaps": snaps})
    if not selected:
        return None, finalized, selected, 0, "unavailable", 0, {}
    all_teams = {row["Team"] for row in team_rows}
    status = ("available" if all_teams == {game["AwayTeam"], game["HomeTeam"]}
              else "partial")
    return team_rows, finalized, selected, unresolved, status, aliases, invalid_shares


def _digest(selected: dict[str, Any]) -> str:
    """Only this GameID's evidence affects the digest, not neighboring games."""
    # Selected rows are semantically unordered; do not depend on weekly Source order.
    values = {
        **selected,
        "PlayerStatsRows": sorted(
            selected["PlayerStatsRows"], key=lambda row: json.dumps(
                row, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
            )
        ),
        "SnapCountsRows": sorted(
            selected["SnapCountsRows"], key=lambda row: json.dumps(
                row, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
            )
        ),
    }
    encoded = json.dumps(values, sort_keys=True, ensure_ascii=False,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_nfl_game_detail_core(
    index: Mapping[str, Any], game_id: str,
    player_stats: Mapping[str, Any] | None = None,
    snap_counts: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Produce a compact game/team-only v1 candidate with no source mutations."""
    season, games = _season_index(index)
    game = games.get(game_id)
    if game is None:
        raise ValueError(f"GameID not found in canonical nfl-games index: {game_id}")
    stat_players, stats_finalized, stat_raw, stat_holds, stats_status, stat_aliases, stat_missing_context = _selected_stats(
        player_stats, season, game,
    )
    team_snap_rows, snaps_finalized, snap_raw, snap_holds, snap_status, snap_aliases, invalid_shares = _selected_snap_counts(
        snap_counts, season, game,
    )
    team_snap_totals = infer_team_snap_volumes(
        team_snap_rows, game["AwayTeam"], game["HomeTeam"],
    )
    invalid_share_rows = sum(sum(counts.values()) for counts in invalid_shares.values())
    if team_snap_totals is not None:
        for team in team_snap_totals:
            for unit, count in invalid_shares.get(team["Team"], {}).items():
                team[unit]["TotalSnaps"] = None
                team[unit]["Status"] = "blocked-invalid-share"
                team[unit]["InvalidShareRows"] = count
    input_digest = _digest({
        "SchemaVersion": 1,
        "DefinitionVersion": _DEFINITION_VERSION,
        "Game": dict(game),
        "PlayerStatsFinalized": stats_finalized,
        "PlayerStatsRows": stat_raw,
        "SnapCountsFinalized": snaps_finalized,
        "SnapCountsRows": snap_raw,
    })
    result = {
        "SchemaVersion": 1,
        "Product": "nfl-games",
        "DetailDefinitionVersion": _DEFINITION_VERSION,
        "Season": season,
        "GameID": game_id,
        "Game": dict(game),
        "TeamStats": {
            "SourceDataset": _STATS_SOURCE,
            "Status": stats_status,
            "SourceFinalized": stats_finalized,
            "UnresolvedPlayerIdentityRows": stat_holds,
            "HistoricalFranchiseAliasRows": stat_aliases,
            "MissingTeamContextRows": stat_missing_context,
            "Method": "sum-of-valid-canonical-player-counting-stats-not-official-boxscore",
            "Teams": _team_totals(stat_players, game),
        },
        "SnapCounts": {
            "SourceDataset": _SNAPS_SOURCE,
            "Status": snap_status,
            "SourceFinalized": snaps_finalized,
            "UnresolvedPlayerIdentityRows": snap_holds,
            "HistoricalFranchiseAliasRows": snap_aliases,
            "Method": "unique-integer-denominator-from-rounded-player-percentages",
            "TeamTotalsOfficiallyVerified": False,
            "Teams": team_snap_totals,
        },
        "Coverage": {
            "GameIndex": "available",
            "TeamStats": stats_status,
            "TeamSnapCounts": snap_status,
            "PlayByPlay": "not-in-core-v1",
            "FullPlayByPlayAvailable": False,
        },
        "Derivation": {
            "DefinitionVersion": _DEFINITION_VERSION,
            "InputFingerprintSHA256": input_digest,
        },
    }
    if invalid_share_rows:
        result["SnapCounts"]["InvalidShareRows"] = invalid_share_rows
    return result


# Contract pilot: one compact GameID detail using the existing NFL Games owner.
# The original PBP reader is called only in memory; its raw SourceRows are
# deliberately NOT emitted in the v2 data product.
_V2_PBP_GROUPS = {
    "Opportunities": (
        "offensive_dropbacks_faced", "pass_attempts_faced", "rush_attempts_faced",
    ),
    "Efficiency": (
        "dropback_epa_per_play_allowed", "pass_epa_per_attempt_allowed",
        "rush_epa_per_play_allowed",
    ),
    "Success": (
        "dropback_success_rate_allowed", "rush_success_rate_allowed",
    ),
    "ExplosivePlays": (
        "pass_explosive_20_rate_allowed", "rush_explosive_10_rate_allowed",
    ),
}
_V2_PBP_COUNT_IDS = frozenset(_V2_PBP_GROUPS["Opportunities"])
_V2_PBP_DEFINITION_VERSION = 1
_V2_PBP_SOURCE_FIELDS = (
    "play_type", "posteam", "defteam", "two_point_attempt",
    "qb_kneel", "qb_spike", "qb_dropback", "qb_scramble",
    "pass_attempt", "rush_attempt", "sack", "epa", "success",
    "complete_pass", "passing_yards", "rushing_yards",
)


def _v2_pilot_metric(
    candidate: Mapping[str, Any] | None,
    metric_id: str,
    opportunity: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Adapt existing research metrics without inventing official parity."""
    is_count = metric_id in _V2_PBP_COUNT_IDS
    if candidate is None:
        return {
            "Status": "unavailable",
            "Unit": "count" if is_count else ("epa-per-play" if "_epa_" in metric_id else "rate"),
            "Value": None,
            "Numerator": None, "Denominator": None,
            "Eligible": None, "Observed": None, "Missing": None,
            "UnknownEligibilityFlagRows": None,
        }
    if is_count:
        unknown = candidate["UnknownFlagCount"]
        known_positive = candidate["Value"]
        # A confirmed subset cannot masquerade as the complete count when
        # an unknown flag could add opportunities.
        known_count = candidate["KnownPlayCount"]
        value = known_positive if unknown == 0 else None
        return {
            "Status": ("unknown-eligibility" if unknown
                       else "candidate-observed" if value is not None
                       else "no-observed-source-evidence"),
            "Unit": "count",
            "Value": value, "Numerator": value, "Denominator": None,
            "Eligible": known_count + unknown,
            "Observed": known_count, "Missing": unknown,
            "UnknownEligibilityFlagRows": unknown,
            "ConfirmedPositiveCount": known_positive,
            "DenominatorNotApplicable": True,
        }
    unknown = (
        opportunity["UnknownFlagCount"] if opportunity is not None else 0
    )
    observed = candidate["Observed"]
    missing = candidate["Missing"]
    status = (
        "no-observed-source-evidence" if not observed
        else "partial-unknown-eligibility" if unknown
        else "partial-missing-outcome" if missing
        else "candidate-observed"
    )
    return {
        "Status": status,
        "Unit": "epa-per-play" if "_epa_" in metric_id else "rate",
        "Value": candidate["Value"],
        # Preserve the unrounded sufficient statistic for ratio-of-sums rollups.
        "Numerator": candidate["UnroundedNumerator"],
        "Denominator": candidate["Denominator"],
        "Eligible": candidate["Eligible"],
        "Observed": observed,
        "Missing": missing,
        "UnknownEligibilityFlagRows": unknown,
        "SufficientStatisticsUnrounded": True,
    }


def build_nfl_game_detail_v2_pilot(
    index: Mapping[str, Any], game_id: str,
    player_stats: Mapping[str, Any] | None = None,
    snap_counts: Mapping[str, Any] | None = None,
    *,
    pbp_rows: list[Mapping[str, str]] | None = None,
    pbp_asset_sha256: str | None = None,
) -> dict[str, Any]:
    """Read-only versioned candidate, never a PBP publisher.

    The complete Game, TeamStats and SnapCounts groups are inherited unchanged
    from the approved core v1 builder. PBP contains ten neutral team-game
    competitive-opportunity facts, not original plays or fantasy judgements.
    """
    core = build_nfl_game_detail_core(index, game_id, player_stats, snap_counts)
    game = core["Game"]
    if pbp_rows is None:
        if pbp_asset_sha256 is not None:
            raise ValueError("PBP SHA supplied without original PBP rows")
        source_rows: list[Mapping[str, Any]] = []
        candidates = None
    else:
        if (
            not isinstance(pbp_asset_sha256, str)
            or len(pbp_asset_sha256) != 64
            or any(c not in "0123456789abcdef" for c in pbp_asset_sha256)
        ):
            raise ValueError("v2 pilot needs a lowercase original-PBP SHA256")
        preview = build_nfl_game_detail(
            index, game_id, pbp_rows=pbp_rows,
            pbp_asset_sha256=pbp_asset_sha256,
        )
        original = preview["PlayByPlay"]["OriginalPlays"]
        source_rows = original["Plays"]
        candidates = original["Analytics"]["CatalogTeamMetricCandidates"]
        required = {m for group in _V2_PBP_GROUPS.values() for m in group}
        if not required.issubset(candidates["CandidateIDs"]):
            raise ValueError("PBP metric candidate catalog missing v2-pilot metric")

    perspective_by_defense = (
        {row["Team"]: row["Metrics"] for row in candidates["ByDefenseTeam"]}
        if candidates is not None else {}
    )
    if candidates is not None and (
        set(perspective_by_defense) != {game["AwayTeam"], game["HomeTeam"]}
    ):
        raise ValueError("PBP candidate defense-team perspectives incomplete")

    observations = []
    for offense in (game["AwayTeam"], game["HomeTeam"]):
        defense = (
            game["HomeTeam"] if offense == game["AwayTeam"]
            else game["AwayTeam"]
        )
        metrics = perspective_by_defense.get(defense)
        if candidates is not None and metrics is None:
            raise ValueError("PBP missing opposing defense")
        groups = {}
        for group, metric_ids in _V2_PBP_GROUPS.items():
            values = {}
            for metric_id in metric_ids:
                count_id = (
                    "offensive_dropbacks_faced" if "dropback_" in metric_id
                    else "pass_attempts_faced" if "pass_" in metric_id
                    else "rush_attempts_faced"
                )
                if metrics is not None and metric_id not in metrics:
                    raise ValueError("PBP missing metric " + metric_id)
                values[metric_id] = _v2_pilot_metric(
                    metrics[metric_id] if metrics is not None else None,
                    metric_id,
                    metrics[count_id] if metrics is not None else None,
                )
            groups[group] = values
        observations.append({
            "OffenseTeam": offense, "DefenseTeam": defense,
            "Perspective": "offense-plays-also-defense-allowed",
            **groups,
        })

    # A GameID-specific fingerprint: preserve full source asset SHA separately
    # for lineage, and canonicalize only this game's formula-consumed PBP fields.
    selected = sorted(
        ({
            "PlayID": p["PlayID"],
            "Fields": {name: p["SourceRow"].get(name) for name in _V2_PBP_SOURCE_FIELDS},
        } for p in source_rows),
        key=lambda row: row["PlayID"],
    )
    fingerprint_input = {
        "SchemaVersion": 2,
        "PBPDefinitionVersion": _V2_PBP_DEFINITION_VERSION,
        "CoreV1FingerprintSHA256": core["Derivation"]["InputFingerprintSHA256"],
        "PBPSourceAssetSHA256": pbp_asset_sha256,
        "SelectedPBP": selected if candidates is not None else None,
    }
    fingerprint = hashlib.sha256(
        json.dumps(fingerprint_input, sort_keys=True, ensure_ascii=False,
                   separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()

    core["SchemaVersion"] = 2
    core["DetailDefinitionVersion"] = 2
    core["PlayByPlayMetrics"] = {
        "Status": ("read-only-pilot-observed-unverified-completeness"
                   if candidates is not None else "unavailable"),
        "SourceDataset": "nflverse.play-by-play",
        "OriginalAssetSHA256": pbp_asset_sha256,
        "Population": "competitive-opportunities-not-official-attempts",
        "MetricCatalogVersion": 1,
        "MetricDefinitionVersion": _V2_PBP_DEFINITION_VERSION,
        "GameSourceRowsObserved": len(source_rows) if candidates is not None else None,
        "CompetitiveScrimmageRowsObserved": (
            candidates["EligibleScrimmagePlayCount"] if candidates is not None else None
        ),
        "ExcludedGamePlayRows": candidates["Excluded"] if candidates is not None else None,
        "GameSourceCompletenessCertified": False,
        "OffensePerspectives": observations,
        "UnverifiedPenaltySemantics": True,
        "RatesAreObservedNumeratorOverObservedDenominator": True,
    }
    core["Coverage"]["PlayByPlay"] = (
        "source-rows-observed-upstream-completeness-unverified"
        if candidates is not None else "unavailable"
    )
    core["Coverage"]["PlayByPlayMetrics"] = core["PlayByPlayMetrics"]["Status"]
    core["Coverage"]["FullPlayByPlayAvailable"] = False
    core["Derivation"]["DefinitionVersion"] = 2
    core["Derivation"]["CoreV1InputFingerprintSHA256"] = (
        core["Derivation"]["InputFingerprintSHA256"]
    )
    core["Derivation"]["InputFingerprintSHA256"] = fingerprint
    core["Derivation"]["PBPMetricDefinitionVersion"] = _V2_PBP_DEFINITION_VERSION
    return core
