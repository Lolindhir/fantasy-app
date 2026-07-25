from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
TEST_DIR = Path(__file__).resolve().parent
if str(TEST_DIR) not in sys.path:
    sys.path.insert(0, str(TEST_DIR))

from podcast_package_builder import build_published_package
from podcast_pipeline_types import PipelineDataError, repo_root_from_script
from podcast_work_validation import validate_work_package
from podcast_pipeline_fixture import create_ready_work_package, write_json


class PodcastPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_root = Path(self.temp_dir.name)
        self.work = create_ready_work_package(self.temp_root)
        self.repo_root = repo_root_from_script()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_ready_synthetic_package_validates(self) -> None:
        report, data = validate_work_package(self.work, self.repo_root, require_ready=True)
        self.assertEqual([], report.errors)
        self.assertIsNotNone(data)
        self.assertEqual(1, len(data.takes))
        self.assertEqual(1, len(data.segments))

    def test_missing_claim_and_dimension_links_are_blocking(self) -> None:
        take_path = self.work / "takes/items/take-test-player.json"
        take = json.loads(take_path.read_text(encoding="utf-8"))
        take["claim_ids"] = []
        take["preserved_dimensions"] = ["positive_case"]
        write_json(take_path, take)
        report, _ = validate_work_package(self.work, self.repo_root, require_ready=True)
        messages = "\n".join(issue.message for issue in report.errors)
        self.assertIn("substantive claim is not linked", messages)
        self.assertIn("expected dimension is not preserved", messages)

    def test_unapproved_golden_profile_is_rejected(self) -> None:
        segment_path = self.work / "content-map/segments/segment-001.json"
        segment = json.loads(segment_path.read_text(encoding="utf-8"))
        segment["golden_profiles"].append("future-profile")
        write_json(segment_path, segment)
        report, _ = validate_work_package(self.work, self.repo_root, require_ready=True)
        self.assertTrue(any("not active" in issue.message for issue in report.errors))

    def test_builder_creates_deterministic_entry_points(self) -> None:
        output = self.temp_root / "published/test-0001"
        result = build_published_package(self.work, self.repo_root, output)
        self.assertEqual(output, result.output_dir)
        self.assertEqual(1, result.take_count)
        self.assertEqual(1, result.mention_count)
        self.assertEqual(1, result.section_count)
        episode = (output / "episode.md").read_text(encoding="utf-8")
        self.assertIn("College-Historie", episode)
        takes = json.loads((output / "takes.json").read_text(encoding="utf-8"))
        self.assertEqual("take-test-player", takes["take_categories"]["players"][0]["id"])
        mentions = json.loads((output / "mentions.json").read_text(encoding="utf-8"))
        self.assertEqual("mention-test-player", mentions["mentions"][0]["id"])
        index = json.loads((output / "index.json").read_text(encoding="utf-8"))
        self.assertEqual(0, index["mention_counts"]["uncovered"])
        self.assertTrue((output / "content-map/segments/segment-001.json").is_file())
        first_snapshot = {path.relative_to(output).as_posix(): path.read_bytes() for path in output.rglob("*") if path.is_file()}
        shutil.rmtree(output)
        build_published_package(self.work, self.repo_root, output)
        second_snapshot = {path.relative_to(output).as_posix(): path.read_bytes() for path in output.rglob("*") if path.is_file()}
        self.assertEqual(first_snapshot, second_snapshot)

    def test_invalid_build_leaves_no_partial_output(self) -> None:
        (self.work / "article/sections/010-player.md").unlink()
        output = self.temp_root / "published/invalid"
        with self.assertRaises(PipelineDataError):
            build_published_package(self.work, self.repo_root, output)
        self.assertFalse(output.exists())

    def test_existing_output_requires_explicit_replace(self) -> None:
        output = self.temp_root / "published/existing"
        output.mkdir(parents=True)
        (output / "sentinel.txt").write_text("keep", encoding="utf-8")
        with self.assertRaises(PipelineDataError):
            build_published_package(self.work, self.repo_root, output)
        self.assertEqual("keep", (output / "sentinel.txt").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
