from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from tools.nfl_source_data_lib.canonical_identity import identity_lookup
from tools.nfl_source_data_lib.common import CANONICAL_SCHEMA_VERSION, Dataset
from tools.nfl_source_data_lib.lifecycle import effective_partition_payload


def stats_dataset(root: Path) -> Dataset:
    return Dataset(
        id="nflverse.player-stats",
        provider="nflverse",
        upstream="test",
        source_url="https://example.invalid/raw-{season}.csv",
        raw_path=root / "raw-{season}.csv",
        metadata_path=root / "metadata-{season}.json",
        required_columns=(),
        minimum_rows=1,
        kind="weekly-player-stats",
        refresh_policy="current-season",
        retention_policy="permanent-by-season",
        license="test",
        attribution="test",
        lifecycle_class="seasonal-finalizable",
        partition_key="season-week",
        finalization_policy="freeze-prior-seasons",
        repair_policy="explicit-force",
        source_mode="season-partitioned",
    )


class HistoricalIdentityRepairTests(unittest.TestCase):
    def payload(self, canonical_player_id: str | None, yards: int = 10) -> dict[str, object]:
        return {
            "SchemaVersion": CANONICAL_SCHEMA_VERSION,
            "Season": 1999,
            "Week": 1,
            "SourceDataset": "nflverse.player-stats",
            "Finalized": True,
            "Records": [
                {
                    "CanonicalPlayerID": canonical_player_id,
                    "SourceIDs": {"GSIS": "00-0005532"},
                    "PlayerName": "Fixture",
                    "Stats": {"receiving_yards": yards},
                }
            ],
        }

    def test_frozen_stats_allow_only_null_to_identity_enrichment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "1999.json"
            existing = self.payload(None)
            candidate = self.payload("NFLP-1")
            path.write_text(json.dumps(existing), encoding="utf-8")
            effective, preserved = effective_partition_payload(
                stats_dataset(root),
                path=path,
                candidate=candidate,
                partition_season=1999,
                observation_season=2026,
                force=False,
            )
            self.assertFalse(preserved)
            self.assertEqual(candidate, effective)

    def test_frozen_stats_reject_identity_enrichment_when_fact_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "1999.json"
            existing = self.payload(None, yards=10)
            candidate = self.payload("NFLP-1", yards=11)
            path.write_text(json.dumps(existing), encoding="utf-8")
            effective, preserved = effective_partition_payload(
                stats_dataset(root),
                path=path,
                candidate=candidate,
                partition_season=1999,
                observation_season=2026,
                force=False,
            )
            self.assertTrue(preserved)
            self.assertEqual(existing, effective)

    def test_frozen_stats_never_replace_existing_nonnull_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "1999.json"
            existing = self.payload("NFLP-1")
            candidate = self.payload("NFLP-2")
            path.write_text(json.dumps(existing), encoding="utf-8")
            effective, preserved = effective_partition_payload(
                stats_dataset(root),
                path=path,
                candidate=candidate,
                partition_season=1999,
                observation_season=2026,
                force=False,
            )
            self.assertTrue(preserved)
            self.assertEqual(existing, effective)

    def test_frozen_snap_counts_allow_identity_only_enrichment_and_replay(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "2024-01.json"
            dataset = replace(stats_dataset(root), id="nflverse.snap-counts", kind="weekly-snap-counts")
            existing = {
                "SchemaVersion": CANONICAL_SCHEMA_VERSION,
                "Season": 2024,
                "Week": 1,
                "SourceDataset": "nflverse.snap-counts",
                "Finalized": True,
                "Records": [
                    {
                        "CanonicalPlayerID": None,
                        "SourceIDs": {"PFR": "WhitCo05"},
                        "GameID": "2024_01_LV_LAC",
                        "OffenseSnaps": 11,
                        "SpecialTeamsSnaps": 14,
                    },
                    {
                        "CanonicalPlayerID": "NFLP-already",
                        "SourceIDs": {"PFR": "Other01"},
                        "GameID": "2024_01_LV_LAC",
                        "OffenseSnaps": 55,
                        "SpecialTeamsSnaps": 0,
                    },
                ],
            }
            candidate = json.loads(json.dumps(existing))
            candidate["Records"][0]["CanonicalPlayerID"] = "NFLP-cody"
            path.write_text(json.dumps(existing), encoding="utf-8")
            effective, preserved = effective_partition_payload(
                dataset, path=path, candidate=candidate,
                partition_season=2024, observation_season=2026, force=False,
            )
            self.assertFalse(preserved)
            self.assertEqual(candidate, effective)
            # A second identical materialization is a frozen no-op.
            path.write_text(json.dumps(effective), encoding="utf-8")
            same, preserved = effective_partition_payload(
                dataset, path=path, candidate=candidate,
                partition_season=2024, observation_season=2026, force=False,
            )
            self.assertTrue(preserved)
            self.assertEqual(candidate, same)

    def test_frozen_snap_counts_reject_semantic_changes_and_identity_reassignment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "2024-01.json"
            dataset = replace(stats_dataset(root), id="nflverse.snap-counts", kind="weekly-snap-counts")
            existing = {
                "SchemaVersion": CANONICAL_SCHEMA_VERSION,
                "Season": 2024,
                "Week": 1,
                "SourceDataset": "nflverse.snap-counts",
                "Finalized": True,
                "Records": [{
                    "CanonicalPlayerID": None,
                    "SourceIDs": {"PFR": "WhitCo05"},
                    "GameID": "2024_01_LV_LAC",
                    "OffenseSnaps": 11,
                    "SpecialTeamsSnaps": 14,
                }],
            }
            path.write_text(json.dumps(existing), encoding="utf-8")
            changes = [
                {"OffenseSnaps": 12},
                {"SpecialTeamsSnaps": 15},
                {"SourceIDs": {"PFR": "Other01"}},
                {"GameID": "2024_02_LV_LAC"},
            ]
            for mutation in changes:
                with self.subTest(mutation=mutation):
                    candidate = json.loads(json.dumps(existing))
                    candidate["Records"][0].update(mutation)
                    candidate["Records"][0]["CanonicalPlayerID"] = "NFLP-cody"
                    effective, preserved = effective_partition_payload(
                        dataset, path=path, candidate=candidate,
                        partition_season=2024, observation_season=2026, force=False,
                    )
                    self.assertTrue(preserved)
                    self.assertEqual(existing, effective)

            assigned = json.loads(json.dumps(existing))
            assigned["Records"][0]["CanonicalPlayerID"] = "NFLP-already"
            path.write_text(json.dumps(assigned), encoding="utf-8")
            candidate = json.loads(json.dumps(assigned))
            candidate["Records"][0]["CanonicalPlayerID"] = "NFLP-cody"
            effective, preserved = effective_partition_payload(
                dataset, path=path, candidate=candidate,
                partition_season=2024, observation_season=2026, force=False,
            )
            self.assertTrue(preserved)
            self.assertEqual(assigned, effective)

    def test_verified_legacy_stat_alias_resolves_through_existing_provider_bridge(self) -> None:
        canonical = [
            {
                "CanonicalPlayerID": "NFLP-fernando",
                "IDs": {"PFR": "SmitFe20"},
                "IDAliases": {},
            }
        ]
        lookup = identity_lookup(canonical)
        self.assertEqual("NFLP-fernando", lookup[("PFR", "SmitFe20")])
        self.assertEqual("NFLP-fernando", lookup[("GSIS", "XX-0000001")])


if __name__ == "__main__":
    unittest.main()
