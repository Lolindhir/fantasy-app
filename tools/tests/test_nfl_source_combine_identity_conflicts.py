import csv
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

from nfl_source_data_lib.audit import _combine_audit
from nfl_source_data_lib.combine import build_combine_files
from nfl_source_data_lib.common import Dataset


COMBINE_FIELDS = [
    "season", "draft_year", "draft_team", "draft_round", "draft_ovr",
    "pfr_id", "cfb_id", "player_name", "pos", "school", "ht", "wt",
    "forty", "bench", "vertical", "broad_jump", "cone", "shuttle",
]


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COMBINE_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def combine_dataset(raw_path: Path) -> Dataset:
    return Dataset(
        "nflverse.combine",
        "nflverse",
        "test",
        "https://example.invalid/combine.csv",
        raw_path,
        Path("metadata.json"),
        tuple(COMBINE_FIELDS),
        1,
        "athletic-measurement-history",
        "discover-new-partitions",
        "permanent-by-season",
        "test",
        "test",
        "immutable-history",
        "season",
        "freeze-prior-seasons",
        "explicit-force",
    )


class CombineIdentityConflictTests(unittest.TestCase):
    def test_distinct_same_season_pfr_claims_are_quarantined_and_audited(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "combine.csv"
            write_csv(raw, [
                {
                    "season": "2000",
                    "draft_year": "2000",
                    "draft_team": "Tennessee Titans",
                    "draft_round": "7",
                    "draft_ovr": "213",
                    "pfr_id": "GreeMi00",
                    "player_name": "Mike Green",
                    "pos": "S",
                    "school": "NW State (LA)",
                    "wt": "189",
                },
                {
                    "season": "2000",
                    "draft_year": "2000",
                    "draft_team": "Tennessee Titans",
                    "draft_round": "7",
                    "draft_ovr": "213",
                    "pfr_id": "GreeMi00",
                    "cfb_id": "mike-green-4",
                    "player_name": "Mike Green",
                    "pos": "FB",
                    "school": "Houston",
                    "wt": "253",
                },
            ])
            canonical = [{"NFLPlayerID": "NFLP-1", "IDs": {"PFR": "GreeMi00"}}]

            grouped, conflicts = build_combine_files(combine_dataset(raw), canonical, {})

            self.assertEqual([], conflicts)
            self.assertEqual(2, len(grouped[2000]))
            for record in grouped[2000]:
                self.assertIsNone(record["NFLPlayerID"])
                self.assertEqual("GreeMi00", record["SourceIDs"]["PFR"])
                self.assertEqual("ambiguous", record["IdentityResolution"]["Status"])
                self.assertEqual("duplicate-source-claim", record["IdentityResolution"]["Reason"])
                self.assertIsNone(record["Draft"])

            audit = _combine_audit(
                [],
                canonical,
                {2000: {"Season": 2000, "Records": grouped[2000]}},
                conflicts,
            )
            self.assertEqual(2, audit["ambiguousIdentityRecordCount"])
            self.assertEqual(1, audit["ambiguousIdentitySourceCount"])
            self.assertEqual("GreeMi00", audit["ambiguousIdentitySources"][0]["PFR"])
            self.assertEqual(2, len(audit["ambiguousIdentitySources"][0]["Claims"]))
            self.assertEqual(2, audit["bySeason"]["2000"]["ambiguousIdentityRecords"])

    def test_identical_duplicate_source_row_still_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "combine.csv"
            row = {
                "season": "2025",
                "pfr_id": "PlayTe00",
                "player_name": "Test Player",
                "pos": "WR",
            }
            write_csv(raw, [row, dict(row)])

            with self.assertRaisesRegex(
                ValueError,
                "Duplicate identical combine row for PFR identity 2025/PlayTe00",
            ):
                build_combine_files(combine_dataset(raw), [], {})

    def test_distinct_pfr_ids_resolving_to_same_canonical_player_still_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "combine.csv"
            write_csv(raw, [
                {
                    "season": "2025",
                    "pfr_id": "PlayTe00",
                    "player_name": "Test Player",
                    "pos": "WR",
                },
                {
                    "season": "2025",
                    "pfr_id": "PlayTe01",
                    "player_name": "Test Player",
                    "pos": "WR",
                },
            ])
            canonical = [
                {"NFLPlayerID": "NFLP-1", "IDs": {"PFR": "PlayTe00"}},
                {"NFLPlayerID": "NFLP-1", "IDs": {"PFR": "PlayTe01"}},
            ]

            with self.assertRaisesRegex(
                ValueError,
                "Duplicate combine canonical identity 2025/NFLP-1",
            ):
                build_combine_files(combine_dataset(raw), canonical, {})


if __name__ == "__main__":
    unittest.main()
