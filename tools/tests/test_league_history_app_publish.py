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
        self.assertEqual("1.01", current[0]["Picks"][0]["DisplayPick"])

    def test_past_file_holds_only_completed_drafts_without_start_times(self):
        past = publish.app_drafts(self.by_season, 2026)["past"]
        self.assertEqual([2026], list(past))
        self.assertIsInstance(past[2026], list)  # always a list, also for exactly one completed draft
        self.assertEqual(1, len(past[2026]))
        draft = past[2026][0]
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


class SlimContractTests(unittest.TestCase):
    """Issue #999 step 6: the App contract omits the approved fields and keeps the explicitly retained ones."""

    def setUp(self):
        drafts = build([provider_draft("d1", "2026", "complete", name="rookie")], open_count=1)
        self.current = publish.app_drafts(drafts_by_season(drafts), 2026)["current"]

    def test_draft_and_pick_fields_are_slimmed(self):
        for draft in self.current:
            for name in publish.DRAFT_DROPPED + ("LeagueID",):
                self.assertNotIn(name, draft)
            self.assertNotIn("Teams", draft["Settings"])
            self.assertNotIn("SleeperDraftID", draft)
            for pick in draft["Picks"]:
                for name in publish.PICK_DROPPED:
                    self.assertNotIn(name, pick)
                self.assertIn("IsCurrentlyTraded", pick)
                self.assertIn("TradeHistory", pick)

    def test_transaction_fields_are_slimmed_and_trade_history_keeps_its_entries(self):
        transaction = {"TransactionID": "1", "Status": "complete", "Week": 3, "Source": "Sleeper", "DraftPicks": [
            {"PickKey": "k", "Round": 1, "PositionInRound": 3, "OverallPick": 3, "Season": "2026", "DraftKey": "2026_Rookie",
             "DraftCode": "R", "DraftSource": "Sleeper", "PickStatus": "Open", "SleeperDraftID": "d", "DraftInstance": 1,
             "SleeperPickNo": None},
        ]}
        result = publish.app_transaction(transaction)
        self.assertEqual("complete", result["Status"])  # Angular filters on it
        self.assertEqual((3, "Sleeper"), (result["Week"], result["Source"]))
        self.assertEqual("1.03", result["DraftPicks"][0]["DisplayPick"])
        for name in publish.TRANSACTION_PICK_DROPPED:
            self.assertNotIn(name, result["DraftPicks"][0])

    def test_trade_history_entries_lose_only_the_source_fields(self):
        pick = {"PickKey": "k", "Round": 1, "TradeHistory": [
            {"TransactionID": "t", "Source": "Sleeper", "DraftSource": "Sleeper", "CreatedAt": 1, "EffectiveAt": 2, "CreatedDate": "d",
             "PreviousOwnerRosterID": 1, "NewOwnerRosterID": 2}]}
        entry = publish._app_pick(pick)["TradeHistory"][0]
        self.assertEqual({"TransactionID", "CreatedAt", "EffectiveAt", "CreatedDate", "PreviousOwnerRosterID", "NewOwnerRosterID"}, set(entry))
        self.assertEqual(2, entry["EffectiveAt"])


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


