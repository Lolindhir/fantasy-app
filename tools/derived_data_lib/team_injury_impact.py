"""team-injury-impact Shared Derived product: Fantasy Injury Impact per team, league week and season (Issue #1584, CP5).

``resolve`` builds the document of one league season from persisted products and canonical facts only:

* data-derived/nfl-player-availability/<season>.json   availability evidence (State, Available, Played), contract v2
* data-derived/player-week-fantasy/<league>/<season>/NN.json  participation-conditional projections of the week
* data-source/leagues/... matchups, league settings, canonical weekly NFL rosters (rostered players, positions, slots), through the
  verified week inputs of team_week_performance_sources
* data-meta Models.InjuryImpact                          the model of the season

Only league-scored weeks (``LeagueScoredWeek``, ADR-071) are computed, because ``Played`` needs final games. A week whose inputs are
not usable (projection partition missing or computed under other scoring settings, availability missing, source not final) is listed
in ``UnavailableWeeks`` with its reason and never filled in. The document carries no clock and no display strings; manager names are
joined by the consumer. Contract: .ai-context/manual/team-injury-impact.yaml.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from data_roots import DATA_DERIVED_ROOT
from league_metadata import data_meta_root, load_league_metadata, model_for
from player_week_fantasy import build_scoring_profile_identity
from team_week_performance_sources import WeekSourceNotReady, _league_source, load_verified_week_inputs

from .models.registry import get_model
from .week_finality import resolve_week_finality

PRODUCT = "team-injury-impact"
SCHEMA_VERSION = 1


class TeamInjuryImpactError(ValueError):
    """Unusable or contradicting inputs (fail closed)."""


def _digest(rows: list[Any]) -> str:
    raw = json.dumps(rows, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _read(path: Path, what: str) -> Any:
    if not path.is_file():
        raise TeamInjuryImpactError(f"{what} missing: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise TeamInjuryImpactError(f"{what} unreadable: {path}") from error


def _slot_hash(slots: Any) -> str:
    return _digest([{"SlotID": s.slot_id, "EligiblePositions": sorted(s.eligible_positions)} for s in slots])


def availability_index(repo_root: Path, season: int) -> tuple[dict[tuple[int, str], dict[str, Any]], str]:
    """(Week, CanonicalPlayerID) -> availability record of the season, and the product version."""
    document = _read(repo_root / DATA_DERIVED_ROOT / "nfl-player-availability" / f"{season}.json", "Availability product")
    if document.get("Season") != season or not isinstance(document.get("Records"), list):
        raise TeamInjuryImpactError(f"Availability product identity mismatch for season {season}")
    index: dict[tuple[int, str], dict[str, Any]] = {}
    for record in document["Records"]:
        key = (record["Week"], record["CanonicalPlayerID"])
        if key in index:
            raise TeamInjuryImpactError(f"Duplicate availability record {key}")
        index[key] = record
    return index, str(document.get("ProductVersion"))


def projection_partition(repo_root: Path, league_id: str, season: int, week: int, settings_hash: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """(CanonicalPlayerID -> record, ProjectionModel) of the week; fails when the partition was built under other scoring settings."""
    path = repo_root / DATA_DERIVED_ROOT / "player-week-fantasy" / league_id / str(season) / f"{week:02d}.json"
    document = _read(path, "PlayerWeekFantasy partition")
    if (document.get("CanonicalLeagueID"), document.get("Season"), document.get("Week")) != (league_id, season, week):
        raise TeamInjuryImpactError(f"PlayerWeekFantasy identity mismatch: {path}")
    if document.get("ScoringProfile", {}).get("SettingsHash") != settings_hash:
        raise TeamInjuryImpactError(f"PlayerWeekFantasy {season}/{week} was built under other scoring settings")
    records: dict[str, Any] = {}
    for record in document["Records"]:
        records[record["CanonicalPlayerID"]] = record
    return records, document["ProjectionModel"]


def _projection_points(record: dict[str, Any] | None) -> float | None:
    if record is None:
        return None
    projection = record.get("Projection") or {}
    if projection.get("Status") != "available" or projection.get("Points") is None:
        return None
    return float(projection["Points"])


def build_week(
    model: Any, repo_root: Path, league_id: str, season: int, week: int, availability: dict[tuple[int, str], dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """(week document, header facts) of one league week; raises TeamInjuryImpactError or WeekSourceNotReady when not computable."""
    inputs = load_verified_week_inputs(repo_root, league_id, season, week)
    settings_hash = build_scoring_profile_identity(league_id, season, inputs["scoring_settings"])["SettingsHash"]
    projections, projection_model = projection_partition(repo_root, league_id, season, week, settings_hash)
    slots = inputs["slots"]
    teams: list[dict[str, Any]] = []
    availability_rows: list[Any] = []
    projection_rows: list[Any] = []
    for row in sorted(inputs["matchup_rows"], key=lambda r: r["CanonicalLeagueRosterID"]):
        players = []
        for reference in row["Players"]:
            player_id = reference["CanonicalPlayerID"]
            record = availability.get((week, player_id))
            points = _projection_points(projections.get(player_id))
            players.append({
                "CanonicalPlayerID": player_id, "Position": inputs["position_by_player"][player_id],
                "Availability": record, "Projection": points,
            })
            availability_rows.append([player_id, None if record is None else [record["State"], record["Available"], record["Played"]]])
            projection_rows.append([player_id, points])
        result = model.compute_team_week(slots, players)
        teams.append({"CanonicalLeagueRosterID": row["CanonicalLeagueRosterID"], **result})
    document = {
        "Week": week,
        "Inputs": {"AvailabilityDigest": _digest(sorted(availability_rows)), "ProjectionDigest": _digest(sorted(projection_rows))},
        "Teams": teams,
    }
    return document, {"SettingsHash": settings_hash, "LineupDefinitionHash": _slot_hash(slots), "ProjectionModel": projection_model}


def resolve(repo_root: Path, league_id: str, season: int) -> dict[str, Any]:
    """The product document of one league season."""
    metadata = load_league_metadata(league_id, data_meta_root(repo_root))
    model = get_model(model_for(metadata, season, "InjuryImpact"), "injury-impact")
    _, league = _league_source(repo_root, league_id, season)
    structure = league["WeekStructure"]
    first = structure["StartWeek"]
    scored = int(resolve_week_finality(repo_root, league_id, season)["LeagueScoredWeek"])
    availability, availability_version = availability_index(repo_root, season)
    weeks: list[dict[str, Any]] = []
    unavailable: list[dict[str, Any]] = []
    headers: list[dict[str, Any]] = []
    for week in range(first, scored + 1):
        try:
            document, header = build_week(model, repo_root, league_id, season, week, availability)
        except (WeekSourceNotReady, TeamInjuryImpactError) as error:
            unavailable.append({"Week": week, "Reason": str(error)})
            continue
        weeks.append(document)
        headers.append(header)
    if len({h["SettingsHash"] for h in headers}) > 1 or len({h["LineupDefinitionHash"] for h in headers}) > 1:
        raise TeamInjuryImpactError(f"Scoring settings or lineup definition change within season {season}")
    roster_ids = sorted({t["CanonicalLeagueRosterID"] for w in weeks for t in w["Teams"]})
    point_models = sorted({json.dumps({k: h["ProjectionModel"].get(k) for k in ("PointModel", "ParticipationCondition")}, sort_keys=True) for h in headers})
    return {
        "SchemaVersion": SCHEMA_VERSION,
        "Product": PRODUCT,
        "CanonicalLeagueID": league_id,
        "Season": season,
        "Models": {"InjuryImpact": model.MODEL_ID},
        "Inputs": {
            "ScoringSettingsHash": headers[0]["SettingsHash"] if headers else None,
            "LineupDefinitionHash": headers[0]["LineupDefinitionHash"] if headers else None,
            "AvailabilityProductVersion": availability_version,
            "ProjectionModels": [json.loads(item) for item in point_models],
        },
        "AsOf": {"LeagueScoredWeek": scored},
        "Weeks": weeks,
        "UnavailableWeeks": unavailable,
        "SeasonTotals": model.season_totals(weeks, roster_ids),
    }
