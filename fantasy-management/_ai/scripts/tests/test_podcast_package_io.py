from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from podcast_package_io import PackageDataError, load_mentions, load_takes  # noqa: E402


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


IDENTITY = {"episode_id": "sl_test", "source_id": "stoned-lack", "source_name": "Stoned Lack"}


class PodcastPackageIoTests(unittest.TestCase):
    def test_inline_takes_remain_supported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp)
            inline = {**IDENTITY, "take_categories": {name: [] for name in ["players", "teams", "positions", "nfl", "fantasy", "other"]}}
            write_json(package / "takes.json", inline)
            loaded = load_takes(package)
            self.assertEqual("inline", loaded.mode)
            self.assertEqual(inline, loaded.aggregate)
            self.assertEqual((), loaded.part_documents)

    def test_split_takes_are_aggregated_by_category(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp)
            players = [{"id": "sl_test_player_001"}]
            write_json(package / "takes/players-part01.json", {**IDENTITY, "category": "players", "takes": players})
            write_json(package / "takes/players-part02.json", {**IDENTITY, "category": "players", "takes": []})
            write_json(package / "takes/teams.json", {**IDENTITY, "category": "teams", "takes": []})
            for category in ["positions", "nfl", "fantasy", "other"]:
                write_json(package / f"takes/{category}.json", {**IDENTITY, "category": category, "takes": []})
            counts = {name: 0 for name in ["players", "teams", "positions", "nfl", "fantasy", "other"]}
            counts["players"] = 1
            write_json(package / "takes.json", {**IDENTITY, "storage_mode": "split", "take_counts": counts, "parts": [
                {"category": "players", "path": "takes/players-part01.json", "count": 1},
                {"category": "players", "path": "takes/players-part02.json", "count": 0},
                {"category": "teams", "path": "takes/teams.json", "count": 0},
                *[{"category": category, "path": f"takes/{category}.json", "count": 0} for category in ["positions", "nfl", "fantasy", "other"]],
            ]})
            loaded = load_takes(package)
            self.assertEqual("split", loaded.mode)
            self.assertEqual(players, loaded.aggregate["take_categories"]["players"])
            self.assertEqual([], loaded.aggregate["take_categories"]["teams"])

    def test_split_mentions_require_contiguous_part_numbers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp)
            write_json(package / "mentions/part01.json", {**IDENTITY, "part_number": 2, "mentions": [{"id": "x"}]})
            write_json(package / "mentions.json", {**IDENTITY, "storage_mode": "split", "mention_count": 1, "parts": [{"path": "mentions/part01.json", "count": 1}]})
            with self.assertRaisesRegex(PackageDataError, "contiguous"):
                load_mentions(package)

    def test_manifest_count_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp)
            write_json(package / "mentions/part01.json", {**IDENTITY, "part_number": 1, "mentions": [{"id": "x"}]})
            write_json(package / "mentions.json", {**IDENTITY, "storage_mode": "split", "mention_count": 2, "parts": [{"path": "mentions/part01.json", "count": 1}]})
            with self.assertRaisesRegex(PackageDataError, "mention_count"):
                load_mentions(package)

    def test_part_path_cannot_escape_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp)
            counts = {name: 0 for name in ["players", "teams", "positions", "nfl", "fantasy", "other"]}
            write_json(package / "takes.json", {**IDENTITY, "storage_mode": "split", "take_counts": counts, "parts": [{"category": "players", "path": "../players.json", "count": 0}]})
            with self.assertRaisesRegex(PackageDataError, "inside the package"):
                load_takes(package)


if __name__ == "__main__":
    unittest.main()
