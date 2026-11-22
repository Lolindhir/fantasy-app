#!/usr/bin/env python3
"""NFL Player Availability Shared-Derived materializer (Issue #1590).

Read-only by default; --write persists data-derived/nfl-player-availability/<season>.json only on a byte difference.
Inputs are persisted facts only: data-derived/nfl-injuries (Shared Derived), and canonical data-source/nfl weekly-rosters,
snap-counts, player-stats, schedules, game-finality. Never raw provider data, never public/data.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from data_roots import DATA_DERIVED_ROOT, DATA_SOURCE_ROOT  # noqa: E402
from derived_data_lib.nfl_player_availability import PRODUCT, derive_nfl_player_availability  # noqa: E402

EXIT_DIFFERENT = 3


def _load(path: Path) -> dict:
    if not path.is_file():
        raise ValueError(f"Input unavailable: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Input not an object: {path}")
    return payload


def _weeks(directory: Path) -> dict[int, dict]:
    if not directory.is_dir():
        return {}
    return {int(p.stem): _load(p) for p in sorted(directory.glob("*.json")) if p.stem.isdigit()}


def serialize(document: dict) -> str:
    """Header fields indented, one record per line: reviewable diffs at a bounded size."""
    head = {k: v for k, v in document.items() if k != "Records"}
    body = json.dumps(head, ensure_ascii=False, indent=2, sort_keys=True)
    lines = ",\n".join("    " + json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(",", ":")) for r in document["Records"])
    records = f'  "Records": [\n{lines}\n  ]' if lines else '  "Records": []'
    return body[:-2] + ",\n" + records + "\n}\n"


def pfr_tokens(nfl: Path) -> dict[str, list[str]]:
    """CanonicalPlayerID -> sorted PFR tokens (IDs.PFR plus IDAliases.PFR) from the canonical identities."""
    tokens: dict[str, list[str]] = {}
    for player in _load(nfl / "identities" / "players.json").get("Players", []):
        own = {player.get("IDs", {}).get("PFR"), *(player.get("IDAliases", {}).get("PFR") or [])}
        own = {t for t in own if isinstance(t, str) and t}
        if own and player.get("CanonicalPlayerID"):
            tokens[player["CanonicalPlayerID"]] = sorted(own)
    return tokens


def participation_plays(nfl: Path, season: int) -> dict[str, dict[str, int]]:
    """GameID -> CanonicalPlayerID -> plays from the compact participation Source projection (empty when the season has none)."""
    path = nfl / "participation" / f"{season}.json"
    if not path.is_file():
        return {}
    return {g["GameID"]: {p: int(n) for p, n in g.get("Players", {}).items()} for g in _load(path).get("Games", [])}


def build(repo_root: Path, season: int, derived_root: Path | None = None) -> dict:
    nfl = repo_root / DATA_SOURCE_ROOT / "nfl"
    derived = derived_root or (repo_root / DATA_DERIVED_ROOT)
    injury_path = derived / "nfl-injuries" / f"{season}.json"
    return derive_nfl_player_availability(
        season,
        injuries=_load(injury_path) if injury_path.is_file() else None,
        rosters=_weeks(nfl / "weekly-rosters" / str(season)),
        snap_counts=_weeks(nfl / "snap-counts" / str(season)),
        player_stats=_weeks(nfl / "player-stats" / str(season)),
        schedule=_load(nfl / "schedules" / f"{season}.json"),
        finality=_load(nfl / "game-finality" / f"{season}.json"),
        player_pfr_tokens=pfr_tokens(nfl),
        participation_plays=participation_plays(nfl, season),
    )


def materialize(repo_root: Path, season: int, *, out_root: Path | None = None, write: bool = False) -> dict:
    out = out_root or (repo_root / DATA_DERIVED_ROOT)
    document = build(repo_root, season, out)
    target = out / PRODUCT / f"{season}.json"
    serialized = serialize(document)
    unchanged = target.is_file() and target.read_text(encoding="utf-8") == serialized
    if write and not unchanged:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(serialized, encoding="utf-8")
    return {
        "Product": PRODUCT, "Season": season, "RecordCount": document["Quality"]["RecordCount"],
        "StateCounts": document["Quality"]["StateCounts"], "OutputPath": str(target),
        "Unchanged": unchanged, "Written": bool(write and not unchanged), "WouldWrite": not unchanged,
    }


def _has_roster_status(season_dir: Path) -> bool:
    """A roster season is a signal source only when its status column is populated (older seasons carry no status)."""
    first = next(iter(sorted(season_dir.glob("*.json"))), None)
    return first is not None and any(r.get("Status") is not None for r in _load(first).get("Records", []))


def discover_seasons(repo_root: Path, derived_root: Path | None = None) -> list[int]:
    """Seasons with at least one signal source: an injury product or a weekly roster with status, and a schedule plus finality."""
    nfl = repo_root / DATA_SOURCE_ROOT / "nfl"
    derived = derived_root or (repo_root / DATA_DERIVED_ROOT)
    injury = {int(p.stem) for p in (derived / "nfl-injuries").glob("*.json") if p.stem.isdigit()}
    rostered = {
        int(p.name) for p in ((nfl / "weekly-rosters").iterdir() if (nfl / "weekly-rosters").is_dir() else ())
        if p.name.isdigit() and _has_roster_status(p)
    }
    scheduled = {int(p.stem) for p in (nfl / "schedules").glob("*.json") if p.stem.isdigit()}
    finals = {int(p.stem) for p in (nfl / "game-finality").glob("*.json") if p.stem.isdigit()}
    seasons = sorted((injury | rostered) & scheduled & finals)
    if not seasons:
        raise ValueError("No NFL player availability seasons discovered")
    return seasons


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--out-root", type=Path, help="override Shared Derived root (isolated test dir)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--season", type=int, action="append")
    group.add_argument("--all-seasons", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true", help="read-only; exit 3 if a partition differs")
    args = parser.parse_args()
    if args.write and args.check:
        parser.error("--write and --check are mutually exclusive")
    try:
        root = args.repo_root.resolve()
        seasons = discover_seasons(root, args.out_root) if args.all_seasons else sorted(set(args.season))
        previews = [materialize(root, s, out_root=args.out_root) for s in seasons]
        results = [materialize(root, s, out_root=args.out_root, write=True) for s in seasons] if args.write else previews
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        print(f"nfl_player_availability_materialize failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps({"Results": results}, ensure_ascii=False, indent=2))
    return EXIT_DIFFERENT if args.check and any(r["WouldWrite"] for r in previews) else 0


if __name__ == "__main__":
    raise SystemExit(main())
