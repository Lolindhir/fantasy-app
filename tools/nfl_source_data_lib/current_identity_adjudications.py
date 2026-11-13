from __future__ import annotations

from pathlib import Path
from typing import Any

from data_roots import DATA_SOURCE_ROOT
from .common import load_json

_ADJUDICATION_PATH = Path(DATA_SOURCE_ROOT) / "nfl/identities/current-identity-adjudications.json"
_SCHEMA_VERSION = 1
_REASSIGNMENT_KIND = "current-provider-reassignment"
_OVERRIDE_KIND = "upstream-claim-override"
_UNOWNED_KIND = "confirmed-unowned-provider-token"
MERGE_KIND = "confirmed-canonical-duplicate-merge"
_MERGE_ANCHOR_CROSS = "cross-provider-id-equality"
_MERGE_ANCHOR_ATTRIBUTES = "attribute-agreement"
_MERGE_ANCHOR_SHARED = "shared-provider-token"
_MERGE_SHARED_PROVIDERS = frozenset({"GSIS", "Sleeper", "ESPN", "PFR", "PFF", "Yahoo"})
_MERGE_REQUIRED_ATTRIBUTES = frozenset({"BirthDate", "NormalizedName", "Position"})
_CONFLICT_POLICY_BY_KIND = {
    _REASSIGNMENT_KIND: "reject-active-conflict",
    _OVERRIDE_KIND: "override-named-upstream-claim",
    _UNOWNED_KIND: "reject-any-conflict",
    MERGE_KIND: "reject-conflict-outside-declared-pair",
}
_STRONG_ANCHOR_PROVIDERS = frozenset({"GSIS", "ESPN", "PFR", "PFF"})


def _required_text(item: dict[str, Any], key: str, *, context: str) -> str:
    value = str(item.get(key) or "").strip()
    if not value:
        raise ValueError(f"{context}.{key} must be a non-empty string")
    return value


def _required_canonical_ids(
    item: dict[str, Any],
    key: str,
    *,
    context: str,
    known_canonical_ids: set[str],
) -> list[str]:
    values = item.get(key)
    if not isinstance(values, list) or not values:
        raise ValueError(f"{context}.{key} must be a non-empty array")

    result: list[str] = []
    seen: set[str] = set()
    for index, value in enumerate(values):
        canonical_id = str(value or "").strip()
        if not canonical_id:
            raise ValueError(f"{context}.{key}[{index}] must be a non-empty string")
        if canonical_id in seen:
            raise ValueError(f"{context}.{key} contains duplicate CanonicalPlayerID: {canonical_id}")
        if canonical_id not in known_canonical_ids:
            raise ValueError(
                f"{context}.{key}[{index}] does not identify an existing canonical player: "
                f"{canonical_id}"
            )
        seen.add(canonical_id)
        result.append(canonical_id)
    return result


def _validate_upstream_claim_override(
    item: dict[str, Any],
    *,
    context: str,
    season: int,
    adjudication_id: str,
    assignments: list[dict[str, str]],
    overridden_claims: dict[tuple[str, str, int], str],
) -> dict[str, Any]:
    """Validate the fields that only an ``upstream-claim-override`` carries.

    An override declares exactly one upstream crosswalk claim wrong for one season
    and names the replacement token for the same provider. It must be backed by an
    independent strong anchor, platform consistency of the replacement token and a
    documented inconsistency of the overridden token.
    """

    if len(assignments) != 1:
        raise ValueError(
            f"{context}.ProviderAssignments must contain exactly one replacement token for "
            f"ResolutionKind '{_OVERRIDE_KIND}'"
        )
    replacement = assignments[0]

    claim = item.get("OverriddenUpstreamClaim")
    claim_context = f"{context}.OverriddenUpstreamClaim"
    if not isinstance(claim, dict):
        raise ValueError(f"{claim_context} must be an object")
    claim_source = _required_text(claim, "Source", context=claim_context)
    claim_provider = _required_text(claim, "Provider", context=claim_context)
    claim_external_id = _required_text(claim, "ExternalID", context=claim_context)
    if claim_provider != replacement["Provider"]:
        raise ValueError(
            f"{claim_context}.Provider must equal the replacement token provider "
            f"'{replacement['Provider']}'"
        )
    if claim_external_id == replacement["ExternalID"]:
        raise ValueError(
            f"{claim_context}.ExternalID must differ from the replacement token"
        )
    claim_key = (claim_provider, claim_external_id, season)
    previous = overridden_claims.get(claim_key)
    if previous is not None:
        raise ValueError(
            "Multiple confirmed current identity adjudications override the same upstream "
            f"claim and season: {claim_provider}/{claim_external_id}/{season} "
            f"({previous}, {adjudication_id})"
        )
    overridden_claims[claim_key] = adjudication_id

    anchors = item.get("IndependentAnchors")
    if not isinstance(anchors, list) or not anchors:
        raise ValueError(
            f"{context}.IndependentAnchors must be a non-empty array with at least one "
            f"strong anchor ({', '.join(sorted(_STRONG_ANCHOR_PROVIDERS))})"
        )
    normalized_anchors: list[dict[str, str]] = []
    for anchor_index, anchor in enumerate(anchors):
        anchor_context = f"{context}.IndependentAnchors[{anchor_index}]"
        if not isinstance(anchor, dict):
            raise ValueError(f"{anchor_context} must be an object")
        provider = _required_text(anchor, "Provider", context=anchor_context)
        if provider not in _STRONG_ANCHOR_PROVIDERS:
            raise ValueError(
                f"{anchor_context}.Provider must be one of "
                f"{sorted(_STRONG_ANCHOR_PROVIDERS)}"
            )
        if provider == replacement["Provider"]:
            raise ValueError(
                f"{anchor_context}.Provider must be independent of the overridden provider "
                f"'{replacement['Provider']}'"
            )
        normalized = {
            "Provider": provider,
            "ExternalID": _required_text(anchor, "ExternalID", context=anchor_context),
            # Provider key under which the replacement token's record carries the
            # same value (for example ESPN on the target equals Tank01 on the source).
            "SourceProvider": str(anchor.get("SourceProvider") or provider).strip(),
        }
        _required_text(anchor, "Summary", context=anchor_context)
        normalized_anchors.append(normalized)

    consistency = item.get("ReplacementTokenConsistency")
    consistency_context = f"{context}.ReplacementTokenConsistency"
    if not isinstance(consistency, dict):
        raise ValueError(f"{consistency_context} must be an object")
    position = _required_text(consistency, "Position", context=consistency_context)
    _required_text(consistency, "Team", context=consistency_context)
    _required_text(consistency, "Summary", context=consistency_context)

    inconsistency = item.get("OverriddenTokenInconsistency")
    inconsistency_context = f"{context}.OverriddenTokenInconsistency"
    if not isinstance(inconsistency, dict):
        raise ValueError(f"{inconsistency_context} must be an object")
    _required_text(inconsistency, "Summary", context=inconsistency_context)

    return {
        "OverriddenUpstreamClaim": {
            "Source": claim_source,
            "Provider": claim_provider,
            "ExternalID": claim_external_id,
        },
        "IndependentAnchors": sorted(
            normalized_anchors, key=lambda a: (a["Provider"], a["ExternalID"])
        ),
        "ReplacementPosition": position,
    }


