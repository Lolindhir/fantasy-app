#!/usr/bin/env python3
"""Canonical League draft adapter for Fantasy Management consumers.

Reads the current season's drafts from `source-data/leagues/<id>/seasons/<season>/drafts.json`
and exposes them in the draft/pick shape the FA-board builder already consumes
(DraftKey, DraftType, Status, Picks[PlayerID, CurrentOwnerRosterID, ...]).

Canonical drafts carry no DraftType. The type is resolved fail-closed from
`Metadata.json` Drafts.Types: an explicit `SleeperDraftIDs` binding for the
season is authoritative; an unbound draft is only classified by the same
free-agent/rookie keyword rule the App generator applies to unbound Sleeper
drafts. Anything else stays unclassified (DraftType None) and the caller must
treat an unclassified open draft as unknown.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any


class CanonicalDraftError(RuntimeError):
    """Raised when canonical draft evidence is missing, invalid or ambiguous."""


_FA_PATTERN = re.compile(r"free[_\s-]?agent|freeagent|waiver|\bfa\b")
_ROOKIE_PATTERN = re.compile(r"rookie")
_STATUS_LABELS = {"complete": "Complete", "drafting": "Drafting", "pre_draft": "PreDraft"}


def drafts_path(root: Path, canonical_league_id: str, season: int) -> Path:
    return (
        root / "source-data" / "leagues" / canonical_league_id / "seasons" / str(season) / "drafts.json"
    )


def _read_json(path: Path) -> Any:
    if not path.is_file():
        raise CanonicalDraftError(f"Required file is missing: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CanonicalDraftError(f"Could not read valid JSON from {path}: {exc}") from exc


def _provider_draft_id(draft: dict[str, Any]) -> str | None:
    rows = [
        row
        for row in (draft.get("ProviderMappings") or [])
        if isinstance(row, dict) and row.get("Provider") == "Sleeper" and row.get("ProviderDraftID")
    ]
    return str(rows[0]["ProviderDraftID"]) if len(rows) == 1 else None


def _draft_code(draft_type: str, instance: int) -> str:
    return draft_type if instance == 1 else f"{draft_type}_{instance}"


def _configured_types(metadata: Any) -> list[dict[str, Any]]:
    types = ((metadata or {}).get("Drafts") or {}).get("Types") if isinstance(metadata, dict) else None
    if not isinstance(types, list) or not types:
        raise CanonicalDraftError("Metadata.json Drafts.Types is missing.")
    result: list[dict[str, Any]] = []
    for row in types:
        if not isinstance(row, dict) or not row.get("DraftType"):
            raise CanonicalDraftError("Metadata.json Drafts.Types contains an invalid entry.")
        result.append(row)
    return result


def _classify(drafts: list[dict[str, Any]], season: int, types: list[dict[str, Any]]) -> dict[int, tuple[str, int]]:
    """Return {index in drafts: (DraftType, DraftInstance)} for classifiable drafts."""

    result: dict[int, tuple[str, int]] = {}
    free_types = list(types)
    ids = [_provider_draft_id(d) for d in drafts]
    for cfg in types:
        bound = (cfg.get("SleeperDraftIDs") or {}).get(str(season))
        if not bound:
            continue
        matches = [i for i, draft_id in enumerate(ids) if draft_id == str(bound)]
        if len(matches) != 1:
            raise CanonicalDraftError(
                f"Configured draft {bound!r} for season {season} was not found exactly once in canonical drafts."
            )
        result[matches[0]] = (str(cfg["DraftType"]), int(cfg.get("DraftInstance") or 1))
        free_types.remove(cfg)

    unbound = sorted(
        (i for i in range(len(drafts)) if i not in result),
        key=lambda i: (drafts[i].get("StartTime") is None, drafts[i].get("StartTime") or 0, ids[i] or ""),
    )
    for index in unbound:
        draft = drafts[index]
        meta = draft.get("Metadata") if isinstance(draft.get("Metadata"), dict) else {}
        text = " ".join(
            str(part)
            for part in [draft.get("Type"), draft.get("Status"), draft.get("Season"), *meta.values()]
            if part not in (None, "")
        ).lower()
        wanted = "Free_Agent" if _FA_PATTERN.search(text) else "Rookie" if _ROOKIE_PATTERN.search(text) else None
        if wanted is None:
            continue
        candidates = sorted(
            (c for c in free_types if c.get("DraftType") == wanted),
            key=lambda c: (int(c.get("DraftInstance") or 1), int(c.get("DraftNo") or 0)),
        )
        if not candidates:
            continue
        result[index] = (wanted, int(candidates[0].get("DraftInstance") or 1))
        free_types.remove(candidates[0])
    return result


def _convert_draft(
    draft: dict[str, Any],
    *,
    season: int,
    draft_type: str,
    instance: int,
    roster_to_team: dict[str, int],
) -> dict[str, Any]:
    code = _draft_code(draft_type, instance)
    draft_key = f"{season}_{code}"
    status_raw = str(draft.get("Status") or "")
    settings = draft.get("Settings") if isinstance(draft.get("Settings"), dict) else {}
    slots = draft.get("SlotToRoster")
    if not isinstance(slots, list) or not slots:
        raise CanonicalDraftError(f"Draft {draft_key} has no SlotToRoster.")
    team_count = len(slots)
    if settings.get("teams") not in (None, team_count):
        raise CanonicalDraftError(f"Draft {draft_key} team count disagrees with SlotToRoster.")
    draft_format = str(draft.get("Type") or "")
    if draft_format not in {"linear", "snake"} or settings.get("reversal_round") not in (None, 0):
        raise CanonicalDraftError(f"Draft {draft_key} has unsupported format {draft_format!r}.")

    slot_owner: dict[int, int] = {}
    for row in slots:
        team_id = roster_to_team.get(str(row.get("CanonicalLeagueRosterID")))
        if team_id is None:
            raise CanonicalDraftError(f"Draft {draft_key} slot roster is not a mapped canonical roster.")
        slot_owner[int(row["Slot"])] = team_id

    picks: list[dict[str, Any]] = []
    for raw in draft.get("Picks") or []:
        player = raw.get("Player") if isinstance(raw.get("Player"), dict) else None
        if not player:
            continue
        sleeper_ids = [
            m.get("ProviderPlayerID")
            for m in (player.get("ProviderMappings") or [])
            if isinstance(m, dict) and m.get("Provider") == "Sleeper" and m.get("ProviderPlayerID")
        ]
        if len(sleeper_ids) != 1:
            raise CanonicalDraftError(f"Draft {draft_key} pick {raw.get('PickNo')} has no unique Sleeper player ID.")
        owner = roster_to_team.get(str(raw.get("CanonicalLeagueRosterID")))
        if owner is None:
            raise CanonicalDraftError(f"Draft {draft_key} pick {raw.get('PickNo')} owner roster is not mapped.")
        overall = int(raw["PickNo"])
        rnd = math.ceil(overall / team_count)
        pos = overall - (rnd - 1) * team_count
        slot = team_count - pos + 1 if draft_format == "snake" and rnd % 2 == 0 else pos
        original = slot_owner.get(slot)
        if original is None:
            raise CanonicalDraftError(f"Draft {draft_key} pick {overall} slot {slot} has no roster.")
        picks.append(
            {
                "PickKey": f"{draft_key}_R{rnd}_OO{original}",
                "DisplayPick": f"{rnd}.{pos:02d}",
                "OverallPick": overall,
                "Round": rnd,
                "PositionInRound": pos,
                "OriginalOwnerRosterID": original,
                "CurrentOwnerRosterID": owner,
                "PlayerID": str(sleeper_ids[0]),
                "Status": "Picked",
            }
        )
    picks.sort(key=lambda p: p["OverallPick"])
    return {
        "DraftKey": draft_key,
        "Season": str(season),
        "DraftType": draft_type,
        "DraftInstance": instance,
        "DraftCode": code,
        "SleeperDraftID": _provider_draft_id(draft),
        "SleeperStatus": status_raw,
        "Status": _STATUS_LABELS.get(status_raw, status_raw),
        "Picks": picks,
    }


def load_canonical_current_drafts(
    root: Path,
    *,
    canonical_league_id: str,
    season: int,
    ownership_teams: list[dict[str, Any]],
    metadata: Any,
) -> list[dict[str, Any]]:
    """Return current-season drafts in builder shape, or raise CanonicalDraftError.

    Free-agent and unclassified open drafts are fully converted; other classified
    drafts (for example the rookie draft) are returned without picks because the
    FA board never reads them. Unclassified drafts that are not complete carry
    DraftType None so the caller can fail closed.
    """

    raw = _read_json(drafts_path(root, canonical_league_id, season))
    if not isinstance(raw, list):
        raise CanonicalDraftError("Canonical drafts.json must be an array.")
    drafts = [d for d in raw if isinstance(d, dict)]
    if len(drafts) != len(raw):
        raise CanonicalDraftError("Canonical drafts.json contains a non-object entry.")
    for draft in drafts:
        if int(draft.get("Season", -1)) != int(season):
            raise CanonicalDraftError("Canonical drafts.json contains a draft of another season.")

    roster_to_team = {
        str(t["CanonicalLeagueRosterID"]): int(t["TeamID"])
        for t in ownership_teams
        if isinstance(t, dict) and t.get("CanonicalLeagueRosterID") and t.get("TeamID") is not None
    }
    classification = _classify(drafts, season, _configured_types(metadata))

    result: list[dict[str, Any]] = []
    for index, draft in enumerate(drafts):
        resolved = classification.get(index)
        if resolved is None:
            status = str(draft.get("Status") or "")
            result.append(
                {
                    "DraftKey": None,
                    "Season": str(season),
                    "DraftType": None,
                    "SleeperDraftID": _provider_draft_id(draft),
                    "SleeperStatus": status,
                    "Status": _STATUS_LABELS.get(status, status),
                    "Picks": [],
                }
            )
            continue
        draft_type, instance = resolved
        if draft_type == "Free_Agent":
            result.append(
                _convert_draft(
                    draft,
                    season=season,
                    draft_type=draft_type,
                    instance=instance,
                    roster_to_team=roster_to_team,
                )
            )
        else:
            status = str(draft.get("Status") or "")
            result.append(
                {
                    "DraftKey": f"{season}_{_draft_code(draft_type, instance)}",
                    "Season": str(season),
                    "DraftType": draft_type,
                    "SleeperStatus": status,
                    "Status": _STATUS_LABELS.get(status, status),
                    "Picks": [],
                }
            )
    return result
