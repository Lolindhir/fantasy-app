"""Reusable League/Sleeper versus canonical PWF score reconciliation (#355).

The canonical league matchup owns league points; PlayerWeekFantasy owns derived
NFL scoring. Missing source values remain unavailable, never zero. Narrow,
versioned policy entries may accept exact provider-evidence divergences without
altering either score or weakening the default mismatch gate.
No publisher, external API access or automatic writes.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping

from data_roots import DATA_DERIVED_ROOT, DATA_SOURCE_ROOT, data_meta_dir
from player_week_fantasy import load_scoring_profile_identity

CONTRACT_VERSION = 1
TOLERANCE = Decimal("0.010001")


def _number(value: Any, label: str) -> Decimal:
    if value is None or isinstance(value, bool):
        raise ValueError(f"Missing or invalid {label}")
    try:
        result = Decimal(str(value))
    except (ValueError, InvalidOperation) as exc:
        raise ValueError(f"Invalid {label}") from exc
    if not result.is_finite():
        raise ValueError(f"Non-finite {label}")
    return result


def _policy(root: Path, league: str) -> dict[tuple[int, int, str], dict]:
    path = data_meta_dir(root) / league / "scoring-divergences.json"
    if not path.is_file():
        return {}
    source = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(source, dict) or source.get("ContractVersion") != 1 or not isinstance(source.get("Exceptions"), list):
        raise ValueError(f"Invalid scoring divergence policy: {path}")
    rules: dict[tuple[int, int, str], dict] = {}
    for rule in source["Exceptions"]:
        if not isinstance(rule, dict):
            raise ValueError("Invalid scoring divergence exception")
        season, week, player = (rule.get("Season"), rule.get("Week"), rule.get("CanonicalPlayerID"))
        if type(season) is not int or type(week) is not int or season < 1 or not 1 <= week <= 25 or not isinstance(player, str) or not player:
            raise ValueError("Invalid scoring divergence exception identity")
        if not isinstance(rule.get("Reference"), str) or not rule["Reference"].strip() or not isinstance(rule.get("Reason"), str) or not rule["Reason"].strip():
            raise ValueError("Scoring divergence exception requires an audit reference and reason")
        expected_league = _number(rule.get("LeaguePoints"), "policy LeaguePoints")
        expected_calc = _number(rule.get("CalculatedPoints"), "policy CalculatedPoints")
        if abs(expected_calc - expected_league) <= TOLERANCE:
            raise ValueError("Scoring divergence policy must not allow equivalent scores")
        key = (season, week, player)
        if key in rules:
            raise ValueError(f"Duplicate scoring divergence exception {key}")
        rules[key] = rule
    return rules


def reconcile(
    root: Path,
    model: Mapping[str, Any],
    matchup_rows: list[dict],
    *,
    require_pwf: bool = False,
) -> dict[str, Any]:
    league, season, week = (model["CanonicalLeagueID"], model["Season"], model["Week"])
    if not isinstance(league, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", league) or type(season) is not int or type(week) is not int:
        raise ValueError("Invalid reconciliation identity")
    scoring_hash = model["ScoringProfile"]["SettingsHash"]
    if not isinstance(scoring_hash, str) or not scoring_hash.startswith("sha256:"):
        raise ValueError("Invalid reconciliation scoring fingerprint")
    rules = _policy(root, league)
    week_rules = {key: value for key, value in rules.items() if key[:2] == (season, week)}
    pwf_path = (root / DATA_DERIVED_ROOT / "player-week-fantasy" / league
                / str(season) / f"{week:02d}.json")
    pwf: dict | None = None
    records: dict[str, dict] = {}
    if pwf_path.is_file():
        try:
            pwf = json.loads(pwf_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Invalid PlayerWeekFantasy parity source: {pwf_path}") from exc
        if not isinstance(pwf, dict):
            raise ValueError("PlayerWeekFantasy snapshot must be an object")
        if any(pwf.get(key) != model[key] for key in ("CanonicalLeagueID", "Season", "Week")):
            raise ValueError("PlayerWeekFantasy league/season/week mismatch")
        if not isinstance(pwf.get("ScoringProfile"), dict) or pwf["ScoringProfile"].get("SettingsHash") != scoring_hash:
            raise ValueError("PlayerWeekFantasy scoring fingerprint mismatch")
        if not isinstance(pwf.get("Records"), list):
            raise ValueError("PlayerWeekFantasy has no Records array")
        for item in pwf["Records"]:
            if not isinstance(item, dict):
                raise ValueError("Invalid PlayerWeekFantasy record")
            player = item.get("CanonicalPlayerID")
            if not isinstance(player, str) or not player or player in records:
                raise ValueError("Missing or duplicate PlayerWeekFantasy player identity")
            records[player] = item
    elif require_pwf:
        raise ValueError(f"Required PlayerWeekFantasy parity source is missing: {pwf_path}")

    league_points: dict[str, Decimal] = {}
    for team in matchup_rows:
        if not isinstance(team, dict) or not isinstance(team.get("PlayerPoints"), list):
            raise ValueError("Missing canonical matchup PlayerPoints")
        for item in team["PlayerPoints"]:
            if not isinstance(item, dict) or not isinstance(item.get("Player"), dict):
                raise ValueError("Invalid canonical matchup PlayerPoints reference")
            player = item["Player"].get("CanonicalPlayerID")
            if not isinstance(player, str) or not player or player in league_points:
                raise ValueError("Missing or duplicate canonical matchup player identity")
            league_points[player] = _number(item.get("Points"), f"matchup {player}")

    rows: list[dict] = []
    verified = accepted = missing_zero = compared = 0
    errors: list[str] = []
    used_rules: set[tuple[int, int, str]] = set()
    for player in sorted(set(records) | set(league_points)):
        raw = records.get(player)
        league_score = league_points.get(player)
        actual = raw.get("Actual") if raw is not None else None
        state = actual.get("State") if isinstance(actual, dict) else None
        calc = None
        if state == "final":
            calc = _number(actual.get("Points"), f"PWF {player}")
        status = "unavailable"
        error = None
        delta = None
        if league_score is not None and pwf is not None:
            if raw is None:
                if league_score != 0:
                    status, error = "mismatch", f"PlayerWeekFantasy is missing nonzero scorer {player}"
                else:
                    missing_zero += 1
            elif state != "final":
                status, error = "mismatch", f"PlayerWeekFantasy Actual is not final for {player}"
            else:
                compared += 1
                delta = calc - league_score
                if abs(delta) <= TOLERANCE:
                    status = "verified"
                    verified += 1
                else:
                    rule = week_rules.get((season, week, player))
                    if (rule is not None and
                            _number(rule["LeaguePoints"], "exception LeaguePoints") == league_score and
                            _number(rule["CalculatedPoints"], "exception CalculatedPoints") == calc):
                        status = "accepted-divergence"
                        accepted += 1
                        used_rules.add((season, week, player))
                    else:
                        status, error = "mismatch", (
                            f"PlayerWeekFantasy scoring mismatch for {player}: "
                            f"league={league_score}, pwf={calc}")
        record = {
            "CanonicalPlayerID": player,
            "LeaguePoints": float(league_score) if league_score is not None else None,
            "CalculatedPoints": float(calc) if calc is not None else None,
            "Difference": float(delta) if delta is not None else None,
            "Status": status,
        }
        if status == "accepted-divergence":
            record["ExceptionReference"] = week_rules[(season, week, player)]["Reference"]
        if error:
            errors.append(error)
        rows.append(record)
    if pwf is not None:
        for stale in sorted(set(week_rules) - used_rules):
            errors.append(f"Stale or unverified scoring divergence exception {stale}")
    if errors:
        state = "mismatch"
    elif pwf is None:
        state = "not-available"
    elif accepted:
        state = "accepted-divergence"
    else:
        state = "verified"
    return {
        "ContractVersion": CONTRACT_VERSION,
        "CanonicalLeagueID": league,
        "Season": season,
        "Week": week,
        "ScoringProfile": {"SettingsHash": scoring_hash},
        "LeagueSource": f"data-source/leagues/{league}/seasons/{season}/matchups/week-{week}.json",
        "CalculatedSource": pwf_path.relative_to(root).as_posix(),
        "State": state,
        "Compared": compared,
        "Verified": verified,
        "AcceptedDivergences": accepted,
        "MissingZeroPoints": missing_zero,
        "Errors": errors,
        "Records": rows,
    }


def output_path(root: Path, report: Mapping[str, Any]) -> Path:
    return (root / DATA_DERIVED_ROOT / "player-scoring-reconciliation"
            / report["CanonicalLeagueID"] / str(report["Season"])
            / f"{report['Week']:02d}.json")


def persist_verified(root: Path, report: dict) -> bool:
    """Explicit opt-in persist; never publish incomplete or mismatched evidence."""
    if report["State"] not in ("verified", "accepted-divergence") or report["Errors"]:
        raise ValueError("Cannot publish unverified player-scoring reconciliation")
    path = output_path(root, report)
    payload = json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if path.is_file() and path.read_text(encoding="utf-8") == payload:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as file:
        file.write(payload)
        temp = Path(file.name)
    try:
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--league", required=True)
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--week", type=int, required=True)
    parser.add_argument("--write", action="store_true", help="Persist only verified evidence; default is read-only")
    args = parser.parse_args()
    root = args.repo_root.resolve()
    league_path = root / DATA_SOURCE_ROOT / "leagues" / args.league / "seasons" / str(args.season) / "league.json"
    league = json.loads(league_path.read_text(encoding="utf-8"))
    bounds = league["WeekStructure"]
    from player_week_fantasy_materialize import _week_finality
    final, game_ids = _week_finality(root, season=args.season, week=args.week)
    if (league.get("CanonicalLeagueID") != args.league or league.get("Season") != args.season
            or bounds.get("LastScoredLeg", 0) < args.week or not final or not game_ids):
        raise ValueError("League/NFL week is not canonically finalized")
    matchup_path = (root / DATA_SOURCE_ROOT / "leagues" / args.league / "seasons"
                    / str(args.season) / "matchups" / f"week-{args.week}.json")
    matchups = json.loads(matchup_path.read_text(encoding="utf-8"))
    model = {"CanonicalLeagueID": args.league, "Season": args.season, "Week": args.week,
             "ScoringProfile": load_scoring_profile_identity(root, args.league, args.season)}
    report = reconcile(root, model, matchups, require_pwf=True)
    if args.write:
        report["Written"] = persist_verified(root, report)
    print(json.dumps(report if not args.write else {k: v for k, v in report.items() if k != "Records"},
                     indent=2, ensure_ascii=False, sort_keys=True))
    return 2 if report["Errors"] or report["State"] == "not-available" else 0


if __name__ == "__main__":
    raise SystemExit(main())
