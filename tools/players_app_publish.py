#!/usr/bin/env python3
"""Consumer generator of the published Players file (ADR-076, Issue #1226).

Usage:
  players_app_publish.py compare [--league ID] [--as-of YYYY-MM-DD] [--report-dir DIR]
  players_app_publish.py write   [--league ID] [--as-of YYYY-MM-DD]

``write`` (cutover, step 5) materializes the player-valuation product into data-derived, resolves the Players rows for the
run date in the league time zone and writes the published file only when the content differs (published form, like
Compare-Players): backup copy under public/data/backup, the file itself and Timestamps.json[Players]. The previously
published file is read only for the change comparison, never as an input of the rows (Q3).

``compare`` is the shadow of the cutover (step 4): it materializes the player-valuation product into a scratch directory
(never into the repository), resolves the Players rows with the players read model for the reference date and compares
them exactly, field by field and in the written text, with the published file. The reference date defaults to the date of
the Players entry of Timestamps.json in the league time zone (data-meta LeagueTimeZone), so Age is reproducible. The
published file is read only for this comparison and is never an input of the model (validation-shadow).

Exit code: 0 = identical, 2 = differences, 1 = the inputs cannot be compared (message on stderr).
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))

import derived_data  # noqa: E402
from data_roots import data_derived_dir  # noqa: E402
import player_valuation_sources as sources  # noqa: E402
from derived_data_lib.players_read_model import (  # noqa: E402
    PlayersReadModelError, players_differ, resolve, serialize_players,
)
from league_metadata import data_meta_root, default_league_id, load_league_metadata  # noqa: E402

EXIT_DIFFERENCES = 2
MAX_EXAMPLES_PER_FIELD = 3


class CompareError(RuntimeError):
    """The comparison cannot be made (missing or unusable published files)."""


def _dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def diff_players(published: Sequence[Mapping[str, Any]], computed: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Exact difference by ID and field. Values are compared in their written form, so 1 and 1.0 differ like in the file."""
    old = {str(p["ID"]): p for p in published}
    new = {str(p["ID"]): p for p in computed}
    fields: Counter = Counter()
    examples: dict[str, list[dict[str, Any]]] = {}
    for player_id in sorted(old.keys() & new.keys()):
        a, b = old[player_id], new[player_id]
        for name in list(a) + [k for k in b if k not in a]:
            if _dump(a.get(name, "<absent>")) != _dump(b.get(name, "<absent>")):
                fields[name] += 1
                bucket = examples.setdefault(name, [])
                if len(bucket) < MAX_EXAMPLES_PER_FIELD:
                    bucket.append({"ID": player_id, "Published": _dump(a.get(name, "<absent>"))[:200],
                                   "Computed": _dump(b.get(name, "<absent>"))[:200]})
    return {
        "OnlyPublished": sorted(old.keys() - new.keys()),
        "OnlyComputed": sorted(new.keys() - old.keys()),
        "DifferingFields": dict(sorted(fields.items())),
        "Examples": examples,
    }


def is_identical(diff: Mapping[str, Any]) -> bool:
    return not (diff["OnlyPublished"] or diff["OnlyComputed"] or diff["DifferingFields"])


def reference_date(timestamp: str, time_zone: str) -> date:
    """Calendar date of an ISO instant in the league time zone."""
    try:
        instant = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError as error:
        raise CompareError(f"Timestamps.json Players is not an ISO instant: {timestamp!r}") from error
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=timezone.utc)
    return instant.astimezone(ZoneInfo(time_zone)).date()


def compare(repo_root: Path, league_id: str, as_of_text: str | None) -> tuple[dict[str, Any], dict[str, Any]]:
    data = repo_root / "public" / "data"
    try:
        published_text = (data / "Players.json").read_text(encoding="utf-8")
        published = json.loads(published_text)
        stamp = json.loads((data / "Timestamps.json").read_text(encoding="utf-8-sig"))["Players"]
    except (OSError, KeyError, json.JSONDecodeError) as error:
        raise CompareError(f"Published Players.json/Timestamps.json unusable: {error}") from error
    metadata = load_league_metadata(league_id, data_meta_root(repo_root))
    as_of = date.fromisoformat(as_of_text) if as_of_text else reference_date(stamp, metadata["LeagueTimeZone"])
    season = sources.current_season(sources.league_manifest(repo_root, league_id))

    with tempfile.TemporaryDirectory(prefix="players-shadow-") as scratch:
        derived_data.materialize_player_valuation(repo_root, Path(scratch), league_id, [season], False)
        result = resolve(repo_root, league_id, season, as_of, derived_root=Path(scratch))

    diff = diff_players(published, result.players)
    report = {
        "CanonicalLeagueID": league_id, "Season": season, "AsOfDate": as_of.isoformat(), "PlayersTimestamp": stamp,
        "Published": len(published), "Computed": len(result.players),
        "TextIdentical": published_text == serialize_players(result.players),
        "Warnings": result.warnings, **diff,
    }
    return report, diff


