from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.transaction_canonical_shadow import (
    build_repo_shadow_report,
    build_roster_provider_lookup,
    build_shadow_report,
    convert_canonical_transaction,
)


class TransactionCanonicalShadowTests(unittest.TestCase):
    def test_converts_canonical_transaction_to_legacy_base_shape(self) -> None:
        rosters = [
            {
                "CanonicalLeagueRosterID": "clr-a",
                "ProviderMappings": [{"Provider": "Sleeper", "ProviderRosterID": "5"}],
            },
            {
                "CanonicalLeagueRosterID": "clr-b",
                "ProviderMappings": [{"Provider": "Sleeper", "ProviderRosterID": "1"}],
            },
        ]
        lookup = build_roster_provider_lookup(rosters)
        canonical = {
            "Adds": [
                {
                    "CanonicalLeagueRosterID": "clr-a",
                    "Player": {
                        "ProviderMappings": [{"Provider": "Sleeper", "ProviderPlayerID": "13414"}]
                    },
                }
            ],
            "CanonicalLeagueRosterIDs": ["clr-b", "clr-a"],
            "CreatedAt": 1788949592892,
            "DraftPicks": [
                {
                    "OriginalCanonicalLeagueRosterID": "clr-a",
                    "PreviousOwnerCanonicalLeagueRosterID": "clr-a",
                    "OwnerCanonicalLeagueRosterID": "clr-b",
                    "Round": 4,
                    "Season": "2028",
                }
            ],
            "Drops": [
                {
                    "CanonicalLeagueRosterID": "clr-b",
                    "Player": {
                        "ProviderMappings": [{"Provider": "Sleeper", "ProviderPlayerID": "13414"}]
                    },
                }
            ],
            "Metadata": {"notes": "note"},
            "ProviderMappings": [
                {"Provider": "Sleeper", "ProviderTransactionID": "1403359943054082048"}
            ],
            "Status": "complete",
            "Type": "trade",
            "Week": 1,
        }
        converted = convert_canonical_transaction(canonical, lookup, season=2026)
        self.assertEqual(converted["TransactionID"], "1403359943054082048")
        self.assertEqual(converted["Source"], "Sleeper")
        self.assertEqual(converted["Season"], "2026")
        self.assertEqual(converted["CreatedDate"], "2026-09-09")
        self.assertEqual(converted["RosterIDs"], [1, 5])
        self.assertEqual(converted["Adds"], {"13414": 5})
        self.assertEqual(converted["Drops"], {"13414": 1})
        self.assertEqual(converted["Notes"], "note")
        self.assertEqual(
            converted["DraftPicks"][0],
            {
                "DraftType": None,
                "DraftInstance": None,
                "DraftCode": None,
                "DraftSource": "Sleeper",
                "DraftKey": None,
                "Season": "2028",
                "Round": 4,
                "OriginalOwnerRosterID": 5,
                "PreviousOwnerRosterID": 5,
                "NewOwnerRosterID": 1,
                "SleeperDraftID": None,
            },
        )

    def test_report_treats_manual_overlay_as_classified_not_strict_failure(self) -> None:
        canonical = [
            {
                "Source": "Sleeper",
                "TransactionID": "t1",
                "Type": "trade",
                "Status": "complete",
                "Season": "2026",
                "Week": 1,
                "CreatedAt": 1,
                "CreatedDate": "1970-01-01",
                "RosterIDs": [1, 5],
                "Adds": {"p": 5},
                "Drops": {"p": 1},
                "DraftPicks": [],
                "Notes": None,
            },
            {
                "Source": "Sleeper",
                "TransactionID": "t2",
                "Type": "trade",
                "Status": "complete",
                "Season": "2026",
                "Week": 1,
                "CreatedAt": 2,
                "CreatedDate": "1970-01-01",
                "RosterIDs": [1, 5],
                "Adds": {},
                "Drops": {},
                "DraftPicks": [],
                "Notes": None,
            },
        ]
        legacy = [
            dict(canonical[0]),
            {
                **canonical[1],
                "Source": "Sleeper_Manual",
                "DraftPicks": [
                    {
                        "DraftSource": "Manual",
                        "Season": "2028",
                        "Round": 4,
                        "OriginalOwnerRosterID": 5,
                        "PreviousOwnerRosterID": 5,
                        "NewOwnerRosterID": 1,
                    }
                ],
            },
            {
                "Source": "Manual",
                "TransactionID": "Manual_2026_x",
                "Type": "trade",
                "Status": "complete",
                "Season": "2026",
                "Week": 1,
                "CreatedAt": 3,
                "CreatedDate": "1970-01-01",
                "RosterIDs": [],
                "Adds": {},
                "Drops": {},
                "DraftPicks": [],
                "Notes": None,
            },
        ]
        report = build_shadow_report(
            canonical,
            legacy,
            canonical_league_id="nfl-reise",
            season=2026,
            manual_bound_ids={"t2"},
        )
        self.assertTrue(report["StrictParity"])
        self.assertEqual(report["Counts"]["StrictCompared"], 1)
        self.assertEqual(report["Classifications"]["ManualBound"], ["t2"])
        self.assertEqual(report["Classifications"]["ManualOnly"], ["Manual_2026_x"])
        self.assertEqual(
            report["Classifications"]["ManualOverlayDifferences"],
            [{"TransactionID": "t2", "Fields": ["DraftPicks", "Source"]}],
        )

    def test_report_fails_strict_parity_on_canonical_owned_field_difference(self) -> None:
        canonical = [
            {
                "Source": "Sleeper",
                "TransactionID": "t1",
                "Type": "waiver",
                "Status": "complete",
                "Season": "2026",
                "Week": 1,
                "CreatedAt": 1,
                "CreatedDate": "1970-01-01",
                "RosterIDs": [1],
                "Adds": {"p": 1},
                "Drops": {},
                "DraftPicks": [],
                "Notes": None,
            }
        ]
        legacy = [{**canonical[0], "Status": "failed"}]
        report = build_shadow_report(
            canonical,
            legacy,
            canonical_league_id="nfl-reise",
            season=2026,
        )
        self.assertFalse(report["StrictParity"])
        self.assertEqual(
            report["Classifications"]["FieldDifferences"],
            [{"TransactionID": "t1", "Fields": ["Status"]}],
        )

    def test_repository_fixture_proves_week_partition_loading_without_hardcoded_ceiling(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            season_dir = root / "source-data" / "leagues" / "test-league" / "seasons" / "2026"
            transaction_dir = season_dir / "transactions"
            transaction_dir.mkdir(parents=True)
            (root / "public" / "data").mkdir(parents=True)
            rosters = [
                {
                    "CanonicalLeagueRosterID": "clr-a",
                    "ProviderMappings": [{"Provider": "Sleeper", "ProviderRosterID": "2"}],
                }
            ]
            (season_dir / "rosters.json").write_text(json.dumps(rosters), encoding="utf-8")
            transaction = {
                "Adds": [],
                "CanonicalLeagueRosterIDs": ["clr-a"],
                "CreatedAt": 1000,
                "DraftPicks": [],
                "Drops": [],
                "Metadata": {},
                "ProviderMappings": [{"Provider": "Sleeper", "ProviderTransactionID": "tx-21"}],
                "Status": "complete",
                "Type": "commissioner",
                "Week": 21,
            }
            (transaction_dir / "week-21.json").write_text(json.dumps([transaction]), encoding="utf-8")
            legacy = [
                {
                    "Source": "Sleeper",
                    "TransactionID": "tx-21",
                    "Type": "commissioner",
                    "Status": "complete",
                    "Season": "2026",
                    "Week": 21,
                    "CreatedAt": 1000,
                    "CreatedDate": "1970-01-01",
                    "RosterIDs": [2],
                    "Adds": {},
                    "Drops": {},
                    "DraftPicks": [],
                    "Notes": None,
                }
            ]
            (root / "public" / "data" / "Transactions.json").write_text(json.dumps(legacy), encoding="utf-8")
            (root / "public" / "data" / "Transactions_Manual.json").write_text("[]", encoding="utf-8")
            report = build_repo_shadow_report(root, canonical_league_id="test-league", season=2026)
            self.assertTrue(report["StrictParity"])
            self.assertEqual(report["Counts"]["CanonicalAdapted"], 1)


class CurrentRepositoryTransactionShadowIntegrationTests(unittest.TestCase):
    def test_current_nfl_reise_2026_canonical_transactions_match_legacy_owned_fields(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        report = build_repo_shadow_report(repo_root, canonical_league_id="nfl-reise", season=2026)
        self.assertTrue(report["StrictParity"], json.dumps(report, indent=2, sort_keys=True))
