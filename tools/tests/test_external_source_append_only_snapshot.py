"""#988 4A.2 dormant writer: synthetic append-only and rights/visibility gates."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from external_source.append_only_snapshot import (  # noqa: E402
    ArchiveAuthorizationError,
    ArchiveWriteError,
    persist_ranked_snapshot,
)
from external_source.snapshot_plan import (  # noqa: E402
    SnapshotCollisionError,
    inspect_planned_snapshot,
    plan_snapshot,
)
from external_source.snapshot_discovery import discover_snapshots  # noqa: E402


class DormantAppendOnlyWriterTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "ranked" / "snapshots"
        self.observed = datetime(2026, 10, 17, 12, 34, 56, tzinfo=timezone.utc)
        self.csv = "name,Rank,position,source_player_id\nFixture,1,QB,100\n"
        self.plan = plan_snapshot(
            self.root, observed_at=self.observed, csv_content=self.csv, schema_version=4
        )

    def metadata(self, plan=None):
        plan = plan or self.plan
        return {
            "schema_version": plan.schema_version,
            "ranking_id": "synthetic-provider-format",
            "fetched_at": self.observed.isoformat(),
            "snapshot": {
                "ranking_sha256": plan.ranking_sha256,
                "csv_columns": ["name", "Rank", "position", "source_player_id"],
                "row_count": 1,
            },
        }

    def save(self, plan=None, csv=None, metadata=None, **overrides):
        plan = plan or self.plan
        return persist_ranked_snapshot(
            plan,
            csv_content=csv or self.csv,
            source_metadata=metadata or self.metadata(plan),
            storage_rights=overrides.get("storage_rights", "allowed"),
            repository_visibility=overrides.get("repository_visibility", "private"),
        )

    def test_public_or_unknown_rights_never_create_any_archive(self) -> None:
        for rights, visibility in (
            ("unknown", "private"),
            ("forbidden", "private"),
            ("restricted", "private"),
            ("allowed", "public"),
            ("allowed", "internal"),
            ("allowed", "unknown"),
        ):
            with self.subTest(rights=rights, visibility=visibility):
                with self.assertRaises(ArchiveAuthorizationError):
                    self.save(storage_rights=rights, repository_visibility=visibility)
                self.assertFalse(self.root.exists())

    def test_private_allowed_snapshot_created_once_and_replay_idempotent(self) -> None:
        self.assertEqual("created", self.save())
        self.assertEqual("identical", self.save())
        self.assertEqual("identical", inspect_planned_snapshot(self.plan, csv_content=self.csv))
        saved = json.loads(self.plan.metadata_file.read_text(encoding="utf-8"))
        self.assertEqual(self.plan.semantic_sha256, saved["snapshot_semantic_sha256"])
        self.assertEqual(self.plan.ranking_sha256, saved["snapshot"]["ranking_sha256"])
        self.assertEqual(self.plan.key, saved["snapshot_key"])
        self.assertEqual(self.csv, self.plan.ranking_file.read_text(encoding="utf-8"))
        observed = discover_snapshots(self.root)
        self.assertEqual([self.plan.key], [item.key for item in observed])

    def test_two_observations_same_day_append_without_overwriting(self) -> None:
        self.assertEqual("created", self.save())
        changed_csv = self.csv.replace("Fixture", "Changed")
        changed = plan_snapshot(
            self.root, observed_at=self.observed, csv_content=changed_csv, schema_version=4,
        )
        self.assertNotEqual(self.plan.directory, changed.directory)
        self.assertEqual("created", self.save(plan=changed, csv=changed_csv))
        self.assertEqual(2, len(discover_snapshots(self.root)))
        self.assertEqual(self.csv, self.plan.ranking_file.read_text(encoding="utf-8"))

    def test_legacy_daily_snapshot_is_untouched(self) -> None:
        daily = self.root / "2026-10-17"
        daily.mkdir(parents=True)
        (daily / "ranking.csv").write_text("legacy\n", encoding="utf-8")
        (daily / "metadata.json").write_text('{"schema_version":1}\n', encoding="utf-8")
        self.assertEqual("created", self.save())
        self.assertEqual("legacy\n", (daily / "ranking.csv").read_text(encoding="utf-8"))
        self.assertEqual(2, len(discover_snapshots(self.root)))

    def test_partial_or_tampered_snapshot_fails_closed(self) -> None:
        self.plan.directory.mkdir(parents=True)
        (self.plan.directory / "ranking.csv").write_text("partial\n", encoding="utf-8")
        with self.assertRaises(SnapshotCollisionError):
            self.save()
        self.assertEqual("partial\n", self.plan.ranking_file.read_text(encoding="utf-8"))

    def test_replay_with_different_metadata_is_collision(self) -> None:
        self.assertEqual("created", self.save())
        other_metadata = self.metadata()
        other_metadata["fetched_at"] = "2026-10-17T12:34:57+00:00"
        with self.assertRaises(SnapshotCollisionError):
            self.save(metadata=other_metadata)
        self.assertEqual(self.metadata()["fetched_at"], json.loads(
            self.plan.metadata_file.read_text(encoding="utf-8")
        )["fetched_at"])

    def test_invalid_source_hash_schema_or_timestamp_fails_before_directory_creation(self) -> None:
        invalid_hash = self.metadata()
        invalid_hash["snapshot"]["ranking_sha256"] = "0" * 64
        with self.assertRaises(ArchiveWriteError):
            self.save(metadata=invalid_hash)
        invalid_schema = self.metadata()
        invalid_schema["schema_version"] = 3
        with self.assertRaises(ArchiveWriteError):
            self.save(metadata=invalid_schema)
        invalid_id = self.metadata()
        invalid_id["snapshot_key"] = "other-date"
        with self.assertRaises(ArchiveWriteError):
            self.save(metadata=invalid_id)
        self.assertFalse(self.root.exists())


if __name__ == "__main__":
    unittest.main()