def _validate_unowned_provider_token(item: dict[str, Any], *, context: str,
                                     assignments: list[dict[str, str]]) -> dict[str, Any]:
    """Explicitly reviewed *unowned* PFR ID, never a name-derived joining rule.

    Require two different established strong anchors of the target plus reviewable
    external provenance. Neither a conflicting claim nor an already owned token
    may be overridden by this resolution kind.
    """
    if len(assignments) != 1 or assignments[0]["Provider"] != "PFR":
        raise ValueError(f"{context}.ProviderAssignments must contain exactly one PFR token")
    anchors = item.get("IndependentAnchors")
    if not isinstance(anchors, list) or len(anchors) < 2:
        raise ValueError(f"{context}.IndependentAnchors requires two strong target anchors")
    normalized: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, anchor in enumerate(anchors):
        place = f"{context}.IndependentAnchors[{index}]"
        if not isinstance(anchor, dict):
            raise ValueError(f"{place} must be an object")
        provider = _required_text(anchor, "Provider", context=place)
        if provider not in {"GSIS", "ESPN", "PFF"} or provider in seen:
            raise ValueError(f"{place}.Provider must be a distinct GSIS/ESPN/PFF anchor")
        seen.add(provider)
        external = _required_text(anchor, "ExternalID", context=place)
        _required_text(anchor, "Summary", context=place)
        normalized.append({"Provider": provider, "ExternalID": external})
    return {"IndependentAnchors": sorted(normalized, key=lambda a: a["Provider"])}


def normalize_person_name(value: Any) -> str:
    return "".join(ch for ch in str(value or "").lower() if ch.isalnum())


