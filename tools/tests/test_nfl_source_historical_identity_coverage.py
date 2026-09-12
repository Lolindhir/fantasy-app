from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from tools.nfl_source_data_lib.canonical_identity import identity_lookup
from tools.nfl_source_data_lib.common import load_registry
from tools.nfl_source_data_lib.coverage import build_player_stats_identity_coverage
from tools.nfl_source_data_lib.identity import build_identities


class HistoricalNFLPlayerIdentityCoverageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_partition(self, season: int, week: int, records: list[dict[str, object]]) -> None:
        path = self.root / f"source-data/nfl/player-stats/{season}/{week:02d}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"Season": season, "Week": week, "Records": records}), encoding="utf-8")

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
    _RAW_CONTEXT_FIELDS = {
        "player_id",
        "player_name",
        "player_display_name",
        "position",
        "position_group",
        "headshot_url",
        "season",
        "week",
        "season_type",
        "game_id",
        "team",
        "opponent_team",
    }

    @staticmethod
    def _is_nonzero(value: object) -> bool:
        text = str(value or "").strip()
        if not text:
            return False
        try:
            return float(text) != 0.0
        except ValueError:
            return True

    def _unclassified_raw_examples(self, repo_root: Path) -> list[dict[str, object]]:
        examples: list[dict[str, object]] = []
        raw_root = repo_root / "source-data/providers/nflverse/player-stats"
        for raw_path in sorted(raw_root.glob("raw-*.csv")):
            with raw_path.open("r", encoding="utf-8-sig", newline="") as handle:
                for row in csv.DictReader(handle):
                    if str(row.get("player_id") or "").strip():
                        continue
                    name = str(row.get("player_display_name") or row.get("player_name") or "").strip()
                    position = str(row.get("position") or "").strip()
                    is_team_aggregate = name.casefold() == "team" or (not name and not position)
                    if is_team_aggregate:
                        continue
                    examples.append(
                        {
                            "Season": row.get("season"),
                            "Week": row.get("week"),
                            "SeasonType": row.get("season_type"),
                            "GameID": row.get("game_id"),
                            "PlayerName": name or None,
                            "Position": position or None,
                            "Team": row.get("team") or None,
                            "OpponentTeam": row.get("opponent_team") or None,
                            "NonZeroStats": {
                                key: value
                                for key, value in row.items()
                                if key not in self._RAW_CONTEXT_FIELDS and self._is_nonzero(value)
                            },
                        }
                    )
        return examples

    def test_repository_historical_unresolved_ids_are_repairable_from_provider_identity(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        coverage = build_player_stats_identity_coverage(repo_root, current_season=2026)
        unresolved = set(coverage["HistoricalUnresolvedGSISIDs"])
        self.assertNotIn("0", unresolved, "team aggregate sentinel must not be treated as a person")

        datasets = {dataset.id: dataset for dataset in load_registry(repo_root)}
        canonical, _, _, _, _ = build_identities(repo_root, datasets)
        rebuilt_lookup = identity_lookup(canonical)
        still_unresolved = sorted(gsis for gsis in unresolved if ("GSIS", gsis) not in rebuilt_lookup)

        self.assertEqual(
            [],
            still_unresolved,
            "historical player-stat identities must be repairable from authoritative provider evidence",
        )

    def test_repository_raw_missing_player_ids_are_explicit_team_aggregates(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        coverage = build_player_stats_identity_coverage(repo_root, current_season=2026)
        diagnostic = json.dumps(
            {
                "RawUnclassifiedMissingPlayerIDExamples": coverage["RawUnclassifiedMissingPlayerIDExamples"],
                "RawUnclassifiedMissingPlayerIDDetails": self._unclassified_raw_examples(repo_root),
                "RawMissingPlayerIDBySeason": coverage["RawMissingPlayerIDBySeason"],
            },
            indent=2,
            sort_keys=True,
        )
        self.assertGreater(coverage["HistoricalRawMissingPlayerIDRecordCount"], 0)
        self.assertEqual(
            coverage["HistoricalRawMissingPlayerIDRecordCount"],
            coverage["HistoricalRawNonPlayerAggregateRecordCount"],
            diagnostic,
        )
        self.assertEqual(0, coverage["HistoricalRawUnclassifiedMissingPlayerIDRecordCount"], diagnostic)
        self.assertEqual(
            coverage["CurrentRawMissingPlayerIDRecordCount"],
            coverage["CurrentRawNonPlayerAggregateRecordCount"],
            diagnostic,
        )
        self.assertEqual(0, coverage["CurrentRawUnclassifiedMissingPlayerIDRecordCount"], diagnostic)
        self.assertEqual([], coverage["RawUnclassifiedMissingPlayerIDExamples"], diagnostic)

    def test_justin_jefferson_keeps_one_canonical_identity_across_historical_week_one_stats(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        canonical_ids: set[str] = set()
        gsis_ids: set[str] = set()
        for season in range(2020, 2026):
            path = repo_root / f"source-data/nfl/player-stats/{season}/01.json"
            self.assertTrue(path.exists(), f"missing canonical Week 1 stats for {season}")
            payload = json.loads(path.read_text(encoding="utf-8"))
            matches = [record for record in payload.get("Records", []) if record.get("PlayerName") == "Justin Jefferson"]
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
