from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.source_data_readiness import HISTORICAL_BANDS, build_league_readiness, build_nfl_readiness


class SourceDataReadinessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_json(self, relative: str, payload: object) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def write_text(self, relative: str, content: str = "x") -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def configure_player_stats_registry(self) -> None:
        self.write_json("source-data/nfl/schedules/2026.json", {})
        self.write_json(
            "source-data/registry.json",
            {
                "datasets": [
                    {
                        "id": "nflverse.player-stats",
                        "rawPath": "providers/nflverse/player-stats/raw-{season}.csv",
                        "metadataPath": "providers/nflverse/player-stats/metadata-{season}.json",
                        "availabilityPolicy": "current-season-may-be-unavailable",
                    }
                ]
            },
        )

    def mark_player_stats_ready(self, season: int) -> None:
        self.write_text(f"source-data/providers/nflverse/player-stats/raw-{season}.csv")
        self.write_json(f"source-data/providers/nflverse/player-stats/metadata-{season}.json", {"availabilityStatus": "available"})
        self.write_json(f"source-data/nfl/player-stats/{season}/1.json", {"Season": season, "Week": 1})

    def test_missing_historical_partition_is_hard_failure_but_current_unavailable_is_not(self) -> None:
        self.configure_player_stats_registry()
        self.mark_player_stats_ready(2025)
        self.write_json(
            "source-data/providers/nflverse/player-stats/metadata-2026.json",
            {"availabilityStatus": "not-yet-available"},
        )

        with patch.dict(
            HISTORICAL_BANDS,
            {"nflverse.player-stats": {"start": 2024, "canonical": "player-stats"}},
            clear=True,
        ):
            readiness = build_nfl_readiness(self.root)

        dataset = readiness["Datasets"]["nflverse.player-stats"]
        self.assertEqual(dataset["MissingHistoricalSeasons"], [2024])
        self.assertFalse(readiness["ReadyForHistoricalScoring"])
        self.assertIn("nflverse.player-stats: missing historical seasons [2024]", readiness["HardFailures"])
        current = next(row for row in dataset["Seasons"] if row["Season"] == 2026)
        self.assertFalse(current["Historical"])
        self.assertEqual(current["AvailabilityStatus"], "not-yet-available")
        self.assertFalse(current["Ready"])

    def test_complete_history_is_ready_even_when_current_season_is_not_yet_available(self) -> None:
        self.configure_player_stats_registry()
        self.mark_player_stats_ready(2024)
        self.mark_player_stats_ready(2025)
        self.write_json(
            "source-data/providers/nflverse/player-stats/metadata-2026.json",
            {"availabilityStatus": "not-yet-available"},
        )

        with patch.dict(
            HISTORICAL_BANDS,
            {"nflverse.player-stats": {"start": 2024, "canonical": "player-stats"}},
            clear=True,
        ):
            readiness = build_nfl_readiness(self.root)

        self.assertTrue(readiness["ReadyForHistoricalScoring"])
        self.assertEqual(readiness["HardFailures"], [])
        self.assertEqual(readiness["Datasets"]["nflverse.player-stats"]["MissingHistoricalSeasons"], [])

    def test_known_unavailable_historical_partition_is_explicit_but_not_a_hard_failure(self) -> None:
        self.write_json("source-data/nfl/schedules/2014.json", {})
        self.write_json(
            "source-data/registry.json",
            {
                "datasets": [
                    {
                        "id": "nflverse.snap-counts",
                        "rawPath": "providers/nflverse/snap-counts/raw-{season}.csv",
                        "metadataPath": "providers/nflverse/snap-counts/metadata-{season}.json",
                        "availabilityPolicy": "current-season-may-be-unavailable",
                    }
                ]
            },
        )
        self.write_text("source-data/providers/nflverse/snap-counts/raw-2013.csv")
        self.write_json(
            "source-data/providers/nflverse/snap-counts/metadata-2013.json",
            {"availabilityStatus": "available"},
        )
        self.write_json("source-data/nfl/snap-counts/2013/1.json", {"Season": 2013, "Week": 1})

        with patch.dict(
            HISTORICAL_BANDS,
            {
                "nflverse.snap-counts": {
                    "start": 2012,
                    "canonical": "snap-counts",
                    "knownUnavailable": {2012: "upstream schema-only asset"},
                }
            },
            clear=True,
        ):
            readiness = build_nfl_readiness(self.root)

        dataset = readiness["Datasets"]["nflverse.snap-counts"]
        self.assertEqual(dataset["MissingHistoricalSeasons"], [])
        self.assertEqual(
            dataset["KnownUnavailableHistoricalSeasons"],
            [{"Season": 2012, "Reason": "upstream schema-only asset"}],
        )
        self.assertEqual(dataset["HistoricalSeasonCountNominal"], 2)
        self.assertEqual(dataset["HistoricalSeasonCountExpected"], 1)
        unavailable = next(row for row in dataset["Seasons"] if row["Season"] == 2012)
        self.assertTrue(unavailable["Historical"])
        self.assertTrue(unavailable["KnownUnavailable"])
        self.assertFalse(unavailable["RequiredForReadiness"])
        self.assertFalse(unavailable["Ready"])
        self.assertTrue(readiness["ReadyForHistoricalScoring"])
        self.assertEqual(readiness["HardFailures"], [])
        self.assertEqual(
            readiness["HistoricalBackfillPolicy"]["KnownUnavailableHistoricalPartitions"],
            [{"DatasetID": "nflverse.snap-counts", "Season": 2012, "Reason": "upstream schema-only asset"}],
        )

    def _configure_league(self) -> str:
        self.write_json(
            "source-data/leagues/_bootstrap/nfl-reise.json",
            {
                "CanonicalLeagueID": "nfl-reise",
                "Provider": "sleeper",
                "CurrentProviderLeagueID": "123",
            },
        )
        self.write_json(
            "source-data/leagues/nfl-reise/manifest.json",
            {
                "Seasons": [
                    {
                        "Season": 2025,
                        "CanonicalLeagueSeasonID": "nfl-reise-2025",
                        "ProviderMappings": [{"Provider": "sleeper", "ProviderLeagueID": "123"}],
                    }
                ]
            },
        )
        season_root = "source-data/leagues/nfl-reise/seasons/2025"
        self.write_json(
            f"{season_root}/league.json",
            {"WeekStructure": {"ExpectedFinalWeek": 17}, "ScoringSettings": {"pass_td": 4}},
        )
        for name in ("members.json", "rosters.json", "drafts.json", "winners-bracket.json", "losers-bracket.json"):
            self.write_json(f"{season_root}/{name}", [])
        return season_root

    def test_league_readiness_uses_human_readable_nfl_reise_namespace(self) -> None:
        self._configure_league()

        readiness = build_league_readiness(self.root)

        self.assertTrue(readiness["Ready"])
        self.assertEqual(readiness["HardFailures"], [])
        self.assertEqual(readiness["LeagueCount"], 1)
        self.assertEqual(readiness["Leagues"][0]["CanonicalLeagueID"], "nfl-reise")
        season = readiness["Leagues"][0]["Seasons"][0]
        self.assertEqual(season["CanonicalLeagueSeasonID"], "nfl-reise-2025")
        self.assertTrue(season["PlayerReferenceCoverage"]["Ready"])

    def test_unresolved_league_player_reference_is_a_hard_failure(self) -> None:
        season_root = self._configure_league()
        self.write_json(
            f"{season_root}/rosters.json",
            [
                {
                    "Players": [
                        {
                            "CanonicalPlayerID": None,
                            "ProviderMappings": [
                                {"Provider": "Sleeper", "ProviderPlayerID": "S1"}
                            ],
                        },
                        {
                            "CanonicalPlayerID": "NFLP-2",
                            "ProviderMappings": [
                                {"Provider": "Sleeper", "ProviderPlayerID": "S2"}
                            ],
                        },
                    ]
                }
            ],
        )

        readiness = build_league_readiness(self.root)

        self.assertFalse(readiness["Ready"])
        self.assertEqual(1, len(readiness["HardFailures"]))
        self.assertIn("1 unresolved canonical player references", readiness["HardFailures"][0])
        coverage = readiness["Leagues"][0]["Seasons"][0]["PlayerReferenceCoverage"]
        self.assertEqual(2, coverage["ReferenceCount"])
        self.assertEqual(1, coverage["ResolvedReferenceCount"])
        self.assertEqual(1, coverage["UnresolvedReferenceCount"])
        self.assertEqual(["S1"], coverage["UnresolvedSleeperPlayerIDs"])
        self.assertFalse(coverage["Ready"])


if __name__ == "__main__":
    unittest.main()
