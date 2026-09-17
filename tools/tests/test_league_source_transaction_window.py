from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from league_source_data_lib.transaction_window import (  # noqa: E402
    load_persisted_current_league_payload,
    resolve_current_transaction_window,
)


class CurrentTransactionWindowTests(unittest.TestCase):
    def _root(self) -> tuple[tempfile.TemporaryDirectory, Path]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        schedule = root / "source-data" / "nfl" / "schedules" / "2026.json"
        schedule.parent.mkdir(parents=True)
        schedule.write_text(
            json.dumps(
                {
                    "SchemaVersion": 2,
                    "Season": 2026,
                    "Games": [
                        {
                            "GameID": f"2026_{week:02d}_A_B",
                            "GameType": "REG",
                            "Week": week,
                        }
                        for week in range(1, 19)
                    ],
                }
            ),
            encoding="utf-8",
        )
        manifest = root / "source-data" / "leagues" / "test-league" / "manifest.json"
        manifest.parent.mkdir(parents=True)
        manifest.write_text(
            json.dumps(
                {
                    "schemaVersion": 1,
                    "CanonicalLeagueID": "test-league",
                    "CurrentCanonicalLeagueSeasonID": "test-league-2026",
                    "CurrentProviderLeagueID": "2000000000000000000",
                    "Seasons": [
                        {
                            "CanonicalLeagueSeasonID": "test-league-2026",
                            "Season": 2026,
                            "ProviderMappings": [
                                {
                                    "Provider": "Sleeper",
                                    "ProviderLeagueID": "2000000000000000000",
                                }
                            ],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        return temporary, root

    @staticmethod
    def _payload(*, status: str = "in_season", leg=7, last_scored_leg=6) -> dict:
        return {
            "league_id": "2000000000000000000",
            "season": "2026",
            "status": status,
            "settings": {
                "leg": leg,
                "last_scored_leg": last_scored_leg,
            },
        }

    def test_current_week_plus_previous_week_is_source_owned_window(self) -> None:
        temporary, root = self._root()
        try:
            window = resolve_current_transaction_window(
                root,
                "test-league",
                "2000000000000000000",
                self._payload(leg=7, last_scored_leg=6),
            )
            self.assertEqual(window["Season"], 2026)
            self.assertEqual(window["CurrentWeek"], 7)
            self.assertEqual(window["Weeks"], [6, 7])
            self.assertEqual(window["WeekCeiling"], 18)
            self.assertEqual(window["Evidence"], "settings.leg")
        finally:
            temporary.cleanup()

    def test_week_one_has_no_week_zero_partition(self) -> None:
        temporary, root = self._root()
        try:
            window = resolve_current_transaction_window(
                root,
                "test-league",
                "2000000000000000000",
                self._payload(leg=1, last_scored_leg=0),
            )
            self.assertEqual(window["Weeks"], [1])
        finally:
            temporary.cleanup()

    def test_last_scored_leg_is_fallback_when_leg_is_not_positive(self) -> None:
        temporary, root = self._root()
        try:
            window = resolve_current_transaction_window(
                root,
                "test-league",
                "2000000000000000000",
                self._payload(leg=0, last_scored_leg=4),
            )
            self.assertEqual(window["CurrentWeek"], 5)
            self.assertEqual(window["Weeks"], [4, 5])
            self.assertEqual(window["Evidence"], "settings.last_scored_leg+1")
        finally:
            temporary.cleanup()

    def test_completed_league_uses_schedule_ceiling(self) -> None:
        temporary, root = self._root()
        try:
            window = resolve_current_transaction_window(
                root,
                "test-league",
                "2000000000000000000",
                self._payload(status="complete", leg=1, last_scored_leg=1),
            )
            self.assertEqual(window["CurrentWeek"], 18)
            self.assertEqual(window["Weeks"], [17, 18])
            self.assertEqual(window["Evidence"], "league.status=complete")
        finally:
            temporary.cleanup()

    def test_provider_week_is_bounded_by_canonical_schedule(self) -> None:
        temporary, root = self._root()
        try:
            window = resolve_current_transaction_window(
                root,
                "test-league",
                "2000000000000000000",
                self._payload(leg=99, last_scored_leg=98),
            )
            self.assertEqual(window["CurrentWeek"], 18)
            self.assertEqual(window["Weeks"], [17, 18])
        finally:
            temporary.cleanup()

    def test_provider_identity_drift_fails_closed(self) -> None:
        temporary, root = self._root()
        try:
            payload = self._payload()
            payload["league_id"] = "different"
            with self.assertRaisesRegex(ValueError, "does not match"):
                resolve_current_transaction_window(
                    root,
                    "test-league",
                    "2000000000000000000",
                    payload,
                )
        finally:
            temporary.cleanup()

    def test_manifest_identity_drift_fails_closed(self) -> None:
        temporary, root = self._root()
        try:
            manifest = root / "source-data" / "leagues" / "test-league" / "manifest.json"
            value = json.loads(manifest.read_text(encoding="utf-8"))
            value["CurrentProviderLeagueID"] = "different"
            manifest.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "provider identity drift"):
                resolve_current_transaction_window(
                    root,
                    "test-league",
                    "2000000000000000000",
                    self._payload(),
                )
        finally:
            temporary.cleanup()

    def test_persisted_current_league_payload_is_reusable_for_materialization(self) -> None:
        temporary, root = self._root()
        try:
            raw = (
                root
                / "source-data"
                / "providers"
                / "sleeper"
                / "leagues"
                / "2000000000000000000"
                / "league.json"
            )
            raw.parent.mkdir(parents=True)
            raw.write_text(json.dumps(self._payload()), encoding="utf-8")
            loaded = load_persisted_current_league_payload(
                root,
                "2000000000000000000",
            )
            self.assertEqual(loaded["league_id"], "2000000000000000000")
            self.assertEqual(loaded["settings"]["leg"], 7)
        finally:
            temporary.cleanup()


if __name__ == "__main__":
    unittest.main()
