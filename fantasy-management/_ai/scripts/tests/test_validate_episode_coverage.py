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
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def create_package(
        self,
        root: Path,
        *,
        takes: list[dict[str, Any]],
        mentions: list[dict[str, Any]],
        mention_counts: dict[str, int],
        episode_text: str,
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

        self.write_json(
            package / "takes.json",
            {
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
            },
        )
        self.write_json(
            package / "mentions.json",
            {
                "episode_id": "test_0001",
                "source_id": "test-source",
                "source_name": "Test Source",
                "mentions": mentions,
            },
        )
        self.write_json(
            package / "index.json",
            {
                "package_schema_version": 2,
                "episode_id": "test_0001",
                "source_id": "test-source",
                "source_name": "Test Source",
                "episode_number": 1,
                "title": "Test Episode",
                "status": "active_source_package",
                "package_path": (
                    "fantasy-management/sources/podcasts/test-source/"
                    "episodes/2026/test_0001/"
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
                "mention_counts": mention_counts,
                "coverage_audit": {
                    "status": "completed",
                    "method": "second_pass_entity_mention_sweep",
                    "uncovered_mentions": mention_counts["uncovered"],
                    "notes": [],
                },
            },
        )
        return package

    def player_take(self, take_id: str, raw: str, entity: str) -> dict[str, Any]:
        return {
            "id": take_id,
            "category": "players",
            "type": "player",
            "raw_entity_mention": raw,
            "entity": entity,
            "team": "TST",
            "position": "WR",
            "entity_resolution": {
                "status": "confirmed",
                "method": "manual_confirmation",
                "confidence": "high",
            },
            "formats": [
                "dynasty"
            ],
            "podcast_take": "Test take.",
            "reasoning": [
                "Test reasoning."
            ],
            "risks": [
                "Test risk."
            ],
            "sentiment": "positive",
            "conviction": "high",
            "evidence": {
                "timestamp_start": "00:01:00",
                "timestamp_end": "00:02:00",
            },
            "tags": [
                "test"
            ],
        }

    def mention(
        self,
        *,
        mention_id: str,
        raw: str,
        entity: str,
        mention_types: list[str],
        standalone: bool,
        subject_take_ids: list[str],
        context_take_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        return {
            "id": mention_id,
            "entity_type": "player",
            "raw_entity_mentions": [
                raw
            ],
            "entity": entity,
            "entity_resolution": {
                "status": "confirmed",
                "method": "manual_confirmation",
                "confidence": "high",
            },
            "mention_types": mention_types,
            "occurrences": [
                {
                    "timestamp_start": "00:01:00",
                    "timestamp_end": "00:02:00",
                    "section": "Test",
                    "context_summary": "Test context.",
                }
            ],
            "coverage": {
                "episode_md": True,
                "episode_md_section": "Complete mention register",
                "standalone_take_required": standalone,
                "subject_take_ids": subject_take_ids,
                "context_take_ids": context_take_ids or [],
                "note": None,
            },
        }

    def validate(self, root: Path, package: Path):
        report = VALIDATOR.Report()
        VALIDATOR.validate_package(
            package_dir=package,
            root=root,
            index_schema_path=INDEX_SCHEMA,
            mentions_schema_path=MENTIONS_SCHEMA,
            report=report,
            warnings_for_legacy=True,
        )
        return report

    def test_valid_schema_version_2_package_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            take_id = "test_0001_player_001"
            package = self.create_package(
                root,
                takes=[self.player_take(take_id, "Test Player", "Test Player")],
                mentions=[
                    self.mention(
                        mention_id="test_0001_mention_001",
                        raw="Test Player",
                        entity="Test Player",
                        mention_types=["ranking_subject", "substantive_take"],
                        standalone=True,
                        subject_take_ids=[take_id],
                    )
                ],
                mention_counts={
                    "total": 1,
                    "resolved": 1,
                    "ambiguous": 0,
                    "unresolved": 0,
                    "ranking_subjects": 1,
                    "substantive_subjects": 1,
                    "context_only": 0,
                    "with_take_links": 1,
                    "uncovered": 0,
                },
                episode_text=(
                    "# Test Episode\n\n"
                    "## Complete mention register\n\n"
                    "| Entity | Role |\n|---|---|\n| Test Player | Ranking subject |\n"
                ),
            )

            report = self.validate(root, package)

            self.assertEqual([], report.errors)

    def test_ranking_subject_without_subject_take_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = self.create_package(
                root,
                takes=[],
                mentions=[
                    self.mention(
                        mention_id="test_0001_mention_001",
                        raw="Missing Player",
                        entity="Missing Player",
                        mention_types=["ranking_subject"],
                        standalone=True,
                        subject_take_ids=[],
                    )
                ],
                mention_counts={
                    "total": 1,
                    "resolved": 1,
                    "ambiguous": 0,
                    "unresolved": 0,
                    "ranking_subjects": 1,
                    "substantive_subjects": 0,
                    "context_only": 0,
                    "with_take_links": 0,
                    "uncovered": 1,
                },
                episode_text="# Test Episode\n\nMissing Player\n",
            )

            report = self.validate(root, package)

            self.assertTrue(
                any("no valid subject take link" in issue.message for issue in report.errors)
            )

    def test_context_link_does_not_cover_another_players_take(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            take_id = "test_0001_player_001"
            package = self.create_package(
                root,
                takes=[self.player_take(take_id, "Main Player", "Main Player")],
                mentions=[
                    self.mention(
                        mention_id="test_0001_mention_001",
                        raw="Comparison Player",
                        entity="Comparison Player",
                        mention_types=["player_comparison"],
                        standalone=False,
                        subject_take_ids=[],
                        context_take_ids=[take_id],
                    )
                ],
                mention_counts={
                    "total": 1,
                    "resolved": 1,
                    "ambiguous": 0,
                    "unresolved": 0,
                    "ranking_subjects": 0,
                    "substantive_subjects": 0,
                    "context_only": 1,
                    "with_take_links": 1,
                    "uncovered": 0,
                },
                episode_text="# Test Episode\n\nComparison Player\n",
            )

            report = self.validate(root, package)

            self.assertTrue(
                any(
                    "not covered as a matching subject take" in issue.message
                    for issue in report.errors
                )
            )


if __name__ == "__main__":
    unittest.main()
