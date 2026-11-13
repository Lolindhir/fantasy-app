#!/usr/bin/env python3
"""Consumer generator: materializes the season-statistics product and renders the App files (Issue #506).

  data-derived/season-statistics/<CanonicalLeagueID>/<season>.json                 Shared Derived product (written only on a difference)
  public/data/SeasonStatistics.json                                                current season plus BiggestUpsetAllTime
  public/data/past_seasons/SeasonStatistics/SeasonStatistics_<season>.json         completed earlier seasons

Usage:
  season_statistics_app_publish.py write [--league ID] [--scope current|history|all] [--fail-on-error]

The App files carry the product document unchanged; the only addition is ``BiggestUpsetAllTime`` in the current file, chosen here (not in
the frontend) from the persisted products of every season: the win with the lowest pregame chance (earlier season, then earlier week on
a tie). Files are written only on a semantic difference and Timestamps.json[SeasonStatistics] is stamped for the current file only. A
season whose canonical evidence is incomplete keeps its last file and raises a warning; the current season fails the run with
--fail-on-error. Without --league more than one league fails closed (the App files carry no league dimension).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from data_roots import data_derived_dir  # noqa: E402
from derived_data import SEASON_STATISTICS, build_season_statistics, league_history_path, serialize  # noqa: E402
from derived_data_lib.league_lifecycle import LifecycleError  # noqa: E402
from derived_data_lib.season_statistics import SeasonStatisticsError  # noqa: E402
from league_metadata import LeagueMetadataError, list_league_ids  # noqa: E402
from league_standings_sources import StandingsSourceError, current_season, manifest  # noqa: E402
from matchup_context_app_publish import Writer, _warn, history_matchup_seasons  # noqa: E402

EXPECTED_ERRORS = (SeasonStatisticsError, LifecycleError, StandingsSourceError, LeagueMetadataError)


def write_product(out_root: Path, league_id: str, documents: dict[int, dict[str, Any]]) -> list[int]:
    """Writes the product files that differ; returns the changed seasons."""
    changed: list[int] = []
    for season, document in sorted(documents.items()):
        text = serialize(document)
        path = league_history_path(out_root, SEASON_STATISTICS, league_id, season)
        if path.is_file() and path.read_text(encoding="utf-8") == text:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        changed.append(season)
    return changed


def persisted_documents(out_root: Path, league_id: str) -> dict[int, dict[str, Any]]:
    folder = out_root / SEASON_STATISTICS / league_id
    return {int(p.stem): json.loads(p.read_text(encoding="utf-8")) for p in sorted(folder.glob("*.json")) if p.stem.isdigit()}


def biggest_upset_all_time(documents: dict[int, dict[str, Any]]) -> dict[str, Any] | None:
    """The lowest pregame chance of any season's BiggestUpset; ties by earlier season, then earlier week."""
    best: tuple[Any, dict[str, Any]] | None = None
    for season, document in sorted(documents.items()):
        upset = document.get("BiggestUpset")
        if upset is None:
            continue
        key = (upset["WinnerPregameWinProbability"], season, upset["Week"])
        if best is None or key < best[0]:
            best = (key, {"Season": season, **upset})
    return None if best is None else best[1]


def leagues(requested: str | None) -> list[str]:
    if requested:
        return [requested]
    ids = list_league_ids()
    if len(ids) != 1:
        raise SeasonStatisticsError(f"the App SeasonStatistics files carry no league dimension; expected exactly one league, found {ids}")
    return ids


def publish(repo_root: Path, league_id: str, scope: str, writer: Writer) -> None:
    out_root = data_derived_dir(repo_root)
    current = current_season(manifest(repo_root, league_id))
    history = history_matchup_seasons(repo_root, league_id, current)
    if scope in ("current", "all"):
        documents = build_season_statistics(repo_root, league_id, [current])
        write_product(out_root, league_id, documents)
        stored = persisted_documents(out_root, league_id)
        rendered = {**documents[current], "BiggestUpsetAllTime": biggest_upset_all_time(stored)}
        writer.put("SeasonStatistics.json", rendered, "SeasonStatistics")
    if scope in ("history", "all"):
        for season in history:
            try:
                documents = build_season_statistics(repo_root, league_id, [season])
            except EXPECTED_ERRORS as error:
                _warn(f"Historical SeasonStatistics {season} not published", f"{type(error).__name__}: {error}")
                continue
            write_product(out_root, league_id, documents)
            writer.put(f"past_seasons/SeasonStatistics/SeasonStatistics_{season}.json", documents[season])


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    sub = parser.add_subparsers(dest="command", required=True)
    write = sub.add_parser("write", help="materialize the product and write the App files (semantic no-op)")
    write.add_argument("--league", default=None)
    write.add_argument("--scope", choices=("current", "history", "all"), default="current")
    write.add_argument("--fail-on-error", action="store_true", help="exit 1 when the current season cannot be built")
    return parser.parse_args(argv)


def run_write(args: argparse.Namespace) -> int:
    writer = Writer(args.repo_root, datetime.now(timezone.utc))
    try:
        for league_id in leagues(args.league):
            publish(args.repo_root, league_id, args.scope, writer)
    except EXPECTED_ERRORS as error:
        _warn("SeasonStatistics not published", f"{type(error).__name__}: {error}")
        writer.finish()
        return 1 if args.fail_on_error else 0
    changed = writer.finish()
    print("\n".join(f"wrote {name}" for name in changed) if changed else "No changes - update skipped.")
    return 0


def main(argv: list[str] | None = None) -> int:
    return run_write(parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
