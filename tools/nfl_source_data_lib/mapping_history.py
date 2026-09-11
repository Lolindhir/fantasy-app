from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

from .canonical_identity import identity_lookup
from .common import clean, load_json, normalize_legacy_canonical_player_fields

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

    claims = _dedupe_claims(claims)
    stats["historicalClaimCount"] = len(claims)
    return claims, conflicts, stats


def extend_provider_mapping_payload(
    payload: dict[str, Any],
    claims: list[dict[str, Any]],
    resolution_conflicts: list[dict[str, Any]],
) -> dict[str, Any]:
    payload = normalize_legacy_canonical_player_fields(payload)
    mappings = [dict(item) for item in payload.get("Mappings", [])]
    conflicts = [dict(item) for item in payload.get("Conflicts", [])]

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

        active_conflict = False
        for conflict in conflicts:
            if conflict.get("Provider") != provider or str(conflict.get("ExternalID")) != str(external_id):
                continue
            first, last = interval(conflict, season)
            if first <= season <= last:
                active_conflict = True
                break
        if active_conflict:
            continue

        exact = next(
            (
                item
                for item in mappings
                if item.get("Provider") == provider
                and str(item.get("ExternalID")) == str(external_id)
                and item.get("CanonicalPlayerID") == internal_id
            ),
            None,
        )
        if exact is not None:
            first, last = interval(exact, season)
            exact["FirstObservedSeason"] = min(first, season)
            exact["LastObservedSeason"] = max(last, season)
            exact["Sources"] = sorted(set(exact.get("Sources") or []) | sources)
            continue

        overlaps = []
        for item in mappings:
            if item.get("Provider") != provider or str(item.get("ExternalID")) != str(external_id):
                continue
            first, last = interval(item, season)
            if first <= season <= last:
                overlaps.append(item)
        if overlaps:
            owners = sorted({internal_id, *(str(item.get("CanonicalPlayerID")) for item in overlaps)})
            conflicts.append(
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

        mappings.append(
            {
                "Provider": provider,
                "ExternalID": external_id,
                "CanonicalPlayerID": internal_id,
                "FirstObservedSeason": season,
                "LastObservedSeason": season,
                "Sources": sorted(sources),
            }
        )

    # Provider disagreements in one archived app snapshot are evidence conflicts,
    # not safe provider mappings. Keep them separately without inventing a winner.
    history_resolution_conflicts = [dict(item) for item in payload.get("HistoricalResolutionConflicts", [])]
    known = {
        (
            item.get("Reason"),
            item.get("Season"),
            item.get("SleeperID"),
            item.get("Tank01ID"),
            item.get("ESPNID"),
        )
        for item in history_resolution_conflicts
    }
    for conflict in resolution_conflicts:
        key = (
            conflict.get("Reason"),
            conflict.get("Season"),
            conflict.get("SleeperID"),
            conflict.get("Tank01ID"),
            conflict.get("ESPNID"),
        )
        if key not in known:
            history_resolution_conflicts.append(conflict)
            known.add(key)

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
            str(item.get("SleeperID") or ""),
            str(item.get("Tank01ID") or ""),
            str(item.get("ESPNID") or ""),
        )
    )
    return {
        **payload,
        "Mappings": mappings,
        "Conflicts": conflicts,
        "HistoricalResolutionConflicts": history_resolution_conflicts,
    }
