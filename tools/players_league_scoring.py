#!/usr/bin/env python3
"""League-scoring inputs for Players.json (#347 D4).

Scores canonical NFL player stats with the league ScoringSettings and exports, per
Sleeper player ID, the weekly rows RequestPlayers.ps1 needs for the current season
and the three prior seasons. It replaces Tank01 PPR points and the Tank01
past_seasons/Players_<year>.json archives as the points source. Salary, ranking
and grading formulas stay in PowerShell.

Identity: Players.json[].ID is the Sleeper player_id. It is resolved to a
CanonicalPlayerID per season through the season-aware provider mappings, so a
player whose Sleeper ID was reassigned for the current season keeps the history
that belongs to the earlier owner of the mapping. A Sleeper ID without exactly one
mapping for the current season is an identity hold: no points are exported and the
consumer keeps the last published values.

The export is deterministic (no timestamps) and consumer-neutral; it is rebuilt on
every Players run from the canonical facts and is not persisted in the repository.

Usage:
  players_league_scoring.py export --season 2026 --sleeper-ids-file ids.json --out export.json
  players_league_scoring.py week-bounds --season 2026
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from historical_fantasy_scoring import number, read_json, score_record  # noqa: E402
from player_week_fantasy import build_scoring_profile_identity  # noqa: E402

LEAGUE_ID = "nfl-reise"
SCHEMA_VERSION = 1
HISTORY_DEPTH = 3
EXPORT_ROW_FIELDS = ("Points", "Snaps", "KickAttempts", "Attempts", "TdPass", "TdRec", "TdRush")


# --------------------------------------------------------------------------- #
# Canonical inputs
# --------------------------------------------------------------------------- #
def final_regular_weeks(repo_root: Path, season: int) -> set[int]:
    path = repo_root / "source-data/nfl/game-finality" / f"{season}.json"
    payload = read_json(path)
    return {
        int(w["Week"])
        for w in payload["Weeks"]
        if w.get("WeekFinal") is True and w.get("GameType", "REG") == "REG"
    }


def resolve_league_week_bounds(repo_root: Path, league_id: str, season: int) -> dict[str, int]:
    """Week bounds of the Players generator from canonical facts only (#347 I1).

    LastLeagueWeek and PlayoffStartWeek come from the canonical League-season
    WeekStructure; FinalScoredWeek is the last week of the uninterrupted run of
    final regular-season weeks in the canonical NFL game finality, capped at
    LastLeagueWeek. A missing structure or finality fails closed.
    """
    path = repo_root / "source-data/leagues" / league_id / "seasons" / str(season) / "league.json"
    if not path.is_file():
        raise ValueError(f"Canonical league source missing: {path}")
    structure = read_json(path).get("WeekStructure")
    if not isinstance(structure, dict):
        raise ValueError(f"No WeekStructure in {path}")

    def positive(name: str) -> int | None:
        value = structure.get(name)
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f"WeekStructure.{name} must be a positive integer in {path}")
        return value

    last_week = positive("ExpectedLastLeagueWeek") or positive("FinalLeagueWeek")
    playoff_start = positive("PlayoffStartWeek")
    if last_week is None:
        raise ValueError(f"WeekStructure in {path} cannot resolve a last league week")
    if playoff_start is None:
        raise ValueError(f"WeekStructure in {path} has no PlayoffStartWeek")

    final_weeks = final_regular_weeks(repo_root, season)
    final_week = 0
    while final_week + 1 in final_weeks:
        final_week += 1
    return {
        "LastLeagueWeek": last_week,
        "PlayoffStartWeek": playoff_start,
        "FinalScoredWeek": min(final_week, last_week),
    }


def league_scoring_settings(repo_root: Path, league_id: str, season: int) -> dict[str, Any]:
    path = repo_root / "source-data/leagues" / league_id / "seasons" / str(season) / "league.json"
    settings = read_json(path).get("ScoringSettings")
    if not isinstance(settings, dict) or not settings:
        raise ValueError(f"No ScoringSettings in {path}")
    return settings


def league_owned_sleeper_ids(repo_root: Path, league_id: str, season: int) -> set[str]:
    rosters = read_json(repo_root / "source-data/leagues" / league_id / "seasons" / str(season) / "rosters.json")
    return {
        str(mapping["ProviderPlayerID"])
        for team in rosters
        for player in team.get("Players") or []
        for mapping in player.get("ProviderMappings") or []
        if mapping.get("Provider") == "Sleeper"
    }


class SleeperIdentityResolver:
    """Season-aware Sleeper player_id -> CanonicalPlayerID.

    Candidates for a season are the persisted Sleeper mappings and the parties of
    persisted mapping conflicts that cover the season. A candidate record without any
    provider ID (a provisional app record) cannot own NFL stats, because stats attach
    through provider IDs; it is dropped as a candidate. Exactly one remaining
    candidate resolves the ID, anything else is ambiguous (fail closed).
    """

    RESOLVED = "resolved"
    AMBIGUOUS = "ambiguous"
    UNMAPPED = "unmapped"

    def __init__(self, mappings_payload: dict[str, Any], identities_payload: dict[str, Any]) -> None:
        self._mappings: dict[str, list[tuple[int, int, str]]] = defaultdict(list)
        self._conflicts: dict[str, list[tuple[int, int, tuple[str, ...]]]] = defaultdict(list)
        self._empty: set[str] = {
            str(record["CanonicalPlayerID"])
            for record in identities_payload.get("Players") or []
            if not (record.get("IDs") or {})
        }
        for mapping in mappings_payload.get("Mappings") or []:
            if mapping.get("Provider") != "Sleeper":
                continue
            first = int(mapping.get("FirstObservedSeason") or 0)
            last = int(mapping.get("LastObservedSeason") or first)
            cid = mapping.get("CanonicalPlayerID")
            if cid:
                self._mappings[str(mapping["ExternalID"])].append((first, last, str(cid)))
        for conflict in mappings_payload.get("Conflicts") or []:
            if conflict.get("Provider") != "Sleeper":
                continue
            first = int(conflict.get("FirstObservedSeason") or 0)
            last = int(conflict.get("LastObservedSeason") or first)
            parties = tuple(str(cid) for cid in conflict.get("CanonicalPlayerIDs") or [])
            self._conflicts[str(conflict["ExternalID"])].append((first, last, parties))

    @classmethod
    def from_repo(cls, repo_root: Path) -> "SleeperIdentityResolver":
        return cls(
            read_json(repo_root / "source-data/nfl/identities/provider-mappings.json"),
            read_json(repo_root / "source-data/nfl/identities/players.json"),
        )

    def _candidates(self, sleeper_id: str, season: int) -> set[str]:
        candidates = {cid for first, last, cid in self._mappings.get(sleeper_id, ()) if first <= season <= last}
        for first, last, parties in self._conflicts.get(sleeper_id, ()):
            if first <= season <= last:
                candidates.update(parties)
        return candidates

    def resolve(self, sleeper_id: str, season: int) -> tuple[str | None, str]:
        """Resolve for one season.

        Mappings only start with the first persisted observation, so a season before the
        earliest observation is resolved through the earliest observation (Sleeper IDs are
        stable per person); a season in a gap between observations stays unmapped.
        """
        sleeper_id = str(sleeper_id)
        candidates = self._candidates(sleeper_id, season)
        if not candidates:
            seasons = [first for first, _, _ in self._mappings.get(sleeper_id, ())]
            seasons += [first for first, _, _ in self._conflicts.get(sleeper_id, ())]
            if seasons and season < min(seasons):
                candidates = self._candidates(sleeper_id, min(seasons))
        owners = {cid for cid in candidates if cid not in self._empty}
        if len(owners) == 1:
            return next(iter(owners)), self.RESOLVED
        if owners:
            return None, self.AMBIGUOUS
        return None, self.UNMAPPED


EVIDENCE_HOLD_STATUS = "ambiguous-evidence"
AMBIGUOUS_FUMBLE_MESSAGE = "ambiguous fumble-team relation"


def _partition_files(repo_root: Path, dataset: str, season: int) -> list[Path]:
    directory = repo_root / "source-data/nfl" / dataset / str(season)
    if not directory.is_dir():
        raise FileNotFoundError(f"Canonical partition directory missing: {directory}")
    return sorted(directory.glob("*.json"))


def build_weekly_scores(
    repo_root: Path,
    seasons: tuple[int, ...],
    current_season: int,
    final_weeks_current: set[int],
    wanted: set[str],
    scoring: dict[str, Any],
    ambiguous_evidence: dict[str, list[tuple[int, int]]] | None = None,
) -> tuple[dict[int, dict[str, dict[int, dict[str, float]]]], Counter, Counter]:
    """weekly[season][cid][week] = {points, snaps, kick_attempts, attempts, td_*}.

    Fail-closed: historical partitions must be Finalized, current partitions are
    limited to canonical WeekFinal REG weeks. With an `ambiguous_evidence` collector a record whose
    special-teams fumble evidence is ambiguous is not scored; it is listed there as
    {CanonicalPlayerID: [(season, week)]} and the caller decides (Players: identity-style hold).
    Without the collector the ambiguity raises.
    """
    weekly: dict[int, dict[str, dict[int, dict[str, float]]]] = {s: defaultdict(dict) for s in seasons}
    unsupported: Counter = Counter()
    counts: Counter = Counter()
    for season in seasons:
        for stats_file in _partition_files(repo_root, "player-stats", season):
            payload = read_json(stats_file)
            week = int(payload["Week"])
            if season == current_season:
                if week not in final_weeks_current:
                    continue
            elif payload.get("Finalized") is not True:
                raise ValueError(f"Historical player-stats partition is not finalized: {stats_file}")
            snaps: dict[str, int] = defaultdict(int)
            snap_path = repo_root / "source-data/nfl/snap-counts" / str(season) / stats_file.name
            if snap_path.exists():
                for record in read_json(snap_path)["Records"]:
                    if record.get("CanonicalPlayerID") in wanted:
                        snaps[record["CanonicalPlayerID"]] += int(record.get("OffenseSnaps") or 0)
            events: dict[str, list[dict[str, Any]]] = defaultdict(list)
            events_path = repo_root / "source-data/nfl/special-teams-fumble-events" / str(season) / stats_file.name
            events_ok = False
            if events_path.exists():
                events_payload = read_json(events_path)
                events_ok = season == current_season or events_payload.get("Finalized") is True
                if events_ok:
                    for event in events_payload["Records"]:
                        events[event.get("CanonicalPlayerID")].append(event)
            for record in payload["Records"]:
                cid = record.get("CanonicalPlayerID")
                if cid not in wanted or record.get("SeasonType", "REG") != "REG":
                    continue
                try:
                    result = score_record(record, scoring, special_teams_fumble_events=events[cid] if events_ok else None)
                except ValueError as error:
                    if ambiguous_evidence is None or AMBIGUOUS_FUMBLE_MESSAGE not in str(error):
                        raise
                    ambiguous_evidence.setdefault(cid, []).append((season, week))
                    continue
                for key in result["UnsupportedNonZeroSettings"]:
                    unsupported[(season, key)] += 1
                stats = record["Stats"]
                weekly[season][cid][week] = {
                    "points": result["FantasyPoints"],
                    "snaps": snaps.get(cid, 0),
                    "kick_attempts": number(stats.get("fg_att")) + number(stats.get("pat_att")),
                    "attempts": number(stats.get("attempts")) + number(stats.get("targets")) + number(stats.get("carries"))
                    + number(stats.get("fg_att")) + number(stats.get("pat_att")),
                    "td_pass": number(stats.get("passing_tds")),
                    "td_rec": number(stats.get("receiving_tds")),
                    "td_rush": number(stats.get("rushing_tds")),
                }
            # snap-only games: nflverse omits all-zero stat lines
            for cid, snap_total in snaps.items():
                if snap_total > 0 and week not in weekly[season][cid]:
                    weekly[season][cid][week] = {
                        "points": 0.0, "snaps": snap_total, "kick_attempts": 0.0, "attempts": 0.0,
                        "td_pass": 0.0, "td_rec": 0.0, "td_rush": 0.0,
                    }
                    counts[f"snap_only_games_{season}"] += 1
    return weekly, unsupported, counts


def net_round(value: float, digits: int) -> float:
    """[math]::Round(value, digits): scales, then rounds half to even (differs from Python round)."""
    factor = 10.0 ** digits
    return round(value * factor) / factor


def played_weeks(weeks: dict[int, dict[str, float]], position: str, max_week: int) -> dict[int, dict[str, float]]:
    out = {}
    for week, row in weeks.items():
        if week > max_week:
            continue
        played = row["kick_attempts"] > 0 if position == "K" else row["snaps"] > 0
        if played:
            out[week] = row
    return out


def season_view(weeks: dict[int, dict[str, float]], position: str, max_week: int, potential: int) -> dict[str, Any]:
    games = played_weeks(weeks, position, max_week)
    total = net_round(sum(g["points"] for g in games.values()), 2)
    count = len(games)
    return {
        "Total": total,
        "AvgGame": net_round(total / count, 2) if count else 0.0,
        "AvgPotentialGame": net_round(total / potential, 2) if potential else 0.0,
        "GamesPlayed": count,
        "PotentialGames": potential,
    }


# --------------------------------------------------------------------------- #
# Export
# --------------------------------------------------------------------------- #
def _export_row(row: dict[str, float]) -> dict[str, float]:
    return {
        "Points": row["points"],
        "Snaps": int(row["snaps"]),
        "KickAttempts": row["kick_attempts"],
        "Attempts": row["attempts"],
        "TdPass": row["td_pass"],
        "TdRec": row["td_rec"],
        "TdRush": row["td_rush"],
    }


def resolve_player_seasons(
    resolver: SleeperIdentityResolver, sleeper_ids: list[str], seasons: tuple[int, ...], current_season: int,
) -> dict[str, dict[str, Any]]:
    resolved: dict[str, dict[str, Any]] = {}
    for sleeper_id in sleeper_ids:
        current, status = resolver.resolve(sleeper_id, current_season)
        entry: dict[str, Any] = {"Status": status, "CanonicalPlayerID": current, "SeasonIdentities": {}}
        if current is not None:
            for season in seasons:
                cid, season_status = resolver.resolve(sleeper_id, season)
                entry["SeasonIdentities"][season] = (cid, season_status)
        resolved[sleeper_id] = entry
    return resolved


def build_export(
    repo_root: Path,
    league_id: str,
    season: int,
    sleeper_ids: list[str],
) -> dict[str, Any]:
    scoring = league_scoring_settings(repo_root, league_id, season)
    profile = build_scoring_profile_identity(league_id, season, scoring)
    final_weeks = final_regular_weeks(repo_root, season)
    seasons = tuple(season - offset for offset in range(HISTORY_DEPTH, -1, -1))
    ids = sorted({str(value) for value in sleeper_ids})

    resolver = SleeperIdentityResolver.from_repo(repo_root)
    resolved = resolve_player_seasons(resolver, ids, seasons, season)
    owned = league_owned_sleeper_ids(repo_root, league_id, season)
    conflicting_owned = sorted(
        sid for sid, entry in resolved.items() if entry["Status"] == resolver.AMBIGUOUS and sid in owned
    )
    if conflicting_owned:
        raise ValueError(
            "League-owned players with an ambiguous current identity cannot be scored: "
            + ", ".join(conflicting_owned)
        )

    wanted = {
        cid
        for entry in resolved.values()
        for cid, status in entry["SeasonIdentities"].values()
        if cid is not None and status == resolver.RESOLVED
    }
    ambiguous_evidence: dict[str, list[tuple[int, int]]] = {}
    weekly, unsupported, counts = build_weekly_scores(
        repo_root, seasons, season, final_weeks, wanted, scoring, ambiguous_evidence
    )
    evidence_hold = {
        sleeper_id
        for sleeper_id, entry in resolved.items()
        if any(cid in ambiguous_evidence for cid, _ in entry["SeasonIdentities"].values())
    }
    owned_evidence_hold = sorted(evidence_hold & owned)
    if owned_evidence_hold:
        raise ValueError(
            "League-owned players with ambiguous special-teams fumble evidence cannot be scored: "
            + ", ".join(owned_evidence_hold)
        )
    if unsupported:
        raise ValueError(
            "ScoringSettings with a non-zero weight that the scorer does not map: "
            + ", ".join(f"{s}:{k}" for (s, k) in sorted(unsupported))
        )

    players: dict[str, Any] = {}
    unresolved_history: list[dict[str, Any]] = []
    for sleeper_id in ids:
        entry = resolved[sleeper_id]
        if sleeper_id in evidence_hold:
            players[sleeper_id] = {"Status": EVIDENCE_HOLD_STATUS, "CanonicalPlayerID": None, "Seasons": {}}
            continue
        if entry["Status"] != resolver.RESOLVED:
            players[sleeper_id] = {"Status": entry["Status"], "CanonicalPlayerID": None, "Seasons": {}}
            continue
        seasons_out: dict[str, dict[str, Any]] = {}
        for season_value in seasons:
            cid, season_status = entry["SeasonIdentities"][season_value]
            if cid is None:
                if season_value != season:
                    unresolved_history.append({"SleeperID": sleeper_id, "Season": season_value, "Reason": season_status})
                seasons_out[str(season_value)] = {}
                continue
            rows = weekly[season_value].get(cid, {})
            seasons_out[str(season_value)] = {
                str(week): _export_row(row)
                for week, row in sorted(rows.items())
                # prior seasons only feed the played-games aggregates; the current season also
                # feeds per-game points for games without a played snap
                if season_value == season or row["snaps"] > 0 or row["kick_attempts"] > 0
            }
        players[sleeper_id] = {"Status": entry["Status"], "CanonicalPlayerID": entry["CanonicalPlayerID"], "Seasons": seasons_out}

    return {
        "SchemaVersion": SCHEMA_VERSION,
        "CanonicalLeagueID": league_id,
        "Season": season,
        "ScoringProfile": profile,
        "FinalRegularWeeksCurrent": sorted(final_weeks),
        "HistorySeasons": [s for s in seasons if s != season],
        "Counts": dict(counts),
        "UnresolvedHistory": unresolved_history,
        "AmbiguousEvidence": [
            {"SleeperID": sid, "Reason": "special-teams-fumble-relation"} for sid in sorted(evidence_hold)
        ],
        "Players": players,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--league", default=LEAGUE_ID)
    sub = parser.add_subparsers(dest="command", required=True)
    export = sub.add_parser("export", help="write the per-Sleeper-ID weekly league-scoring export")
    export.add_argument("--season", type=int, required=True)
    export.add_argument("--sleeper-ids-file", type=Path, required=True, help="JSON array of Sleeper player IDs")
    export.add_argument("--out", type=Path, required=True)
    bounds = sub.add_parser("week-bounds", help="print LastLeagueWeek, PlayoffStartWeek and FinalScoredWeek as JSON")
    bounds.add_argument("--season", type=int, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "week-bounds":
        try:
            bounds = resolve_league_week_bounds(args.repo_root, args.league, args.season)
        except (ValueError, KeyError, OSError) as error:
            print(f"Week bounds unavailable: {error}", file=sys.stderr)
            return 1
        print(json.dumps(bounds, sort_keys=True))
        return 0
    ids = json.loads(args.sleeper_ids_file.read_text(encoding="utf-8-sig"))
    if not isinstance(ids, list) or not ids:
        print("--sleeper-ids-file must hold a non-empty JSON array", file=sys.stderr)
        return 2
    payload = build_export(args.repo_root, args.league, args.season, [str(value) for value in ids])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    held = sum(1 for p in payload["Players"].values() if p["Status"] != SleeperIdentityResolver.RESOLVED)
    print(f"Exported {len(payload['Players'])} players ({held} hold: identity or ambiguous evidence) for season {args.season}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
