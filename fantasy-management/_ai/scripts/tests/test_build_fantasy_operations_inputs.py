from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIRECTORY = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIRECTORY))

from build_fantasy_operations_inputs import (  # noqa: E402
    MaterializationError,
    build,
    canonical_json,
    derive_injury_signal,
    evaluate_catalog_source_observation,
    normalize_name,
)


class FantasyOperationsInputsTests(unittest.TestCase):
    def test_current_source_observation_excludes_insufficient_dataset(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            observation_path = root / "sources/ffc/observation.json"
            observation_path.parent.mkdir(parents=True, exist_ok=True)
            observation_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "source_id": "fantasy-football-calculator",
                        "technical_status": "success",
                        "checked_at": "2026-09-21T04:14:44Z",
                        "datasets": {
                            "redraft-ppr-8-team": {
                                "coverage_status": "insufficient_coverage",
                                "observed_rows": 43,
                                "minimum_usable_rows": 50,
                                "expected_minimum_rows": 50,
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            definition = {
                "source_id": "ffc-redraft-ppr-8-team",
                "access": {
                    "observation": {
                        "path": "sources/ffc/observation.json",
                        "dataset_id": "redraft-ppr-8-team",
                        "usable_statuses": ["usable", "reduced_coverage"],
                    }
                },
            }
            usable, source, issue = evaluate_catalog_source_observation(root, definition)
            self.assertFalse(usable)
            self.assertIsNotNone(source)
            self.assertEqual("current_source_observation_unusable", issue["kind"])
            self.assertEqual(43, issue["details"]["observed_rows"])

    def test_missing_observation_uses_transitional_legacy_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            definition = {
                "source_id": "ffc-redraft-ppr-8-team",
                "access": {
                    "observation": {
                        "path": "sources/ffc/observation.json",
                        "dataset_id": "redraft-ppr-8-team",
                        "usable_statuses": ["usable", "reduced_coverage"],
                    }
                },
            }
            usable, source, issue = evaluate_catalog_source_observation(
                Path(directory),
                definition,
            )
            self.assertTrue(usable)
            self.assertIsNone(source)
            self.assertIsNone(issue)

    def test_name_normalization_removes_suffix_and_punctuation(self) -> None:
        self.assertEqual("marvinharrison", normalize_name("Marvin Harrison Jr."))
        self.assertEqual("jamarrchase", normalize_name("Ja'Marr Chase"))

    def test_injury_signal_requires_external_verification(self) -> None:
        player = {
            "Injured": True,
            "InjuryDetails": {
                "Description": "Aug 5: limited with a hamstring issue.",
                "Designation": "Questionable",
                "ReturnDate": "20260812",
                "Date": "",
            },
        }
        signal = derive_injury_signal(player)
        self.assertEqual("current_injury_signal", signal["coverage_status"])
        self.assertEqual("high", signal["external_verification_priority"])

    def test_build_is_catalog_driven_and_treats_kicker_as_not_applicable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_fixture(root)
            config_path = root / "fantasy-management/automation/input-materialization.json"
            data, quality = build(root, config_path)

            self.assertEqual(3, data["managed_team"]["player_count"])
            quarterback = next(player for player in data["players"] if player["player_id"] == "1")
            receiver = next(player for player in data["players"] if player["player_id"] == "2")
            kicker = next(player for player in data["players"] if player["player_id"] == "3")

            self.assertEqual(["reserve", "roster"], quarterback["roster_sections"])
            self.assertEqual("sleeper_id", quarterback["market"]["fantasycalc"]["join_method"])
            self.assertEqual("two_qb_10_team", quarterback["redraft_adp"]["primary_format"])
            self.assertEqual("ppr_8_team", receiver["redraft_adp"]["primary_format"])

            # This source exists only in the fixture catalog. The materializer code
            # does not know its ID, provider or output key.
            self.assertIn("secondary_expert", receiver["market"])
            self.assertEqual(25, receiver["market"]["secondary_expert"]["overall_rank"])

            self.assertIsNone(kicker["redraft_adp"]["primary_format"])
            self.assertEqual(
                "not_applicable",
                kicker["source_signals"]["fantasypros-dynasty"]["coverage_status"],
            )
            self.assertEqual(
                "not_applicable",
                kicker["source_signals"]["ffc-ppr"]["coverage_status"],
            )
            self.assertFalse(any(issue.get("player_id") == "3" for issue in quality["issues"]))
            self.assertEqual("ok", quality["status"])
            self.assertEqual(
                1,
                quality["coverage"]["sources"]["fantasypros-dynasty"]["not_applicable_players"],
            )
            self.assertEqual(2, quality["coverage"]["primary_adp_applicable"])
            self.assertEqual(2, quality["coverage"]["primary_adp_listed"])

            data_again, quality_again = build(root, config_path)
            self.assertEqual(canonical_json(data), canonical_json(data_again))
            self.assertEqual(canonical_json(quality), canonical_json(quality_again))

    def test_managed_roster_membership_comes_from_canonical_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_fixture(root)

            league_path = root / "public/data/League.json"
            league = json.loads(league_path.read_text(encoding="utf-8"))
            league["Teams"][0]["Roster"] = ["3"]
            league["Teams"][0]["Reserve"] = []
            league["Teams"][0]["Taxi"] = []
            league["Teams"][0]["Starter"] = ["3"]
            league_path.write_text(json.dumps(league), encoding="utf-8")

            config_path = root / "fantasy-management/automation/input-materialization.json"
            data, _ = build(root, config_path)

            self.assertEqual(3, data["managed_team"]["player_count"])
            self.assertEqual("Test Team", data["managed_team"]["name"])
            self.assertEqual("TST", data["managed_team"]["abbreviation"])
            quarterback = next(player for player in data["players"] if player["player_id"] == "1")
            receiver = next(player for player in data["players"] if player["player_id"] == "2")
            self.assertEqual(["reserve", "roster"], quarterback["roster_sections"])
            self.assertTrue(quarterback["is_starter"])
            self.assertEqual(["roster"], receiver["roster_sections"])
            self.assertTrue(receiver["is_starter"])
            source_ids = {source["id"] for source in data["sources"]}
            self.assertIn("league_display", source_ids)
            self.assertIn("canonical_league_manifest", source_ids)
            self.assertIn("canonical_league_rosters", source_ids)
            self.assertIn("canonical_player_identities", source_ids)
            self.assertIn("canonical_sleeper_players", source_ids)

    def test_managed_roster_identity_and_ranking_joins_use_canonical_nfl_sources(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_fixture(root)

            players_path = root / "public/data/Players.json"
            players = json.loads(players_path.read_text(encoding="utf-8"))
            players[0].update(
                {
                    "Name": "Wrong Legacy Name",
                    "Position": "TE",
                    "TeamAbbr": "ZZZ",
                    "Salary": 123,
                    "SalaryProjected": 456,
                    "Status": "Legacy Active",
                    "Age": 27,
                    "Year": 5,
                    "IsFreeAgent": False,
                }
            )
            players_path.write_text(json.dumps(players), encoding="utf-8")

            sleeper_path = root / "source-data/nfl/platform/sleeper/players.json"
            sleeper = json.loads(sleeper_path.read_text(encoding="utf-8"))
            receiver = next(
                row for row in sleeper["Records"] if row["SleeperPlayerID"] == "2"
            )
            receiver["Position"] = "DB"
            receiver["FantasyPositions"] = ["DB", "WR"]
            sleeper_path.write_text(json.dumps(sleeper), encoding="utf-8")

            config_path = root / "fantasy-management/automation/input-materialization.json"
            data, _ = build(root, config_path)

            quarterback = next(
                player for player in data["players"] if player["player_id"] == "1"
            )
            receiver_output = next(
                player for player in data["players"] if player["player_id"] == "2"
            )

            self.assertEqual("Quarter Back", quarterback["name"])
            self.assertEqual("QB", quarterback["position"])
            self.assertEqual("AAA", quarterback["nfl_team"])
            self.assertEqual(123, quarterback["app_data"]["salary"])
            self.assertEqual(456, quarterback["app_data"]["salary_projected"])
            self.assertEqual("Legacy Active", quarterback["app_data"]["status"])
            self.assertEqual(27, quarterback["app_data"]["age"])
            self.assertEqual(5, quarterback["app_data"]["years_experience"])
            self.assertFalse(quarterback["app_data"]["is_free_agent"])
            self.assertEqual(
                "current_injury_signal",
                quarterback["injury"]["coverage_status"],
            )
            self.assertEqual(
                "normalized_name_position",
                quarterback["source_signals"]["fantasypros-dynasty"]["join_method"],
            )
            self.assertEqual(
                "listed",
                quarterback["source_signals"]["fantasypros-dynasty"]["coverage_status"],
            )
            self.assertEqual("WR", receiver_output["position"])
            self.assertEqual(
                "listed",
                receiver_output["source_signals"]["fantasypros-dynasty"]["coverage_status"],
            )

            source_ids = {source["id"] for source in data["sources"]}
            self.assertIn("players", source_ids)
            self.assertIn("canonical_player_identities", source_ids)
            self.assertIn("canonical_sleeper_players", source_ids)

    def test_duplicate_canonical_sleeper_identity_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_fixture(root)

            identities_path = root / "source-data/nfl/identities/players.json"
            identities = json.loads(identities_path.read_text(encoding="utf-8"))
            identities["Players"].append(
                {
                    "CanonicalPlayerID": "canonical-duplicate",
                    "Name": "Duplicate",
                    "IDs": {"Sleeper": "1"},
                }
            )
            identities_path.write_text(json.dumps(identities), encoding="utf-8")

            config_path = root / "fantasy-management/automation/input-materialization.json"
            with self.assertRaisesRegex(
                MaterializationError,
                "duplicate active Sleeper ID 1",
            ):
                build(root, config_path)

    def test_canonical_sleeper_identity_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_fixture(root)

            sleeper_path = root / "source-data/nfl/platform/sleeper/players.json"
            sleeper = json.loads(sleeper_path.read_text(encoding="utf-8"))
            sleeper["Records"][0]["CanonicalPlayerID"] = "canonical-other"
            sleeper_path.write_text(json.dumps(sleeper), encoding="utf-8")

            config_path = root / "fantasy-management/automation/input-materialization.json"
            with self.assertRaisesRegex(
                MaterializationError,
                "Canonical Sleeper player identity mismatch",
            ):
                build(root, config_path)

    def test_malformed_canonical_fantasy_positions_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_fixture(root)

            sleeper_path = root / "source-data/nfl/platform/sleeper/players.json"
            sleeper = json.loads(sleeper_path.read_text(encoding="utf-8"))
            sleeper["Records"][0]["FantasyPositions"] = "QB"
            sleeper_path.write_text(json.dumps(sleeper), encoding="utf-8")

            config_path = root / "fantasy-management/automation/input-materialization.json"
            with self.assertRaisesRegex(
                MaterializationError,
                "FantasyPositions must be an array",
            ):
                build(root, config_path)

    def test_duplicate_catalog_source_ids_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_fixture(root)
            catalog_path = root / "fantasy-management/_ai/operations-source-catalog.json"
            catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
            catalog["sources"].append(dict(catalog["sources"][0]))
            catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
            config_path = root / "fantasy-management/automation/input-materialization.json"
            with self.assertRaisesRegex(MaterializationError, "Duplicate catalog source_id"):
                build(root, config_path)

    def _write_fixture(self, root: Path) -> None:
        paths = [
            "public/data",
            "fantasy-management/automation",
            "fantasy-management/_ai",
            "fantasy-management/league-context",
            "source-data/leagues/test-league/seasons/2026",
            "source-data/nfl/identities",
            "source-data/nfl/platform/sleeper",
            "sources/fp",
            "sources/fc",
            "sources/ppr",
            "sources/two",
            "sources/secondary",
        ]
        for path in paths:
            (root / path).mkdir(parents=True, exist_ok=True)

        config = {
            "schema_version": 2,
            "managed_team": {"identity_field": "TeamID", "team_id": 1},
            "canonical_league": {"canonical_league_id": "test-league"},
            "sources": {
                "league_display": "public/data/League.json",
                "players": "public/data/Players.json",
                "canonical_player_identities": "source-data/nfl/identities/players.json",
                "canonical_sleeper_players": "source-data/nfl/platform/sleeper/players.json",
                "timestamps": "public/data/Timestamps.json",
            },
            "source_catalog": "fantasy-management/_ai/operations-source-catalog.json",
            "outputs": {
                "managed_roster_signals": "generated/signals.json",
                "data_quality": "generated/quality.json",
            },
        }
        self._write_json(root / "fantasy-management/automation/input-materialization.json", config)
        self._write_json(
            root / "public/data/League.json",
            {
                "Teams": [
                    {
                        "TeamID": 1,
                        "Team": "Test Team",
                        "TeamAbbr": "TST",
                        "Roster": ["1", "2", "3"],
                        "Reserve": ["1"],
                        "Taxi": [],
                        "Starter": ["1", "2", "3"],
                    }
                ]
            },
        )
        self._write_json(
            root / "fantasy-management/league-context/owner-registry.json",
            {
                "version": 3,
                "canonical_league_id": "test-league",
                "owners": [
                    {
                        "name": "Owner One",
                        "team_id": 1,
                        "canonical_league_member_id": "member-1",
                    }
                ],
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
                "Settings": {"num_teams": 1},
            },
        )
        self._write_json(
            root / "source-data/leagues/test-league/seasons/2026/members.json",
            [
                {
                    "CanonicalLeagueMemberID": "member-1",
                    "DisplayName": "owner-one",
                    "ProviderMappings": [
                        {"Provider": "Sleeper", "ProviderUserID": "user-1"}
                    ],
                }
            ],
        )
        self._write_json(
            root / "source-data/leagues/test-league/seasons/2026/rosters.json",
            [
                {
                    "CanonicalLeagueMemberID": "member-1",
                    "CanonicalLeagueRosterID": "roster-1",
                    "ProviderOwnerUserID": "user-1",
                    "ProviderMappings": [
                        {"Provider": "Sleeper", "ProviderRosterID": "99"}
                    ],
                    "Players": [
                        self._canonical_player("1"),
                        self._canonical_player("2"),
                        self._canonical_player("3"),
                    ],
                    "Reserve": [self._canonical_player("1")],
                    "Taxi": [],
                    "Starters": [
                        self._canonical_player("1"),
                        self._canonical_player("2"),
                        self._canonical_player("3"),
                    ],
                }
            ],
        )
        self._write_json(
            root / "source-data/nfl/identities/players.json",
            {
                "Players": [
                    {
                        "CanonicalPlayerID": "canonical-1",
                        "Name": "Quarter Back",
                        "IDs": {"Sleeper": "1"},
                    },
                    {
                        "CanonicalPlayerID": "canonical-2",
                        "Name": "Wide Receiver",
                        "IDs": {"Sleeper": "2"},
                    },
                    {
                        "CanonicalPlayerID": "canonical-3",
                        "Name": "Reliable Kicker",
                        "IDs": {"Sleeper": "3"},
                    },
                ]
            },
        )
        self._write_json(
            root / "source-data/nfl/platform/sleeper/players.json",
            {
                "Records": [
                    {
                        "CanonicalPlayerID": "canonical-1",
                        "SleeperPlayerID": "1",
                        "Position": "QB",
                        "FantasyPositions": ["QB"],
                        "Team": "AAA",
                    },
                    {
                        "CanonicalPlayerID": "canonical-2",
                        "SleeperPlayerID": "2",
                        "Position": "WR",
                        "FantasyPositions": ["WR"],
                        "Team": "BBB",
                    },
                    {
                        "CanonicalPlayerID": "canonical-3",
                        "SleeperPlayerID": "3",
                        "Position": "K",
                        "FantasyPositions": ["K"],
                        "Team": "CCC",
                    },
                ]
            },
        )
        self._write_json(
            root / "public/data/Players.json",
            [
                self._player("1", "Quarter Back Jr.", "QB", "AAA", injured=True),
                self._player("2", "Wide Receiver", "WR", "BBB"),
                self._player("3", "Reliable Kicker", "K", "CCC"),
            ],
        )
        self._write_json(
            root / "public/data/Timestamps.json",
            {
                "Players": "2026-08-05T19:15:26Z",
                "League": "2026-08-05T18:00:00Z",
            },
        )

        common_rows = [
            {"name": "Quarter Back", "position": "QB", "team": "AAA"},
            {"name": "Wide Receiver", "position": "WR", "team": "BBB"},
        ]
        self._write_csv(
            root / "sources/fp/ranking.csv",
            [
                {**common_rows[0], "Rank": "10", "position_rank": "QB5", "tier": "2"},
                {**common_rows[1], "Rank": "20", "position_rank": "WR10", "tier": "3"},
            ],
        )
        self._write_csv(
            root / "sources/fc/ranking.csv",
            [
                {
                    **common_rows[0],
                    "Rank": "9",
                    "position_rank": "4",
                    "tier": "2",
                    "value": "5000",
                    "trend_30_day": "100",
                    "roster_percent": "0.99",
                    "trade_frequency": "0.01",
                    "sleeper_id": "1",
                },
                {
                    **common_rows[1],
                    "Rank": "22",
                    "position_rank": "11",
                    "tier": "3",
                    "value": "3500",
                    "trend_30_day": "-20",
                    "roster_percent": "0.95",
                    "trade_frequency": "0.02",
                    "sleeper_id": "2",
                },
            ],
        )
        self._write_csv(
            root / "sources/ppr/ranking.csv",
            [self._adp_row(common_rows[0], "4", "30.0"), self._adp_row(common_rows[1], "2", "12.3")],
        )
        self._write_csv(
            root / "sources/two/ranking.csv",
            [self._adp_row(common_rows[0], "1", "2.1"), self._adp_row(common_rows[1], "5", "44.0")],
        )
        self._write_csv(
            root / "sources/secondary/ranking.csv",
            [{**common_rows[0], "Rank": "12"}, {**common_rows[1], "Rank": "25"}],
        )
        for source in ("fp", "fc", "ppr", "two", "secondary"):
            self._write_json(
                root / f"sources/{source}/latest.json",
                {
                    "ranking_file": f"sources/{source}/ranking.csv",
                    "snapshot_date": "2026-08-05",
                    "ranking_fetched_at": "2026-08-05T08:00:00Z",
                },
            )

        catalog = {
            "schema_version": 1,
            "catalog_id": "fantasy-operations-source-catalog",
            "purpose": "fixture",
            "sources": [
                self._source(
                    "fantasypros-dynasty",
                    "expert_consensus",
                    "fantasypros",
                    "sources/fp/latest.json",
                    "market",
                    "fantasypros",
                    [
                        ("overall_rank", "Rank", "number", None),
                        ("position_rank", "position_rank", "text", None),
                        ("tier", "tier", "text", None),
                    ],
                ),
                self._source(
                    "fantasycalc-dynasty",
                    "market_value",
                    "fantasycalc",
                    "sources/fc/latest.json",
                    "market",
                    "fantasycalc",
                    [("overall_rank", "Rank", "number", None)],
                    id_join=True,
                ),
                self._source(
                    "ffc-ppr",
                    "adp",
                    "ffc",
                    "sources/ppr/latest.json",
                    "redraft_adp",
                    "ppr_8_team",
                    self._adp_signals(),
                    primary_for=["RB", "WR", "TE"],
                ),
                self._source(
                    "ffc-two",
                    "adp",
                    "ffc",
                    "sources/two/latest.json",
                    "redraft_adp",
                    "two_qb_10_team",
                    self._adp_signals(),
                    primary_for=["QB"],
                ),
                self._source(
                    "new-secondary-expert",
                    "expert_consensus",
                    "example-provider",
                    "sources/secondary/latest.json",
                    "market",
                    "secondary_expert",
                    [("overall_rank", "Rank", "number", None)],
                ),
            ],
            "derived_views": {
                "redraft_adp": {
                    "primary_source_rule": "roles.primary_for_positions",
                    "format_gap": {
                        "left_source_id": "ffc-two",
                        "right_source_id": "ffc-ppr",
                        "signal": "percentile",
                    },
                }
            },
        }
        self._write_json(root / "fantasy-management/_ai/operations-source-catalog.json", catalog)

    @staticmethod
    def _canonical_player(player_id: str) -> dict[str, object]:
        return {
            "CanonicalPlayerID": f"canonical-{player_id}",
            "ProviderMappings": [
                {"Provider": "Sleeper", "ProviderPlayerID": player_id}
            ],
        }

    @staticmethod
    def _player(player_id: str, name: str, position: str, team: str, injured: bool = False) -> dict[str, object]:
        return {
            "ID": player_id,
            "Name": name,
            "Position": position,
            "TeamAbbr": team,
            "Injured": injured,
            "InjuryDetails": {
                "Description": "limited" if injured else "",
                "Designation": "Questionable" if injured else "",
                "ReturnDate": "",
                "Date": "",
            },
        }

    @staticmethod
    def _adp_row(base: dict[str, str], rank: str, adp: str) -> dict[str, str]:
        return {
            **base,
            "Rank": rank,
            "adp": adp,
            "times_drafted": "120",
            "stdev": "2.1",
            "sample_total_drafts": "1000",
            "sample_start_date": "2026-08-01",
            "sample_end_date": "2026-08-05",
        }

    @staticmethod
    def _adp_signals() -> list[tuple[str, str, str, str | None]]:
        return [
            ("rank", "Rank", "number", None),
            ("percentile", "Rank", "number", "percentile_from_rank"),
            ("adp", "adp", "number", None),
            ("times_drafted", "times_drafted", "number", None),
        ]

    @staticmethod
    def _source(
        source_id: str,
        source_kind: str,
        provider: str,
        pointer: str,
        section: str,
        key: str,
        signals: list[tuple[str, str, str, str | None]],
        *,
        id_join: bool = False,
        primary_for: list[str] | None = None,
    ) -> dict[str, object]:
        strategies: list[dict[str, str]] = []
        if id_join:
            strategies.append(
                {
                    "type": "id",
                    "method": "sleeper_id",
                    "player_field": "ID",
                    "source_field": "sleeper_id",
                }
            )
        strategies.append(
            {
                "type": "name_position",
                "method": "normalized_name_position",
                "name_field": "name",
                "position_field": "position",
                "team_field": "team",
            }
        )
        signal_entries = []
        for target, source_field, signal_type, transform in signals:
            entry = {"target": target, "source_field": source_field, "type": signal_type}
            if transform:
                entry["transform"] = transform
            signal_entries.append(entry)
        return {
            "source_id": source_id,
            "active": True,
            "source_kind": source_kind,
            "provider": provider,
            "dataset_id": source_id,
            "access": {
                "type": "repo_latest_pointer",
                "location": pointer,
                "ranking_path_field": "ranking_file",
                "timestamp_fields": ["ranking_fetched_at", "snapshot_date"],
            },
            "applicability": {"entity_types": ["player"], "positions": ["QB", "RB", "WR", "TE"]},
            "absence_policy": {
                "inapplicable": "not_applicable",
                "missing": "not_listed",
                "ambiguous": "ambiguous_join",
            },
            "join": {"strategies": strategies},
            "output": {"section": section, "key": key, "signals": signal_entries},
            "roles": {"primary_for_positions": primary_for or []},
            "quality": {
                "minimum_rows": 1,
                "missing_severity": "none",
                "ambiguous_severity": "warning",
                "row_count_severity": "error",
            },
            "freshness": {"max_age_hours": 72},
            "format_context": {},
        }

    @staticmethod
    def _write_json(path: Path, value: object) -> None:
        path.write_text(json.dumps(value), encoding="utf-8")

    @staticmethod
    def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
        fieldnames = sorted({key for row in rows for key in row})
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)


if __name__ == "__main__":
    unittest.main()
