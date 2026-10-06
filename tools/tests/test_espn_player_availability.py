"""ESPN player availability source snapshot (#347): semantic no-op, stable timestamps, fail-closed."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

import espn_player_availability as eap  # noqa: E402


def payload(statuses: dict[str, str | None]) -> dict:
    return {"players": [{"player": {"id": int(pid), "injuryStatus": status}} for pid, status in statuses.items()]}


def many(overrides: dict[str, str | None] | None = None, count: int = 400) -> dict:
    base = {str(1000 + i): "ACTIVE" for i in range(count)}
    base.update(overrides or {})
    return payload(base)


class EspnPlayerAvailabilityTest(unittest.TestCase):
    def sync(self, root: Path, data: dict, at: str, season: int = 2030) -> bool:
        return eap.sync(root, season, data, at)

    def test_second_identical_run_is_a_semantic_no_op(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertTrue(self.sync(root, many(), "2030-09-01T10:00:00Z"))
            self.assertFalse(self.sync(root, many(), "2030-09-01T10:10:00Z"))

    def test_status_since_is_stable_until_status_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.sync(root, many({"1001": "QUESTIONABLE"}), "2030-09-01T10:00:00Z")
            self.sync(root, many({"1001": "QUESTIONABLE", "1002": "OUT"}), "2030-09-01T10:10:00Z")
            self.sync(root, many({"1001": "OUT", "1002": "OUT"}), "2030-09-01T10:20:00Z")
            rows = {r["ESPNPlayerID"]: r for r in eap.load_json(root / eap.SNAPSHOT_PATH)["Players"]}
            self.assertEqual("2030-09-01T10:20:00Z", rows["1001"]["StatusSinceUtc"])
            self.assertEqual("2030-09-01T10:10:00Z", rows["1002"]["StatusSinceUtc"])
            self.assertEqual("2030-09-01T10:00:00Z", rows["1003"]["StatusSinceUtc"])

    def test_missing_status_is_none_not_a_default(self) -> None:
        parsed = eap.parse_players(payload({"1": None, "2": "out"}))
        self.assertEqual({"1": None, "2": "OUT"}, parsed)

    def test_season_change_restarts_timestamps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.sync(root, many(), "2030-09-01T10:00:00Z", season=2030)
            self.sync(root, many(), "2031-09-01T10:00:00Z", season=2031)
            rows = eap.load_json(root / eap.SNAPSHOT_PATH)["Players"]
            self.assertTrue(all(r["StatusSinceUtc"] == "2031-09-01T10:00:00Z" for r in rows))

    def test_implausibly_small_response_keeps_last_known_good(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.sync(root, many(), "2030-09-01T10:00:00Z")
            before = (root / eap.SNAPSHOT_PATH).read_text(encoding="utf-8")
            with self.assertRaises(ValueError):
                self.sync(root, payload({"1": "OUT"}), "2030-09-01T10:10:00Z")
            self.assertEqual(before, (root / eap.SNAPSHOT_PATH).read_text(encoding="utf-8"))

    def test_malformed_and_conflicting_responses_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            eap.parse_players({"unexpected": []})
        conflicting = {"players": [{"player": {"id": 5, "injuryStatus": "OUT"}}, {"player": {"id": 5, "injuryStatus": "ACTIVE"}}]}
        with self.assertRaises(ValueError):
            eap.parse_players(conflicting)


if __name__ == "__main__":
    unittest.main()
