from __future__ import annotations

import json
import sys
import unittest
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from historical_projection_backtest import _scoring_profile, build_scored_played_games  # noqa: E402
from historical_projection_v2_calibration import (  # noqa: E402
    _leave_one_player_out_mean,
    _season_position_aggregates,
)
from historical_projection_v3_calibration import (  # noqa: E402
    HISTORY_TWO_SEASON,
    _history_components,
    _player_baseline,
    _player_season_summaries,
)

STARTER_COUNTS = {"QB": 2, "RB": 2, "WR": 2, "TE": 2, "K": 1}
FLEX_ELIGIBLE = {"RB", "WR", "TE"}
FLEX_COUNT = 4
FANTASY_POSITIONS = {"QB", "RB", "WR", "TE", "FB", "K"}
MODEL_KEYS = ("PureV3", "ByeAwareV3", "ParticipationOracleV3")


def _player_id(value: Any) -> str | None:
    if not isinstance(value, dict):
        return None
    value = value.get("CanonicalPlayerID")
    return str(value) if isinstance(value, str) and value else None


def _walk_player_metadata(
    value: Any,
    positions: dict[str, str],
    teams: dict[str, str],
) -> None:
    if isinstance(value, dict):
        player_id = value.get("CanonicalPlayerID")
        position = value.get("Position")
        team = value.get("Team")
        if isinstance(player_id, str) and player_id:
            if (
                isinstance(position, str)
                and position.upper() in FANTASY_POSITIONS
            ):
                positions[player_id] = position.upper()
            if isinstance(team, str) and team:
                teams[player_id] = team.upper()
        for child in value.values():
            _walk_player_metadata(child, positions, teams)
    elif isinstance(value, list):
        for child in value:
            _walk_player_metadata(child, positions, teams)


def _weekly_player_index(
    root: Path,
    season: int,
    week: int,
) -> tuple[dict[str, str], dict[str, str]]:
    path = root / "source-data/nfl/weekly-rosters" / str(season) / f"{week:02d}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    positions: dict[str, str] = {}
    teams: dict[str, str] = {}
    _walk_player_metadata(payload, positions, teams)
    return positions, teams


def _scheduled_teams_by_week(root: Path, season: int) -> dict[int, set[str]]:
    payload = json.loads(
        (root / "source-data/nfl/schedules" / f"{season}.json").read_text(encoding="utf-8")
    )
    result: dict[int, set[str]] = defaultdict(set)
    for game in payload.get("Games") or []:
        if not isinstance(game, dict) or str(game.get("GameType") or "").upper() != "REG":
            continue
        week = game.get("Week")
        if not isinstance(week, int):
            continue
        for key in ("AwayTeam", "HomeTeam"):
            team = game.get(key)
            if isinstance(team, str) and team:
                result[week].add(team.upper())
    return result


def _select_legal_lineup(
    candidates: list[dict[str, Any]],
    *,
    score_key: str,
) -> list[dict[str, Any]] | None:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in candidates:
        position = str(row["Position"]).upper()
        score = row.get(score_key)
        if score is None or position not in STARTER_COUNTS:
            continue
        buckets[position].append(row)

    for rows in buckets.values():
        rows.sort(key=lambda row: float(row[score_key]), reverse=True)

    for position, count in STARTER_COUNTS.items():
        if len(buckets.get(position, [])) < count:
            return None

    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    for position, count in STARTER_COUNTS.items():
        for row in buckets[position][:count]:
            selected.append(row)
            selected_ids.add(str(row["CanonicalPlayerID"]))

    flex_pool = [
        row
        for position in FLEX_ELIGIBLE
        for row in buckets.get(position, [])
        if str(row["CanonicalPlayerID"]) not in selected_ids
    ]
    flex_pool.sort(key=lambda row: float(row[score_key]), reverse=True)
    if len(flex_pool) < FLEX_COUNT:
        return None

    selected.extend(flex_pool[:FLEX_COUNT])
    if len(selected) != 13:
        raise AssertionError(f"Expected 13 starters, got {len(selected)}")
    return selected


