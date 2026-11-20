"""playoff-odds-v1: exact 50/50 combinatorial playoff chances (Issue #1588).

Pure model without file/network/clock access and without any team strength. Every open
regular-season game is an independent 50/50 win/loss; every outcome combination is counted
exactly (no simulation, no Monte Carlo, no projection). Played results enter only through the
records (wins, losses, ties).

Rules:
  * Final ordering key is the win percentage (wins + 0.5 * ties). Future points are unknown, so
    teams with an equal key share the affected places evenly (every order equally likely).
  * Strict status: ``clinched`` = playoff place in EVERY outcome even if every tiebreak is lost;
    ``eliminated`` = no playoff place in ANY outcome even if every tiebreak is won; else ``alive``.
  * Once the regular season is complete the official table (standings-v1 tiebreak: win percentage,
    points, points against) decides; probabilities are 0 or 1.
  * Counting is a dynamic program over the vector of team scores. If the number of distinct states
    exceeds MAX_STATES the result is explicitly unavailable (never approximated, never 50 percent).

Team count, playoff size and the open games come from the caller (canonical league facts).
"""
from __future__ import annotations

from math import lcm
from types import MappingProxyType
from typing import Any, Mapping, Sequence

MODEL_ID = "playoff-odds-v1"
KIND = "playoff-odds"
MAX_STATES = 1_500_000
DIGITS = 10
PARAMS = MappingProxyType({
    "OpenGameOutcome": "independent-50-50-win-loss",
    "Counting": "exact-dynamic-program",
    "EqualRecordTieRule": "equal-record-teams-share-places",
    "CompleteSeasonTiebreak": ("WinPercentage desc", "Points desc", "PointsAgainst asc"),
    "MaxStates": MAX_STATES,
    "Digits": DIGITS,
})


class PlayoffOddsError(ValueError):
    """Malformed canonical records, pairings or playoff size."""


def _count(value: Any, name: str) -> int:
    if type(value) is not int or value < 0:
        raise PlayoffOddsError(f"Invalid {name}")
    return value


def _unavailable(reason: str, teams: Sequence[Mapping[str, Any]], open_games: int) -> dict[str, Any]:
    return {"Model": MODEL_ID, "Available": False, "Reason": reason,
            "Provenance": {"OpenGames": open_games}, "Teams": [
                {"TeamID": t["TeamID"], "CanonicalLeagueRosterID": t["CanonicalLeagueRosterID"],
                 "Record": {"Wins": t["Wins"], "Losses": t["Losses"], "Ties": t["Ties"]},
                 "PlaceProbabilities": None, "PlayoffProbability": None,
                 "EliminationProbability": None, "Status": None} for t in teams]}


