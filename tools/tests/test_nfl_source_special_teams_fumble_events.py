from __future__ import annotations

import csv
import gzip
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.nfl_source_data_lib import common as common_mod
from tools.nfl_source_data_lib.phase1 import _build_special_teams_fumble_events
from tools.nfl_source_data_lib.source_projection import (
    SPECIAL_TEAMS_FUMBLE_FIELDS,
    SPECIAL_TEAMS_FUMBLE_PROJECTION_ID,
    SPECIAL_TEAMS_FUMBLE_PROJECTION_VERSION,
    project_special_teams_fumble_events,
)


def write_pbp_gzip(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(SPECIAL_TEAMS_FUMBLE_FIELDS))
        writer.writeheader()
        writer.writerows(rows)


def projected_dataset(root: Path) -> common_mod.Dataset:
    return common_mod.Dataset(
        id="nflverse.special-teams-fumble-events",
        provider="nflverse",
        upstream="nflverse/nflverse-data",
        source_url="https://example.invalid/play_by_play_{season}.csv.gz",
        raw_path=root / "source-data/providers/nflverse/special-teams-fumble-events/raw-{season}.json",
        metadata_path=root / "source-data/providers/nflverse/special-teams-fumble-events/metadata-{season}.json",
        required_columns=tuple(SPECIAL_TEAMS_FUMBLE_FIELDS),
        minimum_rows=0,
        kind="special-teams-fumble-event-evidence",
        refresh_policy="current-season",
        retention_policy="permanent-by-season",
        license="test",
        attribution="test",
        lifecycle_class="seasonal-finalizable",
        partition_key="season-week",
        finalization_policy="freeze-prior-seasons",
        repair_policy="explicit-force",
        source_mode="season-partitioned",
        source_format="json",
        availability_policy="current-season-may-be-unavailable",
        materialize=True,
        source_projection_id=SPECIAL_TEAMS_FUMBLE_PROJECTION_ID,
        source_projection_version=SPECIAL_TEAMS_FUMBLE_PROJECTION_VERSION,
        upstream_format="csv.gz",
    )


def base_row(**overrides: str) -> dict[str, str]:
    row = {field: "" for field in SPECIAL_TEAMS_FUMBLE_FIELDS}
    row.update(
        {
            "season": "2025",
            "season_type": "REG",
            "week": "7",
            "game_id": "2025_07_AAA_BBB",
            "play_id": "1234",
            "play_type": "punt",
            "special": "1",
            "home_team": "BBB",
            "away_team": "AAA",
        }
    )
    row.update(overrides)
    return row


def write_game_finality(root: Path, weeks: list[int], *, season: int = 2025) -> None:
    path = root / "source-data/nfl/game-finality" / f"{season}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "SchemaVersion": 2,
                "Season": season,
                "SourceDataset": "nflverse.game-finality",
                "Finalized": True,
                "Weeks": [
                    {
                        "GameType": "REG",
                        "Week": week,
                        "ApplicableGameCount": 1,
                        "FinalGameCount": 1,
                        "WeekFinal": True,
                    }
                    for week in weeks
                ],
            }
        ),
        encoding="utf-8",
    )


