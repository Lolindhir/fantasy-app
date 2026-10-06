#!/usr/bin/env python3
"""Synchronize the ESPN player injury status into the shared NFL source layer (#347).

ESPN ``kona_player_info`` is a provider observation of the current NFL injury status
per player. It is consumer-neutral and independent of any fantasy roster, so the
snapshot covers every player ESPN returns. Output:

* ``source-data/nfl/player-availability/espn.json`` (canonical, keyed by ESPN player ID)
* ``source-data/providers/espn/player-availability/metadata.json`` (provenance)

Rules: a run writes only when the semantic content changed (no-op otherwise);
``StatusSinceUtc`` stays stable while a player's provider status is unchanged; a
failed or implausibly small response leaves the last known good snapshot untouched
and exits non-zero. Player identity mapping (ESPN ID -> Sleeper/Canonical) stays with
the canonical identity layer and is not done here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from nfl_source_data_lib.common import current_source_season, load_json, write_json_if_changed

REPO_ROOT = Path(__file__).resolve().parents[1]
DATASET_ID = "espn.player-availability"
SNAPSHOT_PATH = Path("source-data/nfl/player-availability/espn.json")
METADATA_PATH = Path("source-data/providers/espn/player-availability/metadata.json")
SOURCE_URL_TEMPLATE = (
    "https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{season}"
    "/segments/0/leaguedefaults/3?view=kona_player_info"
)
SCHEMA_VERSION = 1
PLAYER_LIMIT = 3000
MINIMUM_PLAYERS = 300
REQUEST_FILTER = {
    "players": {
        "filterStatus": {"value": ["FREEAGENT", "WAIVERS", "ONTEAM"]},
        "sortPercOwned": {"sortPriority": 1, "sortAsc": False},
        "limit": PLAYER_LIMIT,
    }
}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_payload(season: int, timeout: int = 120) -> Any:
    request = urllib.request.Request(
        SOURCE_URL_TEMPLATE.format(season=season),
        headers={
            "Accept": "application/json",
            "X-Fantasy-Filter": json.dumps(REQUEST_FILTER, separators=(",", ":")),
            "User-Agent": "Lolindhir-fantasy-app-espn-player-availability/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def parse_players(payload: Any) -> dict[str, str | None]:
    """ESPN player ID -> upper-cased provider injury status (None when absent)."""
    entries = payload.get("players") if isinstance(payload, dict) else None
    if not isinstance(entries, list):
        raise ValueError("ESPN response has no players list")
    result: dict[str, str | None] = {}
    for entry in entries:
        player = entry.get("player") if isinstance(entry, dict) and isinstance(entry.get("player"), dict) else entry
        if not isinstance(player, dict):
            continue
        espn_id = str(player.get("id", entry.get("id") if isinstance(entry, dict) else "")).strip()
        if not espn_id or espn_id == "0":
            continue
        status = str(player.get("injuryStatus") or "").strip().upper() or None
        if espn_id in result and result[espn_id] != status:
            raise ValueError(f"ESPN response has conflicting duplicate player {espn_id}")
        result[espn_id] = status
    return result


def build_snapshot(
    season: int,
    observed: dict[str, str | None],
    previous: Any,
    observed_at: str,
    minimum_players: int = MINIMUM_PLAYERS,
) -> dict[str, Any]:
    if len(observed) < minimum_players:
        raise ValueError(f"ESPN response too small: {len(observed)} players (minimum {minimum_players})")
    since: dict[str, tuple[str | None, str]] = {}
    if isinstance(previous, dict) and previous.get("Season") == season:
        for row in previous.get("Players") or []:
            since[str(row["ESPNPlayerID"])] = (row.get("ProviderStatus"), row["StatusSinceUtc"])
    players = []
    for espn_id in sorted(observed, key=lambda value: (len(value), value)):
        status = observed[espn_id]
        prior = since.get(espn_id)
        players.append({
            "ESPNPlayerID": espn_id,
            "ProviderStatus": status,
            "StatusSinceUtc": prior[1] if prior and prior[0] == status else observed_at,
        })
    return {
        "SchemaVersion": SCHEMA_VERSION,
        "SourceDataset": DATASET_ID,
        "Source": "ESPN",
        "Season": season,
        "Players": players,
    }


def metadata_for(snapshot: dict[str, Any], season: int) -> dict[str, Any]:
    rendered = json.dumps(snapshot, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return {
        "SchemaVersion": SCHEMA_VERSION,
        "SourceDataset": DATASET_ID,
        "Provider": "ESPN",
        "SourceUrl": SOURCE_URL_TEMPLATE.format(season=season),
        "Season": season,
        "PlayerCount": len(snapshot["Players"]),
        "ContentSha256": hashlib.sha256(rendered).hexdigest(),
        "Note": "Updated only when the snapshot content changes; the raw provider response is not retained.",
    }


def sync(repo_root: Path, season: int, payload: Any, observed_at: str) -> bool:
    previous = load_json(repo_root / SNAPSHOT_PATH, None)
    snapshot = build_snapshot(season, parse_players(payload), previous, observed_at)
    changed = write_json_if_changed(repo_root / SNAPSHOT_PATH, snapshot)
    if changed:
        write_json_if_changed(repo_root / METADATA_PATH, metadata_for(snapshot, season))
    return changed


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--season", type=int, help="defaults to the current canonical source season")
    args = parser.parse_args(list(argv) if argv is not None else None)
    season = args.season or current_source_season(args.repo_root)
    try:
        changed = sync(args.repo_root, season, fetch_payload(season), utc_now())
    except Exception as error:  # fail closed: keep the last known good snapshot
        print(f"ESPN player availability sync failed: {error}", file=sys.stderr)
        return 1
    print(f"ESPN player availability season {season}: {'updated' if changed else 'no semantic change'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
