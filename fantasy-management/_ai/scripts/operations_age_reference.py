"""Run-scoped explicit Age reference date for Fantasy Operations (Issue #1263 C9a).

A caller may provide FM_OPERATIONS_AS_OF_DATE=YYYY-MM-DD for a replay.
Otherwise, the single UTC run instant exported by the materialization runner
(FM_OPERATIONS_RUN_AT_UTC) is converted to the canonical LeagueTimeZone. Direct
standalone runs use their current UTC instant. This is not a source-refresh
heartbeat, an App timestamp or an FA-board lifecycle instant.
"""
from __future__ import annotations

import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

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
    instant_text = os.environ.get("FM_OPERATIONS_RUN_AT_UTC")
    if instant_text is not None:
        try:
            instant = datetime.fromisoformat(instant_text.replace("Z", "+00:00"))
        except ValueError as exc:
            raise OperationsAgeReferenceError("Invalid FM_OPERATIONS_RUN_AT_UTC") from exc
        if instant.tzinfo is None or instant.utcoffset() != timezone.utc.utcoffset(instant):
            raise OperationsAgeReferenceError("FM_OPERATIONS_RUN_AT_UTC requires a UTC-aware instant")
    else:
        instant = datetime.now(timezone.utc)
    return instant.astimezone(ZoneInfo(metadata["LeagueTimeZone"])).date()
