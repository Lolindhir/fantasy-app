#!/usr/bin/env python3
"""Consumer generator: renders public/data/InjuryImpact.json from the persisted team-injury-impact product (Issue #1584, CP5).

  data-derived/team-injury-impact/<CanonicalLeagueID>/<season>.json   Shared Derived product, input (materialized by
                                                                      tools/team_injury_impact_materialize.py)
  public/data/InjuryImpact.json                                        every league season of the manifest in one file (oldest first)

Usage:
  injury_impact_app_publish.py write [--league ID] [--fail-on-error]

Each season document is reduced to what the display needs (SchemaVersion 2): per week only the Impact per team with its two markers
(lower bound, unknown evidence), the season totals with their top players, the weeks without a verified projection and the model
provenance. Digests, per-week counts and the per-week injured lists stay in the product (chat analyses and Fantasy Management read it).
Additions are ``Teams`` (CanonicalLeagueRosterID -> TeamID, Owner, TeamName of that season, joined from the canonical league source)
and ``PlayerRefs`` (CanonicalPlayerID -> Name, Position, Picture of the top players, from the canonical NFL profiles) because the
product itself holds no display identity. The file is written only on a semantic difference and Timestamps.json[InjuryImpact] is stamped then. A season whose product is missing keeps out of the file with a
warning; the current season fails the run with --fail-on-error. Without --league more than one league fails closed (the App file carries
no league dimension).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from data_roots import DATA_SOURCE_ROOT, data_derived_dir  # noqa: E402
from historical_fantasy_scoring import read_json  # noqa: E402
from derived_data_lib.team_injury_impact import PRODUCT, TeamInjuryImpactError  # noqa: E402
from league_metadata import LeagueMetadataError, list_league_ids  # noqa: E402
from league_standings_sources import StandingsSourceError, current_season, load_season_inputs, manifest, manifest_seasons  # noqa: E402
from app_delivery import Writer, warn  # noqa: E402
from players_population import sized_headshot  # noqa: E402

EXPECTED_ERRORS = (TeamInjuryImpactError, StandingsSourceError, LeagueMetadataError)
SCHEMA_VERSION = 3
WEEK_TEAM_FIELDS = ("CanonicalLeagueRosterID", "Impact", "IsLowerBound", "HasUnknownEvidence")


def leagues(requested: str | None) -> list[str]:
    if requested:
        return [requested]
    ids = list_league_ids()
    if len(ids) != 1:
        raise TeamInjuryImpactError(f"the App InjuryImpact file carries no league dimension; expected exactly one league, found {ids}")
    return ids


def load_profiles(repo_root: Path) -> dict[str, dict[str, Any]]:
    document = read_json(repo_root / DATA_SOURCE_ROOT / "nfl/player-profiles/nflverse.json")
    if document.get("SourceDataset") != "nflverse.players" or not isinstance(document.get("Records"), list):
        raise TeamInjuryImpactError("unexpected canonical NFL player profiles layout")
    return {row["CanonicalPlayerID"]: row for row in document["Records"]}


def player_refs(document: dict[str, Any], profiles: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Display reference of every top player; unknown players keep null display values instead of being dropped."""
    refs: dict[str, dict[str, Any]] = {}
    for item in document["SeasonTotals"]:
        for player in item.get("TopPlayers", []):
            profile = profiles.get(player["CanonicalPlayerID"]) or {}
            headshot = profile.get("Headshot")
            refs[player["CanonicalPlayerID"]] = {
                "Name": profile.get("DisplayName") or None,
                "Position": profile.get("Position") or None,
                "Picture": sized_headshot(headshot) if headshot else None,
                "Team": profile.get("LatestTeam") or None,
            }
    return dict(sorted(refs.items()))


def costly_players(team: dict[str, Any]) -> int:
    """Injured players whose return would have gained points (the same selection the top-player list uses)."""
    return sum(1 for player in team.get("Injured", []) if (player.get("SingleReturnImpact") or 0) > 0)


def slim_season(document: dict[str, Any], teams: list[dict[str, Any]], profiles: dict[str, dict[str, Any]]) -> dict[str, Any]:
    weeks = [
        {"Week": week["Week"], "Teams": [{**{key: team[key] for key in WEEK_TEAM_FIELDS}, "CostlyPlayers": costly_players(team)} for team in week["Teams"]]}
        for week in document["Weeks"]
    ]
    per_roster: dict[str, list[int]] = {}
    for week in document["Weeks"]:
        for team in week["Teams"]:
            per_roster.setdefault(team["CanonicalLeagueRosterID"], []).append(costly_players(team))
    totals = [
        {**item, "CostlyPlayersPerWeek": round(sum(counts) / len(counts), 1) if (counts := per_roster.get(item["CanonicalLeagueRosterID"])) else None}
        for item in document["SeasonTotals"]
    ]
    return {
        "Season": document["Season"],
        "Models": document["Models"],
        "AsOf": document["AsOf"],
        "Teams": teams,
        "Weeks": weeks,
        "UnavailableWeeks": document["UnavailableWeeks"],
        "SeasonTotals": totals,
        "PlayerRefs": player_refs(document, profiles),
    }


def render(repo_root: Path, league_id: str) -> dict[str, Any]:
    out_root = data_derived_dir(repo_root)
    current = current_season(manifest(repo_root, league_id))
    seasons: list[dict[str, Any]] = []
    profiles = load_profiles(repo_root)
    for season in manifest_seasons(manifest(repo_root, league_id)):
        path = out_root / PRODUCT / league_id / f"{season}.json"
        if not path.is_file():
            if season == current:
                raise TeamInjuryImpactError(f"team-injury-impact product missing for {league_id} {season}; materialize it first")
            warn(f"InjuryImpact {season} not published", "team-injury-impact product missing; materialize it first")
            continue
        document = json.loads(path.read_text(encoding="utf-8"))
        identity = {t["CanonicalLeagueRosterID"]: t for t in load_season_inputs(repo_root, league_id, season, current).teams}
        teams = []
        for item in document["SeasonTotals"]:
            team = identity.get(item["CanonicalLeagueRosterID"])
            if team is None:
                raise TeamInjuryImpactError(f"{league_id}/{season}: roster {item['CanonicalLeagueRosterID']} is not a team of that season")
            teams.append({"CanonicalLeagueRosterID": item["CanonicalLeagueRosterID"], "TeamID": team["TeamID"], "Owner": team["Owner"], "TeamName": team["Team"]})
        seasons.append(slim_season(document, teams, profiles))
    return {"SchemaVersion": SCHEMA_VERSION, "Product": PRODUCT, "CanonicalLeagueID": league_id, "Seasons": seasons}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    sub = parser.add_subparsers(dest="command", required=True)
    write = sub.add_parser("write", help="render the App file from the persisted product (semantic no-op)")
    write.add_argument("--league", default=None)
    write.add_argument("--fail-on-error", action="store_true", help="exit 1 when the file cannot be rendered")
    return parser.parse_args(argv)


def run_write(args: argparse.Namespace) -> int:
    writer = Writer(args.repo_root, datetime.now(timezone.utc))
    try:
        for league_id in leagues(args.league):
            writer.put("InjuryImpact.json", render(args.repo_root, league_id), "InjuryImpact")
    except EXPECTED_ERRORS as error:
        warn("InjuryImpact not published", f"{type(error).__name__}: {error}")
        writer.finish()
        return 1 if args.fail_on_error else 0
    changed = writer.finish()
    print("\n".join(f"wrote {name}" for name in changed) if changed else "No changes - update skipped.")
    return 0


def main(argv: list[str] | None = None) -> int:
    return run_write(parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
