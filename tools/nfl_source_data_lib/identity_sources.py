from __future__ import annotations

import re
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from .common import Dataset, canonical_player_id, clean, iter_csv, load_json
from .identity_model import (
    ANCHOR_ID_KEYS,
    ATTACH_ID_KEYS,
    SLEEPER_PLAYERS_SOURCE,
    IdentityCandidate,
    ids_from_ff,
    ids_from_players,
)


_VALID_GSIS_PLAYER_ID = re.compile(r"^00-\d{7}$")
_FF_BIRTHDATE_CORRECTION_MIN_SHARED_ANCHORS = 4


def _player_birthdate_anchors(player_rows: list[dict[str, str]]) -> dict[tuple[str, str], set[str]]:
    anchors: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in player_rows:
        birth_date = clean(row.get("birth_date"))
        if not birth_date:
            continue
        for key, value in ids_from_players(row).items():
            if key in ANCHOR_ID_KEYS:
                anchors[(key, value)].add(birth_date)
    return anchors


def _corroborated_ff_birthdate_correction(
    ids: dict[str, str],
    birth_date: str | None,
    anchors: dict[tuple[str, str], set[str]],
) -> str | None:
    """Return the authoritative nflverse.players DOB for a strongly anchored crosswalk row.

    A current crosswalk DOB mismatch is still fail-closed by default. The only
    bounded exception is when at least four independent strong provider IDs in
    that same row each resolve to one identical nflverse.players birth date and no
    resolved strong anchor points anywhere else. Raw evidence is not mutated; this
    only normalizes the in-memory identity candidate used for reconciliation.
    """

    if not birth_date:
        return None

    resolved_birth_dates: set[str] = set()
    shared_anchor_count = 0
    for key in ANCHOR_ID_KEYS:
        value = ids.get(key)
        if not value:
            continue
        expected = anchors.get((key, value), set())
        if not expected:
            continue
        if len(expected) != 1:
            return None
        resolved_birth_dates.update(expected)
        shared_anchor_count += 1

    if (
        shared_anchor_count < _FF_BIRTHDATE_CORRECTION_MIN_SHARED_ANCHORS
        or len(resolved_birth_dates) != 1
    ):
        return None

    authoritative_birth_date = next(iter(resolved_birth_dates))
    if authoritative_birth_date == birth_date:
        return None
    return authoritative_birth_date


def _is_weak_only(ids: dict[str, str]) -> bool:
    if not ids:
        return False
    strong_or_attach = set(ANCHOR_ID_KEYS) | set(ATTACH_ID_KEYS)
    return not any(key in strong_or_attach for key in ids)


def _replay_signature(
    ids: dict[str, str],
    birth_date: str | None,
    position: str | None,
    name: str | None,
) -> tuple[tuple[tuple[str, str], ...], str, str, str] | None:
    """Return exact canonical-visible evidence for weak-only replay.

    This signature is never used to merge two current candidates. It only lets an
    unchanged weak-only current candidate reconnect to one canonical identity that
    this pipeline already materialized previously. Provider names remain
    non-authoritative: name participates only as an exact replay discriminator.
    """

    if not _is_weak_only(ids):
        return None
    return (
        tuple(sorted((key, value) for key, value in ids.items())),
        clean(birth_date) or "",
        clean(position) or "",
        (clean(name) or "").casefold(),
    )


def _existing_weak_replay_index(
    repo_root: Path,
) -> dict[tuple[tuple[tuple[str, str], ...], str, str, str], set[str]]:
    payload = load_json(repo_root / "source-data/nfl/identities/players.json", {}) or {}
    index: dict[tuple[tuple[tuple[str, str], ...], str, str, str], set[str]] = defaultdict(set)
    for row in payload.get("Players", []) or []:
        ids = {
            key: value
            for key, raw_value in (row.get("IDs") or {}).items()
            if (value := clean(raw_value))
        }
        signature = _replay_signature(
            ids,
            clean(row.get("BirthDate")),
            clean(row.get("Position")),
            clean(row.get("Name")),
        )
        internal_id = canonical_player_id(row)
        if signature is not None and internal_id:
            index[signature].add(internal_id)
    return index


def _replay_existing_weak_identity(
    replay_index: dict[tuple[tuple[tuple[str, str], ...], str, str, str], set[str]],
    ids: dict[str, str],
    birth_date: str | None,
    position: str | None,
    name: str | None,
) -> str | None:
    signature = _replay_signature(ids, birth_date, position, name)
    if signature is None:
        return None
    owners = sorted(replay_index.get(signature, set()))
    return owners[0] if len(owners) == 1 else None


