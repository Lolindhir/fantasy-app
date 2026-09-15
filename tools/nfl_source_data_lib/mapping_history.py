from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

from .canonical_identity import identity_lookup
from .common import clean, iter_csv, load_json, normalize_legacy_canonical_player_fields
from .historical_crosswalk import iter_historical_crosswalk_snapshots
from .identity_model import LINK_ID_KEYS, ids_from_ff

_SEASON_FILE = re.compile(r"Players_(\d{4})\.json$")
_MIN_HISTORICAL_CORROBORATORS = 2
_GIT_PLAYER_SNAPSHOT_PATH = "public/data/Players.json"


def _snapshot_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in ("Players", "players"):
            rows = payload.get(key)
            if isinstance(rows, list):
                return [row for row in rows if isinstance(row, dict)]
    return []


def _snapshot_ids(row: dict[str, Any]) -> dict[str, str]:
    values = {
        "Sleeper": clean(row.get("ID")),
        "Tank01": clean(row.get("TankID")),
        "ESPN": clean(row.get("ESPNID")),
    }
    return {key: value for key, value in values.items() if value}


def _resolve_snapshot_row(
    row: dict[str, Any],
    *,
    season: int,
    lookup: dict[tuple[str, str], str],
    source: str,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None, str]:
    snapshot_ids = _snapshot_ids(row)
    token_results: dict[str, str] = {}
    for provider, external_id in snapshot_ids.items():
        internal_id = lookup.get((provider, external_id))
        if internal_id:
            token_results[provider] = internal_id

    resolved_ids = sorted(set(token_results.values()))
    if len(resolved_ids) > 1:
        return (
            [],
            {
                "Reason": "historical_app_snapshot_provider_disagreement",
                "Season": season,
                "Name": clean(row.get("Name")) or clean(row.get("FullName")),
                "Position": clean(row.get("Position")),
                "SleeperID": snapshot_ids.get("Sleeper"),
                "Tank01ID": snapshot_ids.get("Tank01"),
                "ESPNID": snapshot_ids.get("ESPN"),
                "ResolvedByProvider": dict(sorted(token_results.items())),
                "EvidenceSource": source,
            },
            "conflict",
        )

    # Historical app evidence does not contain an exact birth date. A single
    # provider token is therefore not strong enough to move a temporal mapping:
    # the provider ID may have been corrected or reused later. Require at least
    # two independently resolved provider IDs to agree before treating the row
    # as season-specific identity evidence.
    if len(token_results) < _MIN_HISTORICAL_CORROBORATORS or not resolved_ids:
        return [], None, "insufficient"

    internal_id = resolved_ids[0]
    claims = [
        {
            "Provider": provider,
            "ExternalID": external_id,
            "CanonicalPlayerID": internal_id,
            "ObservedSeason": season,
            "Sources": [source],
        }
        for provider, external_id in sorted(snapshot_ids.items())
    ]
    return claims, None, "resolved"


def _historical_crosswalk_ids(row: dict[str, Any]) -> dict[str, str]:
    return {
        provider: external_id
        for provider, external_id in ids_from_ff(row).items()
        if provider in LINK_ID_KEYS
    }


def _resolve_historical_crosswalk_row(
    row: dict[str, Any],
    *,
    season: int,
    lookup: dict[tuple[str, str], str],
    source: str,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None, str]:
    provider_ids = _historical_crosswalk_ids(row)
    sleeper_id = provider_ids.get("Sleeper")
    if not sleeper_id:
        return [], None, "insufficient"

    # Sleeper is the mapping being reconstructed, so it must never corroborate
    # itself through today's active identity graph. Require two independent
    # non-Sleeper link-provider tokens to resolve to the same canonical person.
    corroborated: dict[str, str] = {}
    for provider, external_id in provider_ids.items():
        if provider == "Sleeper":
            continue
        internal_id = lookup.get((provider, external_id))
        if internal_id:
            corroborated[provider] = internal_id

    resolved_ids = sorted(set(corroborated.values()))
    if len(resolved_ids) > 1:
        return (
            [],
            {
                "Reason": "historical_crosswalk_provider_disagreement",
                "Season": season,
                "SleeperID": sleeper_id,
                "ProviderIDs": dict(sorted(provider_ids.items())),
                "ResolvedByProvider": dict(sorted(corroborated.items())),
                "EvidenceSource": source,
            },
            "conflict",
        )

    if len(corroborated) < _MIN_HISTORICAL_CORROBORATORS or not resolved_ids:
        return [], None, "insufficient"

    internal_id = resolved_ids[0]
    claims = [
        {
            "Provider": provider,
            "ExternalID": external_id,
            "CanonicalPlayerID": internal_id,
            "ObservedSeason": season,
            "Sources": [source],
        }
        for provider, external_id in sorted(provider_ids.items())
    ]
    return claims, None, "resolved"


