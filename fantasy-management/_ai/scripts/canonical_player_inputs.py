"""Canonical player inputs for Fantasy Operations (Issue #919 step 6).

Replaces the former read of the published players read model by two shared sources:
population and profile fields from tools/players_population.py (ADR-043) and
Salary/SalaryProjected from the newest PlayerValuation snapshot of the season
(data-derived/player-valuation, ADR-055). The result keeps the field names the
builders already consume (ID, Age, Year, IsFreeAgent, Injured, InjuryDetails,
Salary, SalaryProjected, Status), so no builder logic changes.

Age uses the shared pure tools/player_age.py calculation with an explicit
reference date from the Fantasy Operations run, not a published Players timestamp.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "tools"))

import players_population  # noqa: E402
from player_age import age_at as shared_age_at  # noqa: E402


class CanonicalPlayerInputsError(RuntimeError):
    pass


def latest_valuation_snapshot(root: Path, league_id: str, season: int) -> dict[str, Any]:
    season_dir = root / "data-derived" / "player-valuation" / league_id / str(season)
    files = sorted(season_dir.glob("week-*.json"))
    if not files:
        raise CanonicalPlayerInputsError(f"No PlayerValuation snapshot for {league_id} {season}")
    return json.loads(files[-1].read_text(encoding="utf-8"))


def age_at(birth_date: str | None, reference: date) -> float | None:
    if not birth_date:
        return None
    return shared_age_at(birth_date, reference)


def _injury_fields(injury: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    def text(value: Any) -> str:
        return "" if value is None else str(value).strip()

    designation = text(injury.get("Status"))
    description = ""
    if designation:
        for candidate in (injury.get("Notes"), injury.get("BodyPart"), injury.get("PracticeDescription")):
            if text(candidate):
                description = text(candidate)
                break
    return bool(designation), {
        "ReturnDate": None,
        "Description": description,
        "Date": text(injury.get("StartDate")),
        "Designation": designation,
    }


def load_players(
    root: Path, league_id: str, season: int, reference_date: date
) -> list[dict[str, Any]]:
    try:
        population = players_population.build_population(root, league_id, season)
    except players_population.PopulationError as exc:
        raise CanonicalPlayerInputsError(str(exc)) from exc
    snapshot = latest_valuation_snapshot(root, league_id, season)
    valuation = {str(row["PlayerID"]): row for row in snapshot["Players"] if row.get("PlayerID") is not None}
    players: list[dict[str, Any]] = []
    for entry in population["Players"]:
        sleeper_id = str(entry["SleeperID"])
        injured, details = _injury_fields(entry.get("Injury") or {})
        row = valuation.get(sleeper_id) or {}
        years = entry.get("YearsExp")
        players.append(
            {
                "ID": sleeper_id,
                "Name": entry.get("FullName"),
                "Position": entry["Position"],
                "TeamAbbr": entry.get("TeamAbbr"),
                "Status": entry.get("Status"),
                "Age": age_at(entry.get("BirthDate"), reference_date),
                "Year": None if years is None else years + 1,
                "IsFreeAgent": entry["IsFreeAgent"],
                "Injured": injured,
                "InjuryDetails": details,
                "Salary": row.get("Salary"),
                "SalaryProjected": row.get("SalaryProjected"),
            }
        )
    return players


def source_files(root: Path, league_id: str, season: int) -> list[tuple[str, Path]]:
    """Files that, besides the already tracked Sleeper snapshot and identities, feed load_players."""
    files: list[tuple[str, Path]] = []
    snapshot_dir = root / "data-derived" / "player-valuation" / league_id / str(season)
    newest = sorted(snapshot_dir.glob("week-*.json"))
    if newest:
        files.append(("player_valuation", newest[-1]))
    files.append(("canonical_player_profiles", root / players_population.PROFILES_PATH))
    rosters = root / "data-source" / "nfl" / "rosters"
    roster = rosters / f"{season}.json"
    used_season = season if roster.is_file() else season - 1
    files.append(("canonical_nfl_rosters", rosters / f"{used_season}.json"))
    weekly_dir = root / "data-source" / "nfl" / "weekly-rosters" / str(used_season)
    for path in sorted(weekly_dir.glob("*.json")) if weekly_dir.is_dir() else []:
        files.append((f"canonical_nfl_weekly_rosters_{path.stem}", path))
    draft = root / "data-source" / "nfl" / "draft" / f"{season}.json"
    if draft.is_file():
        files.append(("canonical_nfl_draft", draft))
    return files