def _persisted_player_stats_gsis_ids(dataset: Dataset) -> set[str]:
    """Return real GSIS player IDs observed in persisted nflverse player-stat raws.

    Historical player stats are authoritative evidence that a GSIS identity took
    part in an NFL game even when that retired player disappeared from today's
    nflverse players/ff-player-ids snapshots. Only the real ``00-#######`` GSIS
    namespace is accepted here; upstream sentinels such as ``0`` and synthetic
    ``XX-*`` values are deliberately excluded and must be handled explicitly.
    """

    if not dataset.is_season_partitioned:
        return set()
    pattern = dataset.raw_path.name.replace("{season}", "*")
    ids: set[str] = set()
    for path in sorted(dataset.raw_path.parent.glob(pattern)):
        if not path.is_file():
            continue
        for row in iter_csv(path):
            gsis = clean(row.get("player_id"))
            if gsis and _VALID_GSIS_PLAYER_ID.fullmatch(gsis):
                ids.add(gsis)
    return ids


def raw_identity_candidates(
    repo_root: Path,
    datasets: dict[str, Dataset],
) -> tuple[list[IdentityCandidate], list[dict[str, str]], list[IdentityCandidate | None], list[dict[str, Any]]]:
    existing_replay_index = _existing_weak_replay_index(repo_root)
    candidates: list[IdentityCandidate] = []
    player_rows = list(iter_csv(datasets["nflverse.players"].raw_path))
    for row in player_rows:
        ids = ids_from_players(row)
        if not ids:
            continue
        name = clean(row.get("display_name"))
        birth_date = clean(row.get("birth_date"))
        position = clean(row.get("position"))
        candidates.append(
            IdentityCandidate(
                ids=ids,
                name=name,
                first_name=clean(row.get("first_name")) or clean(row.get("common_first_name")),
                last_name=clean(row.get("last_name")),
                birth_date=birth_date,
                position=position,
                latest_team=clean(row.get("latest_team")),
                source="nflverse.players",
                priority=10,
                existing_internal_id=_replay_existing_weak_identity(
                    existing_replay_index,
                    ids,
                    birth_date,
                    position,
                    name,
                ),
            )
        )

    anchors = _player_birthdate_anchors(player_rows)
    ff_rows: list[dict[str, str]] = []
    ff_candidates: list[IdentityCandidate | None] = []
    source_conflicts: list[dict[str, Any]] = []

    for row in iter_csv(datasets["nflverse.ff-player-ids"].raw_path):
        ff_rows.append(row)
        raw_ids = ids_from_ff(row)
        ids = dict(raw_ids)
        name = clean(row.get("name"))
        birth_date = clean(row.get("birthdate"))
        candidate_birth_date = birth_date
        position = clean(row.get("position"))
        conflicting_anchors: list[dict[str, Any]] = []
        matching_anchors: list[dict[str, Any]] = []

        if birth_date:
            for key in ANCHOR_ID_KEYS:
                value = raw_ids.get(key)
                if not value:
                    continue
                expected_birth_dates = sorted(anchors.get((key, value), set()))
                if not expected_birth_dates:
                    continue
                detail = {
                    "Provider": key,
                    "ID": value,
                    "NFLVerseBirthDates": expected_birth_dates,
                }
                if birth_date in expected_birth_dates:
                    matching_anchors.append(detail)
                else:
                    conflicting_anchors.append(detail)

        if conflicting_anchors:
            corrected_birth_date = _corroborated_ff_birthdate_correction(
                raw_ids,
                birth_date,
                anchors,
            )
            if corrected_birth_date:
                candidate_birth_date = corrected_birth_date
                source_conflicts.append(
                    {
                        "Source": "nflverse.ff-player-ids",
                        "Reason": "birthdate_conflict_with_nflverse_players",
                        "QuarantineScope": "birthdate-only",
                        "Resolution": "strong_anchor_consensus",
                        "ResolvedBirthDate": corrected_birth_date,
                        "MFLID": raw_ids.get("MFL"),
                        "Name": name,
                        "BirthDate": birth_date,
                        "Position": position,
                        "DraftYear": clean(row.get("draft_year")),
                        "ConflictingAnchors": conflicting_anchors,
                        "MatchingAnchors": matching_anchors,
                        "SuppressedIDs": {},
                    }
                )
            else:
                conflicting_keys = {item["Provider"] for item in conflicting_anchors}
                if matching_anchors:
                    # One exact-birthdate anchor still identifies the person. Keep
                    # unrelated provider mappings and suppress only contradicted anchors.
                    suppressed = {
                        key: value
                        for key, value in raw_ids.items()
                        if key in conflicting_keys
                    }
                    ids = {
                        key: value
                        for key, value in raw_ids.items()
                        if key not in conflicting_keys
                    }
                    quarantine_scope = "mapping"
                else:
                    # No authoritative NFL anchor corroborates this row's birth date.
                    # Do not let provider-only IDs bootstrap a person from contradicted evidence.
                    suppressed = {key: value for key, value in raw_ids.items() if key != "MFL"}
                    ids = {"MFL": raw_ids["MFL"]} if raw_ids.get("MFL") else {}
                    quarantine_scope = "row"

                source_conflicts.append(
                    {
                        "Source": "nflverse.ff-player-ids",
                        "Reason": "birthdate_conflict_with_nflverse_players",
                        "QuarantineScope": quarantine_scope,
                        "MFLID": raw_ids.get("MFL"),
                        "Name": name,
                        "BirthDate": birth_date,
                        "Position": position,
                        "DraftYear": clean(row.get("draft_year")),
                        "ConflictingAnchors": conflicting_anchors,
                        "MatchingAnchors": matching_anchors,
                        "SuppressedIDs": suppressed,
                    }
                )

        candidate = None
        if ids:
            candidate = IdentityCandidate(
                ids=ids,
                name=name,
                first_name=None,
                last_name=None,
                birth_date=candidate_birth_date,
                position=position,
                latest_team=clean(row.get("team")),
                source="nflverse.ff-player-ids",
                priority=20,
                existing_internal_id=_replay_existing_weak_identity(
                    existing_replay_index,
                    ids,
                    candidate_birth_date,
                    position,
                    name,
                ),
            )
            candidates.append(candidate)
        ff_candidates.append(candidate)

    stats_dataset = datasets.get("nflverse.player-stats")
    if stats_dataset is not None:
        claimed_gsis = {
            candidate.ids["GSIS"]
            for candidate in candidates
            if candidate.ids.get("GSIS")
        }
        for gsis in sorted(_persisted_player_stats_gsis_ids(stats_dataset) - claimed_gsis):
            candidates.append(
                IdentityCandidate(
                    ids={"GSIS": gsis},
                    name=None,
                    first_name=None,
                    last_name=None,
                    birth_date=None,
                    position=None,
                    latest_team=None,
                    source="nflverse.player-stats",
                    priority=40,
                )
            )

    return candidates, ff_rows, ff_candidates, source_conflicts


