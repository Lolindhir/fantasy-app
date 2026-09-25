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

            outputs, audit, preserved = _build_special_teams_fumble_events(
                root,
                dataset,
                canonical,
                2026,
                force=False,
            )

            self.assertEqual(0, preserved)
            self.assertEqual(1, len(outputs))
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
