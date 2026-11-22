#!/usr/bin/env python3
"""Compact nflverse ``pbp_participation`` Source projection (Issue #1612, CP4).

Positive on-field participation evidence per season/game/CanonicalPlayerID. Only
a compact projection is retained (``<data-source>/nfl/participation/<season>.json``);
the upstream CSV (CC BY-SA 4.0, 20-50 MB per season) is never stored and no
Release asset is created. Evidence rule: a player is positively observed in a
play when its GSIS id appears in ``offense_players`` or ``defense_players``
(real GSIS in all seasons; ``players_on_play`` is numeric before 2023 and is not
used). ``Plays`` counts distinct plays. Absence from this dataset is NEVER
evidence of not playing. Play types (for example ``no_play``) are not part of
the upstream file, so the interpretation threshold belongs to the consumer.

Accepted seasons are frozen: an upstream revision is reported for review and
never overwrites the stored projection. Runs inside the existing full NFL Source
job (fail-soft), no new workflow, writer, permission or schedule.
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import io
import json
import os
import re
import sys
import tempfile
import urllib.error
from pathlib import Path
from typing import Any, Iterable

from data_roots import DATA_SOURCE_ROOT
from nfl_source_data_lib.common import current_source_season, download, load_json, write_json_if_changed
from nfl_pbp_source_auto import api_json

SOURCE_REPOSITORY = "nflverse/nflverse-data"
RELEASE_TAG = "pbp_participation"
FIRST_SEASON = 2016
MAX_NEW_SEASONS_PER_RUN = 3
OUTPUT_DIR = Path(DATA_SOURCE_ROOT) / "nfl" / "participation"
GSIS = re.compile(r"^00-\d{7}$")
SHA = re.compile(r"^sha256:([0-9a-f]{64})$")
REQUIRED_COLUMNS = {"nflverse_game_id", "play_id", "offense_players", "defense_players"}
LICENSE = "CC BY-SA 4.0"

csv.field_size_limit(10**9)


def attribution(season: int) -> str:
    return "FTN Data via nflverse" if season >= 2023 else "NFL NextGenStats via nflverse"


def gsis_owners(identities: dict[str, Any]) -> dict[str, set[str]]:
    owners: dict[str, set[str]] = collections.defaultdict(set)
    for player in identities.get("Players") or []:
        ids = player.get("IDs") or {}
        aliases = (player.get("IDAliases") or {}).get("GSIS") or []
        for gsis in [ids.get("GSIS"), *aliases]:
            if gsis:
                owners[gsis].add(player["CanonicalPlayerID"])
    return owners


def build_projection(
    csv_text: str, season: int, schedule_game_ids: Iterable[str],
    owners: dict[str, set[str]],
) -> dict[str, Any]:
    """Pure projection of one season file; fails closed on structural defects."""
    reader = csv.DictReader(io.StringIO(csv_text))
    missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
    if missing:
        raise ValueError(f"Participation columns missing: {sorted(missing)}")
    schedule = set(schedule_game_ids)
    seen_plays: set[tuple[str, str]] = set()
    per_game: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    rows = duplicate_rows = empty_rows = malformed = 0
    unresolved: set[str] = set()
    ambiguous: set[str] = set()
    games_seen: set[str] = set()
    for row in reader:
        rows += 1
        game, play = row["nflverse_game_id"], row["play_id"]
        games_seen.add(game)
        if (game, play) in seen_plays:
            duplicate_rows += 1
            continue
        seen_plays.add((game, play))
        players: set[str] = set()
        for column in ("offense_players", "defense_players"):
            for token in filter(None, row[column].split(";")):
                if GSIS.match(token):
                    players.add(token)
                else:
                    malformed += 1
        if not players:
            empty_rows += 1
            continue
        for gsis in players:
            canonical = owners.get(gsis, set())
            if len(canonical) == 1:
                per_game[game][next(iter(canonical))] += 1
            elif canonical:
                ambiguous.add(gsis)
            else:
                unresolved.add(gsis)
    if not rows or not games_seen:
        raise ValueError("Participation season file is empty")
    outside = sorted(games_seen - schedule)
    if outside:
        raise ValueError(f"Participation games not in canonical schedule: {outside[:5]}")
    return {
        "Audit": {
            "SourceRows": rows,
            "DuplicateGamePlayRows": duplicate_rows,
            "RowsWithoutPlayers": empty_rows,
            "MalformedGsisTokens": malformed,
            "GamesObserved": len(games_seen),
            "ScheduleGames": len(schedule),
            "ScheduleGamesWithoutParticipation": len(schedule - games_seen),
            "UnresolvedGsisIds": len(unresolved),
            "AmbiguousGsisIds": len(ambiguous),
        },
        "Games": [
            {"GameID": game, "Players": dict(sorted(counter.items()))}
            for game, counter in sorted(per_game.items())
        ],
    }


def upstream_assets(token: str) -> dict[str, dict[str, Any]]:
    release = api_json(
        f"https://api.github.com/repos/{SOURCE_REPOSITORY}/releases/tags/{RELEASE_TAG}", token,
    )
    if not isinstance(release, dict) or type(release.get("id")) is not int:
        raise ValueError("Official nflverse participation release identity unavailable")
    found: dict[str, dict[str, Any]] = {}
    for page in range(1, 21):
        assets = api_json(
            f"https://api.github.com/repos/{SOURCE_REPOSITORY}/releases/"
            f"{release['id']}/assets?per_page=100&page={page}", token,
        )
        if not isinstance(assets, list):
            raise ValueError("Official participation asset inventory malformed")
        for asset in assets:
            found[str(asset.get("name"))] = asset
        if len(assets) < 100:
            break
    else:
        raise ValueError("Official participation asset pagination exceeded")
    return found


def _trusted(asset: dict[str, Any], season: int) -> tuple[str, str]:
    name = f"pbp_participation_{season}.csv"
    url = f"https://github.com/{SOURCE_REPOSITORY}/releases/download/{RELEASE_TAG}/{name}"
    if (type(asset.get("size")) is not int or asset["size"] <= 0
            or asset.get("browser_download_url") != url or asset.get("state") != "uploaded"):
        raise ValueError(f"Official participation asset lacks trusted identity: {season}")
    digest = asset.get("digest")
    if isinstance(digest, str) and SHA.fullmatch(digest):
        return url, SHA.fullmatch(digest).group(1)
    return url, ""


def run(root: Path, token: str, *, limit: int = MAX_NEW_SEASONS_PER_RUN) -> dict[str, Any]:
    current = current_source_season(root)
    out_dir = root / OUTPUT_DIR
    assets = upstream_assets(token)
    owners = gsis_owners(load_json(root / DATA_SOURCE_ROOT / "nfl/identities/players.json", {}) or {})
    if not owners:
        raise ValueError("Canonical identities unavailable for participation projection")
    report: dict[str, Any] = {"Accepted": [], "Unavailable": [], "ReviewNotices": [], "Blocked": []}
    new_budget = limit
    for season in range(FIRST_SEASON, current + 1):
        path = out_dir / f"{season}.json"
        stored = load_json(path)
        asset = assets.get(f"pbp_participation_{season}.csv")
        if asset is None:
            if stored is None:
                report["Unavailable"].append(season)
            continue
        try:
            url, digest = _trusted(asset, season)
            if stored is not None:
                src = stored.get("Source") or {}
                if (digest and src.get("SHA256") != digest) or src.get("Bytes") != asset["size"]:
                    report["ReviewNotices"].append(season)  # frozen, never overwritten
                continue
            if new_budget <= 0:
                continue
            schedule = load_json(root / DATA_SOURCE_ROOT / "nfl" / "schedules" / f"{season}.json")
            if not schedule:
                raise ValueError("Canonical schedule missing")
            with tempfile.TemporaryDirectory(prefix=f"nfl-participation-{season}-") as tmp:
                target = Path(tmp) / "participation.csv"
                download(url, target)
                raw = target.read_bytes()
            sha = hashlib.sha256(raw).hexdigest()
            if len(raw) != asset["size"] or (digest and sha != digest):
                raise ValueError("Participation download does not match official size/SHA256")
            projection = build_projection(
                raw.decode("utf-8-sig"), season, [g["GameID"] for g in schedule["Games"]], owners,
            )
            document = {
                "SchemaVersion": 1,
                "Dataset": "nflverse.participation",
                "Season": season,
                "Status": "accepted-compact-projection",
                "Source": {
                    "URL": url,
                    "AssetID": asset.get("id"),
                    "AssetUpdatedAtUtc": asset.get("updated_at"),
                    "SHA256": sha,
                    "DigestSource": "official-asset-digest" if digest else "self-sha256",
                    "Bytes": len(raw),
                    "License": LICENSE,
                    "Attribution": attribution(season),
                    "RawRetained": False,
                },
                "Rule": (
                    "Positive evidence only: GSIS in offense_players or defense_players; Plays = distinct "
                    "plays containing the player. Absence is not evidence of not playing; play types are "
                    "not part of the source."
                ),
                **projection,
            }
            write_json_if_changed(path, document)
            report["Accepted"].append(season)
            new_budget -= 1
        except (OSError, ValueError, KeyError, UnicodeDecodeError, urllib.error.URLError) as exc:
            report["Blocked"].append({"Season": season, "Reason": str(exc)})
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--limit", type=int, default=MAX_NEW_SEASONS_PER_RUN)
    args = parser.parse_args()
    try:
        report = run(args.repo_root.resolve(), os.environ.get("PBP_ARCHIVE_TOKEN", ""), limit=args.limit)
    except (OSError, ValueError, KeyError, TypeError, urllib.error.URLError, json.JSONDecodeError) as exc:
        print(f"nfl_participation_source failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 1 if report["Blocked"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