def _safe_mean(values: Iterable[float]) -> float | None:
    rows = list(values)
    return sum(rows) / len(rows) if rows else None


def _r(value: float | None) -> float | None:
    return None if value is None else round(float(value), 4)


def _compare_lineups(
    *,
    model_lineup: list[dict[str, Any]] | None,
    manager_projection: float | None,
    manager_actual: float,
    manager_starter_ids: list[str],
) -> dict[str, Any] | None:
    if model_lineup is None or manager_projection is None:
        return None

    model_projection = sum(float(row["Projection"]) for row in model_lineup)
    model_actual = sum(float(row["Actual"]) for row in model_lineup)
    model_ids = {str(row["CanonicalPlayerID"]) for row in model_lineup}
    expected_delta = manager_projection - model_projection
    realized_delta = manager_actual - model_actual
    return {
        "SameLineup": model_ids == set(manager_starter_ids),
        "ExpectedPointsForgone": -expected_delta,
        "RealizedDeltaVsModel": realized_delta,
        "ManagerAlpha": realized_delta - expected_delta,
        "ModelNoScheduledGameSlots": sum(
            1 for row in model_lineup if not bool(row["ScheduledThisWeek"])
        ),
        "ModelNoConfirmedParticipationSlots": sum(
            1 for row in model_lineup if not bool(row["ConfirmedParticipation"])
        ),
    }


def _aggregate_comparisons(
    team_weeks: list[dict[str, Any]],
    model_key: str,
) -> dict[str, Any]:
    comparable = [row[model_key] for row in team_weeks if row.get(model_key) is not None]
    different = [row for row in comparable if not bool(row["SameLineup"])]
    beat_model = [row for row in different if float(row["RealizedDeltaVsModel"]) > 0]
    model_better = [row for row in different if float(row["RealizedDeltaVsModel"]) < 0]
    tied = [row for row in different if float(row["RealizedDeltaVsModel"]) == 0]

    return {
        "ComparableWeeks": len(comparable),
        "AgainstModelWeeks": len(different),
        "SameAsModelWeeks": len(comparable) - len(different),
        "ExpectedPointsForgoneTotal": _r(
            sum(float(row["ExpectedPointsForgone"]) for row in comparable)
        ),
        "ExpectedPointsForgonePerComparableWeek": _r(
            _safe_mean(float(row["ExpectedPointsForgone"]) for row in comparable)
        ),
        "RealizedPointsVsModelTotal": _r(
            sum(float(row["RealizedDeltaVsModel"]) for row in comparable)
        ),
        "ManagerAlphaTotal": _r(
            sum(float(row["ManagerAlpha"]) for row in comparable)
        ),
        "ManagerAlphaPerComparableWeek": _r(
            _safe_mean(float(row["ManagerAlpha"]) for row in comparable)
        ),
        "BeatModelWeeks": len(beat_model),
        "ModelBetterWeeks": len(model_better),
        "TiedModelWeeks": len(tied),
        "BeatModelRateOnDifferentLineupsPercent": _r(
            100.0 * len(beat_model) / len(different) if different else None
        ),
        "ModelNoScheduledGameSlots": sum(
            int(row["ModelNoScheduledGameSlots"]) for row in comparable
        ),
        "ModelNoConfirmedParticipationSlots": sum(
            int(row["ModelNoConfirmedParticipationSlots"]) for row in comparable
        ),
    }


