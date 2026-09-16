from __future__ import annotations

from pathlib import Path
from typing import Any

from .common import load_json

_ADJUDICATION_PATH = Path("source-data/nfl/identities/historical-identity-adjudications.json")
_SCHEMA_VERSION = 1


def _required_text(item: dict[str, Any], key: str, *, context: str) -> str:
    value = str(item.get(key) or "").strip()
    if not value:
        raise ValueError(f"{context}.{key} must be a non-empty string")
    return value


def load_identity_adjudication_claims(
    repo_root: Path,
    known_canonical_ids: set[str],
) -> list[dict[str, Any]]:
    """Load explicit, season-local human-reviewed provider mapping decisions.

    Adjudications may confirm an otherwise unresolved historical provider token,
    but they never create a CanonicalPlayerID and never rewrite raw provider
    evidence. The source file is versioned repository evidence and every emitted
    claim retains its adjudication ID as provenance.
    """

    path = repo_root / _ADJUDICATION_PATH
    payload = load_json(path)
    if payload is None:
        return []
    if not isinstance(payload, dict):
        raise ValueError(f"Identity adjudications must be an object: {path}")
    if payload.get("SchemaVersion") != _SCHEMA_VERSION:
        raise ValueError(
            f"Identity adjudications SchemaVersion must be {_SCHEMA_VERSION}: {path}"
        )

    entries = payload.get("Adjudications")
    if not isinstance(entries, list):
        raise ValueError(f"Identity adjudications Adjudications must be an array: {path}")

    claims: list[dict[str, Any]] = []
    adjudication_ids: set[str] = set()
    token_seasons: dict[tuple[str, str, int], str] = {}

    for index, item in enumerate(entries):
        context = f"Adjudications[{index}]"
        if not isinstance(item, dict):
            raise ValueError(f"{context} must be an object")

        adjudication_id = _required_text(item, "AdjudicationID", context=context)
        if adjudication_id in adjudication_ids:
            raise ValueError(f"Duplicate identity adjudication ID: {adjudication_id}")
        adjudication_ids.add(adjudication_id)

        status = _required_text(item, "Status", context=context)
        if status != "confirmed":
            raise ValueError(
                f"{context}.Status must be 'confirmed'; unresolved review work does not belong "
                "in the canonical adjudication source"
            )

        season = item.get("Season")
        if isinstance(season, bool) or not isinstance(season, int) or season < 1920:
            raise ValueError(f"{context}.Season must be an NFL season >= 1920")

        provider = _required_text(item, "Provider", context=context)
        external_id = _required_text(item, "ExternalID", context=context)
        canonical_id = _required_text(item, "CanonicalPlayerID", context=context)
        _required_text(item, "SubjectLabel", context=context)
        _required_text(item, "Rationale", context=context)
        _required_text(item, "DecisionAuthority", context=context)
        _required_text(item, "DecisionDate", context=context)

        if canonical_id not in known_canonical_ids:
            raise ValueError(
                f"{context}.CanonicalPlayerID does not identify an existing canonical player: "
                f"{canonical_id}"
            )

        evidence = item.get("Evidence")
        if not isinstance(evidence, list) or not evidence:
            raise ValueError(f"{context}.Evidence must be a non-empty array")
        for evidence_index, evidence_item in enumerate(evidence):
            evidence_context = f"{context}.Evidence[{evidence_index}]"
            if not isinstance(evidence_item, dict):
                raise ValueError(f"{evidence_context} must be an object")
            _required_text(evidence_item, "Source", context=evidence_context)
            _required_text(evidence_item, "Summary", context=evidence_context)

        token_season = (provider, external_id, season)
        previous = token_seasons.get(token_season)
        if previous is not None:
            raise ValueError(
                "Multiple confirmed identity adjudications target the same provider token and "
                f"season: {provider}/{external_id}/{season} ({previous}, {adjudication_id})"
            )
        token_seasons[token_season] = adjudication_id

        claims.append(
            {
                "Provider": provider,
                "ExternalID": external_id,
                "CanonicalPlayerID": canonical_id,
                "ObservedSeason": season,
                "Sources": [f"manual.identity-adjudication:{adjudication_id}"],
            }
        )

    claims.sort(
        key=lambda item: (
            int(item["ObservedSeason"]),
            str(item["Provider"]),
            str(item["ExternalID"]),
            str(item["CanonicalPlayerID"]),
        )
    )
    return claims


