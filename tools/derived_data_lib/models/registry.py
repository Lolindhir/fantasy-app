"""Model registry: model ID -> implementation module (ADR-055).

An unknown ID, or an ID of the wrong kind, is an error; there is no default model and no fallback.
"""
from __future__ import annotations

from types import ModuleType

from .auto_cut import v1 as auto_cut_v1
from .awards import v1 as awards_v1
from .awards import v2 as awards_v2
from .awards import v3 as awards_v3
from .grading import v1 as grading_v1
from .lifecycle import v1 as lifecycle_v1
from .playoff_odds import v1 as playoff_odds_v1, v2 as playoff_odds_v2
from .repairability import v1 as repairability_v1
from .rivalry import v1 as rivalry_v1
from .rivalry import v2 as rivalry_v2
from .roster_cap import v1 as roster_cap_v1
from .salary import v1 as salary_v1
from .salary_cap import v1 as salary_cap_v1
from .season_stats import v1 as season_stats_v1
from .schedule_outlook import v1 as schedule_outlook_v1
from .schedule_outlook import v2 as schedule_outlook_v2
from .standings import v1 as standings_v1
from .team_range import v1 as team_range_v1
from .weekly_recap import v1 as weekly_recap_v1
from .weekly_recap import v2 as weekly_recap_v2
from .win_prob import v1 as win_prob_v1

_MODULES: tuple[ModuleType, ...] = (salary_v1, salary_cap_v1, roster_cap_v1, auto_cut_v1, grading_v1, standings_v1, awards_v1, awards_v2, awards_v3, lifecycle_v1, repairability_v1, team_range_v1, win_prob_v1, season_stats_v1, schedule_outlook_v1, schedule_outlook_v2, playoff_odds_v1, playoff_odds_v2, rivalry_v1, rivalry_v2, weekly_recap_v1, weekly_recap_v2)
_REGISTRY: dict[str, ModuleType] = {module.MODEL_ID: module for module in _MODULES}

KINDS = ("auto-cut", "awards", "grading", "lifecycle", "playoff-odds", "repairability", "rivalry", "roster-cap", "salary", "salary-cap", "schedule-outlook", "season-stats", "standings", "team-range", "weekly-recap", "win-prob")


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