def _validate_duplicate_merge(
    item: dict[str, Any],
    *,
    context: str,
    target_id: str,
    source_ids: list[str],
) -> dict[str, Any]:
    """Format-validate a ``confirmed-canonical-duplicate-merge``.

    The duplicates may legitimately not exist yet (they can only be created by the
    very materialization that this decision then merges), so existence and the
    content anchors are verified against the real records by the state validator
    and by the identity builder, never here.
    """
    duplicates = item.get("DuplicateCanonicalPlayerIDs")
    if not isinstance(duplicates, list) or not duplicates:
        raise ValueError(f"{context}.DuplicateCanonicalPlayerIDs must be a non-empty array")
    normalized_duplicates: list[str] = []
    for index, value in enumerate(duplicates):
        duplicate_id = str(value or "").strip()
        if not duplicate_id:
            raise ValueError(f"{context}.DuplicateCanonicalPlayerIDs[{index}] must be a non-empty string")
        if duplicate_id in normalized_duplicates:
            raise ValueError(f"{context}.DuplicateCanonicalPlayerIDs contains duplicate: {duplicate_id}")
        if duplicate_id == target_id or duplicate_id in source_ids:
            raise ValueError(
                f"{context}.DuplicateCanonicalPlayerIDs must not contain the target or a source: "
                f"{duplicate_id}"
            )
        normalized_duplicates.append(duplicate_id)

    anchors = item.get("IndependentAnchors")
    if not isinstance(anchors, list) or len(anchors) < 2:
        raise ValueError(
            f"{context}.IndependentAnchors requires a '{_MERGE_ANCHOR_CROSS}' anchor and an "
            f"'{_MERGE_ANCHOR_ATTRIBUTES}' anchor"
        )
    cross: list[dict[str, str]] = []
    shared: list[dict[str, str]] = []
    attribute_seen = False
    for index, anchor in enumerate(anchors):
        place = f"{context}.IndependentAnchors[{index}]"
        if not isinstance(anchor, dict):
            raise ValueError(f"{place} must be an object")
        kind = _required_text(anchor, "Kind", context=place)
        _required_text(anchor, "Summary", context=place)
        if kind == _MERGE_ANCHOR_CROSS:
            target_provider = _required_text(anchor, "TargetProvider", context=place)
            duplicate_provider = _required_text(anchor, "DuplicateProvider", context=place)
            if target_provider == duplicate_provider:
                raise ValueError(
                    f"{place} must equate two different providers (same-provider equality is "
                    "no independent anchor)"
                )
            cross.append(
                {
                    "Kind": kind,
                    "TargetProvider": target_provider,
                    "DuplicateProvider": duplicate_provider,
                    "ExternalID": _required_text(anchor, "ExternalID", context=place),
                }
            )
        elif kind == _MERGE_ANCHOR_SHARED:
            provider = _required_text(anchor, "Provider", context=place)
            if provider not in _MERGE_SHARED_PROVIDERS:
                raise ValueError(
                    f"{place}.Provider must be one of {sorted(_MERGE_SHARED_PROVIDERS)}"
                )
            shared.append(
                {
                    "Kind": kind,
                    "Provider": provider,
                    "ExternalID": _required_text(anchor, "ExternalID", context=place),
                }
            )
        elif kind == _MERGE_ANCHOR_ATTRIBUTES:
            fields = anchor.get("Fields")
            if not isinstance(fields, list) or not _MERGE_REQUIRED_ATTRIBUTES <= {
                str(value) for value in fields
            }:
                raise ValueError(
                    f"{place}.Fields must include {sorted(_MERGE_REQUIRED_ATTRIBUTES)}"
                )
            attribute_seen = True
        else:
            raise ValueError(
                f"{place}.Kind must be '{_MERGE_ANCHOR_CROSS}', '{_MERGE_ANCHOR_SHARED}' or "
                f"'{_MERGE_ANCHOR_ATTRIBUTES}'"
            )
    if not (cross or shared) or not attribute_seen:
        raise ValueError(
            f"{context}.IndependentAnchors needs a '{_MERGE_ANCHOR_CROSS}' or "
            f"'{_MERGE_ANCHOR_SHARED}' anchor and an '{_MERGE_ANCHOR_ATTRIBUTES}' anchor"
        )

    contaminated: list[dict[str, str]] = []
    declared = item.get("ContaminatedTokens")
    if declared is not None:
        if not isinstance(declared, list) or not declared:
            raise ValueError(f"{context}.ContaminatedTokens must be a non-empty array when present")
        seen_tokens: set[tuple[str, str]] = set()
        for index, entry in enumerate(declared):
            place = f"{context}.ContaminatedTokens[{index}]"
            if not isinstance(entry, dict):
                raise ValueError(f"{place} must be an object")
            token = (
                _required_text(entry, "Provider", context=place),
                _required_text(entry, "ExternalID", context=place),
            )
            if token in seen_tokens:
                raise ValueError(f"{place} duplicates a declared contaminated token")
            seen_tokens.add(token)
            _required_text(entry, "Summary", context=place)
            contaminated.append(
                {
                    "Provider": token[0],
                    "ExternalID": token[1],
                    "Source": _required_text(entry, "Source", context=place),
                }
            )
    return {
        "DuplicateCanonicalPlayerIDs": sorted(normalized_duplicates),
        "IndependentAnchors": sorted(
            [*cross, *shared],
            key=lambda a: (
                a["Kind"], a.get("TargetProvider", a.get("Provider", "")),
                a.get("DuplicateProvider", ""), a["ExternalID"],
            ),
        ),
        "ContaminatedTokens": sorted(contaminated, key=lambda t: (t["Provider"], t["ExternalID"])),
    }


