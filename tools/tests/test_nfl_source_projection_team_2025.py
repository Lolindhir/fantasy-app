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


def _metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "Count": 0,
            "MAE": None,
            "RMSE": None,
            "Bias": None,
            "MeanProjection": None,
            "MeanActual": None,
        }
    errors = [float(row["Projection"]) - float(row["Actual"]) for row in rows]
    return {
        "Count": len(rows),
        "MAE": round(sum(abs(value) for value in errors) / len(errors), 4),
        "RMSE": round(math.sqrt(sum(value * value for value in errors) / len(errors)), 4),
        "Bias": round(sum(errors) / len(errors), 4),
        "MeanProjection": round(
            sum(float(row["Projection"]) for row in rows) / len(rows), 4
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


class ProjectionV3Team2025Backtest(unittest.TestCase):
    def test_real_2025_team_aggregation_from_accepted_v3(self) -> None:
        scoring = _scoring_profile(ROOT, "nfl-reise", 2025)

        observations_by_season: dict[int, dict[int, list[dict[str, Any]]]] = {}
        audits: dict[int, dict[str, Any]] = {}
        for season in (2023, 2024, 2025):
            observations, audit = build_scored_played_games(
                ROOT,
                season=season,
                scoring=scoring,
                first_week=1,
                last_week=18,
            )
            observations_by_season[season] = observations
            audits[season] = audit

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

        current_points: dict[str, list[float]] = defaultdict(list)
        current_position: dict[str, str] = {}
        team_rows: list[dict[str, Any]] = []
        starter_total = 0
        starter_projected = 0
        unavailable_reasons: Counter[str] = Counter()
        matchup_rows: list[dict[str, Any]] = []
        starter_rows: list[dict[str, Any]] = []

        for week in range(1, 18):
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
            self.assertIsInstance(matchups, list)

            for team in matchups:
                starters = team.get("Starters") or []
                starter_points = team.get("StarterPoints") or []
                self.assertEqual(len(starters), len(starter_points))

                actual = sum(float(item.get("Points") or 0.0) for item in starter_points)
                actual_by_player = {
                    _player_id(item.get("Player")): float(item.get("Points") or 0.0)
                    for item in starter_points
                }
                self.assertAlmostEqual(actual, float(team.get("Points") or 0.0), places=2)

                projections: list[float] = []
                missing: list[dict[str, str]] = []

                for starter in starters:
                    starter_total += 1
                    player_id = _player_id(starter)
                    self.assertIsNotNone(player_id)
                    assert player_id is not None

                    position = current_position.get(player_id)
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
                        projection = float(history_ppg)
                    else:
                        if baseline is None:
                            reason = "missing-baseline"
                            unavailable_reasons[reason] += 1
                            missing.append({"CanonicalPlayerID": player_id, "Reason": reason})
                            continue
                        current_ppg = sum(prior) / len(prior)
                        weight = len(prior) / (len(prior) + 1.0)
                        projection = current_ppg * weight + float(baseline) * (1.0 - weight)

                    projections.append(projection)
                    starter_projected += 1
                    starter_rows.append(
                        {
                            "Week": week,
                            "CanonicalPlayerID": player_id,
                            "Position": position,
                            "Projection": projection,
                            "Actual": actual_by_player.get(player_id, 0.0),
                            "ConfirmedParticipation": player_id in target_observations,
                        }
                    )

                complete = len(projections) == len(starters)
                row = {
                    "Week": week,
                    "CanonicalLeagueMatchupID": team.get("CanonicalLeagueMatchupID"),
                    "CanonicalLeagueRosterID": team.get("CanonicalLeagueRosterID"),
                    "Projection": sum(projections) if complete else None,
                    "Actual": actual,
                    "Complete": complete,
                    "StarterCount": len(starters),
                    "ProjectedStarterCount": len(projections),
                    "Missing": missing,
                }
                matchup_rows.append(row)
                if complete:
                    team_rows.append(row)

            # Target-week outcomes become current-season evidence only after every
            # Week W starter projection is fixed.
            for player_id, observation in target_observations.items():
                current_points[player_id].append(float(observation["FantasyPoints"]))
                current_position[player_id] = str(observation["Position"])

        regular_rows = [row for row in team_rows if int(row["Week"]) <= 13]
        playoff_rows = [row for row in team_rows if int(row["Week"]) >= 14]

        by_week = {
            str(week): _metrics([row for row in team_rows if int(row["Week"]) == week])
            for week in range(1, 18)
        }

        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in matchup_rows:
            matchup_id = row.get("CanonicalLeagueMatchupID")
            if isinstance(matchup_id, str):
                grouped[matchup_id].append(row)

        predicted_winners = 0
        correct_winners = 0
        for pair in grouped.values():
            if len(pair) != 2 or not all(bool(row["Complete"]) for row in pair):
                continue
            if float(pair[0]["Actual"]) == float(pair[1]["Actual"]):
                continue
            if float(pair[0]["Projection"]) == float(pair[1]["Projection"]):
                continue
            predicted_winners += 1
            projected_winner = max(pair, key=lambda row: float(row["Projection"]))
            actual_winner = max(pair, key=lambda row: float(row["Actual"]))
            if projected_winner["CanonicalLeagueRosterID"] == actual_winner["CanonicalLeagueRosterID"]:
                correct_winners += 1

        total_team_rows = len(matchup_rows)
        complete_team_rows = len(team_rows)
        summary = {
            "Contract": {
                "Season": 2025,
                "Weeks": "1-17",
                "RegularSeasonWeeks": "1-13",
                "PlayoffWeeks": "14-17",
                "V3": {
                    "HistoryVariant": HISTORY_TWO_SEASON,
                    "TMinus1Weight": 1.0,
                    "TMinus2Weight": 0.25,
                    "HistoryK": 0.0,
                    "CurrentK": 1.0,
                },
                "NoHistoryColdStart": "no numeric projection",
                "LeakageRule": "Week W outcomes enter current-season state only after all Week W projections are fixed",
            },
            "Coverage": {
                "TeamWeeksTotal": total_team_rows,
                "TeamWeeksComplete": complete_team_rows,
                "TeamWeekCoveragePercent": round(
                    100.0 * complete_team_rows / total_team_rows, 4
                ),
                "StarterSlotsTotal": starter_total,
                "StarterSlotsProjected": starter_projected,
                "StarterCoveragePercent": round(
                    100.0 * starter_projected / starter_total, 4
                ),
                "UnavailableReasons": dict(sorted(unavailable_reasons.items())),
            },
            "Metrics": {
                "AllLeagueWeeks": _metrics(team_rows),
                "RegularSeason": _metrics(regular_rows),
                "Playoffs": _metrics(playoff_rows),
                "ByWeek": by_week,
            },
            "StarterDiagnostics": {
                "AllProjectedStarters": _metrics(starter_rows),
                "ConfirmedParticipation": _metrics(
                    [row for row in starter_rows if row["ConfirmedParticipation"]]
                ),
                "NoConfirmedParticipation": _metrics(
                    [row for row in starter_rows if not row["ConfirmedParticipation"]]
                ),
                "NoConfirmedParticipationCount": sum(
                    1 for row in starter_rows if not row["ConfirmedParticipation"]
                ),
                "ByPosition": {
                    position: _metrics(
                        [row for row in starter_rows if row["Position"] == position]
                    )
                    for position in sorted({str(row["Position"]) for row in starter_rows})
                },
            },
            "MatchupWinnerCheck": {
                "ComparableMatchups": predicted_winners,
                "CorrectHigherScoreSide": correct_winners,
                "AccuracyPercent": (
                    round(100.0 * correct_winners / predicted_winners, 4)
                    if predicted_winners
                    else None
                ),
            },
            "ObservationAudits": audits,
        }

        print("V3_TEAM_2025_BACKTEST_SUMMARY=" + json.dumps(summary, sort_keys=True))

        self.assertEqual(102, total_team_rows)
        self.assertGreater(complete_team_rows, 0)
        self.assertLessEqual(complete_team_rows, total_team_rows)
        self.assertGreater(starter_projected, 0)
        self.assertLessEqual(starter_projected, starter_total)
        self.assertGreater(summary["Metrics"]["AllLeagueWeeks"]["Count"], 0)


if __name__ == "__main__":
    unittest.main()
