#!/usr/bin/env python3
"""Load the inputs of the LeagueTransactions / LeagueDrafts materialization from canonical sources.

Reads only data-source/leagues/<CanonicalLeagueID>/**, data-meta/<CanonicalLeagueID>/metadata.json and the
hand-maintained manual overlay. The Standings placement for configured draft orders comes from the
league-standings product, built in memory (Issue #987 step 4); it is only loaded when a draft needs it.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from data_roots import DATA_SOURCE_ROOT  # noqa: E402
from derived_data_lib.league_history import LeagueHistoryInputs  # noqa: E402
from draft_canonical_consumer import build_legacy_payload  # noqa: E402
from league_metadata import data_meta_root, load_league_metadata  # noqa: E402
from transaction_canonical_consumer import build_repo_canonical_transactions  # noqa: E402
from transaction_canonical_shadow import build_roster_provider_lookup, load_json, manual_overlay_path  # noqa: E402



class LeagueHistorySourceError(ValueError):
    """Raised when canonical sources needed for the league history are missing or inconsistent."""


def _manifest(repo_root: Path, league_id: str) -> dict[str, Any]:
    path = repo_root / DATA_SOURCE_ROOT / "leagues" / league_id / "manifest.json"
    if not path.is_file():
        raise LeagueHistorySourceError(f"League manifest missing: {path}")
    return load_json(path)


def _provider_league_id(entry: dict[str, Any]) -> str:
    ids = [m["ProviderLeagueID"] for m in entry.get("ProviderMappings") or [] if m.get("Provider") == "Sleeper"]
    if len(ids) != 1:
        raise LeagueHistorySourceError(f"Season {entry.get('Season')} needs exactly one Sleeper ProviderLeagueID; found {len(ids)}")
    return str(ids[0])


def load_manual_overlay(repo_root: Path, league_id: str) -> list[dict[str, Any]]:
    path = manual_overlay_path(repo_root, league_id)
    if not path.is_file():
        raise LeagueHistorySourceError(f"Manual transaction overlay missing: {path}")
    payload = load_json(path)
    if payload is None:
        return []
    return payload if isinstance(payload, list) else [payload]


def make_standings_loader(repo_root: Path, league_id: str, league_year: int):
    """Draft-order input from the league-standings product (ADR-072, Issue #987 step 4).

    The product is built in memory from canonical facts, so the draft order depends neither on a published
    App file nor on a previously generated product file.
    """
    def load() -> list[dict[str, Any]]:
        # Lazy imports: derived_data imports this module.
        from derived_data import build_league_standings
        from league_standings_app_publish import render_standings
        return render_standings(build_league_standings(repo_root, league_id), league_year)
    return load


def load_inputs(repo_root: Path, league_id: str) -> LeagueHistoryInputs:
    manifest = _manifest(repo_root, league_id)
    metadata = load_league_metadata(league_id, data_meta_root(repo_root))
    drafts_config = metadata.get("Drafts") or {}
    if str(drafts_config.get("UpcomingDraftCountMode") or "PerDraftType") != "PerDraftType":
        raise LeagueHistorySourceError(f"Unsupported UpcomingDraftCountMode '{drafts_config.get('UpcomingDraftCountMode')}'. Only 'PerDraftType' is supported.")
    open_count = int(drafts_config.get("UpcomingDraftCount") or 0)
    if open_count < 1:
        raise LeagueHistorySourceError("UpcomingDraftCount must be at least 1.")
    types = list(drafts_config.get("Types") or [])
    if not types:
        raise LeagueHistorySourceError("No draft types configured in the league metadata (data-meta).")

    entries = sorted(manifest.get("Seasons") or [], key=lambda item: int(item["Season"]))
    seasons = [int(item["Season"]) for item in entries]
    league_year = int(str(manifest["CurrentCanonicalLeagueSeasonID"]).rsplit("-", 1)[-1])
    canonical_transactions: dict[int, list[dict[str, Any]]] = {}
    payloads: dict[int, dict[str, Any]] = {}
    for season in seasons:
        canonical_transactions[season] = build_repo_canonical_transactions(repo_root, canonical_league_id=league_id, season=season)
        payloads[season] = build_legacy_payload(repo_root, league_id, str(season))

    current_rosters = load_json(repo_root / DATA_SOURCE_ROOT / "leagues" / league_id / "seasons" / str(league_year) / "rosters.json")
    team_ids = sorted(build_roster_provider_lookup(current_rosters).values())

    return LeagueHistoryInputs(
        league_id=league_id,
        league_year=league_year,
        seasons=seasons,
        provider_league_ids={int(item["Season"]): _provider_league_id(item) for item in entries},
        draft_configs=types,
        open_draft_count=open_count,
        owners={str(name): int(value) for name, value in (metadata.get("Owners") or {}).items()},
        canonical_transactions=canonical_transactions,
        payloads=payloads,
        manual_rows=load_manual_overlay(repo_root, league_id),
        team_ids=team_ids,
        standings_loader=make_standings_loader(repo_root, league_id, league_year),
    )
