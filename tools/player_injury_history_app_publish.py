#!/usr/bin/env python3
"""Consumer generator: renders public/data/PlayerInjuryHistory.json from the persisted nfl-player-availability product (Issue #1590).

Pure reshaping, no derivation: every season document of data-derived/nfl-player-availability is regrouped per player. Only players
of the shared Fantasy population rule (the Players file population, built from canonical facts, never read from the published file) are published; the join is Sleeper ID -> CanonicalPlayerID through the canonical identity index.
The current injury status stays with the Players file (Sleeper) and is not part of this file.

Usage:
  player_injury_history_app_publish.py write [--fail-on-error]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from data_roots import DATA_DERIVED_ROOT, DATA_SOURCE_ROOT  # noqa: E402
from derived_data_lib.nfl_player_availability import PRODUCT, PRODUCT_VERSION, RESERVE_STATUSES  # noqa: E402
from league_metadata import data_meta_root, default_league_id  # noqa: E402
from league_standings_sources import current_season, manifest  # noqa: E402
from app_delivery import Writer, load_json, warn  # noqa: E402
from matchup_context import diff_values  # noqa: E402
from players_population import PopulationError, build_population  # noqa: E402

CONTRACT_VERSION = 1
APP_FILE = "PlayerInjuryHistory.json"
TIMESTAMP_KEY = "PlayerInjuryHistory"


class CompactWriter(Writer):
    """Writer with compact JSON: the file holds one row per reported or reserve player-week and is loaded lazily."""

    def put(self, relative: str, payload: Any, timestamp_key: str | None = None) -> None:
        path = self.data / relative
        if path.is_file() and not diff_values(load_json(path), json.loads(json.dumps(payload))):
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
        self.changed.append(f"public/data/{relative}")
        if timestamp_key:
            self._stamped.append(timestamp_key)


class InjuryHistoryError(ValueError):
    """Raised when an input cannot be used safely."""


def sleeper_to_canonical(identity_payload: dict[str, Any]) -> dict[str, str]:
    rows = identity_payload.get("Players")
    if not isinstance(rows, list):
        raise InjuryHistoryError("canonical identity document must contain a Players array")
    bridge: dict[str, str] = {}
    for row in rows:
        sleeper = (row.get("IDs") or {}).get("Sleeper")
        if not sleeper:
            continue
        canonical = row.get("CanonicalPlayerID")
        if bridge.get(str(sleeper), canonical) != canonical:
            raise InjuryHistoryError(f"Sleeper ID {sleeper} maps to more than one CanonicalPlayerID")
        bridge[str(sleeper)] = canonical
    return bridge


def league_week_caps(repo_root: Path, league_id: str) -> dict[int, int]:
    """Last fantasy-relevant NFL week per season from the WeekStructure of ONE league (FinalLeagueWeek, else ExpectedLastLeagueWeek).

    The league is the one whose population selects the players (same scope as population_players), so the week cap and the
    player set always belong to the same league (Issue #1590 follow-up). Seasons beyond the last known league season take
    its value; without league data no cap applies (all regular-season weeks stay).
    """
    caps: dict[int, int] = {}
    for path in sorted((repo_root / DATA_SOURCE_ROOT / "leagues" / league_id / "seasons").glob("*/league.json")):
        if not path.parent.name.isdigit():
            continue
        structure = load_json(path).get("WeekStructure") or {}
        last = structure.get("FinalLeagueWeek") or structure.get("ExpectedLastLeagueWeek")
        if isinstance(last, int):
            season = int(path.parent.name)
            caps[season] = max(caps.get(season, 0), last)
    return caps


def _cap_for(season: int, caps: dict[int, int]) -> int | None:
    if not caps:
        return None
    if season in caps:
        return caps[season]
    return caps[max(caps)] if season > max(caps) else None


def _entry(record: dict[str, Any]) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "Week": record["Week"],
        "GameType": record["GameType"],
        "Team": record["Team"],
        "State": record["State"],
        "Participation": record["Participation"]["State"],
        "Report": record["Report"],
        "Roster": record["Roster"],
    }
    return entry


def build_document(
    seasons: dict[int, dict[str, Any]],
    players: list[dict[str, Any]],
    bridge: dict[str, str],
    week_caps: dict[int, int] | None = None,
) -> dict[str, Any]:
    wanted: dict[str, str] = {}
    for player in players:
        sleeper = str(player.get("ID") or "")
        canonical = bridge.get(sleeper)
        if canonical:
            wanted[canonical] = sleeper
    per_player: dict[str, dict[int, list[dict[str, Any]]]] = {}
    for season, document in sorted(seasons.items()):
        if document.get("ProductVersion") != PRODUCT_VERSION or document.get("Season") != season:
            raise InjuryHistoryError(f"unsupported {PRODUCT} document for season {season}")
        cap = _cap_for(season, week_caps or {})
        if week_caps and cap is None:
            continue  # only league seasons are shown; the product keeps every season
        for record in document.get("Records", []):
            # Only fantasy-relevant weeks: regular season up to the league's last week (the product keeps every NFL week).
            if record.get("GameType") != "REG" or (cap is not None and record["Week"] > cap):
                continue
            # v2 adds healthy roster weeks (the denominator); the App file keeps showing only weeks with a signal (report or reserve).
            if record["Report"] is None and (record["Roster"] or {}).get("Status") not in RESERVE_STATUSES:
                continue
            sleeper = wanted.get(record["CanonicalPlayerID"])
            if sleeper is not None:
                per_player.setdefault(sleeper, {}).setdefault(season, []).append(_entry(record))
    out_players = [
        {
            "ID": sleeper,
            "Seasons": [{"Season": s, "Weeks": sorted(w, key=lambda e: (e["Week"], e["GameType"] or ""))} for s, w in sorted(by_season.items())],
        }
        for sleeper, by_season in sorted(per_player.items())
    ]
    coverage = [
        {
            "Season": season,
            "ReportsAvailable": document["Inputs"]["InjuryProduct"] is not None,
            "RosterStatusAvailable": document["Inputs"]["RosterStatusAvailable"],
            "SnapCountsAvailable": document["Inputs"]["SnapCountsAvailable"],
        }
        for season, document in sorted(seasons.items())
        if not week_caps or _cap_for(season, week_caps) is not None
    ]
    return {
        "ContractVersion": CONTRACT_VERSION,
        "Product": PRODUCT_VERSION,
        "Coverage": coverage,
        "Players": out_players,
    }


def population_players(repo_root: Path) -> list[dict[str, Any]]:
    """Players of the shared Fantasy population rule (tools/players_population.py, ADR-043) for the default league's current season.

    This is the same league scope and rule that define the Players file population (Players.json is built for the default
    league only), applied directly to canonical facts so the published Players file is not an input of this Shared-Derived-based rendering (Issue #1263, finding F4).
    """
    players: dict[str, dict[str, Any]] = {}
    for league_id in [default_league_id(data_meta_root(repo_root))]:
        season = current_season(manifest(repo_root, league_id))
        try:
            population = build_population(repo_root, league_id, season)
        except PopulationError as error:
            raise InjuryHistoryError(f"population unavailable for {league_id}/{season}: {error}") from error
        for entry in population["Players"]:
            players.setdefault(str(entry["SleeperID"]), {"ID": str(entry["SleeperID"])})
    return list(players.values())


def publish(repo_root: Path, writer: Writer) -> None:
    root = repo_root / DATA_DERIVED_ROOT / PRODUCT
    seasons = {int(p.stem): load_json(p) for p in sorted(root.glob("*.json")) if p.stem.isdigit()} if root.is_dir() else {}
    if not seasons:
        raise InjuryHistoryError(f"{PRODUCT} product is not materialized")
    league_id = default_league_id(data_meta_root(repo_root))
    players = population_players(repo_root)
    bridge = sleeper_to_canonical(load_json(repo_root / DATA_SOURCE_ROOT / "nfl" / "identities" / "players.json"))
    writer.put(APP_FILE, build_document(seasons, players, bridge, league_week_caps(repo_root, league_id)), TIMESTAMP_KEY)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    sub = parser.add_subparsers(dest="command", required=True)
    write = sub.add_parser("write", help="render the App file from the persisted product (semantic no-op)")
    write.add_argument("--fail-on-error", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    writer = CompactWriter(args.repo_root, datetime.now(timezone.utc))
    try:
        publish(args.repo_root, writer)
    except (InjuryHistoryError, OSError, json.JSONDecodeError) as error:
        warn("PlayerInjuryHistory not published", f"{type(error).__name__}: {error}")
        writer.finish()
        return 1 if args.fail_on_error else 0
    changed = writer.finish()
    print("\n".join(f"wrote {name}" for name in changed) if changed else "No changes - update skipped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
