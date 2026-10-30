"""Model registry: model ID -> implementation module (ADR-055).

An unknown ID, or an ID of the wrong kind, is an error; there is no default model and no fallback.
"""
from __future__ import annotations

from types import ModuleType

from .awards import v1 as awards_v1
from .grading import v1 as grading_v1
from .lifecycle import v1 as lifecycle_v1
from .salary import v1 as salary_v1
from .salary_cap import v1 as salary_cap_v1
from .standings import v1 as standings_v1

_MODULES: tuple[ModuleType, ...] = (salary_v1, salary_cap_v1, grading_v1, standings_v1, awards_v1, lifecycle_v1)
_REGISTRY: dict[str, ModuleType] = {module.MODEL_ID: module for module in _MODULES}

KINDS = ("awards", "grading", "lifecycle", "salary", "salary-cap", "standings")


class UnknownModelError(ValueError):
    """Raised for an unregistered model ID or an ID that belongs to another kind."""


def model_ids() -> list[str]:
    return sorted(_REGISTRY)


def get_model(model_id: str, kind: str | None = None) -> ModuleType:
    """Return the implementation module of ``model_id``; ``kind`` additionally checks the model kind."""
    module = _REGISTRY.get(model_id) if isinstance(model_id, str) else None
    if module is None:
        raise UnknownModelError(f"Unknown model ID {model_id!r}; registered: {', '.join(model_ids())}")
    if kind is not None and module.KIND != kind:
        raise UnknownModelError(f"Model {model_id!r} is a {module.KIND!r} model, not {kind!r}")
    return module


def describe(model_id: str) -> dict[str, object]:
    """ID, kind, PARAMS and docstring of a model, for snapshot provenance and reports."""
    module = get_model(model_id)
    return {"ModelId": module.MODEL_ID, "Kind": module.KIND, "Params": dict(module.PARAMS), "Description": module.__doc__}
