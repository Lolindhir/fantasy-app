from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIRECTORY = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIRECTORY))

from build_fantasy_operations_inputs import (  # noqa: E402
    build,
    canonical_json,
    derive_injury_signal,
    normalize_name,
)


class FantasyOperationsInputsTests(unittest.TestCase):
    def test_name_normalization_removes_suffix_and_punctuation(self) -> None:
        self.assertEqual("marvinharrison", normalize_name("Marvin Harrison Jr."))
        self.assertEqual("jamarrchase", normalize_name("Ja'Marr Chase"))

    def test_injury_signal_requires_external_verification(self) -> None:
        player = {
            "Injured": True,
            "InjuryDetails": {
                "Description": "Aug 5: limited with a hamstring issue.",
                "Designation": "Questionable",
                "ReturnDate": "20260812",
                "Date": "",
            },
        }
        signal = derive_injury_signal(player)
        self.assertEqual("current_injury_signal", signal["coverage_status"])
        self.assertEqual("high", signal["external_verification_priority"])

    def test_build_deduplicates_roster_sections_and_joins_sources(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_fixture(root)
            config_path = (
                root / "fantasy-management/automation/input-materialization.json"
            )
            data, quality = build(root, config_path)

            self.assertEqual(2, data["managed_team"]["player_count"])
            first = next(
                player for player in data["players"] if player["player_id"] == "1"
            )
            self.assertEqual(["reserve", "roster"], first["roster_sections"])
            self.assertTrue(first["market"]["fantasycalc"]["listed"])
            self.assertEqual(
                "sleeper_id",
                first["market"]["fantasycalc"]["join_method"],
            )
            self.assertEqual(
                "two_qb_10_team",
                first["redraft_adp"]["primary_format"],
            )
            self.assertEqual("warning", quality["status"])

            data_again, _ = build(root, config_path)
            self.assertEqual(canonical_json(data), canonical_json(data_again))

    def _write_fixture(self, root: Path) -> None:
        paths = [
            "public/data",
            "fantasy-management/automation",
            "sources/fp",
            "sources/fc",
            "sources/ppr",
            "sources/two",
        ]
        for path in paths:
            (root / path).mkdir(parents=True, exist_ok=True)

        config = {
            "schema_version": 1,
            "managed_team": {"identity_field": "TeamID", "team_id": 1},
            "sources": {
                "league": "public/data/League.json",
                "players": "public/data/Players.json",
                "timestamps": "public/data/Timestamps.json",
                "fantasypros_latest": "sources/fp/latest.json",
                "fantasycalc_latest": "sources/fc/latest.json",
                "adp_ppr_latest": "sources/ppr/latest.json",
                "adp_two_qb_latest": "sources/two/latest.json",
            },
            "outputs": {
                "managed_roster_signals": "generated/signals.json",
                "data_quality": "generated/quality.json",
            },
        }
        self._write_json(
            root / "fantasy-management/automation/input-materialization.json",
            config,
        )
        self._write_json(
            root / "public/data/League.json",
            {
                "Teams": [
                    {
                        "TeamID": 1,
                        "Team": "Test Team",
                        "TeamAbbr": "TST",
                        "Roster": ["1", "2"],
                        "Reserve": ["1"],
                        "Taxi": [],
                        "Starter": ["1"],
                    }
                ]
            },
        )
        self._write_json(
            root / "public/data/Players.json",
            [
                {
                    "ID": "1",
                    "Name": "Quarter Back Jr.",
                    "Position": "QB",
                    "TeamAbbr": "AAA",
                    "Injured": True,
                    "InjuryDetails": {
                        "Description": "limited",
                        "Designation": "Questionable",
                        "ReturnDate": "",
                        "Date": "",
                    },
                },
                {
                    "ID": "2",
                    "Name": "Wide Receiver",
                    "Position": "WR",
                    "TeamAbbr": "BBB",
                    "Injured": False,
                    "InjuryDetails": {
                        "Description": "",
                        "Designation": "",
                        "ReturnDate": "",
                        "Date": "",
                    },
                },
            ],
        )
        self._write_json(
            root / "public/data/Timestamps.json",
            {
                "Players": "2026-08-05T19:15:26Z",
                "League": "2026-08-05T18:00:00Z",
            },
        )

        self._write_csv(
            root / "sources/fp/ranking.csv",
            [
                {
                    "name": "Quarter Back",
                    "Rank": "10",
                    "position": "QB",
                    "team": "AAA",
                    "position_rank": "QB5",
                    "tier": "2",
                },
                {
                    "name": "Wide Receiver",
                    "Rank": "20",
                    "position": "WR",
                    "team": "BBB",
                    "position_rank": "WR10",
                    "tier": "3",
                },
            ],
        )
        self._write_csv(
            root / "sources/fc/ranking.csv",
            [
                {
                    "name": "Quarter Back",
                    "Rank": "9",
                    "position": "QB",
                    "team": "AAA",
                    "position_rank": "4",
                    "tier": "2",
                    "value": "5000",
                    "trend_30_day": "100",
                    "roster_percent": "0.99",
                    "trade_frequency": "0.01",
                    "sleeper_id": "1",
                },
                {
                    "name": "Wide Receiver",
                    "Rank": "22",
                    "position": "WR",
                    "team": "BBB",
                    "position_rank": "11",
                    "tier": "3",
                    "value": "3500",
                    "trend_30_day": "-20",
                    "roster_percent": "0.95",
                    "trade_frequency": "0.02",
                    "sleeper_id": "2",
                },
            ],
        )
        self._write_csv(
            root / "sources/ppr/ranking.csv",
            [
                {
                    "name": "Wide Receiver",
                    "Rank": "2",
                    "position": "WR",
                    "team": "BBB",
                    "adp": "12.3",
                    "times_drafted": "120",
                    "stdev": "2.1",
                    "sample_total_drafts": "1000",
                    "sample_start_date": "2026-08-01",
                    "sample_end_date": "2026-08-05",
                }
            ],
        )
        self._write_csv(
            root / "sources/two/ranking.csv",
            [
                {
                    "name": "Quarter Back",
                    "Rank": "1",
                    "position": "QB",
                    "team": "AAA",
                    "adp": "2.1",
                    "times_drafted": "200",
                    "stdev": "1.1",
                    "sample_total_drafts": "900",
                    "sample_start_date": "2026-08-01",
                    "sample_end_date": "2026-08-05",
                }
            ],
        )
        for source in ("fp", "fc", "ppr", "two"):
            self._write_json(
                root / f"sources/{source}/latest.json",
                {
                    "ranking_file": f"sources/{source}/ranking.csv",
                    "snapshot_date": "2026-08-05",
                    "ranking_fetched_at": "2026-08-05T08:00:00Z",
                },
            )

    @staticmethod
    def _write_json(path: Path, value: object) -> None:
        path.write_text(json.dumps(value), encoding="utf-8")

    @staticmethod
    def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
        fieldnames = sorted({key for row in rows for key in row})
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)


if __name__ == "__main__":
    unittest.main()
