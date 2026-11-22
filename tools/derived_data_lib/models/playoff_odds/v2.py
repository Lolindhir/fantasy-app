"""playoff-odds-v2: strength-based, seeded playoff chances with the points tiebreak (Issue #1607).

Pure model without file/network/clock access. It replaces the 50/50 view of playoff-odds-v1 (immutable) and adds the two facts
v1 ignored: how strong the teams are and that equal records are decided by points (standings-v1 tiebreak).

Strength is never computed here. The caller passes ``strength_by_roster``: the ``RegularSeason.Teams[].Strength.Value`` that the
selected schedule-outlook model computed in the same run (relative to the league average, 1.0 = average). A change of the strength
calculation therefore flows into the odds without any change of this model. Everything else is derived from the league's own scores up
to the cutoff, nothing is a fixed number:

* ``LeagueMeanPoints`` = points per team-game of all scored regular-season games up to the cutoff (before the first game: previous season).
* Expected points of a team = ``LeagueMeanPoints * Strength.Value``.
* ``PointsStdDev`` = pooled standard deviation of the team-game scores around their season means (current season up to the cutoff
  plus the previous regular season); the previous season keeps the spread estimate stable early in a season.
* Every open game draws both team scores from a normal distribution around the expected points with that spread. The winner is the
  higher score; the points also count for the standings tiebreak (win percentage, points for, points against). A fixed seed
  (PARAMS) makes the simulation deterministic. The win probability of a single game is the exact normal result,
  ``Phi(mean difference / (PointsStdDev * sqrt(2)))``, not simulated.
* If the strength is not known for every team, or no score exists yet (not even in the previous season), every team is treated as equally strong and the product says so
  (``StrengthBasis`` = ``equal-unknown`` with a reason); nothing is invented.

Strict status is unchanged from v1 and purely mathematical: ``clinched`` = playoff place in every win/loss outcome even if every
tiebreak is lost, ``eliminated`` = no playoff place in any outcome even if every tiebreak is won. It is computed by the same exact
dynamic program over the wins; if its state count exceeds MAX_STATES the status is null while the probabilities stay available.
After the regular season the official standings-v1 table decides and probabilities are 0 or 1.

Method parameters (seed, simulation count, digits) are versioned PARAMS; changing any of them is ``playoff-odds-v3``.
"""
from __future__ import annotations

import random
from math import isfinite, sqrt
from statistics import NormalDist
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from .v1 import PlayoffOddsError, _count, _unavailable  # noqa: F401  (shared validation and the unavailable shape)

MODEL_ID = "playoff-odds-v2"
KIND = "playoff-odds"
USES_STRENGTH = True
MAX_STATES = 1_500_000
DIGITS = 4
SEED = 1607
SIMULATIONS = 20000
PARAMS = MappingProxyType({
    "Strength": "outlook-model-Strength.Value-relative-to-league-average",
    "LeagueMeanPoints": "points-per-team-game-as-of-cutoff",
    "PointsStdDev": "pooled-sd-around-season-means-current-and-previous-season",
    "ScoreDistribution": "normal-independent-per-team",
    "Method": "seeded-monte-carlo",
    "Seed": SEED,
    "Simulations": SIMULATIONS,
    "TieRule": ("WinPercentage desc", "Points desc", "PointsAgainst asc"),
    "UnknownStrength": "all-teams-equal-marked",
    "StatusMaxStates": MAX_STATES,
    "Digits": DIGITS,
})

_NORMAL = NormalDist()


