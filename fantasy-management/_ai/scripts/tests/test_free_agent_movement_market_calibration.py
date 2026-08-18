from __future__ import annotations

import csv
import importlib.util
import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
CALIBRATION_PATH = SCRIPT_DIR / "free_agent_movement_market_calibration.py"
BUILDER_PATH = SCRIPT_DIR / "build_free_agent_movement_dataset.py"

CALIBRATION_SPEC = importlib.util.spec_from_file_location(
    "free_agent_movement_market_calibration_test", CALIBRATION_PATH
)
CALIBRATION = importlib.util.module_from_spec(CALIBRATION_SPEC)
assert CALIBRATION_SPEC.loader is not None
CALIBRATION_SPEC.loader.exec_module(CALIBRATION)

BUILDER_SPEC = importlib.util.spec_from_file_location(
    "build_free_agent_movement_dataset_calendar_test", BUILDER_PATH
)
BUILDER = importlib.util.module_from_spec(BUILDER_SPEC)
sys.modules[BUILDER_SPEC.name] = BUILDER
assert BUILDER_SPEC.loader is not None
BUILDER_SPEC.loader.exec_module(BUILDER)


class FreeAgentMovementMarketCalibrationTests(unittest.TestCase):
    def config(self) -> dict:
        return {
            "authoritative_tier_source_id": "fantasypros",
            "fantasycalc": {
                "source_id": "fantasycalc",
                "percentile": {
                    "medium_absolute_delta_points": 10,
                    "high_absolute_delta_points": 15,
                },
                "value": {
                    "medium_absolute_delta": 250,
                    "medium_absolute_percent_change": 20,
                    "high_absolute_delta": 500,
                    "high_absolute_percent_change": 30,
                },
            },
        }

    def test_only_authoritative_source_gets_hard_tier_change(self) -> None:
        fantasycalc = CALIBRATION.materiality_crossings(
            config=self.config(),
            source_id="fantasycalc",
            window_days=1,
            percentile_delta=0,
            value_delta=0,
            value_percent_change=0,
            tier_changed=True,
            tier_from=10,
            tier_to=9,
        )
        fantasypros = CALIBRATION.materiality_crossings(
            config=self.config(),
            source_id="fantasypros",
            window_days=1,
            percentile_delta=0,
            value_delta=None,
            value_percent_change=None,
            tier_changed=True,
            tier_from=10,
            tier_to=9,
        )
        self.assertNotIn("tier_change", {item["kind"] for item in fantasycalc})
        self.assertIn("tier_change", {item["kind"] for item in fantasypros})

    def test_fantasycalc_percentile_bands_are_medium_and_high(self) -> None:
        medium = CALIBRATION.materiality_crossings(
            config=self.config(),
            source_id="fantasycalc",
            window_days=14,
            percentile_delta=12,
            value_delta=None,
            value_percent_change=None,
            tier_changed=False,
            tier_from=None,
            tier_to=None,
        )
        high = CALIBRATION.materiality_crossings(
            config=self.config(),
            source_id="fantasycalc",
            window_days=30,
            percentile_delta=-16,
            value_delta=None,
            value_percent_change=None,
            tier_changed=False,
            tier_from=None,
            tier_to=None,
        )
        self.assertEqual(medium[0]["kind"], "fantasycalc_percentile_movement")
        self.assertEqual(medium[0]["severity"], "medium")
        self.assertEqual(high[0]["severity"], "high")

    def test_fantasycalc_value_requires_absolute_and_relative_movement(self) -> None:
        percentage_only = CALIBRATION.materiality_crossings(
            config=self.config(),
            source_id="fantasycalc",
            window_days=7,
            percentile_delta=0,
            value_delta=100,
            value_percent_change=100,
            tier_changed=False,
            tier_from=None,
            tier_to=None,
        )
        medium = CALIBRATION.materiality_crossings(
            config=self.config(),
            source_id="fantasycalc",
            window_days=7,
            percentile_delta=0,
            value_delta=300,
            value_percent_change=25,
            tier_changed=False,
            tier_from=None,
            tier_to=None,
        )
        high = CALIBRATION.materiality_crossings(
            config=self.config(),
            source_id="fantasycalc",
            window_days=30,
            percentile_delta=0,
            value_delta=-550,
            value_percent_change=-35,
            tier_changed=False,
            tier_from=None,
            tier_to=None,
        )
        self.assertNotIn("fantasycalc_value_movement", {item["kind"] for item in percentage_only})
        medium_value = next(item for item in medium if item["kind"] == "fantasycalc_value_movement")
        high_value = next(item for item in high if item["kind"] == "fantasycalc_value_movement")
        self.assertEqual(medium_value["severity"], "medium")
        self.assertEqual(high_value["severity"], "high")

    def test_history_windows_are_anchored_to_evaluation_date(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_id = "calendar-source"
            source_root = root / "sources" / source_id
            current_relative = f"sources/{source_id}/snapshots/2026-08-16/ranking.csv"
            earlier_relative = f"sources/{source_id}/snapshots/2026-08-15/ranking.csv"
            for relative, percentile in ((current_relative, 60), (earlier_relative, 50)):
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("w", encoding="utf-8", newline="") as handle:
                    writer = csv.DictWriter(handle, fieldnames=["player_id", "percentile"])
                    writer.writeheader()
                    writer.writerow({"player_id": "p1", "percentile": percentile})
            (source_root / "latest.json").write_text(
                json.dumps(
                    {
                        "snapshot_date": "2026-08-16",
                        "ranking_fetched_at": "2026-08-16T05:00:00Z",
                        "ranking_file": current_relative,
                    }
                ),
                encoding="utf-8",
            )
            definition = {
                "source_id": source_id,
                "active": True,
                "source_kind": "market_value",
                "provider": source_id,
                "dataset_id": source_id,
                "access": {
                    "type": "repo_latest_pointer",
                    "location": f"sources/{source_id}/latest.json",
                    "ranking_path_field": "ranking_file",
                    "timestamp_fields": ["ranking_fetched_at", "snapshot_date"],
                },
                "applicability": {"entity_types": ["player"], "positions": ["WR"]},
                "absence_policy": {
                    "inapplicable": "not_applicable",
                    "missing": "not_listed",
                    "ambiguous": "ambiguous_join",
                },
                "join": {
                    "strategies": [
                        {
                            "type": "id",
                            "method": "player_id",
                            "player_field": "ID",
                            "source_field": "player_id",
                        }
                    ]
                },
                "output": {
                    "section": "market",
                    "key": source_id,
                    "signals": [
                        {
                            "target": "percentile",
                            "source_field": "percentile",
                            "type": "number",
                        }
                    ],
                },
                "roles": {},
                "quality": {
                    "minimum_rows": 1,
                    "missing_severity": "none",
                    "ambiguous_severity": "warning",
                    "row_count_severity": "error",
                },
                "freshness": {"max_age_hours": 72},
                "format_context": {},
            }
            history = BUILDER._build_source_history(
                root,
                definition,
                [1, 3],
                date(2026, 8, 18),
            )
            self.assertEqual(history.current_snapshot_date.isoformat(), "2026-08-16")
            self.assertEqual(history.baseline_dates[1], "2026-08-16")
            self.assertEqual(history.baseline_dates[3], "2026-08-15")


if __name__ == "__main__":
    unittest.main()
