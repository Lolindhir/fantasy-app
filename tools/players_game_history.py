#!/usr/bin/env python3
"""Players.json GameHistory from canonical NFL facts (#347 G3).

Replaces the Tank01 Games.json boxscore as the source of ``GameHistory`` in RequestPlayers.ps1.
It is a library used by ``players_league_scoring.build_export`` (one identity resolution, one hold
decision per player); the entries travel in the league-scoring export under ``Players[id].GameHistory``.

Entry rule: a player has an entry for a game when canonical ``player-stats`` holds a row or
``snap-counts`` holds a row for that player and game (nflverse omits all-zero stat lines, so a
snap-only game is a real game with 0 points, also when all snaps are special-teams snaps).

Sources and rules (design: 347-analyse/2026-10-06-g1-schedule-gamehistory-design.md, section 3):
  game data      schedules/<season>.json (teams, date, scores) + game-finality/<season>.json (WeekFinal)
  points         league ScoringSettings through the shared scorer (all weeks, final or not)
  snaps          non-kickers OffenseSnaps/OffensePct, kickers fg_att + pat_att and 1
  QBRating       ESPN QBRTotal from qbr-week, null without a rating row
  LongRush/Rec   maximum of player-game-long-gains; covered game without a row -> 0, game not yet
                 covered by the dataset -> null (unknown, never zero)
  *Avg, Rating   exact fractions rounded half up to one decimal; denominator 0 -> 0
  team keys      canonical abbreviation (ADR-042); GameID keeps the legacy provider spelling (LAR, WSH)

Block presence (Passing, Rushing, Receiving, Kicking) follows the counting stats of the block.
All values are deterministic functions of the canonical facts; nothing is persisted.
"""
from __future__ import annotations

import sys
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from historical_fantasy_scoring import number, read_json  # noqa: E402
from nfl_source_data_lib.teams import NflTeamRegistry  # noqa: E402

TEAM_SPELLING_KIND = "provider-spelling"
POSTSEASON_TYPES = ("WC", "DIV", "CON", "SB")
GAME_HISTORY_SEASON_TYPES = ("REG",) + POSTSEASON_TYPES


class GameHistoryError(ValueError):
    """Canonical input for GameHistory is missing or inconsistent (fail closed)."""


def half_up(numerator: int | float, denominator: int | float, digits: int = 1) -> float:
    """numerator/denominator rounded half up on the exact fraction; denominator 0 -> 0.0."""
    if not denominator:
        return 0.0
    exact = Fraction(numerator) / Fraction(denominator)
    return _quantize(exact, digits)


def _quantize(value: Fraction, digits: int) -> float:
    quantum = Decimal(1).scaleb(-digits)
    exact = Decimal(value.numerator) / Decimal(value.denominator)
    return float(exact.quantize(quantum, rounding=ROUND_HALF_UP))


def passer_rating(completions: int, attempts: int, yards: int, touchdowns: int, interceptions: int) -> float:
    """NFL passer rating, four terms capped to [0, 2.375], one decimal half up; no attempts -> 0."""
    if attempts <= 0:
        return 0.0

    def cap(term: Fraction) -> Fraction:
        return max(Fraction(0), min(Fraction(19, 8), term))

    a = Fraction(attempts)
    total = (
        cap((Fraction(completions) / a - Fraction(3, 10)) * 5)
        + cap((Fraction(yards) / a - 3) * Fraction(1, 4))
        + cap(Fraction(touchdowns) / a * 20)
        + cap(Fraction(19, 8) - Fraction(interceptions) / a * 25)
    )
    return _quantize(total / 6 * 100, 1)


class TeamKeys:
    """Canonical team keys plus the legacy provider spelling used inside GameID."""

    def __init__(self, repo_root: Path) -> None:
        self.registry = NflTeamRegistry.load(repo_root)
        self._legacy_spelling = {
            abbr: next((a["Alias"] for a in team.get("Aliases", []) if a.get("Kind") == TEAM_SPELLING_KIND), abbr)
            for abbr, team in self.registry.teams.items()
        }

    def canonical(self, value: str, season: int) -> str:
        return self.registry.resolve(value, season)

    def spelling(self, canonical: str) -> str:
        return self._legacy_spelling[canonical]