# Fantasy positions of the app population (same set as Get-AppFantasyPosition).
_APP_FANTASY_POSITIONS = ("QB", "RB", "WR", "TE", "K")
# Provider spellings of the same NFL franchise that differ between Sleeper and
# nflverse. Interim table until the F3a team registry owns these aliases.
_TEAM_ALIASES = {"LAR": "LA", "WSH": "WAS"}


def normalize_nfl_team(team: str | None) -> str | None:
    value = clean(team)
    if value is None:
        return None
    value = value.upper()
    return _TEAM_ALIASES.get(value, value)


def _sleeper_fantasy_position(row: dict[str, Any]) -> str | None:
    primary = (clean(row.get("position")) or "").upper()
    if primary in _APP_FANTASY_POSITIONS:
        return primary
    for value in row.get("fantasy_positions") or []:
        candidate = (clean(value) or "").upper()
        if candidate in _APP_FANTASY_POSITIONS:
            return candidate
    return None


def _valid_iso_date(value: str | None) -> bool:
    if not value:
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _current_roster_rows(
    datasets: dict[str, Dataset],
    observation_season: int,
) -> list[dict[str, str]]:
    """Latest weekly row per GSIS from the persisted current-season nflverse roster.

    Returns an empty list when the dataset or the current-season partition is not
    available (for example before the season roster is published); the attribute
    bridge is then simply inactive and unmatched Sleeper players stay provisional.
    """
    dataset = datasets.get("nflverse.rosters")
    if dataset is None or not dataset.is_season_partitioned:
        return []
    path = dataset.raw_path.parent / dataset.raw_path.name.replace(
        "{season}", str(observation_season)
    )
    if not path.is_file():
        return []
    latest: dict[str, tuple[int, dict[str, str]]] = {}
    for row in iter_csv(path):
        gsis = clean(row.get("gsis_id"))
        if not gsis or not clean(row.get("team")):
            continue
        try:
            week = int(clean(row.get("week")) or 0)
        except ValueError:
            week = 0
        previous = latest.get(gsis)
        if previous is None or week >= previous[0]:
            latest[gsis] = (week, row)
    return [row for _, (_, row) in sorted(latest.items())]