class HistoricalReferenceDeliveryTests(unittest.TestCase):
    def test_tyreek_drop_and_brady_draft_are_delivered_without_current_players(self):
        from derived_data_lib.league_history import build_history
        from league_history_sources import load_inputs

        root = TOOLS.parent
        inputs = load_inputs(root, "nfl-reise")
        history = build_history(inputs)
        self.assertFalse(history.unresolved)
        references = publish.build_player_references(root, "nfl-reise", history)
        rendered = publish.render(history, inputs.league_year, references)

        tyreek = [
            transaction["PlayerRefs"]["3321"]
            for transaction in rendered["Transactions"]["current"]
            if "3321" in (transaction.get("Drops") or {})
        ]
        self.assertTrue(tyreek, "Historical Tyreek Hill drop is missing")
        self.assertTrue(all(ref["Name"] == "Tyreek Hill" and ref["Position"] == "WR" for ref in tyreek))
        self.assertTrue(all(set(ref) == {"Name", "Position", "Picture"} for ref in tyreek))

        picks = [
            pick for draft in rendered["Drafts"]["past"][2024] for pick in draft["Picks"]
            if pick.get("PlayerID") == "167" and pick.get("PlayerName") == "Tom Brady"
        ]
        self.assertTrue(picks, "Canonical 2024 Brady draft pick must remain published")
        self.assertTrue(all(pick["PlayerRef"]["Name"] == "Tom Brady" and
                            pick["PlayerRef"]["Position"] == "QB" for pick in picks))
        self.assertTrue(all("Team" not in pick["PlayerRef"] for pick in picks))

    def test_transaction_pick_uses_draft_season_not_transaction_season(self):
        old = {"Name": "Old Player", "Position": "RB", "Picture": None}
        new = {"Name": "New Player", "Position": "TE", "Picture": None}
        transaction = {"TransactionID": "trade", "Adds": {}, "Drops": {}, "DraftPicks": [
            {"PickKey": "2024_Rookie_R1_OO1", "Round": 1, "Season": "2024",
             "DraftKey": "2024_Rookie", "PlayerID": "9", "PlayerName": "Old Player"}
        ]}
        result = publish.app_transaction(transaction, {},
                                         {2024: {"9": old}, 2026: {"9": new}})
        self.assertEqual(old, result["DraftPicks"][0]["PlayerRef"])
        self.assertEqual("Old Player", result["DraftPicks"][0]["PlayerName"])

    def test_unknown_player_never_becomes_an_invented_name(self):
        transaction = {"TransactionID": "x", "Adds": {}, "Drops": {"q": 1}, "DraftPicks": []}
        result = publish.app_transaction(
            transaction, {"q": {"Name": None, "Position": None, "Picture": None}})
        self.assertNotIn("PlayerRefs", result)


class ComparisonTests(unittest.TestCase):
    def test_comparison_is_exact_about_types_and_list_order_but_not_key_order(self):
        self.assertEqual([], publish._difference({"a": 1, "b": [1, 2]}, {"b": [1, 2], "a": 1}))
        self.assertTrue(publish._difference({"a": 1}, {"a": True}))
        self.assertTrue(publish._difference({"a": 1}, {"a": 1.0}))
        self.assertTrue(publish._difference([1, 2], [2, 1]))
        self.assertTrue(publish._difference({"a": 1}, {"a": 1, "b": 2}))


class WriteTests(unittest.TestCase):
    def rendered(self, name="a"):
        return {
            "Transactions": {"current": [{"TransactionID": name}], "past": {"2025": [{"TransactionID": "p"}]}},
            "Drafts": {"current": [{"DraftKey": name}], "past": {"2025": [{"DraftKey": "old"}]}},
        }

    def test_write_is_semantic_noop_and_stamps_only_changed_current_files(self):
        import json
        import tempfile
        from datetime import datetime, timezone

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "public" / "data").mkdir(parents=True)
            (root / "public" / "data" / "Timestamps.json").write_text('{"League": "x"}', encoding="utf-8")
            first = publish.write_files(root, self.rendered(), datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc))
            self.assertIn("public/data/Timestamps.json", first)
            stamps = json.loads((root / "public/data/Timestamps.json").read_text(encoding="utf-8"))
            self.assertEqual("2026-01-02T03:04:05Z", stamps["Transactions"])
            self.assertEqual("x", stamps["League"])
            self.assertEqual([], publish.write_files(root, self.rendered()))
            second = publish.write_files(root, self.rendered("b"), datetime(2027, 1, 1, tzinfo=timezone.utc))
            self.assertEqual("2027-01-01T00:00:00Z", json.loads((root / "public/data/Timestamps.json").read_text(encoding="utf-8"))["Drafts"])
            self.assertNotIn("public/data/past_seasons/Drafts/Drafts_2025.json", second)



