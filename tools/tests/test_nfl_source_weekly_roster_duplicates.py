import csv
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

from nfl_source_data_lib.common import Dataset
from nfl_source_data_lib.phase1 import build_phase1_outputs


CANONICAL = [{
    "CanonicalPlayerID": "NFLP-shaun-phillips",
    "IDs": {"GSIS": "00-0022723"},
    "IDAliases": {},
}]


def weekly_dataset(root: Path) -> Dataset:
    return Dataset(
        id="nflverse.weekly-rosters",
        provider="nflverse",
        upstream="test",
        source_url="https://example.invalid/roster_weekly_{season}.csv",
        raw_path=root / "raw-{season}.csv",
        metadata_path=root / "metadata-{season}.json",
        required_columns=("season", "week", "team", "gsis_id"),
        minimum_rows=1,
        kind="weekly-rosters",
        refresh_policy="current-season",
        retention_policy="permanent-by-season",
        license="test",
        attribution="test",
        lifecycle_class="seasonal-finalizable",
        partition_key="season-week",
        finalization_policy="freeze-prior-seasons",
        repair_policy="explicit-force",
        source_mode="season-partitioned",
        source_format="csv",
        availability_policy="current-season-may-be-unavailable",
        materialize=True,
    )


def write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    fields = [
        "season",
        "team",
        "position",
        "depth_chart_position",
        "jersey_number",
        "status",
        "status_description_abbr",
        "full_name",
        "birth_date",
        "height",
        "weight",
        "college",
        "gsis_id",
        "week",
        "game_type",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def shaun_row(*, season: int, status: str, jersey_number: int = 58) -> dict[str, object]:
    return {
        "season": season,
        "team": "TEN",
        "position": "OLB",
        "depth_chart_position": "",
        "jersey_number": jersey_number,
        "status": status,
        "status_description_abbr": "A01",
        "full_name": "Shaun Phillips",
        "birth_date": "1981-05-13",
        "height": 75,
        "weight": 255,
        "college": "",
        "gsis_id": "00-0022723",
        "week": 4,
        "game_type": "REG",
    }


class WeeklyRosterDuplicateNormalizationTests(unittest.TestCase):
    def test_legacy_shield_status_variants_collapse_after_canonical_normalization(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset = weekly_dataset(root / "raw")
            write_rows(
                dataset.raw_path_for(2014),
                [
                    shaun_row(season=2014, status="ACT"),
                    shaun_row(season=2014, status="TRT"),
                ],
            )

            outputs, audit, _ = build_phase1_outputs(
                root,
                {dataset.id: dataset},
                CANONICAL,
                2026,
            )

            payload = next(payload for path, payload in outputs if path.name == "04.json")
            self.assertEqual(1, len(payload["Records"]))
            record = payload["Records"][0]
            self.assertEqual("NFLP-shaun-phillips", record["CanonicalPlayerID"])
            self.assertIsNone(record["Status"])
            self.assertEqual("A01", record["StatusDescription"])
            self.assertEqual(1, audit["weeklyRosters"]["equivalentDuplicateRowCount"])
            self.assertEqual(2, audit["weeklyRosters"]["legacyWeeklyStatusSuppressedRowCount"])
            self.assertEqual(1, audit["weeklyRosters"]["recordCount"])

    def test_legacy_duplicate_with_remaining_canonical_conflict_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset = weekly_dataset(root / "raw")
            write_rows(
                dataset.raw_path_for(2014),
                [
                    shaun_row(season=2014, status="ACT", jersey_number=58),
                    shaun_row(season=2014, status="TRT", jersey_number=59),
                ],
            )

            with self.assertRaisesRegex(ValueError, "Conflicting duplicate nflverse.weekly-rosters roster identity"):
                build_phase1_outputs(root, {dataset.id: dataset}, CANONICAL, 2026)

    def test_post_legacy_status_conflict_remains_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset = weekly_dataset(root / "raw")
            write_rows(
                dataset.raw_path_for(2016),
                [
                    shaun_row(season=2016, status="ACT"),
                    shaun_row(season=2016, status="TRT"),
                ],
            )

            with self.assertRaisesRegex(ValueError, "Conflicting duplicate nflverse.weekly-rosters roster identity"):
                build_phase1_outputs(root, {dataset.id: dataset}, CANONICAL, 2026)


if __name__ == "__main__":
    unittest.main()
