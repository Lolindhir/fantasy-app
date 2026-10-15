"""Draft identity, provider-draft binding and completed-draft definitions (league-history.yaml, ADR-057).

Faithful port of the draft identity logic that lives in public/requests/utils/league today:
DraftUtils.psm1 (identity, Get-SleeperDraftMap, Resolve-DraftTypeFromSleeperDraft),
DraftHistoryUtils.psm1 and DraftHistoryEmptyDefinitionsFix.psm1 (completed draft definitions).
Behaviour is kept exactly - including the two different classification paths for current and
completed drafts - because the shadow parity of Issue #999 step 4 is exact.

Provider drafts use the Sleeper-shaped payload of tools/draft_canonical_consumer.py
(draft_id, season, type, status, start_time, created, settings, metadata, draft_order,
slot_to_roster_id).
"""
from __future__ import annotations

import re
from typing import Any

FREE_AGENT_PATTERN = re.compile(r"free[_\s-]?agent|freeagent|waiver|\bfa\b")
DRAFT_TYPE_TEXT_PROPERTIES = ("type", "name", "status", "season")
FALSY_SETTING_VALUES = {"0", "false", "no", "off", "none", "null"}


class DraftIdentityError(ValueError):
    """Raised when draft identity or provider binding is inconsistent (fail closed)."""


