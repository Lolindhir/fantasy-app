#!/usr/bin/env python3
"""App delivery of persisted league-records, with semantic no-op (ADR-100, #1672).

Reads the Shared Derived product only; writes public/data/LeagueRecords.json and
the LeagueRecords key in Timestamps.json. No record selection is performed here.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from data_roots import data_derived_dir, data_meta_dir
from league_metadata import default_league_id
from league_records_materialize import read_persisted
from app_delivery import Writer, warn


def publish(repo_root: Path, league_id: str, writer: Writer) -> None:
    document = read_persisted(data_derived_dir(repo_root), league_id)
    writer.put("LeagueRecords.json", document, "LeagueRecords")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("command", choices=["write"])
    parser.add_argument("--league")
    parser.add_argument("--fail-on-error", action="store_true")
    args = parser.parse_args(argv)
    writer = Writer(args.repo_root, datetime.now(timezone.utc))
    try:
        publish(args.repo_root, args.league or default_league_id(data_meta_dir(args.repo_root)), writer)
    except (OSError, ValueError, KeyError, TypeError) as error:
        warn("LeagueRecords not published", str(error))
        return 1 if args.fail_on_error else 0
    changed = writer.finish()
    print("\n".join(f"wrote {name}" for name in changed) if changed else "No changes - update skipped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
