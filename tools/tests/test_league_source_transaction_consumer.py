from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.transaction_canonical_consumer import build_repo_canonical_transactions


class TransactionCanonicalConsumerTests(unittest.TestCase):
    def test_builds_legacy_app_base_shape_from_week_partitions(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            season_dir = root / "source-data" / "leagues" / "test-league" / "seasons" / "2026"
            transaction_dir = season_dir / "transactions"
            transaction_dir.mkdir(parents=True)

            rosters = [
                {
                    "CanonicalLeagueRosterID": "clr-a",
                    "ProviderMappings": [
                        {"Provider": "Sleeper", "ProviderRosterID": "1"}
                    ],
                },
                {
                    "CanonicalLeagueRosterID": "clr-b",
                    "ProviderMappings": [
                        {"Provider": "Sleeper", "ProviderRosterID": "5"}
                    ],
                },
            ]
            (season_dir / "rosters.json").write_text(
                json.dumps(rosters), encoding="utf-8"
            )

            transaction = {
                "Adds": [
                    {
                        "CanonicalLeagueRosterID": "clr-b",
                        "Player": {
                            "ProviderMappings": [
                                {"Provider": "Sleeper", "ProviderPlayerID": "13414"}
                            ]
                        },
                    }
                ],
                "CanonicalLeagueRosterIDs": ["clr-a", "clr-b"],
                "CreatedAt": 1788949592892,
                "DraftPicks": [],
                "Drops": [
                    {
                        "CanonicalLeagueRosterID": "clr-a",
                        "Player": {
                            "ProviderMappings": [
                                {"Provider": "Sleeper", "ProviderPlayerID": "13414"}
                            ]
                        },
                    }
                ],
                "Metadata": {"notes": "fixture"},
                "ProviderMappings": [
                    {"Provider": "Sleeper", "ProviderTransactionID": "tx-1"}
                ],
                "Status": "complete",
                "Type": "trade",
                "Week": 2,
            }
            (transaction_dir / "week-2.json").write_text(
                json.dumps([transaction]), encoding="utf-8"
            )

            result = build_repo_canonical_transactions(
                root,
                canonical_league_id="test-league",
                season=2026,
            )

            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["Source"], "Sleeper")
            self.assertEqual(result[0]["TransactionID"], "tx-1")
            self.assertEqual(result[0]["Season"], "2026")
            self.assertEqual(result[0]["Week"], 2)
            self.assertEqual(result[0]["RosterIDs"], [1, 5])
            self.assertEqual(result[0]["Adds"], {"13414": 5})
            self.assertEqual(result[0]["Drops"], {"13414": 1})
            self.assertEqual(result[0]["Notes"], "fixture")


class CurrentRepositoryTransactionCanonicalConsumerIntegrationTests(unittest.TestCase):
    def test_current_repo_consumer_can_materialize_nfl_reise_2026(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        result = build_repo_canonical_transactions(
            repo_root,
            canonical_league_id="nfl-reise",
            season=2026,
        )
        self.assertGreater(len(result), 0)
        ids = [str(item["TransactionID"]) for item in result]
        self.assertEqual(len(ids), len(set(ids)))


if __name__ == "__main__":
    unittest.main()
