"""NFL Player Availability (nfl-player-availability-v1): per player-week evidence, never a medical claim.

Pure, deterministic derivation. Inputs are only already-persisted facts of one season:

* the Shared Derived product ``nfl-injuries-v1`` (observed report rows; never re-derived from Canonical),
* canonical NFL weekly rosters (NFL roster status plus its code),
* canonical snap counts and player stats (participation evidence),
* the canonical schedule and game finality (game, bye, final).

Report, roster, participation and game facts stay separate evidence fields. ``State`` is a documented
derivation over those fields (see ``.ai-context/manual/nfl-player-availability.yaml``). Missing evidence is
``unknown``, never healthy, available or zero. No onset, diagnosis, return date, games-missed or pre-kickoff claim.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Iterable, Mapping

from derived_data_lib.nfl_franchise_aliases import franchise_equal

PRODUCT = "nfl-player-availability"
PRODUCT_VERSION = "nfl-player-availability-v1"
SCHEMA_VERSION = 1

STATES = (
    "played",
    "not-played-reported",
    "not-played-reserve",
    "not-played-unexplained",
    "bye",
    "unknown",
)

# Roster statuses that bring a player into the population without a report row. Only statuses whose
# meaning is documented with confidence (RES = reserve list incl. injured reserve, PUP = physically unable to
# perform). INA (game-day inactive) alone is intentionally not a signal: it is dominated by healthy scratches.
RESERVE_STATUSES = frozenset({"RES", "PUP"})

# Cancelled games that are absent from the canonical schedule (hand-maintained NFL fact, see nfl-injuries.yaml).
CANCELLED_TEAM_WEEKS: dict[int, frozenset[tuple[int, str]]] = {
    2022: frozenset({(17, "BUF"), (17, "CIN")}),
}

# nflverse roster abbreviations that differ from the schedule token of the same era (only seen in 2013).
ROSTER_TEAM_ALIASES = {"ARZ": "ARI", "BLT": "BAL", "CLV": "CLE", "HST": "HOU", "SL": "STL"}

REGULAR_GAME_TYPE = "REG"


class AvailabilityError(ValueError):
    """Raised when an input cannot be used safely."""


def _team(raw: Any, schedule_teams: frozenset[str], season: int) -> str | None:
    if not isinstance(raw, str) or not raw:
        return None
    if raw in schedule_teams:
        return raw
    alias = ROSTER_TEAM_ALIASES.get(raw)
    if alias in schedule_teams:
        return alias
    for candidate in sorted(schedule_teams):
        if franchise_equal(raw, candidate, season):
            return candidate
    return None


def _report_entries(player_week: Mapping[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for observation in player_week.get("Observations", []):
        reasons: list[str] = []
        raw = observation.get("Reasons") or {}
        for key in (
            "report_primary_injury", "report_secondary_injury",
            "practice_primary_injury", "practice_secondary_injury",
        ):
            text = (raw.get(key) or "").strip()
            if text and text not in reasons:
                reasons.append(text)
        entry = {
            "Game": (observation.get("ReportStatus") or "").strip() or None,
            "Practice": (observation.get("PracticeStatus") or "").strip() or None,
            "Reasons": reasons,
        }
        if entry not in entries:
            entries.append(entry)
    return entries


def _partitions(documents: Iterable[Mapping[str, Any]] | Mapping[int, Mapping[str, Any]]) -> dict[int, Mapping[str, Any]]:
    if isinstance(documents, Mapping):
        return dict(documents)
    return {int(document["Week"]): document for document in documents}


def derive_nfl_player_availability(
    season: int,
    *,
    injuries: Mapping[str, Any] | None,
    rosters: Mapping[int, Mapping[str, Any]],
    snap_counts: Mapping[int, Mapping[str, Any]],
    player_stats: Mapping[int, Mapping[str, Any]],
    schedule: Mapping[str, Any],
    finality: Mapping[str, Any],
    player_pfr_tokens: Mapping[str, Iterable[str]] | None = None,
) -> dict[str, Any]:
    """Return the season document. ``injuries`` may be None when no report product exists for the season.

    ``player_pfr_tokens`` maps CanonicalPlayerID to the PFR tokens known for that player (IDs plus aliases). It is a declared
    input: a snap row without identity only blocks players whose own token is unknown or equal to that row's token.
    """
    pfr_tokens = {pid: frozenset(t for t in tokens if t) for pid, tokens in (player_pfr_tokens or {}).items()}
    if schedule.get("Season") != season or finality.get("Season") != season:
        raise AvailabilityError(f"schedule/finality season mismatch for {season}")
    if injuries is not None and (injuries.get("Season") != season or injuries.get("ProductVersion") != "nfl-injuries-v1"):
        raise AvailabilityError(f"unsupported injury product input for {season}")

    games = [g for g in schedule.get("Games", []) if isinstance(g, Mapping)]
    schedule_teams = frozenset(t for g in games for t in (g.get("AwayTeam"), g.get("HomeTeam")) if t)
    game_by_team_week: dict[tuple[int, str], Mapping[str, Any]] = {}
    for game in games:
        for team in (game["AwayTeam"], game["HomeTeam"]):
            key = (int(game["Week"]), team)
            if key in game_by_team_week:
                raise AvailabilityError(f"team {team} has two games in week {key[0]} of {season}")
            game_by_team_week[key] = game
    final_games = {g["GameID"] for g in finality.get("Games", []) if g.get("Final") is True}
    last_regular_week = max((int(g["Week"]) for g in games if g.get("GameType") == REGULAR_GAME_TYPE), default=0)

    # Participation evidence per game.
    snap_rows = _partitions(snap_counts)
    stat_rows = _partitions(player_stats)
    snap_played: dict[str, set[str]] = defaultdict(set)
    snap_unresolved: dict[str, set[str]] = defaultdict(set)  # GameID -> teams with a row without identity
    # (GameID, team) -> PFR tokens of identity-less rows; None marks a row without any token (could be anyone).
    snap_unresolved_tokens: dict[tuple[str, str], set[str | None]] = defaultdict(set)
    snap_games: set[str] = set()
    for document in snap_rows.values():
        for row in document.get("Records", []):
            game_id = row.get("GameID")
            if not game_id:
                continue
            snap_games.add(game_id)
            player = row.get("CanonicalPlayerID")
            if not player:
                team = _team(row.get("Team"), schedule_teams, season)
                if team:
                    snap_unresolved[game_id].add(team)
                    token = (row.get("SourceIDs") or {}).get("PFR")
                    snap_unresolved_tokens[(game_id, team)].add(token if isinstance(token, str) and token else None)
                continue
            total = sum(int(row.get(k) or 0) for k in ("OffenseSnaps", "DefenseSnaps", "SpecialTeamsSnaps"))
            if total > 0:
                snap_played[game_id].add(player)
    stats_played: dict[str, set[str]] = defaultdict(set)
    for document in stat_rows.values():
        for row in document.get("Records", []):
            player = row.get("CanonicalPlayerID")
            game_id = (row.get("Stats") or {}).get("game_id")
            if player and game_id:
                stats_played[game_id].add(player)

    def participation(game_id: str, team: str, player: str) -> tuple[str, str | None]:
        if player in snap_played.get(game_id, ()) or player in stats_played.get(game_id, ()):
            return "played", "snap-counts" if player in snap_played.get(game_id, ()) else "player-stats"
        if game_id in snap_games:
            if team in snap_unresolved.get(game_id, ()):
                own = pfr_tokens.get(player)
                blocked = snap_unresolved_tokens.get((game_id, team), set())
                if own and None not in blocked and not (own & blocked):
                    # The identity-less row(s) carry other people's tokens, so this player's missing row means not played.
                    return "not-played", "snap-counts-token-excluded"
                return "unknown", "snap-counts-identity-gap"
            return "not-played", "snap-counts"
        return "unknown", None

    # Signals.
    reports: dict[tuple[int, str], dict[str, Any]] = {}
    without_identity = 0
    if injuries is not None:
        for player_week in injuries.get("ObservedPlayerWeeks", []):
            player = player_week.get("CanonicalPlayerID")
            if not player:
                without_identity += int(player_week.get("ObservedReportCount") or 1)
                continue
            reports[(int(player_week["Week"]), player)] = player_week
    roster_by_key: dict[tuple[int, str], Mapping[str, Any]] = {}
    roster_status_available = False
    for week, document in sorted(_partitions(rosters).items()):
        for row in document.get("Records", []):
            player = row.get("CanonicalPlayerID")
            if not player:
                continue
            roster_by_key[(week, player)] = row
            roster_status_available = roster_status_available or row.get("Status") is not None

    keys = set(reports)
    for (week, player), row in roster_by_key.items():
        if row.get("Status") in RESERVE_STATUSES:
            keys.add((week, player))

    cancelled = CANCELLED_TEAM_WEEKS.get(season, frozenset())
    records: list[dict[str, Any]] = []
    for week, player in sorted(keys):
        report = reports.get((week, player))
        roster = roster_by_key.get((week, player))
        raw_team = (roster or {}).get("Team")
        if raw_team is None and report is not None:
            sources = report.get("SourceTeams") or []
            raw_team = sources[0] if sources else None
        team = _team(raw_team, schedule_teams, season)
        game_type = (roster or {}).get("GameType")
        if game_type is None and report is not None:
            game_type = next((o.get("GameType") for o in report.get("Observations", []) if o.get("GameType")), None)
        game = game_by_team_week.get((week, team)) if team else None
        if game is None and game_type != REGULAR_GAME_TYPE and week > last_regular_week:
            continue  # postseason week without a game of this team: not a bye, not a record
        roster_status = (roster or {}).get("Status")
        reserve = roster_status in RESERVE_STATUSES
        evidence: str | None = None
        part: str
        if game is not None:
            game_id = game["GameID"]
            if game_id not in final_games:
                part, evidence, state = "unknown", "game-not-final", "unknown"
            else:
                part, evidence = participation(game_id, team, player)
                if part == "played":
                    state = "played"
                elif part == "not-played":
                    state = "not-played-reported" if report else "not-played-reserve" if reserve else "not-played-unexplained"
                elif reserve and evidence == "snap-counts-identity-gap":
                    # A player on the NFL reserve list cannot have played; the snap rows of his team only miss an identity.
                    state = "not-played-reported" if report else "not-played-reserve"
                else:
                    state = "unknown"
        else:
            game_id = None
            if team is None:
                part, evidence, state = "unknown", "team-unresolved", "unknown"
            elif (week, team) in cancelled:
                part, evidence, state = "unknown", "cancelled-game", "unknown"
            elif game_type == REGULAR_GAME_TYPE or week <= last_regular_week:
                part, evidence, state = "no-game", "bye", "bye"
            else:
                continue
        records.append({
            "Week": week,
            "CanonicalPlayerID": player,
            "Team": team or raw_team,
            "GameType": game_type,
            "GameID": game_id,
            "State": state,
            "Participation": {"State": part, "Evidence": evidence},
            "Report": _report_entries(report) if report else None,
            "Roster": None if roster is None else {"Status": roster_status, "Code": roster.get("StatusDescription")},
        })

    state_counts = Counter(record["State"] for record in records)
    coverage = []
    for week in sorted({int(g["Week"]) for g in games}):
        week_games = [g for g in games if int(g["Week"]) == week]
        coverage.append({
            "Week": week,
            "Games": len(week_games),
            "FinalGames": sum(1 for g in week_games if g["GameID"] in final_games),
            "GamesWithSnapCounts": sum(1 for g in week_games if g["GameID"] in snap_games),
            "RosterPartition": week in _partitions(rosters),
        })
    return {
        "Product": PRODUCT,
        "ProductVersion": PRODUCT_VERSION,
        "SchemaVersion": SCHEMA_VERSION,
        "Season": season,
        "Inputs": {
            "InjuryProduct": None if injuries is None else {
                "ProductVersion": injuries["ProductVersion"],
                "SourceAssetSha256": injuries.get("SourceAssetSha256"),
                "IdentityGraphFingerprint": injuries.get("IdentityGraphFingerprint"),
            },
            "RosterStatusAvailable": roster_status_available,
            "SnapCountsAvailable": bool(snap_games),
            "PlayerStatsAvailable": bool(stats_played),
            "PfrTokenIndexAvailable": bool(pfr_tokens),
        },
        "Quality": {
            "RecordCount": len(records),
            "StateCounts": {state: state_counts.get(state, 0) for state in STATES},
            "ReportObservationsWithoutIdentity": without_identity,
            "WeekCoverage": coverage,
            "MissingEvidenceMeaning": "unknown-not-healthy-or-available",
        },
        "Records": records,
    }
