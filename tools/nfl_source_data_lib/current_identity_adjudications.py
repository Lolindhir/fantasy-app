from __future__ import annotations

from pathlib import Path
from typing import Any

from .common import load_json

_ADJUDICATION_PATH = Path("source-data/nfl/identities/current-identity-adjudications.json")
_SCHEMA_VERSION = 1
_RESOLUTION_KIND = "current-provider-reassignment"
_CONFLICT_POLICY = "reject-active-conflict"


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
        if resolution_kind != _RESOLUTION_KIND:
            raise ValueError(
                f"{context}.ResolutionKind must be '{_RESOLUTION_KIND}'"
            )

        conflict_policy = _required_text(item, "ConflictPolicy", context=context)
        if conflict_policy != _CONFLICT_POLICY:
            raise ValueError(
                f"{context}.ConflictPolicy must be '{_CONFLICT_POLICY}'"
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
            }
        )

    decisions.sort(key=lambda item: item["AdjudicationID"])
    return decisions


def validate_current_identity_adjudications_against_state(
    adjudications: list[dict[str, Any]],
    canonical_players: list[dict[str, Any]],
    mapping_conflicts: list[dict[str, Any]],
    observation_season: int,
) -> None:
    """Fail closed if a proposed current reassignment contradicts active identity state.

    This validator deliberately does not apply decisions. It provides the safety
    boundary required before a future identity-builder integration:
    - the target may not already carry a different active value for an assigned provider;
    - an assigned provider token may not be owned by an undeclared third canonical identity;
    - an assigned token may not overlap an active provider conflict.

    The declared source CanonicalPlayerIDs are the only existing owners that may be
    superseded by a future application step.
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
    for conflict in mapping_conflicts:
        provider = str(conflict.get("Provider") or "").strip()
        external_id = str(conflict.get("ExternalID") or "").strip()
        if not provider or not external_id:
            continue
        first_raw = conflict.get("FirstObservedSeason")
        last_raw = conflict.get("LastObservedSeason")
        if first_raw is None and last_raw is None:
            active_conflict_tokens.add((provider, external_id))
            continue
        first = int(first_raw if first_raw is not None else observation_season)
        last = int(last_raw if last_raw is not None else first)
        if first <= observation_season <= last:
            active_conflict_tokens.add((provider, external_id))

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

        for assignment in adjudication["ProviderAssignments"]:
            provider = str(assignment["Provider"])
            external_id = str(assignment["ExternalID"])
            token = (provider, external_id)

            if token in active_conflict_tokens:
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