def sleeper_player_candidates(
    repo_root: Path,
    datasets: dict[str, Dataset],
    observation_season: int,
    *,
    external_anchor_candidates: dict[tuple[str, str], list[IdentityCandidate]],
    persisted_sleeper_ids: set[str],
    other_sleeper_ids: set[str],
) -> tuple[list[IdentityCandidate], list[dict[str, Any]]]:
    """Identity candidates from the persisted Sleeper platform snapshot.

    Replaces the former ``app.Players`` evidence (#347 H1a). The snapshot is
    provider evidence, not an app output, so the identity builder no longer
    depends on ``public/data/Players.json``.

    Population: Sleeper records with an app fantasy position and a valid birth
    date that either carry a current NFL team or already have a persisted Sleeper
    mapping. Records outside that population neither create nor attach identities.

    Sleeper's birth date is descriptive only: it never vetoes or enables a merge
    except through the bridge below, because it can differ from nflverse.

    Evidence: the Sleeper ID, plus Sleeper's ``espn_id`` only for a new Sleeper ID
    and only when current external evidence corroborates it without contradicting
    the Sleeper ID (same rule as the former app bridge).
    Provider IDs such as Sleeper's ``gsis_id`` are deliberately not used.

    Rule ``sleeperCurrentRosterAttributeBridge``: a record whose Sleeper ID is new
    (no other source and no persisted identity holds it) may attach to exactly one
    current nflverse roster record when exact birth date, current team and
    position match, the match is unique on both sides and no provider ID
    contradicts it. Names play no role. Anything else stays provisional.
    """
    dataset = datasets.get("sleeper.players")
    if dataset is None or not dataset.raw_path.exists():
        return [], []
    raw = load_json(dataset.raw_path)
    if not isinstance(raw, dict):
        raise ValueError("Sleeper players source must be an object keyed by player_id")

    candidates: list[IdentityCandidate] = []
    for object_key, row in sorted(raw.items(), key=lambda item: str(item[0])):
        if not isinstance(row, dict):
            continue
        sleeper_id = clean(row.get("player_id")) or clean(object_key)
        if not sleeper_id:
            continue
        position = _sleeper_fantasy_position(row)
        birth_date = clean(row.get("birth_date"))
        if position is None or not _valid_iso_date(birth_date):
            continue
        team = normalize_nfl_team(row.get("team"))
        if team is None and sleeper_id not in persisted_sleeper_ids:
            continue
        ids = {"Sleeper": sleeper_id}
        espn = clean(row.get("espn_id"))
        known_sleeper_id = sleeper_id in persisted_sleeper_ids or sleeper_id in other_sleeper_ids
        # A Sleeper ID that other evidence already holds identifies the person on
        # its own; Sleeper's ESPN claim may contradict that holder and must not
        # create a second owner of the Sleeper ID. It only bridges new Sleeper IDs.
        if espn and not known_sleeper_id and external_anchor_candidates.get(("ESPN", espn)):
            external_values = {
                value
                for candidate in external_anchor_candidates[("ESPN", espn)]
                if (value := clean(candidate.ids.get("Sleeper")))
            }
            if not external_values - {sleeper_id}:
                ids["ESPN"] = espn
        candidates.append(
            IdentityCandidate(
                ids=ids,
                name=clean(row.get("full_name")),
                first_name=clean(row.get("first_name")),
                last_name=clean(row.get("last_name")),
                birth_date=None,
                descriptive_birth_date=birth_date,
                position=position,
                latest_team=team,
                source=SLEEPER_PLAYERS_SOURCE,
                priority=30,
            )
        )

    diagnostics: list[dict[str, Any]] = []
    roster_rows = _current_roster_rows(datasets, observation_season)
    roster_by_key: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    for row in roster_rows:
        birth_date = clean(row.get("birth_date"))
        team = normalize_nfl_team(row.get("team"))
        position = (clean(row.get("position")) or "").upper()
        if birth_date and team and position:
            roster_by_key[(birth_date, team, position)].append(clean(row.get("gsis_id")) or "")

    sleeper_by_key: dict[tuple[str, str, str], list[IdentityCandidate]] = defaultdict(list)
    for candidate in candidates:
        if (
            candidate.ids["Sleeper"] in other_sleeper_ids
            or candidate.ids["Sleeper"] in persisted_sleeper_ids
            or "ESPN" in candidate.ids
            or not candidate.latest_team
        ):
            continue
        sleeper_by_key[
            (
                candidate.descriptive_birth_date or "",
                candidate.latest_team,
                candidate.position or "",
            )
        ].append(candidate)

    for key, bridged in sorted(sleeper_by_key.items()):
        gsis_values = roster_by_key.get(key, [])
        if len(gsis_values) == 1 and len(bridged) == 1:
            bridged[0].bridge_gsis = gsis_values[0]
        elif gsis_values:
            diagnostics.append(
                {
                    "Source": "identity-resolution",
                    "Reason": "sleeper_attribute_bridge_not_unique",
                    "BirthDate": key[0],
                    "Team": key[1],
                    "Position": key[2],
                    "SleeperIDs": sorted(item.ids["Sleeper"] for item in bridged),
                    "RosterGSISIDs": sorted(gsis_values),
                }
            )
    return candidates, diagnostics
