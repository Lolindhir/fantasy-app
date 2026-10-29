#!/usr/bin/env python3
"""Incremental Shared Derived refresh for the ten-minute League Live chain (Issue #471, step 3).

For every league in data-meta this keeps the products that the App already shows in step with it:

* league-transactions and league-drafts of the league's current season
  (same materializer as the weekly update-transactions run, tools/derived_data.py),
* TeamWeekPerformance (Best Manager / Best Coach) of the newest league-scored week of the current
  season (same strict materializer as the weekly run, tools/team_week_performance_materialize.py,
  with an independent, non-blocking PWF parity diagnostic).

Older seasons and weeks stay with the weekly runs; no new calculation lives here. Everything is
written only on a semantic difference. A product that cannot be built (a week whose NFL finality or
PlayerWeekFantasy parity is not ready, unreadable sources) keeps its last good file, is reported as a
warning and does not fail the chain, so a not-yet-final week can never block the App League
publication. The weekly runs remain the loud backstop.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from data_roots import data_derived_dir  # noqa: E402
from derived_data import LEAGUE_DRAFTS, LEAGUE_TRANSACTIONS, materialize_league_history  # noqa: E402
from league_history_sources import _manifest  # noqa: E402
from league_metadata import data_meta_root, list_league_ids  # noqa: E402
from team_week_performance_materialize import discover_finalized_weeks, materialize  # noqa: E402


def current_season(repo_root: Path, league_id: str) -> int:
    manifest = _manifest(repo_root, league_id)
    return int(str(manifest["CurrentCanonicalLeagueSeasonID"]).rsplit("-", 1)[-1])


def _warn(title: str, message: str) -> None:
    print(f"::warning title={title}::{message}", file=sys.stderr)


def refresh_history(repo_root: Path, league_id: str, season: int) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for product in (LEAGUE_TRANSACTIONS, LEAGUE_DRAFTS):
        entry: dict[str, Any] = {"Product": product, "Season": season}
        try:
            summary = materialize_league_history(
                repo_root, data_derived_dir(repo_root), league_id, product, [season], False,
            )
        except Exception as error:  # fail-closed product: keep the last good file, report visibly
            entry.update(Status="blocked", Reason=f"{type(error).__name__}: {error}")
            _warn(f"{product} not refreshed", f"{league_id}/{season}: {entry['Reason']}")
        else:
            written = sum(int(item.get("Written", 0)) for item in summary["Seasons"])
            entry.update(Status="changed" if written else "unchanged")
        results.append(entry)
    return results


def refresh_team_week_performance(repo_root: Path, league_id: str, season: int) -> dict[str, Any]:
    entry: dict[str, Any] = {"Product": "team-week-performance", "Season": season}
    try:
        weeks = [
            week for current_id, year, week
            in discover_finalized_weeks(repo_root, league_id=league_id, seasons=[season])
            if current_id == league_id and year == season
        ]
        if not weeks:
            entry.update(Status="no-scored-week")
            return entry
        week = max(weeks)
        entry["Week"] = week
        report = materialize(repo_root, league_id, season, week, write=True, require_pwf=False)
    except Exception as error:  # fail-closed product: keep the last good file, report visibly
        entry.update(Status="blocked", Reason=f"{type(error).__name__}: {error}")
        _warn("TeamWeekPerformance not refreshed", f"{league_id}/{season}: {entry['Reason']}")
    else:
        entry.update(Status="changed" if report["Changed"] else "unchanged")
        parity = report.get("PlayerWeekFantasyParity")
        if isinstance(parity, dict):
            entry["PlayerWeekFantasyParity"] = parity
            if parity.get("State") not in ("verified", "accepted-divergence"):
                _warn("Independent player scoring differs from Sleeper",
                      f"{league_id}/{season}/W{week}: {parity.get('State')}: "
                      f"{parity.get('Reason', 'PWF evidence unavailable')}")
    return entry


def refresh(repo_root: Path) -> list[dict[str, Any]]:
    root = repo_root.resolve()
    results: list[dict[str, Any]] = []
    for league_id in list_league_ids(data_meta_root(root)):
        season = current_season(root, league_id)
        for entry in (*refresh_history(root, league_id, season),
                      refresh_team_week_performance(root, league_id, season)):
            results.append({"CanonicalLeagueID": league_id, **entry})
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", type=Path, default=TOOLS.parent)
    args = parser.parse_args(argv)
    print(json.dumps(refresh(args.repo_root), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
