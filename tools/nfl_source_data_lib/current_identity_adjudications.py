from __future__ import annotations

from pathlib import Path
from typing import Any

from .common import load_json

_ADJUDICATION_PATH = Path("source-data/nfl/identities/current-identity-adjudications.json")
_SCHEMA_VERSION = 1
_REASSIGNMENT_KIND = "current-provider-reassignment"
_OVERRIDE_KIND = "upstream-claim-override"
_CONFLICT_POLICY_BY_KIND = {
    _REASSIGNMENT_KIND: "reject-active-conflict",
    _OVERRIDE_KIND: "override-named-upstream-claim",
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

        source_ids = _required_canonical_ids(
            item,
            "SourceCanonicalPlayerIDs",
            context=context,
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
        if not isinstance(assignments, list) or not assignments:
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

    decisions.sort(key=lambda item: item["AdjudicationID"])
    return decisions


def validate_current_identity_adjudications_against_state(
    adjudications: list[dict[str, Any]],
    canonical_players: list[dict[str, Any]],
    mapping_conflicts: list[dict[str, Any]],
    observation_season: int,
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

    statuses: list[dict[str, str]] = []
    for adjudication in adjudications:
        adjudication_id = str(adjudication["AdjudicationID"])
        target_id = str(adjudication["TargetCanonicalPlayerID"])
        source_ids = {str(value) for value in adjudication["SourceCanonicalPlayerIDs"]}
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

        if adjudication.get("ResolutionKind") == _OVERRIDE_KIND:
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

        statuses.append({"AdjudicationID": adjudication_id, "Status": "active"})
        for assignment in adjudication["ProviderAssignments"]:
            provider = str(assignment["Provider"])
            external_id = str(assignment["ExternalID"])
            token = (provider, external_id)

            # A conflict whose parties are exactly the declared target and sources is
            # the split this decision resolves; any third party keeps it fail-closed.
            conflict_members = active_conflict_members.get(token, set())
            if token in active_conflict_tokens and (
                not conflict_members or not conflict_members <= source_ids | {target_id}
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
            unexpected = owners - source_ids - {target_id}
            if unexpected:
                raise ValueError(
                    f"Current identity adjudication {adjudication_id} provider token "
                    f"{provider}/{external_id} has undeclared current owners: {sorted(unexpected)}"
                )

    return statuses


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
