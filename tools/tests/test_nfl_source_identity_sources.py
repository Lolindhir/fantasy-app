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


def dataset(dataset_id: str, raw_path: Path, *, season_partitioned: bool = False) -> Dataset:
    return Dataset(
        id=dataset_id,
        provider="test",
        upstream="test",
        source_url="https://example.invalid/{season}" if season_partitioned else "https://example.invalid",
        raw_path=raw_path,
        metadata_path=(
            raw_path.parent / "metadata-{season}.json"
            if season_partitioned
            else raw_path.with_suffix(".metadata.json")
        ),
        required_columns=(),
        minimum_rows=1,
        kind="test",
        refresh_policy="test",
        retention_policy="test",
        license="test",
        attribution="test",
        source_mode="season-partitioned" if season_partitioned else "fixed",
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

    def test_persisted_stats_seed_retired_real_gsis_without_name_matching(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            players_path = root / "players.csv"
            ff_path = root / "ids.csv"
            stats_template = root / "stats/raw-{season}.csv"
            write_csv(
                players_path,
                [{"gsis_id": "00-1234567", "display_name": "Current Player", "position": "WR"}],
                ["gsis_id", "display_name", "position"],
            )
            write_csv(
                ff_path,
                [],
                ["mfl_id", "gsis_id", "sleeper_id", "espn_id", "pfr_id", "name", "birthdate", "position"],
            )
            write_csv(
                root / "stats/raw-1999.csv",
                [
                    {"player_id": "00-0005532", "player_name": "P.Franklin"},
                    {"player_id": "00-1234567", "player_name": "Current Player"},
                    {"player_id": "0", "player_name": ""},
                    {"player_id": "XX-0000001", "player_name": "S.Fernando"},
                ],
                ["player_id", "player_name"],
            )
            datasets = {
                "nflverse.players": dataset("nflverse.players", players_path),
                "nflverse.ff-player-ids": dataset("nflverse.ff-player-ids", ff_path),
                "nflverse.player-stats": dataset(
                    "nflverse.player-stats",
                    stats_template,
                    season_partitioned=True,
                ),
            }

            candidates, _, _, _ = raw_identity_candidates(root, datasets)
            fallback = [candidate for candidate in candidates if candidate.source == "nflverse.player-stats"]

            self.assertEqual(1, len(fallback))
            self.assertEqual({"GSIS": "00-0005532"}, fallback[0].ids)
            self.assertIsNone(fallback[0].name)
            self.assertFalse(any(candidate.ids.get("GSIS") == "0" for candidate in fallback))
            self.assertFalse(any(candidate.ids.get("GSIS") == "XX-0000001" for candidate in fallback))


if __name__ == "__main__":
    unittest.main()