def ps_string(value: Any) -> str:
    """PowerShell [string] cast for the scalar values found in provider payloads."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "True" if value else "False"
    return str(value)


# --------------------------------------------------------------------------- identity


def draft_instance(config: dict[str, Any]) -> int:
    instance = int(config.get("DraftInstance", 1))
    if instance < 1:
        raise DraftIdentityError(f"DraftInstance must be at least 1 for draft type '{config.get('DraftType')}'.")
    return instance


def draft_code(draft_type: str, instance: int = 1) -> str:
    if instance < 1:
        raise DraftIdentityError(f"DraftInstance must be at least 1 for draft type '{draft_type}'.")
    return draft_type if instance == 1 else f"{draft_type}_{instance}"


def draft_key(season: str | int, draft_type: str, instance: int = 1) -> str:
    return f"{season}_{draft_code(draft_type, instance)}"


def pick_key(key: str, round_no: int, original_owner_roster_id: int) -> str:
    return f"{key}_R{int(round_no)}_OO{int(original_owner_roster_id)}"


def identity_from_key(key: str, configs: list[dict[str, Any]]) -> dict[str, Any]:
    if not key or not key.strip():
        raise DraftIdentityError("DraftKey must not be empty.")
    separator = key.find("_")
    if separator <= 0:
        raise DraftIdentityError(f"DraftKey '{key}' does not contain a season prefix.")
    season = key[:separator]
    matches = []
    for config in configs:
        draft_type = str(config["DraftType"])
        instance = draft_instance(config)
        expected = draft_key(season, draft_type, instance)
        if expected == key:
            matches.append({
                "Season": season,
                "DraftType": draft_type,
                "DraftInstance": instance,
                "DraftCode": draft_code(draft_type, instance),
                "DraftKey": expected,
            })
    if len(matches) != 1:
        raise DraftIdentityError(f"DraftKey '{key}' could not be resolved to exactly one configured draft instance.")
    return matches[0]


def sorted_configs(configs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(configs, key=lambda config: int(config["DraftNo"]))


def assert_draft_type_configs(configs: list[dict[str, Any]]) -> None:
    identity_keys: set[str] = set()
    draft_nos: set[int] = set()
    bindings: dict[str, str] = {}
    for config in configs:
        draft_type = str(config.get("DraftType") or "")
        if not draft_type.strip():
            raise DraftIdentityError("DraftType must not be empty.")
        instance = draft_instance(config)
        identity = f"{draft_type}|{instance}"
        if identity in identity_keys:
            raise DraftIdentityError(f"Duplicate draft identity configured: DraftType '{draft_type}', DraftInstance '{instance}'.")
        identity_keys.add(identity)
        draft_no = int(config["DraftNo"])
        if draft_no < 1:
            raise DraftIdentityError(f"DraftNo must be at least 1 for draft '{identity}'.")
        if draft_no in draft_nos:
            raise DraftIdentityError(f"Duplicate DraftNo '{draft_no}' in the league metadata (data-meta).")
        draft_nos.add(draft_no)
        for provider_id in (config.get("SleeperDraftIDs") or {}).values():
            provider_id = ps_string(provider_id)
            if not provider_id.strip():
                continue
            if provider_id in bindings:
                raise DraftIdentityError(f"Sleeper draft '{provider_id}' is bound to multiple configured draft instances.")
            bindings[provider_id] = identity


def configured_sleeper_draft_id(config: dict[str, Any], season: str) -> str | None:
    value = (config.get("SleeperDraftIDs") or {}).get(season)
    if value is None or not ps_string(value).strip():
        return None
    return ps_string(value)


# ----------------------------------------------------------------- provider draft helpers


def is_complete(provider_draft: dict[str, Any] | None) -> bool:
    return provider_draft is not None and ps_string(provider_draft.get("status")) == "complete"


def draft_created_sort_key(draft: dict[str, Any]) -> tuple[Any, ...]:
    created = draft.get("created")
    return ((0, 0) if created is None else (1, int(created)), ps_string(draft.get("draft_id")))


def _draft_text_parts(draft: dict[str, Any], *, with_metadata_names: bool) -> list[str]:
    parts = [ps_string(draft[name]) for name in DRAFT_TYPE_TEXT_PROPERTIES if name in draft]
    metadata = draft.get("metadata")
    if metadata:
        for name, value in metadata.items():
            if with_metadata_names:
                parts.append(ps_string(name))
            parts.append(ps_string(value))
    return parts


def resolve_draft_type_from_provider_draft(draft: dict[str, Any], configs: list[dict[str, Any]]) -> str | None:
    """DraftUtils.psm1::Resolve-DraftTypeFromSleeperDraft."""
    text = " ".join(part for part in _draft_text_parts(draft, with_metadata_names=False) if part.strip()).lower()
    if FREE_AGENT_PATTERN.search(text):
        if any(str(config["DraftType"]) == "Free_Agent" for config in configs):
            return "Free_Agent"
    if "rookie" in text:
        if any(str(config["DraftType"]) == "Rookie" for config in configs):
            return "Rookie"
    return None


def provider_draft_map(configs: list[dict[str, Any]], provider_drafts: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """DraftUtils.psm1::Get-SleeperDraftMap for the drafts of one season: DraftKey -> provider draft."""
    assert_draft_type_configs(configs)
    result: dict[str, dict[str, Any]] = {}
    if not provider_drafts:
        return result
    seen: set[str] = set()
    for draft in provider_drafts:
        draft_id = ps_string(draft.get("draft_id"))
        if draft_id in seen:
            raise DraftIdentityError(f"Duplicate draft_id '{draft_id}' in Sleeper league drafts.")
        seen.add(draft_id)

    by_season: dict[str, list[dict[str, Any]]] = {}
    for draft in provider_drafts:
        by_season.setdefault(ps_string(draft.get("season")), []).append(draft)

    for season, group in by_season.items():
        season_drafts = sorted(group, key=draft_created_sort_key)
        unbound_configs = list(sorted_configs(configs))
        unbound_drafts = list(season_drafts)

        for config in sorted_configs(configs):
            configured_id = configured_sleeper_draft_id(config, season)
            if configured_id is None:
                continue
            matches = [draft for draft in unbound_drafts if ps_string(draft.get("draft_id")) == configured_id]
            if len(matches) != 1:
                raise DraftIdentityError(
                    f"Configured Sleeper draft '{configured_id}' for season '{season}' was not found exactly once "
                    "in the provider response; explicit bindings are authoritative and will not fall back to another draft."
                )
            key = draft_key(season, str(config["DraftType"]), draft_instance(config))
            result[key] = matches[0]
            unbound_drafts = [draft for draft in unbound_drafts if ps_string(draft.get("draft_id")) != configured_id]
            unbound_configs = [item for item in unbound_configs if item is not config]

        for draft in list(unbound_drafts):
            draft_type = resolve_draft_type_from_provider_draft(draft, unbound_configs)
            candidates: list[dict[str, Any]] = []
            if draft_type:
                candidates = sorted(
                    (config for config in unbound_configs if str(config["DraftType"]) == draft_type),
                    key=lambda config: (draft_instance(config), int(config["DraftNo"])),
                )
            if not candidates:
                candidates = sorted_configs(unbound_configs)
            if not candidates:
                continue  # PowerShell warns and skips: no configured draft instance remains.
            config = candidates[0]
            key = draft_key(season, str(config["DraftType"]), draft_instance(config))
            result[key] = draft
            unbound_configs = [item for item in unbound_configs if item is not config]
    return result


# ---------------------------------------------------------- completed draft definitions


def configured_rounds_from_provider_draft(draft: dict[str, Any]) -> int | None:
    settings = draft.get("settings")
    if settings is not None:
        rounds = settings.get("rounds")
        if rounds is not None and ps_string(rounds).strip():
            return int(rounds)
    rounds = draft.get("rounds")
    if rounds is not None and ps_string(rounds).strip():
        return int(rounds)
    return None


def max_configured_rounds(configs: list[dict[str, Any]]) -> int:
    values = [int(config["Rounds"]) for config in configs if config.get("Rounds") is not None and int(config["Rounds"]) > 0]
    return max(values) if values else 0


def _truthy_setting(value: Any) -> bool:
    if value is None:
        return False
    text = ps_string(value).strip().lower()
    if not text:
        return False
    return text not in FALSY_SETTING_VALUES


def settings_classification(draft: dict[str, Any]) -> str | None:
    settings = draft.get("settings")
    if settings is None:
        return None
    for name, raw in settings.items():
        key = ps_string(name).lower()
        value = ps_string(raw).strip().lower()
        truthy = _truthy_setting(raw)
        if "rookie" in key and truthy:
            return "Rookie"
        if "veteran" in key and truthy:
            return "Veteran"
        if "player" in key or "restriction" in key or "pool" in key:
            if "rookie" in value:
                return "Rookie"
            if "veteran" in value:
                return "Veteran"
            if value in ("all", "any", "none"):
                return "Free_Agent"
            if "unrestricted" in value or "no restriction" in value:
                return "Free_Agent"
            if "free agent" in value or "free_agent" in value or "freeagent" in value:
                return "Free_Agent"
    return None


def configured_type_or_default(
    draft_type: str,
    configs: list[dict[str, Any]],
    default_draft_no: int,
    default_rounds: int,
    instance: int = 1,
) -> dict[str, Any]:
    for config in configs:
        if str(config["DraftType"]) == draft_type and draft_instance(config) == instance:
            return config
    return {
        "DraftType": draft_type,
        "DraftInstance": instance,
        "DraftNo": default_draft_no,
        "Rounds": default_rounds,
        "OrderSource": "Sleeper",
    }


def resolve_history_type(draft: dict[str, Any], configs: list[dict[str, Any]], fallback: dict[str, Any] | None) -> str:
    """DraftHistoryUtils.psm1::Resolve-DraftHistoryTypeFromSleeperDraft."""
    classified = settings_classification(draft)
    if classified:
        return classified
    text = " ".join(part for part in _draft_text_parts(draft, with_metadata_names=True) if part.strip()).lower()
    if "rookie" in text:
        return "Rookie"
    if "veteran" in text or " vet " in text:
        return "Veteran"
    if "free agent" in text or "free_agent" in text or "freeagent" in text:
        return "Free_Agent"
    if "startup" in text or "start up" in text:
        return "Free_Agent"
    rounds = configured_rounds_from_provider_draft(draft)
    max_rounds = max_configured_rounds(configs)
    if rounds is not None and max_rounds > 0 and rounds > max_rounds:
        return "Free_Agent"
    if fallback is not None:
        return str(fallback["DraftType"])
    return "Veteran"


def completed_draft_definitions(
    season: str,
    provider_drafts: list[dict[str, Any]],
    configs: list[dict[str, Any]],
    provider_league_id: str | None,
) -> list[dict[str, Any]]:
    """DraftHistoryEmptyDefinitionsFix.psm1::Get-SleeperCompletedDraftDefinitionsForSeasonSafe.

    Completed drafts of one season, classified by the history heuristics (explicit SleeperDraftIDs
    bindings are not used on this path, exactly as today), numbered per (Season, DraftType).
    """
    if not provider_drafts:
        return []
    fallback_types = sorted_configs(configs)
    ordered = sorted(provider_drafts, key=draft_created_sort_key)
    definitions: list[dict[str, Any]] = []
    completed_index = 0
    for draft in ordered:
        if not is_complete(draft):
            continue
        completed_index += 1
        fallback = fallback_types[completed_index - 1] if completed_index - 1 < len(fallback_types) else None
        draft_type = resolve_history_type(draft, configs, fallback) or "Veteran"
        draft_season = ps_string(draft.get("season")) or season
        rounds = configured_rounds_from_provider_draft(draft)
        if rounds is None or rounds <= 0:
            rounds = 0
        config = configured_type_or_default(draft_type, configs, completed_index, rounds)
        definitions.append({
            "ProviderLeagueID": provider_league_id,
            "Season": draft_season,
            "DraftType": draft_type,
            "DraftInstance": 1,
            "DraftCode": draft_type,
            "DraftNo": completed_index,
            "DraftKey": draft_key(draft_season, draft_type),
            "DraftTypeConfig": config,
            "ProviderDraft": draft,
            "TypeOccurrence": 1,
            "TypeCount": 1,
        })
    if not definitions:
        return []
    return _with_type_occurrences(definitions, configs)


def _with_type_occurrences(definitions: list[dict[str, Any]], configs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for definition in definitions:
        groups.setdefault((definition["Season"], definition["DraftType"]), []).append(definition)
    for items in groups.values():
        items.sort(key=lambda item: item["DraftNo"])
        count = len(items)
        for index, item in enumerate(items):
            instance = index + 1
            fallback_rounds = int(item["DraftTypeConfig"].get("Rounds") or 0)
            item["DraftInstance"] = instance
            item["DraftCode"] = draft_code(item["DraftType"], instance)
            item["DraftKey"] = draft_key(item["Season"], item["DraftType"], instance)
            item["DraftTypeConfig"] = configured_type_or_default(
                item["DraftType"], configs, item["DraftNo"], fallback_rounds, instance
            )
            item["TypeOccurrence"] = instance
            item["TypeCount"] = count
    return sorted(definitions, key=lambda item: (int(item["Season"]), item["DraftNo"], item["DraftKey"]))
