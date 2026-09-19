from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIRECTORY = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIRECTORY))

from canonical_league_ownership import (  # noqa: E402
    CanonicalOwnershipError,
    build_canonical_ownership_snapshot,
    compare_to_app_league,
    resolve_current_canonical_season,
)


class CanonicalLeagueOwnershipTests(unittest.TestCase):
    def test_current_season_resolves_only_from_canonical_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_fixture(root)

            self.assertEqual(
                2026,
                resolve_current_canonical_season(
                    root,
                    canonical_league_id="test-league",
                ),
            )

            manifest_path = root / "source-data/leagues/test-league/manifest.json"
            manifest = self._read_json(manifest_path)
            manifest["CurrentCanonicalLeagueSeasonID"] = "missing-season"
            self._write_json(manifest_path, manifest)

            with self.assertRaisesRegex(
                CanonicalOwnershipError,
                "must resolve to exactly one manifest season",
            ):
                resolve_current_canonical_season(
                    root,
                    canonical_league_id="test-league",
                )

    def test_team_id_is_bridged_by_canonical_member_not_provider_roster_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_fixture(root, provider_roster_id="99")

            snapshot = build_canonical_ownership_snapshot(
                root,
                canonical_league_id="test-league",
                season=2026,
            )

            self.assertEqual(1, snapshot["Teams"][0]["TeamID"])
            self.assertEqual("member-1", snapshot["Teams"][0]["CanonicalLeagueMemberID"])
            self.assertEqual("99", snapshot["Teams"][0]["ProviderRosterID"])

    def test_shadow_parity_matches_member_and_roster_basis_facts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_fixture(root)
            snapshot = build_canonical_ownership_snapshot(
                root,
                canonical_league_id="test-league",
                season=2026,
            )
            app_league = self._read_json(root / "public/data/League.json")

            self.assertEqual([], compare_to_app_league(snapshot, app_league))

    def test_missing_explicit_team_bridge_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_fixture(root)
            registry_path = root / "fantasy-management/league-context/owner-registry.json"
            registry = self._read_json(registry_path)
            del registry["owners"][0]["canonical_league_member_id"]
            self._write_json(registry_path, registry)

            with self.assertRaisesRegex(
                CanonicalOwnershipError,
                "has no canonical_league_member_id bridge",
            ):
                build_canonical_ownership_snapshot(
                    root,
                    canonical_league_id="test-league",
                    season=2026,
                )

    def test_cross_team_duplicate_player_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_fixture(root, include_second_team=True)
            rosters_path = (
                root
                / "source-data/leagues/test-league/seasons/2026/rosters.json"
            )
            rosters = self._read_json(rosters_path)
            rosters[1]["Players"] = list(rosters[0]["Players"])
            rosters[1]["Starters"] = list(rosters[0]["Starters"])
            self._write_json(rosters_path, rosters)

            with self.assertRaisesRegex(
                CanonicalOwnershipError,
                "appears on multiple canonical rosters",
            ):
                build_canonical_ownership_snapshot(
                    root,
                    canonical_league_id="test-league",
                    season=2026,
                )

    def test_member_and_roster_owner_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_fixture(root)
            rosters_path = (
                root
                / "source-data/leagues/test-league/seasons/2026/rosters.json"
            )
            rosters = self._read_json(rosters_path)
            rosters[0]["ProviderOwnerUserID"] = "wrong-owner"
            self._write_json(rosters_path, rosters)

            with self.assertRaisesRegex(
                CanonicalOwnershipError,
                "roster/member owner mismatch",
            ):
                build_canonical_ownership_snapshot(
                    root,
                    canonical_league_id="test-league",
                    season=2026,
                )

    def test_repository_managed_roster_signals_match_canonical_membership(self) -> None:
        root = Path(__file__).resolve().parents[4]
        snapshot = build_canonical_ownership_snapshot(
            root,
            canonical_league_id="nfl-reise",
            season=resolve_current_canonical_season(
                root,
                canonical_league_id="nfl-reise",
            ),
        )
        managed = next(team for team in snapshot["Teams"] if team["TeamID"] == 1)
        signals = self._read_json(
            root / "fantasy-management/generated/operations/managed-roster-signals.json"
        )
        players = {
            str(player["player_id"]): player
            for player in signals["players"]
        }

        expected_ids = set(managed["Roster"]) | set(managed["Reserve"]) | set(managed["Taxi"])
        self.assertEqual(expected_ids, set(players))
        starters = set(managed["Starter"])
        reserve = set(managed["Reserve"])
        taxi = set(managed["Taxi"])
        roster = set(managed["Roster"])
        for player_id, player in players.items():
            expected_sections = sorted(
                section
                for section, bucket in (
                    ("roster", roster),
                    ("reserve", reserve),
                    ("taxi", taxi),
                )
                if player_id in bucket
            )
            self.assertEqual(expected_sections, player["roster_sections"])
            self.assertEqual(player_id in starters, player["is_starter"])

    def test_repository_current_ownership_is_strictly_equal(self) -> None:
        root = Path(__file__).resolve().parents[4]
        metadata = self._read_json(root / "public/data/Metadata.json")
        snapshot = build_canonical_ownership_snapshot(
            root,
            canonical_league_id="nfl-reise",
            season=int(metadata["LeagueYear"]),
        )
        app_league = self._read_json(root / "public/data/League.json")

        differences = compare_to_app_league(snapshot, app_league)
        self.assertEqual([], differences)
        self.assertEqual(6, len(snapshot["Teams"]))

    def _write_fixture(
        self,
        root: Path,
        *,
        provider_roster_id: str = "7",
        include_second_team: bool = False,
    ) -> None:
        for path in (
            "fantasy-management/league-context",
            "source-data/leagues/test-league/seasons/2026",
            "public/data",
        ):
            (root / path).mkdir(parents=True, exist_ok=True)

        owners = [
            {
                "name": "Owner One",
                "team_id": 1,
                "canonical_league_member_id": "member-1",
            }
        ]
        members = [
            {
                "CanonicalLeagueMemberID": "member-1",
                "DisplayName": "owner-one",
                "ProviderMappings": [
                    {"Provider": "Sleeper", "ProviderUserID": "user-1"}
                ],
            }
        ]
        rosters = [
            self._roster(
                member_id="member-1",
                canonical_roster_id="roster-1",
                provider_owner_id="user-1",
                provider_roster_id=provider_roster_id,
                player_id="player-1",
            )
        ]
        app_teams = [
            {
                "TeamID": 1,
                "Owner": "owner-one",
                "OwnerID": "user-1",
                "Roster": ["player-1"],
                "Reserve": [],
                "Taxi": [],
                "Starter": ["player-1"],
            }
        ]

        if include_second_team:
            owners.append(
                {
                    "name": "Owner Two",
                    "team_id": 2,
                    "canonical_league_member_id": "member-2",
                }
            )
            members.append(
                {
                    "CanonicalLeagueMemberID": "member-2",
                    "DisplayName": "owner-two",
                    "ProviderMappings": [
                        {"Provider": "Sleeper", "ProviderUserID": "user-2"}
                    ],
                }
            )
            rosters.append(
                self._roster(
                    member_id="member-2",
                    canonical_roster_id="roster-2",
                    provider_owner_id="user-2",
                    provider_roster_id="8",
                    player_id="player-2",
                )
            )
            app_teams.append(
                {
                    "TeamID": 2,
                    "Owner": "owner-two",
                    "OwnerID": "user-2",
                    "Roster": ["player-2"],
                    "Reserve": [],
                    "Taxi": [],
                    "Starter": ["player-2"],
                }
            )

        self._write_json(
            root / "fantasy-management/league-context/owner-registry.json",
            {
                "version": 3,
                "canonical_league_id": "test-league",
                "owners": owners,
            },
        )
        self._write_json(
            root / "source-data/leagues/test-league/manifest.json",
            {
                "CanonicalLeagueID": "test-league",
                "CurrentCanonicalLeagueSeasonID": "test-league-2026",
                "Seasons": [
                    {
                        "CanonicalLeagueSeasonID": "test-league-2026",
                        "Season": 2026,
                    }
                ],
            },
        )
        self._write_json(
            root / "source-data/leagues/test-league/seasons/2026/league.json",
            {
                "CanonicalLeagueID": "test-league",
                "Season": 2026,
                "Settings": {"num_teams": len(owners)},
            },
        )
        self._write_json(
            root / "source-data/leagues/test-league/seasons/2026/members.json",
            members,
        )
        self._write_json(
            root / "source-data/leagues/test-league/seasons/2026/rosters.json",
            rosters,
        )
        self._write_json(root / "public/data/League.json", {"Teams": app_teams})

    @staticmethod
    def _roster(
        *,
        member_id: str,
        canonical_roster_id: str,
        provider_owner_id: str,
        provider_roster_id: str,
        player_id: str,
    ) -> dict[str, object]:
        player = {
            "CanonicalPlayerID": f"canonical-{player_id}",
            "ProviderMappings": [
                {"Provider": "Sleeper", "ProviderPlayerID": player_id}
            ],
        }
        return {
            "CanonicalLeagueMemberID": member_id,
            "CanonicalLeagueRosterID": canonical_roster_id,
            "ProviderOwnerUserID": provider_owner_id,
            "ProviderMappings": [
                {"Provider": "Sleeper", "ProviderRosterID": provider_roster_id}
            ],
            "Players": [player],
            "Reserve": [],
            "Taxi": [],
            "Starters": [player],
        }

    @staticmethod
    def _write_json(path: Path, value: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    @staticmethod
    def _read_json(path: Path) -> object:
        return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