def verify_duplicate_pair(
    adjudication: dict[str, Any],
    target_view: dict[str, Any],
    duplicate_view: dict[str, Any],
    *,
    duplicate_id: str,
) -> None:
    """Fail closed unless two identity views are provably the same person.

    A *view* is ``{"IDs": {provider: set[str]}, "BirthDates": set, "Positions": set,
    "Names": set}`` (names already normalized). Names alone are never an anchor: the
    pair needs equal non-empty BirthDate, Position and name, one equal ID value held
    under two different providers, and no provider on which the two disagree.
    """
    adjudication_id = str(adjudication["AdjudicationID"])

    def reject(reason: str) -> None:
        raise ValueError(
            f"Current identity adjudication {adjudication_id} cannot merge {duplicate_id} into "
            f"{adjudication['TargetCanonicalPlayerID']}: {reason}"
        )

    for field, key in (("BirthDate", "BirthDates"), ("Position", "Positions"), ("name", "Names")):
        target_values = {str(v) for v in target_view.get(key) or set() if str(v or "").strip()}
        duplicate_values = {str(v) for v in duplicate_view.get(key) or set() if str(v or "").strip()}
        if len(target_values) != 1 or target_values != duplicate_values:
            reject(
                f"{field} is missing or differs (target {sorted(target_values)}, "
                f"duplicate {sorted(duplicate_values)})"
            )
    target_ids = target_view.get("IDs") or {}
    contaminated = {
        (str(t["Provider"]), str(t["ExternalID"]))
        for t in adjudication.get("ContaminatedTokens") or []
    }
    # Tokens the review declared as upstream contamination of the duplicate do not
    # count as evidence either way: not as an anchor and not as a contradiction.
    duplicate_ids = {
        provider: {v for v in values if (provider, v) not in contaminated}
        for provider, values in (duplicate_view.get("IDs") or {}).items()
    }
    for anchor in adjudication["IndependentAnchors"]:
        kind = anchor.get("Kind")
        external_id = str(anchor.get("ExternalID") or "")
        if kind == _MERGE_ANCHOR_CROSS:
            if external_id in target_ids.get(str(anchor["TargetProvider"]), set()) and (
                external_id in duplicate_ids.get(str(anchor["DuplicateProvider"]), set())
            ):
                break
        elif kind == _MERGE_ANCHOR_SHARED:
            provider = str(anchor["Provider"])
            if external_id in target_ids.get(provider, set()) and (
                external_id in duplicate_ids.get(provider, set())
            ):
                break
    else:
        reject("no declared cross-provider or shared-token anchor is carried by both records")
    for provider in sorted(set(target_ids) & set(duplicate_ids)):
        if target_ids[provider] and duplicate_ids[provider] and target_ids[provider] != duplicate_ids[provider]:
            reject(
                f"provider {provider} contradicts (target {sorted(target_ids[provider])}, "
                f"duplicate {sorted(duplicate_ids[provider])})"
            )


def view_from_record(record: dict[str, Any]) -> dict[str, Any]:
    ids: dict[str, set[str]] = {}
    for provider, value in (record.get("IDs") or {}).items():
        if str(value or "").strip():
            ids.setdefault(str(provider), set()).add(str(value))
    for provider, values in (record.get("IDAliases") or {}).items():
        for value in values or []:
            if str(value or "").strip():
                ids.setdefault(str(provider), set()).add(str(value))
    return {
        "IDs": ids,
        "BirthDates": {str(record["BirthDate"])} if record.get("BirthDate") else set(),
        "Positions": {str(record["Position"])} if record.get("Position") else set(),
        "Names": {normalize_person_name(record["Name"])} if record.get("Name") else set(),
    }


