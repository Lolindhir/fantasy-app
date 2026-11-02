"""Run-scoped explicit Age reference date for Fantasy Operations (Issue #1263 C9a).

A caller may provide FM_OPERATIONS_AS_OF_DATE=YYYY-MM-DD for a replay.
Otherwise, the single UTC run instant exported by the materialization runner
(FM_OPERATIONS_RUN_AT_UTC) is converted to the canonical LeagueTimeZone. Direct
standalone runs use their current UTC instant. The run instant is shared with the FA-board evaluation clock, but Age
uses only its league-local date. Neither is an App/source freshness timestamp.
"""
from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path
from zoneinfo import ZoneInfo
from operations_run_instant import OperationsRunInstantError, run_instant_utc

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "tools"))
from league_metadata import load_league_metadata, data_meta_root  # noqa: E402


class OperationsAgeReferenceError(ValueError):
    pass


def age_reference_date(root: Path, league_id: str) -> date:
    override = os.environ.get("FM_OPERATIONS_AS_OF_DATE")
    if override is not None:
        try:
            if not override or date.fromisoformat(override).isoformat() != override:
                raise ValueError("expected YYYY-MM-DD")
            return date.fromisoformat(override)
        except ValueError as exc:
            raise OperationsAgeReferenceError("FM_OPERATIONS_AS_OF_DATE must be YYYY-MM-DD") from exc

    metadata = load_league_metadata(league_id, data_meta_root(root))
    try:
        instant = run_instant_utc()
    except OperationsRunInstantError as exc:
        raise OperationsAgeReferenceError(str(exc)) from exc
    return instant.astimezone(ZoneInfo(metadata["LeagueTimeZone"])).date()
