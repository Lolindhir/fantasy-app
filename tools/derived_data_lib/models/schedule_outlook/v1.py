"""schedule-outlook-v1: pure regular-season remainder and two independent strength-of-schedule measures.

Issue #1519, checkpoint I1. This model accepts *only* normalized scheduled pairings and
already-cut-off historical team strengths. It has no file/network/clock access and cannot
inspect a future result, starter, roster, or bracket. The caller must establish that its
ratings belong to the requested as-of week and that its pairings are accepted canonical
source facts. Playoff paths and producer integration are deliberately later checkpoints.

A missing opponent rating never silently becomes zero or league average. A team is ranked
only when all its remaining opponents have a usable rating and the corresponding metric
is available for every team in the same snapshot.
"""
from __future__ import annotations

from math import isfinite
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from ...playoff_brackets import round_windows

MODEL_ID = "schedule-outlook-v1"
KIND = "schedule-outlook"
PARAMS = MappingProxyType({
    "Digits": 4,
    "RemainingSoS": "arithmetic-mean-per-opponent-game",
    "Ranking": "competition-ascending-on-complete-coverage",
    "ZeroRemainingGames": "null",
})
DIGITS = 4
METRICS = (
    ("RelativeScoringStrength", "RemainingSoSRelativeStrength", "RemainingSoSRelativeStrengthRank"),
    ("ProjectedBestBallStrength", "RemainingOpponentBestBallStrength", "RemainingOpponentBestBallStrengthRank"),
)


class ScheduleOutlookError(ValueError):
    """Malformed or incomplete canonical schedule/identity evidence."""


def _text(value: Any) -> str:
    return value if isinstance(value, str) and value.strip() == value and value else ""


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if not isfinite(number) or number < 0:
        return None
    return number


def _round(number: float | None) -> float | None:
    return None if number is None else round(number, DIGITS) + 0.0


def compute_regular_season(
    *,
    teams: Sequence[Mapping[str, Any]],
    pairings_by_week: Mapping[int, Sequence[Mapping[str, Any]]],
    strengths_by_roster: Mapping[str, Mapping[str, Any]],
    after_week: int,
    regular_season_last_week: int,
) -> dict[str, Any]:
    """Build a week-cut-off regular-season outlook without reading an existing derived snapshot.

    `teams` must contain CanonicalLeagueRosterID and TeamID; future pairing records
    need only CanonicalLeagueMatchupID, Team1CanonicalLeagueRosterID and
    Team2CanonicalLeagueRosterID. The assembler MUST project raw matchups down to
    these three facts before calling this function. Historical strengths are
    looked up by canonical roster ID and must be prefiltered to `min(after_week,
    regular_season_last_week)` (none at Week 0).
    """
    if type(after_week) is not int or type(regular_season_last_week) is not int or after_week < 0 or regular_season_last_week < 1:
        raise ScheduleOutlookError("Invalid Week cutoff or regular-season end")
    team_map: dict[str, Any] = {}
    team_ids: set[Any] = set()
    for team in teams:
        rid, tid = team.get("CanonicalLeagueRosterID"), team.get("TeamID")
        if not _text(rid) or type(tid) is not int or tid <= 0 or tid in team_ids or rid in team_map:
            raise ScheduleOutlookError("Duplicate or invalid canonical team identity")
        team_map[rid] = tid
        team_ids.add(tid)
    if len(team_map) < 2:
        raise ScheduleOutlookError("Expected at least two distinct fantasy teams")
    if after_week == 0 and strengths_by_roster:
        raise ScheduleOutlookError("Week 0 must not contain historical scored team ratings")
    if set(strengths_by_roster) - set(team_map):
        raise ScheduleOutlookError("Ratings contain an unknown canonical roster identity")

    upcoming: list[dict[str, Any]] = []
    by_team: dict[str, list[dict[str, Any]]] = {rid: [] for rid in team_map}
    for week in range(max(1, after_week + 1), regular_season_last_week + 1):
        raw_week = pairings_by_week.get(week)
        if raw_week is None:
            raise ScheduleOutlookError(f"Missing canonical pairing source for regular-season Week {week}")
        seen_teams: set[str] = set()
        seen_matchups: set[str] = set()
        pairs: list[tuple[str, str, str]] = []
        for row in raw_week:
            matchup, a, b = (row.get("CanonicalLeagueMatchupID"),
                             row.get("Team1CanonicalLeagueRosterID"), row.get("Team2CanonicalLeagueRosterID"))
            if not all(_text(x) for x in (matchup, a, b)) or a == b or a not in team_map or b not in team_map:
                raise ScheduleOutlookError(f"Invalid regular-season pairing in Week {week}")
            if matchup in seen_matchups or a in seen_teams or b in seen_teams:
                raise ScheduleOutlookError(f"Duplicate matchup or participant in Week {week}")
            seen_matchups.add(matchup)
            seen_teams.update((a, b))
            pairs.append((matchup, min(a, b), max(a, b)))
        if seen_teams != set(team_map):
            raise ScheduleOutlookError(f"Incomplete Week {week}: missing canonical matchup participants")
        for matchup, a, b in sorted(pairs, key=lambda x: (x[1], x[2], x[0])):
            upcoming.append({"Week": week, "CanonicalLeagueMatchupID": matchup,
                             "Team1CanonicalLeagueRosterID": a, "Team2CanonicalLeagueRosterID": b})
            for own, opponent in ((a, b), (b, a)):
                rating = strengths_by_roster.get(opponent) or {}
                game = {"Week": week, "CanonicalLeagueMatchupID": matchup,
                        "OpponentCanonicalLeagueRosterID": opponent, "OpponentTeamID": team_map[opponent]}
                for source_key, _, _ in METRICS:
                    game["Opponent" + source_key] = _round(_number(rating.get(source_key)))
                by_team[own].append(game)

    result_teams: list[dict[str, Any]] = []
    for rid, team_id in sorted(team_map.items(), key=lambda x: x[1]):
        games = by_team[rid]
        record: dict[str, Any] = {
            "TeamID": team_id, "CanonicalLeagueRosterID": rid, "RemainingGames": len(games),
            "Upcoming": games,
        }
        for source_key, output_key, rank_key in METRICS:
            values = [g["Opponent" + source_key] for g in games]
            record["Known" + source_key + "Games"] = sum(v is not None for v in values)
            record[output_key] = (_round(sum(values) / len(values)) if values and all(v is not None for v in values) else None)
            record[rank_key] = None
        result_teams.append(record)

    for _, score_key, rank_key in METRICS:
        values = [x[score_key] for x in result_teams]
        if all(v is not None for v in values):
            for item in result_teams:
                item[rank_key] = 1 + sum(v < item[score_key] for v in values)

    return {"AfterWeek": after_week, "RatingWeek": None if after_week == 0 else min(after_week, regular_season_last_week),
            "UpcomingMatchups": upcoming, "Teams": result_teams}


