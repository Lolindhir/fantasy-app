from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

STANDARD_PLAYOFF_FORMATS = {
    "one-week-rounds",
    "two-week-rounds",
    "two-week-championship",
}


def resolve_nfl_regular_season_week_ceiling(repo_root: Path, season: int) -> int:
    path = repo_root / "source-data" / "nfl" / "schedules" / f"{season}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"Canonical NFL schedule is required for league week acquisition: {path}"
        )
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Canonical NFL schedule must be an object: {path}")
    try:
        payload_season = int(payload.get("Season"))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Canonical NFL schedule has invalid Season: {path}") from exc
    if payload_season != int(season):
        raise ValueError(
            f"Canonical NFL schedule season mismatch: requested {season}, got {payload_season}"
        )
    games = payload.get("Games")
    if not isinstance(games, list) or not games:
        raise ValueError(f"Canonical NFL schedule Games must be a non-empty array: {path}")

    regular_weeks: set[int] = set()
    for game in games:
        if not isinstance(game, dict):
            raise ValueError(f"Canonical NFL schedule contains a non-object game: {path}")
        if str(game.get("GameType") or "").upper() != "REG":
            continue
        week = game.get("Week")
        if isinstance(week, bool):
            raise ValueError(f"Canonical NFL schedule contains invalid REG Week: {week!r}")
        try:
            week_number = int(week)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Canonical NFL schedule contains invalid REG Week: {week!r}"
            ) from exc
        if week_number < 1:
            raise ValueError(
                f"Canonical NFL schedule contains non-positive REG Week: {week_number}"
            )
        regular_weeks.add(week_number)

    if not regular_weeks:
        raise ValueError(f"Canonical NFL schedule contains no REG weeks: {path}")
    ceiling = max(regular_weeks)
    expected = set(range(1, ceiling + 1))
    if regular_weeks != expected:
        missing = sorted(expected - regular_weeks)
        raise ValueError(
            f"Canonical NFL schedule REG weeks are not contiguous for {season}; missing {missing}"
        )
    return ceiling


def _optional_positive_int(value: object, source: str) -> int | None:
    if value is None or str(value).strip() == "":
        return None
    if isinstance(value, bool):
        raise ValueError(f"{source} must be a positive integer")
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{source} must be a positive integer: {value!r}") from exc
    if result <= 0:
        return None
    return result


def _playoff_round_count(
    league_raw: dict[str, Any],
    winners_bracket_raw: list[dict[str, Any]],
    *,
    completed: bool,
) -> int | None:
    observed_rounds: set[int] = set()
    for item in winners_bracket_raw:
        if not isinstance(item, dict):
            raise ValueError("Sleeper winners bracket entries must be objects")
        value = item.get("r")
        if value is None:
            continue
        try:
            round_number = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Sleeper winners bracket has invalid round: {value!r}") from exc
        if round_number < 1:
            raise ValueError(f"Sleeper winners bracket has non-positive round: {round_number}")
        observed_rounds.add(round_number)

    settings = league_raw.get("settings") or {}
    if not isinstance(settings, dict):
        raise ValueError("Sleeper league settings must be an object")
    playoff_teams = _optional_positive_int(settings.get("playoff_teams"), "settings.playoff_teams")
    expected_rounds = math.ceil(math.log2(playoff_teams)) if playoff_teams and playoff_teams > 1 else None

    observed_max = max(observed_rounds) if observed_rounds else None
    if observed_max is not None and expected_rounds is not None and observed_max > expected_rounds:
        raise ValueError(
            f"Sleeper winners bracket has round {observed_max} beyond expected "
            f"{expected_rounds} rounds for {playoff_teams} playoff teams"
        )
    if completed and expected_rounds is not None and observed_max is not None and observed_max != expected_rounds:
        raise ValueError(
            f"Completed Sleeper season bracket round count {observed_max} does not match "
            f"{expected_rounds} rounds implied by {playoff_teams} playoff teams"
        )
    return observed_max or expected_rounds


