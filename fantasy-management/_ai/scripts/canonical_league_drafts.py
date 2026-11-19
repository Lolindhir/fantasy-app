#!/usr/bin/env python3
"""League draft adapter for Fantasy Management consumers.

Reads the Shared Derived product `data-derived/league-drafts/<CanonicalLeagueID>/<season>.json`
(ADR-057, `.ai-context/manual/league-history.yaml`) and returns the drafts of that season in the
shape the FA-board builder consumes (DraftKey, DraftType, Status, SleeperStatus, Picks[PlayerID,
CurrentOwnerRosterID, ...]).

The product owns DraftType/DraftInstance classification (league metadata binding and the
free-agent/rookie rule in `tools/derived_data_lib/league_draft_identity.py`), the status labels and
the pick ownership. This adapter does not classify, relabel or re-derive anything; it only validates
the product identity and adds the display pick label (`<round>.<position>`), a consumer
presentation field the product deliberately does not carry.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SUPPORTED_CONTRACT_VERSIONS = {2}


class CanonicalDraftError(RuntimeError):
    """Raised when the league-drafts product is missing, invalid or inconsistent."""


def drafts_path(root: Path, canonical_league_id: str, season: int) -> Path:
    return root / "data-derived" / "league-drafts" / canonical_league_id / f"{season}.json"


def _read_json(path: Path) -> Any:
    if not path.is_file():
        raise CanonicalDraftError(f"Required file is missing: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CanonicalDraftError(f"Could not read valid JSON from {path}: {exc}") from exc


def _with_display_pick(pick: Any, draft_key: str) -> dict[str, Any]:
    if not isinstance(pick, dict):
        raise CanonicalDraftError(f"Draft {draft_key} contains a non-object pick.")
    result = dict(pick)
    round_no, position = pick.get("Round"), pick.get("PositionInRound")
    if isinstance(round_no, int) and isinstance(position, int):
        result["DisplayPick"] = f"{round_no}.{position:02d}"
    return result


def load_canonical_current_drafts(
    root: Path,
    *,
    canonical_league_id: str,
    season: int,
) -> list[dict[str, Any]]:
    """Return the drafts of the season from the league-drafts product, or raise CanonicalDraftError."""

    document = _read_json(drafts_path(root, canonical_league_id, season))
    if not isinstance(document, dict):
        raise CanonicalDraftError("The league-drafts product must be an object.")
    if document.get("ContractVersion") not in SUPPORTED_CONTRACT_VERSIONS:
        raise CanonicalDraftError(
            f"Unsupported league-drafts ContractVersion {document.get('ContractVersion')!r}."
        )
    if document.get("CanonicalLeagueID") != canonical_league_id or str(document.get("Season")) != str(season):
        raise CanonicalDraftError("The league-drafts product identity does not match league and season.")
    drafts = document.get("Drafts")
    if not isinstance(drafts, list) or any(not isinstance(d, dict) for d in drafts):
        raise CanonicalDraftError("The league-drafts product Drafts must be an array of objects.")

    result: list[dict[str, Any]] = []
    for draft in drafts:
        if str(draft.get("Season")) != str(season):
            raise CanonicalDraftError("The league-drafts product contains a draft of another season.")
        picks = draft.get("Picks")
        if not isinstance(picks, list):
            raise CanonicalDraftError(f"Draft {draft.get('DraftKey')} has no Picks array.")
        key = str(draft.get("DraftKey"))
        result.append({**draft, "Picks": [_with_display_pick(p, key) for p in picks]})
    return result
