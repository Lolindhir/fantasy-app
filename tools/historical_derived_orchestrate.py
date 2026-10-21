#!/usr/bin/env python3
"""Read-only production preflight of repeatable historical PWF -> TWP derivation.

Rebuilds in a disposable directory; no Git push, App write, Source write or
persistent Derived write. This is NOT a publisher. Issue #471.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import tempfile
from pathlib import Path
from typing import Sequence

from historical_pwf_batch import discover_scored_weeks, materialize_historical
from team_week_performance_materialize import materialize as materialize_twp

Target = tuple[str, int, int]
_WEEK_INPUT = re.compile(
    r"^data-source/(?:nfl/(?:weekly-rosters|player-stats)/(\d{4})/(\d{2})\.json|"
    r"leagues/([A-Za-z0-9_-]+)/seasons/(\d{4})/matchups/week-(\d+)\.json)$"
)
_SEASON_INPUT = re.compile(
    r"^data-source/(?:nfl/(?:game-finality|rosters|schedules)/(\d{4})\.json|"
    r"leagues/([A-Za-z0-9_-]+)/seasons/(\d{4})/league\.json)$"
)


def select_targets(
    available: Sequence[Target], *, mode: str, season: int | None = None,
    week: int | None = None, changed_paths: Sequence[str] = (),
) -> list[Target]:
    """Unknown input changes widen to full, never silently omit dependencies."""
    targets = sorted(set(available))
    if mode == "full":
        if season is not None or week is not None or changed_paths:
            raise ValueError("Full mode does not accept filters")
        return targets
    if mode == "week":
        if (type(season) is not int or type(week) is not int
                or season < 1 or week < 1 or changed_paths):
            raise ValueError("Week mode requires --season and --week only")
        selected = [t for t in targets if t[1:] == (season, week)]
        if not selected:
            raise ValueError("Requested week is not canonically scored")
        return selected
    if mode != "incremental" or season is not None or week is not None or not changed_paths:
        raise ValueError("Incremental mode requires --changed-path and no week filters")
    chosen: set[Target] = set()
    for path in changed_paths:
        if not path or path.startswith("/") or ".." in Path(path).parts or "\\" in path:
            raise ValueError(f"Invalid changed path: {path!r}")
        weekly = _WEEK_INPUT.fullmatch(path)
        if weekly:
            year = int(weekly.group(1) or weekly.group(4))
            leg = int(weekly.group(2) or weekly.group(5))
            league = weekly.group(3)
            # NFL history feeds rolling projections and calibration across
            # seasons. Rebuild this week and all later scored weeks, including
            # future seasons; league matchups are week-local by contrast.
            forward = league is None
            chosen.update(t for t in targets
                          if ((t[1] > year or (t[1] == year and t[2] >= leg))
                              if forward else t[1:] == (year, leg))
                          and (league is None or t[0] == league))
            continue
        season_match = _SEASON_INPUT.fullmatch(path)
        if season_match:
            year = int(season_match.group(1) or season_match.group(3))
            league = season_match.group(2)
            # NFL season evidence can be a historical projection/calibration
            # dependency for future seasons; a league's own settings are local.
            chosen.update(t for t in targets
                          if (t[1] >= year if league is None else t[1] == year)
                          and (league is None or t[0] == league))
            continue
        # Unexpected source, code, metadata or scoring change: recompute all.
        return targets
    return sorted(chosen)


def _stage(root: Path, destination: Path) -> None:
    """Symlink immutable input readers; copy only owned Derived output products."""
    for name in ("data-source", "data-meta", "public"):
        source = root / name
        if not source.is_dir():
            raise ValueError(f"Missing source input directory: {source}")
        (destination / name).symlink_to(source, target_is_directory=True)
    derived = destination / "data-derived"
    derived.mkdir()
    for product in ("player-week-fantasy", "team-week-performance"):
        original = root / "data-derived" / product
        if original.is_dir():
            shutil.copytree(original, derived / product)


def _assert_not_live(root: Path, targets: Sequence[Target]) -> None:
    """Never collide with the current App PWF publication week."""
    path = root / "public/data/FantasyGameContext.json"
    if not path.is_file():
        raise ValueError("Cannot establish live App week protection")
    try:
        context = json.loads(path.read_text(encoding="utf-8"))
        season, week = int(context["Season"]), int(context["Week"])
    except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid current App week; historical check denied") from exc
    if any(t[1:] == (season, week) for t in targets):
        raise ValueError(f"Historical run overlaps current App week {season}/{week}")


def _run_pwf(stage: Path, selected: Sequence[Target]) -> int:
    """Use original producer without unsafe cross-product season/week filters."""
    changed = 0
    for league, season, week in selected:
        result = materialize_historical(
            stage, league_id=league, seasons=[season], weeks=[week], write=True,
        )
        if result["TargetCount"] != 1 or result["BlockedCount"] or result["ReadyCount"] != 1:
            raise ValueError(f"PWF not ready {league}/{season}/{week}: {result['Weeks']}")
        changed += result["ChangedCount"]
    return changed


def _run_twp(stage: Path, selected: Sequence[Target]) -> tuple[int, int]:
    changed, accepted = 0, 0
    for league, season, week in selected:
        result = materialize_twp(stage, league, season, week, write=True, require_pwf=True)
        parity = result["PlayerWeekFantasyParity"]
        if parity["State"] not in ("verified", "accepted-divergence"):
            raise ValueError(f"TWP scoring not verified: {league}/{season}/{week}")
        if parity["State"] == "accepted-divergence" and parity.get("AcceptedDivergences") != 1:
            raise ValueError("Unclassified multi-player score divergence")
        accepted += parity.get("AcceptedDivergences", 0)
        changed += int(result["Changed"])
    return changed, accepted


def _output(root: Path, product: str, target: Target) -> Path:
    league, season, week = target
    return (root / "data-derived" / product / league / str(season) / f"{week:02d}.json")


def _different(first: Path, second: Path) -> bool:
    return not first.is_file() or first.read_bytes() != second.read_bytes()


def preflight(
    repo_root: Path, *, mode: str = "full", season: int | None = None,
    week: int | None = None, changed_paths: Sequence[str] = (),
    league_id: str | None = None,
) -> dict:
    """Reconcile both products in an ephemeral checkout; never write to repo."""
    root = repo_root.resolve()
    all_targets = discover_scored_weeks(root, league_id=league_id)
    selected = select_targets(
        all_targets, mode=mode, season=season, week=week, changed_paths=changed_paths,
    )
    _assert_not_live(root, selected)
    if not selected:
        return {
            "Mode": mode, "ScoredWeekCount": len(all_targets), "TargetCount": 0,
            "PWFWouldChange": 0, "TWPWouldChange": 0,
            "AcceptedDivergences": 0, "SecondPassNoop": True,
            "Published": False, "Weeks": [],
        }
    with tempfile.TemporaryDirectory(prefix="historical-derived-audit-") as temp:
        stage = Path(temp)
        _stage(root, stage)
        _run_pwf(stage, selected)
        _, accepted = _run_twp(stage, selected)
        changed_pwf = sum(
            _different(_output(root, "player-week-fantasy", t),
                       _output(stage, "player-week-fantasy", t)) for t in selected
        )
        changed_twp = sum(
            _different(_output(root, "team-week-performance", t),
                       _output(stage, "team-week-performance", t)) for t in selected
        )
        # Existing published TWP supplies live Awards. Do not change it in an
        # historical release without separate explicit review.
        affected_published = [
            t for t in selected
            if _output(root, "team-week-performance", t).is_file()
            and _different(_output(root, "team-week-performance", t),
                           _output(stage, "team-week-performance", t))
        ]
        if affected_published:
            raise ValueError(f"Existing published Team Awards would change: {affected_published}")
        second_pwf = _run_pwf(stage, selected)
        second_twp, second_accepted = _run_twp(stage, selected)
        if second_pwf or second_twp or accepted != second_accepted:
            raise ValueError("Second source-derived reconstruction is not idempotent")
        return {
            "Mode": mode, "ScoredWeekCount": len(all_targets),
            "TargetCount": len(selected), "PWFWouldChange": changed_pwf,
            "TWPWouldChange": changed_twp, "AcceptedDivergences": accepted,
            "SecondPassNoop": True, "Published": False,
            "Weeks": [{"League": league, "Season": year, "Week": leg}
                      for league, year, leg in selected],
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--league")
    parser.add_argument("--mode", choices=("full", "week", "incremental"), default="full")
    parser.add_argument("--season", type=int)
    parser.add_argument("--week", type=int)
    parser.add_argument("--changed-path", action="append", default=[])
    args = parser.parse_args(argv)
    try:
        report = preflight(
            args.repo_root, league_id=args.league, mode=args.mode,
            season=args.season, week=args.week, changed_paths=args.changed_path,
        )
    except (ValueError, OSError, KeyError) as exc:
        parser.exit(2, f"Historical Derived preflight failed closed: {exc}\n")
    print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