def compute(
    *,
    teams: Sequence[Mapping[str, Any]],
    open_games: Sequence[tuple[str, str]],
    playoff_teams: Any,
    regular_season_complete: bool,
) -> dict[str, Any]:
    """Return the PlayoffOdds block.

    ``teams``: CanonicalLeagueRosterID, TeamID, Wins, Losses, Ties and (needed only when the
    regular season is complete) Points, PointsAgainst. ``open_games``: pairs of roster IDs of every
    still open regular-season game (empty when complete).
    """
    n = len(teams)
    if n < 2:
        raise PlayoffOddsError("Expected at least two teams")
    rows: list[dict[str, Any]] = []
    index: dict[str, int] = {}
    for team in teams:
        rid = team.get("CanonicalLeagueRosterID")
        if not isinstance(rid, str) or not rid or rid in index or type(team.get("TeamID")) is not int:
            raise PlayoffOddsError("Duplicate or invalid team identity")
        index[rid] = len(rows)
        rows.append({"TeamID": team["TeamID"], "CanonicalLeagueRosterID": rid,
                     "Wins": _count(team.get("Wins"), "Wins"), "Losses": _count(team.get("Losses"), "Losses"),
                     "Ties": _count(team.get("Ties"), "Ties")})
    games = len({r["Wins"] + r["Losses"] + r["Ties"] for r in rows})
    if games != 1:
        raise PlayoffOddsError("Teams have played different numbers of games")
    if type(playoff_teams) is not int or playoff_teams < 1:
        return _unavailable("unknown-playoff-teams", rows, len(open_games))
    places_cut = min(playoff_teams, n)

    if regular_season_complete:
        if open_games:
            raise PlayoffOddsError("Complete regular season must not have open games")
        full = []
        for team, row in zip(teams, rows):
            points, against = team.get("Points"), team.get("PointsAgainst")
            if isinstance(points, bool) or isinstance(against, bool) or not isinstance(points, (int, float)) or not isinstance(against, (int, float)):
                raise PlayoffOddsError("Final table needs points and points against")
            full.append((row, -(2 * row["Wins"] + row["Ties"]), -float(points), float(against)))
        order = sorted(range(n), key=lambda i: full[i][1:])
        place_of: dict[int, int] = {}
        for pos, i in enumerate(order):
            place_of[i] = 1 if pos == 0 else (place_of[order[pos - 1]] if full[i][1:] == full[order[pos - 1]][1:] else pos + 1)
        out = []
        for i, row in enumerate(rows):
            place = place_of[i]
            probabilities = [1.0 if p == place else 0.0 for p in range(1, n + 1)]
            in_playoffs = place <= places_cut
            out.append({**row, "Record": {"Wins": row["Wins"], "Losses": row["Losses"], "Ties": row["Ties"]},
                        "PlaceProbabilities": probabilities, "PlayoffProbability": 1.0 if in_playoffs else 0.0,
                        "EliminationProbability": 0.0 if in_playoffs else 1.0,
                        "Status": "clinched" if in_playoffs else "eliminated"})
            for key in ("Wins", "Losses", "Ties"):
                del out[-1][key]
        return {"Model": MODEL_ID, "Available": True, "Reason": None,
                "Provenance": _provenance(0, places_cut, True), "Teams": out}

    pairs = []
    for a, b in open_games:
        if a not in index or b not in index or a == b:
            raise PlayoffOddsError("Invalid open game pairing")
        pairs.append((index[a], index[b]))
    start = tuple(2 * r["Wins"] + r["Ties"] for r in rows)
    states: dict[tuple[int, ...], int] = {start: 1}
    for a, b in pairs:
        nxt: dict[tuple[int, ...], int] = {}
        for state, count in states.items():
            for winner in (a, b):
                new = list(state)
                new[winner] += 2
                key = tuple(new)
                nxt[key] = nxt.get(key, 0) + count
        states = nxt
        if len(states) > MAX_STATES:
            return _unavailable("state-limit-exceeded", rows, len(pairs))

    scale = lcm(*range(1, n + 1))
    total = (2 ** len(pairs)) * scale
    place_sums = [[0] * n for _ in range(n)]
    best = [n + 1] * n
    worst = [0] * n
    for state, count in states.items():
        for i in range(n):
            score = state[i]
            better = sum(1 for s in state if s > score)
            equal = sum(1 for j, s in enumerate(state) if s == score and j != i)
            best[i] = min(best[i], better + 1)
            worst[i] = max(worst[i], better + equal + 1)
            share = count * scale // (equal + 1)
            for place in range(better, better + equal + 1):
                place_sums[i][place] += share
    out = []
    for i, row in enumerate(rows):
        probabilities = [round(v / total, DIGITS) + 0.0 for v in place_sums[i]]
        playoff = sum(place_sums[i][:places_cut])
        status = "clinched" if worst[i] <= places_cut else "eliminated" if best[i] > places_cut else "alive"
        out.append({"TeamID": row["TeamID"], "CanonicalLeagueRosterID": row["CanonicalLeagueRosterID"],
                    "Record": {"Wins": row["Wins"], "Losses": row["Losses"], "Ties": row["Ties"]},
                    "PlaceProbabilities": probabilities,
                    "PlayoffProbability": round(playoff / total, DIGITS) + 0.0,
                    "EliminationProbability": round((total - playoff) / total, DIGITS) + 0.0,
                    "Status": status})
    return {"Model": MODEL_ID, "Available": True, "Reason": None,
            "Provenance": _provenance(len(pairs), places_cut, False), "Teams": out}


def _provenance(open_games: int, playoff_teams: int, complete: bool) -> dict[str, Any]:
    return {"OpenGames": open_games, "OutcomeCount": str(2 ** open_games), "PlayoffTeams": playoff_teams,
            "RegularSeasonComplete": complete, "TieRule": "equal-record-teams-share-places",
            "Method": "exact-enumeration-50-50"}
