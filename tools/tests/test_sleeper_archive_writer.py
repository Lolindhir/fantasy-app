"""#988 Sleeper daily + semantic change archival contract, synthetic files only."""
from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
ROOT = TOOLS.parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from external_source.sleeper_archive_writer import (  # noqa: E402
    SleeperArchiveAuthorizationError, SleeperArchiveCollisionError, persist_sleeper_observation,
)
from external_source.sleeper_snapshot_discovery import discover_sleeper_snapshots  # noqa: E402
from external_source.sleeper_trending import semantic_fingerprint  # noqa: E402


class SleeperAppendOnlyArchiveTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.snapshots = Path(tmp.name) / "data-source/market/roster-activity/sleeper/snapshots"
        self.latest = json.loads(
            (ROOT / "data-source/market/roster-activity/sleeper/latest.json").read_text(encoding="utf-8")
        )
        self.at = datetime(2026, 10, 17, 10, 1, 2, tzinfo=timezone.utc)

    def payload(self, observed=None, *, changed=False):
        output = copy.deepcopy(self.latest)
        output["generated_at"] = (observed or self.at).isoformat()
        if changed:
            player = next(p for p in output["players"] if p["add"]["status"] == "listed")
            player["add"]["count"] += 1
            activity = {}
            for kind in ("add", "drop"):
                activity[kind] = sorted(
                    [
                        {"player_id": p["sleeper_player_id"], "rank": p[kind]["rank"], "count": p[kind]["count"]}
                        for p in output["players"] if p[kind]["status"] == "listed"
                    ],
                    key=lambda row: row["rank"],
                )
            output["semantic_fingerprint"] = semantic_fingerprint(
                activity, lookback_hours=output["lookback_hours"], limit=output["limit"],
            )
        return output

    def write(self, document=None, **kwargs):
        return persist_sleeper_observation(
            self.snapshots,
            latest_document=document or self.payload(),
            storage_rights=kwargs.get("storage_rights", "allowed"),
            repository_visibility=kwargs.get("repository_visibility", "private"),
        )

    def test_public_or_unknown_retention_rights_fail_before_any_canonical_write(self):
        for rights, visibility in (
            ("unknown", "private"), ("restricted", "private"),
            ("forbidden", "private"), ("allowed", "public"),
            ("allowed", "internal"), ("allowed", "unknown"),
        ):
            with self.subTest(rights=rights, visibility=visibility):
                with self.assertRaises(SleeperArchiveAuthorizationError):
                    self.write(storage_rights=rights, repository_visibility=visibility)
                self.assertFalse(self.snapshots.exists())

    def test_first_daily_snapshot_is_complete_and_strips_derived_comparison(self):
        self.assertEqual("created", self.write())
        self.assertEqual("unchanged", self.write())
        saved = discover_sleeper_snapshots(self.snapshots)
        self.assertEqual(1, len(saved))
        self.assertTrue(saved[0].observation_file.is_file())
        evidence = json.loads(saved[0].observation_file.read_text(encoding="utf-8"))
        self.assertNotIn("comparison", evidence)
        self.assertEqual("sleeper", evidence["provider"])
        self.assertEqual("roster_activity", evidence["signal_kind"])
        self.assertEqual(self.latest["attribution"], evidence["attribution"])

    def test_daily_baseline_retained_even_when_rolling_activity_is_identical(self):
        self.assertEqual("created", self.write())
        next_day = self.at + timedelta(days=1)
        self.assertEqual("created", self.write(self.payload(next_day)))
        self.assertEqual("unchanged", self.write(self.payload(next_day + timedelta(minutes=20))))
        saved = discover_sleeper_snapshots(self.snapshots)
        self.assertEqual([self.at.date(), next_day.date()], [s.day for s in saved])

    def test_semantic_change_creates_intraday_snapshot_without_overwriting_first(self):
        self.assertEqual("created", self.write())
        before = discover_sleeper_snapshots(self.snapshots)[0].observation_file.read_bytes()
        new = self.payload(self.at + timedelta(minutes=2), changed=True)
        self.assertEqual("created", self.write(new))
        self.assertEqual("unchanged", self.write(self.payload(self.at + timedelta(minutes=3), changed=True)))
        entries = discover_sleeper_snapshots(self.snapshots)
        self.assertEqual(2, len(entries))
        self.assertEqual(before, entries[0].observation_file.read_bytes())
        self.assertNotEqual(
            json.loads(entries[0].observation_file.read_text())["semantic_fingerprint"],
            json.loads(entries[1].observation_file.read_text())["semantic_fingerprint"],
        )

    def test_invalid_fingerprint_and_backward_observation_fail_closed(self):
        doc = self.payload()
        player = next(p for p in doc["players"] if p["add"]["status"] == "listed")
        player["add"]["count"] += 1
        with self.assertRaisesRegex(ValueError, "Source fingerprint"):
            self.write(doc)
        self.assertFalse(self.snapshots.exists())
        self.assertEqual("created", self.write())
        with self.assertRaisesRegex(SleeperArchiveCollisionError, "Out-of-order"):
            self.write(self.payload(self.at - timedelta(hours=1)))
        self.assertEqual(1, len(discover_sleeper_snapshots(self.snapshots)))

    def test_partial_or_conflicting_immutable_source_fails_closed(self):
        self.assertEqual("created", self.write())
        saved = discover_sleeper_snapshots(self.snapshots)[0]
        saved.observation_file.unlink()
        with self.assertRaisesRegex(ValueError, "Missing immutable Sleeper observation"):
            self.write(self.payload(self.at + timedelta(minutes=5)))
        self.assertFalse(saved.observation_file.exists())


if __name__ == "__main__":
    unittest.main()
