#!/usr/bin/env python3
"""Read-only restore probe for the Shared Derived products of every league (#471).

Each product is rebuilt in two isolated temporary roots and compared with the published files:

* empty:  only data-source, data-meta and public/requests are visible; the product is built twice.
* normal: published data-derived plus historical Standings are visible, as in a
          productive run; the product is built once. The published Players hold
          seed was retired by ADR-076 and is never copied or loaded.
* published: the files in the repository.

Per product (and league) the three-way comparison gives one status:

* ready:             empty == normal == published, the second empty pass is a no-op.
* stale-published:   empty == normal, only the published files are behind (hint, not an error).
* latent-blocker:    the product only builds with the transitional Standings input (Issue #987, hint).
* restore-defect:    empty != normal, the product silently depends on previously generated output (error).
* nondeterministic:  the second empty pass changed output (error).
* blocked:           a source is not ready or a build failed (error).

This is NOT a publisher; nothing in the repository is written.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from data_roots import DATA_DERIVED_ROOT, DATA_META_ROOT, DATA_SOURCE_ROOT
from derived_data import (
    LEAGUE_DRAFTS, LEAGUE_STANDINGS, LEAGUE_TRANSACTIONS,
    materialize_league_history, materialize_league_standings, materialize_player_valuation,
)
from historical_pwf_batch import materialize_historical
from league_metadata import list_league_ids
from nfl_games_materialize import discover_seasons, materialize as materialize_nfl_games
from team_week_performance_materialize import materialize_all_finalized

PLAYER_VALUATION = "player-valuation"
PLAYER_WEEK_FANTASY = "player-week-fantasy"
TEAM_WEEK_PERFORMANCE = "team-week-performance"
NFL_GAMES = "nfl-games"

# Stable report order; official TeamWeekPerformance is independent of PWF score parity.
PRODUCTS = (
    PLAYER_VALUATION, LEAGUE_TRANSACTIONS, LEAGUE_DRAFTS, LEAGUE_STANDINGS,
    PLAYER_WEEK_FANTASY, TEAM_WEEK_PERFORMANCE, NFL_GAMES,
)
GLOBAL_PRODUCTS = frozenset({NFL_GAMES})

FAILING = frozenset({"blocked", "nondeterministic", "restore-defect"})
HINTS = frozenset({"stale-published", "latent-blocker"})
LATENT_STANDINGS_ISSUE = "#987"
STANDINGS_MARKER = "transitional Standings"
# Only the historical Standings shadow is copied; the retired player seed is excluded.
PUBLISHED_APP_FILES = ("Standings.json",)
EXAMPLE_LIMIT = 12

Unit = tuple[str, str | None]


def unit_key(unit: Unit) -> str:
    product, league = unit
    return product if league is None else f"{product}/{league}"


def _files(root: Path, unit: Unit) -> dict[str, str]:
    """Relative path -> sha256 of every product file (of one league for league products)."""
    product, league = unit
    directory = root / DATA_DERIVED_ROOT / product
    if league is not None:
        directory = directory / league
    if not directory.is_dir():
        return {}
    return {
        p.relative_to(directory).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(directory.rglob("*.json"))
    }


def _written(summary: dict[str, Any]) -> int:
    return sum(int(season["Written"]) for season in summary["Seasons"])


def _held(summary: dict[str, Any]) -> int:
    return sum(int(x.get("HeldRowsAcrossSnapshots", 0)) for x in summary["Seasons"])


def _blocked_reason(report: dict[str, Any]) -> str:
    reasons = [str(w.get("Reason")) for w in report.get("Weeks", []) if w.get("Status") == "blocked"]
    return f"{report['BlockedCount']} blocked weeks, first: {reasons[:2]}"


def _build(unit: Unit, root: Path) -> tuple[int, int]:
    """Run the productive generator of one unit in `root`; return (writes, held rows)."""
    product, league = unit
    output = root / DATA_DERIVED_ROOT
    if product == PLAYER_VALUATION:
        summary = materialize_player_valuation(root, output, league, None, False)
        return _written(summary), _held(summary)
    if product in (LEAGUE_TRANSACTIONS, LEAGUE_DRAFTS):
        return _written(materialize_league_history(root, output, league, product, None, False)), 0
    if product == LEAGUE_STANDINGS:
        return _written(materialize_league_standings(root, output, league, None, False)), 0
    if product == PLAYER_WEEK_FANTASY:
        report = materialize_historical(root, league_id=league, write=True)
        if report["BlockedCount"]:
            raise ValueError(_blocked_reason(report))
        return int(report.get("ChangedCount", 0)), 0
    if product == TEAM_WEEK_PERFORMANCE:
        report = materialize_all_finalized(root, league_id=league, write=True, require_pwf=False)
        if report["BlockedCount"]:
            raise ValueError(_blocked_reason(report))
        return int(report["ChangedCount"]), 0
    if product == NFL_GAMES:
        return sum(
            int(materialize_nfl_games(root, season, write=True)["Written"])
            for season in discover_seasons(root)
        ), 0
    raise ValueError(f"Unknown product: {product}")


def _run_variant(
    shadow: Path, units: list[Unit], *, passes: int,
) -> dict[Unit, dict[str, Any]]:
    results: dict[Unit, dict[str, Any]] = {}
    for unit in units:
        product, league = unit
        entry: dict[str, Any] = {"error": None, "writes": [], "files": [], "held": 0}
        results[unit] = entry
        try:
            for index in range(passes):
                writes, held = _build(unit, shadow)
                if index == 0:
                    entry["held"] = held
                entry["writes"].append(writes)
                entry["files"].append(_files(shadow, unit))
            if not entry["files"][0]:
                raise ValueError("Materializer produced no product snapshots")
        except (OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
            entry["error"] = str(exc) or type(exc).__name__
    return results


def _diff(left: dict[str, str], right: dict[str, str]) -> dict[str, list[str]]:
    return {
        "Differing": sorted(k for k in left.keys() & right.keys() if left[k] != right[k]),
        "OnlyLeft": sorted(left.keys() - right.keys()),
        "OnlyRight": sorted(right.keys() - left.keys()),
    }


def _classify(empty: dict[str, Any], normal: dict[str, Any], published: dict[str, str]) -> dict[str, Any]:
    """Three-way comparison of one unit; see the module docstring for the statuses."""
    latent = bool(empty["error"]) and STANDINGS_MARKER in empty["error"] and not normal["error"]
    result: dict[str, Any] = {"PreviouslyPublishedCount": len(published)}
    if normal["error"] or (empty["error"] and not latent):
        result["Status"] = "blocked"
        result["Reason"] = (
            f"Productive-like build failed: {normal['error']}" if normal["error"]
            else f"Clean-root build failed: {empty['error']}"
        )
        return result
    normal_files = normal["files"][0]
    result["HeldRowsAcrossSnapshots"] = normal["held"]
    against_published = _diff(normal_files, published)
    result["ChangedVsPublishedCount"] = len(against_published["Differing"])
    result["MissingInPublishedCount"] = len(against_published["OnlyLeft"])
    result["StalePublishedExamples"] = (against_published["Differing"] + against_published["OnlyLeft"])[:EXAMPLE_LIMIT]
    stale = bool(against_published["Differing"] or against_published["OnlyLeft"])
    if latent:
        result["Status"] = "latent-blocker"
        result["LatentBlocker"] = LATENT_STANDINGS_ISSUE
        result["Reason"] = (
            f"Builds only with the transitional Standings input ({LATENT_STANDINGS_ISSUE}): {empty['error']}"
        )
        return result
    first, second = empty["files"]
    result["RebuiltCount"] = len(first)
    result["SecondPassWrites"] = empty["writes"][1]
    result["SecondPassByteIdentical"] = first == second
    if empty["writes"][1] != 0 or first != second:
        result["Status"] = "nondeterministic"
        result["Reason"] = "Second clean-root pass changed reconstructed output"
        return result
    # A published file that the normal run left untouched and the empty run cannot build is an orphan,
    # not a hidden dependency: it is reported as stale instead of a defect.
    versus = _diff(first, normal_files)
    orphans = [k for k in versus["OnlyRight"] if normal_files[k] == published.get(k)]
    defects = {
        "Differing": versus["Differing"],
        "OnlyEmpty": versus["OnlyLeft"],
        "OnlyNormal": [k for k in versus["OnlyRight"] if k not in orphans],
    }
    result["RestoreDefectCount"] = sum(len(v) for v in defects.values())
    if result["RestoreDefectCount"]:
        result["Status"] = "restore-defect"
        result["RestoreDefectExamples"] = {k: v[:EXAMPLE_LIMIT] for k, v in defects.items() if v}
        result["Reason"] = "Clean-root output differs from the productive-like run"
        return result
    result["OrphanedPublishedCount"] = len(orphans)
    if stale or orphans:
        result["Status"] = "stale-published"
        result["Reason"] = "Published files are behind; clean-root and productive-like output agree"
    else:
        result["Status"] = "ready"
    return result


def _prepare(shadow: Path, source: Path, *, published: bool) -> None:
    for name in (DATA_SOURCE_ROOT, DATA_META_ROOT):
        (shadow / name).symlink_to(source / name, target_is_directory=True)
    (shadow / "public/data").mkdir(parents=True)
    # PowerShell bridge of TeamWeekPerformance (existing FantasyRelevance slot rules).
    if (source / "public/requests").is_dir():
        (shadow / "public/requests").symlink_to(source / "public/requests", target_is_directory=True)
    derived = source / DATA_DERIVED_ROOT
    if published and derived.is_dir():
        shutil.copytree(derived, shadow / DATA_DERIVED_ROOT)
    else:
        (shadow / DATA_DERIVED_ROOT).mkdir()
    if published:
        for name in PUBLISHED_APP_FILES:
            if (source / "public/data" / name).is_file():
                shutil.copy2(source / "public/data" / name, shadow / "public/data" / name)


def audit(repo_root: Path, *, leagues: list[str] | None = None) -> dict[str, Any]:
    """Rebuild every product with and without existing Derived/App files and compare with the published ones.

    Live repository data-derived, public/data and workflow state remain untouched.
    """
    source = repo_root.resolve()
    for name in (DATA_SOURCE_ROOT, DATA_META_ROOT):
        if not (source / name).is_dir():
            raise ValueError(f"Missing required canonical root: {name}")
    league_ids = leagues or list_league_ids(source / DATA_META_ROOT)
    if not league_ids:
        raise ValueError("No league found in data-meta")
    units: list[Unit] = [
        (product, None if product in GLOBAL_PRODUCTS else league)
        for product in PRODUCTS
        for league in ([None] if product in GLOBAL_PRODUCTS else league_ids)
    ]
    with tempfile.TemporaryDirectory(prefix="derived-clean-root-audit-") as empty_dir, \
         tempfile.TemporaryDirectory(prefix="derived-normal-root-audit-") as normal_dir:
        empty_root, normal_root = Path(empty_dir), Path(normal_dir)
        _prepare(empty_root, source, published=False)
        _prepare(normal_root, source, published=True)
        empty = _run_variant(empty_root, units, passes=2)
        normal = _run_variant(normal_root, units, passes=1)
    results: dict[str, dict[str, Any]] = {}
    for unit in units:
        product, league = unit
        results[unit_key(unit)] = {
            "Product": product, "League": league,
            **_classify(empty[unit], normal[unit], _files(source, unit)),
        }
    failed = sorted(k for k, v in results.items() if v["Status"] in FAILING)
    return {
        "Mode": "three-way-clean-root-probe",
        "Leagues": league_ids,
        "ReadOnly": True,
        "Published": False,
        "Scope": [unit_key(u) for u in units],
        "Products": results,
        "FailedProducts": failed,
        "HintProducts": {k: v["Status"] for k, v in sorted(results.items()) if v["Status"] in HINTS},
        "ReadyForFullRestore": not failed,
    }


def render_summary(result: dict[str, Any]) -> str:
    """Markdown for the GitHub Job Summary: one row per unit, errors first, hints named."""
    failed = set(result["FailedProducts"])
    lines = [
        "### Shared Derived restore gate",
        "",
        f"Result: **{'FAIL' if failed else 'PASS'}** ({len(result['Products'])} units, leagues: "
        f"{', '.join(result['Leagues']) or 'none'}). Read-only; nothing was written.",
        "",
        "| Unit | Status | Detail |",
        "|---|---|---|",
    ]
    for key, item in sorted(result["Products"].items(), key=lambda kv: (kv[0] not in failed, kv[0])):
        detail = str(item.get("Reason") or "").replace("|", "/").replace("\n", " ")
        lines.append(f"| {key} | {item['Status']} | {detail} |")
    if result["HintProducts"]:
        lines += ["", "Hints (no failure): " + ", ".join(
            f"{k} = {v}" for k, v in result["HintProducts"].items())]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--league", action="append", help="CanonicalLeagueID (repeatable); default: every league in data-meta")
    parser.add_argument("--github-summary", action="store_true",
                        help="append a Markdown table to $GITHUB_STEP_SUMMARY (CI restore gate)")
    args = parser.parse_args()
    try:
        result = audit(args.repo_root, leagues=args.league)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Clean-root probe could not start: {exc}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if args.github_summary and summary:
        with open(summary, "a", encoding="utf-8") as fp:
            fp.write(render_summary(result))
    return 0 if result["ReadyForFullRestore"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
