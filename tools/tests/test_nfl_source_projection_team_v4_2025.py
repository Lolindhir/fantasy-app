from __future__ import annotations

import json
import math
import sys
import unittest
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from historical_projection_backtest import (  # noqa: E402
    _scoring_profile,
    build_scored_played_games,
)
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
from historical_projection_v4_calibration import (  # noqa: E402
    FEATURE_OPPORTUNITY,
    FEATURE_SNAP,
    RECENT_WINDOW,
    VARIANT_COMBINED,
    VARIANT_SNAP,
    _adjustment,
    _fallback_older_current_mean,
    _historical_usage_baseline,
    _position_group,
    _recent_mean,
    _usage_by_week,
    _usage_season_summaries,
    build_v4_report,
)

MODELS = ("V3", "V4A", "V4C")


def _metrics(rows: list[dict[str, Any]], projection_key: str) -> dict[str, Any]:
    if not rows:
        return {
            "Count": 0,
            "MAE": None,
            "RMSE": None,
            "Bias": None,
            "MeanProjection": None,
            "MeanActual": None,
        }
    errors = [float(row[projection_key]) - float(row["Actual"]) for row in rows]
    return {
        "Count": len(rows),
        "MAE": round(sum(abs(value) for value in errors) / len(errors), 4),
        "RMSE": round(math.sqrt(sum(value * value for value in errors) / len(errors)), 4),
        "Bias": round(sum(errors) / len(errors), 4),
        "MeanProjection": round(
            sum(float(row[projection_key]) for row in rows) / len(rows), 4
        ),
        "MeanActual": round(
            sum(float(row["Actual"]) for row in rows) / len(rows), 4
        ),
    }


def _player_id(value: Any) -> str | None:
    if not isinstance(value, dict):
        return None
    player_id = value.get("CanonicalPlayerID")
    return player_id if isinstance(player_id, str) and player_id else None


def _usage_features(
    player_id: str,
    *,
    target_season: int,
    current_usage_history: dict[str, list[dict[str, Any]]],
    usage_season_summaries: dict[int, dict[str, dict[str, Any]]],
) -> dict[str, Any]:
    history = current_usage_history.get(player_id, [])
    result: dict[str, Any] = {"PositionGroup": None}

    for feature, history_key in (
        (FEATURE_SNAP, "SnapShare"),
        (FEATURE_OPPORTUNITY, "Opportunity"),
    ):
        recent = _recent_mean(history, history_key)
        baseline = _historical_usage_baseline(
            player_id,
            target_season=target_season,
            feature=history_key,
            season_summaries=usage_season_summaries,
        )
        if baseline is None:
            baseline = _fallback_older_current_mean(history, history_key)

        available = recent is not None and baseline is not None
        result[feature] = (
            float(recent) - float(baseline) if available else 0.0
        )
        result[f"{feature}Available"] = available

    return result


def _apply_v4(
    v3_projection: float,
    row: dict[str, Any],
    *,
    fit: dict[str, Any],
    clip: float | None,
) -> float:
    raw = _adjustment(row, fit)
    if clip is not None:
        raw = max(-float(clip), min(float(clip), raw))
    return v3_projection + raw