class WeeklyLeagueDerivedPublicationTests(unittest.TestCase):
    """Keep both existing LeagueHistory products inside one classified weekly writer."""

    def test_existing_weekly_writer_publishes_both_derived_families_and_app(self):
        workflow = (TOOLS.parent / ".github/workflows/update-transactions.yml").read_text(encoding="utf-8")
        self.assertIn("--scope transactions", workflow)
        self.assertIn("--path public/data", workflow)
        self.assertIn("--path data-derived/league-transactions", workflow)
        self.assertIn("--path data-derived/league-drafts", workflow)
        self.assertIn("bash -euo pipefail -c", workflow)
        first = workflow.index("materialize --product league-transactions")
        second = workflow.index("materialize --product league-drafts")
        consumer = workflow.index("league_history_app_publish.py write --fail-on-error")
        self.assertLess(first, second)
        self.assertLess(second, consumer)
        self.assertIn("schedule_archive.py write", workflow)
        self.assertIn("RequestPastSeasonsIndex.ps1", workflow)

    def test_weekly_writer_covers_every_league_and_summarizes_each_product(self):
        workflow = (TOOLS.parent / ".github/workflows/update-transactions.yml").read_text(encoding="utf-8")
        self.assertNotIn("--league", workflow)
        self.assertIn("Summarize Derived products", workflow)
        for product in ("league-transactions", "league-drafts"):
            self.assertIn(f"derived-summary/{product}.json", workflow)


    def test_isolated_manual_drafts_mode_reuses_weekly_writer_with_no_scheduler_change(self):
        """#1263 G5: keep manual Drafts restore isolated, without a second workflow file."""
        import yaml

        workflow_path = TOOLS.parent / ".github/workflows/update-transactions.yml"
        text = workflow_path.read_text(encoding="utf-8")
        definition = yaml.safe_load(text)
        events = definition.get("on", definition.get(True))
        manual = events["workflow_dispatch"]["inputs"]["mode"]
        self.assertEqual("all", manual["default"])
        self.assertEqual(["all", "drafts"], manual["options"])
        self.assertFalse((TOOLS.parent / ".github/workflows/update-drafts.yml").exists())
        steps = definition["jobs"]["update"]["steps"]
        full_step = next(step for step in steps if "historical League Derived" in step.get("name", ""))
        drafts_step = next(step for step in steps if "Drafts-only" in step.get("name", ""))
        self.assertIn("inputs.mode != 'drafts'", full_step["if"])
        self.assertIn("inputs.mode == 'drafts'", drafts_step["if"])
        for command in (
            "--scope drafts",
            "--path data-derived/league-drafts",
            "derived_data.py materialize --product league-drafts",
            "league_history_app_publish.py write --fail-on-error",
            "RequestPastSeasonsIndex.ps1",
        ):
            self.assertIn(command, drafts_step["run"])
        self.assertIn("inputs.mode != 'drafts'", next(
            step for step in steps if step.get("name") == "Summarize Derived products"
        )["if"])
        self.assertIn("repository_dispatch", events)

    def test_no_new_scheduler_target_or_live_ten_minute_history_job(self):
        import json
        schedules = json.loads(
            (TOOLS.parent / ".github/workflow-schedules.json").read_text(encoding="utf-8")
        )
        targets = [item for item in schedules["targets"] if item["id"] == "transactions"]
        self.assertEqual(1, len(targets))
        self.assertEqual("update-transactions.yml", targets[0]["workflow"])
        self.assertEqual(["5 4 * * 3"], targets[0]["cron"])
        league_live = (TOOLS.parent / ".github/workflows/league-live.yml").read_text(encoding="utf-8")
        self.assertNotIn("derived_data.py materialize --product league-transactions", league_live)
        self.assertNotIn("derived_data.py materialize --product league-drafts", league_live)

if __name__ == "__main__":
    unittest.main()
