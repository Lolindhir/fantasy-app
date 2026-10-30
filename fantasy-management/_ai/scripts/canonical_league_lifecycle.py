"""Lifecycle input of Fantasy Management from the shared lifecycle model (ADR-073, Issue #1199 step 5).

Fantasy Management no longer interprets the League.json Status/Phase of the App delivery: it asks the central
lifecycle function (tools/derived_data_lib/league_lifecycle.py) for the league season at an explicit instant, so App and
Management share one answer. Missing or contradicting canonical inputs raise ``LeagueLifecycleUnavailable``.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class LeagueLifecycleUnavailable(RuntimeError):
    """The shared lifecycle cannot be resolved from canonical inputs (fail closed)."""


def _parse_instant(value: Any) -> datetime:
    text = str(value or "").strip()
    if not text:
        raise LeagueLifecycleUnavailable("No instant (generated_at) to resolve the lifecycle at.")
    try:
        moment = datetime.fromisoformat(text[:-1] + "+00:00" if text.endswith("Z") else text)
    except ValueError as exc:
        raise LeagueLifecycleUnavailable(f"Instant is not ISO 8601: {text!r}") from exc
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def resolve_lifecycle_state(root: Path, canonical_league_id: str, season: int, at: Any) -> dict[str, Any]:
    """Lifecycle of ``canonical_league_id``/``season`` at ``at`` (ISO text or datetime); computed, never persisted."""

    tools = Path(root).resolve() / "tools"
    if str(tools) not in sys.path:
        sys.path.insert(0, str(tools))
    try:
        from derived_data_lib.league_lifecycle import LifecycleError, resolve_lifecycle
    except ImportError as exc:  # pragma: no cover - repository layout error
        raise LeagueLifecycleUnavailable(f"Lifecycle module is not importable from {tools}: {exc}") from exc
    instant = at if isinstance(at, datetime) else _parse_instant(at)
    try:
        return resolve_lifecycle(Path(root).resolve(), canonical_league_id, int(season), instant)
    except LifecycleError as exc:
        raise LeagueLifecycleUnavailable(str(exc)) from exc
