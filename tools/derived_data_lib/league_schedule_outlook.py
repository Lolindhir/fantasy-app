"""Pure, consumer-neutral League Schedule Outlook V1 document assembly (Issue #1519).

This is deliberately NOT a file/materialization/writer entrypoint. The accepted
canonical facts and replayable season-statistics must first pass the existing
read-only Outlook preview's cut-off/finality checks. The future materializer
will choose the model through data-meta, rebuild its upstream inputs, call this
assembly function, and publish only through an explicitly approved bounded
Derived writer. No App file or older Outlook snapshot is an input.
"""
from __future__ import annotations

from typing import Any, Mapping

from .models.registry import get_model

PRODUCT = "league-schedule-outlook"
SCHEMA_VERSION = 1
RECONSTRUCTION = "reconstructed-from-accepted-sources"


class LeagueScheduleOutlookError(ValueError):
    """Incomplete, inconsistent or wrongly versioned schedule-outlook input."""


def assemble(preview: Mapping[str, Any], *, selected_model_id: str, input_fingerprint: str | None = None) -> dict[str, Any]:
    """Build a deterministic V1 Shared-Derived document from a verified as-of preview.

    Model selection is an explicit input. The caller must load it from the
    hand-maintained metadata for the selected league/season; no default or
    silent fallback is allowed. This helper intentionally cannot write files.

    ``input_fingerprint`` (optional, lowercase SHA-256 hex) is the materializer's digest of
    exactly the accepted inputs the cutoff depends on. It is deterministic provenance, never
    a clock value; without it the document keeps the I5b shape used by the restore candidate.
    """
    if not isinstance(preview, Mapping) or preview.get("PreviewOnly") is not True:
        raise LeagueScheduleOutlookError("Expected a validated read-only Outlook preview")
    get_model(selected_model_id, kind="schedule-outlook")
    league_id = preview.get("CanonicalLeagueID")
    season_id = preview.get("CanonicalLeagueSeasonID")
    season = preview.get("Season")
    if not isinstance(league_id, str) or not league_id or not isinstance(season_id, str) or not season_id:
        raise LeagueScheduleOutlookError("Missing canonical League/Season identity")
    if type(season) is not int or season < 1:
        raise LeagueScheduleOutlookError("Invalid canonical Season")
    models, asof = preview.get("Models"), preview.get("AsOf")
    regular, playoffs = preview.get("RegularSeason"), preview.get("Playoffs")
    if not isinstance(models, Mapping) or models.get("ScheduleOutlook") != selected_model_id:
        raise LeagueScheduleOutlookError("Selected model differs from verified preview model")
    if not isinstance(asof, Mapping):
        raise LeagueScheduleOutlookError("Missing as-of evidence")
    week, rating_week = asof.get("AfterWeek"), asof.get("RatingWeek")
    if type(week) is not int or week < 0 or (rating_week is not None and
                                               (type(rating_week) is not int or rating_week < 1 or rating_week > week)):
        raise LeagueScheduleOutlookError("Invalid after-week/rating-week boundary")
    if (week == 0) != (rating_week is None):
        raise LeagueScheduleOutlookError("Week 0 must not have ratings; a later cutoff must")
    season_stats = models.get("SeasonStats")
    if (rating_week is None and season_stats is not None) or (
        rating_week is not None and (not isinstance(season_stats, str) or not season_stats)
    ):
        raise LeagueScheduleOutlookError("Season-statistics model evidence missing or unexpected")
    if not isinstance(regular, Mapping) or regular.get("AfterWeek") != week or regular.get("RatingWeek") != rating_week:
        raise LeagueScheduleOutlookError("Regular-season preview cutoffs disagree")
    if not isinstance(regular.get("UpcomingMatchups"), list) or not isinstance(regular.get("Teams"), list):
        raise LeagueScheduleOutlookError("Missing regular-season outlook rows")
    if not isinstance(playoffs, Mapping) or not isinstance(playoffs.get("Format"), Mapping) or not isinstance(playoffs.get("Paths"), list):
        raise LeagueScheduleOutlookError("Missing reconstructed playoff format/paths")
    if type(playoffs["Format"].get("PlayoffStartWeek")) is not int:
        raise LeagueScheduleOutlookError("Missing canonical playoff start week")
    if input_fingerprint is not None and (
        not isinstance(input_fingerprint, str) or len(input_fingerprint) != 64
        or any(ch not in "0123456789abcdef" for ch in input_fingerprint)
    ):
        raise LeagueScheduleOutlookError("Input fingerprint must be a lowercase SHA-256 hex digest")
    if any(key in preview for key in ("ObservedAt", "GeneratedAt")):
        raise LeagueScheduleOutlookError("Volatile observation/build timestamps are not historical inputs")

    odds = preview.get("PlayoffOdds")
    odds_model = models.get("PlayoffOdds")
    if (odds is None) != (odds_model is None):
        raise LeagueScheduleOutlookError("PlayoffOdds block and model evidence must appear together")
    if odds is not None:
        get_model(odds_model, kind="playoff-odds")
        if not isinstance(odds, Mapping) or odds.get("Model") != odds_model or not isinstance(odds.get("Teams"), list):
            raise LeagueScheduleOutlookError("Invalid PlayoffOdds block")
    model_block = {"ScheduleOutlook": selected_model_id, "SeasonStats": season_stats}
    if odds_model is not None:
        model_block["PlayoffOdds"] = odds_model
    document = {
        "SchemaVersion": SCHEMA_VERSION,
        "Product": PRODUCT,
        "CanonicalLeagueID": league_id,
        "CanonicalLeagueSeasonID": season_id,
        "Season": season,
        "Models": model_block,
        "AsOf": {"AfterWeek": week, "RatingWeek": rating_week},
        "Provenance": ({"Reconstruction": RECONSTRUCTION} if input_fingerprint is None else
                       {"Reconstruction": RECONSTRUCTION, "InputFingerprint": input_fingerprint}),
        "RegularSeason": dict(regular),
        "Playoffs": dict(playoffs),
    }
    if odds is not None:
        document["PlayoffOdds"] = dict(odds)
    return document
