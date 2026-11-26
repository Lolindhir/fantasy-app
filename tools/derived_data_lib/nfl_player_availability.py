"""NFL Player Availability (nfl-player-availability-v3): per player-week evidence, never a medical claim.

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

import hashlib
import json
from collections import Counter, defaultdict
from typing import Any, Iterable, Mapping

from derived_data_lib.nfl_franchise_aliases import franchise_equal

PRODUCT = "nfl-player-availability"
PRODUCT_VERSION = "nfl-player-availability-v3"
SCHEMA_VERSION = 3

# v3 (Issue #1612): nflverse participation (GSIS on-field plays per game) is independent positive evidence. Model parameters, versioned with
# the product. Absence from participation is never evidence.
# * a player without snap/stat evidence (participation unknown) with at least this many plays is played;
# * a player whose snap rows say not played but who has at least this many plays gets unknown (conflict), never played.
PARTICIPATION_MIN_PLAYS_UNKNOWN = 1
PARTICIPATION_MIN_PLAYS_CONFLICT = 5

STATES = (
    "played",
    "not-played-reported",
    "not-played-reserve",
    "not-played-unexplained",
    "healthy-scratch",
    "not-on-active-roster",
    "bye",
    "unknown",
)

# Roster statuses that bring a player into the population without a report row. Only statuses whose
# meaning is documented with confidence (RES = reserve list incl. injured reserve, PUP = physically unable to
# perform). INA (game-day inactive) alone is intentionally not a signal: it is dominated by healthy scratches.
RESERVE_STATUSES = frozenset({"RES", "PUP"})

# v2 population: every roster week of a player on the game-day roster (ACT active, INA game-day inactive) in a season whose
# roster status column exists (data-driven, from 2016), restricted to these positions (Robert, Issue #1610). Report weeks and
# RES/PUP weeks of every position stay in the population in every season. ``None`` for ``healthy_positions`` means all positions.
ROSTER_WEEK_STATUSES = frozenset({"ACT", "INA"})
FANTASY_POSITIONS = frozenset({"QB", "RB", "WR", "TE", "K"})

# Issue #1616 (G2): every other non-null roster status (DEV practice squad, CUT, RET, EXE, SUS and so on) of a position in the cut is a record
# with Available no and, without a report, the State not-on-active-roster. Statuses carry no further interpretation.
# Issue #1616 (G1): a bye week has no roster row. A record is written for a player whose roster row of the directly preceding regular
# week has one of these statuses (the player stays attached to the team through its bye) and whose team has no game in the week.
# CUT, RET, TRD and similar statuses end the attachment and never produce a bye record.
BYE_CARRY_STATUSES = frozenset({"ACT", "INA", "RES", "PUP", "DEV", "SUS", "EXE"})

# Report game statuses that make a player unavailable for the game.
UNAVAILABLE_REPORT_STATUSES = frozenset({"Out", "Doubtful"})

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


def _available(roster_status: str | None, report: list[dict[str, Any]] | None) -> str:
    """Available yes | no | unknown (bye is set by the caller for bye weeks) from roster status and the observed game status; never inferred from a missing row."""
    if roster_status in RESERVE_STATUSES:
        return "no"
    if any(entry["Game"] in UNAVAILABLE_REPORT_STATUSES for entry in report or ()):
        return "no"
    if roster_status in ROSTER_WEEK_STATUSES:
        return "yes"
    if roster_status is not None:
        return "no"  # any other NFL roster status: not on the active roster (Issue #1616)
    return "unknown"


def _partitions(documents: Iterable[Mapping[str, Any]] | Mapping[int, Mapping[str, Any]]) -> dict[int, Mapping[str, Any]]:
    if isinstance(documents, Mapping):
        return dict(documents)
    return {int(document["Week"]): document for document in documents}


def population_keys_sha256(keys: Iterable[tuple[int, str]]) -> str:
    """Stable fingerprint of the exact required player-week set, not source freshness."""
    payload = json.dumps(sorted(keys), ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def expected_population_keys(
    season: int,
    *,
    injuries: Mapping[str, Any] | None,
    rosters: Mapping[int, Mapping[str, Any]],
    schedule: Mapping[str, Any],
    healthy_positions: frozenset[str] | None = FANTASY_POSITIONS,
) -> set[tuple[int, str]]:
    """Independent source-side population oracle, without participation or finality.

    Keep this validation separate from the record assembly. It checks the entire
    expected key set, including report-only records, roster statuses and future
    byes. A revised partition can change the expected set even if its week was
    already present. It does not determine Availability, Played or State.
    """
    games = [g for g in schedule.get("Games", []) if isinstance(g, Mapping)]
    scheduled = {(int(g["Week"]), t) for g in games for t in (g["AwayTeam"], g["HomeTeam"])}
    teams = frozenset(t for _, t in scheduled)
    last_regular = max((int(g["Week"]) for g in games if g.get("GameType") == REGULAR_GAME_TYPE), default=0)
    roster_rows = {
        (week, r["CanonicalPlayerID"]): r
        for week, doc in sorted(_partitions(rosters).items())
        for r in doc.get("Records", []) if r.get("CanonicalPlayerID")
    }
    reports = {
        (int(r["Week"]), r["CanonicalPlayerID"]): r
        for r in (injuries or {}).get("ObservedPlayerWeeks", []) if r.get("CanonicalPlayerID")
    }

    def eligible(row: Mapping[str, Any]) -> bool:
        status = row.get("Status")
        return status in RESERVE_STATUSES or (
            status is not None and (healthy_positions is None or row.get("Position") in healthy_positions)
        )

    expected: set[tuple[int, str]] = set()
    for key in reports.keys() | {k for k, row in roster_rows.items() if eligible(row)}:
        week, _ = key
        if week <= last_regular:
            expected.add(key)
            continue
        # Outside the regular season a non-playing team has no record, not a bye.
        row, report = roster_rows.get(key, {}), reports.get(key, {})
        raw_team = row.get("Team")
        if raw_team is None:
            sources = report.get("SourceTeams") or []
            raw_team = sources[0] if sources else None
        game_type = row.get("GameType")
        if game_type is None:
            game_type = next((o.get("GameType") for o in report.get("Observations", []) if o.get("GameType")), None)
        if game_type == REGULAR_GAME_TYPE or (week, _team(raw_team, teams, season)) in scheduled:
            expected.add(key)

    for (week, pid), row in roster_rows.items():
        next_key = (week + 1, pid)
        team = _team(row.get("Team"), teams, season)
        if (
            eligible(row) and row.get("Status") in BYE_CARRY_STATUSES
            and row.get("GameType") == REGULAR_GAME_TYPE
            and week < last_regular and next_key not in roster_rows
            and next_key not in reports and team and (week + 1, team) not in scheduled
        ):
            expected.add(next_key)
    return expected


def verify_population_witness(document: Mapping[str, Any]) -> set[tuple[int, str]]:
    """Validate the exact key set of an already-published snapshot."""
    records = document["Records"]
    keys = {(r["Week"], r["CanonicalPlayerID"]) for r in records}
    witness = document["Quality"]["Population"].get("RecordKeysSha256")
    if (
        len(keys) != len(records)
        or document["Quality"]["RecordCount"] != len(records)
        or witness != population_keys_sha256(keys)
    ):
        raise AvailabilityError(f'{document["Season"]}: persisted population witness mismatch')
    return keys


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
    healthy_positions: frozenset[str] | None = FANTASY_POSITIONS,
    participation_plays: Mapping[str, Mapping[str, int]] | None = None,
) -> dict[str, Any]:
    """Return the season document. ``injuries`` may be None when no report product exists for the season.

    ``player_pfr_tokens`` maps CanonicalPlayerID to the PFR tokens known for that player (IDs plus aliases). It is a declared
    input: a snap row without identity only blocks players whose own token is unknown or equal to that row's token.
    """
    plays_by_game = participation_plays or {}
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
        plays = int(plays_by_game.get(game_id, {}).get(player) or 0)
        if player in snap_played.get(game_id, ()) or player in stats_played.get(game_id, ()):
            return "played", "snap-counts" if player in snap_played.get(game_id, ()) else "player-stats"
        if game_id in snap_games:
            if team in snap_unresolved.get(game_id, ()):
                own = pfr_tokens.get(player)
                blocked = snap_unresolved_tokens.get((game_id, team), set())
                if own and None not in blocked and not (own & blocked):
                    # The identity-less row(s) carry other people's tokens, so this player's missing row means not played.
                    if plays >= PARTICIPATION_MIN_PLAYS_CONFLICT:
                        return "unknown", "participation-conflict"
                    return "not-played", "snap-counts-token-excluded"
                if plays >= PARTICIPATION_MIN_PLAYS_UNKNOWN:
                    return "played", "participation"
                return "unknown", "snap-counts-identity-gap"
            if plays >= PARTICIPATION_MIN_PLAYS_CONFLICT:
                return "unknown", "participation-conflict"
            return "not-played", "snap-counts"
        if plays >= PARTICIPATION_MIN_PLAYS_UNKNOWN:
            return "played", "participation"
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
    healthy_weeks = 0
    for (week, player), row in roster_by_key.items():
        if row.get("Status") in RESERVE_STATUSES:
            keys.add((week, player))
        elif row.get("Status") in ROSTER_WEEK_STATUSES and (healthy_positions is None or row.get("Position") in healthy_positions):
            keys.add((week, player))
            healthy_weeks += 1
        elif row.get("Status") is not None and (healthy_positions is None or row.get("Position") in healthy_positions):
            keys.add((week, player))  # G2: other NFL roster status
    # G1: synthesized bye records. The team is the one of the last roster week before the bye (a team change around the bye keeps it).
    bye_source: dict[tuple[int, str], Mapping[str, Any]] = {}
    for (week, player), row in sorted(roster_by_key.items()):
        status = row.get("Status")
        if status not in BYE_CARRY_STATUSES or row.get("GameType") != REGULAR_GAME_TYPE or week + 1 > last_regular_week:
            continue
        if status not in RESERVE_STATUSES and healthy_positions is not None and row.get("Position") not in healthy_positions:
            continue
        nxt = (week + 1, player)
        if nxt in roster_by_key or nxt in keys:
            continue
        team = _team(row.get("Team"), schedule_teams, season)
        if team and (week + 1, team) not in game_by_team_week:
            bye_source[nxt] = row
            keys.add(nxt)

    cancelled = CANCELLED_TEAM_WEEKS.get(season, frozenset())
    records: list[dict[str, Any]] = []
    for week, player in sorted(keys):
        report = reports.get((week, player))
        roster = roster_by_key.get((week, player))
        synthetic = bye_source.get((week, player))
        raw_team = (roster or synthetic or {}).get("Team")
        if raw_team is None and report is not None:
            sources = report.get("SourceTeams") or []
            raw_team = sources[0] if sources else None
        team = _team(raw_team, schedule_teams, season)
        game_type = (roster or synthetic or {}).get("GameType")
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
                    state = (
                        "not-played-reported" if report else "not-played-reserve" if reserve
                        else "healthy-scratch" if roster_status in ROSTER_WEEK_STATUSES
                        else "not-on-active-roster" if roster_status is not None else "not-played-unexplained"
                    )
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
        report_entries = _report_entries(report) if report else None
        records.append({
            "Week": week,
            "CanonicalPlayerID": player,
            "Team": team or raw_team,
            "GameType": game_type,
            "GameID": game_id,
            "State": state,
            "Available": "bye" if state == "bye" else _available(roster_status, report_entries),
            "Played": True if part == "played" else False if part == "not-played" else None,
            "Participation": {
                "State": part, "Evidence": evidence,
                "Plays": int(plays_by_game[game_id][player]) if game_id and player in plays_by_game.get(game_id, {}) else None,
            },
            "Report": report_entries,
            "Roster": None if roster is None else {"Status": roster_status, "Code": roster.get("StatusDescription")},
        })

    # Validate against the source-side oracle before a materializer may publish.
    expected_keys = expected_population_keys(
        season, injuries=injuries, rosters=rosters, schedule=schedule, healthy_positions=healthy_positions,
    )
    actual_keys = {(r["Week"], r["CanonicalPlayerID"]) for r in records}
    if actual_keys != expected_keys or len(actual_keys) != len(records):
        missing = sorted(expected_keys - actual_keys)[:10]
        extra = sorted(actual_keys - expected_keys)[:10]
        raise AvailabilityError(f"{season}: population mismatch; missing={missing}, extra={extra}")

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
            "ParticipationAvailable": bool(plays_by_game),
            "ParticipationParameters": {
                "MinPlaysUnknownToPlayed": PARTICIPATION_MIN_PLAYS_UNKNOWN,
                "MinPlaysConflict": PARTICIPATION_MIN_PLAYS_CONFLICT,
            },
        },
        "Quality": {
            "RecordCount": len(records),
            "StateCounts": {state: state_counts.get(state, 0) for state in STATES},
            "ReportObservationsWithoutIdentity": without_identity,
            "WeekCoverage": coverage,
            "Population": {
                "RosterWeeksIncluded": roster_status_available,
                "RosterWeekStatuses": sorted(ROSTER_WEEK_STATUSES) if roster_status_available else [],
                "Positions": None if healthy_positions is None else sorted(healthy_positions),
                "RecordKeysSha256": population_keys_sha256(expected_keys),
                "ByeWeeksIncluded": roster_status_available,
                "OtherRosterStatusesIncluded": roster_status_available,
                "Rule": "report-or-reserve-weeks-of-all-positions-plus-roster-and-bye-weeks-of-the-position-cut-when-roster-status-exists" if roster_status_available
                else "report-weeks-only-no-roster-status",
            },
            "MissingEvidenceMeaning": "unknown-not-healthy-or-available",
        },
        "Records": records,
    }
