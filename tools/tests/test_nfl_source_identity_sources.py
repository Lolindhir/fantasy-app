import csv
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

from nfl_source_data_lib.common import Dataset
from nfl_source_data_lib.identity_sources import raw_identity_candidates


def write_csv(path: Path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def dataset(dataset_id: str, raw_path: Path) -> Dataset:
    return Dataset(
        id=dataset_id,
        provider="test",
        upstream="test",
        source_url="https://example.invalid",
        raw_path=raw_path,
        metadata_path=raw_path.with_suffix(".metadata.json"),
        required_columns=(),
        minimum_rows=1,
        kind="test",
        refresh_policy="test",
        retention_policy="test",
        license="test",
        attribution="test",
    )


class NflSourceIdentitySourceTests(unittest.TestCase):
    def test_one_bad_anchor_is_suppressed_without_losing_good_sleeper_mapping(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            players_path = root / "players.csv"
            ff_path = root / "ids.csv"
            write_csv(
                players_path,
                [
                    {"gsis_id": "00-A", "display_name": "Player A", "pfr_id": "Good00", "espn_id": "111", "position": "WR", "birth_date": "2000-01-01"},
                    {"gsis_id": "00-B", "display_name": "Player B", "pfr_id": "Other00", "espn_id": "222", "position": "RB", "birth_date": "1990-01-01"},
                ],
                ["gsis_id", "display_name", "pfr_id", "espn_id", "position", "birth_date"],
            )
            write_csv(
                ff_path,
                [
                    {"mfl_id": "1", "gsis_id": "00-A", "sleeper_id": "S1", "espn_id": "222", "pfr_id": "Good00", "name": "Player A", "birthdate": "2000-01-01", "position": "WR"}
                ],
                ["mfl_id", "gsis_id", "sleeper_id", "espn_id", "pfr_id", "name", "birthdate", "position"],
            )
            datasets = {
                "nflverse.players": dataset("nflverse.players", players_path),
                "nflverse.ff-player-ids": dataset("nflverse.ff-player-ids", ff_path),
            }
            candidates, _, ff_candidates, conflicts = raw_identity_candidates(root, datasets)
            self.assertEqual(3, len(candidates))
            ff_candidate = ff_candidates[0]
            self.assertIsNotNone(ff_candidate)
            self.assertEqual("S1", ff_candidate.ids["Sleeper"])
            self.assertEqual("00-A", ff_candidate.ids["GSIS"])
            self.assertEqual("Good00", ff_candidate.ids["PFR"])
            self.assertNotIn("ESPN", ff_candidate.ids)
            self.assertEqual("mapping", conflicts[0]["QuarantineScope"])
            self.assertEqual({"ESPN": "222"}, conflicts[0]["SuppressedIDs"])

    def test_no_matching_anchor_keeps_full_row_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            players_path = root / "players.csv"
            ff_path = root / "ids.csv"
            write_csv(
                players_path,
                [{"gsis_id": "00-A", "display_name": "Player A", "pfr_id": "Good00", "espn_id": "111", "position": "WR", "birth_date": "2000-01-01"}],
                ["gsis_id", "display_name", "pfr_id", "espn_id", "position", "birth_date"],
            )
            write_csv(
                ff_path,
                [{"mfl_id": "99", "gsis_id": "00-A", "sleeper_id": "S1", "espn_id": "111", "pfr_id": "Good00", "name": "Legacy Homonym", "birthdate": "1970-01-01", "position": "DL"}],
                ["mfl_id", "gsis_id", "sleeper_id", "espn_id", "pfr_id", "name", "birthdate", "position"],
            )
            datasets = {
                "nflverse.players": dataset("nflverse.players", players_path),
                "nflverse.ff-player-ids": dataset("nflverse.ff-player-ids", ff_path),
            }
            _, _, ff_candidates, conflicts = raw_identity_candidates(root, datasets)
            self.assertEqual({"MFL": "99"}, ff_candidates[0].ids)
            self.assertEqual("row", conflicts[0]["QuarantineScope"])
            self.assertIn("Sleeper", conflicts[0]["SuppressedIDs"])


if __name__ == "__main__":
    unittest.main()