def apply_identity_adjudications(
    payload: dict[str, Any],
    claims: list[dict[str, Any]],
) -> dict[str, Any]:
    """Apply confirmed adjudications without weakening ordinary conflict rules.

    A confirmation can fill exactly its observed season and may join same-owner
    intervals that become contiguous because of that observation. It cannot
    bridge any other unobserved gap, override an active provider conflict, or
    replace a different owner already valid in that season.
    """

    if not claims:
        return payload

    mappings = [dict(item) for item in payload.get("Mappings", [])]
    conflicts = [dict(item) for item in payload.get("Conflicts", [])]
    mappings_by_token: dict[tuple[str, str], list[dict[str, Any]]] = {}
    conflicts_by_token: dict[tuple[str, str], list[dict[str, Any]]] = {}

    for item in mappings:
        token = (str(item.get("Provider") or ""), str(item.get("ExternalID") or ""))
        mappings_by_token.setdefault(token, []).append(item)
    for item in conflicts:
        token = (str(item.get("Provider") or ""), str(item.get("ExternalID") or ""))
        conflicts_by_token.setdefault(token, []).append(item)

    def interval(item: dict[str, Any], default_season: int) -> tuple[int, int]:
        first = int(item.get("FirstObservedSeason") or default_season)
        last = int(item.get("LastObservedSeason") or first)
        return first, last

    for claim in claims:
        provider = str(claim["Provider"])
        external_id = str(claim["ExternalID"])
        canonical_id = str(claim["CanonicalPlayerID"])
        season = int(claim["ObservedSeason"])
        sources = set(claim.get("Sources") or [])
        token = (provider, external_id)
        token_mappings = mappings_by_token.setdefault(token, [])

        for conflict in conflicts_by_token.get(token, []):
            first, last = interval(conflict, season)
            if first <= season <= last:
                raise ValueError(
                    "Confirmed identity adjudication cannot override an active provider conflict: "
                    f"{provider}/{external_id}/{season}"
                )

        overlapping = []
        for item in token_mappings:
            if str(item.get("CanonicalPlayerID") or "") == canonical_id:
                continue
            first, last = interval(item, season)
            if first <= season <= last:
                overlapping.append(item)
        if overlapping:
            owners = sorted(
                {canonical_id, *(str(item.get("CanonicalPlayerID") or "") for item in overlapping)}
            )
            raise ValueError(
                "Confirmed identity adjudication conflicts with an existing season-valid owner: "
                f"{provider}/{external_id}/{season} -> {owners}"
            )

        touching = []
        for item in token_mappings:
            if str(item.get("CanonicalPlayerID") or "") != canonical_id:
                continue
            first, last = interval(item, season)
            if first - 1 <= season <= last + 1:
                touching.append(item)

        if touching:
            primary = touching[0]
            first_values = [interval(item, season)[0] for item in touching]
            last_values = [interval(item, season)[1] for item in touching]
            primary["FirstObservedSeason"] = min([season, *first_values])
            primary["LastObservedSeason"] = max([season, *last_values])
            merged_sources = set(sources)
            for item in touching:
                merged_sources.update(item.get("Sources") or [])
            primary["Sources"] = sorted(merged_sources)
            for item in touching[1:]:
                token_mappings.remove(item)
            continue

        token_mappings.append(
            {
                "Provider": provider,
                "ExternalID": external_id,
                "CanonicalPlayerID": canonical_id,
                "FirstObservedSeason": season,
                "LastObservedSeason": season,
                "Sources": sorted(sources),
            }
        )

    mappings = [item for bucket in mappings_by_token.values() for item in bucket]
    mappings.sort(
        key=lambda item: (
            str(item["Provider"]),
            str(item["ExternalID"]),
            int(item["FirstObservedSeason"]),
            str(item["CanonicalPlayerID"]),
        )
    )
    return {**payload, "Mappings": mappings, "Conflicts": conflicts}
