"""Versioned adapter for exact neutral record-based playoff models (Issue #1693).

The integer mass is authoritative; JSON float probabilities are convenience
approximations. Before regular-season completion, points are not an input.
"""
from __future__ import annotations

from math import isfinite
from typing import Any, Mapping, Sequence

from .exact_v1 import EnumerationLimit, enumerate_places
from .v1 import PlayoffOddsError, _count


def compute_record_odds(
    *,
    model_id: str,
    params: Mapping[str, Any],
    teams: Sequence[Mapping[str, Any]],
    open_games: Sequence[tuple[str, str]],
    playoff_teams: Any,
    regular_season_complete: bool,
) -> dict[str, Any]:
    n = len(teams)
    if n < 2:
        raise PlayoffOddsError("Expected at least two teams")
    rows = []
    index: dict[str, int] = {}
    team_ids: set[int] = set()
    for team in teams:
        rid, tid = team.get("CanonicalLeagueRosterID"), team.get("TeamID")
        if not isinstance(rid, str) or not rid or rid in index or type(tid) is not int or tid in team_ids:
            raise PlayoffOddsError("Duplicate or invalid team identity")
        index[rid] = len(rows)
        team_ids.add(tid)
        rows.append({"TeamID": tid, "CanonicalLeagueRosterID": rid,
                     "Record": {key: _count(team.get(key), key) for key in ("Wins", "Losses", "Ties")}})
    played_counts = {sum(row["Record"].values()) for row in rows}
    if len(played_counts) != 1:
        raise PlayoffOddsError("Teams have played different numbers of games")
    played = played_counts.pop()
    pairs = []
    remaining = [0] * n
    for a, b in open_games:
        if a not in index or b not in index or a == b:
            raise PlayoffOddsError("Invalid open game pairing")
        pairs.append((index[a], index[b]))
        remaining[index[a]] += 1
        remaining[index[b]] += 1
    if regular_season_complete and pairs:
        raise PlayoffOddsError("Complete regular season must not have open games")

    weights = params["OutcomeWeights"]
    cut = min(playoff_teams, n) if type(playoff_teams) is int and playoff_teams > 0 else None
    provenance = {"OpenGames": len(pairs), "PlayoffTeams": cut,
                  "RegularSeasonComplete": regular_season_complete,
                  "OutcomeWeights": {"Loss": weights[0], "Tie": weights[1], "Win": weights[2]},
                  "OutcomeWeightDenominator": sum(weights),
                  "TieRule": "equal-record-teams-share-places",
                  "Method": "exact-enumeration-wtl-record"}

    def unavailable(reason: str) -> dict[str, Any]:
        return {"Model": model_id, "Available": False, "Reason": reason, "Provenance": provenance,
                "Teams": [{**row, "PlaceProbabilities": None, "PlaceMassNumerators": None,
                           "PossiblePlaces": None, "PlayoffProbability": None,
                           "EliminationProbability": None, "Status": None} for row in rows]}

    if cut is None:
        return unavailable("unknown-playoff-teams")

    if regular_season_complete:
        # Reuse the canonical standings implementation, including competition ranks.
        from ..standings.v1 import rank_teams
        if not played:
            return unavailable("no-scored-games")
        for team in teams:
            for key in ("Points", "PointsAgainst"):
                value = team.get(key)
                if type(value) not in (int, float) or not isfinite(value):
                    raise PlayoffOddsError("Final table needs finite points and points against")
        places = {team["CanonicalLeagueRosterID"]: team["PlaceRegular"] for team in rank_teams(teams)}
        provenance.update({"Method": "official-table", "TieRule": "standings-v1"})
        # A shared official rank crossing the cut does not determine the bracket field.
        if sum(place <= cut for place in places.values()) != cut:
            return unavailable("ambiguous-final-playoff-boundary")
        denominator = 1
        numerators = [tuple(int(p == places[row["CanonicalLeagueRosterID"]]) for p in range(1, n + 1))
                      for row in rows]
    else:
        if len(set(remaining)) != 1:
            return unavailable("unequal-final-game-count")
        total_games = played + remaining[0]
        provenance["PlayedGamesPerTeam"] = played
        provenance["RegularSeasonGamesPerTeam"] = total_games
        minimum_num, minimum_den = params["MinPlayedFraction"]
        if total_games == 0 or played * minimum_den < total_games * minimum_num:
            return unavailable("season-progress-too-low")
        starts = [2 * row["Record"]["Wins"] + row["Record"]["Ties"] for row in rows]
        try:
            exact = enumerate_places(starts, pairs, weights, max_states=params["MaxStates"],
                                     max_transitions=params["MaxTransitions"])
        except EnumerationLimit as error:
            return unavailable(str(error))
        denominator, numerators = exact.denominator, exact.numerators
        provenance.update({"StateCount": exact.state_count, "Transitions": exact.transitions})

    provenance.update({"OutcomeCount": str(3 ** len(pairs)), "PlaceMassDenominator": str(denominator)})
    out = []
    for row, masses in zip(rows, numerators):
        playoff = sum(masses[:cut])
        elimination = denominator - playoff
        out.append({**row, "PlaceProbabilities": [mass / denominator for mass in masses],
                    "PlaceMassNumerators": [str(mass) for mass in masses],
                    "PossiblePlaces": [p for p, mass in enumerate(masses, 1) if mass],
                    "PlayoffProbability": playoff / denominator, "EliminationProbability": elimination / denominator,
                    "Status": "clinched" if elimination == 0 else "eliminated" if playoff == 0 else "alive"})
    return {"Model": model_id, "Available": True, "Reason": None, "Provenance": provenance, "Teams": out}