def _git_snapshot_commits(repo_root: Path, season: int) -> list[str]:
    """Return bounded contemporaneous Players.json snapshots for one NFL season.

    Git history is evidence only. Missing/shallow history must not make ordinary
    materialization fail; it simply means no historical claim can be made from
    this source. The first and last snapshot in the season window are enough to
    cover stable veterans plus in-season additions without parsing every large
    generated Players.json revision.
    """

    try:
        result = subprocess.run(
            [
                "git",
                "log",
                "--format=%H",
                "--reverse",
                f"--since={season}-09-01T00:00:00Z",
                f"--until={season + 1}-03-01T00:00:00Z",
                "--",
                _GIT_PLAYER_SNAPSHOT_PATH,
            ],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return []

    commits = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if len(commits) <= 2:
        return commits
    return [commits[0], commits[-1]]


def _git_snapshot_rows(repo_root: Path, commit: str) -> list[dict[str, Any]]:
    try:
        result = subprocess.run(
            ["git", "show", f"{commit}:{_GIT_PLAYER_SNAPSHOT_PATH}"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
        return _snapshot_rows(json.loads(result.stdout))
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError):
        return []


def _dedupe_claims(claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[tuple[str, str, str, int], dict[str, Any]] = {}
    for claim in claims:
        key = (
            str(claim["Provider"]),
            str(claim["ExternalID"]),
            str(claim["CanonicalPlayerID"]),
            int(claim["ObservedSeason"]),
        )
        existing = merged.get(key)
        if existing is None:
            merged[key] = dict(claim)
            merged[key]["Sources"] = sorted(set(claim.get("Sources") or []))
            continue
        existing["Sources"] = sorted(
            set(existing.get("Sources") or []) | set(claim.get("Sources") or [])
        )
    return [merged[key] for key in sorted(merged)]


def build_historical_app_mapping_claims(
    repo_root: Path,
    canonical: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    lookup = identity_lookup(canonical)
    claims: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    stats = {
        "snapshotSeasonCount": 0,
        "snapshotPlayerCount": 0,
        "resolvedPlayerCount": 0,
        "unresolvedPlayerCount": 0,
        "insufficientCorroborationCount": 0,
        "conflictingPlayerCount": 0,
        "gitSnapshotSeasonCount": 0,
        "gitSnapshotCommitCount": 0,
        "gitSnapshotPlayerCount": 0,
        "gitResolvedPlayerCount": 0,
        "gitUnresolvedPlayerCount": 0,
        "gitInsufficientCorroborationCount": 0,
        "gitConflictingPlayerCount": 0,
        "externalSnapshotSeasonCount": 0,
        "externalSnapshotCount": 0,
        "externalSnapshotPlayerCount": 0,
        "externalResolvedPlayerCount": 0,
        "externalUnresolvedPlayerCount": 0,
        "externalInsufficientCorroborationCount": 0,
        "externalConflictingPlayerCount": 0,
        "externalHistoricalClaimCount": 0,
        "externalSleeperClaimCount": 0,
        "historicalClaimCount": 0,
    }

    archive_root = repo_root / "public/data/past_seasons"
    archive_seasons: list[int] = []
    for path in sorted(archive_root.glob("Players_*.json")):
        match = _SEASON_FILE.search(path.name)
        if not match:
            continue
        season = int(match.group(1))
        archive_seasons.append(season)
        rows = _snapshot_rows(load_json(path, []) or [])
        stats["snapshotSeasonCount"] += 1
        stats["snapshotPlayerCount"] += len(rows)

        for row in rows:
            row_claims, conflict, status = _resolve_snapshot_row(
                row,
                season=season,
                lookup=lookup,
                source=f"app.PastPlayers.{season}",
            )
            if status == "resolved":
                stats["resolvedPlayerCount"] += 1
                claims.extend(row_claims)
            elif status == "conflict":
                stats["conflictingPlayerCount"] += 1
                if conflict is not None:
                    conflicts.append(conflict)
            else:
                stats["unresolvedPlayerCount"] += 1
                stats["insufficientCorroborationCount"] += 1

    # The archived Players_<season>.json files are derived from historical
    # Tank01 boxscores and therefore normally contain only TankID. Git history
    # of the contemporaneous generated Players.json is a stronger bridge: that
    # read model was built by joining Sleeper.player_id with Tank01.playerID.
    # Reuse the exact same two-provider corroboration rule before extending any
    # historical temporal mapping. No Git evidence means no claim.
    for season in sorted(set(archive_seasons)):
        commits = _git_snapshot_commits(repo_root, season)
        if not commits:
            continue
        stats["gitSnapshotSeasonCount"] += 1
        stats["gitSnapshotCommitCount"] += len(commits)
        for commit in commits:
            rows = _git_snapshot_rows(repo_root, commit)
            stats["gitSnapshotPlayerCount"] += len(rows)
            source = f"app.Players.git.{season}@{commit[:12]}"
            for row in rows:
                row_claims, conflict, status = _resolve_snapshot_row(
                    row,
                    season=season,
                    lookup=lookup,
                    source=source,
                )
                if status == "resolved":
                    stats["gitResolvedPlayerCount"] += 1
                    claims.extend(row_claims)
                elif status == "conflict":
                    stats["gitConflictingPlayerCount"] += 1
                    if conflict is not None:
                        conflicts.append(conflict)
                else:
                    stats["gitUnresolvedPlayerCount"] += 1
                    stats["gitInsufficientCorroborationCount"] += 1

    external_claims: list[dict[str, Any]] = []
    external_seasons: set[int] = set()
    for snapshot in iter_historical_crosswalk_snapshots(repo_root):
        season = int(snapshot["season"])
        external_seasons.add(season)
        stats["externalSnapshotCount"] += 1
        source = (
            f"{snapshot['sourceId']}.git.{season}.{snapshot['role']}"
            f"@{str(snapshot['commitSha'])[:12]}"
        )
        rows = list(iter_csv(Path(snapshot["path"])))
        stats["externalSnapshotPlayerCount"] += len(rows)
        for row in rows:
            row_claims, conflict, status = _resolve_historical_crosswalk_row(
                row,
                season=season,
                lookup=lookup,
                source=source,
            )
            if status == "resolved":
                stats["externalResolvedPlayerCount"] += 1
                external_claims.extend(row_claims)
            elif status == "conflict":
                stats["externalConflictingPlayerCount"] += 1
                if conflict is not None:
                    conflicts.append(conflict)
            else:
                stats["externalUnresolvedPlayerCount"] += 1
                stats["externalInsufficientCorroborationCount"] += 1

    stats["externalSnapshotSeasonCount"] = len(external_seasons)
    deduped_external = _dedupe_claims(external_claims)
    stats["externalHistoricalClaimCount"] = len(deduped_external)
    stats["externalSleeperClaimCount"] = sum(
        1 for claim in deduped_external if claim["Provider"] == "Sleeper"
    )
    claims.extend(deduped_external)

    claims = _dedupe_claims(claims)
    stats["historicalClaimCount"] = len(claims)
    return claims, conflicts, stats


def _resolution_conflict_key(item: dict[str, Any]) -> tuple[Any, ...]:
    return (
        item.get("Reason"),
        item.get("Season"),
        item.get("SleeperID"),
        item.get("Tank01ID"),
        item.get("ESPNID"),
        item.get("EvidenceSource"),
        tuple(
            sorted(
                (str(provider), str(player_id))
                for provider, player_id in (item.get("ResolvedByProvider") or {}).items()
            )
        ),
    )


def extend_provider_mapping_payload(
    payload: dict[str, Any],
    claims: list[dict[str, Any]],
    resolution_conflicts: list[dict[str, Any]],
) -> dict[str, Any]:
    payload = normalize_legacy_canonical_player_fields(payload)
    mappings = [dict(item) for item in payload.get("Mappings", [])]
    conflicts = [dict(item) for item in payload.get("Conflicts", [])]

    # Historical replay can contain hundreds of thousands of claims. Only the
    # same provider token can overlap or touch a claim's validity interval.
    mappings_by_token: dict[tuple[str, str], list[dict[str, Any]]] = {}
    conflicts_by_token: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for item in mappings:
        token = (item.get("Provider"), str(item.get("ExternalID")))
        mappings_by_token.setdefault(token, []).append(item)
    for item in conflicts:
        token = (item.get("Provider"), str(item.get("ExternalID")))
        conflicts_by_token.setdefault(token, []).append(item)

    def interval(item: dict[str, Any], default_season: int) -> tuple[int, int]:
        first = int(item.get("FirstObservedSeason") or default_season)
        last = int(item.get("LastObservedSeason") or first)
        return first, last

    for claim in sorted(
        claims,
        key=lambda item: (
            int(item["ObservedSeason"]),
            item["Provider"],
            item["ExternalID"],
            item["CanonicalPlayerID"],
        ),
    ):
        provider = claim["Provider"]
        external_id = claim["ExternalID"]
        internal_id = claim["CanonicalPlayerID"]
        season = int(claim["ObservedSeason"])
        sources = set(claim.get("Sources") or [])
        token = (provider, str(external_id))
        token_mappings = mappings_by_token.setdefault(token, [])
        token_conflicts = conflicts_by_token.setdefault(token, [])

        active_conflict = False
        for conflict in token_conflicts:
            first, last = interval(conflict, season)
            if first <= season <= last:
                active_conflict = True
                break
        if active_conflict:
            continue

        # A historical observation may only bridge contiguous seasons. Do not
        # widen an exact mapping across an unobserved gap merely because the
        # current snapshot has the same provider token. First reject any
        # different-owner mapping that is already valid for this season.
        overlaps = []
        for item in token_mappings:
            if item.get("CanonicalPlayerID") == internal_id:
                continue
            first, last = interval(item, season)
            if first <= season <= last:
                overlaps.append(item)
        if overlaps:
            owners = sorted({internal_id, *(str(item.get("CanonicalPlayerID")) for item in overlaps)})
            token_conflicts.append(
                {
                    "Provider": provider,
                    "ExternalID": external_id,
                    "CanonicalPlayerIDs": owners,
                    "FirstObservedSeason": season,
                    "LastObservedSeason": season,
                    "Status": "ambiguous",
                    "Reason": "historical_mapping_overlap",
                    "SourcesByCanonicalPlayerID": {internal_id: sorted(sources)},
                }
            )
            continue

        touching = []
        for item in token_mappings:
            if item.get("CanonicalPlayerID") != internal_id:
                continue
            first, last = interval(item, season)
            if first - 1 <= season <= last + 1:
                touching.append(item)

        if touching:
            primary = touching[0]
            first_values = [interval(item, season)[0] for item in touching]
            last_values = [interval(item, season)[1] for item in touching]
            primary["FirstObservedSeason"] = min([season, *first_values])
            primary["LastObservedSeason"] = max([season, *last_values])
            merged_sources = set(sources)
            for item in touching:
                merged_sources.update(item.get("Sources") or [])
            primary["Sources"] = sorted(merged_sources)
            for item in touching[1:]:
                token_mappings.remove(item)
            continue

        token_mappings.append(
            {
                "Provider": provider,
                "ExternalID": external_id,
                "CanonicalPlayerID": internal_id,
                "FirstObservedSeason": season,
                "LastObservedSeason": season,
                "Sources": sorted(sources),
            }
        )

    # Provider disagreements in one historical evidence snapshot are evidence
    # conflicts, not safe provider mappings. Keep them separately without
    # inventing a winner.
    history_resolution_conflicts = [
        dict(item) for item in payload.get("HistoricalResolutionConflicts", [])
    ]
    known = {_resolution_conflict_key(item) for item in history_resolution_conflicts}
    for conflict in resolution_conflicts:
        key = _resolution_conflict_key(conflict)
        if key not in known:
            history_resolution_conflicts.append(conflict)
            known.add(key)

    mappings = [item for bucket in mappings_by_token.values() for item in bucket]
    conflicts = [item for bucket in conflicts_by_token.values() for item in bucket]
    mappings.sort(
        key=lambda item: (
            item["Provider"],
            str(item["ExternalID"]),
            int(item["FirstObservedSeason"]),
            item["CanonicalPlayerID"],
        )
    )
    conflicts.sort(
        key=lambda item: (
            item["Provider"],
            str(item["ExternalID"]),
            int(item["FirstObservedSeason"]),
            tuple(item["CanonicalPlayerIDs"]),
        )
    )
    history_resolution_conflicts.sort(
        key=lambda item: (
            int(item.get("Season") or 0),
            str(item.get("Reason") or ""),
            str(item.get("SleeperID") or ""),
            str(item.get("EvidenceSource") or ""),
        )
    )
    return {
        **payload,
        "Mappings": mappings,
        "Conflicts": conflicts,
        "HistoricalResolutionConflicts": history_resolution_conflicts,
    }
