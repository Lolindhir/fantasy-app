#!/usr/bin/env python3
"""Canonical League ownership adapter for Fantasy Management shadow validation.

This module exposes only shared league basis facts that already belong to
`source-data/leagues/**`. It deliberately does not reproduce App/Fantasy
derived fields such as salary, standings, awards, draft-pick readmodels or team
windows.

The stable Fantasy Management TeamID remains application-owned. The bridge to
Canonical League data is explicit in owner-registry.json through
`canonical_league_member_id`; provider roster IDs are provenance only and are
never treated as the stable TeamID contract.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


class CanonicalOwnershipError(RuntimeError):
    """Raised when canonical ownership evidence is incomplete or ambiguous."""


def _read_json(path: Path) -> Any:
    if not path.is_file():
        raise CanonicalOwnershipError(f"Required file is missing: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CanonicalOwnershipError(f"Could not read valid JSON from {path}: {exc}") from exc


def _require_object(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CanonicalOwnershipError(f"{context} must be an object.")
    return value


def _require_list(value: Any, context: str) -> list[Any]:
    if not isinstance(value, list):
        raise CanonicalOwnershipError(f"{context} must be an array.")
    return value


def _unique_provider_value(
    mappings: Any,
    *,
    provider: str,
    field: str,
    context: str,
) -> str:
    rows = _require_list(mappings, f"{context}.ProviderMappings")
    matches = [
        row
        for row in rows
        if isinstance(row, dict)
        and row.get("Provider") == provider
        and row.get(field) not in (None, "")
    ]
    if len(matches) != 1:
        raise CanonicalOwnershipError(
            f"{context} must contain exactly one {provider} mapping with {field}; "
            f"found {len(matches)}."
        )
    return str(matches[0][field])


def _provider_player_ids(entries: Any, context: str) -> list[str]:
    rows = _require_list(entries, context)
    result: list[str] = []
    seen: set[str] = set()
    for index, row in enumerate(rows):
        item = _require_object(row, f"{context}[{index}]")
        player_id = _unique_provider_value(
            item.get("ProviderMappings"),
            provider="Sleeper",
            field="ProviderPlayerID",
            context=f"{context}[{index}]",
        )
        if player_id in seen:
            raise CanonicalOwnershipError(
                f"{context} contains duplicate Sleeper player ID {player_id}."
            )
        seen.add(player_id)
        result.append(player_id)
    return result


def resolve_current_canonical_season(
    repo_root: Path,
    *,
    canonical_league_id: str,
) -> int:
    """Resolve the active season only from the Canonical League manifest."""

    root = repo_root.resolve()
    manifest_path = root / "source-data" / "leagues" / canonical_league_id / "manifest.json"
    manifest = _require_object(_read_json(manifest_path), "manifest.json")

    if manifest.get("CanonicalLeagueID") != canonical_league_id:
        raise CanonicalOwnershipError(
            "Canonical league manifest identity mismatch: "
            f"expected {canonical_league_id!r}, found {manifest.get('CanonicalLeagueID')!r}."
        )

    current_season_id = manifest.get("CurrentCanonicalLeagueSeasonID")
    if not isinstance(current_season_id, str) or not current_season_id:
        raise CanonicalOwnershipError(
            "manifest.json has no CurrentCanonicalLeagueSeasonID."
        )

    seasons = _require_list(manifest.get("Seasons"), "manifest.json.Seasons")
    matches = [
        row
        for row in seasons
        if isinstance(row, dict)
        and row.get("CanonicalLeagueSeasonID") == current_season_id
    ]
    if len(matches) != 1:
        raise CanonicalOwnershipError(
            "CurrentCanonicalLeagueSeasonID must resolve to exactly one manifest season; "
            f"found {len(matches)} matches for {current_season_id!r}."
        )

    try:
        season = int(matches[0]["Season"])
    except (KeyError, TypeError, ValueError) as exc:
        raise CanonicalOwnershipError(
            f"Manifest season {current_season_id!r} has no valid Season."
        ) from exc

    if season <= 0:
        raise CanonicalOwnershipError(
            f"Manifest season {current_season_id!r} has invalid Season {season}."
        )
    return season


def build_canonical_ownership_snapshot(
    repo_root: Path,
    *,
    canonical_league_id: str,
    season: int,
    owner_registry_path: Path | None = None,
) -> dict[str, Any]:
    """Build the FM ownership basis from canonical League source data.

    The returned team records intentionally preserve the current Sleeper player
    ID surface because Players.json still uses Sleeper player_id as its public ID
    contract. Canonical player identity remains available in source-data and can
    be migrated independently under the player-contract guardrails.
    """

    root = repo_root.resolve()
    registry_path = owner_registry_path or (
        root / "fantasy-management/league-context/owner-registry.json"
    )
    registry = _require_object(_read_json(registry_path), "owner-registry.json")

    configured_league_id = registry.get("canonical_league_id")
    if configured_league_id != canonical_league_id:
        raise CanonicalOwnershipError(
            "owner-registry.json canonical_league_id mismatch: "
            f"expected {canonical_league_id!r}, found {configured_league_id!r}."
        )

    season_root = (
        root
        / "source-data"
        / "leagues"
        / canonical_league_id
        / "seasons"
        / str(season)
    )
    league = _require_object(_read_json(season_root / "league.json"), "league.json")
    members = _require_list(_read_json(season_root / "members.json"), "members.json")
    rosters = _require_list(_read_json(season_root / "rosters.json"), "rosters.json")

    if league.get("CanonicalLeagueID") != canonical_league_id:
        raise CanonicalOwnershipError(
            "Canonical league source identity mismatch in league.json."
        )
    if int(league.get("Season", -1)) != int(season):
        raise CanonicalOwnershipError(
            f"Canonical league season mismatch: expected {season}, "
            f"found {league.get('Season')!r}."
        )

    member_by_id: dict[str, dict[str, Any]] = {}
    for index, raw_member in enumerate(members):
        member = _require_object(raw_member, f"members.json[{index}]")
        member_id = member.get("CanonicalLeagueMemberID")
        if not isinstance(member_id, str) or not member_id:
            raise CanonicalOwnershipError(
                f"members.json[{index}] has no CanonicalLeagueMemberID."
            )
        if member_id in member_by_id:
            raise CanonicalOwnershipError(
                f"Duplicate CanonicalLeagueMemberID {member_id} in members.json."
            )
        member_by_id[member_id] = member

    roster_by_member_id: dict[str, dict[str, Any]] = {}
    for index, raw_roster in enumerate(rosters):
        roster = _require_object(raw_roster, f"rosters.json[{index}]")
        member_id = roster.get("CanonicalLeagueMemberID")
        if not isinstance(member_id, str) or not member_id:
            raise CanonicalOwnershipError(
                f"rosters.json[{index}] has no CanonicalLeagueMemberID."
            )
        if member_id in roster_by_member_id:
            raise CanonicalOwnershipError(
                f"Multiple canonical rosters resolve to member {member_id}."
            )
        roster_by_member_id[member_id] = roster

    owners = _require_list(registry.get("owners"), "owner-registry.json.owners")
    seen_team_ids: set[int] = set()
    seen_member_ids: set[str] = set()
    globally_owned_players: dict[str, int] = {}
    teams: list[dict[str, Any]] = []

    for index, raw_owner in enumerate(owners):
        owner = _require_object(raw_owner, f"owner-registry.json.owners[{index}]")
        try:
            team_id = int(owner["team_id"])
        except (KeyError, TypeError, ValueError) as exc:
            raise CanonicalOwnershipError(
                f"owner-registry.json.owners[{index}] has invalid team_id."
            ) from exc

        member_id = owner.get("canonical_league_member_id")
        if not isinstance(member_id, str) or not member_id:
            raise CanonicalOwnershipError(
                f"TeamID {team_id} has no canonical_league_member_id bridge."
            )
        if team_id in seen_team_ids:
            raise CanonicalOwnershipError(f"Duplicate TeamID {team_id} in owner registry.")
        if member_id in seen_member_ids:
            raise CanonicalOwnershipError(
                f"CanonicalLeagueMemberID {member_id} is assigned to multiple TeamIDs."
            )
        seen_team_ids.add(team_id)
        seen_member_ids.add(member_id)

        member = member_by_id.get(member_id)
        roster = roster_by_member_id.get(member_id)
        if member is None:
            raise CanonicalOwnershipError(
                f"TeamID {team_id} maps to missing canonical member {member_id}."
            )
        if roster is None:
            raise CanonicalOwnershipError(
                f"TeamID {team_id} maps to member {member_id} without a canonical roster."
            )

        provider_owner_id = _unique_provider_value(
            member.get("ProviderMappings"),
            provider="Sleeper",
            field="ProviderUserID",
            context=f"member {member_id}",
        )
        roster_owner_id = str(roster.get("ProviderOwnerUserID") or "")
        if roster_owner_id != provider_owner_id:
            raise CanonicalOwnershipError(
                f"Canonical roster/member owner mismatch for TeamID {team_id}: "
                f"member={provider_owner_id!r}, roster={roster_owner_id!r}."
            )

        roster_ids = _provider_player_ids(roster.get("Players"), f"TeamID {team_id}.Players")
        reserve_ids = _provider_player_ids(roster.get("Reserve"), f"TeamID {team_id}.Reserve")
        taxi_ids = _provider_player_ids(roster.get("Taxi"), f"TeamID {team_id}.Taxi")
        starter_ids = _provider_player_ids(roster.get("Starters"), f"TeamID {team_id}.Starters")

        roster_set = set(roster_ids)
        for bucket_name, bucket_ids in (
            ("Reserve", reserve_ids),
            ("Taxi", taxi_ids),
            ("Starter", starter_ids),
        ):
            missing = sorted(set(bucket_ids) - roster_set)
            if missing:
                raise CanonicalOwnershipError(
                    f"TeamID {team_id} {bucket_name} contains players absent from Roster: "
                    + ", ".join(missing)
                )

        for player_id in roster_ids:
            prior_team_id = globally_owned_players.get(player_id)
            if prior_team_id is not None:
                raise CanonicalOwnershipError(
                    f"Sleeper player ID {player_id} appears on multiple canonical rosters: "
                    f"TeamID {prior_team_id} and TeamID {team_id}."
                )
            globally_owned_players[player_id] = team_id

        canonical_roster_id = roster.get("CanonicalLeagueRosterID")
        if not isinstance(canonical_roster_id, str) or not canonical_roster_id:
            raise CanonicalOwnershipError(
                f"TeamID {team_id} canonical roster has no CanonicalLeagueRosterID."
            )

        teams.append(
            {
                "TeamID": team_id,
                "CanonicalLeagueMemberID": member_id,
                "CanonicalLeagueRosterID": canonical_roster_id,
                "OwnerDisplayName": member.get("DisplayName"),
                "ProviderOwnerUserID": provider_owner_id,
                "ProviderRosterID": _unique_provider_value(
                    roster.get("ProviderMappings"),
                    provider="Sleeper",
                    field="ProviderRosterID",
                    context=f"roster {canonical_roster_id}",
                ),
                "Roster": roster_ids,
                "Reserve": reserve_ids,
                "Taxi": taxi_ids,
                "Starter": starter_ids,
            }
        )

    expected_team_count = league.get("Settings", {}).get("num_teams")
    if expected_team_count is not None and int(expected_team_count) != len(teams):
        raise CanonicalOwnershipError(
            f"Canonical team count mismatch: league expects {expected_team_count}, "
            f"owner registry resolves {len(teams)}."
        )
    if len(rosters) != len(teams):
        raise CanonicalOwnershipError(
            f"Canonical roster coverage mismatch: {len(rosters)} rosters exist but "
            f"{len(teams)} stable TeamIDs are mapped."
        )

    teams.sort(key=lambda item: item["TeamID"])
    return {
        "CanonicalLeagueID": canonical_league_id,
        "Season": int(season),
        "Teams": teams,
    }


def enrich_canonical_ownership_with_display(
    snapshot: dict[str, Any],
    app_league: dict[str, Any],
) -> list[dict[str, Any]]:
    """Attach app-owned Team/TeamAbbr display metadata by stable TeamID only.

    Legacy League.json roster membership is intentionally ignored. This helper is
    suitable for consumers that have already cut their ownership basis to the
    canonical League source but still preserve the existing display contract.
    """

    canonical_teams = _require_list(snapshot.get("Teams"), "snapshot.Teams")
    app_teams = _require_list(app_league.get("Teams"), "public/data/League.json.Teams")

    display_by_team_id: dict[int, dict[str, Any]] = {}
    for index, raw_team in enumerate(app_teams):
        team = _require_object(raw_team, f"League.json.Teams[{index}]")
        try:
            team_id = int(team["TeamID"])
        except (KeyError, TypeError, ValueError) as exc:
            raise CanonicalOwnershipError(
                f"League.json.Teams[{index}] has invalid TeamID."
            ) from exc
        if team_id in display_by_team_id:
            raise CanonicalOwnershipError(
                f"League.json has duplicate TeamID {team_id}."
            )
        display_by_team_id[team_id] = team

    canonical_ids: set[int] = set()
    enriched: list[dict[str, Any]] = []
    for index, raw_team in enumerate(canonical_teams):
        team = _require_object(raw_team, f"snapshot.Teams[{index}]")
        try:
            team_id = int(team["TeamID"])
        except (KeyError, TypeError, ValueError) as exc:
            raise CanonicalOwnershipError(
                f"snapshot.Teams[{index}] has invalid TeamID."
            ) from exc
        if team_id in canonical_ids:
            raise CanonicalOwnershipError(
                f"Canonical ownership snapshot has duplicate TeamID {team_id}."
            )
        canonical_ids.add(team_id)

        display = display_by_team_id.get(team_id)
        if display is None:
            raise CanonicalOwnershipError(
                f"League.json display enrichment is missing TeamID {team_id}."
            )

        enriched.append(
            {
                **team,
                "Team": display.get("Team"),
                "TeamAbbr": display.get("TeamAbbr"),
            }
        )

    extra_display_ids = sorted(set(display_by_team_id) - canonical_ids)
    if extra_display_ids:
        raise CanonicalOwnershipError(
            "League.json display enrichment contains TeamIDs absent from canonical "
            "ownership: " + ", ".join(str(team_id) for team_id in extra_display_ids)
        )

    enriched.sort(key=lambda item: int(item["TeamID"]))
    return enriched


def compare_to_app_league(
    snapshot: dict[str, Any],
    app_league: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return exact shadow differences for the ownership/member basis facts."""

    app_teams = _require_list(app_league.get("Teams"), "public/data/League.json.Teams")
    by_team_id: dict[int, dict[str, Any]] = {}
    for index, raw_team in enumerate(app_teams):
        team = _require_object(raw_team, f"League.json.Teams[{index}]")
        try:
            team_id = int(team["TeamID"])
        except (KeyError, TypeError, ValueError) as exc:
            raise CanonicalOwnershipError(
                f"League.json.Teams[{index}] has invalid TeamID."
            ) from exc
        if team_id in by_team_id:
            raise CanonicalOwnershipError(f"League.json has duplicate TeamID {team_id}.")
        by_team_id[team_id] = team

    differences: list[dict[str, Any]] = []
    snapshot_teams = _require_list(snapshot.get("Teams"), "snapshot.Teams")
    snapshot_ids = {int(team["TeamID"]) for team in snapshot_teams}
    app_ids = set(by_team_id)
    for team_id in sorted(snapshot_ids - app_ids):
        differences.append({"TeamID": team_id, "Field": "Team", "Canonical": "present", "App": "missing"})
    for team_id in sorted(app_ids - snapshot_ids):
        differences.append({"TeamID": team_id, "Field": "Team", "Canonical": "missing", "App": "present"})

    field_map = {
        "OwnerDisplayName": "Owner",
        "ProviderOwnerUserID": "OwnerID",
        "Roster": "Roster",
        "Reserve": "Reserve",
        "Taxi": "Taxi",
        "Starter": "Starter",
    }
    for canonical_team in snapshot_teams:
        team_id = int(canonical_team["TeamID"])
        app_team = by_team_id.get(team_id)
        if app_team is None:
            continue
        for canonical_field, app_field in field_map.items():
            canonical_value = canonical_team.get(canonical_field)
            app_value = app_team.get(app_field)
            if canonical_value != app_value:
                differences.append(
                    {
                        "TeamID": team_id,
                        "Field": app_field,
                        "Canonical": canonical_value,
                        "App": app_value,
                    }
                )
    return differences


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build and optionally compare the Canonical FM ownership shadow."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[3],
    )
    parser.add_argument("--canonical-league-id", default="nfl-reise")
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument(
        "--compare-league",
        type=Path,
        help="Repository-relative or absolute public/data/League.json path.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    root = args.repo_root.resolve()
    snapshot = build_canonical_ownership_snapshot(
        root,
        canonical_league_id=args.canonical_league_id,
        season=args.season,
    )
    result: dict[str, Any] = {
        "canonical_league_id": snapshot["CanonicalLeagueID"],
        "season": snapshot["Season"],
        "team_count": len(snapshot["Teams"]),
        "teams": [
            {
                "team_id": team["TeamID"],
                "roster": len(team["Roster"]),
                "reserve": len(team["Reserve"]),
                "taxi": len(team["Taxi"]),
                "starter": len(team["Starter"]),
            }
            for team in snapshot["Teams"]
        ],
    }

    exit_code = 0
    if args.compare_league:
        league_path = args.compare_league
        if not league_path.is_absolute():
            league_path = root / league_path
        app_league = _require_object(_read_json(league_path), "public/data/League.json")
        differences = compare_to_app_league(snapshot, app_league)
        result["parity"] = {
            "strict": len(differences) == 0,
            "difference_count": len(differences),
            "differences": differences,
        }
        if differences:
            exit_code = 1

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
