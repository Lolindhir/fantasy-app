from __future__ import annotations

import json
import math
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

TARGET_SEASONS = (2024, 2025)
FANTASY_POSITIONS = {"QB", "RB", "WR", "TE", "FB", "K"}
IGNORED_LINEUP_SLOTS = {"BN", "IR", "RESERVE", "TAXI"}
SLOT_ELIGIBILITY = {
    "FLEX": {"RB", "WR", "TE"},
    "SUPER_FLEX": {"QB", "RB", "WR", "TE"},
    "WRRB_FLEX": {"WR", "RB"},
    "REC_FLEX": {"WR", "TE"},
}


def _player_id(value: Any) -> str | None:
    if not isinstance(value, dict):
        return None
    player_id = value.get("CanonicalPlayerID")
    return str(player_id) if isinstance(player_id, str) and player_id else None


def _normalize_lineup_position(position: str) -> str:
    value = position.upper()
    return "RB" if value == "FB" else value


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
            if isinstance(position, str) and position.upper() in FANTASY_POSITIONS:
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
        (root / "source-data/nfl/schedules" / f"{season}.json").read_text(
            encoding="utf-8"
        )
    )
    result: dict[int, set[str]] = defaultdict(set)
    for game in payload.get("Games") or []:
        if not isinstance(game, dict):
            continue
        if str(game.get("GameType") or "").upper() != "REG":
            continue
        week = game.get("Week")
        if not isinstance(week, int):
            continue
        for key in ("AwayTeam", "HomeTeam"):
            team = game.get(key)
            if isinstance(team, str) and team:
                result[week].add(team.upper())
    return result


def _slot_allowed_positions(slot: str) -> set[str]:
    slot_key = slot.upper()
    if slot_key in SLOT_ELIGIBILITY:
        return set(SLOT_ELIGIBILITY[slot_key])
    if slot_key in {"QB", "RB", "WR", "TE", "K"}:
        return {slot_key}
    raise ValueError(f"Unsupported historical starter slot: {slot}")


def _starter_slots(roster_positions: Iterable[str]) -> list[str]:
    return [
        str(slot).upper()
        for slot in roster_positions
        if str(slot).upper() not in IGNORED_LINEUP_SLOTS
    ]


def _select_optimal_lineup(
    candidates: list[dict[str, Any]],
    *,
    slots: list[str],
    score_key: str,
) -> list[dict[str, Any]] | None:
    # The lineup objective only depends on how many players of each base
    # position are selected. Enumerate feasible position-count vectors induced by
    # the actual season's slot types, then take the top-N candidates per position.
    reachable: set[tuple[int, int, int, int, int]] = {(0, 0, 0, 0, 0)}
    positions = ("QB", "RB", "WR", "TE", "K")
    position_index = {position: index for index, position in enumerate(positions)}

    for slot in slots:
        allowed = _slot_allowed_positions(slot)
        next_reachable: set[tuple[int, int, int, int, int]] = set()
        for counts in reachable:
            for position in allowed:
                index = position_index[position]
                updated = list(counts)
                updated[index] += 1
                next_reachable.add(tuple(updated))
        reachable = next_reachable

    by_position: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in candidates:
        score = row.get(score_key)
        if score is None:
            continue
        position = _normalize_lineup_position(str(row["Position"]))
        if position not in position_index:
            continue
        by_position[position].append(row)

    for rows in by_position.values():
        rows.sort(key=lambda row: float(row[score_key]), reverse=True)

    best_score: float | None = None
    best_counts: tuple[int, int, int, int, int] | None = None

    for counts in reachable:
        possible = True
        score = 0.0
        for position, count in zip(positions, counts):
            rows = by_position.get(position, [])
            if len(rows) < count:
                possible = False
                break
            score += sum(float(row[score_key]) for row in rows[:count])
        if not possible:
            continue
        if best_score is None or score > best_score:
            best_score = score
            best_counts = counts

    if best_counts is None:
        return None

    selected: list[dict[str, Any]] = []
    for position, count in zip(positions, best_counts):
        selected.extend(by_position.get(position, [])[:count])

    if len(selected) != len(slots):
        raise AssertionError(
            f"Expected {len(slots)} selected players, got {len(selected)}"
        )
    return selected


