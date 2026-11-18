"""weekly-recap-v2: the four weekly league-context player awards (Issue #499).

Adds ``PlayerAwards`` to every recap week; everything else of the recap stays as in ``weekly-recap-v1``. The awards are characterful awards
for this league, not NFL leaderboards. All points are the league-scored points of the canonical league matchups (raw, no rounding rule beyond
4 decimals); a *starter* is a player of the submitted lineup, a *bench* player is every other rostered player of that week.

* **MVP** - the starter(s) with the most points of the week, league-wide.
* **Matchup Hero** - for each starter of a winning team the swing is his points minus the points of the best bench player of the same
  position (0 when the team has none). A starter is *decisive* when his swing is larger than the matchup margin (his team would have lost
  without him). The Hero is the decisive starter(s) with the largest swing; no decisive starter means no Hero.
* **Heartbreaker** - the starter(s) with the most points in a lost matchup. A tied matchup has no loser.
* **Unsung Hero** - a bench player of a losing team whose swap for one starter, on a slot he is eligible for (FLEX and SUPER_FLEX included, the
  full lineup must stay legal), or his addition to an empty slot, would have flipped the matchup (strictly more points than the winner). His gain
  is the points he would have added; the winner is the player(s) with the largest gain, and the swap with the largest gain is reported.

Ties share every award. Overlap is allowed (Hero only in a win, Heartbreaker only in a loss, an Unsung Hero is never a starter), so a player
holds at most two awards in a week. Missing evidence (a starter or bench player without points or position, a team count other than two per
matchup) raises ``ValueError``; the caller then leaves the week without awards, nothing is guessed.

A model is a pure function of its explicit inputs: it reads no file, no clock and no league configuration. Immutable after its first
productive use; any change is ``weekly-recap-v3``.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Decimal
from types import MappingProxyType
from typing import Any

from weekly_lineup_optimizer import ScoredPlayer, StartingSlot, maximize_lineup

MODEL_ID = "weekly-recap-v2"
KIND = "weekly-recap"

PLAYER_AWARDS = True
AWARD_KEYS = ("MVP", "MatchupHero", "Heartbreaker", "UnsungHero")

PARAMS = MappingProxyType({
    "PlayerAwards": PLAYER_AWARDS,
    "Awards": AWARD_KEYS,
    "Ties": "shared",
    "HeroReplacement": "best-bench-same-position-else-zero",
    "UnsungHeroEligibility": "slot-eligible-full-lineup-legal",
    "PointsDigits": 4,
})


def _points(value: Any, label: str) -> Decimal:
    if value is None or isinstance(value, bool):
        raise ValueError(f"missing points for {label}")
    return Decimal(str(round(float(value), 4)))


def _num(value: Decimal) -> int | float:
    return int(value) if value == value.to_integral_value() else float(value)


def _entry(player: Mapping[str, Any], team_id: Any, matchup_id: str, **figures: Any) -> dict[str, Any]:
    return {
        "PlayerID": player["PlayerID"],
        "CanonicalPlayerID": player.get("CanonicalPlayerID"),
        "FantasyTeamID": team_id,
        "FantasyMatchupID": matchup_id,
        "Position": player["Position"],
        **{key: (_num(value) if isinstance(value, Decimal) else value) for key, value in figures.items()},
    }


def _sort_key(entry: Mapping[str, Any]) -> tuple[str, str]:
    return (str(entry["FantasyTeamID"]).zfill(8), str(entry["PlayerID"]))


def _top(candidates: list[tuple[Decimal, dict[str, Any]]]) -> list[dict[str, Any]]:
    """All entries sharing the largest rank value, in a stable order."""
    if not candidates:
        return []
    best = max(value for value, _ in candidates)
    return sorted((entry for value, entry in candidates if value == best), key=_sort_key)


def _legal(slots: Sequence[StartingSlot], lineup: Sequence[Mapping[str, Any]]) -> bool:
    """Whether the players can fill distinct slots they are eligible for (a one-to-one assignment of every player)."""
    if len(lineup) > len(slots):
        return False
    scored = [ScoredPlayer(player["PlayerID"], player["Position"], Decimal(1)) for player in lineup]
    return len(maximize_lineup(slots, scored).assignments) == len(lineup)


def player_awards(matchups: Sequence[Mapping[str, Any]], slots: Sequence[StartingSlot]) -> dict[str, Any]:
    """The four player awards of one week.

    ``matchups``: per paired matchup ``{"FantasyMatchupID", "Teams": [{"FantasyTeamID", "Score", "Players": [{"PlayerID", "CanonicalPlayerID",
    "Position", "Points", "IsStarter"}]}]}`` with exactly two teams; ``slots``: the starting slots with their eligible positions.
    """
    mvp: list[tuple[Decimal, dict[str, Any]]] = []
    hero: list[tuple[Decimal, dict[str, Any]]] = []
    heartbreaker: list[tuple[Decimal, dict[str, Any]]] = []
    unsung: list[tuple[Decimal, dict[str, Any]]] = []
    for matchup in matchups:
        teams = list(matchup["Teams"])
        if len(teams) != 2:
            raise ValueError(f"matchup {matchup['FantasyMatchupID']} does not have two teams")
        matchup_id = str(matchup["FantasyMatchupID"])
        scores = [_points(team["Score"], f"team {team['FantasyTeamID']} score") for team in teams]
        prepared: list[tuple[list[dict[str, Any]], list[dict[str, Any]]]] = []
        for team in teams:
            starters: list[dict[str, Any]] = []
            bench: list[dict[str, Any]] = []
            for player in team["Players"]:
                if not player.get("Position"):
                    raise ValueError(f"missing position for player {player['PlayerID']}")
                item = {**player, "Points": _points(player.get("Points"), f"player {player['PlayerID']}")}
                (starters if player["IsStarter"] else bench).append(item)
            if not starters:
                raise ValueError(f"team {team['FantasyTeamID']} has no starter")
            prepared.append((starters, bench))
            for starter in starters:
                mvp.append((starter["Points"], _entry(starter, team["FantasyTeamID"], matchup_id, Points=starter["Points"])))
        if scores[0] == scores[1]:
            continue
        winner = 0 if scores[0] > scores[1] else 1
        margin = abs(scores[0] - scores[1])
        win_starters, win_bench = prepared[winner]
        for starter in win_starters:
            same_position = [bench["Points"] for bench in win_bench if bench["Position"] == starter["Position"]]
            swing = starter["Points"] - max(same_position, default=Decimal(0))
            if swing > margin:
                hero.append((swing, _entry(starter, teams[winner]["FantasyTeamID"], matchup_id, Points=starter["Points"], Swing=swing, Margin=margin)))
        loser = 1 - winner
        lose_starters, lose_bench = prepared[loser]
        loser_id = teams[loser]["FantasyTeamID"]
        for starter in lose_starters:
            heartbreaker.append((starter["Points"], _entry(starter, loser_id, matchup_id, Points=starter["Points"], Margin=margin)))
        for sub in lose_bench:
            best: tuple[Decimal, str, dict[str, Any] | None] | None = None
            replaced_options: list[dict[str, Any] | None] = [*lose_starters, None]
            for replaced in replaced_options:
                gain = sub["Points"] - (replaced["Points"] if replaced is not None else Decimal(0))
                if gain <= margin:
                    continue
                if best is not None and gain < best[0]:
                    continue
                lineup = [player for player in lose_starters if player is not replaced] + [sub]
                if not _legal(slots, lineup):
                    continue
                # An equal gain prefers a real swap over an addition to an empty slot, then the lower player ID.
                key = ("0" if replaced is not None else "1") + (replaced["PlayerID"] if replaced is not None else "")
                if best is None or gain > best[0] or (gain == best[0] and key < best[1]):
                    best = (gain, key, replaced)
            if best is not None:
                gain, _, replaced = best
                unsung.append((gain, _entry(sub, loser_id, matchup_id, Points=sub["Points"], Gain=gain, Margin=margin,
                                            ReplacedPlayerID=replaced["PlayerID"] if replaced is not None else None)))
    return {
        "State": "available",
        "MVP": _top(mvp),
        "MatchupHero": _top(hero),
        "Heartbreaker": _top(heartbreaker),
        "UnsungHero": _top(unsung),
    }


def unavailable() -> dict[str, Any]:
    """The marker of a week whose evidence is incomplete: no award, never a guess."""
    return {"State": "unavailable", "MVP": [], "MatchupHero": [], "Heartbreaker": [], "UnsungHero": []}
