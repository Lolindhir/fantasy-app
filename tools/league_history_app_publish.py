#!/usr/bin/env python3
"""Consumer generator: App-shaped Transactions and Drafts from the league history products (ADR-057, Issue #999).

Takes the Shared Derived products (data-derived/league-transactions and league-drafts, or the in-memory
result of derived_data_lib.league_history.build_history) and renders exactly the files the App reads today:

  public/data/Transactions.json                       Transactions of the current season
  public/data/past_seasons/Transactions/Transactions_<season>.json   earlier seasons
  public/data/Drafts.json                             current season (any status) plus open future drafts
  public/data/past_seasons/Drafts/Drafts_<season>.json   completed drafts of one season

The consumer owns the presentation fields (DisplayStatus, DisplayDraftKey, DisplayAbrDraftKey,
DisplayDraftType, DisplayPick); the products carry none of them. Since Issue #999 step 6 the App contract is
slim: the fields in the *_DROPPED tuples are not delivered and past Drafts files are always a list.

Usage:
  league_history_app_publish.py compare [--league nfl-reise]   exact comparison against public/data
  league_history_app_publish.py write   [--league nfl-reise]   write the App files (semantic no-op, Timestamps.json)

`write` keeps the last good files when the history cannot be built (fail-closed product) and reports the
problem as a GitHub warning annotation; it exits 0 unless --fail-on-error is given.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from derived_data_lib.league_drafts import DraftBuildError  # noqa: E402
from derived_data_lib.league_history import HistoryResult, build_history  # noqa: E402
from league_history_sources import load_inputs  # noqa: E402

# Slim App contract (Issue #999 step 6, field list approved by Robert 2026-10-15). Fields the products carry but
# the App contract omits are dropped by _slim; every other field must have a position here (see _ordered).
# Draft-level SleeperDraftID stays only while Fantasy Management reads it (resolve_active_fa_draft in the FA
# board); remove it from DRAFT_FIELD_ORDER as soon as FM no longer reads it (league-history.yaml, Issue #999).
TRANSACTION_PICK_ORDER = (
    "DraftType", "DraftKey", "Season", "Round", "OriginalOwnerRosterID", "PreviousOwnerRosterID",
    "NewOwnerRosterID", "PickKey", "DisplayPick", "PlayerID", "PlayerName",
)
TRANSACTION_DROPPED = ("Status",)  # the product only holds completed transactions
TRANSACTION_PICK_DROPPED = (
    "DraftCode", "DraftSource", "PickStatus", "SleeperDraftID", "DraftInstance", "PositionInRound", "OverallPick",
    "SleeperPickNo",
)
DRAFT_FIELD_ORDER = (
    "DraftKey", "DisplayDraftKey", "DisplayAbrDraftKey", "Season", "DraftType", "DraftInstance",
    "DisplayDraftType", "DraftNo", "SleeperDraftID", "SleeperStatus", "SleeperStartTime", "DraftStartTimeUtc",
    "Status", "DisplayStatus", "Settings", "Picks",
)
DRAFT_DROPPED = ("DraftCode", "DraftSource", "PickSource", "OrderSource", "OrderMode")
DRAFT_SETTINGS_DROPPED = ("Teams",)
PICK_FIELD_ORDER = (
    "PickKey", "DraftKey", "Season", "DraftType", "DraftInstance", "Round", "PositionInRound", "OverallPick",
    "DisplayPick", "OriginalOwnerRosterID", "CurrentOwnerRosterID", "IsCurrentlyTraded", "TradeHistory",
    "PlayerID", "PlayerName", "Status", "SleeperPickNo", "SleeperPickedBy",
)
PICK_DROPPED = ("LeagueID", "DraftCode", "TradeSource", "WasTraded")
TRADE_HISTORY_DROPPED = ("Source", "DraftSource")


def display_pick(round_no: int, position: int | None) -> str:
    """Format-DraftDisplayPick."""
    return f"Round {round_no}" if position is None else f"{round_no}.{position:02d}"


def display_type(draft_type: str) -> str:
    return draft_type.replace("_", " ").strip()


def type_abbreviation(draft_type: str) -> str:
    parts = [part for part in draft_type.split("_") if part.strip()]
    return "".join(part[0].upper() for part in parts) if parts else draft_type.upper()


def display_status(status: str, season: str, league_year: int) -> str:
    """DraftUtils.psm1::Get-DraftDisplayStatus (the effective variant in the committed files)."""
    if status == "PreDraft":
        return "Upcoming"
    if status == "Drafting":
        return "Live"
    if status == "Complete":
        return "Completed"
    if status == "Virtual":
        return "Upcoming" if int(season) == league_year else "Future"
    return status


def _slim(source: dict[str, Any], dropped: tuple[str, ...]) -> dict[str, Any]:
    return {key: value for key, value in source.items() if key not in dropped}


def _ordered(source: dict[str, Any], order: tuple[str, ...]) -> dict[str, Any]:
    unknown = [key for key in source if key not in order]
    if unknown:
        raise ValueError(f"Fields without a position in the App contract: {unknown}")
    return {key: source[key] for key in order if key in source}


# ---------------------------------------------------------------------------- transactions


def app_transaction(transaction: dict[str, Any]) -> dict[str, Any]:
    result = _slim(transaction, TRANSACTION_DROPPED)
    picks = []
    for pick in transaction["DraftPicks"]:
        entry = dict(pick)
        if entry.get("PickKey"):
            entry["DisplayPick"] = display_pick(int(entry["Round"]), entry.get("PositionInRound"))
        picks.append(_ordered(_slim(entry, TRANSACTION_PICK_DROPPED), TRANSACTION_PICK_ORDER))
    result["DraftPicks"] = picks
    return result


def app_transactions(transactions_by_season: dict[int, list[dict[str, Any]]], league_year: int) -> dict[str, Any]:
    return {
        "current": [app_transaction(item) for item in transactions_by_season.get(league_year, [])],
        "past": {
            season: [app_transaction(item) for item in items]
            for season, items in sorted(transactions_by_season.items()) if season < league_year
        },
    }


# ---------------------------------------------------------------------------- drafts


def _app_draft_base(draft: dict[str, Any], excluded: tuple[str, ...] = ()) -> dict[str, Any]:
    entry = _slim(draft, ("ProviderLeagueID", *DRAFT_DROPPED, *excluded))
    if isinstance(entry.get("Settings"), dict):
        entry["Settings"] = _slim(entry["Settings"], DRAFT_SETTINGS_DROPPED)
    return entry


def _app_pick(pick: dict[str, Any]) -> dict[str, Any]:
    entry = _slim(pick, PICK_DROPPED)
    entry["DisplayPick"] = display_pick(int(pick["Round"]), pick.get("PositionInRound"))
    if "TradeHistory" in entry:
        entry["TradeHistory"] = [_slim(item, TRADE_HISTORY_DROPPED) for item in entry["TradeHistory"]]
    return _ordered(entry, PICK_FIELD_ORDER)


def app_current_draft(draft: dict[str, Any], league_year: int) -> dict[str, Any]:
    entry = _app_draft_base(draft)
    entry["DisplayDraftKey"] = f"{draft['Season']} {display_type(draft['DraftType'])}" + (
        f" #{draft['DraftInstance']}" if int(draft["DraftInstance"]) > 1 else "")
    entry["DisplayAbrDraftKey"] = f"{draft['Season']} {type_abbreviation(draft['DraftType'])}" + (
        f" #{draft['DraftInstance']}" if int(draft["DraftInstance"]) > 1 else "")
    entry["DisplayDraftType"] = display_type(draft["DraftType"])
    entry["DisplayStatus"] = display_status(draft["Status"], draft["Season"], league_year)
    entry["Picks"] = [_app_pick(pick) for pick in draft["Picks"]]
    return _ordered(entry, DRAFT_FIELD_ORDER)


def app_history_draft(draft: dict[str, Any], occurrence: int, count: int) -> dict[str, Any]:
    """New-DraftHistoryOutputOrderAware: no start-time fields, occurrence-based display keys."""
    suffix = f" #{occurrence}" if count > 1 else ""
    entry = _app_draft_base(draft, ("SleeperStartTime", "DraftStartTimeUtc"))
    entry["DisplayDraftKey"] = f"{draft['Season']} {display_type(draft['DraftType'])}{suffix}"
    entry["DisplayAbrDraftKey"] = f"{draft['Season']} {type_abbreviation(draft['DraftType'])}{suffix}"
    entry["DisplayDraftType"] = display_type(draft["DraftType"])
    entry["DisplayStatus"] = display_status(draft["Status"], draft["Season"], 0)
    entry["Picks"] = [_app_pick(pick) for pick in draft["Picks"]]
    return _ordered(entry, DRAFT_FIELD_ORDER)


def app_drafts(drafts_by_season: dict[int, list[dict[str, Any]]], league_year: int) -> dict[str, Any]:
    current = [
        app_current_draft(draft, league_year)
        for season, drafts in sorted(drafts_by_season.items()) if season >= league_year
        for draft in sorted(drafts, key=lambda d: d["DraftNo"])
    ]
    past: dict[int, Any] = {}
    for season, drafts in sorted(drafts_by_season.items()):
        if season > league_year:
            continue
        completed = sorted((d for d in drafts if d["Status"] == "Complete"), key=lambda d: (d["DraftNo"], d["DraftKey"]))
        if not completed:
            continue
        counts: dict[str, int] = {}
        for draft in completed:
            counts[draft["DraftType"]] = counts.get(draft["DraftType"], 0) + 1
        seen: dict[str, int] = {}
        entries = []
        for draft in completed:
            seen[draft["DraftType"]] = seen.get(draft["DraftType"], 0) + 1
            entries.append(app_history_draft(draft, seen[draft["DraftType"]], counts[draft["DraftType"]]))
        past[season] = entries
    return {"current": current, "past": past}


def render(history: HistoryResult, league_year: int) -> dict[str, Any]:
    return {
        "Transactions": app_transactions(history.transactions, league_year),
        "Drafts": app_drafts(history.drafts, league_year),
    }


# ---------------------------------------------------------------------------- writing


def _dump(payload: Any) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def write_files(repo_root: Path, rendered: dict[str, Any], now: datetime | None = None) -> list[str]:
    """Write the rendered App files only where they differ semantically; return the changed relative paths.

    Timestamps.json[Transactions|Drafts] follows the current-season file only, like Save-JsonFile did.
    Historical files carry no timestamp. A file is never deleted.
    """
    data = repo_root / "public" / "data"
    stamp = (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
    changed: list[str] = []
    stamped: list[str] = []

    def put(relative: str, payload: Any, timestamp_key: str | None = None) -> None:
        path = data / relative
        if path.is_file() and not _difference(payload, _load(path)):
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_dump(payload), encoding="utf-8")
        changed.append(f"public/data/{relative}")
        if timestamp_key:
            stamped.append(timestamp_key)

    put("Transactions.json", rendered["Transactions"]["current"], "Transactions")
    for season, items in rendered["Transactions"]["past"].items():
        put(f"past_seasons/Transactions/Transactions_{season}.json", items)
    put("Drafts.json", rendered["Drafts"]["current"], "Drafts")
    for season, payload in rendered["Drafts"]["past"].items():
        put(f"past_seasons/Drafts/Drafts_{season}.json", payload)

    if stamped:
        stamp_path = data / "Timestamps.json"
        timestamps = _load(stamp_path) if stamp_path.is_file() else {}
        for key in stamped:
            timestamps[key] = stamp
        stamp_path.write_text(_dump(timestamps), encoding="utf-8")
        changed.append("public/data/Timestamps.json")
    return changed


# ---------------------------------------------------------------------------- shadow comparison


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _difference(left: Any, right: Any, path: str = "$") -> list[str]:
    """Exact semantic comparison: dict key order is irrelevant, list order and value types are not."""
    if type(left) is not type(right):
        return [f"{path}: type {type(left).__name__} != {type(right).__name__} ({left!r} vs {right!r})"]
    if isinstance(left, dict):
        found = [f"{path}.{key}: missing in expected" for key in left.keys() - right.keys()]
        found += [f"{path}.{key}: missing in actual" for key in right.keys() - left.keys()]
        for key in left.keys() & right.keys():
            found += _difference(left[key], right[key], f"{path}.{key}")
        return found
    if isinstance(left, list):
        if len(left) != len(right):
            return [f"{path}: length {len(left)} != {len(right)}"]
        found = []
        for index, (a, b) in enumerate(zip(left, right)):
            found += _difference(a, b, f"{path}[{index}]")
        return found
    return [] if left == right else [f"{path}: {left!r} != {right!r}"]


def shadow_compare(repo_root: Path, rendered: dict[str, Any]) -> dict[str, list[str]]:
    """Compare the rendered App files with the files on disk; key = relative path, value = differences."""
    data = repo_root / "public" / "data"
    results: dict[str, list[str]] = {}

    def check(relative: str, actual: Any) -> None:
        path = data / relative
        results[f"public/data/{relative}"] = [f"file missing on disk"] if not path.is_file() else _difference(actual, _load(path))

    check("Transactions.json", rendered["Transactions"]["current"])
    for season, items in rendered["Transactions"]["past"].items():
        check(f"past_seasons/Transactions/Transactions_{season}.json", items)
    check("Drafts.json", rendered["Drafts"]["current"])
    for season, payload in rendered["Drafts"]["past"].items():
        check(f"past_seasons/Drafts/Drafts_{season}.json", payload)
    # Files on disk that no rendered file corresponds to would be silently ignored otherwise.
    expected = {f"Transactions_{s}.json" for s in rendered["Transactions"]["past"]}
    for path in sorted((data / "past_seasons" / "Transactions").glob("Transactions_*.json")):
        if path.name not in expected:
            results[f"public/data/past_seasons/Transactions/{path.name}"] = ["file on disk has no rendered counterpart"]
    expected = {f"Drafts_{s}.json" for s in rendered["Drafts"]["past"]}
    for path in sorted((data / "past_seasons" / "Drafts").glob("Drafts_*.json")):
        if path.name not in expected:
            results[f"public/data/past_seasons/Drafts/{path.name}"] = ["file on disk has no rendered counterpart"]
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    sub = parser.add_subparsers(dest="command", required=True)
    compare = sub.add_parser("compare", help="render the App files in memory and compare them exactly with public/data")
    compare.add_argument("--league", default="nfl-reise")
    write = sub.add_parser("write", help="write the App files from the history (semantic no-op)")
    write.add_argument("--league", default="nfl-reise")
    write.add_argument("--fail-on-error", action="store_true", help="exit 1 when the history cannot be built")
    return parser.parse_args()


def run_write(args: argparse.Namespace) -> int:
    try:
        inputs = load_inputs(args.repo_root, args.league)
        history = build_history(inputs)
        if history.unresolved:
            raise DraftBuildError(f"Transaction picks without a unique draft identity: {history.unresolved}")
        rendered = render(history, inputs.league_year)
    except Exception as error:  # fail-closed product: keep the last good files, report visibly
        print(f"::warning title=League history not published::{type(error).__name__}: {error}", file=sys.stderr)
        print("League history could not be built; the last good App files stay unchanged.", file=sys.stderr)
        return 1 if args.fail_on_error else 0
    changed = write_files(args.repo_root, rendered)
    print("\n".join(f"wrote {name}" for name in changed) if changed else "No changes - update skipped.")
    return 0


def main() -> int:
    args = parse_args()
    if args.command == "write":
        return run_write(args)
    inputs = load_inputs(args.repo_root, args.league)
    history = build_history(inputs)
    if history.unresolved:
        print(f"Transaction picks without a unique draft identity: {history.unresolved}", file=sys.stderr)
        return 1
    results = shadow_compare(args.repo_root, render(history, inputs.league_year))
    failed = 0
    for name, differences in sorted(results.items()):
        print(f"{'OK  ' if not differences else 'DIFF'} {name}" + (f" ({len(differences)} differences)" if differences else ""))
        for line in differences[:20]:
            print(f"     {line}")
        failed += 1 if differences else 0
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
