#!/usr/bin/env python3
"""Read-only resolution of the disabled Weekly League Review trigger (#1263 C8i).

FinalScoredWeek comes from the same shared canonical lifecycle and Week-Finality
model as the App generator. This module never reads App League.json or writes
job State, activates the disabled job, or treats an advanced week as proof of
the separately retained minimum-data-age/freshness and dependency gates.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from canonical_league_ownership import (  # noqa: E402
    CanonicalOwnershipError,
    resolve_current_canonical_season,
)
from canonical_league_lifecycle import (  # noqa: E402
    LeagueLifecycleUnavailable,
    resolve_lifecycle_state,
)


class WeeklyReviewTriggerUnavailable(RuntimeError):
    """Trigger source evidence is missing, invalid or contradictory (fail closed)."""


def _instant(value: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise WeeklyReviewTriggerUnavailable("Explicit at_utc ISO 8601 instant is required.")
    try:
        instant = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise WeeklyReviewTriggerUnavailable(f"Invalid at_utc instant: {value!r}") from exc
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise WeeklyReviewTriggerUnavailable("at_utc must be timezone-aware.")
    return instant


def _validate_trigger(trigger: dict[str, Any]) -> str:
    if not isinstance(trigger, dict):
        raise WeeklyReviewTriggerUnavailable("Trigger must be an object.")
    if (
        trigger.get("type") != "league_week_finalized"
        or trigger.get("source_type") != "canonical_lifecycle"
        or trigger.get("final_week_field") != "FinalScoredWeek"
        or "league_source" in trigger
    ):
        raise WeeklyReviewTriggerUnavailable("Weekly review must use canonical lifecycle FinalScoredWeek.")
    league_id = trigger.get("canonical_league_id")
    if not isinstance(league_id, str) or not league_id.strip() or "/" in league_id or ".." in league_id:
        raise WeeklyReviewTriggerUnavailable("Invalid canonical_league_id.")
    age = trigger.get("minimum_data_age_minutes")
    if isinstance(age, bool) or not isinstance(age, int) or age < 0:
        raise WeeklyReviewTriggerUnavailable("Invalid minimum_data_age_minutes.")
    if trigger.get("retry_when_not_ready") is not True:
        raise WeeklyReviewTriggerUnavailable("Weekly review must retain retry_when_not_ready.")
    return league_id


def _advanced(season: int, final_week: int, last_processed_key: str | None) -> bool:
    if final_week == 0:
        return False
    if last_processed_key is None:
        return True
    if not isinstance(last_processed_key, str):
        raise WeeklyReviewTriggerUnavailable("Invalid last_processed_key.")
    match = re.fullmatch(r"(\d{4})-week-(\d{1,2})", last_processed_key)
    if not match:
        raise WeeklyReviewTriggerUnavailable("Invalid last_processed_key: expected season-week-<week>.")
    prev_season, prev_week = map(int, match.groups())
    if prev_week < 1 or prev_week > 25 or prev_season > season:
        raise WeeklyReviewTriggerUnavailable("last_processed_key is impossible or from a future season.")
    return prev_season < season or final_week > prev_week


def resolve_trigger(
    root: Path,
    trigger: dict[str, Any],
    *,
    at_utc: str,
    last_processed_key: str | None = None,
) -> dict[str, Any]:
    """Evaluate only canonical week advancement, not freshness, eligibility or writes."""
    league_id = _validate_trigger(trigger)
    instant = _instant(at_utc)
    try:
        season = resolve_current_canonical_season(root, canonical_league_id=league_id)
        lifecycle = resolve_lifecycle_state(root, league_id, season, instant)
    except (CanonicalOwnershipError, LeagueLifecycleUnavailable) as exc:
        raise WeeklyReviewTriggerUnavailable(str(exc)) from exc
    if not isinstance(lifecycle, dict) or (
        lifecycle.get("CanonicalLeagueID") != league_id
        or lifecycle.get("Season") != season
    ):
        raise WeeklyReviewTriggerUnavailable("Canonical lifecycle league/season identity mismatch.")
    final_week = lifecycle.get("FinalScoredWeek")
    if isinstance(final_week, bool) or not isinstance(final_week, int) or final_week < 0 or final_week > 25:
        raise WeeklyReviewTriggerUnavailable("Canonical FinalScoredWeek is missing or invalid.")
    is_new = _advanced(season, final_week, last_processed_key)
    return {
        "canonical_league_id": league_id,
        "season": season,
        "at_utc": instant.isoformat(),
        "final_scored_week": final_week,
        "candidate_key": f"{season}-week-{final_week}" if final_week > 0 else None,
        "advanced_beyond_last_processed": is_new,
        "freshness_gate_evaluated": False,
        "job_activation_or_write_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--job", type=Path, default=Path("fantasy-management/automation/jobs/weekly-league-review.json"))
    parser.add_argument("--at-utc", required=True, help="Explicit timezone-aware ISO 8601 evaluation instant")
    parser.add_argument("--last-processed-key", default=None)
    args = parser.parse_args()
    root = args.repo_root.resolve()
    path = args.job if args.job.is_absolute() else root / args.job
    try:
        job = json.loads(path.read_text(encoding="utf-8"))
        if job.get("id") != "weekly-league-review" or job.get("enabled") is not False:
            raise WeeklyReviewTriggerUnavailable("Only the disabled weekly-league-review definition is supported.")
        result = resolve_trigger(root, job["trigger"], at_utc=args.at_utc, last_processed_key=args.last_processed_key)
    except (OSError, ValueError, KeyError, WeeklyReviewTriggerUnavailable) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
