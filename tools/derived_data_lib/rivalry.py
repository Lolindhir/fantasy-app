"""Pure assembly of the league-rivalry product (Issue #1455, .ai-context/manual/league-rivalry.yaml).

Reads only the computed matchup context of every season (canonical matchups with the bracket label, ADR-075), the canonical season status and
data-meta; no App file. The counting rules are the model ``rivalry-v1``; this module collects the final matchups per season, applies the model of
the season and builds the per-team, per-opponent records for the filters ``all``, ``regular`` and ``playoffs``.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from data_roots import DATA_SOURCE_ROOT
from league_metadata import data_meta_root, load_league_metadata, model_for, validate_against_manifest

from .matchup_context import MatchupContextError, resolve_matchups
from .models.registry import get_model

PRODUCT = "league-rivalry"
SCHEMA_VERSION = 1
MODEL_KIND = "Rivalry"


class RivalryError(ValueError):
    """Incomplete or contradicting evidence (fail closed)."""


def season_games(matchups: dict[str, Any], model: Any, season_complete: bool) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Counted games of one season as directional rows plus the counters of excluded playoff games.

    A directional row is ``(TeamID, OpponentID, game)`` per participant. Final matchups without a result or without exactly two participants
    are skipped, like the former frontend util.
    """
    rows: list[dict[str, Any]] = []
    stats = {"CountedRegular": 0, "CountedPlayoffs": 0, "ExcludedConsolation": 0, "ExcludedUnclassified": 0, "ExcludedSeasonIncomplete": 0}
    season = str(matchups["Season"])
    for week in matchups["Weeks"]:
        stage = week["Stage"]
        for matchup in week["Matchups"]:
            if matchup["CompletionState"] != "final" or not matchup.get("Result"):
                continue
            participants = matchup["Participants"]
            if len(participants) != 2:
                continue
            bracket = matchup.get("Bracket")
            if not model.counts(stage, bracket, season_complete):
                if stage == "playoffs":
                    if not season_complete:
                        stats["ExcludedSeasonIncomplete"] += 1
                    elif bracket == "consolation":
                        stats["ExcludedConsolation"] += 1
                    else:
                        stats["ExcludedUnclassified"] += 1
                continue
            stats["CountedPlayoffs" if stage == "playoffs" else "CountedRegular"] += 1
            result = matchup["Result"]
            for own, other in ((participants[0], participants[1]), (participants[1], participants[0])):
                outcome = "tie" if result["Type"] == "tie" else ("win" if result["WinnerTeamID"] == own["TeamID"] else "loss")
                rows.append({
                    "TeamID": own["TeamID"],
                    "OpponentID": other["TeamID"],
                    "Game": model.game_record(season, int(week["Week"]), matchup["FantasyMatchupID"], stage, bracket, outcome,
                                              own["Points"], other["Points"]),
                })
    return rows, stats


def build_records(rows: list[dict[str, Any]], model: Any) -> list[dict[str, Any]]:
    """Per team, opponent and filter record (only pairs with at least one counted game); display order only, not a ranking."""
    grouped: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault((row["TeamID"], row["OpponentID"]), []).append(row["Game"])
    records: list[dict[str, Any]] = []
    for (team_id, opponent_id), games in grouped.items():
        ordered = sorted(games, key=lambda g: (int(g["Season"]), g["Week"]))
        for filter_name in model.FILTERS:
            selected = [g for g in ordered if model.in_filter(g["Stage"], filter_name)]
            if selected:
                records.append({"TeamID": team_id, "OpponentID": opponent_id, "Filter": filter_name, **model.summarize(selected)})
    order = {name: index for index, name in enumerate(model.FILTERS)}
    records.sort(key=lambda r: (r["TeamID"], order[r["Filter"]], -len(r["Games"]), r["OpponentID"]))
    return records


def resolve(repo_root: Path, league_id: str, at_utc: datetime) -> dict[str, Any]:
    """The league-rivalry document of one league over every manifest season; computed from the matchup context at ``at_utc``."""
    import league_standings_sources as sources

    manifest = sources.manifest(repo_root, league_id)
    metadata = load_league_metadata(league_id, data_meta_root(repo_root))
    validate_against_manifest(metadata, manifest)
    current = sources.current_season(manifest)
    seasons = sources.manifest_seasons(manifest)
    chosen = {season: model_for(metadata, season, MODEL_KIND) for season in seasons}
    if len(set(chosen.values())) != 1:
        raise RivalryError(f"rivalry-v1 aggregates all seasons with one model; the league chooses {sorted(set(chosen.values()))}")
    model = get_model(next(iter(chosen.values())), "rivalry")

    rows: list[dict[str, Any]] = []
    season_summaries: list[dict[str, Any]] = []
    for season in seasons:
        try:
            matchups = resolve_matchups(repo_root, league_id, season, at_utc)
        except MatchupContextError as exc:
            raise RivalryError(f"{league_id} season {season}: {exc}") from exc
        status_path = repo_root / DATA_SOURCE_ROOT / "leagues" / league_id / "seasons" / str(season) / "league.json"
        import json
        status = json.loads(status_path.read_text(encoding="utf-8")).get("Status")
        complete = season < current or status == "complete"
        season_rows, stats = season_games(matchups, model, complete)
        rows.extend(season_rows)
        season_summaries.append({"Season": str(season), "PlayoffsComplete": complete, **stats})
    return {
        "SchemaVersion": SCHEMA_VERSION,
        "Product": PRODUCT,
        "CanonicalLeagueID": league_id,
        "Models": {str(season): {"Rivalry": chosen[season]} for season in seasons},
        "Seasons": season_summaries,
        "Records": build_records(rows, model),
    }