def _index_games(repo_root: Path, season: int) -> dict[str, dict[str, Any]]:
    schedule = read_json(repo_root / "source-data/nfl/schedules" / f"{season}.json")
    if int(schedule.get("Season", -1)) != season:
        raise GameHistoryError(f"Canonical schedule season mismatch for {season}")
    games = {str(game["GameID"]): game for game in schedule.get("Games") or []}
    if not games:
        raise GameHistoryError(f"Canonical schedule {season} has no games")
    return games


def _week_final(repo_root: Path, season: int) -> dict[tuple[str, int], bool]:
    payload = read_json(repo_root / "source-data/nfl/game-finality" / f"{season}.json")
    return {(str(w["GameType"]), int(w["Week"])): bool(w.get("WeekFinal")) for w in payload.get("Weeks") or []}


def _partition_records(repo_root: Path, dataset: str, season: int) -> list[tuple[int, list[dict[str, Any]]]]:
    directory = repo_root / "source-data/nfl" / dataset / str(season)
    if not directory.is_dir():
        raise GameHistoryError(f"Canonical partition directory missing: {directory}")
    out = []
    for path in sorted(directory.glob("*.json")):
        payload = read_json(path)
        out.append((int(payload["Week"]), payload.get("Records") or []))
    return out


def _qbr_index(repo_root: Path, season: int) -> dict[tuple[str, str], float | None]:
    path = repo_root / "source-data/nfl/qbr-week" / f"{season}.json"
    if not path.exists():
        return {}
    payload = read_json(path)
    index: dict[tuple[str, str], float | None] = {}
    for record in payload.get("Records") or []:
        value = record.get("QBRTotal")
        index[(record["CanonicalPlayerID"], record["GameID"])] = None if value is None else float(value)
    return index


def _long_gain_index(
    repo_root: Path, season: int
) -> tuple[dict[tuple[str, str, str], int], set[str]]:
    path = repo_root / "source-data/nfl/player-game-long-gains" / f"{season}.json"
    if not path.exists():
        return {}, set()
    payload = read_json(path)
    covered = {str(game["GameID"]) for game in payload.get("Games") or []}
    longest: dict[tuple[str, str, str], int] = {}
    for record in payload.get("Records") or []:
        key = (record["CanonicalPlayerID"], record["GameID"], record["GainType"])
        yards = int(record["Yards"])
        longest[key] = yards if key not in longest else max(longest[key], yards)
    return longest, covered


def _has_passing(s: dict[str, Any]) -> bool:
    return any(number(s.get(k)) != 0 for k in ("attempts", "completions", "passing_yards", "passing_tds", "passing_interceptions"))


def _has_rushing(s: dict[str, Any]) -> bool:
    return any(number(s.get(k)) != 0 for k in ("carries", "rushing_yards", "rushing_tds"))


def _has_receiving(s: dict[str, Any]) -> bool:
    return any(number(s.get(k)) != 0 for k in ("targets", "receptions", "receiving_yards", "receiving_tds"))


def _has_kicking(s: dict[str, Any]) -> bool:
    return any(number(s.get(k)) != 0 for k in ("fg_att", "fg_made", "fg_missed", "pat_att", "pat_made", "pat_missed"))


