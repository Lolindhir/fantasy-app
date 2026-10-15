"""Tests for the League history consumer generator (Issue #999 step 4).

The exact comparison against the committed public/data files is the command
`python3 tools/league_history_app_publish.py compare`; it is deliberately not a unit test because the
committed App files and the canonical sources are refreshed by different workflows and can differ for a
few minutes. These tests pin the presentation rules with constructed leagues.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from derived_data_lib.league_history import HistoryResult  # noqa: E402
import league_history_app_publish as publish  # noqa: E402
from test_league_drafts import CONFIGS, TEAMS, build, provider_draft, standings  # noqa: E402
from derived_data_lib.league_drafts import build_drafts  # noqa: E402


def drafts_by_season(drafts):
    result = {}
    for draft in drafts:
        result.setdefault(int(draft["Season"]), []).append(draft)
    return result


class DisplayTests(unittest.TestCase):
    def test_display_pick(self):
        self.assertEqual("Round 4", publish.display_pick(4, None))
        self.assertEqual("1.01", publish.display_pick(1, 1))
        self.assertEqual("12.10", publish.display_pick(12, 10))

    def test_display_status(self):
        self.assertEqual("Completed", publish.display_status("Complete", "2026", 2026))
        self.assertEqual("Upcoming", publish.display_status("Virtual", "2026", 2026))
        self.assertEqual("Future", publish.display_status("Virtual", "2027", 2026))
        self.assertEqual("Live", publish.display_status("Drafting", "2026", 2026))
        self.assertEqual("Upcoming", publish.display_status("PreDraft", "2026", 2026))

    def test_type_names(self):
        self.assertEqual("Free Agent", publish.display_type("Free_Agent"))
        self.assertEqual("FA", publish.type_abbreviation("Free_Agent"))


class DraftFileTests(unittest.TestCase):
    def setUp(self):
        drafts = build(
            [provider_draft("d1", "2026", "complete", name="rookie"), provider_draft("d2", "2026", "pre_draft", name="free agent")],
            open_count=1,
        )
        self.by_season = drafts_by_season(drafts)

    def test_current_file_holds_current_and_future_drafts_with_start_times(self):
        current = publish.app_drafts(self.by_season, 2026)["current"]
        self.assertEqual(["2026_Rookie", "2026_Free_Agent", "2027_Rookie"], [d["DraftKey"] for d in current])
        self.assertEqual(("Future", "Virtual"), (current[2]["DisplayStatus"], current[2]["Status"]))
        self.assertIn("DraftStartTimeUtc", current[0])
        self.assertEqual("Completed", current[0]["DisplayStatus"])
        self.assertEqual("2026 Free Agent", current[1]["DisplayDraftKey"])
        self.assertEqual("2026 FA", current[1]["DisplayAbrDraftKey"])
        self.assertEqual("p2026", current[0]["LeagueID"])
        self.assertEqual("1.01", current[0]["Picks"][0]["DisplayPick"])

    def test_past_file_holds_only_completed_drafts_without_start_times(self):
        past = publish.app_drafts(self.by_season, 2026)["past"]
        self.assertEqual([2026], list(past))
        draft = past[2026]  # exactly one completed draft: written as a plain object like ConvertTo-Json does
        self.assertIsInstance(draft, dict)
        self.assertNotIn("SleeperStartTime", draft)
        self.assertNotIn("DraftStartTimeUtc", draft)
        self.assertEqual("2026 Rookie", draft["DisplayDraftKey"])

    def test_two_completed_drafts_of_one_type_get_occurrence_suffixes_in_a_list(self):
        configs = [dict(CONFIGS[0]), dict(CONFIGS[0], DraftInstance=2, DraftNo=3), CONFIGS[1]]
        provider = [provider_draft("d1", "2026", "complete", name="rookie"), provider_draft("d2", "2026", "complete", name="rookie")]
        provider[1]["created"] = 2
        by_season = drafts_by_season(build(provider, configs=configs, open_count=1))
        past = publish.app_drafts(by_season, 2026)["past"][2026]
        self.assertIsInstance(past, list)
        self.assertEqual(["2026 Rookie #1", "2026 Rookie #2"], [d["DisplayDraftKey"] for d in past])


class TransactionFileTests(unittest.TestCase):
    def test_display_pick_only_for_resolved_picks_and_keys_are_ordered(self):
        transaction = {"TransactionID": "1", "DraftPicks": [
            {"PickKey": "2026_Rookie_R1_OO1", "Round": 1, "PositionInRound": 3, "Season": "2026", "DraftKey": "2026_Rookie"},
            {"PickKey": None, "Round": 2, "PositionInRound": None, "Season": "2027", "DraftKey": None},
        ]}
        picks = publish.app_transaction(transaction)["DraftPicks"]
        self.assertEqual("1.03", picks[0]["DisplayPick"])
        self.assertNotIn("DisplayPick", picks[1])
        self.assertEqual(["DraftKey", "Season", "Round"], list(picks[0])[:3])

    def test_current_and_past_split_by_league_year(self):
        by_season = {2025: [{"TransactionID": "a", "DraftPicks": []}], 2026: [{"TransactionID": "b", "DraftPicks": []}]}
        result = publish.app_transactions(by_season, 2026)
        self.assertEqual(["b"], [t["TransactionID"] for t in result["current"]])
        self.assertEqual({2025}, set(result["past"]))


class ComparisonTests(unittest.TestCase):
    def test_comparison_is_exact_about_types_and_list_order_but_not_key_order(self):
        self.assertEqual([], publish._difference({"a": 1, "b": [1, 2]}, {"b": [1, 2], "a": 1}))
        self.assertTrue(publish._difference({"a": 1}, {"a": True}))
        self.assertTrue(publish._difference({"a": 1}, {"a": 1.0}))
        self.assertTrue(publish._difference([1, 2], [2, 1]))
        self.assertTrue(publish._difference({"a": 1}, {"a": 1, "b": 2}))


if __name__ == "__main__":
    unittest.main()
