from __future__ import annotations

import json
import tempfile
import unittest
from collections import defaultdict
from pathlib import Path

from tools.nfl_source_data_lib.coverage import build_player_stats_identity_coverage


class HistoricalNFLPlayerIdentityCoverageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_partition(self, season: int, week: int, records: list[dict[str, object]]) -> None:
        path = self.root / f"source-data/nfl/player-stats/{season}/{week:02d}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"Season": season, "Week": week, "Records": records}),
            encoding="utf-8",
        )

    @staticmethod
    def record(gsis: str | None, canonical_player_id: str | None) -> dict[str, object]:
        return {
            "CanonicalPlayerID": canonical_player_id,
            "SourceIDs": {"GSIS": gsis} if gsis is not None else {},
            "PlayerName": "Fixture Player",
            "Stats": {"receiving_yards": 10},
        }

    def test_same_gsis_can_anchor_one_canonical_player_across_seasons(self) -> None:
        self.write_partition(2023, 1, [self.record("00-1", "NFLP-1")])
        self.write_partition(2024, 1, [self.record("00-1", "NFLP-1")])
        self.write_partition(2025, 1, [self.record("00-1", "NFLP-1")])

        coverage = build_player_stats_identity_coverage(self.root, current_season=2026)

        self.assertTrue(coverage["Ready"])
        self.assertEqual(3, coverage["HistoricalRecordCount"])
        self.assertEqual(3, coverage["HistoricalResolvedRecordCount"])
        self.assertEqual(0, coverage["HistoricalUnresolvedRecordCount"])
        self.assertEqual(1, coverage["MultiSeasonCanonicalPlayerCount"])
        self.assertEqual([], coverage["GSISCanonicalConflicts"])

    def test_unresolved_historical_stat_record_is_not_ready(self) -> None:
        self.write_partition(2025, 1, [self.record("00-1", None)])

        coverage = build_player_stats_identity_coverage(self.root, current_season=2026)

        self.assertFalse(coverage["Ready"])
        self.assertEqual(1, coverage["HistoricalUnresolvedRecordCount"])
        self.assertEqual(["00-1"], coverage["HistoricalUnresolvedGSISIDs"])

    def test_gsis_mapping_to_multiple_canonical_players_fails_closed(self) -> None:
        self.write_partition(2024, 1, [self.record("00-1", "NFLP-1")])
        self.write_partition(2025, 1, [self.record("00-1", "NFLP-2")])

        coverage = build_player_stats_identity_coverage(self.root, current_season=2026)

        self.assertFalse(coverage["Ready"])
        self.assertEqual(1, coverage["GSISCanonicalConflictCount"])
        self.assertEqual(
            [{"GSIS": "00-1", "CanonicalPlayerIDs": ["NFLP-1", "NFLP-2"]}],
            coverage["GSISCanonicalConflicts"],
        )

    def test_current_unresolved_record_is_diagnostic_but_not_historical_failure(self) -> None:
        self.write_partition(2025, 1, [self.record("00-1", "NFLP-1")])
        self.write_partition(2026, 1, [self.record("00-2", None)])

        coverage = build_player_stats_identity_coverage(self.root, current_season=2026)

        self.assertTrue(coverage["Ready"])
        self.assertEqual(0, coverage["HistoricalUnresolvedRecordCount"])
        self.assertEqual(1, coverage["CurrentUnresolvedRecordCount"])
        self.assertEqual(["00-2"], coverage["CurrentUnresolvedGSISIDs"])


class RealCareerIdentityRegressionTests(unittest.TestCase):
    def test_repository_historical_player_stats_have_complete_canonical_identity(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        coverage = build_player_stats_identity_coverage(repo_root, current_season=2026)
        problematic_seasons = {
            season: details
            for season, details in coverage["BySeason"].items()
            if details["Historical"]
            and (details["UnresolvedRecordCount"] or details["MissingGSISRecordCount"])
        }
        unresolved_ids = set(coverage["HistoricalUnresolvedGSISIDs"])
        unresolved_examples: dict[str, list[dict[str, object]]] = defaultdict(list)
        for season, details in problematic_seasons.items():
            season_root = repo_root / f"source-data/nfl/player-stats/{season}"
            for partition in sorted(season_root.glob("*.json")):
                payload = json.loads(partition.read_text(encoding="utf-8"))
                for record in payload.get("Records", []):
                    gsis = str((record.get("SourceIDs") or {}).get("GSIS") or "")
                    if gsis not in unresolved_ids or record.get("CanonicalPlayerID"):
                        continue
                    if len(unresolved_examples[gsis]) >= 5:
                        continue
                    unresolved_examples[gsis].append(
                        {
                            "Season": int(season),
                            "Week": record.get("Week"),
                            "SeasonType": record.get("SeasonType"),
                            "PlayerName": record.get("PlayerName"),
                            "Position": record.get("Position"),
                            "Team": record.get("Team"),
                            "OpponentTeam": record.get("OpponentTeam"),
                        }
                    )
        diagnostic = {
            "HistoricalRecordCount": coverage["HistoricalRecordCount"],
            "HistoricalUnresolvedRecordCount": coverage["HistoricalUnresolvedRecordCount"],
            "HistoricalMissingGSISRecordCount": coverage["HistoricalMissingGSISRecordCount"],
            "HistoricalUnresolvedGSISIDs": coverage["HistoricalUnresolvedGSISIDs"],
            "GSISCanonicalConflicts": coverage["GSISCanonicalConflicts"],
            "ProblematicSeasons": problematic_seasons,
            "UnresolvedExamples": dict(sorted(unresolved_examples.items())),
        }
        self.assertTrue(coverage["Ready"], json.dumps(diagnostic, indent=2, sort_keys=True))

    def test_justin_jefferson_keeps_one_canonical_identity_across_historical_week_one_stats(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        canonical_ids: set[str] = set()
        gsis_ids: set[str] = set()

        for season in range(2020, 2026):
            path = repo_root / f"source-data/nfl/player-stats/{season}/01.json"
            self.assertTrue(path.exists(), f"missing canonical Week 1 stats for {season}")
            payload = json.loads(path.read_text(encoding="utf-8"))
            matches = [
                record
                for record in payload.get("Records", [])
                if record.get("PlayerName") == "Justin Jefferson"
            ]
            self.assertEqual(1, len(matches), f"expected one Justin Jefferson Week 1 record in {season}")
            record = matches[0]
            canonical_player_id = record.get("CanonicalPlayerID")
            gsis = (record.get("SourceIDs") or {}).get("GSIS")
            self.assertTrue(canonical_player_id, f"missing CanonicalPlayerID for Justin Jefferson in {season}")
            self.assertTrue(gsis, f"missing GSIS for Justin Jefferson in {season}")
            canonical_ids.add(str(canonical_player_id))
            gsis_ids.add(str(gsis))

        self.assertEqual(1, len(canonical_ids), f"career split across CanonicalPlayerIDs: {sorted(canonical_ids)}")
        self.assertEqual(1, len(gsis_ids), f"career fixture changed GSIS unexpectedly: {sorted(gsis_ids)}")


if __name__ == "__main__":
    unittest.main()
