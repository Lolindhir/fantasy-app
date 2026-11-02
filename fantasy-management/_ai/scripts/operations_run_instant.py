"""One UTC evaluation instant per Fantasy Operations materialization attempt.

The runner exports FM_OPERATIONS_RUN_AT_UTC once before invoking all builders.
Direct standalone builds default to their current UTC instant; tests and replay
may fix the instant with the environment override. This is NOT a source
timestamp, content-change timestamp, or publication freshness heartbeat.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone


class OperationsRunInstantError(ValueError):
    """Invalid explicit materialization instant."""


def run_instant_utc() -> datetime:
    value = os.environ.get("FM_OPERATIONS_RUN_AT_UTC")
    if value is None:
        return datetime.now(timezone.utc)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise OperationsRunInstantError("Invalid FM_OPERATIONS_RUN_AT_UTC") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise OperationsRunInstantError("FM_OPERATIONS_RUN_AT_UTC requires a UTC-aware instant")
    return parsed.astimezone(timezone.utc)


def run_instant_iso_utc() -> str:
    return run_instant_utc().isoformat().replace("+00:00", "Z")