def write(repo_root: Path, league_id: str, as_of_text: str | None, now: datetime | None = None) -> tuple[bool, list[str]]:
    """Write the Players file on a content change; returns (changed, warnings). Fail closed on any input problem."""
    data = repo_root / "public" / "data"
    target = data / "Players.json"
    moment = now or datetime.now(timezone.utc)
    metadata = load_league_metadata(league_id, data_meta_root(repo_root))
    as_of = date.fromisoformat(as_of_text) if as_of_text else moment.astimezone(ZoneInfo(metadata["LeagueTimeZone"])).date()
    season = sources.current_season(sources.league_manifest(repo_root, league_id))

    derived_data.materialize_player_valuation(repo_root, data_derived_dir(repo_root), league_id, None, False)
    result = resolve(repo_root, league_id, season, as_of)

    old = None
    if target.is_file():
        try:
            old = json.loads(target.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            old = None  # unreadable old file counts as changed, never as an input
    if not players_differ(old, result.players):
        return False, result.warnings

    backup_dir = data / "backup"
    if target.is_file():
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = moment.astimezone(timezone.utc).strftime("%Y%m%d_%H%M%S")
        (backup_dir / f"Players_{stamp}.json").write_bytes(target.read_bytes())
    target.write_text(serialize_players(result.players), encoding="utf-8", newline="\n")

    stamp_path = data / "Timestamps.json"
    timestamps = json.loads(stamp_path.read_text(encoding="utf-8-sig")) if stamp_path.is_file() else {}
    timestamps["Players"] = moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    stamp_path.write_text(json.dumps(timestamps, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return True, result.warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    cmd = sub.add_parser("compare", help="shadow comparison against the published Players file")
    cmd.add_argument("--league", default=None, help="CanonicalLeagueID (default: the only league in data-meta)")
    cmd.add_argument("--as-of", help="reference date YYYY-MM-DD; default: date of Timestamps.json Players in the league time zone")
    cmd.add_argument("--report-dir", type=Path, help="write players-shadow.json here")
    cmd.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    wr = sub.add_parser("write", help="write the Players file on a content change")
    wr.add_argument("--league", default=None, help="CanonicalLeagueID (default: the only league in data-meta)")
    wr.add_argument("--as-of", help="reference date YYYY-MM-DD; default: today in the league time zone")
    wr.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    if args.league is None:
        args.league = default_league_id(data_meta_root(args.repo_root))
    if args.command == "write":
        try:
            changed, warnings = write(args.repo_root, args.league, args.as_of)
        except (PlayersReadModelError, sources.SourceError, ValueError, OSError) as error:
            print(f"players_app_publish: {error}", file=sys.stderr)
            return 1
        for warning in warnings:
            print(f"WARNING: {warning}", file=sys.stderr)
        print("Players file written." if changed else "No changes - update skipped.")
        return 0
    try:
        report, diff = compare(args.repo_root, args.league, args.as_of)
    except (CompareError, PlayersReadModelError, sources.SourceError, ValueError) as error:
        print(f"players_app_publish: {error}", file=sys.stderr)
        return 1
    if args.report_dir:
        args.report_dir.mkdir(parents=True, exist_ok=True)
        (args.report_dir / "players-shadow.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    identical = is_identical(diff)
    print(f"players_app_publish compare: {report['Published']} published, {report['Computed']} computed, AsOfDate {report['AsOfDate']}, "
          f"{'identical' if identical else 'DIFFERENCES'}, text {'identical' if report['TextIdentical'] else 'different'}")
    if not identical:
        print(f"  only published: {diff['OnlyPublished'][:10]}  only computed: {diff['OnlyComputed'][:10]}")
        for name, count in diff["DifferingFields"].items():
            print(f"  {name}: {count} player(s), e.g. {diff['Examples'][name][0]}")
    for warning in report["Warnings"]:
        print(f"WARNING: {warning}", file=sys.stderr)
    return 0 if identical else EXIT_DIFFERENCES


if __name__ == "__main__":
    raise SystemExit(main())
