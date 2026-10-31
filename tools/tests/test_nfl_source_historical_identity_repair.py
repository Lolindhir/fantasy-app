from __future__ import annotations

import csv
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from tools.nfl_source_data_lib.canonical_identity import identity_lookup
from tools.nfl_source_data_lib.common import CANONICAL_SCHEMA_VERSION, Dataset
from tools.nfl_source_data_lib.lifecycle import effective_partition_payload
from tools.nfl_source_data_lib.phase1 import _build_snap_counts


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
                approved_snap_pfr_bindings=frozenset({("WhitCo05", "NFLP-cody")}),
            )
            self.assertFalse(preserved)
            self.assertEqual(candidate, effective)
            # A second identical materialization is a frozen no-op.
            path.write_text(json.dumps(effective), encoding="utf-8")
            same, preserved = effective_partition_payload(
                dataset, path=path, candidate=candidate,
                partition_season=2024, observation_season=2026, force=False,
                approved_snap_pfr_bindings=frozenset({("WhitCo05", "NFLP-cody")}),
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
                        approved_snap_pfr_bindings=frozenset({("WhitCo05", "NFLP-cody")}),
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
                approved_snap_pfr_bindings=frozenset({("WhitCo05", "NFLP-cody")}),
            )
            self.assertTrue(preserved)
            self.assertEqual(assigned, effective)

    def test_frozen_snap_partition_limits_changes_to_confirmed_pfr_token(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "2024-01.json"
            dataset = replace(stats_dataset(root), id="nflverse.snap-counts", kind="weekly-snap-counts")
            existing = {
                "SchemaVersion": CANONICAL_SCHEMA_VERSION, "Season": 2024, "Week": 1,
                "SourceDataset": "nflverse.snap-counts", "Finalized": True,
                "Records": [
                    {"CanonicalPlayerID": None, "SourceIDs": {"PFR": "WhitCo05"}, "OffenseSnaps": 11},
                    {"CanonicalPlayerID": None, "SourceIDs": {"PFR": "Other01"}, "OffenseSnaps": 12},
                ],
            }
            candidate = json.loads(json.dumps(existing))
            candidate["Records"][0]["CanonicalPlayerID"] = "NFLP-cody"
            candidate["Records"][1]["CanonicalPlayerID"] = "NFLP-other"
            path.write_text(json.dumps(existing), encoding="utf-8")
            effective, preserved = effective_partition_payload(
                dataset, path=path, candidate=candidate,
                partition_season=2024, observation_season=2026, force=False,
                approved_snap_pfr_bindings=frozenset({("WhitCo05", "NFLP-cody")}),
            )
            self.assertFalse(preserved)
            self.assertEqual("NFLP-cody", effective["Records"][0]["CanonicalPlayerID"])
            self.assertIsNone(effective["Records"][1]["CanonicalPlayerID"])
            self.assertEqual(existing["Records"][1], effective["Records"][1])
            # Default fail-closed: without explicit adjudication there is no enrichment.
            effective, preserved = effective_partition_payload(
                dataset, path=path, candidate=candidate,
                partition_season=2024, observation_season=2026, force=False,
            )
            self.assertTrue(preserved)
            self.assertEqual(existing, effective)

    def test_real_snap_builder_replays_only_reviewed_frozen_pfr_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset = replace(
                stats_dataset(root), id="nflverse.snap-counts",
                kind="weekly-snap-counts", raw_path=root / "raw-{season}.csv",
            )
            with (root / "raw-2024.csv").open("w", encoding="utf-8", newline="") as handle:
                columns = [
                    "season", "game_id", "week", "pfr_player_id", "player", "position",
                    "team", "game_type", "offense_snaps", "offense_pct", "defense_snaps",
                    "defense_pct", "st_snaps", "st_pct",
                ]
                writer = csv.DictWriter(handle, fieldnames=columns)
                writer.writeheader()
                for token, name, snaps in [
                    ("WhitCo05", "Cody White", "11"),
                    ("Other01", "Other Player", "12"),
                ]:
                    writer.writerow({
                        "season": 2024, "game_id": "2024_01_LV_LAC", "week": 1,
                        "pfr_player_id": token, "player": name, "position": "WR",
                        "team": "LV", "game_type": "REG", "offense_snaps": snaps,
                        "offense_pct": "0.2", "defense_snaps": "0",
                        "defense_pct": "0", "st_snaps": "14", "st_pct": "0.3",
                    })
            canonical = [
                {"CanonicalPlayerID": "NFLP-cody", "IDs": {"PFR": "WhitCo05"}},
                {"CanonicalPlayerID": "NFLP-other", "IDs": {"PFR": "Other01"}},
            ]
            initial, _, _ = _build_snap_counts(
                root, dataset, canonical, 2026, force=True,
            )
            self.assertEqual(1, len(initial))
            path, source_payload = initial[0]
            existing = json.loads(json.dumps(source_payload))
            for row in existing["Records"]:
                row["CanonicalPlayerID"] = None
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(existing), encoding="utf-8")
            approved = frozenset({("WhitCo05", "NFLP-cody")})
            repaired, _, preserved = _build_snap_counts(
                root, dataset, canonical, 2026, force=False,
                approved_snap_pfr_bindings=approved,
            )
            self.assertEqual(0, preserved)
            expected = json.loads(json.dumps(existing))
            for row in expected["Records"]:
                if row["SourceIDs"]["PFR"] == "WhitCo05":
                    row["CanonicalPlayerID"] = "NFLP-cody"
            self.assertEqual(expected, repaired[0][1])
            # Re-running the exact materializer after publication must be a no-op.
            path.write_text(json.dumps(repaired[0][1]), encoding="utf-8")
            repeated, _, preserved = _build_snap_counts(
                root, dataset, canonical, 2026, force=False,
                approved_snap_pfr_bindings=approved,
            )
            self.assertEqual(1, preserved)
            self.assertEqual(expected, repeated[0][1])

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
