"""App consumer of the league-schedule-outlook product: index-verified latest snapshot, fail-closed, semantic no-op (#1519).

Synthetic product files only (no hard-wired league data).
"""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
import league_schedule_outlook_app_publish as pub  # noqa: E402
from matchup_context_app_publish import Writer  # noqa: E402

LEAGUE, SEASON = "test-league", 2030


def write_product(root: Path, weeks: int = 3, tamper: bool = False, drop_index_entry: int | None = None) -> Path:
    folder = root / "league-schedule-outlook" / LEAGUE / str(SEASON)
    folder.mkdir(parents=True)
    entries = []
    for week in range(weeks):
        document = {"Product": "league-schedule-outlook", "Season": SEASON, "AsOf": {"AfterWeek": week}, "Marker": f"w{week}"}
        raw = json.dumps(document, separators=(",", ":")).encode()
        name = f"after-week-{week:02d}.json"
        (folder / name).write_bytes(raw)
        entries.append({"AfterWeek": week, "File": name, "InputFingerprint": "f", "Sha256": hashlib.sha256(raw).hexdigest()})
    if tamper:
        (folder / f"after-week-{weeks - 1:02d}.json").write_bytes(b'{"AsOf":{"AfterWeek":%d},"Marker":"x"}' % (weeks - 1))
    if drop_index_entry is not None:
        entries = [e for e in entries if e["AfterWeek"] != drop_index_entry]
    index = {"Product": pub.INDEX_PRODUCT, "Season": SEASON, "LeagueScoredWeek": weeks - 1, "Snapshots": entries}
    (folder / "index.json").write_text(json.dumps(index), encoding="utf-8")
    return folder


class LatestSnapshotTests(unittest.TestCase):
    def test_returns_newest_snapshot_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            write_product(Path(tmp), weeks=4)
            self.assertEqual(pub.latest_snapshot(Path(tmp), LEAGUE, SEASON)["Marker"], "w3")

    def test_missing_index_is_unavailable_not_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(pub.ScheduleOutlookPublishError):
                pub.latest_snapshot(Path(tmp), LEAGUE, SEASON)

    def test_hash_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            write_product(Path(tmp), tamper=True)
            with self.assertRaises(pub.ScheduleOutlookPublishError):
                pub.latest_snapshot(Path(tmp), LEAGUE, SEASON)

    def test_gap_in_cutoffs_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            write_product(Path(tmp), weeks=4, drop_index_entry=1)
            with self.assertRaises(pub.ScheduleOutlookPublishError):
                pub.latest_snapshot(Path(tmp), LEAGUE, SEASON)


class WriterTests(unittest.TestCase):
    def test_semantic_noop_and_timestamp_only_on_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "public" / "data").mkdir(parents=True)
            now = datetime(2030, 1, 1, tzinfo=timezone.utc)
            first = Writer(root, now)
            first.put("ScheduleOutlook.json", {"A": 1}, "ScheduleOutlook")
            self.assertIn("public/data/Timestamps.json", first.finish())
            second = Writer(root, now)
            second.put("ScheduleOutlook.json", {"A": 1}, "ScheduleOutlook")
            self.assertEqual(second.finish(), [])


if __name__ == "__main__":
    unittest.main()