def _observed_playoff_format(
    playoff_start: int | None,
    playoff_round_count: int | None,
    final_week: int | None,
) -> str | None:
    if playoff_start is None or playoff_round_count is None or final_week is None:
        return None
    playoff_week_count = final_week - playoff_start + 1
    if playoff_week_count < 1:
        raise ValueError(
            f"Final league week {final_week} precedes playoff start week {playoff_start}"
        )
    if playoff_week_count == playoff_round_count:
        return "one-week-rounds"
    if playoff_week_count == 2 * playoff_round_count:
        return "two-week-rounds"
    if playoff_round_count > 1 and playoff_week_count == playoff_round_count + 1:
        return "two-week-championship"
    return "observed-custom"


def _expected_last_week(playoff_start: int, playoff_round_count: int, playoff_format: str) -> int:
    if playoff_format == "one-week-rounds":
        playoff_week_count = playoff_round_count
    elif playoff_format == "two-week-rounds":
        playoff_week_count = 2 * playoff_round_count
    elif playoff_format == "two-week-championship":
        playoff_week_count = playoff_round_count + 1
    else:
        raise ValueError(f"Cannot project unsupported playoff format: {playoff_format}")
    return playoff_start + playoff_week_count - 1


def derive_observed_week_structure(
    league_raw: object,
    winners_bracket_raw: object,
    matchup_by_week: dict[int, object],
    nfl_week_ceiling: int,
) -> dict[str, Any]:
    if not isinstance(league_raw, dict):
        raise ValueError("Sleeper league raw dataset must be an object")
    if not isinstance(winners_bracket_raw, list):
        raise ValueError("Sleeper winners bracket raw dataset must be an array")
    if nfl_week_ceiling < 1:
        raise ValueError("NFL regular-season week ceiling must be positive")

    season = _optional_positive_int(league_raw.get("season"), "league.season")
    if season is None:
        raise ValueError("Sleeper league season is required")
    settings = league_raw.get("settings") or {}
    if not isinstance(settings, dict):
        raise ValueError("Sleeper league settings must be an object")

    start_week = _optional_positive_int(settings.get("start_week"), "settings.start_week") or 1
    playoff_start = _optional_positive_int(
        settings.get("playoff_week_start"), "settings.playoff_week_start"
    )
    playoff_teams = _optional_positive_int(settings.get("playoff_teams"), "settings.playoff_teams")
    provider_round_type = settings.get("playoff_round_type")
    provider_round_type_key = (
        None if provider_round_type is None or str(provider_round_type).strip() == ""
        else str(provider_round_type).strip()
    )

    completed = str(league_raw.get("status") or "").strip().lower() == "complete"
    round_count = _playoff_round_count(
        league_raw,
        winners_bracket_raw,
        completed=completed,
    )

    highest_nonempty_matchup_week: int | None = None
    highest_assigned_matchup_week: int | None = None
    for week, raw in matchup_by_week.items():
        if not isinstance(week, int) or week < 1 or week > nfl_week_ceiling:
            raise ValueError(f"Matchup evidence contains invalid week {week!r}")
        if not isinstance(raw, list):
            raise ValueError(f"Sleeper matchup week {week} must be an array")
        if raw:
            highest_nonempty_matchup_week = max(highest_nonempty_matchup_week or week, week)
        for item in raw:
            if not isinstance(item, dict):
                raise ValueError(f"Sleeper matchup week {week} contains a non-object entry")
            matchup_id = item.get("matchup_id")
            if matchup_id is None:
                continue
            assigned_matchup_id = _optional_positive_int(
                matchup_id,
                f"matchups.week-{week}.matchup_id",
            )
            if assigned_matchup_id is None:
                raise ValueError(
                    f"Sleeper matchup week {week} contains a non-positive matchup_id"
                )
            highest_assigned_matchup_week = max(highest_assigned_matchup_week or week, week)

    last_scored_leg = _optional_positive_int(
        settings.get("last_scored_leg"), "settings.last_scored_leg"
    )
    final_week: int | None = None
    if completed:
        final_week = last_scored_leg or highest_assigned_matchup_week
        if final_week is None:
            raise ValueError(
                f"Completed Sleeper season {season} has no final-week evidence"
            )
        if highest_assigned_matchup_week is not None and highest_assigned_matchup_week > final_week:
            raise ValueError(
                f"Completed Sleeper season {season} has assigned matchup week "
                f"{highest_assigned_matchup_week} beyond last_scored_leg {final_week}"
            )
        if final_week > nfl_week_ceiling:
            raise ValueError(
                f"Completed Sleeper season {season} final week {final_week} exceeds "
                f"NFL REG ceiling {nfl_week_ceiling}"
            )

    observed_format = _observed_playoff_format(playoff_start, round_count, final_week)
    return {
        "Season": season,
        "NFLRegularSeasonWeekCeiling": nfl_week_ceiling,
        "StartWeek": start_week,
        "PlayoffStartWeek": playoff_start,
        "PlayoffTeams": playoff_teams,
        "PlayoffRoundType": provider_round_type,
        "PlayoffRoundCount": round_count,
        "HighestNonEmptyMatchupWeek": highest_nonempty_matchup_week,
        "HighestAssignedMatchupWeek": highest_assigned_matchup_week,
        "LastScoredLeg": last_scored_leg,
        "ObservedPlayoffFormat": observed_format,
        "ProjectedPlayoffFormat": observed_format if observed_format in STANDARD_PLAYOFF_FORMATS else None,
        "ExpectedLastLeagueWeek": final_week,
        "FinalLeagueWeek": final_week,
        "ProjectionEvidence": (
            {"Source": "completed-season-observation", "EvidenceSeasons": [season]}
            if completed and observed_format in STANDARD_PLAYOFF_FORMATS
            else None
        ),
        "_ProviderRoundTypeKey": provider_round_type_key,
        "_Completed": completed,
    }


