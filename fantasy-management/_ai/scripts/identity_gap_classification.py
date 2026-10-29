"""Classify current identity gaps by structure (Issue #347, plan block B3).

Implements the class patterns of ``currentIdentityGapResolution`` in
``.ai-context/manual/player-identity.yaml``. A gap is a current-season player whose
provisional CanonicalPlayerID differs from a durable CanonicalPlayerID that the
name/position diagnostic attributes to the same person. The classification looks only
at provider ID tokens of the two canonical records; names are never evidence.

Nothing here merges, removes or grants canonical facts. It only decides whether an
open gap is *classified* (stays in the population as ``identity_hold``) or
*unclassified* (keeps blocking cutovers).
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import date
from typing import Any, Iterable

PLACEHOLDER_GSIS_UPGRADE = "placeholderGsisUpgrade"
SPLIT_IDENTITY = "splitIdentity"
WRONG_UPSTREAM_CLAIM = "wrongUpstreamClaim"
CLASSES = (PLACEHOLDER_GSIS_UPGRADE, SPLIT_IDENTITY, WRONG_UPSTREAM_CLAIM)

# Date on which Robert accepted the class contract (PR #846). Open gaps are aged from
# here until a persisted first-seen state exists.
CLASSIFICATION_DECIDED_AT = date(2026, 10, 4)

_VALID_GSIS = re.compile(r"^00-\d{7}$")


def _ids(record: dict[str, Any]) -> dict[str, str]:
    return {
        str(provider): str(value).strip()
        for provider, value in (record.get("IDs") or {}).items()
        if str(value or "").strip()
    }


def _has_valid_gsis(ids: dict[str, str]) -> bool:
    return bool(_VALID_GSIS.match(ids.get("GSIS", "")))


def classify_identity_gap(
    gap_record: dict[str, Any],
    other_record: dict[str, Any],
    *,
    esb_occurrences: Counter[str] | None = None,
) -> str | None:
    """Return the gap class for one provisional/durable record pair, or None.

    ``esb_occurrences`` counts ESB values over all canonical records; the placeholder
    GSIS rule only applies when the shared ESB value occurs on exactly these two.
    """

    gap_ids = _ids(gap_record)
    other_ids = _ids(other_record)
    shared_providers = set(gap_ids) & set(other_ids)
    disagreeing = {p for p in shared_providers if gap_ids[p] != other_ids[p]}

    esb = gap_ids.get("ESB")
    if (
        esb
        and esb == other_ids.get("ESB")
        and (esb_occurrences is None or esb_occurrences.get(esb) == 2)
        and _has_valid_gsis(gap_ids) != _has_valid_gsis(other_ids)
        and disagreeing <= {"GSIS"}
    ):
        return PLACEHOLDER_GSIS_UPGRADE

    if not shared_providers:
        return SPLIT_IDENTITY

    # Same provider, different token, no other disagreement: an upstream crosswalk
    # attributes a token to the durable record that the other record contradicts.
    # Requires a token value of the provisional record that reappears on the durable
    # record under a different provider key (e.g. Tank01 == ESPN), so that two
    # unrelated same-name players with different Sleeper IDs stay unclassified.
    if len(disagreeing) == 1 and shared_providers == disagreeing:
        gap_values = {
            value for provider, value in gap_ids.items() if provider not in disagreeing
        }
        other_values = {
            value for provider, value in other_ids.items() if provider not in disagreeing
        }
        if gap_values & other_values:
            return WRONG_UPSTREAM_CLAIM

    return None


def esb_occurrence_counter(records: Iterable[dict[str, Any]]) -> Counter[str]:
    return Counter(
        esb for record in records if (esb := _ids(record).get("ESB"))
    )


def age_in_days(as_of: date, since: date = CLASSIFICATION_DECIDED_AT) -> int:
    return max((as_of - since).days, 0)
