from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "validate_episode_coverage.py"
SPEC = importlib.util.spec_from_file_location("validate_episode_coverage", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load validator module from {SCRIPT_PATH}")
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)

SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schemas"
INDEX_SCHEMA = SCHEMA_DIR / "episode-index.schema.json"
MENTIONS_SCHEMA = SCHEMA_DIR / "episode-mentions.schema.json"


class MentionCoverageValidatorTests(unittest.TestCase):
    def write_json(self, path: Path, data: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def player_take(self, take_id: str, name: str) -> dict[str, Any]:
        return {
            "id": take_id,
            "category": "players",
            "type": "ranking_subject",
            "raw_entity_mention": name,
            "entity": name,
            "team": "TST",
            "position": "WR",
            "entity_resolution": {
                "status": "confirmed",
                "method": "manual_confirmation",
                "confidence": "high",
            },
            "formats": ["dynasty"],
            "podcast_take": "Test take.",
            "reasoning": ["Test reasoning."],
            "risks": ["Test risk."],
            "sentiment": "positive",
            "conviction": "high",
            "evidence": {"timestamp_start": "00:01:00"},
            "tags": ["test"],
        }

    def mention(
        self,
        mention_id: str,
        name: str,
        mention_types: list[str],
        subject_ids: list[str],
        *,
        episode_md: bool = True,
        note: str | None = None,
    ) -> dict[str, Any]:
        return {
            "id": mention_id,
            "entity_type": "player",
            "raw_entity_mentions": [name],
            "entity": name,
            "entity_resolution": {
                "status": "confirmed",
                "method": "manual_confirmation",
                "confidence": "high",
            },
            "mention_types": mention_types,
            "occurrences": [{"timestamp_start": "00:01:00"}],
            "coverage": {
                "episode_md": episode_md,
                "standalone_take_required": bool(subject_ids),
                "subject_take_ids": subject_ids,
                "context_take_ids": [],
                "note": note,
            },
        }

    def create_package(
        self,
        root: Path,
        takes: list[dict[str, Any]],
        mentions: list[dict[str, Any]],
        episode_text: str,
        *,
        audit_status: str = "completed",
    ) -> Path:
        package = (
            root
            / "fantasy-management"
            / "sources"
            / "podcasts"
            / "test-source"
            / "episodes"
            / "2026"
            / "test_0001"
        )
        package.mkdir(parents=True, exist_ok=True)
        (package / "episode.md").write_text(episode_text, encoding="utf-8")

        takes_data = {
            "episode_id": "test_0001",
            "source_id": "test-source",
            "source_name": "Test Source",
            "take_categories": {
                "players": takes,
                "teams": [],
                "positions": [],
                "nfl": [],
                "fantasy": [],
                "other": [],
            },
        }
        self.write_json(package / "takes.json", takes_data)

        mention_data = {
            "episode_id": "test_0001",
            "source_id": "test-source",
            "source_name": "Test Source",
            "mentions": mentions,
        }
        self.write_json(package / "mentions.json", mention_data)

        take_map = {take["id"]: take for take in takes}
        counts = VALIDATOR.calculate_counts(mentions, take_map)
        index_data = {
            "package_schema_version": 2,
            "episode_id": "test_0001",
            "source_id": "test-source",
            "source_name": "Test Source",
            "episode_number": 1,
            "title": "Test Episode",
            "status": "active_source_package",
            "package_path": (
                "fantasy-management/sources/podcasts/test-source/episodes/2026/test_0001/"
            ),
            "files": {
                "episode_summary": "episode.md",
                "takes": "takes.json",
                "mentions": "mentions.json",
            },
            "take_counts": {
                "players": len(takes),
                "teams": 0,
                "positions": 0,
                "nfl": 0,
                "fantasy": 0,
                "other": 0,
            },
            "mention_counts": counts,
            "coverage_audit": {
                "status": audit_status,
                "method": "second_pass_entity_mention_sweep",
                "uncovered_mentions": counts["uncovered"],
                "notes": [],
            },
        }
        self.write_json(package / "index.json", index_data)
        return package

    def validate(self, root: Path, package: Path):
        report = VALIDATOR.Report()
        VALIDATOR.validate_package(
            package,
            root,
            INDEX_SCHEMA,
            MENTIONS_SCHEMA,
            report,
            True,
        )
        return report

    def test_substantive_subject_passes_without_technical_register(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            take_id = "test_0001_player_001"
            package = self.create_package(
                root,
                [self.player_take(take_id, "Test Player")],
                [
                    self.mention(
                        "test_0001_mention_001",
                        "Test Player",
                        ["ranking_subject"],
                        [take_id],
                    )
                ],
                "# Test Episode\n\n## Player profile\n\nTest Player is discussed in detail.\n",
            )
            report = self.validate(root, package)
            self.assertEqual([], report.errors)

    def test_audit_only_context_with_note_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = self.create_package(
                root,
                [],
                [
                    self.mention(
                        "test_0001_mention_001",
                        "Comparison Player",
                        ["player_comparison"],
                        [],
                        episode_md=False,
                        note="Technical comparison only; no substantive reader section required.",
                    )
                ],
                "# Test Episode\n\nNo substantive player subject.\n",
            )
            report = self.validate(root, package)
            self.assertEqual([], report.errors)

    def test_audit_only_context_without_note_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = self.create_package(
                root,
                [],
                [
                    self.mention(
                        "test_0001_mention_001",
                        "Comparison Player",
                        ["player_comparison"],
                        [],
                        episode_md=False,
                    )
                ],
                "# Test Episode\n",
            )
            report = self.validate(root, package)
            self.assertTrue(any("coverage.note" in issue.message for issue in report.errors))

    def test_required_subject_without_take_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = self.create_package(
                root,
                [],
                [
                    self.mention(
                        "test_0001_mention_001",
                        "Missing Player",
                        ["ranking_subject"],
                        [],
                    )
                ],
                "# Test Episode\n\nMissing Player\n",
            )
            report = self.validate(root, package)
            self.assertTrue(any("requires a valid subject take" in issue.message for issue in report.errors))

    def test_needs_review_status_fails_schema_v2_completion(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            take_id = "test_0001_player_001"
            package = self.create_package(
                root,
                [self.player_take(take_id, "Test Player")],
                [self.mention("test_0001_mention_001", "Test Player", ["ranking_subject"], [take_id])],
                "# Test Episode\n\nTest Player\n",
                audit_status="needs_review",
            )
            report = self.validate(root, package)
            self.assertTrue(any("coverage_audit.status" in issue.message for issue in report.errors))

    def test_non_pretty_json_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = self.create_package(root, [], [], "# Test Episode\n")
            path = package / "mentions.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            report = self.validate(root, package)
            self.assertTrue(any("canonical pretty JSON" in issue.message for issue in report.errors))


if __name__ == "__main__":
    unittest.main()
