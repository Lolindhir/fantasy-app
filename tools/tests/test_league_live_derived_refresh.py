"""League Live incremental Shared Derived refresh (Issue #471, step 3): scope and fail-soft behaviour."""
from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import league_live_derived_refresh as refresh  # noqa: E402

ROOT = Path("/unused")


class RefreshTests(unittest.TestCase):
    def run_refresh(self, *, weeks, materialize_side_effect=None, history_side_effect=None):
        history = patch.object(
            refresh, "materialize_league_history",
            side_effect=history_side_effect or (lambda *a, **k: {"Seasons": [{"Written": 0}]}),
        )
        discover = patch.object(refresh, "discover_finalized_weeks", return_value=weeks)
        twp = patch.object(
            refresh, "materialize",
            side_effect=materialize_side_effect or (lambda *a, **k: {"Changed": True}),
        )
        with patch.object(refresh, "list_league_ids", return_value=["lg-a", "lg-b"]), \
                patch.object(refresh, "data_meta_root", return_value=ROOT), \
                patch.object(refresh, "data_derived_dir", return_value=ROOT), \
                patch.object(refresh, "current_season", return_value=2030), \
                history as history_mock, discover as discover_mock, twp as twp_mock, \
                redirect_stderr(io.StringIO()) as err:
            result = refresh.refresh(ROOT)
        return result, history_mock, discover_mock, twp_mock, err.getvalue()

    def test_every_league_and_only_current_season_newest_week(self):
        weeks = [("lg-a", 2030, 1), ("lg-a", 2030, 3), ("lg-a", 2030, 2)]
        result, history, discover, twp, _ = self.run_refresh(weeks=weeks)
        self.assertEqual(4, history.call_count)  # two products for each of two leagues
        for call in history.call_args_list:
            self.assertEqual([2030], call.args[4])
            self.assertFalse(call.args[5])
        self.assertEqual(2, discover.call_count)
        for call in discover.call_args_list:
            self.assertEqual([2030], call.kwargs["seasons"])
        # lg-b has no scored week in the (shared) fake result: only lg-a's newest week is written
        twp.assert_called_once_with(ROOT, "lg-a", 2030, 3, write=True, require_pwf=False)
        statuses = {(r["CanonicalLeagueID"], r["Product"]): r["Status"] for r in result}
        self.assertEqual("changed", statuses[("lg-a", "team-week-performance")])
        self.assertEqual("no-scored-week", statuses[("lg-b", "team-week-performance")])

    def test_pwf_mismatch_is_reported_as_warning_without_blocking_sleeper_awards(self):
        result, _, _, twp, err = self.run_refresh(
            weeks=[("lg-a", 2030, 4)],
            materialize_side_effect=lambda *a, **k: {
                "Changed": True,
                "PlayerWeekFantasyParity": {
                    "State": "mismatch", "Reason": "Sleeper=26.28 PWF=26.18",
                },
            },
        )
        twp.assert_called_once_with(ROOT, "lg-a", 2030, 4,
                                    write=True, require_pwf=False)
        award = next(x for x in result
                     if x["Product"] == "team-week-performance" and x["CanonicalLeagueID"] == "lg-a")
        self.assertEqual("changed", award["Status"])
        self.assertEqual("mismatch", award["PlayerWeekFantasyParity"]["State"])
        self.assertIn("Independent player scoring differs from Sleeper", err)
        self.assertIn("Sleeper=26.28 PWF=26.18", err)

    def test_unready_week_is_a_warning_and_never_raises(self):
        result, _, _, _, err = self.run_refresh(
            weeks=[("lg-a", 2030, 4), ("lg-b", 2030, 4)],
            materialize_side_effect=ValueError("not final"),
        )
        blocked = [r for r in result if r["Status"] == "blocked"]
        self.assertEqual(2, len(blocked))
        self.assertIn("::warning title=TeamWeekPerformance not refreshed", err)

    def test_history_failure_keeps_last_good_file_and_warns(self):
        result, _, _, twp, err = self.run_refresh(
            weeks=[("lg-a", 2030, 1)], history_side_effect=RuntimeError("boom"),
        )
        history_rows = [r for r in result if r["Product"].startswith("league-")]
        self.assertTrue(history_rows and all(r["Status"] == "blocked" for r in history_rows))
        self.assertIn("::warning title=league-transactions not refreshed", err)
        twp.assert_called()  # an independent product still runs


class LeagueLiveStepOrderTests(unittest.TestCase):
    def test_products_before_consumers(self):
        workflow = (TOOLS.parent / ".github/workflows/league-live.yml").read_text(encoding="utf-8")
        steps = [
            "python3 tools/league_live_derived_refresh.py",
            # PlayerWeekFantasy/MatchupProjections no longer depend on an App file (ADR-075), so they precede the App files
            "python3 tools/player_week_fantasy_refresh.py",
            # WeeklyRecaps (RequestLeaguePublication) reads Matchups.json
            "python3 tools/matchup_context_app_publish.py write",
            "python3 tools/league_history_app_publish.py write",
            "pwsh ./public/requests/RequestLeaguePublication.ps1",
        ]
        positions = [workflow.index(step) for step in steps]
        self.assertEqual(sorted(positions), positions)


if __name__ == "__main__":
    unittest.main()
