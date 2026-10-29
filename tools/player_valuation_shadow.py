#!/usr/bin/env python3
"""Shadow of the PlayerValuation product against the published Players.json / League.json (Issue #919 step 4).

Read-only. Materializes the PlayerValuation snapshots into a scratch directory (never into the repo) and
compares the snapshot of the published final scored week field by field and EXACTLY (no rounding tolerance,
Robert 2026-10-14) with the committed public/data files:

  Players.json  Salary, SalaryProjected, Ranking[] (all types), the Rank row of Grading[] and the
                averages behind PointHistory / FantasyPointsAvg*
  League.json   SalaryCap, SalaryCapProjected

Historical snapshots have no published counterpart; for them the tool reports plausibility facts
(coverage per position, holds, valued rows, cap series) instead of a parity verdict.

Usage:
  player_valuation_shadow.py [--league nfl-reise] [--report-dir DIR] [--snapshots-root DIR]
Exit code: 0 = exact parity, 1 = at least one mismatch, 2 = the inputs cannot be compared (fail closed).
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import derived_data  # noqa: E402
import player_valuation_sources as sources  # noqa: E402

EXIT_MISMATCH = 1
EXIT_UNCOMPARABLE = 2

# snapshot Inputs name -> (published scalar fields | PointHistory key)
CURRENT_FIELDS = {"AvgPotentialGame": "FantasyPointsAvgPotentialGame", "AvgGame": "FantasyPointsAvgGame"}
HISTORY_KEYS = ("SeasonMinus1", "SeasonMinus2", "SeasonMinus3")
HISTORY_FIELDS = ("AvgPotentialGame", "AvgGame")


class ShadowError(RuntimeError):
    """The comparison cannot be made (missing or inconsistent inputs)."""


def _read(path: Path) -> Any:
    if not path.is_file():
        raise ShadowError(f"Missing published file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def published_week(league: dict[str, Any], players: list[dict[str, Any]]) -> int:
    week = league.get("FinalScoredWeek")
    if not isinstance(week, int) or isinstance(week, bool):
        raise ShadowError(f"League.json FinalScoredWeek is not an integer: {week!r}")
    if not players:
        raise ShadowError("Players.json is empty")
    return week


def _rank_row(player: dict[str, Any]) -> dict[str, Any] | None:
    rows = [g for g in (player.get("Grading") or []) if g.get("Type") == "Rank"]
    if len(rows) > 1:
        raise ShadowError(f"Player {player.get('ID')} has {len(rows)} Rank grading rows")
    return rows[0] if rows else None


def _ranking_map(rows: list[dict[str, Any]] | None) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for row in rows or []:
        if row["Type"] in result:
            raise ShadowError(f"Duplicate ranking type {row['Type']}")
        result[row["Type"]] = row["Value"]
    return result


def compare_player(snap_row: dict[str, Any], published: dict[str, Any]) -> list[dict[str, Any]]:
    """Field differences for one player; an empty list means exact parity."""
    diffs: list[dict[str, Any]] = []

    def check(field: str, ours: Any, theirs: Any) -> None:
        if ours != theirs:
            diffs.append({"PlayerID": published["ID"], "Name": published.get("Name"), "Position": published.get("Position"),
                          "Field": field, "Snapshot": ours, "Published": theirs})

    check("Salary", snap_row["Salary"], published.get("Salary"))
    check("SalaryProjected", snap_row["SalaryProjected"], published.get("SalaryProjected"))

    ours_rank, theirs_rank = _ranking_map(snap_row["Ranking"]), _ranking_map(published.get("Ranking"))
    for rtype in sorted(set(ours_rank) | set(theirs_rank)):
        check(f"Ranking.{rtype}", ours_rank.get(rtype, "<absent>"), theirs_rank.get(rtype, "<absent>"))

    grade_ours = next((g for g in snap_row["Grading"] if g["Type"] == "Rank"), None)
    grade_theirs = _rank_row(published)
    for field in ("Value", "Rank", "Grade"):
        ours_value = grade_ours.get(field, "<absent>") if grade_ours else "<no row>"
        theirs_value = grade_theirs.get(field, "<absent>") if grade_theirs else "<no row>"
        # Intentional deviation (2026-10-15): the pre-fix published file grades an unranked player A, grading-v1 gives none.
        if field == "Grade" and ours_value is None and grade_ours.get("Rank") is None and theirs_value == "A":
            continue
        check(f"Grading.Rank.{field}", ours_value, theirs_value)

    inputs = snap_row["Inputs"]
    if inputs is None:
        diffs.append({"PlayerID": published["ID"], "Name": published.get("Name"), "Position": published.get("Position"),
                      "Field": "Inputs", "Snapshot": None, "Published": "<present>"})
        return diffs
    for ours_name, theirs_name in CURRENT_FIELDS.items():
        check(f"Inputs.Current.{ours_name}", inputs["Current"][ours_name], published.get(theirs_name))
    history = published.get("PointHistory") or {}
    for key in HISTORY_KEYS:
        for name in HISTORY_FIELDS:
            check(f"Inputs.{key}.{name}", inputs[key][name], (history.get(key) or {}).get(name, "<absent>"))
    return diffs


def compare_snapshot(snapshot: dict[str, Any], players: list[dict[str, Any]], league: dict[str, Any]) -> dict[str, Any]:
    by_id = {}
    for p in players:
        if p["ID"] in by_id:
            raise ShadowError(f"Duplicate published player ID {p['ID']}")
        by_id[p["ID"]] = p
    snap_by_id: dict[str, dict[str, Any]] = {}
    snapshot_without_sleeper_id = 0
    for row in snapshot["Players"]:
        if row["PlayerID"] is None:
            snapshot_without_sleeper_id += 1
            continue
        if row["PlayerID"] in snap_by_id:
            raise ShadowError(f"Duplicate snapshot PlayerID {row['PlayerID']}")
        snap_by_id[row["PlayerID"]] = row

    diffs: list[dict[str, Any]] = []
    for pid in sorted(set(by_id) & set(snap_by_id)):
        diffs.extend(compare_player(snap_by_id[pid], by_id[pid]))

    cap_diffs = []
    for ours_name, theirs_name in (("SalaryCap", "SalaryCap"), ("SalaryCapProjected", "SalaryCapProjected")):
        ours, theirs = snapshot["League"][ours_name], league.get(theirs_name)
        if ours != theirs:
            cap_diffs.append({"Field": ours_name, "Snapshot": ours, "Published": theirs})

    return {
        "Compared": len(set(by_id) & set(snap_by_id)),
        "PublishedOnly": sorted(set(by_id) - set(snap_by_id)),
        "SnapshotOnly": sorted(set(snap_by_id) - set(by_id)),
        "SnapshotRowsWithoutSleeperID": snapshot_without_sleeper_id,
        "FieldDifferences": diffs,
        "CapDifferences": cap_diffs,
    }


def plausibility(snapshot: dict[str, Any]) -> dict[str, Any]:
    rows = snapshot["Players"]
    valued = [r for r in rows if r["Inputs"] is not None]
    return {
        "Season": snapshot["Season"],
        "AsOfFinalScoredWeek": snapshot["AsOfFinalScoredWeek"],
        "Rows": len(rows),
        "Valued": len(valued),
        "Held": sum(1 for r in rows if r["Hold"] is not None),
        "HeldWithoutInputs": sum(1 for r in rows if r["Hold"] is not None and r["Inputs"] is None),
        "RowsWithoutSleeperID": sum(1 for r in rows if r["PlayerID"] is None),
        "ByPosition": dict(sorted(Counter(r["Position"] for r in rows).items())),
        "SalaryCap": snapshot["League"]["SalaryCap"],
        "SalaryCapProjected": snapshot["League"]["SalaryCapProjected"],
        "TopN": snapshot["League"]["TopN"],
    }


def load_snapshots(root: Path, league_id: str) -> dict[tuple[int, int], dict[str, Any]]:
    base = root / sources.PRODUCT / league_id
    if not base.is_dir():
        raise ShadowError(f"No snapshots under {base}")
    result: dict[tuple[int, int], dict[str, Any]] = {}
    for path in sorted(base.glob("*/week-*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        result[(payload["Season"], payload["AsOfFinalScoredWeek"])] = payload
    return result


def run_shadow(repo_root: Path, league_id: str, snapshots_root: Path | None) -> dict[str, Any]:
    league = _read(repo_root / "public" / "data" / "League.json")
    players = _read(repo_root / "public" / "data" / "Players.json")
    week = published_week(league, players)
    season = int(league["Season"])

    scratch = None
    root = snapshots_root
    if root is None:
        scratch = tempfile.TemporaryDirectory(prefix="player-valuation-shadow-")
        root = Path(scratch.name)
        derived_data.materialize_player_valuation(repo_root, root, league_id, None, check_only=False)
    try:
        snapshots = load_snapshots(root, league_id)
    finally:
        if scratch is not None:
            scratch.cleanup()
    if (season, week) not in snapshots:
        raise ShadowError(f"No snapshot for published season {season} week {week}")

    parity = compare_snapshot(snapshots[(season, week)], players, league)
    return {
        "CanonicalLeagueID": league_id,
        "PublishedSeason": season,
        "PublishedFinalScoredWeek": week,
        "Parity": parity,
        "Exact": not parity["FieldDifferences"] and not parity["CapDifferences"]
                 and not parity["PublishedOnly"] and not parity["SnapshotOnly"],
        "Plausibility": [plausibility(s) for _, s in sorted(snapshots.items())],
    }


def render_markdown(report: dict[str, Any]) -> str:
    parity = report["Parity"]
    lines = [
        f"# PlayerValuation Shadow-Parität ({report['CanonicalLeagueID']}, {report['PublishedSeason']} Woche {report['PublishedFinalScoredWeek']})",
        "",
        f"- Ergebnis: **{'exakte Parität' if report['Exact'] else 'ABWEICHUNGEN'}**",
        f"- Verglichene Spieler: {parity['Compared']}",
        f"- Nur in Players.json: {len(parity['PublishedOnly'])}; nur im Snapshot: {len(parity['SnapshotOnly'])}; Snapshot-Zeilen ohne Sleeper-ID: {parity['SnapshotRowsWithoutSleeperID']}",
        f"- Feldabweichungen: {len(parity['FieldDifferences'])}; Cap-Abweichungen: {len(parity['CapDifferences'])}",
        "",
    ]
    for d in parity["CapDifferences"]:
        lines.append(f"- {d['Field']}: Snapshot {d['Snapshot']} / veröffentlicht {d['Published']}")
    for d in parity["FieldDifferences"][:50]:
        lines.append(f"- {d['PlayerID']} {d['Name']} ({d['Position']}) {d['Field']}: Snapshot {d['Snapshot']} / veröffentlicht {d['Published']}")
    lines += ["", "## Plausibilität je Snapshot", "", "| Saison | Woche | Zeilen | bewertet | Holds | Holds ohne Inputs | ohne Sleeper-ID | SalaryCap | SalaryCapProjected |", "|---|---|---|---|---|---|---|---|---|"]
    for p in report["Plausibility"]:
        lines.append(f"| {p['Season']} | {p['AsOfFinalScoredWeek']} | {p['Rows']} | {p['Valued']} | {p['Held']} | {p['HeldWithoutInputs']} | {p['RowsWithoutSleeperID']} | {p['SalaryCap']} | {p['SalaryCapProjected']} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--league", default="nfl-reise")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--snapshots-root", type=Path, default=None, help="Reuse already materialized snapshots instead of building into a scratch directory")
    parser.add_argument("--report-dir", type=Path, default=None, help="Write shadow-report.json and shadow-report.md here")
    args = parser.parse_args()
    try:
        report = run_shadow(args.repo_root, args.league, args.snapshots_root)
    except (ShadowError, sources.SourceError) as exc:
        print(f"UNCOMPARABLE: {exc}", file=sys.stderr)
        return EXIT_UNCOMPARABLE
    markdown = render_markdown(report)
    if args.report_dir:
        args.report_dir.mkdir(parents=True, exist_ok=True)
        (args.report_dir / "shadow-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (args.report_dir / "shadow-report.md").write_text(markdown, encoding="utf-8")
    print(markdown)
    return 0 if report["Exact"] else EXIT_MISMATCH


if __name__ == "__main__":
    sys.exit(main())