def _safe_mean(values: Iterable[float]) -> float | None:
    rows = list(values)
    return sum(rows) / len(rows) if rows else None


def _round(value: float | None) -> float | None:
    return None if value is None else round(float(value), 4)


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 2:
        return None
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    denominator_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    denominator_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    if denominator_x == 0 or denominator_y == 0:
        return None
    return numerator / (denominator_x * denominator_y)


def _average_ranks(values: list[float]) -> list[float]:
    indexed = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    cursor = 0
    while cursor < len(indexed):
        end = cursor + 1
        while end < len(indexed) and indexed[end][1] == indexed[cursor][1]:
            end += 1
        average_rank = (cursor + 1 + end) / 2.0
        for index, _value in indexed[cursor:end]:
            ranks[index] = average_rank
        cursor = end
    return ranks


def _spearman(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 2:
        return None
    return _pearson(_average_ranks(xs), _average_ranks(ys))


def _comparison(
    *,
    manager_projection: float | None,
    manager_actual: float,
    manager_starter_ids: list[str],
    model_lineup: list[dict[str, Any]] | None,
) -> dict[str, Any] | None:
    if manager_projection is None or model_lineup is None:
        return None
    model_projection = sum(float(row["Projection"]) for row in model_lineup)
    model_actual = sum(float(row["Actual"]) for row in model_lineup)
    model_ids = {str(row["CanonicalPlayerID"]) for row in model_lineup}
    expected_delta = manager_projection - model_projection
    realized_delta = manager_actual - model_actual
    return {
        "SameLineup": model_ids == set(manager_starter_ids),
        "ExpectedPointsForgone": -expected_delta,
        "RealizedPointsVsModel": realized_delta,
        "ManagerAlpha": realized_delta - expected_delta,
    }


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    comparable = [row for row in rows if row.get("Comparison") is not None]
    different = [
        row["Comparison"]
        for row in comparable
        if not bool(row["Comparison"]["SameLineup"])
    ]
    comparisons = [row["Comparison"] for row in comparable]
    beat = [row for row in different if float(row["RealizedPointsVsModel"]) > 0]
    model_better = [
        row for row in different if float(row["RealizedPointsVsModel"]) < 0
    ]
    tied = [row for row in different if float(row["RealizedPointsVsModel"]) == 0]

    return {
        "ComparableWeeks": len(comparisons),
        "DifferentLineupWeeks": len(different),
        "SameLineupWeeks": len(comparisons) - len(different),
        "BeatModelWeeks": len(beat),
        "ModelBetterWeeks": len(model_better),
        "TiedWeeks": len(tied),
        "BeatModelRatePercent": _round(
            100.0 * len(beat) / len(different) if different else None
        ),
        "ExpectedPointsForgonePerWeek": _round(
            _safe_mean(float(row["ExpectedPointsForgone"]) for row in comparisons)
        ),
        "RealizedPointsVsModelTotal": _round(
            sum(float(row["RealizedPointsVsModel"]) for row in comparisons)
        ),
        "RealizedPointsVsModelPerWeek": _round(
            _safe_mean(float(row["RealizedPointsVsModel"]) for row in comparisons)
        ),
        "ManagerAlphaTotal": _round(
            sum(float(row["ManagerAlpha"]) for row in comparisons)
        ),
        "ManagerAlphaPerWeek": _round(
            _safe_mean(float(row["ManagerAlpha"]) for row in comparisons)
        ),
    }


def _analyze_season(
    *,
    root: Path,
    target_season: int,
) -> dict[str, Any]:
    scoring = _scoring_profile(root, "nfl-reise", target_season)

    observations_by_season: dict[int, dict[int, list[dict[str, Any]]]] = {}
    for season in (target_season - 2, target_season - 1, target_season):
        observations, _audit = build_scored_played_games(
            root,
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
    ) = _season_position_aggregates(
        observations_by_season[target_season - 1]
    )

    season_root = (
        root
        / "source-data/leagues/nfl-reise/seasons"
        / str(target_season)
    )
    league = json.loads((season_root / "league.json").read_text(encoding="utf-8"))
    members = json.loads((season_root / "members.json").read_text(encoding="utf-8"))
    rosters = json.loads((season_root / "rosters.json").read_text(encoding="utf-8"))

    final_week = int(league["Settings"]["last_scored_leg"])
    slots = _starter_slots(league["RosterPositions"])
    scheduled_teams = _scheduled_teams_by_week(root, target_season)

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
    rows: list[dict[str, Any]] = []
    coverage = Counter()

    for week in range(1, final_week + 1):
        weekly_positions, weekly_teams = _weekly_player_index(
            root, target_season, week
        )
        target_observations = {
            str(row["CanonicalPlayerID"]): row
            for row in observations_by_season[target_season].get(week, [])
        }
        matchup_path = season_root / "matchups" / f"week-{week}.json"
        matchups = json.loads(matchup_path.read_text(encoding="utf-8"))

        for team in matchups:
            coverage["team_weeks"] += 1
            roster_id = str(team["CanonicalLeagueRosterID"])
            member_id = roster_to_member.get(roster_id)
            manager = member_names.get(member_id or "", roster_id)

            roster_player_ids = [
                player_id
                for player_id in (
                    _player_id(item) for item in (team.get("Players") or [])
                )
                if player_id is not None
            ]
            starter_ids = [
                player_id
                for player_id in (
                    _player_id(item) for item in (team.get("Starters") or [])
                )
                if player_id is not None
            ]
            if len(starter_ids) != len(slots):
                raise AssertionError(
                    f"{target_season} W{week} {manager}: "
                    f"{len(starter_ids)} starters for {len(slots)} slots"
                )

            player_points = {
                _player_id(item.get("Player")): float(item.get("Points") or 0.0)
                for item in (team.get("PlayerPoints") or [])
                if _player_id(item.get("Player")) is not None
            }

            candidates: list[dict[str, Any]] = []
            projection_by_player: dict[str, float] = {}

            for player_id in roster_player_ids:
                source_position = (
                    weekly_positions.get(player_id)
                    or current_positions.get(player_id)
                )
                if source_position is None:
                    previous = season_summaries.get(
                        target_season - 1, {}
                    ).get(player_id)
                    older = season_summaries.get(
                        target_season - 2, {}
                    ).get(player_id)
                    target = target_observations.get(player_id)
                    source_position = (
                        str(previous["Position"])
                        if previous is not None
                        else str(older["Position"])
                        if older is not None
                        else str(target["Position"])
                        if target is not None
                        else None
                    )
                if source_position is None:
                    coverage["unknown_position_entries"] += 1
                    continue

                projection_position = source_position.upper()
                lineup_position = _normalize_lineup_position(projection_position)
                if lineup_position not in {"QB", "RB", "WR", "TE", "K"}:
                    continue

                prior = current_points.get(player_id, [])
                history_ppg, history_games = _history_components(
                    player_id,
                    target_season=target_season,
                    season_summaries=season_summaries,
                    variant=HISTORY_TWO_SEASON,
                    decay=0.25,
                )
                history_backed = history_ppg is not None and history_games > 0

                position_prior = _leave_one_player_out_mean(
                    position=projection_position,
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
                    projection = (
                        current_ppg * weight
                        + float(baseline) * (1.0 - weight)
                    )

                if projection is not None:
                    projection_by_player[player_id] = projection
                else:
                    coverage["no_projection_entries"] += 1

                nfl_team = weekly_teams.get(player_id)
                candidates.append(
                    {
                        "CanonicalPlayerID": player_id,
                        "Position": lineup_position,
                        "Projection": projection,
                        "Actual": player_points.get(player_id, 0.0),
                        "ScheduledThisWeek": (
                            nfl_team is not None
                            and nfl_team in scheduled_teams.get(week, set())
                        ),
                        "ConfirmedParticipation": player_id
                        in target_observations,
                    }
                )

            manager_projection_values = [
                projection_by_player.get(player_id) for player_id in starter_ids
            ]
            manager_projection = (
                sum(
                    float(value)
                    for value in manager_projection_values
                    if value is not None
                )
                if all(value is not None for value in manager_projection_values)
                else None
            )
            manager_actual = float(team.get("Points") or 0.0)

            confirmed_candidates = [
                row for row in candidates if row["ConfirmedParticipation"]
            ]
            oracle_lineup = _select_optimal_lineup(
                confirmed_candidates,
                slots=slots,
                score_key="Projection",
            )

            manager_confirmed = all(
                player_id in target_observations for player_id in starter_ids
            )
            if manager_confirmed:
                coverage["manager_all_starters_participated"] += 1

            comparison = (
                _comparison(
                    manager_projection=manager_projection,
                    manager_actual=manager_actual,
                    manager_starter_ids=starter_ids,
                    model_lineup=oracle_lineup,
                )
                if manager_confirmed
                else None
            )
            if comparison is not None:
                coverage["clean_comparable"] += 1

            rows.append(
                {
                    "Season": target_season,
                    "Week": week,
                    "Manager": manager,
                    "ManagerAllStartersParticipated": manager_confirmed,
                    "Comparison": comparison,
                }
            )

        # Target Week W enters current-season history only after all W decisions
        # have been evaluated.
        for player_id, observation in target_observations.items():
            current_points[player_id].append(float(observation["FantasyPoints"]))
            current_positions[player_id] = str(observation["Position"]).upper()

    by_manager: dict[str, Any] = {}
    for manager in sorted({str(row["Manager"]) for row in rows}):
        manager_rows = [row for row in rows if row["Manager"] == manager]
        by_manager[manager] = {
            "TeamWeeks": len(manager_rows),
            "CleanScoringWeeks": sum(
                1 for row in manager_rows if row["Comparison"] is not None
            ),
            **_aggregate(manager_rows),
        }

    return {
        "Season": target_season,
        "StarterSlots": slots,
        "Coverage": {
            "TeamWeeks": coverage["team_weeks"],
            "ManagerAllStartersParticipatedWeeks": coverage[
                "manager_all_starters_participated"
            ],
            "CleanComparableWeeks": coverage["clean_comparable"],
            "NoProjectionRosterEntries": coverage["no_projection_entries"],
            "UnknownPositionRosterEntries": coverage[
                "unknown_position_entries"
            ],
        },
        "League": _aggregate(rows),
        "ByManager": by_manager,
    }


class ProjectionV3ManagerPersistenceAnalysis(unittest.TestCase):
    def test_manager_alpha_persistence_2024_2025(self) -> None:
        seasons = {
            str(season): _analyze_season(root=ROOT, target_season=season)
            for season in TARGET_SEASONS
        }

        managers_2024 = set(seasons["2024"]["ByManager"])
        managers_2025 = set(seasons["2025"]["ByManager"])
        common_managers = sorted(managers_2024 & managers_2025)

        alpha_2024 = [
            float(
                seasons["2024"]["ByManager"][manager]["ManagerAlphaPerWeek"]
            )
            for manager in common_managers
        ]
        alpha_2025 = [
            float(
                seasons["2025"]["ByManager"][manager]["ManagerAlphaPerWeek"]
            )
            for manager in common_managers
        ]
        realized_2024 = [
            float(
                seasons["2024"]["ByManager"][manager][
                    "RealizedPointsVsModelPerWeek"
                ]
            )
            for manager in common_managers
        ]
        realized_2025 = [
            float(
                seasons["2025"]["ByManager"][manager][
                    "RealizedPointsVsModelPerWeek"
                ]
            )
            for manager in common_managers
        ]
        beat_2024 = [
            float(
                seasons["2024"]["ByManager"][manager]["BeatModelRatePercent"]
            )
            for manager in common_managers
        ]
        beat_2025 = [
            float(
                seasons["2025"]["ByManager"][manager]["BeatModelRatePercent"]
            )
            for manager in common_managers
        ]

        by_manager: dict[str, Any] = {}
        for manager in common_managers:
            s24 = seasons["2024"]["ByManager"][manager]
            s25 = seasons["2025"]["ByManager"][manager]
            realized_sign_consistent = (
                float(s24["RealizedPointsVsModelPerWeek"]) == 0
                or float(s25["RealizedPointsVsModelPerWeek"]) == 0
                or (
                    float(s24["RealizedPointsVsModelPerWeek"]) > 0
                    and float(s25["RealizedPointsVsModelPerWeek"]) > 0
                )
                or (
                    float(s24["RealizedPointsVsModelPerWeek"]) < 0
                    and float(s25["RealizedPointsVsModelPerWeek"]) < 0
                )
            )
            alpha_sign_consistent = (
                float(s24["ManagerAlphaPerWeek"]) == 0
                or float(s25["ManagerAlphaPerWeek"]) == 0
                or (
                    float(s24["ManagerAlphaPerWeek"]) > 0
                    and float(s25["ManagerAlphaPerWeek"]) > 0
                )
                or (
                    float(s24["ManagerAlphaPerWeek"]) < 0
                    and float(s25["ManagerAlphaPerWeek"]) < 0
                )
            )
            by_manager[manager] = {
                "2024": s24,
                "2025": s25,
                "RealizedDirectionConsistent": realized_sign_consistent,
                "AlphaDirectionConsistent": alpha_sign_consistent,
                "TwoSeasonRealizedPointsVsModel": _round(
                    float(s24["RealizedPointsVsModelTotal"])
                    + float(s25["RealizedPointsVsModelTotal"])
                ),
                "TwoSeasonManagerAlpha": _round(
                    float(s24["ManagerAlphaTotal"])
                    + float(s25["ManagerAlphaTotal"])
                ),
            }

        persistence = {
            "CommonManagers": len(common_managers),
            "Managers": common_managers,
            "ManagerAlphaPerWeek": {
                "Pearson2024vs2025": _round(
                    _pearson(alpha_2024, alpha_2025)
                ),
                "Spearman2024vs2025": _round(
                    _spearman(alpha_2024, alpha_2025)
                ),
            },
            "RealizedPointsVsModelPerWeek": {
                "Pearson2024vs2025": _round(
                    _pearson(realized_2024, realized_2025)
                ),
                "Spearman2024vs2025": _round(
                    _spearman(realized_2024, realized_2025)
                ),
            },
            "BeatModelRatePercent": {
                "Pearson2024vs2025": _round(
                    _pearson(beat_2024, beat_2025)
                ),
                "Spearman2024vs2025": _round(
                    _spearman(beat_2024, beat_2025)
                ),
            },
            "RealizedDirectionConsistentManagers": sum(
                1
                for value in by_manager.values()
                if value["RealizedDirectionConsistent"]
            ),
            "AlphaDirectionConsistentManagers": sum(
                1
                for value in by_manager.values()
                if value["AlphaDirectionConsistent"]
            ),
        }

        summary = {
            "Contract": {
                "TargetSeasons": list(TARGET_SEASONS),
                "Comparison": "Participation-controlled V3 scoring choice only",
                "ManagerWeekEligibility": (
                    "all actual manager starters must have confirmed target-week participation"
                ),
                "ModelEligibility": (
                    "V3 may choose only roster players with confirmed target-week participation"
                ),
                "ImportantLimitation": (
                    "Participation is hindsight-only and used strictly to isolate scoring-choice signal; "
                    "this is not a deployable pregame availability model"
                ),
                "V3": {
                    "HistoryVariant": HISTORY_TWO_SEASON,
                    "TMinus1Weight": 1.0,
                    "TMinus2Weight": 0.25,
                    "HistoryK": 0.0,
                    "CurrentK": 1.0,
                    "NoHistoryColdStart": "no numeric projection",
                },
                "LineupRules": {
                    "2024": seasons["2024"]["StarterSlots"],
                    "2025": seasons["2025"]["StarterSlots"],
                },
            },
            "Seasons": seasons,
            "Persistence": persistence,
            "ByManager": by_manager,
        }

        print(
            "V3_MANAGER_PERSISTENCE_2024_2025="
            + json.dumps(summary, sort_keys=True)
        )

        self.assertEqual(6, len(common_managers))
        self.assertEqual(102, seasons["2024"]["Coverage"]["TeamWeeks"])
        self.assertEqual(102, seasons["2025"]["Coverage"]["TeamWeeks"])
        self.assertGreater(seasons["2024"]["Coverage"]["CleanComparableWeeks"], 0)
        self.assertGreater(seasons["2025"]["Coverage"]["CleanComparableWeeks"], 0)


if __name__ == "__main__":
    unittest.main()
