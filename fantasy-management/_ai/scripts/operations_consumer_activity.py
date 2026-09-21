"""Resolve Fantasy Operations consumer activity from shared NFL domain context."""

from __future__ import annotations

from typing import Any

VALID_RELEVANCE = {"required", "secondary", "inactive"}
VALID_PHASES = {
    "pre_regular_season",
    "regular_season",
    "postseason",
    "post_regular_season",
}


class ConsumerActivityPolicyError(RuntimeError):
    """Raised when consumer activity policy is invalid."""


def resolve_consumer_activity(
    policy: dict[str, Any] | None,
    *,
    phase: str | None,
) -> dict[str, Any]:
    if phase is not None and phase not in VALID_PHASES:
        raise ConsumerActivityPolicyError(f"Unsupported NFL phase: {phase}")

    modules = []
    if policy is not None:
        configured = policy.get("modules")
        if not isinstance(configured, list):
            raise ConsumerActivityPolicyError("consumer_activity.modules must be an array")
        seen: set[str] = set()
        for item in configured:
            if not isinstance(item, dict):
                raise ConsumerActivityPolicyError("consumer activity module must be an object")
            module_id = str(item.get("id") or "").strip()
            if not module_id or module_id in seen:
                raise ConsumerActivityPolicyError(
                    f"Invalid or duplicate consumer activity module id: {module_id!r}"
                )
            seen.add(module_id)

            default_relevance = item.get("default_relevance")
            if default_relevance not in VALID_RELEVANCE:
                raise ConsumerActivityPolicyError(
                    f"Invalid default relevance for {module_id}: {default_relevance!r}"
                )
            phase_policy = item.get("phase_policy") or {}
            if not isinstance(phase_policy, dict):
                raise ConsumerActivityPolicyError(
                    f"phase_policy for {module_id} must be an object"
                )
            unknown_phases = set(phase_policy) - VALID_PHASES
            if unknown_phases:
                raise ConsumerActivityPolicyError(
                    f"Unsupported phases for {module_id}: {sorted(unknown_phases)}"
                )
            for policy_phase, relevance in phase_policy.items():
                if relevance not in VALID_RELEVANCE:
                    raise ConsumerActivityPolicyError(
                        f"Invalid relevance for {module_id}/{policy_phase}: {relevance!r}"
                    )

            relevance = phase_policy.get(phase, default_relevance)
            reason = (
                f"phase_policy:{phase}"
                if phase is not None and phase in phase_policy
                else "default_policy"
            )
            modules.append(
                {
                    "id": module_id,
                    "relevance": relevance,
                    "active": relevance != "inactive",
                    "reason": reason,
                }
            )

    return {
        "schema_version": 1,
        "phase": phase,
        "modules": modules,
        "required_module_ids": [
            item["id"] for item in modules if item["relevance"] == "required"
        ],
        "secondary_module_ids": [
            item["id"] for item in modules if item["relevance"] == "secondary"
        ],
        "inactive_module_ids": [
            item["id"] for item in modules if item["relevance"] == "inactive"
        ],
    }


def apply_freshness_readiness(
    consumer_activity: dict[str, Any],
    *,
    freshness_status: str,
    monitoring_allowed: bool,
    no_event_conclusion_allowed: bool,
) -> dict[str, Any]:
    if freshness_status not in {"ok", "degraded", "blocked"}:
        raise ConsumerActivityPolicyError(
            f"Unsupported freshness status: {freshness_status}"
        )

    modules = []
    for item in consumer_activity["modules"]:
        module = dict(item)
        if not module["active"]:
            module.update(
                {
                    "runtime_status": "inactive_by_policy",
                    "execution_allowed": False,
                    "no_event_conclusion_allowed": None,
                }
            )
        elif not monitoring_allowed:
            module.update(
                {
                    "runtime_status": "blocked_by_freshness",
                    "execution_allowed": False,
                    "no_event_conclusion_allowed": False,
                }
            )
        elif freshness_status == "degraded":
            module.update(
                {
                    "runtime_status": "active_degraded",
                    "execution_allowed": True,
                    "no_event_conclusion_allowed": no_event_conclusion_allowed,
                }
            )
        else:
            module.update(
                {
                    "runtime_status": "active_ready",
                    "execution_allowed": True,
                    "no_event_conclusion_allowed": no_event_conclusion_allowed,
                }
            )
        modules.append(module)

    return {
        **consumer_activity,
        "modules": modules,
    }
