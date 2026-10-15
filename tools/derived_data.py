#!/usr/bin/env python3
"""Materializer for Shared Derived Data products (ADR-038, ADR-055).

First product: player-valuation (.ai-context/manual/player-valuation.yaml): Salary, SalaryProjected,
Ranking, rank Grading and the Salary Cap for every season of the league manifest and every
AsOfFinalScoredWeek, written to <derived root>/player-valuation/<CanonicalLeagueID>/<season>/week-<NN>.json.

The model per league and season comes from the league metadata (tools/league_metadata.py, ADR-054);
the model code lives in tools/derived_data_lib. A snapshot is rebuilt from canonical facts on every run
and written only on a semantic difference (a second run is a file-level no-op). Nothing publishes the
output yet; the product stays a local/test artifact until the cutover of Issue #919 step 5.

Second product family: league-transactions (league-history.yaml, ADR-057, Issue #999), written to
<derived root>/league-transactions/<CanonicalLeagueID>/<season>.json for every manifest season. Nothing
publishes it yet; the App files in public/data stay produced by the PowerShell rebuild until the cutover.

Usage:
  derived_data.py materialize --product player-valuation|league-transactions [--league nfl-reise]
                              [--season 2026 ...] [--out-root DIR] [--check]
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
from derived_data_lib.league_history import build_transaction_stage, transactions_document  # noqa: E402
from league_history_sources import LeagueHistorySourceError, load_inputs  # noqa: E402
from players_league_scoring import SleeperIdentityResolver  # noqa: E402

LEAGUE_TRANSACTIONS = "league-transactions"
PRODUCTS = (sources.PRODUCT, LEAGUE_TRANSACTIONS)
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


def materialize_player_valuation(
    repo_root: Path, out_root: Path, league_id: str, seasons: list[int] | None, check_only: bool,
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
            snapshot = build_snapshot(context, source.players, existing.lookup_for(as_of))
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


def league_transactions_path(out_root: Path, league_id: str, season: int) -> Path:
    return out_root / LEAGUE_TRANSACTIONS / league_id / f"{season}.json"


def materialize_league_transactions(
    repo_root: Path, out_root: Path, league_id: str, seasons: list[int] | None, check_only: bool,
) -> dict[str, Any]:
    inputs = load_inputs(repo_root, league_id)
    wanted = inputs.seasons if not seasons else sorted(set(seasons))
    unknown = [s for s in wanted if s not in inputs.seasons]
    if unknown:
        raise sources.SourceError(f"Seasons not in the league manifest: {unknown}; available: {inputs.seasons}")
    stage = build_transaction_stage(inputs)
    if stage.unresolved:
        raise sources.SourceError(f"Transaction picks without a unique draft identity: {stage.unresolved}")
    resolver = SleeperIdentityResolver.from_repo(repo_root)
    summary: dict[str, Any] = {"Product": LEAGUE_TRANSACTIONS, "CanonicalLeagueID": league_id, "Seasons": []}
    for season in wanted:
        document = transactions_document(
            league_id, season, stage.transactions[season], lambda player, year: resolver.resolve(player, year)[0]
        )
        text = serialize(document)
        path = league_transactions_path(out_root, league_id, season)
        unchanged = path.is_file() and path.read_text(encoding="utf-8") == text
        if not unchanged and not check_only:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        summary["Seasons"].append({
            "Season": season,
            "Transactions": len(document["Transactions"]),
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
    mat.add_argument("--check", action="store_true", help="write nothing; exit 3 when any snapshot would change")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_root = args.out_root or data_derived_dir(args.repo_root)
    try:
        leagues = [args.league] if args.league else list_league_ids(data_meta_root(args.repo_root))
        if args.product == LEAGUE_TRANSACTIONS:
            results = [
                materialize_league_transactions(args.repo_root, out_root, league, args.season, args.check)
                for league in leagues
            ]
        else:
            results = [
                materialize_player_valuation(args.repo_root, out_root, league, args.season, args.check)
                for league in leagues
            ]
    except (sources.SourceError, LeagueMetadataError, LeagueHistorySourceError, ValueError, KeyError, OSError) as error:
        print(f"derived_data materialize failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(results, indent=2, sort_keys=True))
    if args.check and any(s.get("WouldWrite") for r in results for s in r["Seasons"]):
        return EXIT_CHANGED
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
