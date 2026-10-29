#!/usr/bin/env python3
"""Consumer rendering and shadow comparison of the league-standings product (ADR-072, Issue #987 step 3).

Renders the App delivery of the Shared Derived product ``league-standings`` in the exact shape of the
published ``public/data/Standings.json`` and of the placements that ``RequestLeague.ps1`` embeds in
``League.json`` (``Standings`` and ``Teams[].Placements``), and compares both with the files on disk. Until the
cutover (step 4) the PowerShell generators stay productive; this module only reads and writes nothing.

Rendering rules (identical to the current contract):
  * ``Standings.json`` is ``AllTime`` first, then every season newest first; the weekly movement fields
    (PreviousWeekPlace, PlaceDelta, WeeklyMovements) exist only on the rows of the current season.
  * Playoff rows carry ``OwnerAvatar`` as CDN URL (the product stores the provider avatar ID).
  * Placements: ``Current`` (League.Season), ``Previous`` (Season - 1) and ``AllTime`` per team with the
    Playoffs and Regular row without TeamID/Owner/TeamName and the team's awards.

Numbers are compared by value (a whole double and an integer are equal); every other type, key set and list
order must match.

Usage:
  league_standings_app_publish.py compare [--league nfl-reise] [--repo-root DIR]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from derived_data import build_league_standings  # noqa: E402
from league_metadata import data_meta_root, list_league_ids  # noqa: E402

AVATAR_URL = "https://sleepercdn.com/avatars/{}"
MOVEMENT_FIELDS = ("PreviousWeekPlace", "PlaceDelta", "WeeklyMovements")
IDENTITY_FIELDS = ("TeamID", "Owner", "TeamName")
EXIT_DIFFERENT = 3


def _regular_row(row: dict[str, Any], is_current: bool) -> dict[str, Any]:
    rendered = dict(row)
    if not is_current:
        for field in MOVEMENT_FIELDS:
            rendered.pop(field, None)
    return rendered


def _playoff_row(row: dict[str, Any]) -> dict[str, Any]:
    if "OwnerAvatarID" not in row:  # all-time rows carry no avatars
        return dict(row)
    rendered = {}
    for key, value in row.items():
        if key == "OwnerAvatarID":
            rendered["OwnerAvatar"] = AVATAR_URL.format(value) if value else None
        else:
            rendered[key] = value
    return rendered


def render_standings(documents: dict[int, dict[str, Any]], league_year: int) -> list[dict[str, Any]]:
    """Content of Standings.json: AllTime, then the seasons newest first."""
    if not documents:
        raise ValueError("No league-standings documents to render")
    seasons = []
    for season in sorted(documents, reverse=True):
        document = documents[season]
        seasons.append({
            "Season": str(season),
            "Playoffs": [_playoff_row(r) for r in document["Playoffs"]],
            "RegularSeason": [_regular_row(r, season == league_year) for r in document["RegularSeason"]],
            "Awards": list(document["Awards"]),
        })
    all_time = documents[max(documents)]["AllTime"]
    return [{
        "Season": "AllTime",
        "Playoffs": [_playoff_row(r) for r in all_time["Playoffs"]],
        "RegularSeason": [dict(r) for r in all_time["RegularSeason"]],
    }] + seasons


def render_placements(standings: list[dict[str, Any]], team_ids: list[int], league_year: int) -> dict[int, dict[str, dict[str, Any]]]:
    """Per team the Current, Previous and AllTime placements as RequestLeague.ps1 enriches them."""
    keys = {"AllTime": "AllTime", str(league_year): "Current", str(league_year - 1): "Previous"}
    placements: dict[int, dict[str, dict[str, Any]]] = {team_id: {} for team_id in team_ids}
    for season in standings:
        key = keys.get(season["Season"])
        if key is None:
            continue
        for team_id in team_ids:
            entry = placements[team_id].setdefault(key, {})
            playoff = next((r for r in season["Playoffs"] if r["TeamID"] == team_id), None)
            if playoff is not None:
                entry["Playoffs"] = {k: v for k, v in playoff.items() if k not in IDENTITY_FIELDS}
            regular = next((r for r in season["RegularSeason"] if r["TeamID"] == team_id), None)
            if regular is not None:
                entry["Regular"] = {k: v for k, v in regular.items() if k not in IDENTITY_FIELDS}
            entry["Awards"] = [{k: v for k, v in a.items() if k not in IDENTITY_FIELDS}
                               for a in season.get("Awards") or [] if a["TeamID"] == team_id]
    return placements


def difference(left: Any, right: Any, path: str = "$") -> list[str]:
    """Semantic comparison: dict key order is irrelevant; numbers compare by value; types, keys and list order must match."""
    left_number = isinstance(left, (int, float)) and not isinstance(left, bool)
    right_number = isinstance(right, (int, float)) and not isinstance(right, bool)
    if left_number and right_number:
        return [] if left == right else [f"{path}: {left!r} != {right!r}"]
    if type(left) is not type(right):
        return [f"{path}: type {type(left).__name__} != {type(right).__name__} ({left!r} vs {right!r})"]
    if isinstance(left, dict):
        found = [f"{path}.{key}: only in product" for key in sorted(left.keys() - right.keys())]
        found += [f"{path}.{key}: only in published file" for key in sorted(right.keys() - left.keys())]
        for key in sorted(left.keys() & right.keys()):
            found += difference(left[key], right[key], f"{path}.{key}")
        return found
    if isinstance(left, list):
        if len(left) != len(right):
            return [f"{path}: length {len(left)} != {len(right)}"]
        found = []
        for index, (a, b) in enumerate(zip(left, right)):
            found += difference(a, b, f"{path}[{index}]")
        return found
    return [] if left == right else [f"{path}: {left!r} != {right!r}"]


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def shadow_compare(repo_root: Path, league_id: str, documents: dict[int, dict[str, Any]] | None = None) -> dict[str, list[str]]:
    """Differences between the rendered product and the published App files; key = comparison, value = differences.

    ``Standings.json`` and the ``League.json`` Standings copy are compared as a whole; the team placements are
    compared per team with ``Awards`` separated into its own entry (see ``KNOWN_LEGACY_AWARDS_DEVIATION``).
    """
    documents = documents if documents is not None else build_league_standings(repo_root, league_id)
    data = repo_root / "public" / "data"
    league = _load(data / "League.json")
    league_year = int(league["Season"])
    rendered = render_standings(documents, league_year)
    results: dict[str, list[str]] = {}

    standings_path = data / "Standings.json"
    results["public/data/Standings.json"] = (
        difference(rendered, _load(standings_path)) if standings_path.is_file() else ["file missing on disk"])
    results["public/data/League.json#Standings"] = difference(rendered, league.get("Standings"))

    team_ids = [int(t["TeamID"]) for t in league["Teams"]]
    expected = render_placements(rendered, team_ids, league_year)
    placement_diffs: list[str] = []
    award_diffs: list[str] = []
    for team in league["Teams"]:
        team_id = int(team["TeamID"])
        published = team.get("Placements") or {}
        for key in sorted(set(expected[team_id]) | set(published)):
            mine, theirs = expected[team_id].get(key), published.get(key)
            if mine is None or theirs is None:
                placement_diffs.append(f"$.Teams[{team_id}].Placements.{key}: present on one side only")
                continue
            mine_awards, theirs_awards = mine.get("Awards"), theirs.get("Awards")
            placement_diffs += difference({k: v for k, v in mine.items() if k != "Awards"},
                                          {k: v for k, v in theirs.items() if k != "Awards"}, f"$.Teams[{team_id}].Placements.{key}")
            award_diffs += difference(mine_awards, theirs_awards, f"$.Teams[{team_id}].Placements.{key}.Awards")
    results["public/data/League.json#Teams.Placements"] = placement_diffs
    results[KNOWN_LEGACY_AWARDS_DEVIATION] = award_diffs
    return results


# RequestLeague.ps1 fills Placements.<key>.Awards from a hashtable keyed by the award's TeamID and looks it up with
# the team's TeamID; the published League.json holds an empty list for every team although the season awards exist
# (Issue #987 step 3 finding). The comparison reports this as its own entry instead of mixing it into the
# placement differences; the cutover decides whether the intended content is delivered.
KNOWN_LEGACY_AWARDS_DEVIATION = "public/data/League.json#Teams.Placements.Awards (known legacy deviation)"


def run_compare(args: argparse.Namespace) -> int:
    leagues = [args.league] if args.league else list_league_ids(data_meta_root(args.repo_root))
    exit_code = 0
    for league_id in leagues:
        results = shadow_compare(args.repo_root, league_id)
        print(f"League {league_id}")
        for name, diffs in results.items():
            known = name == KNOWN_LEGACY_AWARDS_DEVIATION
            print(f"  {name}: {'identical' if not diffs else str(len(diffs)) + ' difference(s)'}")
            for line in diffs[:20]:
                print(f"    {line}")
            if diffs and not known:
                exit_code = EXIT_DIFFERENT
    return exit_code


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    sub = parser.add_subparsers(dest="command", required=True)
    compare = sub.add_parser("compare", help="compare the rendered product with the published Standings.json and League.json")
    compare.add_argument("--league", help="CanonicalLeagueID (default: every league in data-meta)")
    compare.set_defaults(func=run_compare)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