def load_current_identity_adjudications(
    repo_root: Path,
    known_canonical_ids: set[str],
    observation_season: int,
) -> list[dict[str, Any]]:
    """Load explicit current-season provider reassignments.

    This source is intentionally separate from historical adjudications. A current
    adjudication may reassign explicitly enumerated provider tokens from one or
    more already-existing provisional CanonicalPlayerIDs to one already-existing
    durable CanonicalPlayerID for exactly one observation season.

    The loader validates every persisted decision, but only returns decisions for
    the requested observation season. This prevents a current adjudication from
    silently carrying forward into a later NFL season.
    """

    path = repo_root / _ADJUDICATION_PATH
    payload = load_json(path)
    if payload is None:
        return []
    if not isinstance(payload, dict):
        raise ValueError(f"Current identity adjudications must be an object: {path}")
    if payload.get("SchemaVersion") != _SCHEMA_VERSION:
        raise ValueError(
            f"Current identity adjudications SchemaVersion must be {_SCHEMA_VERSION}: {path}"
        )

    entries = payload.get("Adjudications")
    if not isinstance(entries, list):
        raise ValueError(
            f"Current identity adjudications Adjudications must be an array: {path}"
        )

    decisions: list[dict[str, Any]] = []
    adjudication_ids: set[str] = set()
    token_seasons: dict[tuple[str, str, int], str] = {}
    overridden_claims: dict[tuple[str, str, int], str] = {}

    for index, item in enumerate(entries):
        context = f"Adjudications[{index}]"
        if not isinstance(item, dict):
            raise ValueError(f"{context} must be an object")

        adjudication_id = _required_text(item, "AdjudicationID", context=context)
        if adjudication_id in adjudication_ids:
            raise ValueError(f"Duplicate current identity adjudication ID: {adjudication_id}")
        adjudication_ids.add(adjudication_id)

        status = _required_text(item, "Status", context=context)
        if status != "confirmed":
            raise ValueError(
                f"{context}.Status must be 'confirmed'; unresolved review work does not belong "
                "in the canonical current-adjudication source"
            )

        season = item.get("Season")
        if isinstance(season, bool) or not isinstance(season, int) or season < 1920:
            raise ValueError(f"{context}.Season must be an NFL season >= 1920")

        resolution_kind = _required_text(item, "ResolutionKind", context=context)
        if resolution_kind not in _CONFLICT_POLICY_BY_KIND:
            raise ValueError(
                f"{context}.ResolutionKind must be one of {sorted(_CONFLICT_POLICY_BY_KIND)}"
            )

        expected_policy = _CONFLICT_POLICY_BY_KIND[resolution_kind]
        conflict_policy = _required_text(item, "ConflictPolicy", context=context)
        if conflict_policy != expected_policy:
            raise ValueError(
                f"{context}.ConflictPolicy must be '{expected_policy}' for "
                f"ResolutionKind '{resolution_kind}'"
            )

        target_id = _required_text(item, "TargetCanonicalPlayerID", context=context)
        if target_id not in known_canonical_ids:
            raise ValueError(
                f"{context}.TargetCanonicalPlayerID does not identify an existing canonical "
                f"player: {target_id}"
            )

        if resolution_kind == _UNOWNED_KIND:
            source_ids = item.get("SourceCanonicalPlayerIDs")
            if source_ids != []:
                raise ValueError(
                    f"{context}.SourceCanonicalPlayerIDs must be [] for a formerly unowned token"
                )
        elif resolution_kind == MERGE_KIND:
            raw_sources = item.get("SourceCanonicalPlayerIDs")
            if raw_sources == []:
                source_ids = []
            else:
                source_ids = _required_canonical_ids(
                    item, "SourceCanonicalPlayerIDs", context=context,
                    known_canonical_ids=known_canonical_ids,
                )
        else:
            source_ids = _required_canonical_ids(
                item, "SourceCanonicalPlayerIDs", context=context,
                known_canonical_ids=known_canonical_ids,
            )
        if target_id in source_ids:
            raise ValueError(
                f"{context}.TargetCanonicalPlayerID must not also appear in "
                "SourceCanonicalPlayerIDs"
            )

        _required_text(item, "SubjectLabel", context=context)
        _required_text(item, "Rationale", context=context)
        _required_text(item, "DecisionAuthority", context=context)
        _required_text(item, "DecisionDate", context=context)

        assignments = item.get("ProviderAssignments")
        if resolution_kind == MERGE_KIND:
            if assignments not in (None, []):
                raise ValueError(
                    f"{context}.ProviderAssignments must be empty for ResolutionKind "
                    f"'{MERGE_KIND}' (a merge moves every token of the duplicate)"
                )
            assignments = []
        elif not isinstance(assignments, list) or not assignments:
            raise ValueError(f"{context}.ProviderAssignments must be a non-empty array")

        normalized_assignments: list[dict[str, str]] = []
        local_tokens: set[tuple[str, str]] = set()
        for assignment_index, assignment in enumerate(assignments):
            assignment_context = f"{context}.ProviderAssignments[{assignment_index}]"
            if not isinstance(assignment, dict):
                raise ValueError(f"{assignment_context} must be an object")
            provider = _required_text(assignment, "Provider", context=assignment_context)
            external_id = _required_text(assignment, "ExternalID", context=assignment_context)
            token = (provider, external_id)
            if token in local_tokens:
                raise ValueError(
                    f"{context}.ProviderAssignments contains duplicate provider token: "
                    f"{provider}/{external_id}"
                )
            local_tokens.add(token)

            token_season = (provider, external_id, season)
            previous = token_seasons.get(token_season)
            if previous is not None:
                raise ValueError(
                    "Multiple confirmed current identity adjudications target the same provider "
                    f"token and season: {provider}/{external_id}/{season} "
                    f"({previous}, {adjudication_id})"
                )
            token_seasons[token_season] = adjudication_id
            normalized_assignments.append(
                {"Provider": provider, "ExternalID": external_id}
            )

        override_fields: dict[str, Any] = {}
        if resolution_kind == _OVERRIDE_KIND:
            override_fields = _validate_upstream_claim_override(
                item,
                context=context,
                season=season,
                adjudication_id=adjudication_id,
                assignments=normalized_assignments,
                overridden_claims=overridden_claims,
            )
        elif resolution_kind == _UNOWNED_KIND:
            override_fields = _validate_unowned_provider_token(
                item, context=context, assignments=normalized_assignments
            )
        elif resolution_kind == MERGE_KIND:
            override_fields = _validate_duplicate_merge(
                item, context=context, target_id=target_id, source_ids=list(source_ids)
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

        if season != observation_season:
            continue

        decisions.append(
            {
                "AdjudicationID": adjudication_id,
                "Season": season,
                "ResolutionKind": resolution_kind,
                "TargetCanonicalPlayerID": target_id,
                "SourceCanonicalPlayerIDs": sorted(source_ids),
                "ProviderAssignments": sorted(
                    normalized_assignments,
                    key=lambda assignment: (
                        assignment["Provider"],
                        assignment["ExternalID"],
                    ),
                ),
                "Provenance": f"manual.current-identity-adjudication:{adjudication_id}",
                **override_fields,
            }
        )

    _validate_merge_topology(entries)
    decisions.sort(key=lambda item: item["AdjudicationID"])
    return decisions


def _validate_merge_topology(entries: list[dict[str, Any]]) -> None:
    """No chains: a merged duplicate is nobody's target, source or second duplicate."""
    by_season: dict[int, list[dict[str, Any]]] = {}
    for item in entries:
        by_season.setdefault(item["Season"], []).append(item)
    for season, items in by_season.items():
        duplicates: dict[str, str] = {}
        for item in items:
            if item["ResolutionKind"] != MERGE_KIND:
                continue
            for duplicate_id in item["DuplicateCanonicalPlayerIDs"]:
                if duplicate_id in duplicates:
                    raise ValueError(
                        f"Duplicate {duplicate_id} is merged by two adjudications in {season}: "
                        f"{duplicates[duplicate_id]}, {item['AdjudicationID']}"
                    )
                duplicates[duplicate_id] = item["AdjudicationID"]
        for item in items:
            related = {str(item["TargetCanonicalPlayerID"])} | {
                str(value) for value in item.get("SourceCanonicalPlayerIDs") or []
            }
            for related_id in related:
                owner = duplicates.get(related_id)
                if owner is not None and owner != item["AdjudicationID"]:
                    raise ValueError(
                        f"Adjudication {item['AdjudicationID']} uses {related_id}, which "
                        f"{owner} merges away as a duplicate (chains are not allowed)"
                    )


def validate_current_identity_adjudications_against_state(
    adjudications: list[dict[str, Any]],
    canonical_players: list[dict[str, Any]],
    mapping_conflicts: list[dict[str, Any]],
    observation_season: int,
    mapping_claims: list[dict[str, Any]] | None = None,
) -> list[dict[str, str]]:
    """Fail closed if a proposed current reassignment contradicts active identity state.

    This validator deliberately does not apply decisions. It provides the safety
    boundary required before a future identity-builder integration:
    - the target may not already carry a different active value for an assigned provider;
    - an assigned provider token may not be owned by an undeclared third canonical identity;
    - an assigned token may not overlap an active provider conflict, unless every
      party of that conflict is the declared target or a declared source.

    The declared source CanonicalPlayerIDs are the only existing owners that may be
    superseded by a future application step.

    An ``upstream-claim-override`` is the only kind that may resolve a conflict, and
    only the exact upstream claim it names. Instead of raising, it reports itself as
    ``obsolete`` when the named upstream claim has changed or disappeared and as
    ``superseded-by-upstream`` when the target already carries the replacement token.

    Returns one ``{"AdjudicationID", "Status"}`` entry per adjudication, where Status
    is ``active``, ``obsolete`` or ``superseded-by-upstream``.
    """

    by_id = {
        str(player.get("CanonicalPlayerID") or ""): player
        for player in canonical_players
        if str(player.get("CanonicalPlayerID") or "")
    }

    token_owners: dict[tuple[str, str], set[str]] = {}
    for canonical_id, player in by_id.items():
        ids = player.get("IDs") or {}
        aliases = player.get("IDAliases") or {}
        for provider, value in ids.items():
            external_id = str(value or "").strip()
            if external_id:
                token_owners.setdefault((str(provider), external_id), set()).add(canonical_id)
        for provider, values in aliases.items():
            for value in values or []:
                external_id = str(value or "").strip()
                if external_id:
                    token_owners.setdefault((str(provider), external_id), set()).add(canonical_id)

    active_conflict_tokens: set[tuple[str, str]] = set()
    active_conflict_members: dict[tuple[str, str], set[str]] = {}
    for conflict in mapping_conflicts:
        provider = str(conflict.get("Provider") or "").strip()
        external_id = str(conflict.get("ExternalID") or "").strip()
        if not provider or not external_id:
            continue
        first_raw = conflict.get("FirstObservedSeason")
        last_raw = conflict.get("LastObservedSeason")
        members = {str(value) for value in conflict.get("CanonicalPlayerIDs") or []}
        if first_raw is None and last_raw is None:
            active_conflict_tokens.add((provider, external_id))
            active_conflict_members.setdefault((provider, external_id), set()).update(members)
            continue
        first = int(first_raw if first_raw is not None else observation_season)
        last = int(last_raw if last_raw is not None else first)
        if first <= observation_season <= last:
            active_conflict_tokens.add((provider, external_id))
            active_conflict_members.setdefault((provider, external_id), set()).update(members)

    # Duplicates a merge declares are parties of the split every other decision of the
    # same target resolves: they may appear as conflict members and token owners.
    merged_duplicates: dict[str, set[str]] = {}
    for adjudication in adjudications:
        if adjudication.get("ResolutionKind") == MERGE_KIND:
            merged_duplicates.setdefault(
                str(adjudication["TargetCanonicalPlayerID"]), set()
            ).update(str(value) for value in adjudication["DuplicateCanonicalPlayerIDs"])

    statuses: list[dict[str, str]] = []
    for adjudication in adjudications:
        adjudication_id = str(adjudication["AdjudicationID"])
        target_id = str(adjudication["TargetCanonicalPlayerID"])
        source_ids = {str(value) for value in adjudication["SourceCanonicalPlayerIDs"]}
        extra_ids = merged_duplicates.get(target_id, set())
        target = by_id.get(target_id)
        if target is None:
            raise ValueError(
                f"Current identity adjudication {adjudication_id} target is missing from "
                f"current canonical state: {target_id}"
            )

        target_ids = {
            str(provider): str(value)
            for provider, value in (target.get("IDs") or {}).items()
            if str(value or "").strip()
        }
        target_aliases = {
            str(provider): {str(value) for value in values or [] if str(value or "").strip()}
            for provider, values in (target.get("IDAliases") or {}).items()
        }

        if adjudication.get("ResolutionKind") == MERGE_KIND:
            statuses.append(
                {
                    "AdjudicationID": adjudication_id,
                    "Status": _validate_merge_against_state(
                        adjudication,
                        by_id=by_id,
                        token_owners=token_owners,
                        active_conflict_members=active_conflict_members,
                        mapping_claims=mapping_claims or [],
                        observation_season=observation_season,
                    ),
                }
            )
            continue

        if adjudication.get("ResolutionKind") == _UNOWNED_KIND:
            assignment = adjudication["ProviderAssignments"][0]
            token = (str(assignment["Provider"]), str(assignment["ExternalID"]))
            if token in active_conflict_tokens:
                raise ValueError(
                    f"Current identity adjudication {adjudication_id} cannot assign conflicted "
                    f"previously unowned token: {token}"
                )
            owners = token_owners.get(token, set())
            if owners - {target_id}:
                raise ValueError(
                    f"Current identity adjudication {adjudication_id} token is not unowned: "
                    f"{sorted(owners - {target_id})}"
                )
            for claim in mapping_claims or []:
                if (str(claim.get("Provider")), str(claim.get("ExternalID"))) != token:
                    continue
                first = int(claim.get("FirstObservedSeason") or observation_season)
                last = int(claim.get("LastObservedSeason") or first)
                if first <= observation_season <= last and str(claim.get("CanonicalPlayerID")) != target_id:
                    raise ValueError(
                        f"Current identity adjudication {adjudication_id} conflicts with "
                        f"historical mapping owner: {claim.get('CanonicalPlayerID')}"
                    )
            for anchor in adjudication["IndependentAnchors"]:
                provider = str(anchor["Provider"])
                external = str(anchor["ExternalID"])
                if external not in ({target_ids.get(provider)} | target_aliases.get(provider, set())):
                    raise ValueError(
                        f"Current identity adjudication {adjudication_id} missing verified "
                        f"target anchor {provider}/{external}"
                    )
            statuses.append({"AdjudicationID": adjudication_id, "Status": "active"})
            # The general target-values and undeclared-owner checks run below.
        elif adjudication.get("ResolutionKind") == _OVERRIDE_KIND:
            statuses.append(
                {
                    "AdjudicationID": adjudication_id,
                    "Status": _validate_override_against_state(
                        adjudication,
                        target=target,
                        target_ids=target_ids,
                        target_aliases=target_aliases,
                        by_id=by_id,
                        token_owners=token_owners,
                        active_conflict_tokens=active_conflict_tokens,
                        observation_season=observation_season,
                    ),
                }
            )
            continue

        if adjudication.get("ResolutionKind") != _UNOWNED_KIND:
            statuses.append({"AdjudicationID": adjudication_id, "Status": "active"})
        for assignment in adjudication["ProviderAssignments"]:
            provider = str(assignment["Provider"])
            external_id = str(assignment["ExternalID"])
            token = (provider, external_id)

            # A conflict whose parties are exactly the declared target and sources is
            # the split this decision resolves; any third party keeps it fail-closed.
            conflict_members = active_conflict_members.get(token, set())
            if token in active_conflict_tokens and (
                not conflict_members or not conflict_members <= source_ids | {target_id} | extra_ids
            ):
                raise ValueError(
                    f"Current identity adjudication {adjudication_id} cannot override active "
                    f"provider conflict: {provider}/{external_id}/{observation_season}"
                )

            target_values = set(target_aliases.get(provider, set()))
            if provider in target_ids:
                target_values.add(target_ids[provider])
            incompatible_target_values = target_values - {external_id}
            if incompatible_target_values:
                raise ValueError(
                    f"Current identity adjudication {adjudication_id} cannot assign "
                    f"{provider}/{external_id} because target {target_id} already has a different "
                    f"active {provider} value: {sorted(incompatible_target_values)}"
                )

            owners = token_owners.get(token, set())
            unexpected = owners - source_ids - {target_id} - extra_ids
            if unexpected:
                raise ValueError(
                    f"Current identity adjudication {adjudication_id} provider token "
                    f"{provider}/{external_id} has undeclared current owners: {sorted(unexpected)}"
                )

    return statuses


def _validate_merge_against_state(
    adjudication: dict[str, Any],
    *,
    by_id: dict[str, dict[str, Any]],
    token_owners: dict[tuple[str, str], set[str]],
    active_conflict_members: dict[tuple[str, str], set[str]],
    mapping_claims: list[dict[str, Any]],
    observation_season: int,
) -> str:
    """Verify a duplicate merge against the persisted records that already exist.

    A duplicate that is not persisted yet (or no longer is) is reported as
    ``superseded-by-upstream``; the identity builder verifies the same pair against
    the freshly built component before it merges anything.
    """
    adjudication_id = str(adjudication["AdjudicationID"])
    target_id = str(adjudication["TargetCanonicalPlayerID"])
    source_ids = {str(value) for value in adjudication["SourceCanonicalPlayerIDs"]}
    present = [
        str(value) for value in adjudication["DuplicateCanonicalPlayerIDs"] if str(value) in by_id
    ]
    if not present:
        return "superseded-by-upstream"
    pair = {target_id, *present}
    allowed = pair | source_ids
    for duplicate_id in present:
        verify_duplicate_pair(
            adjudication,
            view_from_record(by_id[target_id]),
            view_from_record(by_id[duplicate_id]),
            duplicate_id=duplicate_id,
        )
    contaminated = {
        (str(t["Provider"]), str(t["ExternalID"]))
        for t in adjudication.get("ContaminatedTokens") or []
    }
    for record_id in pair:
        for token in _record_tokens(by_id[record_id]):
            if token in contaminated:
                continue  # belongs to another person by review; never merged
            outsiders = token_owners.get(token, set()) - allowed
            if outsiders:
                raise ValueError(
                    f"Current identity adjudication {adjudication_id} token {token[0]}/{token[1]} "
                    f"has an owner outside the declared pair: {sorted(outsiders)}"
                )
            members = active_conflict_members.get(token, set())
            if members and not members <= allowed:
                raise ValueError(
                    f"Current identity adjudication {adjudication_id} token {token[0]}/{token[1]} "
                    f"is in an active conflict with a third identity: {sorted(members - allowed)}"
                )
            for claim in mapping_claims:
                if (str(claim.get("Provider")), str(claim.get("ExternalID"))) != token:
                    continue
                first = int(claim.get("FirstObservedSeason") or observation_season)
                last = int(claim.get("LastObservedSeason") or first)
                owner = str(claim.get("CanonicalPlayerID"))
                if first <= observation_season <= last and owner not in allowed:
                    raise ValueError(
                        f"Current identity adjudication {adjudication_id} token "
                        f"{token[0]}/{token[1]} has a historical mapping owner outside the "
                        f"declared pair: {owner}"
                    )
    return "active"


def _validate_override_against_state(
    adjudication: dict[str, Any],
    *,
    target: dict[str, Any],
    target_ids: dict[str, str],
    target_aliases: dict[str, set[str]],
    by_id: dict[str, dict[str, Any]],
    token_owners: dict[tuple[str, str], set[str]],
    active_conflict_tokens: set[tuple[str, str]],
    observation_season: int,
) -> str:
    adjudication_id = str(adjudication["AdjudicationID"])
    target_id = str(adjudication["TargetCanonicalPlayerID"])
    source_ids = {str(value) for value in adjudication["SourceCanonicalPlayerIDs"]}
    claim = adjudication["OverriddenUpstreamClaim"]
    provider = str(claim["Provider"])
    overridden_id = str(claim["ExternalID"])
    replacement = adjudication["ProviderAssignments"][0]
    replacement_id = str(replacement["ExternalID"])

    target_values = set(target_aliases.get(provider, set()))
    if provider in target_ids:
        target_values.add(target_ids[provider])

    # The named upstream claim is gone or changed: report instead of applying silently.
    if replacement_id in target_values:
        return "superseded-by-upstream"
    if overridden_id not in target_values:
        return "obsolete"
    if target_values - {overridden_id}:
        return "obsolete"

    replacement_token = (provider, replacement_id)
    if replacement_token in active_conflict_tokens:
        raise ValueError(
            f"Current identity adjudication {adjudication_id} cannot override active provider "
            f"conflict on the replacement token: {provider}/{replacement_id}/{observation_season}"
        )
    unexpected = token_owners.get(replacement_token, set()) - source_ids - {target_id}
    if unexpected:
        raise ValueError(
            f"Current identity adjudication {adjudication_id} replacement token "
            f"{provider}/{replacement_id} has undeclared current owners: {sorted(unexpected)}"
        )
    if not any(
        replacement_token in _record_tokens(by_id[source_id]) for source_id in source_ids
    ):
        raise ValueError(
            f"Current identity adjudication {adjudication_id} replacement token "
            f"{provider}/{replacement_id} is not carried by any declared source record"
        )

    target_position = str(target.get("Position") or "").strip()
    declared_position = str(adjudication.get("ReplacementPosition") or "").strip()
    if target_position and declared_position and target_position != declared_position:
        raise ValueError(
            f"Current identity adjudication {adjudication_id} declares replacement position "
            f"{declared_position} but target {target_id} has position {target_position}"
        )

    target_tokens = _record_tokens(target)
    source_tokens: set[tuple[str, str]] = set()
    for source_id in source_ids:
        source_tokens |= _record_tokens(by_id[source_id])
    for anchor in adjudication["IndependentAnchors"]:
        anchor_id = str(anchor["ExternalID"])
        if (str(anchor["Provider"]), anchor_id) not in target_tokens:
            raise ValueError(
                f"Current identity adjudication {adjudication_id} anchor "
                f"{anchor['Provider']}/{anchor_id} is not carried by target {target_id}"
            )
        if (str(anchor["SourceProvider"]), anchor_id) not in source_tokens:
            raise ValueError(
                f"Current identity adjudication {adjudication_id} anchor value {anchor_id} "
                f"is not carried by any declared source record under "
                f"{anchor['SourceProvider']}"
            )
    return "active"


def _record_tokens(record: dict[str, Any]) -> set[tuple[str, str]]:
    tokens: set[tuple[str, str]] = set()
    for provider, value in (record.get("IDs") or {}).items():
        external_id = str(value or "").strip()
        if external_id:
            tokens.add((str(provider), external_id))
    for provider, values in (record.get("IDAliases") or {}).items():
        for value in values or []:
            external_id = str(value or "").strip()
            if external_id:
                tokens.add((str(provider), external_id))
    return tokens