def _num(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if isfinite(number) else None


def _round(value: float | None) -> float | None:
    return None if value is None else round(value, DIGITS) + 0.0


def win_probability(mean_a: float, mean_b: float, spread: float) -> float:
    """Exact probability that A scores more than B for independent normal scores with equal spread."""
    if spread <= 0:
        return 0.5 if mean_a == mean_b else (1.0 if mean_a > mean_b else 0.0)
    return _NORMAL.cdf((mean_a - mean_b) / (spread * sqrt(2.0)))


def _season_stats(values: Sequence[float]) -> tuple[float, float] | None:
    """(mean, sum of squared deviations from the mean) of one season's team-game scores, None without scores."""
    if not values:
        return None
    mean = sum(values) / len(values)
    return mean, sum((v - mean) ** 2 for v in values)


def scoring_basis(
    rosters: Sequence[str],
    strength_by_roster: Mapping[str, Any],
    points_by_roster: Mapping[str, Sequence[float]],
    previous_points: Sequence[float] = (),
) -> dict[str, Any]:
    """League mean, spread and the expected points per roster, all from the league's own scored team-games.

    * Mean = points per team-game of the current season up to the cutoff; before the first game the previous regular season.
    * Spread = pooled standard deviation of the team-game scores around their own season mean (current season up to the cutoff
      plus the previous regular season, each around its own mean). It is the weekly scoring spread of the league as it is,
      including the differences between teams, so it is never narrower than the real game-to-game noise.
    * ``Basis`` is ``outlook-strength`` when every team has a usable strength and a mean exists, otherwise ``equal-unknown`` with a
      ``Reason`` (all teams then expect the league mean). Nothing is invented: without any score the mean and spread are None.
    """
    current = [float(p) for rid in rosters for p in points_by_roster.get(rid, ())]
    previous = [float(p) for p in previous_points]
    if any(not isfinite(p) for p in current + previous):
        raise PlayoffOddsError("Non-finite observed points")
    cur, prev = _season_stats(current), _season_stats(previous)
    parts = [x for x in (cur, prev) if x is not None]
    if not parts:
        return {"Basis": "equal-unknown", "Reason": "no-scored-games", "Mean": None, "StdDev": None, "MeanSource": None,
                "Observations": 0, "PreviousObservations": 0, "Expected": {rid: None for rid in rosters},
                "Strength": {rid: None for rid in rosters}}
    mean = (cur or prev)[0]
    dof = len(current) + len(previous) - len(parts)
    spread = sqrt(sum(x[1] for x in parts) / dof) if dof > 0 else None
    strengths = {rid: _num(strength_by_roster.get(rid)) for rid in rosters}
    known = all(s is not None and s >= 0 for s in strengths.values())
    if known and mean > 0 and spread is not None:
        basis, reason = "outlook-strength", None
        expected = {rid: mean * strengths[rid] for rid in rosters}
    else:
        basis = "equal-unknown"
        reason = "strength-unknown" if not known else "no-positive-mean" if mean <= 0 else "no-spread"
        expected = {rid: mean for rid in rosters}
        strengths = {rid: None for rid in rosters}
    return {"Basis": basis, "Reason": reason, "Mean": mean, "StdDev": spread,
            "MeanSource": "current-season" if cur else "previous-season",
            "Observations": len(current), "PreviousObservations": len(previous),
            "Expected": expected, "Strength": strengths}


def _strict_status(starts: Sequence[int], pairs: Sequence[tuple[int, int]], cut: int) -> list[str | None]:
    """Exact best/worst place over every win/loss outcome (tiebreaks ignored); None when the state limit is exceeded."""
    n = len(starts)
    states: set[tuple[int, ...]] = {tuple(starts)}
    for a, b in pairs:
        nxt: set[tuple[int, ...]] = set()
        for state in states:
            for winner in (a, b):
                new = list(state)
                new[winner] += 2
                nxt.add(tuple(new))
        states = nxt
        if len(states) > MAX_STATES:
            return [None] * n
    best, worst = [n + 1] * n, [0] * n
    for state in states:
        for i in range(n):
            better = sum(1 for s in state if s > state[i])
            equal = sum(1 for j, s in enumerate(state) if s == state[i] and j != i)
            best[i] = min(best[i], better + 1)
            worst[i] = max(worst[i], better + equal + 1)
    return ["clinched" if worst[i] <= cut else "eliminated" if best[i] > cut else "alive" for i in range(n)]


def compute(
    *,
    teams: Sequence[Mapping[str, Any]],
    open_games: Sequence[tuple[str, str]],
    playoff_teams: Any,
    regular_season_complete: bool,
    strength_by_roster: Mapping[str, Any] | None = None,
    points_by_roster: Mapping[str, Sequence[float]] | None = None,
    previous_points: Sequence[float] = (),
    upcoming_matchups: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return the PlayoffOdds block.

    ``teams``: CanonicalLeagueRosterID, TeamID, Wins, Losses, Ties, Points, PointsAgainst (as of the cutoff).
    ``open_games``: roster ID pairs of every open regular-season game. ``strength_by_roster``: Strength.Value per roster from the
    schedule-outlook model of the same run. ``points_by_roster``: the scored regular-season points per roster up to the cutoff;
    ``previous_points``: every team-game score of the previous regular season (flat; empty without a previous season).
    ``upcoming_matchups``: the outlook's UpcomingMatchups (Week, CanonicalLeagueMatchupID, roster IDs) aligned with ``open_games``;
    used only for the per-game win probabilities.
    """
    n = len(teams)
    if n < 2:
        raise PlayoffOddsError("Expected at least two teams")
    strength_by_roster = strength_by_roster or {}
    points_by_roster = points_by_roster or {}
    rows: list[dict[str, Any]] = []
    index: dict[str, int] = {}
    for team in teams:
        rid = team.get("CanonicalLeagueRosterID")
        if not isinstance(rid, str) or not rid or rid in index or type(team.get("TeamID")) is not int:
            raise PlayoffOddsError("Duplicate or invalid team identity")
        points, against = _num(team.get("Points")), _num(team.get("PointsAgainst"))
        if points is None or against is None:
            raise PlayoffOddsError("Teams need points and points against")
        index[rid] = len(rows)
        rows.append({"TeamID": team["TeamID"], "CanonicalLeagueRosterID": rid,
                     "Wins": _count(team.get("Wins"), "Wins"), "Losses": _count(team.get("Losses"), "Losses"),
                     "Ties": _count(team.get("Ties"), "Ties"), "Points": points, "PointsAgainst": against})
    if len({r["Wins"] + r["Losses"] + r["Ties"] for r in rows}) != 1:
        raise PlayoffOddsError("Teams have played different numbers of games")
    if type(playoff_teams) is not int or playoff_teams < 1:
        return _unavailable("unknown-playoff-teams", rows, len(open_games))
    cut = min(playoff_teams, n)
    rosters = [r["CanonicalLeagueRosterID"] for r in rows]
    basis = scoring_basis(rosters, strength_by_roster, points_by_roster, previous_points)

    def record(row: Mapping[str, Any]) -> dict[str, int]:
        return {"Wins": row["Wins"], "Losses": row["Losses"], "Ties": row["Ties"]}

    scoring = {"LeagueMeanPoints": _round(basis["Mean"]), "PointsStdDev": _round(basis["StdDev"]),
               "MeanSource": basis["MeanSource"],
               "ScoredTeamGames": basis["Observations"], "PreviousSeasonTeamGames": basis["PreviousObservations"]}

    if regular_season_complete:
        if open_games:
            raise PlayoffOddsError("Complete regular season must not have open games")
        order = sorted(range(n), key=lambda i: (-(2 * rows[i]["Wins"] + rows[i]["Ties"]), -rows[i]["Points"], rows[i]["PointsAgainst"]))
        keys = {i: (2 * rows[i]["Wins"] + rows[i]["Ties"], rows[i]["Points"], rows[i]["PointsAgainst"]) for i in range(n)}
        place_of: dict[int, int] = {}
        for pos, i in enumerate(order):
            place_of[i] = 1 if pos == 0 else (place_of[order[pos - 1]] if keys[i] == keys[order[pos - 1]] else pos + 1)
        out = []
        for i, row in enumerate(rows):
            place = place_of[i]
            in_playoffs = place <= cut
            out.append({"TeamID": row["TeamID"], "CanonicalLeagueRosterID": row["CanonicalLeagueRosterID"], "Record": record(row),
                        "PlaceProbabilities": [1.0 if p == place else 0.0 for p in range(1, n + 1)],
                        "PlayoffProbability": 1.0 if in_playoffs else 0.0,
                        "EliminationProbability": 0.0 if in_playoffs else 1.0,
                        "Status": "clinched" if in_playoffs else "eliminated",
                        "ExpectedPoints": None, "Upcoming": []})
        return {"Model": MODEL_ID, "Available": True, "Reason": None,
                "Provenance": _provenance(0, cut, True, basis), "Scoring": scoring, "Teams": out}

    pairs: list[tuple[int, int]] = []
    for a, b in open_games:
        if a not in index or b not in index or a == b:
            raise PlayoffOddsError("Invalid open game pairing")
        pairs.append((index[a], index[b]))
    if upcoming_matchups is not None and len(upcoming_matchups) != len(pairs):
        raise PlayoffOddsError("Upcoming matchups and open games disagree")

    # Seeded simulation. Unit scale (mean 0, spread 1) when no score exists: all teams are then identical, so only the order matters.
    mean = basis["Mean"] if basis["Mean"] is not None else 0.0
    spread = basis["StdDev"] if basis["StdDev"] else 1.0
    expected = [basis["Expected"][rid] if basis["Expected"][rid] is not None else mean for rid in rosters]
    start_wins = [2 * r["Wins"] + r["Ties"] for r in rows]
    start_for = [r["Points"] for r in rows]
    start_against = [r["PointsAgainst"] for r in rows]
    rng = random.Random(SEED)
    gauss = rng.gauss
    place_sums = [[0] * n for _ in range(n)]
    for _ in range(SIMULATIONS):
        wins, pf, pa = list(start_wins), list(start_for), list(start_against)
        for a, b in pairs:
            sa = gauss(expected[a], spread)
            sb = gauss(expected[b], spread)
            pf[a] += sa
            pa[a] += sb
            pf[b] += sb
            pa[b] += sa
            if sa > sb:
                wins[a] += 2
            elif sb > sa:
                wins[b] += 2
            else:
                wins[a] += 1
                wins[b] += 1
        order = sorted(range(n), key=lambda i: (-wins[i], -pf[i], pa[i]))
        for place, i in enumerate(order):
            place_sums[i][place] += 1

    status = _strict_status(start_wins, pairs, cut)
    per_team_upcoming: list[list[dict[str, Any]]] = [[] for _ in range(n)]
    if upcoming_matchups is not None:
        for game, (a, b) in zip(upcoming_matchups, pairs):
            probability = (win_probability(expected[a], expected[b], spread)
                           if basis["Expected"][rosters[a]] is not None else None)
            equal = basis["Basis"] == "equal-unknown"
            for own, other, p in ((a, b, probability), (b, a, None if probability is None else 1.0 - probability)):
                per_team_upcoming[own].append({
                    "Week": game.get("Week"), "CanonicalLeagueMatchupID": game.get("CanonicalLeagueMatchupID"),
                    "OpponentCanonicalLeagueRosterID": rosters[other], "OpponentTeamID": rows[other]["TeamID"],
                    "WinProbability": 0.5 if equal else _round(p) if p is not None else None,
                    "OpponentExpectedPoints": _round(basis["Expected"][rosters[other]]),
                })
    out = []
    for i, row in enumerate(rows):
        probabilities = [round(v / SIMULATIONS, DIGITS) + 0.0 for v in place_sums[i]]
        playoff = sum(place_sums[i][:cut])
        out.append({"TeamID": row["TeamID"], "CanonicalLeagueRosterID": row["CanonicalLeagueRosterID"], "Record": record(row),
                    "PlaceProbabilities": probabilities,
                    "PlayoffProbability": round(playoff / SIMULATIONS, DIGITS) + 0.0,
                    "EliminationProbability": round((SIMULATIONS - playoff) / SIMULATIONS, DIGITS) + 0.0,
                    "Status": status[i],
                    "ExpectedPoints": _round(basis["Expected"][row["CanonicalLeagueRosterID"]]),
                    "Upcoming": per_team_upcoming[i]})
    return {"Model": MODEL_ID, "Available": True, "Reason": None,
            "Provenance": _provenance(len(pairs), cut, False, basis, status_available=status[0] is not None),
            "Scoring": scoring, "Teams": out}


def _provenance(open_games: int, playoff_teams: int, complete: bool, basis: Mapping[str, Any], *, status_available: bool = True) -> dict[str, Any]:
    result: dict[str, Any] = {
        "OpenGames": open_games, "PlayoffTeams": playoff_teams, "RegularSeasonComplete": complete,
        "TieRule": "win-percentage-points-for-points-against",
        "Method": "official-table" if complete else "seeded-monte-carlo-normal-scores",
        "StrengthBasis": basis["Basis"], "StrengthReason": basis["Reason"],
        "StrengthSource": "RegularSeason.Teams[].Strength.Value",
    }
    if not complete:
        result.update({"Seed": SEED, "Simulations": SIMULATIONS, "StatusAvailable": status_available})
    return result