def compute_playoff_paths(
    *,
    structure: Mapping[str, Any],
    winners_bracket: Sequence[Mapping[str, Any]],
    losers_bracket: Sequence[Mapping[str, Any]],
    canonical_roster_ids: set[str],
    after_week: int,
    regular_season_last_week: int,
) -> dict[str, Any]:
    """Reconstruct *known by cutoff* playoff paths from canonical bracket routing.

    A bracket's archived winner and resolved late-round participants represent
    hindsight unless their round has already ended. Thus this function uses
    Winner/Loser facts ONLY for rounds with all legs scored by `after_week`,
    and uses Team1/2Source for later participants, ignoring any hindsight-resolved
    Team1/2CanonicalLeagueRosterID on those routed slots.

    Round finality is provided by the caller's already validated LeagueScoredWeek
    cutoff; never call this without the league week-finality gate. All fixture
    and format facts are canonical and may be retrospectively reconstructed.
    """
    if (type(after_week) is not int or after_week < 0 or
            type(regular_season_last_week) is not int or regular_season_last_week < 1):
        raise ScheduleOutlookError("Invalid playoff as-of cutoff")
    if not isinstance(structure, Mapping):
        raise ScheduleOutlookError("Missing playoff format")
    windows = round_windows(structure)
    if windows is None:
        raise ScheduleOutlookError("Unknown or conflicting playoff round format")
    start = structure.get("PlayoffStartWeek")
    if type(start) is not int or start - 1 != regular_season_last_week:
        raise ScheduleOutlookError("Regular-season boundary differs from playoff start")
    if not isinstance(winners_bracket, (list, tuple)) or not isinstance(losers_bracket, (list, tuple)):
        raise ScheduleOutlookError("Playoff brackets must be arrays")
    if not canonical_roster_ids or not all(_text(r) for r in canonical_roster_ids):
        raise ScheduleOutlookError("Missing canonical roster identities")

    all_games: list[dict[str, Any]] = []
    for bracket, source_rows in (("winners", winners_bracket), ("losers", losers_bracket)):
        seen_match: set[int] = set()
        for row in source_rows:
            if not isinstance(row, Mapping):
                raise ScheduleOutlookError("Invalid canonical playoff bracket row")
            match, round_no = row.get("Match"), row.get("Round")
            if (type(match) is not int or match < 1 or match in seen_match
                    or type(round_no) is not int or round_no < 1 or round_no > len(windows)):
                raise ScheduleOutlookError(f"Invalid or duplicate {bracket} bracket match/round")
            seen_match.add(match)
            all_games.append({"Bracket": bracket, "Match": match, "Round": round_no, "Input": row})

    # Source routing may refer only to a match of an earlier round within the same bracket.
    games_by_key = {(g["Bracket"], g["Match"]): g for g in all_games}
    for g in all_games:
        row = g["Input"]
        for source_key in ("Team1Source", "Team2Source"):
            value = row.get(source_key)
            if value is None:
                continue
            if not isinstance(value, Mapping) or set(value) != {"Match", "Outcome"}:
                raise ScheduleOutlookError("Invalid bracket advancement source")
            ref, outcome = value["Match"], value["Outcome"]
            parent = games_by_key.get((g["Bracket"], ref)) if type(ref) is int else None
            if outcome not in ("Winner", "Loser") or parent is None or parent["Round"] >= g["Round"]:
                raise ScheduleOutlookError("Invalid, missing or forward playoff advancement path")

    resolved_results: dict[tuple[str, int], dict[str, str | None]] = {}
    paths: list[dict[str, Any]] = []
    for g in sorted(all_games, key=lambda x: (x["Round"], x["Bracket"], x["Match"])):
        row, round_no, match, bracket = g["Input"], g["Round"], g["Match"], g["Bracket"]
        window = windows[round_no - 1]
        state = ("not-started" if after_week < window[0] else
                 "in-progress" if after_week < window[-1] else "final")
        participants: list[dict[str, Any]] = []
        for slot in (1, 2):
            source = row.get(f"Team{slot}Source")
            direct = row.get(f"Team{slot}CanonicalLeagueRosterID")
            if source is not None:
                parent = resolved_results.get((bracket, source["Match"]))
                rid = parent.get(source["Outcome"]) if parent is not None else None
                certainty = "confirmed" if rid is not None else "conditional"
            elif after_week < regular_season_last_week:
                # An archived final bracket's seed is NOT evidence of the seed
                # already being known during regular-season Week N.
                rid, certainty = None, "unknown"
            elif direct is None:
                rid, certainty = None, "unknown"
            elif _text(direct) and direct in canonical_roster_ids:
                rid, certainty = direct, "confirmed"
            else:
                raise ScheduleOutlookError("Unknown canonical direct playoff participant")
            participants.append({
                "CanonicalLeagueRosterID": rid,
                "Certainty": certainty,
                "Source": None if source is None else {"Match": source["Match"], "Outcome": source["Outcome"]},
                "DirectSeed": bool(source is None and round_no > 1 and rid is not None),
            })
        ids = [p["CanonicalLeagueRosterID"] for p in participants]
        if ids[0] is not None and ids[0] == ids[1]:
            raise ScheduleOutlookError("Playoff matchup contains the same canonical roster twice")
        winner = loser = None
        if state == "final":
            raw_winner, raw_loser = row.get("WinnerCanonicalLeagueRosterID"), row.get("LoserCanonicalLeagueRosterID")
            # Final brackets have learned the result. A scored *completed*
            # round may use it; an incomplete two-leg round may never use it.
            for name, value in (("Winner", raw_winner), ("Loser", raw_loser)):
                if value is not None and (not _text(value) or value not in canonical_roster_ids
                                          or value not in ids):
                    raise ScheduleOutlookError(f"Invalid confirmed {name} for playoff match {match}")
            if raw_winner is not None and raw_loser is not None and raw_winner == raw_loser:
                raise ScheduleOutlookError("Playoff winner equals loser")
            if raw_winner is not None and all(x is not None for x in ids):
                winner = raw_winner
                loser = raw_loser
        resolved_results[(bracket, match)] = {"Winner": winner, "Loser": loser}
        placement = row.get("Placement")
        if placement is not None and (type(placement) is not int or placement < 1):
            raise ScheduleOutlookError("Invalid canonical playoff placement")
        label = ("consolation" if bracket == "losers" else
                 "placement" if placement is not None and placement > 1 else "championship")
        path = {
            "Bracket": bracket, "Match": match, "Round": round_no,
            "RoundWeeks": list(window), "RoundState": state,
            "Category": label, "Placement": placement,
            "Participants": participants,
            "ParticipantCertainty": ("confirmed" if all(p["Certainty"] == "confirmed" for p in participants) else
                                     "conditional" if any(p["Certainty"] == "conditional" for p in participants) else
                                     "unknown"),
            "WinnerCanonicalLeagueRosterID": winner,
            "LoserCanonicalLeagueRosterID": loser,
        }
        paths.append(path)
    observed = structure.get("ObservedPlayoffFormat")
    projected = structure.get("ProjectedPlayoffFormat")
    return {
        "Format": {
            "PlayoffStartWeek": start,
            "PlayoffTeams": structure.get("PlayoffTeams"),
            "PlayoffRoundType": structure.get("PlayoffRoundType"),
            "RoundWeeks": [list(w) for w in windows],
            "ObservedPlayoffFormat": observed,
            "ProjectedPlayoffFormat": projected,
            "FormatEvidence": "observed" if observed is not None else
                              "projected" if projected is not None else "unknown",
        },
        "Paths": paths,
    }
