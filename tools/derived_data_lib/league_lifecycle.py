"""League lifecycle for one league, season and instant (ADR-073, Issue #1199).

Reads the canonical facts the lifecycle model needs and calls the model chosen in data-meta (Models.Lifecycle):

* ``data-source/leagues/<league>/seasons/<season>/league.json``  provider status and settings
* ``data-derived/league-drafts/<league>/<season>.json``          drafts of the season (product, not Drafts.json)
* ``data-source/nfl/schedules`` + ``game-finality``                regular-season kickoffs and final games (the Schedule.json derivation of tools/schedule_archive.py, not Schedule.json)
* ``week_finality``                                               FinalScoredWeek and LastLeagueWeek
* ``data-meta/<league>/metadata.json``                            Cap Deadline, buffer and the model choice

The instant is an explicit input; nothing is persisted. A missing or contradicting input raises ``LifecycleError`` and no
status is guessed. Contract: ``league-lifecycle.yaml``.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from data_roots import DATA_DERIVED_ROOT, DATA_SOURCE_ROOT
from league_metadata import LeagueMetadataError, data_meta_root, load_league_metadata, model_for, season_entry
from schedule_archive import ScheduleArchiveError, build_schedule

from .models.lifecycle.v1 import Facts, Game
from .models.registry import UnknownModelError, get_model
from .week_finality import WeekFinalityError, resolve_week_finality

UTC = timezone.utc


class LifecycleError(ValueError):
    """Missing or contradicting lifecycle input (fail closed)."""


def _read(path: Path, what: str) -> Any:
    if not path.is_file():
        raise LifecycleError(f"{what} missing: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise LifecycleError(f"{what} is not valid JSON: {path}: {exc}") from exc


def parse_instant(text: str, what: str) -> datetime:
    """ISO 8601 instant with an explicit offset or Z, as an aware UTC datetime."""
    try:
        moment = datetime.fromisoformat(str(text).strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise LifecycleError(f"{what} is not an ISO instant: {text!r}") from exc
    if moment.tzinfo is None:
        raise LifecycleError(f"{what} has no time zone: {text!r}")
    return moment.astimezone(UTC)


def _games(repo_root: Path, season: int) -> list[Game]:
    try:
        records = build_schedule(repo_root, season, {"REG"})
    except (ScheduleArchiveError, OSError, KeyError) as exc:
        raise LifecycleError(f"Canonical NFL schedule for {season} is unusable: {exc}") from exc
    games = []
    for record in records:
        week_label = str(record["gameWeek"])
        if not week_label.startswith("Week ") or not week_label[5:].isdigit():
            raise LifecycleError(f"Unexpected game week {week_label!r} in {record['gameID']}")
        epoch = str(record["gameTime_epoch"]).strip()
        kickoff = datetime.fromtimestamp(int(float(epoch)), UTC) if epoch else None
        games.append(Game(int(week_label[5:]), str(record["gameID"]), kickoff, str(record["gameStatus"]).startswith("Final")))
    return games


def load_facts(repo_root: Path, league_id: str, season: int) -> tuple[Any, Facts]:
    """Return (model module, facts) for the league season; all inputs are canonical, product or data-meta."""
    try:
        metadata = load_league_metadata(league_id, data_meta_root(repo_root))
        model = get_model(model_for(metadata, season, "Lifecycle"), "lifecycle")
        entry = season_entry(metadata, season)
    except (LeagueMetadataError, UnknownModelError) as exc:
        raise LifecycleError(str(exc)) from exc
    cap_deadline = parse_instant(entry["CapDeadline"], "CapDeadline") if "CapDeadline" in entry else None

    league_path = repo_root / DATA_SOURCE_ROOT / "leagues" / league_id / "seasons" / str(season) / "league.json"
    league = _read(league_path, "Canonical league source")
    if league.get("CanonicalLeagueID") != league_id or str(league.get("Season")) != str(season):
        raise LifecycleError(f"Canonical league source {league_path} belongs to another league or season")
    settings = league.get("Settings")
    if not isinstance(settings, dict):
        raise LifecycleError(f"No Settings in {league_path}")

    drafts_path = repo_root / DATA_DERIVED_ROOT / "league-drafts" / league_id / f"{season}.json"
    drafts = _read(drafts_path, "league-drafts product")
    if drafts.get("CanonicalLeagueID") != league_id or str(drafts.get("Season")) != str(season) or not isinstance(drafts.get("Drafts"), list):
        raise LifecycleError(f"league-drafts product {drafts_path} is not a draft list of {league_id}/{season}")

    try:
        finality = resolve_week_finality(repo_root, league_id, season)
    except WeekFinalityError as exc:
        raise LifecycleError(f"Week finality unavailable: {exc}") from exc

    facts = Facts(
        season=season,
        provider_status=str(league.get("Status") or ""),
        settings=settings,
        final_scored_week=int(finality["LeagueScoredWeek"]),
        last_league_week=int(finality["LastLeagueWeek"]),
        drafts=drafts["Drafts"],
        games=_games(repo_root, season),
        cap_deadline=cap_deadline,
        cap_buffer_days=int(entry.get("CapDeadlineBufferDays", 0)),
    )
    return model, facts


def resolve_lifecycle(repo_root: Path, league_id: str, season: int, at_utc: datetime) -> dict[str, Any]:
    """Lifecycle of ``league_id``/``season`` at ``at_utc`` (timezone-aware); computed, never persisted."""
    if at_utc.tzinfo is None:
        raise LifecycleError("AtUtc must be timezone-aware")
    model, facts = load_facts(repo_root, league_id, season)
    try:
        result = model.resolve(facts, at_utc)
    except ValueError as exc:
        raise LifecycleError(f"Lifecycle model {model.MODEL_ID} rejected the inputs: {exc}") from exc
    return {
        "CanonicalLeagueID": league_id,
        "Season": season,
        "Model": model.MODEL_ID,
        "AtUtc": at_utc.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        **result,
    }
