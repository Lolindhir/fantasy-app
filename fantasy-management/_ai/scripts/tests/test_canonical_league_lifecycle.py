from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

SCRIPT_DIRECTORY = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIRECTORY))

TOOLS_DIRECTORY = Path(__file__).resolve().parents[4] / "tools"
if str(TOOLS_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIRECTORY))

import canonical_league_lifecycle as module  # noqa: E402


class CanonicalLeagueLifecycleTests(unittest.TestCase):
    def test_delegates_to_shared_function_with_utc_instant(self) -> None:
        root = Path(__file__).resolve().parents[4]
        sentinel = {"Status": "In-Season"}
        with mock.patch("derived_data_lib.league_lifecycle.resolve_lifecycle", return_value=sentinel) as resolve:
            result = module.resolve_lifecycle_state(root, "league-x", 2026, "2026-09-03T08:00:00Z")
        self.assertIs(sentinel, result)
        args = resolve.call_args.args
        self.assertEqual(("league-x", 2026), args[1:3])
        self.assertEqual(datetime(2026, 9, 3, 8, 0, tzinfo=timezone.utc), args[3])

    def test_lifecycle_error_becomes_unavailable(self) -> None:
        root = Path(__file__).resolve().parents[4]
        from derived_data_lib.league_lifecycle import LifecycleError

        with mock.patch("derived_data_lib.league_lifecycle.resolve_lifecycle", side_effect=LifecycleError("x")):
            with self.assertRaises(module.LeagueLifecycleUnavailable):
                module.resolve_lifecycle_state(root, "league-x", 2026, "2026-09-03T08:00:00Z")

    def test_missing_or_invalid_instant_fails_closed(self) -> None:
        root = Path(__file__).resolve().parents[4]
        for bad in (None, "", "not-a-date"):
            with self.assertRaises(module.LeagueLifecycleUnavailable):
                module.resolve_lifecycle_state(root, "league-x", 2026, bad)


if __name__ == "__main__":
    unittest.main()
