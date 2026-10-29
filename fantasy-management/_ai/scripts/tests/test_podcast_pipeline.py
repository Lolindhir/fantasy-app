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


    def test_weekly_profiles_and_game_context_contract(self) -> None:
        from jsonschema import Draft202012Validator
        from podcast_pipeline_schema import load_golden_profiles, schema_path
        from podcast_pipeline_types import PipelineReport

        report = PipelineReport()
        active = load_golden_profiles(self.repo_root, report)
        self.assertEqual([], report.errors)
        self.assertIn("game-matchup-preview", active.active_ids)
        self.assertIn("weekly-fantasy-start-sit", active.active_ids)

        def schema(key: str) -> dict:
            return json.loads(schema_path(self.repo_root, key).read_text(encoding="utf-8"))

        context = {"season": 2026, "week": 7, "game": {"home_team": "Example A", "away_team": "Example B"}}
        subject = {"type": "game", "entity": "Example B @ Example A"}
        segment = json.loads((self.work / "content-map/segments/segment-001.json").read_text(encoding="utf-8"))
        take = json.loads((self.work / "takes/items/take-test-player.json").read_text(encoding="utf-8"))
        segment.update(segment_type="weekly_matchup", primary_subjects=[subject], weekly_context=context,
                       golden_profiles=["game-matchup-preview"])
        take.update(type="start_sit", primary_subject=subject, weekly_context=context,
                    golden_profiles=["weekly-fantasy-start-sit"])
        self.assertEqual([], list(Draft202012Validator(schema("content_map_segment")).iter_errors(segment)))
        self.assertEqual([], list(Draft202012Validator(schema("take_item")).iter_errors(take)))
        segment.pop("weekly_context")
        take.pop("weekly_context")
        self.assertTrue(list(Draft202012Validator(schema("content_map_segment")).iter_errors(segment)))
        self.assertTrue(list(Draft202012Validator(schema("take_item")).iter_errors(take)))

    def test_legacy_takes_require_no_weekly_context(self) -> None:
        from jsonschema import Draft202012Validator
        from podcast_pipeline_schema import schema_path

        take = json.loads((self.work / "takes/items/take-test-player.json").read_text(encoding="utf-8"))
        schema = json.loads(schema_path(self.repo_root, "take_item").read_text(encoding="utf-8"))
        self.assertEqual([], list(Draft202012Validator(schema).iter_errors(take)))


if __name__ == "__main__":
    unittest.main()
