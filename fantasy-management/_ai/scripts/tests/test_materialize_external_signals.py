from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIRECTORY = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIRECTORY))

from materialize_external_signals import (  # noqa: E402
    ExternalSignalMaterializationError,
    build,
    canonical_json,
)


class ExternalSignalMaterializationTests(unittest.TestCase):
    def test_build_resolves_identity_ownership_views_and_changes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = self._write_fixture(root)
            data, quality = build(root, config_path)

            players = {player["player_id"]: player for player in data["players"]}
            self.assertEqual("mighty_giants", players["1"]["ownership"]["status"])
            self.assertEqual("opponent_rostered", players["4"]["ownership"]["status"])
            self.assertEqual("fantasy_free_agent", players["5"]["ownership"]["status"])
            self.assertEqual("unresolved", players["999"]["identity_status"])
            self.assertTrue(
                players["6"]["source_signals"]["sleeper-trending"]["changes"]["add"]["left_top_n"]
            )

            add_view = data["views"]["sleeper-trending"]["add"]
            self.assertEqual("QB One", add_view[0]["name"])
            self.assertEqual("mighty_giants", add_view[0]["ownership_status"])
            self.assertEqual(4, len(add_view))

            self.assertEqual("ok", quality["status"])
            sleeper_quality = quality["coverage"]["external_signals"]["sleeper-trending"]
            self.assertEqual(4, sleeper_quality["row_count"])
            self.assertFalse(sleeper_quality["baseline"])
            self.assertTrue(sleeper_quality["material_event_eligible"])

            data_again, quality_again = build(root, config_path)
            self.assertEqual(canonical_json(data), canonical_json(data_again))
            self.assertEqual(canonical_json(quality), canonical_json(quality_again))

    def test_duplicate_source_ids_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = self._write_fixture(root)
            catalog_path = root / "fantasy-management/_ai/operations-external-signal-catalog.json"
            catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
            catalog["sources"].append(dict(catalog["sources"][0]))
            self._write_json(catalog_path, catalog)
            with self.assertRaisesRegex(
                ExternalSignalMaterializationError,
                "Duplicate external signal source_id",
            ):
                build(root, config_path)

    def test_duplicate_player_ids_in_source_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = self._write_fixture(root)
            source_path = root / "signals/sleeper.json"
            source = json.loads(source_path.read_text(encoding="utf-8"))
            source["players"].append(dict(source["players"][0]))
            self._write_json(source_path, source)
            with self.assertRaisesRegex(
                ExternalSignalMaterializationError,
                "duplicate player identity 1",
            ):
                build(root, config_path)

    def _write_fixture(self, root: Path) -> Path:
        self._write_json(
            root / "public/data/League.json",
            {
                "Teams": [
                    {
                        "TeamID": 1,
                        "Team": "Mighty Giants",
                        "TeamAbbr": "MiG",
                        "Roster": ["1"],
                        "Reserve": [],
                        "Taxi": [],
                    },
                    {
                        "TeamID": 2,
                        "Team": "Opponent",
                        "TeamAbbr": "OPP",
                        "Roster": ["4"],
                        "Reserve": [],
                        "Taxi": [],
                    },
                ]
            },
        )
        self._write_json(
            root / "public/data/Players.json",
            [
                {"ID": "1", "Name": "QB One", "Position": "QB", "TeamAbbr": "AAA"},
                {"ID": "4", "Name": "WR Four", "Position": "WR", "TeamAbbr": "BBB"},
                {"ID": "5", "Name": "WR Five", "Position": "WR", "TeamAbbr": "CCC"},
            ],
        )
        self._write_json(
            root / "fantasy-management/generated/operations/data-quality.json",
            {
                "schema_version": 1,
                "report_id": "fantasy-operations-data-quality",
                "generated_at": "2026-08-06T10:00:00Z",
                "input_fingerprint": "a" * 64,
                "status": "ok",
                "coverage": {},
                "issues": [],
                "source_freshness": [],
                "interpretation_limits": [],
            },
        )
        self._write_json(
            root / "signals/sleeper.json",
            {
                "generated_at": "2026-08-06T12:00:00Z",
                "attribution": "Trending data provided by Sleeper",
                "players": [
                    self._signal_player("1", 1, 100),
                    self._signal_player("4", 2, 90),
                    self._signal_player("5", 3, 80),
                    self._signal_player("999", 4, 70),
                ],
                "comparison": {
                    "baseline": False,
                    "comparable": True,
                    "reason": "same_configuration_previous_snapshot_available",
                    "previous_generated_at": "2026-08-05T12:00:00Z",
                    "material_event_eligible": True,
                    "activity": {
                        "add": {
                            "entered_top_n": ["5", "999"],
                            "left_top_n": ["6"],
                            "rank_changed": [
                                {
                                    "sleeper_player_id": "1",
                                    "old_rank": 3,
                                    "new_rank": 1,
                                    "rank_delta": 2,
                                }
                            ],
                            "count_changed": [],
                        },
                        "drop": {
                            "entered_top_n": [],
                            "left_top_n": [],
                            "rank_changed": [],
                            "count_changed": [],
                        },
                    },
                },
            },
        )
        self._write_json(
            root / "fantasy-management/_ai/operations-external-signal-catalog.json",
            {
                "schema_version": 1,
                "catalog_id": "fantasy-operations-external-signal-catalog",
                "purpose": "fixture",
                "sources": [self._catalog_source()],
            },
        )
        config_path = root / "fantasy-management/automation/external-signal-materialization.json"
        self._write_json(
            config_path,
            {
                "schema_version": 1,
                "managed_team": {"identity_field": "TeamID", "team_id": 1},
                "sources": {
                    "league": "public/data/League.json",
                    "players": "public/data/Players.json",
                    "base_quality": "fantasy-management/generated/operations/data-quality.json",
                },
                "signal_catalog": "fantasy-management/_ai/operations-external-signal-catalog.json",
                "outputs": {
                    "external_signal_relevance": "fantasy-management/generated/operations/external-signal-relevance.json",
                    "data_quality": "fantasy-management/generated/operations/data-quality.json",
                },
            },
        )
        return config_path

    @staticmethod
    def _signal_player(player_id: str, rank: int, count: int) -> dict[str, object]:
        return {
            "sleeper_player_id": player_id,
            "add": {"status": "listed", "rank": rank, "count": count},
            "drop": {"status": "not_listed", "rank": None, "count": None},
        }

    @staticmethod
    def _catalog_source() -> dict[str, object]:
        return {
            "source_id": "sleeper-trending",
            "active": True,
            "provider": "sleeper",
            "dataset_id": "nfl-roster-activity-24h-top100",
            "location": "signals/sleeper.json",
            "rows_field": "players",
            "timestamp_fields": ["generated_at"],
            "source_player_id_field": "sleeper_player_id",
            "attribution_field": "attribution",
            "comparison_contract": "top_n_activity_v1",
            "signal_fields": [
                {"target": "add_status", "source_field": "add.status", "type": "text"},
                {"target": "add_rank", "source_field": "add.rank", "type": "number"},
                {"target": "add_count", "source_field": "add.count", "type": "number"},
                {"target": "drop_status", "source_field": "drop.status", "type": "text"},
                {"target": "drop_rank", "source_field": "drop.rank", "type": "number"},
                {"target": "drop_count", "source_field": "drop.count", "type": "number"},
            ],
            "unresolved_identity_severity": "info",
            "freshness": {"max_age_hours": 30},
            "interpretation": {},
        }

    @staticmethod
    def _write_json(path: Path, value: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
