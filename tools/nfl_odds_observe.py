#!/usr/bin/env python3
"""Read-only canonical nflverse Spread/Total observation probe (#471).

A caller may poll upstream frequently without touching the repository. This
probe validates current-season GameIDs against the canonical NFL schedule and
compares observations with the last *published* canonical odds snapshot. It
never writes Source, Derived, scheduler checkpoints, or commits; a future
scoped publisher must perform final validation again against latest main.

Small differences are published only in a caller-supplied fixed batch slot
(or from a separately durable pending_since), never just because the source
snapshot is many hours old. Bookmaker price changes cannot trigger a publish.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from data_roots import DATA_SOURCE_ROOT
from nfl_source_data_lib.common import clean, as_float, download
from nfl_source_data_lib.source_projection import project_schedule_odds
from odds_change_gate import OddsGateConfig, evaluate_games

REQUIRED = ("game_id", "spread_line", "total_line")
FIELDS = ("SpreadLine", "TotalLine")


def parse_time(value: str) -> datetime:
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ValueError("Observation time must contain an explicit timezone")
    return stamp


def _read_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid JSON object: {path}")
    return payload


def _line(value: Any, game_id: str, field: str) -> float | None:
    original = clean(value)
    if original is None:
        return None
    converted = as_float(original)
    if converted is None or not math.isfinite(converted):
        raise ValueError(f"{game_id}: invalid {field}={value!r}")
    return converted


def candidate_lines(source: Path, season: int, expected_game_ids: set[str]) -> dict[str, dict]:
    """Only 2026/current-season game_id rows matter, but require complete coverage."""
    result: dict[str, dict] = {}
    with source.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or any(col not in reader.fieldnames for col in REQUIRED):
            raise ValueError(f"Source lacks mandatory game/line columns: {source}")
        for row in reader:
            game_id = clean(row.get("game_id"))
            if not game_id:
                raise ValueError("Upstream contains empty game_id")
            if not game_id.startswith(f"{season}_"):
                continue
            if game_id not in expected_game_ids:
                raise ValueError(f"Unknown current-season GameID: {game_id}")
            if game_id in result:
                raise ValueError(f"Duplicate current-season GameID: {game_id}")
            spread = _line(row.get("spread_line"), game_id, "spread_line")
            total = _line(row.get("total_line"), game_id, "total_line")
            if total is not None and total <= 0:
                raise ValueError(f"{game_id}: invalid nonpositive total")
            if total is not None and spread is not None and abs(spread) > total:
                raise ValueError(f"{game_id}: spread exceeds total")
            result[game_id] = {"SpreadLine": spread, "TotalLine": total}
    missing = expected_game_ids - set(result)
    if missing:
        raise ValueError(f"Missing {len(missing)} canonical GameIDs in upstream: {sorted(missing)[:3]}")
    return result


def observe(
    root: Path, season: int, projected_csv: Path, observed_at: datetime,
    *, batch_window_due: bool = False, config: OddsGateConfig = OddsGateConfig(),
) -> dict:
    base = root / DATA_SOURCE_ROOT
    schedule = _read_json(base / "nfl" / "schedules" / f"{season}.json")
    market = _read_json(base / "nfl" / "schedule-odds" / f"{season}.json")
    metadata = _read_json(base / "providers" / "nflverse" / "schedule-odds" / "metadata.json")
    if (schedule.get("Season") != season or market.get("Season") != season
            or market.get("SourceDataset") != "nflverse.schedule-odds"):
        raise ValueError("Incompatible canonical Source season/dataset")
    scheduled = schedule.get("Games")
    published_games = market.get("Games")
    if not isinstance(scheduled, list) or not isinstance(published_games, list):
        raise ValueError("Canonical Source Games must be lists")
    ids = [g.get("GameID") for g in scheduled]
    if len(set(ids)) != len(ids) or not ids or any(not isinstance(k, str) for k in ids):
        raise ValueError("Invalid or duplicate canonical GameIDs")
    published = {g["GameID"]: g for g in published_games}
    if len(published) != len(published_games) or set(published) != set(ids):
        raise ValueError("Canonical Schedule/Odds GameID mismatch")
    observed = candidate_lines(projected_csv, season, set(ids))
    checkpoint = metadata.get("retrievedAtUtc")
    if not isinstance(checkpoint, str):
        raise ValueError("Published Source has no retrieval timestamp")
    published_at = parse_time(checkpoint)
    if published_at > observed_at:
        raise ValueError("Source timestamp is in the future relative to observation")
    decisions = evaluate_games(
        published=published, observed=observed,
        published_at_by_game={game_id: published_at for game_id in ids},
        observed_at=observed_at, batch_window_due=batch_window_due, config=config,
    )
    reasons: dict[str, int] = {}
    publish = []
    for d in decisions:
        reasons[d.reason] = reasons.get(d.reason, 0) + 1
        if d.publish:
            publish.append({
                "GameID": d.game_id, "Reason": d.reason,
                "SpreadDelta": str(d.spread_delta) if d.spread_delta is not None else None,
                "TotalDelta": str(d.total_delta) if d.total_delta is not None else None,
            })
    # This is an advisory preflight; production must re-fetch/revalidate after a race.
    return {
        "Season": season,
        "ObservedAtUtc": observed_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "PublishedEvidenceAtUtc": published_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "GameCount": len(ids),
        "BatchWindowDue": batch_window_due,
        "Reasons": reasons,
        "PublishableGameCount": len(publish),
        "Publishable": publish,
        "WriteAttempted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--season", type=int, required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--candidate", type=Path, help="pre-existing projected CSV for offline evaluation")
    source.add_argument("--fetch", action="store_true", help="download and project upstream to a temporary file, never commit")
    parser.add_argument("--observed-at", help="timezone-aware ISO instant; default actual probe start UTC")
    parser.add_argument("--batch-window-due", action="store_true",
                        help="explicit scheduled hourly batch slot for small changes")
    args = parser.parse_args()
    try:
        observed_at = parse_time(args.observed_at) if args.observed_at else datetime.now(timezone.utc)
        with tempfile.TemporaryDirectory(prefix="nfl-odds-observation-") as directory:
            if args.fetch:
                registry = _read_json(args.repo_root / DATA_SOURCE_ROOT / "registry.json")
                dataset = next(
                    d for d in registry["datasets"] if d["id"] == "nflverse.schedule-odds"
                )
                downloaded = Path(directory) / "games.csv"
                projected = Path(directory) / "odds.csv"
                download(dataset["sourceUrl"], downloaded)
                project_schedule_odds(downloaded, projected)
                candidate = projected
            else:
                candidate = args.candidate
            result = observe(args.repo_root.resolve(), args.season, candidate, observed_at,
                             batch_window_due=args.batch_window_due)
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, TypeError, StopIteration,
            json.JSONDecodeError, csv.Error) as error:
        print(f"nfl_odds_observe failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
