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
    "CanonicalPlayerID": "NFLP-fred-taylor",
    "IDs": {"GSIS": "00-0016098"},
    "IDAliases": {},
}]


def season_dataset(root: Path) -> Dataset:
    return Dataset(
        id="nflverse.rosters",
        provider="nflverse",
        upstream="test",
        source_url="https://example.invalid/roster_{season}.csv",
        raw_path=root / "raw-{season}.csv",
        metadata_path=root / "metadata-{season}.json",
        required_columns=("season", "team", "gsis_id"),
        minimum_rows=1,
        kind="seasonal-roster",
        refresh_policy="current-season",
        retention_policy="permanent-by-season",
        license="test",
        attribution="test",
        lifecycle_class="seasonal-finalizable",
        partition_key="season",
        finalization_policy="freeze-prior-seasons",
        repair_policy="explicit-force",
        source_mode="season-partitioned",
        source_format="csv",
        availability_policy="required",
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
        "espn_id",
        "sportradar_id",
        "yahoo_id",
        "rotowire_id",
        "pff_id",
        "pfr_id",
        "fantasy_data_id",
        "sleeper_id",
        "esb_id",
        "week",
        "game_type",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def fred_row(
    *,
    team: str = "NE",
    week: int = 19,
    jersey_number: int = 21,
    espn_id: str = "",
    rotowire_id: str = "",
    pff_id: str = "333",
    pfr_id: str = "",
) -> dict[str, object]:
    return {
        "season": 2010,
        "team": team,
        "position": "RB",
        "depth_chart_position": "",
        "jersey_number": jersey_number,
        "status": "ACT",
        "status_description_abbr": "I01",
        "full_name": "Fred Taylor",
        "birth_date": "1976-01-27",
        "height": 73,
        "weight": 228,
        "college": "",
        "gsis_id": "00-0016098",
        "espn_id": espn_id,
        "sportradar_id": "",
        "yahoo_id": "",
        "rotowire_id": rotowire_id,
        "pff_id": pff_id,
        "pfr_id": pfr_id,
        "fantasy_data_id": "",
        "sleeper_id": "",
        "esb_id": "",
        "week": week,
        "game_type": "DIV",
    }


class SeasonRosterDuplicateNormalizationTests(unittest.TestCase):
    def test_real_fred_taylor_duplicate_merges_compatible_optional_source_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset = season_dataset(root / "raw")
            write_rows(
                dataset.raw_path_for(2010),
                [
                    fred_row(),
                    fred_row(espn_id="1430", rotowire_id="906", pfr_id="TaylFr00"),
                ],
            )

            outputs, audit, _ = build_phase1_outputs(
                root,
                {dataset.id: dataset},
                CANONICAL,
                2026,
            )

            payload = next(payload for path, payload in outputs if path.name == "2010.json")
            self.assertEqual(1, len(payload["Records"]))
            record = payload["Records"][0]
            self.assertEqual("NFLP-fred-taylor", record["CanonicalPlayerID"])
            self.assertEqual(
                {
                    "GSIS": "00-0016098",
                    "ESPN": "1430",
                    "PFR": "TaylFr00",
                    "PFF": "333",
                    "Rotowire": "906",
                },
                record["SourceIDs"],
            )
            self.assertEqual(1, audit["rosters"]["equivalentDuplicateRowCount"])
            self.assertEqual(1, audit["rosters"]["recordCount"])

    def test_season_identity_does_not_use_provider_week(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset = season_dataset(root / "raw")
            write_rows(
                dataset.raw_path_for(2010),
                [
                    fred_row(week=18),
                    fred_row(week=19, espn_id="1430"),
                ],
            )

            outputs, audit, _ = build_phase1_outputs(root, {dataset.id: dataset}, CANONICAL, 2026)
            payload = next(payload for path, payload in outputs if path.name == "2010.json")
            self.assertEqual(1, len(payload["Records"]))
            self.assertEqual(1, audit["rosters"]["equivalentDuplicateRowCount"])

    def test_remaining_canonical_fact_conflict_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset = season_dataset(root / "raw")
            write_rows(
                dataset.raw_path_for(2010),
                [
                    fred_row(jersey_number=21),
                    fred_row(jersey_number=22),
                ],
            )

            with self.assertRaisesRegex(ValueError, "Conflicting duplicate nflverse.rosters roster identity"):
                build_phase1_outputs(root, {dataset.id: dataset}, CANONICAL, 2026)

    def test_conflicting_nonempty_source_id_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset = season_dataset(root / "raw")
            write_rows(
                dataset.raw_path_for(2010),
                [
                    fred_row(pfr_id="TaylFr00"),
                    fred_row(pfr_id="OtherFr00"),
                ],
            )

            with self.assertRaisesRegex(ValueError, "Conflicting duplicate nflverse.rosters SourceID PFR"):
                build_phase1_outputs(root, {dataset.id: dataset}, CANONICAL, 2026)

    def test_same_gsis_on_different_teams_remains_distinct(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset = season_dataset(root / "raw")
            write_rows(
                dataset.raw_path_for(2010),
                [
                    fred_row(team="NE"),
                    fred_row(team="JAX"),
                ],
            )

            outputs, audit, _ = build_phase1_outputs(root, {dataset.id: dataset}, CANONICAL, 2026)
            payload = next(payload for path, payload in outputs if path.name == "2010.json")
            self.assertEqual(2, len(payload["Records"]))
            self.assertEqual(["JAX", "NE"], [record["Team"] for record in payload["Records"]])
            self.assertEqual(0, audit["rosters"]["equivalentDuplicateRowCount"])


if __name__ == "__main__":
    unittest.main()