def build_historical_playoff_format_evidence(
    observed_structures: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    evidence: dict[str, dict[str, Any]] = {}
    for structure in observed_structures:
        if not structure.get("_Completed"):
            continue
        key = structure.get("_ProviderRoundTypeKey")
        playoff_format = structure.get("ObservedPlayoffFormat")
        season = int(structure["Season"])
        if key is None or playoff_format not in STANDARD_PLAYOFF_FORMATS:
            continue
        existing = evidence.get(key)
        if existing is None:
            evidence[key] = {"Format": playoff_format, "EvidenceSeasons": [season]}
            continue
        if existing["Format"] != playoff_format:
            raise ValueError(
                f"Sleeper playoff_round_type {key} maps to conflicting observed formats: "
                f"{existing['Format']} in {existing['EvidenceSeasons']} vs "
                f"{playoff_format} in {season}"
            )
        existing["EvidenceSeasons"].append(season)
    for item in evidence.values():
        item["EvidenceSeasons"] = sorted(set(item["EvidenceSeasons"]))
    return evidence


def apply_historical_playoff_projection(
    structure: dict[str, Any],
    evidence: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    result = dict(structure)
    completed = bool(result.pop("_Completed", False))
    key = result.pop("_ProviderRoundTypeKey", None)
    if completed:
        return result

    if (
        result.get("PlayoffStartWeek") is None
        or result.get("PlayoffRoundCount") is None
        or key is None
    ):
        return result
    historical = evidence.get(key)
    if historical is None:
        return result

    projected_format = str(historical["Format"])
    expected_last = _expected_last_week(
        int(result["PlayoffStartWeek"]),
        int(result["PlayoffRoundCount"]),
        projected_format,
    )
    if expected_last > int(result["NFLRegularSeasonWeekCeiling"]):
        raise ValueError(
            f"Projected League final week {expected_last} exceeds NFL REG ceiling "
            f"{result['NFLRegularSeasonWeekCeiling']} for season {result['Season']}"
        )
    result["ProjectedPlayoffFormat"] = projected_format
    result["ExpectedLastLeagueWeek"] = expected_last
    result["ProjectionEvidence"] = {
        "Source": "historical-same-playoff-round-type",
        "EvidenceSeasons": list(historical["EvidenceSeasons"]),
    }
    return result


def derive_season_week_structures(
    inputs: list[tuple[object, object, dict[int, object], int]],
) -> list[dict[str, Any]]:
    observed = [
        derive_observed_week_structure(league, bracket, matchups, ceiling)
        for league, bracket, matchups, ceiling in inputs
    ]
    evidence = build_historical_playoff_format_evidence(observed)
    return [apply_historical_playoff_projection(item, evidence) for item in observed]
