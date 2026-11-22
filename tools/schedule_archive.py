#!/usr/bin/env python3
"""Consumer generator: past-season Schedule archives public/data/past_seasons/Schedule_<season>.json (Issue #999 step 7b).

The files are no static archives: they are rebuilt from the canonical NFL facts
(data-source/nfl/schedules/<season>.json + game-finality/<season>.json) and rewritten only on a semantic difference,
so a change of the derivation logic or a corrected canonical fact reaches them with the next weekly run.

The record shape, the field order and every conversion repeat public/requests/utils/general/CanonicalScheduleUtils.psm1
(New-AppScheduleGame, Get-CanonicalAppSchedule), which builds the current Schedule.json. `compare-current` proves that
parity against the published Schedule.json. Unlike the current file the archives keep all game types (the records carry
seasonType), so postseason games are part of them.

One game is not part of the canonical schedule: the cancelled 2022 week-17 game BUF@CIN. It is added from SUPPLEMENTS
(hand-maintained NFL fact, explicit and visible) because the archive has always listed it.

Usage:
  schedule_archive.py compare-current            parity of the generator with public/data/Schedule.json
  schedule_archive.py write [--season N ...]     write the archives (default: first needed season up to the season before the current league season)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from data_roots import DATA_SOURCE_ROOT  # noqa: E402
from derived_data_lib.models.registry import get_model  # noqa: E402
from derived_data_lib.nfl_games import kickoff_epoch as shared_kickoff_epoch  # noqa: E402
from league_metadata import data_meta_root, load_all_league_metadata, model_for  # noqa: E402

from derived_data_lib.nfl_schedule_games import (  # noqa: E402,F401
    POSTSEASON_TYPES,
    SUPPLEMENTS,
    ScheduleArchiveError,
    TeamRegistry,
    _score,
    app_game,
    build_schedule,
    game_time_text,
    kickoff_epoch,
    season_type,
)


def _dump(payload: Any) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _current_season(root: Path) -> int:
    """Latest current season over all league manifests (the NFL schedule is league-independent)."""
    seasons = []
    for manifest_path in sorted((root / DATA_SOURCE_ROOT / "leagues").glob("*/manifest.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        seasons.append(int(str(manifest["CurrentCanonicalLeagueSeasonID"]).rsplit("-", 1)[-1]))
    if not seasons:
        raise ScheduleArchiveError("No league manifest found; the current season is unknown.")
    return max(seasons)


def write_archives(root: Path, seasons: list[int]) -> list[str]:
    """Write Schedule_<season>.json only where the content differs semantically; returns the changed paths."""
    changed: list[str] = []
    target = root / "public" / "data" / "past_seasons"
    for season in seasons:
        records = build_schedule(root, season)
        path = target / f"Schedule_{season}.json"
        if path.is_file() and _load(path) == records:
            continue
        path.write_text(_dump(records), encoding="utf-8")
        changed.append(f"public/data/past_seasons/Schedule_{season}.json")
    return changed


def first_needed_season(root: Path) -> int:
    """Oldest season any league needs: its first season minus the history its Salary model reads (salary-v1: 3)."""
    firsts = []
    for metadata in load_all_league_metadata(data_meta_root(root)).values():
        for season in metadata["Seasons"]:
            model = get_model(model_for(metadata, season, "Salary"), "salary")
            firsts.append(int(season) - int(getattr(model, "HISTORY_SEASONS", 0)))
    if not firsts:
        raise ScheduleArchiveError("No league season found; the first needed archive season is unknown.")
    return min(firsts)


def default_seasons(root: Path) -> list[int]:
    return list(range(first_needed_season(root), _current_season(root)))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parent.parent))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("compare-current", help="generator parity with the published public/data/Schedule.json")
    write = sub.add_parser("write", help="write the past-season archives (semantic no-op)")
    write.add_argument("--season", type=int, action="append", help="limit to season(s); default all archive seasons")
    write.add_argument("--fail-on-error", action="store_true", help="exit 1 when a season cannot be built")
    args = parser.parse_args(argv)
    root = Path(args.repo_root)

    if args.command == "compare-current":
        season = _current_season(root)
        built = build_schedule(root, season, {"REG"})
        published = _load(root / "public" / "data" / "Schedule.json")
        if built == published and [list(r) for r in built] == [list(r) for r in published]:
            print(f"OK: generator equals public/data/Schedule.json ({len(built)} games, season {season}).")
            return 0
        diffs = [(a, b) for a, b in zip(built, published) if a != b][:3]
        print(f"MISMATCH: built {len(built)} vs published {len(published)} games; first differences: {diffs}")
        return 1

    failures = 0
    for season in args.season or default_seasons(root):
        try:
            changed = write_archives(root, [season])
        except ScheduleArchiveError as exc:
            failures += 1
            print(f"::warning::Schedule archive {season} kept as is: {exc}")
            continue
        print(f"Schedule_{season}.json: {'written' if changed else 'unchanged'}")
    return 1 if failures and args.fail_on_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
