#!/usr/bin/env python3
"""Build the deterministic Fantasy Operations FA-board read model.

The read model combines the current league ownership state, the currently active
Free-Agent draft, already materialized provider-neutral player signals, and
current managed-team reserve/taxi capacity. It is decision infrastructure only:
it does not browse, call AI services, or emit add/drop/draft recommendations.

Availability is fail-closed. A negative ownership result is trusted only when
League.json was fully validated, and a player is considered draft-available only
when the current Free-Agent draft state is also resolved. Positive ownership or
an assigned pick always blocks availability even when another source is degraded.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Literal

SCHEMA_VERSION = 1
CONFIG_SCHEMA_VERSION = 1
DATASET_ID = "fa-board-readmodel"
PLAYER_SIGNAL_DATASET_ID = "player-signals"
UNKNOWN = "unknown"

Eligibility = bool | Literal["unknown"]
SlotCost = int | Literal["unknown"]


class FaBoardMaterializationError(RuntimeError):
    """Raised when the FA-board read model cannot be built safely."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FaBoardMaterializationError(f"Missing required JSON input: {path}") from exc
    except json.JSONDecodeError as exc:
        raise FaBoardMaterializationError(f"Invalid JSON input {path}: {exc}") from exc


def source_hash(path: Path) -> str:
    try:
        return sha256_text(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FaBoardMaterializationError(f"Missing required source file: {path}") from exc


def optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def optional_number(value: Any) -> int | float | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number.is_integer():
        return int(number)
    return round(number, 4)


def parse_datetime(value: Any) -> datetime | None:
    text = optional_text(value)
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def max_timestamp(values: Iterable[Any]) -> str | None:
    parsed = [item for item in (parse_datetime(value) for value in values) if item is not None]
    if not parsed:
        return None
    return max(parsed).isoformat().replace("+00:00", "Z")


def normalize_status(value: Any) -> str:
    text = str(value or "").strip().upper().replace("-", "_").replace(" ", "_")
    while "__" in text:
        text = text.replace("__", "_")
    return text


def safe_id_list(value: Any, *, field: str, issues: list[dict[str, Any]], required: bool) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        issues.append({"severity": "error", "kind": "invalid_roster_section", "field": field})
        return []
    result: list[str] = []
    for item in value:
        if item is None or str(item).strip() == "":
            issues.append({"severity": "error", "kind": "invalid_player_id", "field": field})
            continue
        result.append(str(item))
    if required and value is None:
        issues.append({"severity": "error", "kind": "missing_roster_section", "field": field})
    return result


def validate_player_signals(source: Any) -> dict[str, Any]:
    if not isinstance(source, dict):
        raise FaBoardMaterializationError("player-signals input must be an object")
    if source.get("schema_version") != 1 or source.get("dataset_id") != PLAYER_SIGNAL_DATASET_ID:
        raise FaBoardMaterializationError("Input is not a schema-version-1 player-signals dataset")
    players = source.get("players")
    if not isinstance(players, list) or not players:
        raise FaBoardMaterializationError("player-signals must contain a non-empty players array")
    ids = [str(player.get("player_id")) for player in players if isinstance(player, dict)]
    if len(ids) != len(players) or len(ids) != len(set(ids)):
        raise FaBoardMaterializationError("player-signals contains invalid or duplicate player IDs")
    return source


def build_league_state(league: Any, managed_team_id: str) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    if not isinstance(league, dict):
        return {"complete": False, "issues": [{"severity": "error", "kind": "league_not_object"}]}

    teams = league.get("Teams")
    settings = league.get("Settings") if isinstance(league.get("Settings"), dict) else {}
    taxi_slots_raw = optional_number(settings.get("taxi_slots"))
    reserve_slots_raw = optional_number(settings.get("reserve_slots"))
    taxi_slots = int(taxi_slots_raw) if isinstance(taxi_slots_raw, (int, float)) else 0
    reserve_slots = int(reserve_slots_raw) if isinstance(reserve_slots_raw, (int, float)) else 0

    if not isinstance(teams, list) or not teams:
        return {"complete": False, "issues": [{"severity": "error", "kind": "league_teams_missing"}]}

    ownership: dict[str, list[dict[str, Any]]] = defaultdict(list)
    team_by_id: dict[str, dict[str, Any]] = {}
    managed_team: dict[str, Any] | None = None

    for team in teams:
        if not isinstance(team, dict):
            issues.append({"severity": "error", "kind": "invalid_team_record"})
            continue
        team_id = optional_text(team.get("TeamID"))
        if not team_id:
            issues.append({"severity": "error", "kind": "team_without_id"})
            continue
        if team_id in team_by_id:
            issues.append({"severity": "error", "kind": "duplicate_team_id", "team_id": team_id})
            continue
        team_by_id[team_id] = team

        if "Roster" not in team:
            issues.append({"severity": "error", "kind": "missing_roster_section", "team_id": team_id, "section": "Roster"})
        if taxi_slots > 0 and "Taxi" not in team:
            issues.append({"severity": "error", "kind": "missing_roster_section", "team_id": team_id, "section": "Taxi"})
        if reserve_slots > 0 and "Reserve" not in team:
            issues.append({"severity": "error", "kind": "missing_roster_section", "team_id": team_id, "section": "Reserve"})

        roster = safe_id_list(team.get("Roster"), field=f"team:{team_id}:Roster", issues=issues, required=False)
        taxi = safe_id_list(team.get("Taxi"), field=f"team:{team_id}:Taxi", issues=issues, required=False)
        reserve = safe_id_list(team.get("Reserve"), field=f"team:{team_id}:Reserve", issues=issues, required=False)

        section_sets = {"Roster": set(roster), "Taxi": set(taxi), "Reserve": set(reserve)}
        for player_id in sorted(set().union(*section_sets.values())):
            sections = [name for name in ("Roster", "Taxi", "Reserve") if player_id in section_sets[name]]
            ownership[player_id].append(
                {
                    "team_id": team_id,
                    "team_name": optional_text(team.get("Team")),
                    "team_abbreviation": optional_text(team.get("TeamAbbr")),
                    "roster_sections": sections,
                }
            )

        if team_id == managed_team_id:
            managed_team = {
                "team_id": team_id,
                "team_name": optional_text(team.get("Team")),
                "roster": set(roster),
                "taxi": set(taxi),
                "reserve": set(reserve),
            }

    for player_id, owners in ownership.items():
        if len(owners) > 1:
            issues.append(
                {
                    "severity": "error",
                    "kind": "multiple_team_ownership",
                    "player_id": player_id,
                    "team_ids": [owner["team_id"] for owner in owners],
                }
            )

    if managed_team is None:
        issues.append({"severity": "error", "kind": "managed_team_missing", "team_id": managed_team_id})

    roster_size = league.get("RosterSize")
    active_capacity = len(roster_size) if isinstance(roster_size, list) else None
    if active_capacity is None:
        issues.append({"severity": "error", "kind": "roster_size_missing"})

    complete = not any(issue.get("severity") == "error" for issue in issues)
    return {
        "complete": complete,
        "issues": issues,
        "ownership": ownership,
        "team_by_id": team_by_id,
        "managed_team": managed_team,
        "settings": settings,
        "active_capacity": active_capacity,
        "league_season": optional_text(league.get("Season")),
        "league_phase": optional_text(league.get("Phase")),
        "league_status": optional_text(league.get("Status")),
        "season_kickoff": optional_text(league.get("SeasonKickoff")),
        "current_week": optional_number(league.get("CurrentWeek")),
    }


def resolve_active_fa_draft(drafts: Any, league_state: dict[str, Any]) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    if not isinstance(drafts, list):
        return {
            "resolution_status": UNKNOWN,
            "draft": None,
            "picked_by_player": {},
            "issues": [{"severity": "error", "kind": "drafts_not_array"}],
        }

    candidates: list[tuple[int, dict[str, Any]]] = []
    league_season = league_state.get("league_season")
    for draft in drafts:
        if not isinstance(draft, dict):
            continue
        if normalize_status(draft.get("DraftType")) not in {"FREE_AGENT", "FREEAGENT"}:
            continue
        season = optional_text(draft.get("Season"))
        if league_season and season and season != league_season:
            continue
        status = normalize_status(draft.get("Status") or draft.get("SleeperStatus"))
        priority = 2 if status in {"DRAFTING", "LIVE"} else 1 if status in {"PREDRAFT", "PRE_DRAFT", "UPCOMING"} else 0
        if priority:
            candidates.append((priority, draft))

    if not candidates:
        phase = normalize_status(league_state.get("league_phase"))
        status = normalize_status(league_state.get("league_status"))
        if "DRAFT" in phase or "DRAFT" in status:
            issues.append({"severity": "error", "kind": "active_fa_draft_missing_during_draft_phase"})
            return {"resolution_status": UNKNOWN, "draft": None, "picked_by_player": {}, "issues": issues}
        return {"resolution_status": "none", "draft": None, "picked_by_player": {}, "issues": issues}

    highest = max(priority for priority, _ in candidates)
    top = [draft for priority, draft in candidates if priority == highest]
    if len(top) != 1:
        issues.append(
            {
                "severity": "error",
                "kind": "ambiguous_active_fa_draft",
                "draft_keys": [optional_text(draft.get("DraftKey")) for draft in top],
            }
        )
        return {"resolution_status": UNKNOWN, "draft": None, "picked_by_player": {}, "issues": issues}

    draft = top[0]
    picks = draft.get("Picks")
    if not isinstance(picks, list):
        issues.append({"severity": "error", "kind": "active_fa_draft_picks_missing"})
        return {"resolution_status": UNKNOWN, "draft": draft, "picked_by_player": {}, "issues": issues}

    picked_by_player: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for pick in picks:
        if not isinstance(pick, dict):
            issues.append({"severity": "warning", "kind": "invalid_draft_pick_record"})
            continue
        player_id = optional_text(pick.get("PlayerID"))
        if not player_id:
            continue
        pick_status = normalize_status(pick.get("Status"))
        if pick_status not in {"PICKED", "COMPLETE", "SELECTED"}:
            issues.append(
                {
                    "severity": "warning",
                    "kind": "assigned_player_with_unexpected_pick_status",
                    "player_id": player_id,
                    "pick_key": optional_text(pick.get("PickKey")),
                    "status": optional_text(pick.get("Status")),
                }
            )
        picked_by_player[player_id].append(pick)

    for player_id, rows in picked_by_player.items():
        if len(rows) > 1:
            issues.append(
                {
                    "severity": "error",
                    "kind": "duplicate_player_assignment_in_active_draft",
                    "player_id": player_id,
                    "pick_keys": [optional_text(row.get("PickKey")) for row in rows],
                }
            )

    return {"resolution_status": "active", "draft": draft, "picked_by_player": picked_by_player, "issues": issues}


def ownership_bucket(owners: list[dict[str, Any]]) -> str | None:
    if len(owners) != 1:
        return None
    sections = set(owners[0].get("roster_sections") or [])
    if "Reserve" in sections:
        return "Reserve"
    if "Taxi" in sections:
        return "Taxi"
    if "Roster" in sections:
        return "Roster"
    return None


def reserve_eligibility(player: dict[str, Any], league_state: dict[str, Any]) -> Eligibility:
    if not league_state.get("complete"):
        return UNKNOWN
    settings = league_state.get("settings") or {}
    if int(optional_number(settings.get("reserve_slots")) or 0) <= 0:
        return False

    injury = player.get("injury") if isinstance(player.get("injury"), dict) else {}
    app_data = player.get("app_data") if isinstance(player.get("app_data"), dict) else {}
    statuses = {normalize_status(injury.get("designation")), normalize_status(app_data.get("status"))}
    statuses.discard("")

    automatic = {
        "IR",
        "INJURED_RESERVE",
        "PUP",
        "PHYSICALLY_UNABLE_TO_PERFORM",
    }
    if statuses & automatic:
        return True

    optional_rules = {
        "OUT": "reserve_allow_out",
        "O": "reserve_allow_out",
        "DOUBTFUL": "reserve_allow_doubtful",
        "D": "reserve_allow_doubtful",
        "SUSPENDED": "reserve_allow_sus",
        "SUS": "reserve_allow_sus",
        "SSPD": "reserve_allow_sus",
        "NA": "reserve_allow_na",
        "NOT_ACTIVE": "reserve_allow_na",
        "DNR": "reserve_allow_dnr",
        "HOLDOUT": "reserve_allow_dnr",
        "COVID": "reserve_allow_cov",
        "COVID_19": "reserve_allow_cov",
        "COV": "reserve_allow_cov",
    }
    for status in statuses:
        setting = optional_rules.get(status)
        if setting and int(optional_number(settings.get(setting)) or 0) == 1:
            return True
    return False


def taxi_window_status(league_state: dict[str, Any], generated_at: str | None) -> str:
    if not league_state.get("complete"):
        return UNKNOWN
    settings = league_state.get("settings") or {}
    if int(optional_number(settings.get("taxi_slots")) or 0) <= 0:
        return "closed_no_slots"

    # Sleeper exposes taxi_deadline as an opaque numeric setting but does not
    # document the integer-to-calendar mapping in its public API contract. Do not
    # invent that mapping. We only call the window open when current canonical
    # league state independently proves we are still in the draft/preseason phase
    # and the materialized source time is before the configured season kickoff.
    phase = normalize_status(league_state.get("league_phase"))
    status = normalize_status(league_state.get("league_status"))
    kickoff = parse_datetime(league_state.get("season_kickoff"))
    generated = parse_datetime(generated_at)
    prelock_phase = "DRAFT" in phase or status in {"DRAFT_SEASON", "PRE_DRAFT", "DRAFTING"}
    if prelock_phase and kickoff is not None and generated is not None and generated < kickoff:
        return "open_preseason"
    if kickoff is not None and generated is not None and generated >= kickoff:
        return "closed_or_locked"
    return UNKNOWN


def taxi_prelock_eligibility(player: dict[str, Any], league_state: dict[str, Any]) -> Eligibility:
    if not league_state.get("complete"):
        return UNKNOWN
    settings = league_state.get("settings") or {}
    slots = int(optional_number(settings.get("taxi_slots")) or 0)
    if slots <= 0:
        return False

    app_data = player.get("app_data") if isinstance(player.get("app_data"), dict) else {}
    years = optional_number(app_data.get("years_experience"))
    if years is None:
        return UNKNOWN
    years_int = int(years)
    allow_vets = int(optional_number(settings.get("taxi_allow_vets")) or 0) == 1
    max_years_raw = optional_number(settings.get("taxi_years"))
    max_years = int(max_years_raw) if max_years_raw is not None else None

    if not allow_vets and years_int > 0:
        return False
    if max_years is not None and max_years > 0 and years_int > max_years:
        return False
    return True


def taxi_eligibility_now(player: dict[str, Any], league_state: dict[str, Any], generated_at: str | None) -> Eligibility:
    prelock = taxi_prelock_eligibility(player, league_state)
    if prelock is False:
        return False
    if prelock == UNKNOWN:
        return UNKNOWN
    window = taxi_window_status(league_state, generated_at)
    if window == "open_preseason":
        return True
    if window in {"closed_no_slots", "closed_or_locked"}:
        return False
    return UNKNOWN


def max_special_assignments(eligibilities: list[tuple[bool, bool]], reserve_capacity: int, taxi_capacity: int) -> int:
    states: set[tuple[int, int, int]] = {(0, 0, 0)}
    for reserve_ok, taxi_ok in eligibilities:
        next_states = set(states)
        for used_reserve, used_taxi, stashed in states:
            if reserve_ok and used_reserve < reserve_capacity:
                next_states.add((used_reserve + 1, used_taxi, stashed + 1))
            if taxi_ok and used_taxi < taxi_capacity:
                next_states.add((used_reserve, used_taxi + 1, stashed + 1))
        states = next_states
    return max(stashed for _, _, stashed in states)


def slot_cost_on_materialization(
    candidate: tuple[Eligibility, Eligibility],
    pending: list[tuple[Eligibility, Eligibility]],
    reserve_capacity: int,
    taxi_capacity: int,
) -> SlotCost:
    reserve_ok, taxi_ok = candidate
    if reserve_ok is False and taxi_ok is False:
        return 1
    if reserve_ok == UNKNOWN or taxi_ok == UNKNOWN:
        return UNKNOWN
    if any(reserve == UNKNOWN or taxi == UNKNOWN for reserve, taxi in pending):
        return UNKNOWN

    known_pending = [(bool(reserve), bool(taxi)) for reserve, taxi in pending]
    before = len(known_pending) - max_special_assignments(known_pending, reserve_capacity, taxi_capacity)
    with_candidate = known_pending + [(bool(reserve_ok), bool(taxi_ok))]
    after = len(with_candidate) - max_special_assignments(with_candidate, reserve_capacity, taxi_capacity)
    delta = after - before
    return 0 if delta <= 0 else 1


def compact_market(player: dict[str, Any]) -> dict[str, Any]:
    """Keep only board-relevant market fields plus source/snapshot metadata.

    The source player-signal rows are intentionally large. Re-copying complete
    source result trees would defeat the purpose of a connector-friendly FA
    board, so this view retains only the values used for ordering/triage and the
    metadata needed to audit their origin and freshness.
    """
    market = player.get("market") if isinstance(player.get("market"), dict) else {}
    output: dict[str, Any] = {}
    for key in ("fantasycalc", "fantasypros"):
        value = market.get(key)
        if not isinstance(value, dict):
            continue
        signals = value.get("signals") if isinstance(value.get("signals"), dict) else {}
        freshness = value.get("freshness") if isinstance(value.get("freshness"), dict) else {}
        provider_view = {
            "source_id": optional_text(value.get("source_id")),
            "provider": optional_text(value.get("provider")),
            "dataset_id": optional_text(value.get("dataset_id")),
            "listed": bool(value.get("listed")),
            "rank": optional_number(signals.get("overall_rank")),
            "percentile": optional_number(signals.get("percentile")),
            "position_rank": signals.get("position_rank"),
            "tier": signals.get("tier"),
            "freshness_status": optional_text(freshness.get("status")) or UNKNOWN,
            "source_timestamp": optional_text(freshness.get("source_timestamp")),
        }
        if key == "fantasycalc":
            provider_view.update(
                {
                    "value": optional_number(signals.get("value")),
                    "trend_30_day": optional_number(signals.get("trend_30_day")),
                    "roster_percent": optional_number(signals.get("roster_percent")),
                    "trade_frequency": optional_number(signals.get("trade_frequency")),
                }
            )
        output[key] = provider_view
    return output


def pick_view(pick: dict[str, Any], league_state: dict[str, Any]) -> dict[str, Any]:
    owner_id = optional_text(pick.get("CurrentOwnerRosterID"))
    team = (league_state.get("team_by_id") or {}).get(owner_id) if owner_id else None
    return {
        "pick_key": optional_text(pick.get("PickKey")),
        "display_pick": optional_text(pick.get("DisplayPick")),
        "overall_pick": optional_number(pick.get("OverallPick")),
        "owner_team_id": owner_id,
        "owner_team_name": optional_text(team.get("Team")) if isinstance(team, dict) else None,
        "status": optional_text(pick.get("Status")),
    }


def draft_materialization_mode(draft_state: dict[str, Any], league_state: dict[str, Any]) -> str:
    if draft_state.get("resolution_status") != "active":
        return "not_applicable"
    picked = draft_state.get("picked_by_player") or {}
    if not picked:
        return "not_observed"
    ownership = league_state.get("ownership") or {}
    observed: list[str] = []
    for player_id, rows in picked.items():
        pick = rows[0]
        owner_id = optional_text(pick.get("CurrentOwnerRosterID"))
        owners = ownership.get(player_id, [])
        if not owners:
            observed.append("pending")
        elif owner_id and len(owners) == 1 and owners[0].get("team_id") == owner_id:
            observed.append("materialized")
        else:
            observed.append("conflict")
    if "conflict" in observed:
        return UNKNOWN
    values = set(observed)
    if values == {"pending"}:
        return "deferred"
    if values == {"materialized"}:
        return "materialized"
    return "mixed"


def active_slot_cost_now(materialization_cost: SlotCost, draft_mode: str, draft_active: bool) -> SlotCost:
    if materialization_cost == 0:
        return 0
    if not draft_active:
        return materialization_cost
    if draft_mode == "deferred":
        return 0
    if draft_mode == "materialized":
        return materialization_cost
    return UNKNOWN


def build(root: Path, config_path: Path) -> dict[str, Any]:
    config = load_json(config_path)
    if not isinstance(config, dict) or config.get("schema_version") != CONFIG_SCHEMA_VERSION:
        raise FaBoardMaterializationError("Unexpected FA-board materialization config schema version")

    sources = config.get("sources") or {}
    player_signals_path = root / sources["player_signals"]
    league_path = root / sources["league"]
    drafts_path = root / sources["drafts"]
    timestamps_path = root / sources["timestamps"]

    player_signals = validate_player_signals(load_json(player_signals_path))
    league = load_json(league_path)
    drafts = load_json(drafts_path)
    timestamps = load_json(timestamps_path)
    if not isinstance(timestamps, dict):
        timestamps = {}

    managed_team_id = str((config.get("managed_team") or {}).get("team_id"))
    league_state = build_league_state(league, managed_team_id)
    draft_state = resolve_active_fa_draft(drafts, league_state)

    generated_at = max_timestamp(
        [
            player_signals.get("generated_at"),
            timestamps.get("League"),
            timestamps.get("Drafts"),
            timestamps.get("Players"),
        ]
    ) or optional_text(player_signals.get("generated_at"))

    quality_issues: list[dict[str, Any]] = []
    quality_issues.extend(league_state.get("issues") or [])
    quality_issues.extend(draft_state.get("issues") or [])
    player_quality = player_signals.get("quality") if isinstance(player_signals.get("quality"), dict) else {}
    if player_quality.get("status") == "error":
        quality_issues.append({"severity": "warning", "kind": "player_signals_upstream_error"})

    source_players = {str(player["player_id"]): player for player in player_signals["players"]}
    ownership = league_state.get("ownership") or {}
    picked_by_player = draft_state.get("picked_by_player") or {}
    draft_mode = draft_materialization_mode(draft_state, league_state)
    draft_active = draft_state.get("resolution_status") == "active"

    managed_team = league_state.get("managed_team")
    managed_reserve = set(managed_team.get("reserve") or []) if managed_team else set()
    managed_taxi = set(managed_team.get("taxi") or []) if managed_team else set()
    settings = league_state.get("settings") or {}
    reserve_slots = int(optional_number(settings.get("reserve_slots")) or 0)
    taxi_slots = int(optional_number(settings.get("taxi_slots")) or 0)
    reserve_capacity = max(0, reserve_slots - len(managed_reserve)) if managed_team else 0
    taxi_capacity = max(0, taxi_slots - len(managed_taxi)) if managed_team else 0

    pending_managed_ids: list[str] = []
    if draft_active:
        for player_id, rows in picked_by_player.items():
            pick = rows[0]
            owner_id = optional_text(pick.get("CurrentOwnerRosterID"))
            if owner_id != managed_team_id:
                continue
            owners = ownership.get(player_id, [])
            already_managed = any(owner.get("team_id") == managed_team_id for owner in owners)
            if not already_managed:
                pending_managed_ids.append(player_id)

    pending_eligibilities: list[tuple[Eligibility, Eligibility]] = []
    for player_id in sorted(set(pending_managed_ids)):
        player = source_players.get(player_id)
        if player is None:
            pending_eligibilities.append((UNKNOWN, UNKNOWN))
            quality_issues.append(
                {"severity": "warning", "kind": "pending_draft_player_missing_from_player_signals", "player_id": player_id}
            )
            continue
        pending_eligibilities.append(
            (
                reserve_eligibility(player, league_state),
                taxi_eligibility_now(player, league_state, generated_at),
            )
        )

    output_players: list[dict[str, Any]] = []
    availability_counts: Counter[str] = Counter()
    position_counts: Counter[str] = Counter()

    for player in player_signals["players"]:
        player_id = str(player["player_id"])
        owners = ownership.get(player_id, [])
        draft_rows = picked_by_player.get(player_id, [])

        if owners:
            availability = "rostered"
        elif not league_state.get("complete"):
            availability = UNKNOWN
        elif draft_state.get("resolution_status") == UNKNOWN:
            availability = UNKNOWN
        elif draft_rows:
            availability = "drafted"
        else:
            availability = "available"

        if draft_state.get("resolution_status") == UNKNOWN:
            player_draft_status = UNKNOWN
        elif draft_state.get("resolution_status") == "none":
            player_draft_status = "no_active_draft"
        elif draft_rows:
            player_draft_status = "picked"
        else:
            player_draft_status = "not_picked"

        reserve_now = reserve_eligibility(player, league_state)
        taxi_prelock = taxi_prelock_eligibility(player, league_state)
        taxi_now = taxi_eligibility_now(player, league_state, generated_at)

        materialization_cost: SlotCost = UNKNOWN
        immediate_cost: SlotCost = UNKNOWN
        if availability == "available":
            if not managed_team or not league_state.get("complete"):
                materialization_cost = UNKNOWN
            else:
                materialization_cost = slot_cost_on_materialization(
                    (reserve_now, taxi_now),
                    pending_eligibilities,
                    reserve_capacity,
                    taxi_capacity,
                )
            immediate_cost = active_slot_cost_now(materialization_cost, draft_mode, draft_active)

        owner_team_id = owners[0].get("team_id") if len(owners) == 1 else None
        owner_team_name = owners[0].get("team_name") if len(owners) == 1 else None
        pick = draft_rows[0] if len(draft_rows) == 1 else None
        market = compact_market(player)
        source_freshness = {
            "player_signals_generated_at": optional_text(player_signals.get("generated_at")),
            "market": {
                key: value.get("freshness_status", UNKNOWN)
                for key, value in market.items()
                if isinstance(value, dict)
            },
        }
        injury = player.get("injury") if isinstance(player.get("injury"), dict) else {}

        row = {
            "player_id": player_id,
            "player_name": optional_text(player.get("name")),
            "position": optional_text(player.get("position")),
            "nfl_team": optional_text(player.get("nfl_team")),
            "availability_status": availability,
            "owner_team_id": owner_team_id,
            "owner_team_name": owner_team_name,
            "roster_bucket": ownership_bucket(owners),
            "ownership_teams": owners,
            "current_fa_draft_status": player_draft_status,
            "current_fa_draft_pick": pick_view(pick, league_state) if pick is not None else None,
            "player_status": optional_text((player.get("app_data") or {}).get("status")) if isinstance(player.get("app_data"), dict) else None,
            "injury_status": optional_text(injury.get("coverage_status")),
            "injury_designation": optional_text(injury.get("designation")),
            "reserve_eligible_now": reserve_now,
            "taxi_eligible_now": taxi_now,
            "taxi_prelock_eligible": taxi_prelock,
            "active_slot_cost_now": immediate_cost,
            "active_slot_cost_on_materialization": materialization_cost,
            "market": market,
            "source_freshness": source_freshness,
        }
        output_players.append(row)
        availability_counts[availability] += 1
        position_counts[str(row["position"] or "unknown")] += 1

    output_players.sort(
        key=lambda row: (
            str(row.get("position") or ""),
            str(row.get("player_name") or "").casefold(),
            str(row["player_id"]),
        )
    )

    materialized_controlled: set[str] = set()
    materialized_active: set[str] = set()
    managed_name = None
    if managed_team:
        materialized_controlled = set(managed_team["roster"]) | set(managed_team["taxi"]) | set(managed_team["reserve"])
        materialized_active = materialized_controlled - set(managed_team["taxi"]) - set(managed_team["reserve"])
        managed_name = managed_team.get("team_name")
    pending_unique = sorted(set(pending_managed_ids))
    effective_controlled = materialized_controlled | set(pending_unique)

    current_draft = draft_state.get("draft") if isinstance(draft_state.get("draft"), dict) else None
    source_records = {
        "league": {
            "path": sources["league"],
            "content_sha256": source_hash(league_path),
            "source_timestamp": optional_text(timestamps.get("League")),
            "complete_for_negative_ownership": bool(league_state.get("complete")),
        },
        "drafts": {
            "path": sources["drafts"],
            "content_sha256": source_hash(drafts_path),
            "source_timestamp": optional_text(timestamps.get("Drafts")),
            "resolution_status": draft_state.get("resolution_status"),
        },
        "player_signals": {
            "path": sources["player_signals"],
            "content_sha256": source_hash(player_signals_path),
            "source_timestamp": optional_text(player_signals.get("generated_at")),
            "input_fingerprint": optional_text(player_signals.get("input_fingerprint")),
        },
        "timestamps": {
            "path": sources["timestamps"],
            "content_sha256": source_hash(timestamps_path),
            "source_timestamp": max_timestamp(timestamps.values()),
        },
    }

    fingerprint_payload = {
        "config": config,
        "sources": source_records,
        "active_draft_key": optional_text(current_draft.get("DraftKey")) if current_draft else None,
        "managed_team_id": managed_team_id,
    }

    quality_status = "error" if any(issue.get("severity") == "error" for issue in quality_issues) else "warning" if quality_issues else "ok"
    result = {
        "schema_version": SCHEMA_VERSION,
        "dataset_id": DATASET_ID,
        "generated_at": generated_at,
        "input_fingerprint": sha256_text(canonical_json(fingerprint_payload)),
        "managed_team": {"team_id": managed_team_id, "name": managed_name},
        "sources": source_records,
        "current_fa_draft": {
            "resolution_status": draft_state.get("resolution_status"),
            "draft_key": optional_text(current_draft.get("DraftKey")) if current_draft else None,
            "season": optional_text(current_draft.get("Season")) if current_draft else None,
            "status": optional_text(current_draft.get("Status")) if current_draft else None,
            "materialization_mode": draft_mode,
            "picked_player_count": len(picked_by_player),
        },
        "managed_team_capacity": {
            "active_roster_capacity": league_state.get("active_capacity"),
            "materialized_roster_count": len(materialized_controlled),
            "materialized_active_roster_count": len(materialized_active),
            "pending_controlled_draft_count": len(pending_unique),
            "effective_controlled_roster_count": len(effective_controlled),
            "reserve_slots": reserve_slots,
            "reserve_occupied": len(managed_reserve),
            "reserve_free_before_pending": reserve_capacity,
            "taxi_slots": taxi_slots,
            "taxi_occupied": len(managed_taxi),
            "taxi_free_before_pending": taxi_capacity,
            "taxi_window_status": taxi_window_status(league_state, generated_at),
            "pending_special_capacity_exact": not any(
                reserve == UNKNOWN or taxi == UNKNOWN for reserve, taxi in pending_eligibilities
            ),
        },
        "population": {
            "player_count": len(output_players),
            "positions": dict(sorted(position_counts.items())),
            "availability": dict(sorted(availability_counts.items())),
        },
        "players": output_players,
        "quality": {
            "status": quality_status,
            "issue_count": len(quality_issues),
            "issues": quality_issues,
            "availability_fail_closed": True,
        },
    }
    validate_output(result)
    return result


def validate_output(data: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "dataset_id",
        "generated_at",
        "input_fingerprint",
        "managed_team",
        "sources",
        "current_fa_draft",
        "managed_team_capacity",
        "population",
        "players",
        "quality",
    }
    missing = required - data.keys()
    if missing:
        raise FaBoardMaterializationError(f"Output missing required keys: {sorted(missing)}")
    if data["schema_version"] != SCHEMA_VERSION or data["dataset_id"] != DATASET_ID:
        raise FaBoardMaterializationError("Unexpected FA-board output identity")
    players = data["players"]
    ids = [str(player.get("player_id")) for player in players]
    if len(ids) != len(set(ids)):
        raise FaBoardMaterializationError("FA-board output contains duplicate player IDs")
    if data["population"]["player_count"] != len(players):
        raise FaBoardMaterializationError("FA-board population count does not match players array")
    for player in players:
        status = player.get("availability_status")
        if status == "available":
            if player.get("owner_team_id") is not None or player.get("current_fa_draft_status") == "picked":
                raise FaBoardMaterializationError("Available player has blocking ownership or draft state")
        if player.get("active_slot_cost_now") not in {0, 1, UNKNOWN}:
            raise FaBoardMaterializationError("Invalid active_slot_cost_now")
        if player.get("active_slot_cost_on_materialization") not in {0, 1, UNKNOWN}:
            raise FaBoardMaterializationError("Invalid active_slot_cost_on_materialization")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("fantasy-management/automation/fa-board-materialization.json"),
    )
    parser.add_argument("--check", action="store_true", help="Build and validate without writing output")
    args = parser.parse_args()

    root = args.root.resolve()
    config_path = args.config if args.config.is_absolute() else root / args.config
    config = load_json(config_path)
    result = build(root, config_path)
    if args.check:
        print(
            "Validated FA-board readmodel with {} players; availability={}; quality={}.".format(
                result["population"]["player_count"],
                result["population"]["availability"],
                result["quality"]["status"],
            )
        )
        return 0

    output_path = root / config["output"]["fa_board_readmodel"]
    write_json(output_path, result)
    print(
        "Wrote {} with {} players; availability={}; quality={}.".format(
            output_path.relative_to(root),
            result["population"]["player_count"],
            result["population"]["availability"],
            result["quality"]["status"],
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