class SpecialTeamsFumbleRegistryTests(unittest.TestCase):
    def test_registry_loads_versioned_projected_source_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry_path = root / "source-data/registry.json"
            registry_path.parent.mkdir(parents=True, exist_ok=True)
            registry_path.write_text(
                json.dumps(
                    {
                        "schemaVersion": 3,
                        "datasets": [
                            {
                                "id": "nflverse.special-teams-fumble-events",
                                "provider": "nflverse",
                                "upstream": "nflverse/nflverse-data",
                                "sourceMode": "season-partitioned",
                                "sourceUrl": "https://example.invalid/play_by_play_{season}.csv.gz",
                                "sourceFormat": "json",
                                "sourceProjection": {
                                    "id": SPECIAL_TEAMS_FUMBLE_PROJECTION_ID,
                                    "version": SPECIAL_TEAMS_FUMBLE_PROJECTION_VERSION,
                                    "upstreamFormat": "csv.gz",
                                },
                                "rawPath": "providers/nflverse/special-teams-fumble-events/raw-{season}.json",
                                "metadataPath": "providers/nflverse/special-teams-fumble-events/metadata-{season}.json",
                                "requiredColumns": list(SPECIAL_TEAMS_FUMBLE_FIELDS),
                                "minimumRows": 0,
                                "availabilityPolicy": "current-season-may-be-unavailable",
                                "materialize": True,
                                "kind": "special-teams-fumble-event-evidence",
                                "refreshPolicy": "current-season",
                                "retentionPolicy": "permanent-by-season",
                                "lifecycle": {
                                    "class": "seasonal-finalizable",
                                    "partitionKey": "season-week",
                                    "finalization": "freeze-prior-seasons",
                                    "repairPolicy": "explicit-force",
                                },
                                "license": "test",
                                "attribution": "test",
                            }
                        ],
                        "plannedDatasets": [],
                    }
                ),
                encoding="utf-8",
            )

            datasets = common_mod.load_registry(root)

            self.assertEqual(1, len(datasets))
            dataset = datasets[0]
            self.assertEqual(SPECIAL_TEAMS_FUMBLE_PROJECTION_ID, dataset.source_projection_id)
            self.assertEqual(SPECIAL_TEAMS_FUMBLE_PROJECTION_VERSION, dataset.source_projection_version)
            self.assertEqual("csv.gz", dataset.upstream_format)
            self.assertEqual("json", dataset.source_format)

    def test_registry_rejects_unknown_projection_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry_path = root / "source-data/registry.json"
            registry_path.parent.mkdir(parents=True, exist_ok=True)
            registry_path.write_text(
                json.dumps(
                    {
                        "schemaVersion": 3,
                        "datasets": [
                            {
                                "id": "nflverse.special-teams-fumble-events",
                                "provider": "nflverse",
                                "upstream": "nflverse/nflverse-data",
                                "sourceMode": "season-partitioned",
                                "sourceUrl": "https://example.invalid/play_by_play_{season}.csv.gz",
                                "sourceFormat": "json",
                                "sourceProjection": {
                                    "id": SPECIAL_TEAMS_FUMBLE_PROJECTION_ID,
                                    "version": 999,
                                    "upstreamFormat": "csv.gz",
                                },
                                "rawPath": "providers/nflverse/special-teams-fumble-events/raw-{season}.json",
                                "metadataPath": "providers/nflverse/special-teams-fumble-events/metadata-{season}.json",
                                "requiredColumns": list(SPECIAL_TEAMS_FUMBLE_FIELDS),
                                "minimumRows": 0,
                                "availabilityPolicy": "current-season-may-be-unavailable",
                                "materialize": True,
                                "kind": "special-teams-fumble-event-evidence",
                                "refreshPolicy": "current-season",
                                "retentionPolicy": "permanent-by-season",
                                "lifecycle": {
                                    "class": "seasonal-finalizable",
                                    "partitionKey": "season-week",
                                    "finalization": "freeze-prior-seasons",
                                    "repairPolicy": "explicit-force",
                                },
                                "license": "test",
                                "attribution": "test",
                            }
                        ],
                        "plannedDatasets": [],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "unsupported sourceProjection"):
                common_mod.load_registry(root)


class SpecialTeamsFumbleProjectionTests(unittest.TestCase):
    def test_projection_keeps_only_special_teams_fumble_event_plays(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "pbp.csv.gz"
            output = root / "projected.json"
            rows = [
                base_row(
                    forced_fumble_player_1_team="AAA",
                    forced_fumble_player_1_player_id="00-1",
                    fumble_recovery_1_team="AAA",
                    fumble_recovery_1_player_id="00-2",
                    fumbled_1_team="BBB",
                ),
                base_row(
                    play_id="1235",
                    play_type="pass",
                    special="0",
                    forced_fumble_player_1_team="AAA",
                    forced_fumble_player_1_player_id="00-3",
                ),
                base_row(play_id="1236", play_type="kickoff"),
            ]
            write_pbp_gzip(source, rows)

            stats = project_special_teams_fumble_events(source, output)
            payload = json.loads(output.read_text(encoding="utf-8"))

            self.assertEqual(3, stats["sourceRowCount"])
            self.assertEqual(2, stats["specialTeamsRowCount"])
            self.assertEqual(1, stats["projectedRowCount"])
            self.assertEqual(1, len(payload["Records"]))
            self.assertEqual("00-1", payload["Records"][0]["forced_fumble_player_1_player_id"])
            self.assertEqual(
                SPECIAL_TEAMS_FUMBLE_PROJECTION_ID,
                payload["Projection"]["ID"],
            )

    def test_projection_rejects_special_flag_on_non_special_play_type(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "pbp.csv.gz"
            output = root / "projected.json"
            write_pbp_gzip(
                source,
                [
                    base_row(
                        play_type="pass",
                        forced_fumble_player_1_player_id="00-1",
                        forced_fumble_player_1_team="AAA",
                    )
                ],
            )
            with self.assertRaisesRegex(ValueError, "unsupported play_type"):
                project_special_teams_fumble_events(source, output)

    def test_projected_sync_persists_projection_provenance_and_freezes_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            upstream = root / "upstream.csv.gz"
            write_pbp_gzip(
                upstream,
                [
                    base_row(
                        forced_fumble_player_1_team="AAA",
                        forced_fumble_player_1_player_id="00-1",
                    )
                ],
            )
            dataset = projected_dataset(root)

            def fake_download(_url: str, target: Path) -> None:
                shutil.copyfile(upstream, target)

            with patch.object(common_mod, "download", side_effect=fake_download) as mocked:
                result = common_mod.sync_dataset(
                    dataset,
                    season=2025,
                    current_season=2026,
                )
            self.assertEqual("updated", result["status"])
            self.assertEqual(1, result["rowCount"])
            self.assertEqual(1, mocked.call_count)

            metadata = json.loads(dataset.metadata_path_for(2025).read_text(encoding="utf-8"))
            self.assertEqual(
                SPECIAL_TEAMS_FUMBLE_PROJECTION_ID,
                metadata["sourceProjection"]["id"],
            )
            self.assertEqual(1, metadata["projectionStats"]["projectedRowCount"])
            self.assertGreater(metadata["upstreamByteSize"], 0)
            self.assertEqual(64, len(metadata["upstreamContentHashSha256"]))

            with patch.object(common_mod, "download", side_effect=AssertionError("history should freeze")):
                frozen = common_mod.sync_dataset(
                    dataset,
                    season=2025,
                    current_season=2026,
                )
            self.assertEqual("frozen-existing", frozen["status"])


class SpecialTeamsFumbleCanonicalTests(unittest.TestCase):
    def test_materializer_emits_forced_fumble_and_recovery_and_dedupes_slots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset = projected_dataset(root)
            raw = dataset.raw_path_for(2025)
            raw.parent.mkdir(parents=True, exist_ok=True)
            raw.write_text(
                json.dumps(
                    {
                        "SchemaVersion": 1,
                        "Projection": {
                            "ID": SPECIAL_TEAMS_FUMBLE_PROJECTION_ID,
                            "Version": SPECIAL_TEAMS_FUMBLE_PROJECTION_VERSION,
                        },
                        "Columns": list(SPECIAL_TEAMS_FUMBLE_FIELDS),
                        "Records": [
                            base_row(
                                forced_fumble_player_1_team="AAA",
                                forced_fumble_player_1_player_id="00-1",
                                forced_fumble_player_2_team="AAA",
                                forced_fumble_player_2_player_id="00-1",
                                fumble_recovery_1_team="AAA",
                                fumble_recovery_1_player_id="00-2",
                                fumbled_1_team="BBB",
                            )
                        ],
                    }
                ),
                encoding="utf-8",
            )
            canonical = [
                {"CanonicalPlayerID": "NFLP-1", "IDs": {"GSIS": "00-1"}},
                {"CanonicalPlayerID": "NFLP-2", "IDs": {"GSIS": "00-2"}},
            ]
            write_game_finality(root, [7])

            outputs, audit, preserved = _build_special_teams_fumble_events(
                root,
                dataset,
                canonical,
                2026,
                force=False,
            )

            self.assertEqual(0, preserved)
            self.assertEqual(1, len(outputs))
            self.assertEqual(0, audit["emptyFinalizedPartitionCount"])
            self.assertEqual(2, audit["eventCount"])
            self.assertEqual(1, audit["equivalentDuplicateEventCount"])
            records = outputs[0][1]["Records"]
            forced = next(row for row in records if row["EventType"] == "forced-fumble")
            recovery = next(row for row in records if row["EventType"] == "fumble-recovery")
            self.assertEqual("NFLP-1", forced["CanonicalPlayerID"])
            self.assertEqual("NFLP-2", recovery["CanonicalPlayerID"])
            self.assertEqual(["BBB"], recovery["FumbledTeams"])
            self.assertTrue(recovery["SpecialTeams"])
            self.assertTrue(outputs[0][1]["Finalized"])

    def test_finalized_historical_week_without_events_emits_empty_partition(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset = projected_dataset(root)
            raw = dataset.raw_path_for(2025)
            raw.parent.mkdir(parents=True, exist_ok=True)
            raw.write_text(
                json.dumps(
                    {
                        "SchemaVersion": 1,
                        "Projection": {
                            "ID": SPECIAL_TEAMS_FUMBLE_PROJECTION_ID,
                            "Version": SPECIAL_TEAMS_FUMBLE_PROJECTION_VERSION,
                        },
                        "Columns": list(SPECIAL_TEAMS_FUMBLE_FIELDS),
                        "Records": [
                            base_row(
                                forced_fumble_player_1_team="AAA",
                                forced_fumble_player_1_player_id="00-1",
                            )
                        ],
                    }
                ),
                encoding="utf-8",
            )
            canonical = [{"CanonicalPlayerID": "NFLP-1", "IDs": {"GSIS": "00-1"}}]
            write_game_finality(root, [7, 8])

            outputs, audit, preserved = _build_special_teams_fumble_events(
                root,
                dataset,
                canonical,
                2026,
                force=False,
            )

            self.assertEqual(0, preserved)
            self.assertEqual(2, len(outputs))
            self.assertEqual(1, audit["eventCount"])
            self.assertEqual(1, audit["emptyFinalizedPartitionCount"])
            by_week = {payload["Week"]: (path, payload) for path, payload in outputs}
            empty_path, empty_payload = by_week[8]
            self.assertEqual(
                root / "source-data/nfl/special-teams-fumble-events/2025/08.json",
                empty_path,
            )
            self.assertTrue(empty_payload["Finalized"])
            self.assertEqual([], empty_payload["Records"])

    def test_conflicting_duplicate_event_identity_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset = projected_dataset(root)
            raw = dataset.raw_path_for(2025)
            raw.parent.mkdir(parents=True, exist_ok=True)
            raw.write_text(
                json.dumps(
                    {
                        "SchemaVersion": 1,
                        "Projection": {
                            "ID": SPECIAL_TEAMS_FUMBLE_PROJECTION_ID,
                            "Version": SPECIAL_TEAMS_FUMBLE_PROJECTION_VERSION,
                        },
                        "Columns": list(SPECIAL_TEAMS_FUMBLE_FIELDS),
                        "Records": [
                            base_row(
                                forced_fumble_player_1_team="AAA",
                                forced_fumble_player_1_player_id="00-1",
                                forced_fumble_player_2_team="BBB",
                                forced_fumble_player_2_player_id="00-1",
                            )
                        ],
                    }
                ),
                encoding="utf-8",
            )
            canonical = [{"CanonicalPlayerID": "NFLP-1", "IDs": {"GSIS": "00-1"}}]

            with self.assertRaisesRegex(ValueError, "Conflicting duplicate"):
                _build_special_teams_fumble_events(
                    root,
                    dataset,
                    canonical,
                    2026,
                    force=False,
                )

    def test_unresolved_historical_event_identity_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset = projected_dataset(root)
            raw = dataset.raw_path_for(2025)
            raw.parent.mkdir(parents=True, exist_ok=True)
            raw.write_text(
                json.dumps(
                    {
                        "SchemaVersion": 1,
                        "Projection": {
                            "ID": SPECIAL_TEAMS_FUMBLE_PROJECTION_ID,
                            "Version": SPECIAL_TEAMS_FUMBLE_PROJECTION_VERSION,
                        },
                        "Columns": list(SPECIAL_TEAMS_FUMBLE_FIELDS),
                        "Records": [
                            base_row(
                                forced_fumble_player_1_team="AAA",
                                forced_fumble_player_1_player_id="00-unresolved",
                            )
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "historical event cannot resolve GSIS"):
                _build_special_teams_fumble_events(
                    root,
                    dataset,
                    [],
                    2026,
                    force=False,
                )


if __name__ == "__main__":
    unittest.main()
