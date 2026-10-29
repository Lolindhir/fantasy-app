"""Registry-driven NFL season-phase gate for external source fetchers (contract: external-source-data.yaml).

The per-dataset seasonPolicy in data-source/external-registry.json owns which phases a dataset is requested in:
a phase marked `inactive` means no request is made. The phase itself comes from the shared resolver over the
canonical NFL schedule (tools/nfl_season_context.py). Fail-closed towards not requesting.
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1]
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from external_source.registry import get_dataset, load_registry  # noqa: E402
from nfl_season_context import NflSeasonContextError, resolve_nfl_season_context  # noqa: E402


def skip_reason(repo_root: Path, dataset_id: str, season: int, as_of: datetime) -> str | None:
    """Return why the dataset must not be requested now, or None when its current phase is not inactive.

    A season without a canonical schedule is not an active phase either.
    """

    dataset = get_dataset(load_registry(repo_root), dataset_id)
    try:
        context = resolve_nfl_season_context(repo_root, as_of=as_of, season=season)
    except NflSeasonContextError as exc:
        return f"no canonical NFL schedule for season {season} ({exc})"
    phase = context["phase"]
    if dataset["seasonPolicy"].get(phase) == "inactive":
        return f"NFL season {season} is in phase {phase}, registry seasonPolicy of {dataset_id} marks it inactive"
    return None
