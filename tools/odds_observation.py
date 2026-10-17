#!/usr/bin/env python3
"""Inspect nflverse odds and stage a resumable semantic change buffer (#471).

Default is read-only. The upstream games.csv must be provided by the caller;
there is no hidden network access, repository publisher or scheduler here.
Use --write-state only with a dedicated, independently persisted technical
state checkout; never direct it into canonical Source/Derived files.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from data_roots import DATA_SOURCE_ROOT
from nfl_source_data_lib.common import download
from odds_observation_buffer import plan_observation, read_upstream_lines, serialize_state


def _load(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected JSON object")
    return data


def _atomic_write(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def fetch_registered_odds(root: Path, destination: Path) -> None:
    """Fetch just the existing registered nflverse games.csv Source artifact."""
    registry = _load(root / DATA_SOURCE_ROOT / "registry.json")
    matches = [row for row in registry.get("datasets", [])
               if row.get("id") == "nflverse.schedule-odds"]
    if len(matches) != 1:
        raise ValueError("Exactly one canonical nflverse.schedule-odds registry entry required")
    source_url = matches[0].get("sourceUrl")
    if source_url != "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv":
        raise ValueError("Unexpected registered NFL odds origin")
    download(source_url, destination)


def run(
    root: Path, *,
    season: int,
    upstream_csv: Path,
    state_input: Path | None = None,
    state_output: Path | None = None,
    observed_at: datetime,
) -> dict:
    source = root / DATA_SOURCE_ROOT / "nfl"
    schedule = _load(source / "schedules" / f"{season}.json")
    odds = _load(source / "schedule-odds" / f"{season}.json")
    expected = {row["GameID"] for row in schedule["Games"]}
    upstream = read_upstream_lines(upstream_csv, season, expected)
    if state_input is not None and not state_input.is_file():
        raise ValueError("Persisted odds state is missing; explicit bootstrap is required")
    state = _load(state_input) if state_input is not None else None
    plan, next_state = plan_observation(
        season=season, schedule=schedule, canonical_odds=odds,
        observed_lines=upstream, previous_state=state, observed_at=observed_at,
    )
    if state_output is not None:
        # Technical state may live in a dedicated isolated branch checkout only.
        if state_output.resolve().is_relative_to(root.resolve()):
            raise ValueError("Odds-buffer state must not be written into the main repository checkout")
        _atomic_write(state_output, serialize_state(next_state))
    return plan


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--season", type=int, required=True)
    upstream = parser.add_mutually_exclusive_group(required=True)
    upstream.add_argument("--upstream-csv", type=Path, help="existing upstream games.csv file")
    upstream.add_argument("--fetch-registered-odds", action="store_true",
                          help="download only the declared nflverse schedule odds Source artifact")
    parser.add_argument("--state-input", type=Path)
    parser.add_argument("--write-state", type=Path,
                        help="explicit durable technical state path, not canonical or App data")
    parser.add_argument("--observed-at", help="ISO8601 timestamp; defaults to actual UTC time")
    args = parser.parse_args()
    try:
        at = (datetime.fromisoformat(args.observed_at.replace("Z", "+00:00"))
              if args.observed_at else datetime.now(timezone.utc))
        with tempfile.TemporaryDirectory(prefix="nfl-odds-observe-") as tmp:
            upstream_csv = args.upstream_csv
            if args.fetch_registered_odds:
                upstream_csv = Path(tmp) / "games.csv"
                fetch_registered_odds(args.repo_root.resolve(), upstream_csv)
            plan = run(
                args.repo_root.resolve(), season=args.season,
                upstream_csv=upstream_csv, state_input=args.state_input,
                state_output=args.write_state, observed_at=at,
            )
    except (ValueError, TypeError, KeyError, OSError, json.JSONDecodeError) as error:
        print(f"odds_observation failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(plan, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
