#!/usr/bin/env python3
"""Generate the L10 TeamCapOutlook App read model from canonical league rosters and PlayerValuation.

One read model for the league's current season. This is an App consumer delivery contract,
not a source or an independent persisted derived-data product. The existing League Live
rebuild/publish owner publishes it. Current and projected lenses use the same versioned
central models. InputRoster is a salary witness for client-side stale checking only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from data_roots import DATA_SOURCE_ROOT, data_derived_dir  # noqa: E402
from derived_data_lib.models import registry  # noqa: E402
from derived_data_lib.models.roster_cap.v1 import SalaryEntry  # noqa: E402
from league_metadata import data_meta_root, default_league_id, load_league_metadata, model_for  # noqa: E402
from league_standings_sources import _sleeper_value, current_season, manifest  # noqa: E402

CONTRACT_VERSION = 1
OUTPUT_NAME = "TeamCapOutlook.json"


class OutlookError(ValueError):
    """Inputs cannot safely produce the current-season team-cap outlook."""


def _json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as error:
        raise OutlookError(f"Required canonical input {path}: {error}") from error


def _salary(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not (0 <= value < float("inf")):
        raise OutlookError(f"{label} must be finite and nonnegative")
    if int(value) != value:
        raise OutlookError(f"{label} must contain whole-dollar Salary values")
    return int(value)


def _player_id(item: dict[str, Any]) -> str:
    return _sleeper_value(item.get("ProviderMappings"), "ProviderPlayerID", "canonical roster player")


def _team_id(roster: dict[str, Any]) -> int:
    value = _sleeper_value(roster.get("ProviderMappings"), "ProviderRosterID", "canonical league roster")
    if not value.isdigit() or int(value) < 1:
        raise OutlookError(f"Invalid Sleeper roster ID {value!r}")
    return int(value)


def _cuts(result: Any) -> list[dict[str, Any]]:
    return [
        {
            "PlayerID": cut.player_id,
            "CutOrder": cut.cut_order,
            "SalaryRank": cut.salary_rank,
            "SalaryUsed": cut.salary_used,
            "CapBeforeCut": cut.cap_before_cut,
            "CapAfterCut": cut.cap_after_cut,
        }
        for cut in result
    ]


def build(
    league_id: str,
    season: int,
    raw_rosters: list[dict[str, Any]],
    valuation: dict[str, Any],
    metadata: dict[str, Any],
) -> dict[str, Any]:
    """Pure delivery adapter: no I/O, fail closed on ambiguous IDs, explicit team-unavailable for missing Salary."""
    if (valuation.get("CanonicalLeagueID"), valuation.get("Season")) != (league_id, season):
        raise OutlookError("PlayerValuation league/season does not match current canonical league")
    if not isinstance(valuation.get("Players"), list):
        raise OutlookError("PlayerValuation has no player rows")
    if not isinstance(raw_rosters, list) or not raw_rosters:
        raise OutlookError("Canonical league rosters are empty")
    model_ids = {key: model_for(metadata, season, key) for key in ("RosterCap", "AutoCut")}
    usage = registry.get_model(model_ids["RosterCap"], kind="roster-cap")
    cut_model = registry.get_model(model_ids["AutoCut"], kind="auto-cut")
    cap_model = registry.get_model(model_for(metadata, season, "SalaryCap"), kind="salary-cap")
    cap_size = int(cap_model.PARAMS["SalaryRelevantTeamSize"])
    league = valuation.get("League") or {}
    if league.get("SalaryRelevantTeamSize") != cap_size or league.get("TeamCount") != len(raw_rosters):
        raise OutlookError("PlayerValuation SalaryRelevantTeamSize/TeamCount mismatch canonical roster population")
    caps = {
        "Current": _salary(league.get("SalaryCap"), "SalaryCap"),
        "Projected": _salary(league.get("SalaryCapProjected"), "SalaryCapProjected"),
    }
    indexed: dict[str, dict[str, Any]] = {}
    for player in valuation["Players"]:
        pid = str(player.get("PlayerID") or "")
        if not pid or pid in indexed:
            raise OutlookError(f"Missing or duplicate PV PlayerID: {pid!r}")
        indexed[pid] = player

    teams = []
    used: set[int] = set()
    for roster in sorted(raw_rosters, key=_team_id):
        team_id = _team_id(roster)
        if team_id in used:
            raise OutlookError(f"Duplicate fantasy TeamID {team_id}")
        used.add(team_id)
        rows = roster.get("Players") or []
        if not isinstance(rows, list):
            raise OutlookError(f"Team {team_id} Players must be a list")
        ids = [_player_id(player) for player in rows]
        if len(ids) != len(set(ids)):
            raise OutlookError(f"Team {team_id} has duplicate PlayerID")
        unknown = [pid for pid in ids if pid not in indexed
                   or indexed[pid].get("Salary") is None
                   or indexed[pid].get("SalaryProjected") is None]
        if unknown:
            teams.append({
                "TeamID": team_id, "Status": "unavailable",
                "Reason": "MissingPlayerValuation", "MissingPlayerIDs": unknown,
            })
            continue
        witness = [
            {"PlayerID": pid,
             "Salary": _salary(indexed[pid]["Salary"], f"{pid}.Salary"),
             "SalaryProjected": _salary(indexed[pid]["SalaryProjected"], f"{pid}.SalaryProjected")}
            for pid in ids
        ]
        lenses: dict[str, Any] = {}
        for lens, key in (("Current", "Salary"), ("Projected", "SalaryProjected")):
            salary_entries = [SalaryEntry(row["PlayerID"], row[key]) for row in witness]
            summary = usage.compute(salary_entries, cap_size)
            cuts = cut_model.compute(salary_entries, cap_size, caps[lens])
            lenses[lens] = {"Usage": summary.cap, "TopPlayerIDs": list(summary.top_player_ids),
                            "Cuts": _cuts(cuts)}
        teams.append({
            "TeamID": team_id, "Status": "ready", "InputRoster": witness,
            "Current": lenses["Current"], "Projected": lenses["Projected"],
        })
    return {
        "ContractVersion": CONTRACT_VERSION,
        "CanonicalLeagueID": league_id,
        "Season": season,
        "AsOfFinalScoredWeek": valuation.get("AsOfFinalScoredWeek"),
        "Models": model_ids,
        "SalaryRelevantTeamSize": cap_size,
        "SalaryCap": caps["Current"],
        "SalaryCapProjected": caps["Projected"],
        "Teams": teams,
    }


def load(repo_root: Path, league_id: str) -> dict[str, Any]:
    season = current_season(manifest(repo_root, league_id))
    season_root = repo_root / DATA_SOURCE_ROOT / "leagues" / league_id / "seasons" / str(season)
    rosters = _json(season_root / "rosters.json")
    folder = data_derived_dir(repo_root) / "player-valuation" / league_id / str(season)
    snapshots = sorted(folder.glob("week-*.json"))
    if not snapshots:
        raise OutlookError(f"PlayerValuation missing for {league_id}/{season}")
    snapshot = _json(snapshots[-1])
    metadata = load_league_metadata(league_id, data_meta_root(repo_root))
    return build(league_id, season, rosters, snapshot, metadata)


def write(repo_root: Path, league_id: str) -> bool:
    result = load(repo_root, league_id)
    data_dir = repo_root / "public" / "data"
    target = data_dir / OUTPUT_NAME
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if target.is_file() and target.read_text(encoding="utf-8") == serialized:
        return False
    data_dir.mkdir(parents=True, exist_ok=True)
    target.write_text(serialized, encoding="utf-8", newline="\n")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("write", "check"))
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--league", help="CanonicalLeagueID; default only when data-meta has exactly one league")
    args = parser.parse_args(argv)
    try:
        league_id = args.league or default_league_id(data_meta_root(args.repo_root))
        if args.command == "check":
            result = load(args.repo_root, league_id)
            print(f"TeamCapOutlook check: {len(result['Teams'])} teams, "
                  f"{sum(t['Status'] == 'ready' for t in result['Teams'])} ready")
        else:
            print("TeamCapOutlook written" if write(args.repo_root, league_id)
                  else "TeamCapOutlook unchanged")
    except (ValueError, OSError) as error:
        print(f"TeamCapOutlook: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
