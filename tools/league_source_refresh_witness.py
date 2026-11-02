#!/usr/bin/env python3
"""Source-owned, no-op-safe full League refresh witness (Issue #1263 C9c.3).

This is NOT an App Timestamps replacement for consumers yet. A witness proves
one previously finalized canonical league week was covered by a successful
full Sleeper acquisition and canonical materialization. Only the existing full
League Source publisher may call complete, after its second-pass no-op check.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from data_roots import DATA_SOURCE_ROOT
from derived_data_lib.week_finality import resolve_week_finality

WITNESS_ROOT = "data-source/_sync/league-refresh-witnesses"
RAW_DATASETS = {
    "league.json": "sleeper.league",
    "members.json": "sleeper.league-members",
    "rosters.json": "sleeper.league-rosters",
    "matchups/week-{week}.json": "sleeper.matchups",
    "transactions/week-{week}.json": "sleeper.transactions",
}
CANONICAL_FILES = (
    "league.json", "members.json", "rosters.json",
    "winners-bracket.json", "losers-bracket.json",
    "matchups/week-{week}.json", "transactions/week-{week}.json",
)


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _digest(value: Any) -> str:
    content = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _file_sha(path: Path) -> str:
    if not path.is_file():
        raise ValueError(f"Required witness input is missing: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _week_finality_fingerprint(root: Path, season: int, week: int) -> str:
    path = root / DATA_SOURCE_ROOT / "nfl" / "game-finality" / f"{season}.json"
    data = _load(path)
    rows = [r for r in data.get("Weeks", []) if r.get("GameType") == "REG" and r.get("Week") == week]
    if len(rows) != 1 or rows[0].get("WeekFinal") is not True:
        raise ValueError(f"Week {season}/{week} has no unique final NFL week")
    row = rows[0]
    games = sorted(
        ({"GameID": g.get("GameID"), "Final": g.get("Final")} for g in data.get("Games", [])
         if g.get("GameType") == "REG" and g.get("Week") == week),
        key=lambda g: str(g["GameID"]),
    )
    if (not games or len(games) != row.get("ApplicableGameCount")
            or row.get("FinalGameCount") != len(games)
            or any(g["Final"] is not True or not g["GameID"] for g in games)):
        raise ValueError(f"Inconsistent finalized game evidence for {season}/{week}")
    return _digest({"row": row, "games": games})


def _current_candidates(root: Path) -> list[dict[str, Any]]:
    league_root = root / DATA_SOURCE_ROOT / "leagues"
    candidates: list[dict[str, Any]] = []
    for path in sorted(league_root.glob("*/manifest.json")):
        manifest = _load(path)
        league_id = manifest.get("CanonicalLeagueID")
        season_id = manifest.get("CurrentCanonicalLeagueSeasonID")
        provider_id = str(manifest.get("CurrentProviderLeagueID") or "")
        if (not isinstance(league_id, str)
                or not re.fullmatch(r"[A-Za-z0-9_-]+", league_id)
                or league_id != path.parent.name or not provider_id.isdigit()):
            raise ValueError(f"Invalid current League identity: {path}")
        seasons = manifest.get("Seasons")
        selected = [s for s in seasons if isinstance(s, dict) and s.get("CanonicalLeagueSeasonID") == season_id] if isinstance(seasons, list) else []
        if len(selected) != 1:
            raise ValueError(f"Ambiguous current canonical League season: {path}")
        s = selected[0]
        season = s.get("Season")
        mappings = s.get("ProviderMappings")
        if (type(season) is not int or season < 2000 or not isinstance(mappings, list)
                or sum(1 for m in mappings if isinstance(m, dict) and m.get("Provider") == "Sleeper"
                       and str(m.get("ProviderLeagueID")) == provider_id) != 1):
            raise ValueError(f"Invalid current Season/Provider mapping: {path}")
        finality = resolve_week_finality(root, league_id, season)
        week = finality["LeagueScoredWeek"]
        if not week:
            continue
        row = next((x for x in finality["Weeks"] if x["Week"] == week), None)
        if row is None or not row["LeagueScored"] or not row["NflGamesFinal"]:
            raise ValueError("Finalized candidate lacks required shared evidence")
        candidates.append({
            "CanonicalLeagueID": league_id,
            "CanonicalLeagueSeasonID": season_id,
            "ProviderLeagueID": provider_id,
            "Season": season,
            "Week": week,
            "FinalityFingerprint": _week_finality_fingerprint(root, season, week),
        })
    return candidates


def prepare(root: Path) -> dict[str, Any]:
    return {"schemaVersion": 1, "scope": "full", "candidates": _current_candidates(root)}


def _inputs(root: Path, candidate: dict[str, Any]) -> list[dict[str, str]]:
    league, season, week = candidate["CanonicalLeagueID"], candidate["Season"], candidate["Week"]
    provider = candidate["ProviderLeagueID"]
    raw_root = Path(DATA_SOURCE_ROOT) / "providers/sleeper/leagues" / provider
    canon_root = Path(DATA_SOURCE_ROOT) / "leagues" / league / "seasons" / str(season)
    paths = [Path(DATA_SOURCE_ROOT) / "leagues" / league / "manifest.json"]
    for template in CANONICAL_FILES:
        paths.append(canon_root / template.format(week=week))
    for template, dataset in RAW_DATASETS.items():
        raw = raw_root / template.format(week=week)
        metadata = raw.with_name(raw.stem + ".metadata.json")
        payload = _load(root / raw)
        meta = _load(root / metadata)
        if (meta.get("Dataset") != dataset or meta.get("Provider") != "Sleeper"
                or str(meta.get("ProviderLeagueID")) != provider
                or meta.get("Season") != season
                or ("/week-" in str(raw) and meta.get("Week") != week)
                or meta.get("ContentSha256") != _digest(payload)):
            raise ValueError(f"Raw League acquisition metadata does not validate: {metadata}")
        paths.extend((raw, metadata))
    return [{"path": p.as_posix(), "sha256": _file_sha(root / p)}
            for p in sorted(paths, key=str)]


def complete(root: Path, preflight: dict[str, Any], raw: dict, canonical: dict,
             *, completed_at: datetime) -> dict[str, int]:
    if preflight.get("schemaVersion") != 1 or preflight.get("scope") != "full":
        raise ValueError("Only preflighted full acquisition may publish a witness")
    if completed_at.tzinfo is None or completed_at.utcoffset() is None:
        raise ValueError("Completion clock must be timezone-aware")
    before = preflight.get("candidates")
    after = _current_candidates(root)
    if not isinstance(before, list) or before != after:
        raise ValueError("Finality/League identity changed during full acquisition; witness denied")
    raw_by_id = {r["CanonicalLeagueID"]: r for r in raw.get("Leagues", [])}
    canon_by_id = {r["CanonicalLeagueID"]: r for r in canonical.get("Leagues", [])}
    if (len(raw_by_id) != len(raw.get("Leagues", []))
            or len(canon_by_id) != len(canonical.get("Leagues", []))):
        raise ValueError("Ambiguous League results")
    changed = 0
    for item in after:
        league, season, week = item["CanonicalLeagueID"], item["Season"], item["Week"]
        acquisition = raw_by_id.get(league, {})
        materialization = canon_by_id.get(league, {})
        if (acquisition.get("DatasetPartitions", 0) < 1
                or materialization.get("MaterializationScope") != "full"
                or materialization.get("CanonicalFiles", 0) < 1):
            raise ValueError(f"Missing successful full League acquisition/materialization: {league}")
        inputs = _inputs(root, item)
        fingerprint = _digest({"identity": item, "inputs": inputs})
        path = root / WITNESS_ROOT / league / f"{season}-week-{week:02d}.json"
        previous = _load(path) if path.is_file() else None
        if previous is not None and previous.get("InputsFingerprint") == fingerprint:
            continue  # A successful identical refresh is NOT a daily heartbeat commit.
        payload = {
            "schemaVersion": 1, **item, "Scope": "full",
            "SucceededAtUtc": completed_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "Inputs": inputs, "InputsFingerprint": fingerprint,
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
        changed += 1
    return {"candidates": len(after), "changed": changed}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "complete"))
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--preflight", type=Path)
    parser.add_argument("--raw-result", type=Path)
    parser.add_argument("--canonical-result", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            result = prepare(args.repo_root)
        else:
            if not args.preflight or not args.raw_result or not args.canonical_result:
                parser.error("complete requires --preflight, --raw-result and --canonical-result")
            result = complete(args.repo_root, _load(args.preflight), _load(args.raw_result),
                              _load(args.canonical_result), completed_at=datetime.now(timezone.utc))
    except (OSError, KeyError, TypeError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
