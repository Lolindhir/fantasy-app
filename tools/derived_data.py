#!/usr/bin/env python3
"""Materializer for Shared Derived Data products (ADR-038, ADR-055).

First product: player-valuation (.ai-context/manual/player-valuation.yaml): Salary, SalaryProjected,
Ranking, rank Grading and the Salary Cap for every season of the league manifest and every
AsOfFinalScoredWeek, written to <derived root>/player-valuation/<CanonicalLeagueID>/<season>/week-<NN>.json.

The model per league and season comes from the league metadata (tools/league_metadata.py, ADR-054);
the model code lives in tools/derived_data_lib. A snapshot is rebuilt from canonical facts on every run
and written only on a semantic difference (a second run is a file-level no-op). Since the cutover
(Issue #919 step 5) RequestPlayers.ps1 runs it and fills Players.json / League.json from the snapshot.

Second product family: league-transactions and league-drafts (league-history.yaml, ADR-057, Issue #999),
written to <derived root>/league-transactions|league-drafts/<CanonicalLeagueID>/<season>.json. Both come
from one in-memory run in ADR-026 order (the transaction picks carry the draft pick results). The App consumer generator already publishes its own in-memory history
result; the additive CP2 PlayerRefs do not alter that App delivery until Issue #1100 CP3.
The optional --hold-seed-players-file explicitly reads the last published
public/data/Players.json, not a new canonical identity source.

Third product: league-standings (league-standings.yaml, ADR-072, Issue #987), one file per league and season at
<derived root>/league-standings/<CanonicalLeagueID>/<season>.json with the regular-season table, the weekly tables,
playoffs, awards and the all-time standing through that season. The seasons are chained (Most Improved, all-time) and
always rebuilt chronologically in one run; the models come from data-meta (standings-v1, awards-v1).

Usage:
  derived_data.py materialize --product player-valuation|league-transactions|league-drafts|league-standings [--league nfl-reise]
                              [--season 2026 ...] [--out-root DIR] [--check]
                              [--hold-seed-players-file PUBLISHED_PLAYERS_JSON]   (player-valuation only)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from data_roots import data_derived_dir  # noqa: E402
from derived_data_lib.player_valuation import MODEL_KINDS, SnapshotContext, build_snapshot  # noqa: E402
from league_metadata import (  # noqa: E402
    LeagueMetadataError,
    data_meta_root,
    list_league_ids,
    load_league_metadata,
    model_for,
    validate_against_manifest,
)
import player_valuation_sources as sources  # noqa: E402
from derived_data_lib.league_history import build_history, drafts_document, transactions_document  # noqa: E402
from league_history_sources import LeagueHistorySourceError, load_inputs  # noqa: E402
from derived_data_lib.league_standings import build_season  # noqa: E402
from derived_data_lib.models.registry import get_model  # noqa: E402
import league_standings_sources as standings_sources  # noqa: E402
from derived_data_lib.league_player_refs import LeaguePlayerReferenceResolver, provider_draft_names  # noqa: E402

LEAGUE_TRANSACTIONS = "league-transactions"
LEAGUE_DRAFTS = "league-drafts"
LEAGUE_STANDINGS = "league-standings"
PRODUCTS = (sources.PRODUCT, LEAGUE_TRANSACTIONS, LEAGUE_DRAFTS, LEAGUE_STANDINGS)
EXIT_CHANGED = 3  # --check found a snapshot that differs from disk


def snapshot_path(out_root: Path, league_id: str, season: int, week: int) -> Path:
    return out_root / sources.PRODUCT / league_id / str(season) / f"week-{week:02d}.json"


def serialize(snapshot: dict[str, Any]) -> str:
    """Deterministic compact JSON: fixed key order from the builder, no timestamps."""
    return json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")) + "\n"


class ExistingSnapshots:
    """Hold-row source: the persisted snapshot of the same week, else the newest earlier week of the season."""

    def __init__(self, out_root: Path, league_id: str, season: int) -> None:
        self._out_root, self._league_id, self._season = out_root, league_id, season
        self._cache: dict[int, dict[str, dict[str, Any]] | None] = {}

    def _inputs_by_key(self, week: int) -> dict[str, dict[str, Any]] | None:
        if week not in self._cache:
            path = snapshot_path(self._out_root, self._league_id, self._season, week)
            if path.is_file():
                payload = json.loads(path.read_text(encoding="utf-8"))
                self._cache[week] = {
                    (row["CanonicalPlayerID"] or row["PlayerID"]): row["Inputs"]
                    for row in payload["Players"] if row.get("Inputs") is not None
                }
            else:
                self._cache[week] = None
        return self._cache[week]

    def forget(self, week: int) -> None:
        self._cache.pop(week, None)

    def lookup_for(self, as_of: int):
        def lookup(key: str) -> tuple[dict[str, Any] | None, int | None]:
            for week in range(as_of, -1, -1):
                inputs = (self._inputs_by_key(week) or {}).get(key)
                if inputs is not None:
                    return inputs, week
            return None, None
        return lookup


def load_hold_seed(players_file: Path) -> dict[str, dict[str, Any]]:
    """Inputs of the last published Players.json by Sleeper player ID (cutover hold seed, Issue #919 step 5).

    Identity-hold players keep the last published scoring values. Once snapshots exist the persisted snapshot is
    the hold source; the published file only covers a hold that no snapshot knows yet (RequestPlayers.ps1 parity).
    """
    players = json.loads(players_file.read_text(encoding="utf-8"))
    seed: dict[str, dict[str, Any]] = {}
    for player in players:
        history = player.get("PointHistory") or {}
        try:
            inputs = {"Current": {
                "AvgPotentialGame": float(player["FantasyPointsAvgPotentialGame"]),
                "AvgGame": float(player["FantasyPointsAvgGame"]),
            }}
            for name in ("SeasonMinus1", "SeasonMinus2", "SeasonMinus3"):
                inputs[name] = {
                    "AvgPotentialGame": float(history[name]["AvgPotentialGame"]),
                    "AvgGame": float(history[name]["AvgGame"]),
                }
        except (KeyError, TypeError, ValueError):
            continue
        seed[str(player["ID"])] = inputs
    return seed


def materialize_player_valuation(
    repo_root: Path, out_root: Path, league_id: str, seasons: list[int] | None, check_only: bool,
    hold_seed: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    manifest = sources.league_manifest(repo_root, league_id)
    metadata = load_league_metadata(league_id, data_meta_root(repo_root))
    validate_against_manifest(metadata, manifest)
    available = sources.manifest_seasons(manifest)
    wanted = available if not seasons else sorted(set(seasons))
    unknown = [s for s in wanted if s not in available]
    if unknown:
        raise sources.SourceError(f"Seasons not in the league manifest: {unknown}; available: {available}")

    summary: dict[str, Any] = {"Product": sources.PRODUCT, "CanonicalLeagueID": league_id, "Seasons": []}
    for season in wanted:
        source = sources.load_season_source(repo_root, league_id, season, manifest)
        model_ids = {name: model_for(metadata, season, name) for name in MODEL_KINDS}
        existing = ExistingSnapshots(out_root, league_id, season)
        written = unchanged = total_bytes = held_rows = 0
        for as_of in range(0, source.final_scored_week + 1):
            context = SnapshotContext(
                league_id=league_id,
                season=season,
                as_of_final_scored_week=as_of,
                scoring_profile=source.scoring_profile,
                model_ids=model_ids,
                team_count=source.team_count,
                last_league_week=source.last_league_week,
                bye_weeks=source.bye_weeks,
            )
            lookup = existing.lookup_for(as_of)
            if hold_seed and season == available[-1] and as_of == source.final_scored_week:
                lookup = _with_seed(lookup, hold_seed, as_of)
            snapshot = build_snapshot(context, source.players, lookup)
            text = serialize(snapshot)
            total_bytes += len(text.encode("utf-8"))
            held_rows += sum(1 for row in snapshot["Players"] if row["Hold"] is not None)
            path = snapshot_path(out_root, league_id, season, as_of)
            if path.is_file() and path.read_text(encoding="utf-8") == text:
                unchanged += 1
                continue
            written += 1
            if not check_only:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")
                existing.forget(as_of)
        summary["Seasons"].append({
            **source.report,
            "Models": model_ids,
            "Snapshots": source.final_scored_week + 1,
            "Written" if not check_only else "WouldWrite": written,
            "Unchanged": unchanged,
            "Bytes": total_bytes,
            "HeldRowsAcrossSnapshots": held_rows,
        })
    return summary


def _with_seed(lookup, hold_seed: dict[str, dict[str, Any]], as_of: int):
    def seeded(key: str) -> tuple[dict[str, Any] | None, int | None]:
        inputs, week = lookup(key)
        if inputs is None and key in hold_seed:
            return hold_seed[key], as_of
        return inputs, week
    return seeded


def league_history_path(out_root: Path, product: str, league_id: str, season: int) -> Path:
    return out_root / product / league_id / f"{season}.json"


def league_transactions_path(out_root: Path, league_id: str, season: int) -> Path:
    return league_history_path(out_root, LEAGUE_TRANSACTIONS, league_id, season)


def materialize_league_history(
    repo_root: Path, out_root: Path, league_id: str, product: str, seasons: list[int] | None, check_only: bool,
) -> dict[str, Any]:
    inputs = load_inputs(repo_root, league_id)
    if seasons:
        unknown = [s for s in seasons if s not in inputs.seasons]
        if product == LEAGUE_TRANSACTIONS and unknown:
            raise sources.SourceError(f"Seasons not in the league manifest: {unknown}; available: {inputs.seasons}")
    history = build_history(inputs)
    if history.unresolved:
        raise sources.SourceError(f"Transaction picks without a unique draft identity: {history.unresolved}")
    documents: dict[int, tuple[dict[str, Any], int]] = {}
    resolver = LeaguePlayerReferenceResolver.from_repo(repo_root)
    if product == LEAGUE_TRANSACTIONS:
        for season in inputs.seasons:
            names = provider_draft_names(history.drafts.get(season, []))
            document = transactions_document(
                league_id, season, history.transactions[season], resolver.resolve, names
            )
            documents[season] = (document, len(document["Transactions"]))
    else:
        for season, drafts in sorted(history.drafts.items()):
            names = provider_draft_names(drafts)
            documents[season] = (
                drafts_document(league_id, season, drafts, resolver.resolve, names), len(drafts)
            )
    wanted = sorted(documents) if not seasons else [s for s in sorted(set(seasons)) if s in documents]
    summary: dict[str, Any] = {"Product": product, "CanonicalLeagueID": league_id, "Seasons": []}
    for season in wanted:
        document, count = documents[season]
        text = serialize(document)
        path = league_history_path(out_root, product, league_id, season)
        unchanged = path.is_file() and path.read_text(encoding="utf-8") == text
        if not unchanged and not check_only:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        summary["Seasons"].append({
            "Season": season,
            "Transactions" if product == LEAGUE_TRANSACTIONS else "Drafts": count,
            "Bytes": len(text.encode("utf-8")),
            "Unchanged": 1 if unchanged else 0,
            "Written" if not check_only else "WouldWrite": 0 if unchanged else 1,
        })
    return summary


def materialize_league_standings(
    repo_root: Path, out_root: Path, league_id: str, seasons: list[int] | None, check_only: bool,
) -> dict[str, Any]:
    manifest = standings_sources.manifest(repo_root, league_id)
    metadata = load_league_metadata(league_id, data_meta_root(repo_root))
    validate_against_manifest(metadata, manifest)
    available = standings_sources.manifest_seasons(manifest)
    unknown = [s for s in (seasons or []) if s not in available]
    if unknown:
        raise standings_sources.StandingsSourceError(f"Seasons not in the league manifest: {unknown}; available: {available}")
    wanted = set(seasons or available)
    current = standings_sources.current_season(manifest)

    summary: dict[str, Any] = {"Product": LEAGUE_STANDINGS, "CanonicalLeagueID": league_id, "Seasons": []}
    previous: dict[str, Any] | None = None
    completed_newest_first: list[dict[str, Any]] = []
    for season in available:
        inputs = standings_sources.load_season_inputs(repo_root, league_id, season, current)
        standings_model = get_model(model_for(metadata, season, "Standings"), "standings")
        awards_model = get_model(model_for(metadata, season, "Awards"), "awards")
        document = build_season(inputs, standings_model, awards_model, previous, completed_newest_first)
        previous = document
        if document["IsCompleted"]:
            completed_newest_first.insert(0, document)
        if season not in wanted:
            continue
        text = serialize(document)
        path = league_history_path(out_root, LEAGUE_STANDINGS, league_id, season)
        unchanged = path.is_file() and path.read_text(encoding="utf-8") == text
        if not unchanged and not check_only:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        summary["Seasons"].append({
            "Season": season,
            "Models": document["Models"],
            "CompletedWeeks": document["AsOf"]["CompletedWeeks"],
            "Weeks": len(document["Weeks"]),
            "Awards": len(document["Awards"]),
            "Bytes": len(text.encode("utf-8")),
            "Unchanged": 1 if unchanged else 0,
            "Written" if not check_only else "WouldWrite": 0 if unchanged else 1,
        })
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    sub = parser.add_subparsers(dest="command", required=True)
    mat = sub.add_parser("materialize", help="compute a product from canonical facts and write changed snapshots")
    mat.add_argument("--product", required=True, choices=PRODUCTS)
    mat.add_argument("--league", help="CanonicalLeagueID (default: every league in data-meta)")
    mat.add_argument("--season", type=int, action="append", help="only this season (repeatable); default: all manifest seasons")
    mat.add_argument("--out-root", type=Path, help="derived data root (default: the repository's derived root)")
    mat.add_argument("--hold-seed-players-file", type=Path,
                     help="published Players.json whose values seed identity-hold rows that no snapshot knows yet")
    mat.add_argument("--check", action="store_true", help="write nothing; exit 3 when any snapshot would change")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_root = args.out_root or data_derived_dir(args.repo_root)
    try:
        leagues = [args.league] if args.league else list_league_ids(data_meta_root(args.repo_root))
        if args.product == LEAGUE_STANDINGS:
            results = [
                materialize_league_standings(args.repo_root, out_root, league, args.season, args.check)
                for league in leagues
            ]
        elif args.product in (LEAGUE_TRANSACTIONS, LEAGUE_DRAFTS):
            results = [
                materialize_league_history(args.repo_root, out_root, league, args.product, args.season, args.check)
                for league in leagues
            ]
        else:
            hold_seed = load_hold_seed(args.hold_seed_players_file) if args.hold_seed_players_file else None
            results = [
                materialize_player_valuation(args.repo_root, out_root, league, args.season, args.check, hold_seed)
                for league in leagues
            ]
    except (sources.SourceError, LeagueMetadataError, LeagueHistorySourceError, standings_sources.StandingsSourceError,
            ValueError, KeyError, OSError) as error:
        print(f"derived_data materialize failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(results, indent=2, sort_keys=True))
    if args.check and any(s.get("WouldWrite") for r in results for s in r["Seasons"]):
        return EXIT_CHANGED
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