class ProjectionV4Team2025Backtest(unittest.TestCase):
    def test_v3_v4_team_end_score_on_actual_2025_starters(self) -> None:
        scoring = _scoring_profile(ROOT, "nfl-reise", 2025)

        # Reproduce the exact accepted V4 calibration contract before evaluating
        # team aggregation. 2025 remains holdout-only.
        v4_report = build_v4_report(
            ROOT,
            league_id="nfl-reise",
            scoring_season=2025,
            calibration_seasons=[2023, 2024],
            holdout_season=2025,
            first_week=1,
            last_week=18,
        )
        snap_calibration = v4_report["Calibrations"][VARIANT_SNAP]
        combined_calibration = v4_report["Calibrations"][VARIANT_COMBINED]

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

        usage_by_season = {
            season: _usage_by_week(
                ROOT,
                season=season,
                first_week=1,
                last_week=18,
            )
            for season in (2023, 2024, 2025)
        }
        played_ids_by_season = {
            season: {
                week: {str(row["CanonicalPlayerID"]) for row in rows}
                for week, rows in observations.items()
            }
            for season, observations in observations_by_season.items()
        }
        usage_season_summaries = {
            season: _usage_season_summaries(
                usage_by_season[season],
                played_ids_by_season[season],
            )
            for season in (2023, 2024)
        }

        current_points: dict[str, list[float]] = defaultdict(list)
        current_positions: dict[str, str] = {}
        current_usage_history: dict[str, list[dict[str, Any]]] = defaultdict(list)

        rows: list[dict[str, Any]] = []
        starter_total = 0
        starter_projected = 0
        unavailable_reasons: Counter[str] = Counter()

        for week in range(1, 18):
            target_observations = {
                str(row["CanonicalPlayerID"]): row
                for row in observations_by_season[2025].get(week, [])
            }
            target_usage = usage_by_season[2025].get(week, {})

            matchup_path = (
                ROOT
                / "source-data/leagues/nfl-reise/seasons/2025/matchups"
                / f"week-{week}.json"
            )
            matchups = json.loads(matchup_path.read_text(encoding="utf-8"))
            self.assertIsInstance(matchups, list)

            for team in matchups:
                starters = team.get("Starters") or []
                starter_points = team.get("StarterPoints") or []
                self.assertEqual(len(starters), len(starter_points))

                actual = sum(float(item.get("Points") or 0.0) for item in starter_points)
                self.assertAlmostEqual(actual, float(team.get("Points") or 0.0), places=2)

                projections = {model: [] for model in MODELS}
                missing: list[dict[str, str]] = []
                all_starters_participated = True

                for starter in starters:
                    starter_total += 1
                    player_id = _player_id(starter)
                    self.assertIsNotNone(player_id)
                    assert player_id is not None

                    if player_id not in target_observations:
                        all_starters_participated = False

                    position = current_positions.get(player_id)
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

                    prior = current_points.get(player_id, [])
                    history_ppg, history_games = _history_components(
                        player_id,
                        target_season=2025,
                        season_summaries=season_summaries,
                        variant=HISTORY_TWO_SEASON,
                        decay=0.25,
                    )
                    history_backed = history_ppg is not None and history_games > 0

                    if position is None:
                        reason = "unknown-position"
                        unavailable_reasons[reason] += 1
                        missing.append({"CanonicalPlayerID": player_id, "Reason": reason})
                        continue

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

                    if not prior:
                        if not history_backed:
                            reason = "no-history-cold-start"
                            unavailable_reasons[reason] += 1
                            missing.append({"CanonicalPlayerID": player_id, "Reason": reason})
                            continue
                        v3 = float(history_ppg)
                    else:
                        if baseline is None:
                            reason = "missing-baseline"
                            unavailable_reasons[reason] += 1
                            missing.append({"CanonicalPlayerID": player_id, "Reason": reason})
                            continue
                        current_ppg = sum(prior) / len(prior)
                        weight = len(prior) / (len(prior) + 1.0)
                        v3 = current_ppg * weight + float(baseline) * (1.0 - weight)

                    feature_row = _usage_features(
                        player_id,
                        target_season=2025,
                        current_usage_history=current_usage_history,
                        usage_season_summaries=usage_season_summaries,
                    )
                    feature_row["PositionGroup"] = _position_group(position)

                    v4a = _apply_v4(
                        v3,
                        feature_row,
                        fit=snap_calibration["FinalFit"],
                        clip=snap_calibration["Selected"]["Clip"],
                    )
                    v4c = _apply_v4(
                        v3,
                        feature_row,
                        fit=combined_calibration["FinalFit"],
                        clip=combined_calibration["Selected"]["Clip"],
                    )

                    projections["V3"].append(v3)
                    projections["V4A"].append(v4a)
                    projections["V4C"].append(v4c)
                    starter_projected += 1

                complete = all(len(projections[model]) == len(starters) for model in MODELS)
                rows.append(
                    {
                        "Week": week,
                        "CanonicalLeagueMatchupID": team.get("CanonicalLeagueMatchupID"),
                        "CanonicalLeagueRosterID": team.get("CanonicalLeagueRosterID"),
                        "Actual": actual,
                        "Complete": complete,
                        "AllStartersParticipated": all_starters_participated,
                        "StarterCount": len(starters),
                        "ProjectedStarterCount": len(projections["V3"]),
                        "Missing": missing,
                        "V3": sum(projections["V3"]) if complete else None,
                        "V4A": sum(projections["V4A"]) if complete else None,
                        "V4C": sum(projections["V4C"]) if complete else None,
                    }
                )

            # Week-W outcomes and usage enter state only after all W projections
            # have been fixed for every team.
            for player_id, observation in target_observations.items():
                current_points[player_id].append(float(observation["FantasyPoints"]))
                current_positions[player_id] = str(observation["Position"])
                usage = target_usage.get(player_id)
                if usage is not None:
                    current_usage_history[player_id].append(
                        {
                            "SnapShare": usage.get("SnapShare"),
                            "Opportunity": usage.get("Opportunity"),
                        }
                    )

        complete_rows = [row for row in rows if row["Complete"]]
        all_participated_rows = [
            row for row in complete_rows if row["AllStartersParticipated"]
        ]
        regular_rows = [row for row in complete_rows if int(row["Week"]) <= 13]
        playoff_rows = [row for row in complete_rows if int(row["Week"]) >= 14]

        metrics = {
            model: {
                "AllLeagueWeeks": _metrics(complete_rows, model),
                "AllStartersParticipated": _metrics(all_participated_rows, model),
                "RegularSeason": _metrics(regular_rows, model),
                "Playoffs": _metrics(playoff_rows, model),
            }
            for model in MODELS
        }

        matchup_direction: dict[str, Any] = {}
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            matchup_id = row.get("CanonicalLeagueMatchupID")
            if isinstance(matchup_id, str):
                grouped[matchup_id].append(row)

        for model in MODELS:
            comparable = 0
            correct = 0
            for pair in grouped.values():
                if len(pair) != 2 or not all(bool(row["Complete"]) for row in pair):
                    continue
                if float(pair[0]["Actual"]) == float(pair[1]["Actual"]):
                    continue
                if float(pair[0][model]) == float(pair[1][model]):
                    continue
                comparable += 1
                projected_winner = max(pair, key=lambda row: float(row[model]))
                actual_winner = max(pair, key=lambda row: float(row["Actual"]))
                if (
                    projected_winner["CanonicalLeagueRosterID"]
                    == actual_winner["CanonicalLeagueRosterID"]
                ):
                    correct += 1
            matchup_direction[model] = {
                "ComparableMatchups": comparable,
                "CorrectHigherScoreSide": correct,
                "AccuracyPercent": (
                    round(100.0 * correct / comparable, 4) if comparable else None
                ),
            }

        summary = {
            "Contract": {
                "Season": 2025,
                "Weeks": "1-17",
                "ActualLineup": "historical matchup Starters",
                "TeamPrediction": "sum of pregame player projections for actual starters",
                "CommonCohortRule": "V3/V4-A/V4-C must all project every starter in a team-week",
                "V4Holdout": "same coefficients/hyperparameters selected without 2025",
                "LeakageRule": (
                    "Week W fantasy points, snaps and opportunities enter state only "
                    "after all Week W team projections are fixed"
                ),
            },
            "Coverage": {
                "TeamWeeksTotal": len(rows),
                "TeamWeeksCompleteCommon": len(complete_rows),
                "TeamWeekCoveragePercent": round(
                    100.0 * len(complete_rows) / len(rows), 4
                ),
                "AllStartersParticipatedCompleteTeamWeeks": len(all_participated_rows),
                "StarterSlotsTotal": starter_total,
                "StarterSlotsProjected": starter_projected,
                "StarterCoveragePercent": round(
                    100.0 * starter_projected / starter_total, 4
                ),
                "UnavailableReasons": dict(sorted(unavailable_reasons.items())),
            },
            "Metrics": metrics,
            "MatchupDirection": matchup_direction,
        }

        print("V4_TEAM_2025_BACKTEST_SUMMARY=" + json.dumps(summary, sort_keys=True))

        self.assertEqual(102, len(rows))
        self.assertEqual(97, len(complete_rows))
        self.assertEqual(1318, starter_projected)
        self.assertEqual(1326, starter_total)
        self.assertEqual({"no-history-cold-start": 8}, dict(unavailable_reasons))
        self.assertEqual(97, metrics["V3"]["AllLeagueWeeks"]["Count"])
        self.assertEqual(97, metrics["V4A"]["AllLeagueWeeks"]["Count"])
        self.assertEqual(97, metrics["V4C"]["AllLeagueWeeks"]["Count"])


if __name__ == "__main__":
    unittest.main()