def build_game_histories(
    repo_root: Path,
    season: int,
    cids: set[str],
    weekly_points: dict[str, dict[int, dict[str, float]]],
    points_unavailable: dict[str, list[tuple[int, int]]] | None = None,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, int]]:
    """GameHistory entries per CanonicalPlayerID, newest game first (legacy GameID descending).

    ``weekly_points`` is the league-scored weekly output for the current season
    (``build_weekly_scores(...)[0][season]``); a game without points because its stat line could
    not be scored (``points_unavailable``: cid -> [(season, week)]) gets no entry rather than a
    wrong zero. Returns (entries, counters).
    """
    keys = TeamKeys(repo_root)
    games = _index_games(repo_root, season)
    week_final = _week_final(repo_root, season)
    qbr = _qbr_index(repo_root, season)
    long_gains, long_covered = _long_gain_index(repo_root, season)
    skipped = {(cid, w) for cid, items in (points_unavailable or {}).items() for s, w in items if s == season}

    stat_rows: dict[tuple[str, str], dict[str, Any]] = {}
    snap_rows: dict[tuple[str, str], dict[str, Any]] = {}
    for week, records in _partition_records(repo_root, "player-stats", season):
        for record in records:
            cid = record.get("CanonicalPlayerID")
            if cid not in cids or record.get("SeasonType", "REG") not in GAME_HISTORY_SEASON_TYPES:
                continue
            game_id = str((record.get("Stats") or {}).get("game_id") or "")
            if game_id not in games:
                raise GameHistoryError(f"player-stats row of {cid} week {week} names game '{game_id}' missing in the canonical schedule")
            stat_rows[(cid, game_id)] = record
    snap_dir = repo_root / "source-data/nfl/snap-counts" / str(season)
    if snap_dir.is_dir():
        stats_weeks = {week for week, _ in _partition_records(repo_root, "player-stats", season)}
        for path in sorted(snap_dir.glob("*.json")):
            payload = read_json(path)
            if int(payload["Week"]) not in stats_weeks:
                continue  # points need the stats partition of that week
            for record in payload.get("Records") or []:
                cid = record.get("CanonicalPlayerID")
                if cid not in cids or record.get("GameType", "REG") not in GAME_HISTORY_SEASON_TYPES:
                    continue
                game_id = str(record.get("GameID") or "")
                if game_id not in games:
                    raise GameHistoryError(f"snap-counts row of {cid} names game '{game_id}' missing in the canonical schedule")
                key = (cid, game_id)
                if key in snap_rows:
                    previous = snap_rows[key]
                    previous["OffenseSnaps"] = int(previous.get("OffenseSnaps") or 0) + int(record.get("OffenseSnaps") or 0)
                else:
                    snap_rows[key] = dict(record)

    counters: dict[str, int] = defaultdict(int)
    entries: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for cid, game_id in sorted(set(stat_rows) | set(snap_rows)):
        game = games[game_id]
        week = int(game["Week"])
        if (cid, week) in skipped:
            counters["games_skipped_points_unavailable"] += 1
            continue
        row = stat_rows.get((cid, game_id))
        snap = snap_rows.get((cid, game_id))
        stats = (row or {}).get("Stats") or {}
        team_raw = (row or snap or {}).get("Team")
        if not team_raw:
            raise GameHistoryError(f"No team for {cid} in {game_id}")
        team = keys.canonical(str(team_raw), season)
        home = keys.canonical(str(game["HomeTeam"]), season)
        away = keys.canonical(str(game["AwayTeam"]), season)
        if team not in (home, away):
            raise GameHistoryError(f"Team {team} of {cid} is neither home nor away in {game_id}")
        game_day = str(game["GameDay"]).replace("-", "")
        legacy_game_id = f"{game_day}_{keys.spelling(away)}@{keys.spelling(home)}"
        points = (weekly_points.get(cid) or {}).get(week)
        if points is None and row is None:
            points = {"points": 0.0}  # snap-only game: no stat line means all-zero stats
        if points is None:
            raise GameHistoryError(f"No league points for {cid} week {week}; the scorer and the entry rule disagree")

        has_pass, has_rush, has_rec, has_kick = (
            _has_passing(stats), _has_rushing(stats), _has_receiving(stats), _has_kicking(stats)
        )
        if has_kick:
            snap_count = int(number(stats.get("fg_att")) + number(stats.get("pat_att")))
            snap_pct: float | int = 1
        else:
            snap_count = int((snap or {}).get("OffenseSnaps") or 0)
            snap_pct = float((snap or {}).get("OffensePct") or 0)

        entry: dict[str, Any] = {
            "GameID": legacy_game_id,
            "Week": week,
            "WeekFinal": bool(week_final.get((str(game["GameType"]), week), False)),
            "Date": game_day,
            "Home": home,
            "Away": away,
            "HomePoints": game.get("HomeScore"),
            "AwayPoints": game.get("AwayScore"),
            "TeamID": team,
            "TeamAbv": team,
            "FantasyPoints": points["points"],
            "Touchdowns": int(number(stats.get("passing_tds")) + number(stats.get("receiving_tds")) + number(stats.get("rushing_tds"))),
            "SnapCount": snap_count,
            "SnapPercentage": snap_pct,
            "Attempts": int(
                number(stats.get("attempts")) + number(stats.get("targets")) + number(stats.get("carries"))
                + number(stats.get("fg_att")) + number(stats.get("pat_att"))
            ),
        }
        if has_pass:
            attempts = int(number(stats.get("attempts")))
            completions = int(number(stats.get("completions")))
            yards = int(number(stats.get("passing_yards")))
            tds = int(number(stats.get("passing_tds")))
            ints = int(number(stats.get("passing_interceptions")))
            entry["Passing"] = {
                "QBRating": qbr.get((cid, game_id)),
                "Rating": passer_rating(completions, attempts, yards, tds, ints),
                "PassAttempts": attempts,
                "PassAvg": half_up(yards, attempts),
                "PassTDs": tds,
                "PassYards": yards,
                "Interceptions": ints,
                "PassCompletions": completions,
            }
        if has_rec:
            receptions = int(number(stats.get("receptions")))
            yards = int(number(stats.get("receiving_yards")))
            entry["Receiving"] = {
                "Receptions": receptions,
                "ReceptionTDs": int(number(stats.get("receiving_tds"))),
                "LongReceptions": _long_gain(long_gains, long_covered, cid, game_id, "LongReception"),
                "Targets": int(number(stats.get("targets"))),
                "ReceptionYards": yards,
                "ReceptionAvg": half_up(yards, receptions),
            }
        if has_rush:
            carries = int(number(stats.get("carries")))
            yards = int(number(stats.get("rushing_yards")))
            entry["Rushing"] = {
                "RushAvg": half_up(yards, carries),
                "RushYards": yards,
                "Carries": carries,
                "LongRush": _long_gain(long_gains, long_covered, cid, game_id, "LongRush"),
                "RushTDs": int(number(stats.get("rushing_tds"))),
            }
        if has_kick:
            fg_made = int(number(stats.get("fg_made")))
            fg_att = int(number(stats.get("fg_att")))
            pat_made = int(number(stats.get("pat_made")))
            pat_att = int(number(stats.get("pat_att")))
            entry["Kicking"] = {
                "KickingPts": float(3 * fg_made + pat_made),
                "FgLong": int(number(stats.get("fg_long"))),
                "FgMade": fg_made,
                "FgAttempts": fg_att,
                "FgMissed": int(number(stats.get("fg_missed"))),
                "FgPct": half_up(fg_made * 100, fg_att),
                "XpMade": pat_made,
                "XpAttempts": pat_att,
                "XpMissed": int(number(stats.get("pat_missed"))),
            }
        entries[cid].append(entry)
        counters["entries"] += 1
        if row is None:
            counters["snap_only_entries"] += 1

    for cid in entries:
        entries[cid].sort(key=lambda e: e["GameID"], reverse=True)
    return dict(entries), dict(counters)


def _long_gain(
    longest: dict[tuple[str, str, str], int], covered: set[str], cid: str, game_id: str, gain_type: str
) -> int | None:
    if game_id not in covered:
        return None
    return longest.get((cid, game_id, gain_type), 0)