class ProjectionV3ManagerLineup2025Analysis(unittest.TestCase):
    def test_2025_manager_lineup_decisions_against_v3(self) -> None:
        scoring = _scoring_profile(ROOT, "nfl-reise", 2025)

        observations_by_season: dict[int, dict[int, list[dict[str, Any]]]] = {}
        for season in (2023, 2024, 2025):
            observations, _audit = build_scored_played_games(
                ROOT,
                season=season,
                scoring=scoring,
                first_week=1,
                last_week=18,
            )
            observations_by_season[season] = observations

        season_summaries = {
            season: _player_season_summaries(rows)
            for season, rows in observations_by_season.items()
        }
        (
            previous_player_sums,
            previous_player_counts,
            previous_position_sums,
            previous_position_counts,
        ) = _season_position_aggregates(observations_by_season[2024])

        scheduled_teams = _scheduled_teams_by_week(ROOT, 2025)

        members = json.loads(
            (
                ROOT
                / "source-data/leagues/nfl-reise/seasons/2025/members.json"
            ).read_text(encoding="utf-8")
        )
        rosters = json.loads(
            (
                ROOT
                / "source-data/leagues/nfl-reise/seasons/2025/rosters.json"
            ).read_text(encoding="utf-8")
        )
        member_names = {
            str(row["CanonicalLeagueMemberID"]): str(row["DisplayName"])
            for row in members
        }
        roster_to_member = {
            str(row["CanonicalLeagueRosterID"]): str(row["CanonicalLeagueMemberID"])
            for row in rosters
        }

        current_points: dict[str, list[float]] = defaultdict(list)
        current_positions: dict[str, str] = {}
        team_weeks: list[dict[str, Any]] = []
        coverage = Counter()

        for week in range(1, 18):
            weekly_positions, weekly_teams = _weekly_player_index(ROOT, 2025, week)
            week_scheduled_teams = scheduled_teams.get(week, set())
            target_observations = {
                str(row["CanonicalPlayerID"]): row
                for row in observations_by_season[2025].get(week, [])
            }

            matchup_path = (
                ROOT
                / "source-data/leagues/nfl-reise/seasons/2025/matchups"
                / f"week-{week}.json"
            )
            matchups = json.loads(matchup_path.read_text(encoding="utf-8"))

            for team in matchups:
                coverage["team_weeks"] += 1
                roster_id = str(team["CanonicalLeagueRosterID"])
                member_id = roster_to_member.get(roster_id)
                manager = member_names.get(member_id or "", roster_id)

                player_points = {
                    _player_id(item.get("Player")): float(item.get("Points") or 0.0)
                    for item in (team.get("PlayerPoints") or [])
                    if _player_id(item.get("Player")) is not None
                }
                roster_player_ids = [
                    player_id
                    for player_id in (_player_id(item) for item in (team.get("Players") or []))
                    if player_id is not None
                ]
                starter_ids = [
                    player_id
                    for player_id in (_player_id(item) for item in (team.get("Starters") or []))
                    if player_id is not None
                ]

                self.assertEqual(13, len(starter_ids))
                self.assertTrue(set(starter_ids).issubset(set(roster_player_ids)))

                candidates: list[dict[str, Any]] = []
                projection_by_player: dict[str, float] = {}

                for player_id in roster_player_ids:
                    position = weekly_positions.get(player_id) or current_positions.get(player_id)
                    if position is None:
                        previous = season_summaries.get(2024, {}).get(player_id)
                        older = season_summaries.get(2023, {}).get(player_id)
                        target = target_observations.get(player_id)
                        position = (
                            str(previous["Position"])
                            if previous is not None
                            else str(older["Position"])
                            if older is not None
                            else str(target["Position"])
                            if target is not None
                            else None
                        )
                    if position is None or position.upper() not in FANTASY_POSITIONS:
                        coverage["unknown_position_roster_entries"] += 1
                        continue
                    position = position.upper()

                    prior = current_points.get(player_id, [])
                    history_ppg, history_games = _history_components(
                        player_id,
                        target_season=2025,
                        season_summaries=season_summaries,
                        variant=HISTORY_TWO_SEASON,
                        decay=0.25,
                    )
                    history_backed = history_ppg is not None and history_games > 0

                    position_prior = _leave_one_player_out_mean(
                        position=position,
                        player_id=player_id,
                        player_sums=previous_player_sums,
                        player_counts=previous_player_counts,
                        position_sums=previous_position_sums,
                        position_counts=previous_position_counts,
                    )
                    baseline = _player_baseline(
                        history_ppg=history_ppg,
                        effective_history_games=history_games,
                        position_prior=position_prior,
                        history_k=0.0,
                    )

                    projection: float | None
                    if not prior:
                        projection = float(history_ppg) if history_backed else None
                    elif baseline is None:
                        projection = None
                    else:
                        current_ppg = sum(prior) / len(prior)
                        weight = len(prior) / (len(prior) + 1.0)
                        projection = current_ppg * weight + float(baseline) * (1.0 - weight)

                    if projection is None:
                        coverage["no_projection_roster_entries"] += 1
                    else:
                        projection_by_player[player_id] = projection

                    nfl_team = weekly_teams.get(player_id)
                    scheduled_this_week = (
                        nfl_team is not None and nfl_team in week_scheduled_teams
                    )
                    candidates.append(
                        {
                            "CanonicalPlayerID": player_id,
                            "Position": position,
                            "NFLTeam": nfl_team,
                            "Projection": projection,
                            "Actual": player_points.get(player_id, 0.0),
                            "ScheduledThisWeek": scheduled_this_week,
                            "ConfirmedParticipation": player_id in target_observations,
                        }
                    )

                manager_actual = float(team.get("Points") or 0.0)
                manager_projection_values = [
                    projection_by_player.get(player_id) for player_id in starter_ids
                ]
                manager_projection_complete = all(
                    value is not None for value in manager_projection_values
                )
                manager_projection = (
                    sum(float(value) for value in manager_projection_values if value is not None)
                    if manager_projection_complete
                    else None
                )

                pure_model = _select_legal_lineup(candidates, score_key="Projection")
                bye_aware_model = _select_legal_lineup(
                    [row for row in candidates if row["ScheduledThisWeek"]],
                    score_key="Projection",
                )
                participation_oracle_model = _select_legal_lineup(
                    [row for row in candidates if row["ConfirmedParticipation"]],
                    score_key="Projection",
                )
                actual_optimal_lineup = _select_legal_lineup(candidates, score_key="Actual")

                row: dict[str, Any] = {
                    "Week": week,
                    "Manager": manager,
                    "ManagerActual": manager_actual,
                    "ActualOptimal": (
                        sum(float(item["Actual"]) for item in actual_optimal_lineup)
                        if actual_optimal_lineup is not None
                        else None
                    ),
                }
                row["PureV3"] = _compare_lineups(
                    model_lineup=pure_model,
                    manager_projection=manager_projection,
                    manager_actual=manager_actual,
                    manager_starter_ids=starter_ids,
                )
                row["ByeAwareV3"] = _compare_lineups(
                    model_lineup=bye_aware_model,
                    manager_projection=manager_projection,
                    manager_actual=manager_actual,
                    manager_starter_ids=starter_ids,
                )
                row["ParticipationOracleV3"] = _compare_lineups(
                    model_lineup=participation_oracle_model,
                    manager_projection=manager_projection,
                    manager_actual=manager_actual,
                    manager_starter_ids=starter_ids,
                )

                if manager_projection is not None:
                    coverage["manager_projection_complete_team_weeks"] += 1
                if actual_optimal_lineup is not None:
                    coverage["actual_efficiency_team_weeks"] += 1
                for model_key in MODEL_KEYS:
                    if row[model_key] is not None:
                        coverage[f"{model_key}_comparable_team_weeks"] += 1

                team_weeks.append(row)

            # Week W outcomes enter current-season evidence only after every
            # lineup decision for Week W has been evaluated.
            for player_id, observation in target_observations.items():
                current_points[player_id].append(float(observation["FantasyPoints"]))
                current_positions[player_id] = str(observation["Position"]).upper()

        by_manager: dict[str, Any] = {}
        for manager in sorted({str(row["Manager"]) for row in team_weeks}):
            rows = [row for row in team_weeks if row["Manager"] == manager]
            efficiency_rows = [row for row in rows if row["ActualOptimal"] is not None]
            total_manager_actual = sum(float(row["ManagerActual"]) for row in efficiency_rows)
            total_optimal_actual = sum(float(row["ActualOptimal"]) for row in efficiency_rows)
            by_manager[manager] = {
                "TeamWeeks": len(rows),
                "ActualLineupEfficiencyPercent": _r(
                    100.0 * total_manager_actual / total_optimal_actual
                    if total_optimal_actual > 0
                    else None
                ),
                "ActualPointsLeftOnBenchPerWeek": _r(
                    _safe_mean(
                        float(row["ActualOptimal"]) - float(row["ManagerActual"])
                        for row in efficiency_rows
                    )
                ),
                **{
                    model_key: _aggregate_comparisons(rows, model_key)
                    for model_key in MODEL_KEYS
                },
            }

        efficiency_all = [row for row in team_weeks if row["ActualOptimal"] is not None]
        total_manager_actual = sum(float(row["ManagerActual"]) for row in efficiency_all)
        total_optimal_actual = sum(float(row["ActualOptimal"]) for row in efficiency_all)

        summary = {
            "Contract": {
                "Season": 2025,
                "Weeks": "1-17",
                "RosterTruth": "week-specific matchup Players",
                "ManagerLineupTruth": "week-specific matchup Starters",
                "FlexEligibility": sorted(FLEX_ELIGIBLE),
                "V3": {
                    "HistoryVariant": HISTORY_TWO_SEASON,
                    "TMinus1Weight": 1.0,
                    "TMinus2Weight": 0.25,
                    "HistoryK": 0.0,
                    "CurrentK": 1.0,
                    "NoHistoryColdStart": "no numeric projection",
                },
                "ComparisonLayers": {
                    "PureV3": "projection only; deliberately no schedule or availability filter",
                    "ByeAwareV3": "decision-time schedule filter removes players whose NFL team has no game that week",
                    "ParticipationOracleV3": "hindsight diagnostic restricted to confirmed participants; not a deployable pregame model",
                },
                "ManagerAlpha": "Realized relative advantage minus expected relative advantage",
            },
            "Coverage": {
                "TeamWeeks": coverage["team_weeks"],
                "ManagerProjectionCompleteTeamWeeks": coverage[
                    "manager_projection_complete_team_weeks"
                ],
                "ActualEfficiencyTeamWeeks": coverage["actual_efficiency_team_weeks"],
                "PureV3ComparableTeamWeeks": coverage["PureV3_comparable_team_weeks"],
                "ByeAwareV3ComparableTeamWeeks": coverage[
                    "ByeAwareV3_comparable_team_weeks"
                ],
                "ParticipationOracleV3ComparableTeamWeeks": coverage[
                    "ParticipationOracleV3_comparable_team_weeks"
                ],
                "UnknownPositionRosterEntries": coverage["unknown_position_roster_entries"],
                "NoProjectionRosterEntries": coverage["no_projection_roster_entries"],
            },
            "League": {
                "ActualLineupEfficiencyPercent": _r(
                    100.0 * total_manager_actual / total_optimal_actual
                    if total_optimal_actual > 0
                    else None
                ),
                "ActualPointsLeftOnBenchPerWeek": _r(
                    _safe_mean(
                        float(row["ActualOptimal"]) - float(row["ManagerActual"])
                        for row in efficiency_all
                    )
                ),
                **{
                    model_key: _aggregate_comparisons(team_weeks, model_key)
                    for model_key in MODEL_KEYS
                },
            },
            "ByManager": by_manager,
        }

        print("V3_MANAGER_2025_ANALYSIS=" + json.dumps(summary, sort_keys=True))

        self.assertEqual(102, coverage["team_weeks"])
        self.assertEqual(6, len(by_manager))
        self.assertGreater(coverage["ByeAwareV3_comparable_team_weeks"], 0)
        self.assertGreater(coverage["ParticipationOracleV3_comparable_team_weeks"], 0)
        # The schedule-aware layer must remove all known bye selections by construction.
        self.assertEqual(
            0,
            summary["League"]["ByeAwareV3"]["ModelNoScheduledGameSlots"],
        )
        self.assertEqual(
            0,
            summary["League"]["ParticipationOracleV3"][
                "ModelNoConfirmedParticipationSlots"
            ],
        )


if __name__ == "__main__":
    unittest.main()
