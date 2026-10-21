"""Tests for the LeagueDrafts stage (league-history.yaml, ADR-057, Issue #999 step 3).

Constructed leagues pin the ported PowerShell semantics (order, trades, pick results, open future drafts,
pipeline write-back); one repository-level test checks invariants of the real canonical data without
wiring any concrete player, team or draft into the assertions.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
REPO = TOOLS.parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from derived_data_lib.league_drafts import DraftBuildError, build_drafts  # noqa: E402
from derived_data_lib.league_history import LeagueHistoryInputs, build_history  # noqa: E402

CONFIGS = [
    {"DraftType": "Rookie", "DraftInstance": 1, "DraftNo": 1, "Rounds": 2, "SleeperFuturePickPool": True,
     "OrderSource": "PreviousPlayoffs"},
    {"DraftType": "Free_Agent", "DraftInstance": 1, "DraftNo": 2, "Rounds": 2, "OrderSource": "AllTime", "Order": "Descending"},
]
TEAMS = [1, 2, 3]


def provider_draft(draft_id, season, status, kind="linear", name="", slots=(2, 3, 1), start=1783526479213):
    return {
        "draft_id": draft_id, "season": season, "type": kind, "status": status, "start_time": start,
        "created": 1, "settings": {"rounds": 2}, "metadata": {"name": name},
        "draft_order": {}, "slot_to_roster_id": {str(i + 1): rid for i, rid in enumerate(slots)},
    }


def result(draft_id, pick_no, roster, player=None, by="u"):
    return {"draft_id": draft_id, "pick_no": pick_no, "roster_id": roster, "player_id": player, "picked_by": by,
            "metadata": {"first_name": "First", "last_name": f"P{pick_no}"}}


def movement(transaction_id, key, round_no, original, previous, new, created=10, source="Sleeper"):
    return {
        "Source": source, "TransactionID": transaction_id, "Status": "complete", "CreatedAt": created,
        "CreatedDate": "2026-01-01",
        "DraftPicks": [{"DraftKey": key, "DraftSource": "Sleeper", "Season": key.split("_", 1)[0], "Round": round_no,
                        "OriginalOwnerRosterID": original, "PreviousOwnerRosterID": previous, "NewOwnerRosterID": new}],
    }


def standings(playoffs_2025=((1, 3), (2, 1), (3, 2)), all_time=((1, 2), (2, 3), (3, 1))):
    return [
        {"Season": "2025", "Playoffs": [{"Place": place, "TeamID": team} for place, team in playoffs_2025]},
        {"Season": "AllTime", "Playoffs": [{"Place": place, "TeamID": team} for place, team in all_time]},
    ]


def build(drafts=(), picks=None, transactions=(), configs=CONFIGS, open_count=2, loader=None, league_year=2026,
          seasons=(2026,)):
    payload = {"Drafts": list(drafts), "PicksByDraftID": picks if picks is not None else {d["draft_id"]: [] for d in drafts}}
    return build_drafts(
        league_year=league_year, seasons=list(seasons), provider_league_ids={s: f"p{s}" for s in seasons},
        configs=configs, open_count=open_count, team_ids=TEAMS,
        standings_loader=loader if loader is not None else (lambda: standings()),
        payloads={s: payload for s in seasons}, transactions=list(transactions),
    )


def by_key(drafts):
    return {draft["DraftKey"]: draft for draft in drafts}


class OrderTests(unittest.TestCase):
    def test_linear_keeps_and_snake_reverses_the_provider_order_in_even_rounds(self):
        linear = build([provider_draft("d1", "2026", "pre_draft", name="rookie")])
        rookie = by_key(linear)["2026_Rookie"]
        self.assertEqual([2, 3, 1, 2, 3, 1], [p["OriginalOwnerRosterID"] for p in rookie["Picks"]])
        self.assertEqual([1, 2, 3, 4, 5, 6], [p["OverallPick"] for p in rookie["Picks"]])
        self.assertEqual(("Sleeper", "GeneratedFromSleeperOrderAndTrades", "Exact"),
                         (rookie["OrderSource"], rookie["PickSource"], rookie["OrderMode"]))
        snake = by_key(build([provider_draft("d1", "2026", "pre_draft", kind="snake", name="rookie")]))["2026_Rookie"]
        self.assertEqual([2, 3, 1, 1, 3, 2], [p["OriginalOwnerRosterID"] for p in snake["Picks"]])
        self.assertEqual([1, 2, 3, 1, 2, 3], [p["PositionInRound"] for p in snake["Picks"]])
        self.assertEqual("snake", snake["Settings"]["Type"])

    def test_draft_without_provider_order_uses_the_configured_standings_order(self):
        drafts = by_key(build([]))
        # Rookie: PreviousPlayoffs ascending by place -> 3, 1, 2; Free_Agent: AllTime descending -> 1, 3, 2
        self.assertEqual([3, 1, 2], [p["OriginalOwnerRosterID"] for p in drafts["2026_Rookie"]["Picks"][:3]])
        self.assertEqual([1, 3, 2], [p["OriginalOwnerRosterID"] for p in drafts["2026_Free_Agent"]["Picks"][:3]])
        self.assertEqual(("GeneratedFromConfiguredOrderAndTrades", "PreviousPlayoffs"),
                         (drafts["2026_Rookie"]["PickSource"], drafts["2026_Rookie"]["OrderSource"]))
        self.assertEqual("Virtual", drafts["2026_Rookie"]["Status"])
        self.assertIsNone(drafts["2026_Rookie"]["SleeperDraftID"])

    def test_order_map_selects_and_orders_by_mapped_value(self):
        configs = [dict(CONFIGS[0], OrderMap={"1": 2, "3": 1}), CONFIGS[1]]
        drafts = by_key(build([], configs=configs, open_count=1))
        self.assertEqual([2, 3], [p["OriginalOwnerRosterID"] for p in drafts["2026_Rookie"]["Picks"][:2]])  # place 3 (team 2) -> 1, place 1 (team 3) -> 2
        self.assertEqual(2, drafts["2026_Rookie"]["Settings"]["Teams"])

    def test_missing_ranking_or_duplicate_standing_fails_closed(self):
        with self.assertRaises(DraftBuildError):
            build([], loader=lambda: [])
        with self.assertRaises(DraftBuildError):
            build([], loader=lambda: standings() + standings())

    def test_future_drafts_are_round_only_with_sorted_teams(self):
        drafts = by_key(build([provider_draft("d1", "2026", "complete", name="rookie")]))
        future = drafts["2027_Rookie"]
        self.assertEqual(("RoundOnly", "UnknownFuture", "Virtual"), (future["OrderMode"], future["OrderSource"], future["Status"]))
        self.assertEqual([1, 2, 3, 1, 2, 3], [p["OriginalOwnerRosterID"] for p in future["Picks"]])
        self.assertTrue(all(p["PositionInRound"] is None and p["OverallPick"] is None for p in future["Picks"]))
        self.assertEqual("Virtual", future["DraftSource"])
        self.assertIsNone(future["SleeperStartTime"])

    def test_completed_current_draft_does_not_consume_an_open_slot(self):
        drafts = build([provider_draft("d1", "2026", "complete", name="rookie")], open_count=2)
        rookie_seasons = [d["Season"] for d in drafts if d["DraftType"] == "Rookie"]
        self.assertEqual(["2026", "2027", "2028"], rookie_seasons)  # 2026 complete + two open
        free_agent_seasons = [d["Season"] for d in drafts if d["DraftType"] == "Free_Agent"]
        self.assertEqual(["2026", "2027"], free_agent_seasons)  # 2026 is current (included), 2026 open + 2027 open

    def test_start_time_is_rendered_like_dotnet_round_trip_format(self):
        drafts = by_key(build([provider_draft("d1", "2026", "pre_draft", name="rookie", start=1783526479213)]))
        draft = drafts["2026_Rookie"]
        self.assertEqual(1783526479213, draft["SleeperStartTime"])
        self.assertEqual("2026-07-08T16:01:19.2130000Z", draft["DraftStartTimeUtc"])
        self.assertEqual("PreDraft", draft["Status"])

    def test_multiple_instances_of_one_type_get_their_own_keys(self):
        configs = [dict(CONFIGS[0]), dict(CONFIGS[0], DraftInstance=2, DraftNo=3), CONFIGS[1]]
        keys = {d["DraftKey"] for d in build([], configs=configs, open_count=1)}
        self.assertIn("2026_Rookie", keys)
        self.assertIn("2026_Rookie_2", keys)


class TradeAndResultTests(unittest.TestCase):
    def test_movements_apply_in_created_order_and_build_trade_history(self):
        txs = [
            movement("b", "2026_Rookie", 1, 2, 3, 1, created=20),
            movement("a", "2026_Rookie", 1, 2, 2, 3, created=10),
        ]
        rookie = by_key(build([provider_draft("d1", "2026", "pre_draft", name="rookie")], transactions=txs))["2026_Rookie"]
        pick = next(p for p in rookie["Picks"] if p["PickKey"] == "2026_Rookie_R1_OO2")
        self.assertEqual(1, pick["CurrentOwnerRosterID"])
        self.assertEqual(["a", "b"], [e["TransactionID"] for e in pick["TradeHistory"]])
        self.assertEqual((True, True, "Sleeper"), (pick["WasTraded"], pick["IsCurrentlyTraded"], pick["TradeSource"]))

    def test_effective_order_overrides_submission_order_for_pick_ownership(self):
        first = movement("a", "2026_Rookie", 1, 2, 2, 3, created=200)
        second = movement("b", "2026_Rookie", 1, 2, 3, 1, created=100)
        first["EffectiveAt"] = 300
        second["EffectiveAt"] = 400
        rookie = by_key(build([provider_draft("d1", "2026", "pre_draft", name="rookie")],
                              transactions=[first, second]))["2026_Rookie"]
        pick = next(p for p in rookie["Picks"] if p["PickKey"] == "2026_Rookie_R1_OO2")
        self.assertEqual(1, pick["CurrentOwnerRosterID"])
        self.assertEqual(["a", "b"], [row["TransactionID"] for row in pick["TradeHistory"]])
        self.assertEqual([300, 400], [row["EffectiveAt"] for row in pick["TradeHistory"]])

    def test_pick_traded_back_is_not_currently_traded(self):
        txs = [movement("a", "2026_Rookie", 1, 2, 2, 3, created=1), movement("b", "2026_Rookie", 1, 2, 3, 2, created=2)]
        rookie = by_key(build([provider_draft("d1", "2026", "pre_draft", name="rookie")], transactions=txs))["2026_Rookie"]
        pick = next(p for p in rookie["Picks"] if p["PickKey"] == "2026_Rookie_R1_OO2")
        self.assertEqual((True, False), (pick["WasTraded"], pick["IsCurrentlyTraded"]))

    def test_equal_round_swap_moves_both_picks_in_opposite_directions(self):
        txs = [movement("a", "2026_Rookie", 1, 1, 1, 2), movement("a", "2026_Rookie", 1, 2, 2, 1)]
        # one transaction carries both movements
        txs = [dict(txs[0], DraftPicks=txs[0]["DraftPicks"] + txs[1]["DraftPicks"])]
        rookie = by_key(build([provider_draft("d1", "2026", "pre_draft", name="rookie")], transactions=txs))["2026_Rookie"]
        owners = {p["PickKey"]: p["CurrentOwnerRosterID"] for p in rookie["Picks"] if p["Round"] == 1}
        self.assertEqual({"2026_Rookie_R1_OO1": 2, "2026_Rookie_R1_OO2": 1, "2026_Rookie_R1_OO3": 3}, owners)

    def test_other_status_and_other_drafts_are_ignored(self):
        pending = dict(movement("a", "2026_Rookie", 1, 1, 1, 2), Status="pending")
        other = movement("b", "2026_Free_Agent", 1, 1, 1, 3)
        rookie = by_key(build([provider_draft("d1", "2026", "pre_draft", name="rookie")], transactions=[pending, other]))["2026_Rookie"]
        self.assertTrue(all(not p["WasTraded"] for p in rookie["Picks"]))

    def test_movement_of_a_missing_pick_fails_closed(self):
        with self.assertRaises(DraftBuildError):
            build([provider_draft("d1", "2026", "pre_draft", name="rookie")], transactions=[movement("a", "2026_Rookie", 9, 1, 1, 2)])

    def test_results_set_player_owner_and_trade_source_of_unrecorded_trades(self):
        draft = provider_draft("d1", "2026", "complete", name="rookie")
        picks = {"d1": [result("d1", 1, 1, "pl1", "u1"), result("d1", 2, 3, None, "u3")]}
        rookie = by_key(build([draft], picks=picks))["2026_Rookie"]
        first, second = rookie["Picks"][0], rookie["Picks"][1]
        self.assertEqual(("Picked", "pl1", "First P1", 1, "u1"),
                         (first["Status"], first["PlayerID"], first["PlayerName"], first["SleeperPickNo"], first["SleeperPickedBy"]))
        # pick 1 originally belongs to team 2; the provider result says team 1 made it
        self.assertEqual((1, True, True, "SleeperDraftPick"),
                         (first["CurrentOwnerRosterID"], first["WasTraded"], first["IsCurrentlyTraded"], first["TradeSource"]))
        self.assertEqual(("Open", None), (second["Status"], second["PlayerID"]))  # no player yet
        self.assertEqual("GeneratedFromSleeperOrderTradesAndResults", rookie["PickSource"])

    def test_result_that_maps_to_no_pick_fails_closed(self):
        draft = provider_draft("d1", "2026", "complete", name="rookie")
        with self.assertRaises(DraftBuildError):
            build([draft], picks={"d1": [result("d1", 99, 1, "x")]})

    def test_missing_pick_payload_fails_closed(self):
        draft = provider_draft("d1", "2026", "complete", name="rookie")
        with self.assertRaises(DraftBuildError):
            build([draft], picks={})


class HistoryTests(unittest.TestCase):
    def test_past_completed_draft_uses_provider_order_and_largest_round_count(self):
        draft = provider_draft("d25", "2025", "complete", name="rookie")
        picks = {"d25": [result("d25", n, TEAMS[(n - 1) % 3], f"p{n}") for n in range(1, 10)]}  # 3 rounds worth of picks
        payloads = {2025: {"Drafts": [draft], "PicksByDraftID": picks}, 2026: {"Drafts": [], "PicksByDraftID": {}}}
        drafts = build_drafts(
            league_year=2026, seasons=[2025, 2026], provider_league_ids={2025: "p25", 2026: "p26"}, configs=CONFIGS,
            open_count=1, team_ids=TEAMS, standings_loader=lambda: standings(), payloads=payloads, transactions=[],
        )
        past = by_key(drafts)["2025_Rookie"]
        self.assertEqual(3, past["Settings"]["Rounds"])
        self.assertEqual(9, len(past["Picks"]))
        self.assertEqual("p25", past["ProviderLeagueID"])
        self.assertTrue(all(p["Status"] == "Picked" for p in past["Picks"]))

    def test_history_adds_missing_trade_history_for_traded_completed_picks(self):
        draft = provider_draft("d25", "2025", "complete", name="rookie")
        payloads = {2025: {"Drafts": [draft], "PicksByDraftID": {"d25": []}}, 2026: {"Drafts": [], "PicksByDraftID": {}}}
        txs = [movement("t", "2025_Rookie", 1, 2, 2, 3, created=5)]
        drafts = build_drafts(
            league_year=2026, seasons=[2025, 2026], provider_league_ids={2025: "p25", 2026: "p26"}, configs=CONFIGS,
            open_count=1, team_ids=TEAMS, standings_loader=lambda: standings(), payloads=payloads, transactions=txs,
        )
        pick = next(p for p in by_key(drafts)["2025_Rookie"]["Picks"] if p["PickKey"] == "2025_Rookie_R1_OO2")
        self.assertEqual([("t", 2, 3)], [(e["TransactionID"], e["PreviousOwnerRosterID"], e["NewOwnerRosterID"]) for e in pick["TradeHistory"]])
        self.assertEqual((3, True, "Sleeper"), (pick["CurrentOwnerRosterID"], pick["WasTraded"], pick["TradeSource"]))

    def test_conflicting_provider_binding_fails_closed(self):
        # The same provider draft cannot be the bound current draft and a history draft under another key.
        current = provider_draft("d1", "2026", "complete", name="rookie")
        configs = [dict(CONFIGS[0], SleeperDraftIDs={"2026": "d1"}), CONFIGS[1]]
        # history classification calls it a Free_Agent draft (explicit hint), the binding calls it a Rookie
        current["metadata"]["name"] = "free agent draft"
        with self.assertRaises(DraftBuildError):
            build([current], configs=configs)


class PipelineTests(unittest.TestCase):
    def test_pick_details_are_written_back_into_transaction_picks(self):
        draft = provider_draft("d1", "2026", "complete", name="rookie")
        picks = {"d1": [result("d1", 1, 2, "pl1")]}
        transaction = {
            "Source": "Sleeper", "TransactionID": "t1", "Type": "trade", "Status": "complete", "Season": "2026", "Week": 1,
            "CreatedAt": 5, "CreatedDate": "2026-01-01", "RosterIDs": [1, 2], "Adds": {}, "Drops": {}, "Notes": None,
            "DraftPicks": [{"DraftType": None, "DraftInstance": None, "DraftCode": None, "DraftSource": "Sleeper", "DraftKey": None,
                            "Season": "2026", "Round": 1, "OriginalOwnerRosterID": 2, "PreviousOwnerRosterID": 2,
                            "NewOwnerRosterID": 1, "SleeperDraftID": None}],
        }
        inputs = LeagueHistoryInputs(
            league_id="L", league_year=2026, seasons=[2026], provider_league_ids={2026: "p26"}, draft_configs=CONFIGS,
            open_draft_count=1, owners={"Ann": 1, "Bob": 2, "Cy": 3},
            canonical_transactions={2026: [transaction]},
            payloads={2026: {"Drafts": [draft], "PicksByDraftID": picks,
                             "TradedPicksByDraftID": {"d1": [{"season": "2026", "round": 1, "roster_id": 2,
                                                              "previous_owner_id": 2, "owner_id": 1}]}}},
            manual_rows=[], team_ids=TEAMS, standings_loader=lambda: standings(),
        )
        history = build_history(inputs)
        self.assertEqual([], history.unresolved)
        pick = history.transactions[2026][0]["DraftPicks"][0]
        self.assertEqual(("2026_Rookie", "2026_Rookie_R1_OO2", 1, "pl1", "Picked"),
                         (pick["DraftKey"], pick["PickKey"], pick["OverallPick"], pick["PlayerID"], pick["PickStatus"]))
        self.assertIn(2026, history.drafts)


class RepositoryInvariantTests(unittest.TestCase):
    """Invariants of the real canonical data; no concrete player, team or draft is asserted."""

    def test_materialization_is_idempotent_and_internally_consistent(self):
        with tempfile.TemporaryDirectory() as out:
            base = [sys.executable, str(TOOLS / "derived_data.py"), "materialize", "--out-root", out]
            for product in ("league-transactions", "league-drafts"):
                first = subprocess.run(base + ["--product", product], capture_output=True, text=True, cwd=REPO)
                self.assertEqual(0, first.returncode, first.stderr)
                second = subprocess.run(base + ["--product", product, "--check"], capture_output=True, text=True, cwd=REPO)
                self.assertEqual(0, second.returncode, second.stdout + second.stderr)
            draft_keys, pick_keys = set(), set()
            for path in sorted(Path(out, "league-drafts").rglob("*.json")):
                payload = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(2, payload["ContractVersion"])
                self.assertIn("PlayerRefs", payload)
                for draft in payload["Drafts"]:
                    self.assertEqual(str(payload["Season"]), draft["Season"])
                    self.assertNotIn(draft["DraftKey"], draft_keys)
                    draft_keys.add(draft["DraftKey"])
                    teams = draft["Settings"]["Teams"]
                    self.assertEqual(draft["Settings"]["Rounds"] * teams, len(draft["Picks"]))
                    for pick in draft["Picks"]:
                        pick_keys.add(pick["PickKey"])
                        self.assertEqual(pick["IsCurrentlyTraded"], pick["CurrentOwnerRosterID"] != pick["OriginalOwnerRosterID"])
                        if pick["TradeHistory"]:
                            self.assertTrue(pick["WasTraded"])
                        if pick["Status"] == "Picked":
                            self.assertTrue(pick["PlayerID"])
                        if draft["OrderMode"] == "RoundOnly":
                            self.assertIsNone(pick["OverallPick"])
            # Exact historical source regression, independent of current Players.json.
            past = json.loads((Path(out) / "league-drafts/nfl-reise/2024.json").read_text(encoding="utf-8"))
            self.assertTrue(any(
                pick.get("PlayerID") == "167" and pick.get("PlayerName") == "Tom Brady"
                for draft in past["Drafts"] for pick in draft["Picks"]
            ))
            brady = past["PlayerRefs"]["167"]
            self.assertEqual("NFLP-c2ccbe304851ede41925", brady["CanonicalPlayerID"])
            self.assertEqual("Tom Brady", brady["Name"])

            for path in sorted(Path(out, "league-transactions").rglob("*.json")):
                for transaction in json.loads(path.read_text(encoding="utf-8"))["Transactions"]:
                    for pick in transaction["DraftPicks"]:
                        if pick.get("DraftSource") == "Sleeper":
                            self.assertIn(pick["PickKey"], pick_keys, (path.name, transaction["TransactionID"]))


if __name__ == "__main__":
    unittest.main()
