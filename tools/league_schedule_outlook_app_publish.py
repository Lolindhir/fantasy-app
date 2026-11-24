#!/usr/bin/env python3
"""Consumer generator: renders the App file from the persisted league-schedule-outlook product (Issue #1519).

  data-derived/league-schedule-outlook/<CanonicalLeagueID>/<Season>/index.json + after-week-NN.json   Shared Derived product, input
  public/data/ScheduleOutlook.json    the snapshot of the newest fully scored cutoff of the current season, unchanged (App delivery)

Usage:
  league_schedule_outlook_app_publish.py write [--league ID] [--fail-on-error]

The product is read through its completeness index only: a missing or inconsistent index, a missing snapshot or a hash mismatch is
"unavailable" (warning, the last App file stays), never an empty outlook. The document is carried over unchanged, so Angular only displays it.
Files are written only on a semantic difference and Timestamps.json[ScheduleOutlook] is stamped only then. Without --league more than one
league fails closed (the App file carries no league dimension).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from data_roots import data_derived_dir  # noqa: E402
from derived_data_lib.league_lifecycle import LifecycleError  # noqa: E402
from derived_data_lib.league_schedule_outlook import PRODUCT  # noqa: E402
from league_metadata import LeagueMetadataError, list_league_ids  # noqa: E402
from league_standings_sources import StandingsSourceError, current_season, manifest  # noqa: E402
from app_delivery import Writer, warn  # noqa: E402

INDEX_PRODUCT = "league-schedule-outlook-index"


class ScheduleOutlookPublishError(ValueError):
    """The persisted product is missing or inconsistent; nothing is published."""


EXPECTED_ERRORS = (ScheduleOutlookPublishError, LifecycleError, StandingsSourceError, LeagueMetadataError)


def latest_snapshot(out_root: Path, league_id: str, season: int) -> dict[str, Any]:
    """The newest snapshot named by a consistent index, verified against the recorded SHA-256."""
    folder = out_root / PRODUCT / league_id / str(season)
    index_path = folder / "index.json"
    if not index_path.is_file():
        raise ScheduleOutlookPublishError(f"{PRODUCT} index missing for {league_id} {season}; materialize it first")
    index = json.loads(index_path.read_text(encoding="utf-8"))
    snapshots = index.get("Snapshots") or []
    if index.get("Product") != INDEX_PRODUCT or index.get("Season") != season or not snapshots:
        raise ScheduleOutlookPublishError(f"{PRODUCT} index of {league_id} {season} is inconsistent")
    weeks = sorted(entry["AfterWeek"] for entry in snapshots)
    if weeks != list(range(len(weeks))) or weeks[-1] != index.get("LeagueScoredWeek"):
        raise ScheduleOutlookPublishError(f"{PRODUCT} index of {league_id} {season} is not a complete 0..LeagueScoredWeek set")
    newest = max(snapshots, key=lambda entry: entry["AfterWeek"])
    path = folder / newest["File"]
    if not path.is_file():
        raise ScheduleOutlookPublishError(f"{PRODUCT} snapshot {newest['File']} of {league_id} {season} is missing")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != newest["Sha256"]:
        raise ScheduleOutlookPublishError(f"{PRODUCT} snapshot {newest['File']} of {league_id} {season} does not match the index hash")
    document = json.loads(raw.decode("utf-8"))
    if document.get("AsOf", {}).get("AfterWeek") != newest["AfterWeek"]:
        raise ScheduleOutlookPublishError(f"{PRODUCT} snapshot {newest['File']} contradicts its index entry")
    return document


def leagues(requested: str | None) -> list[str]:
    if requested:
        return [requested]
    ids = list_league_ids()
    if len(ids) != 1:
        raise ScheduleOutlookPublishError(f"the App ScheduleOutlook file carries no league dimension; expected exactly one league, found {ids}")
    return ids


def publish(repo_root: Path, league_id: str, writer: Writer) -> None:
    season = current_season(manifest(repo_root, league_id))
    writer.put("ScheduleOutlook.json", latest_snapshot(data_derived_dir(repo_root), league_id, season), "ScheduleOutlook")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    sub = parser.add_subparsers(dest="command", required=True)
    write = sub.add_parser("write", help="render the App file from the persisted product (semantic no-op)")
    write.add_argument("--league", default=None)
    write.add_argument("--fail-on-error", action="store_true", help="exit 1 when the product is unavailable")
    return parser.parse_args(argv)


def run_write(args: argparse.Namespace) -> int:
    writer = Writer(args.repo_root, datetime.now(timezone.utc))
    try:
        for league_id in leagues(args.league):
            publish(args.repo_root, league_id, writer)
    except EXPECTED_ERRORS as error:
        warn("ScheduleOutlook not published", f"{type(error).__name__}: {error}")
        writer.finish()
        return 1 if args.fail_on_error else 0
    changed = writer.finish()
    print("\n".join(f"wrote {name}" for name in changed) if changed else "No changes - update skipped.")
    return 0


def main(argv: list[str] | None = None) -> int:
    return run_write(parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
