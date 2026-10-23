"""Tests for the LeagueTransactions stages (league-history.yaml, ADR-057, Issue #999 step 2).

Constructed leagues pin the ported PowerShell semantics (manual overlay, pick identity resolution,
pick-result enrichment); one repository-level test checks invariants of the real canonical data without
wiring any concrete player or transaction into the assertions.
"""
from __future__ import annotations

import hashlib
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

from derived_data_lib.league_history import (  # noqa: E402
    LeagueHistoryInputs,
    build_transaction_stage,
    drafts_document,
    transactions_document,
)
from derived_data_lib.league_player_refs import LeaguePlayerReferenceResolver, provider_draft_names  # noqa: E402
from players_league_scoring import SleeperIdentityResolver  # noqa: E402
from derived_data_lib.league_transactions import (  # noqa: E402
    TransactionHistoryError,
    enrich_pick_details,
    manual_transaction_id,
    merge_manual_overlay,
    resolve_pick_identities,
    sort_transactions,
)

CONFIGS = [
    {"DraftType": "Rookie", "DraftInstance": 1, "DraftNo": 1, "Rounds": 2, "SleeperFuturePickPool": True,
     "OrderSource": "PreviousPlayoffs"},
    {"DraftType": "Free_Agent", "DraftInstance": 1, "DraftNo": 2, "Rounds": 2, "OrderSource": "AllTime"},
]
OWNERS = {"Ann": 1, "Bob": 2, "Cy": 3}


def tx(transaction_id, season="2026", week=1, created=1000, picks=(), adds=None, drops=None, source="Sleeper"):
    return {
        "Source": source, "TransactionID": transaction_id, "Type": "trade", "Status": "complete",
        "Season": season, "Week": week, "CreatedAt": created, "CreatedDate": "2026-01-01",
        "RosterIDs": [1, 2], "Adds": adds or {}, "Drops": drops or {}, "DraftPicks": [dict(p) for p in picks],
        "Notes": None,
    }


def provider_pick(season, round_no, original, previous, new):
    return {
        "DraftType": None, "DraftInstance": None, "DraftCode": None, "DraftSource": "Sleeper", "DraftKey": None,
        "Season": season, "Round": round_no, "OriginalOwnerRosterID": original, "PreviousOwnerRosterID": previous,
        "NewOwnerRosterID": new, "SleeperDraftID": None,
    }


def traded(season, round_no, original, previous, owner):
    return {"season": season, "round": round_no, "roster_id": original, "previous_owner_id": previous, "owner_id": owner}


def context(key, draft_type, draft_id, traded_picks):
    season = key.split("_", 1)[0]
    return {"Season": season, "DraftType": draft_type, "DraftInstance": 1, "DraftCode": draft_type,
            "DraftKey": key, "SleeperDraftID": draft_id, "TradedPicks": traded_picks}


class ManualOverlayTests(unittest.TestCase):
    def test_manual_transaction_id_is_a_stable_twelve_digit_sha1(self):
        manual = {"Season": "2026", "Date": "2026-06-12", "Picks": [
            {"DraftKey": "2026_Free_Agent", "Round": 2, "Original": "Bob", "From": "Ann", "To": "Cy"}]}
        raw = "2026|2026-06-12|-R2-O2-F1-T3"  # overlay picks have no Season, as in the PowerShell ID rule
        expected = "Manual_2026_" + hashlib.sha1(raw.encode()).hexdigest().upper()[:12]
        self.assertEqual(expected, manual_transaction_id(manual, OWNERS))

    def test_unknown_owner_fails_closed(self):
        manual = {"Season": "2026", "Date": "2026-06-12", "Picks": [
            {"DraftKey": "2026_Rookie", "Round": 1, "Original": "Nobody", "From": "Ann", "To": "Cy"}]}
        with self.assertRaises(TransactionHistoryError):
            manual_transaction_id(manual, OWNERS)

    def test_binding_adds_picks_and_recomputes_roster_ids(self):
        base = [tx("100", picks=[provider_pick("2026", 1, 1, 1, 2)], adds={"p1": 2}, drops={"p1": 1})]
        rows = [{"Season": "2026", "Date": "2026-01-02", "Week": 1, "SleeperTransactionID": 100,
                 "Picks": [{"DraftKey": "2027_Free_Agent", "Round": 4, "Original": "Cy", "From": "Cy", "To": "Ann"}]}]
        merged = merge_manual_overlay(base, rows, "2026", OWNERS, CONFIGS)
        self.assertEqual("Sleeper_Manual", merged[0]["Source"])
        self.assertEqual(["Manual", "Sleeper"], sorted(p["DraftSource"] for p in merged[0]["DraftPicks"]))
        self.assertEqual([1, 2, 3], merged[0]["RosterIDs"])  # the manual pick moves Cy -> Ann
        manual = next(p for p in merged[0]["DraftPicks"] if p["DraftSource"] == "Manual")
        self.assertEqual(("2027_Free_Agent", "Free_Agent", 1), (manual["DraftKey"], manual["DraftType"], manual["DraftInstance"]))

    def test_unbound_row_becomes_manual_transaction_and_sorting_is_newest_first(self):
        base = [tx("100", week=2, created=2000), tx("101", week=1, created=3000)]
        rows = [{"Season": "2026", "Date": "2026-01-02", "Week": 3, "Picks": [
            {"DraftKey": "2026_Rookie", "Round": 1, "Original": "Ann", "From": "Ann", "To": "Bob"}]},
            {"Season": "2025", "Date": "2025-01-02", "Week": 1, "Picks": []}]  # other season is ignored
        merged = merge_manual_overlay(base, rows, "2026", OWNERS, CONFIGS)
        self.assertEqual(3, len(merged))
        self.assertEqual("Manual", merged[0]["Source"])  # week 3 sorts first (descending)
        self.assertEqual(["Manual", "Sleeper", "Sleeper"], [item["Source"] for item in merged])
        self.assertEqual(1, merged[0]["CreatedAt"] // 1000 // 86400 // 365 - 55)  # a real epoch day was derived

    def test_binding_without_canonical_transaction_fails_closed(self):
        rows = [{"Season": "2026", "SleeperTransactionID": "999", "Picks": []}]
        with self.assertRaises(TransactionHistoryError):
            merge_manual_overlay([tx("100")], rows, "2026", OWNERS, CONFIGS)

    def test_duplicate_binding_fails_closed(self):
        rows = [{"Season": "2026", "SleeperTransactionID": "100", "Picks": []},
                {"Season": "2026", "SleeperTransactionID": 100, "Picks": []}]
        with self.assertRaises(TransactionHistoryError):
            merge_manual_overlay([tx("100")], rows, "2026", OWNERS, CONFIGS)

    def test_sort_is_descending_by_effective_time_independent_of_submission_and_week(self):
        items = [tx("a", week=1, created=5), tx("b", week=2, created=1), tx("c", week=2, created=1)]
        items[1]["EffectiveAt"] = 9
        items[2]["EffectiveAt"] = 9
        self.assertEqual(["c", "b", "a"], [item["TransactionID"] for item in sort_transactions(items)])

    def test_waiver_processing_time_beats_submission_and_manual_falls_back(self):
        first = tx("waiver", created=1792268727874)
        first["Type"] = "waiver"
        first["StatusUpdatedAt"] = 1792317947771  # 18 Oct, 12:05 local vs 17 Oct, 22:25 submitted
        later_submitted = tx("cut", created=1792312508118)
        later_submitted["StatusUpdatedAt"] = 1792312508118
        merged = merge_manual_overlay([first, later_submitted], [], "2026", OWNERS, CONFIGS)
        self.assertEqual(["waiver", "cut"], [item["TransactionID"] for item in merged])
        self.assertEqual(1792317947771, merged[0]["EffectiveAt"])
        self.assertEqual(1792268727874, merged[0]["CreatedAt"])
        self.assertNotIn("StatusUpdatedAt", merged[0])
        legacy = merge_manual_overlay([tx("old", created=1234)], [], "2026", OWNERS, CONFIGS)
        self.assertEqual(1234, legacy[0]["EffectiveAt"])
        manual = merge_manual_overlay([], [{"Season": "2026", "Date": "2026-01-02",
            "Week": 1, "Picks": []}], "2026", OWNERS, CONFIGS)
        self.assertEqual(manual[0]["CreatedAt"], manual[0]["EffectiveAt"])


class PickIdentityTests(unittest.TestCase):
    def test_exact_movement_beats_identity_only(self):
        contexts = [
            context("2026_Rookie", "Rookie", "d1", [traded("2026", 1, 1, 1, 2)]),
            context("2026_Free_Agent", "Free_Agent", "d2", [traded("2026", 1, 1, 9, 9)]),
        ]
        items = [tx("1", picks=[provider_pick("2026", 1, 1, 1, 2)])]
        self.assertEqual([], resolve_pick_identities(items, contexts, CONFIGS, 2026) and [])
        pick = items[0]["DraftPicks"][0]
        self.assertEqual(("2026_Rookie", "d1", "Rookie"), (pick["DraftKey"], pick["SleeperDraftID"], pick["DraftType"]))

    def test_two_exact_matches_are_ambiguous_and_stay_unresolved(self):
        contexts = [
            context("2026_Rookie", "Rookie", "d1", [traded("2026", 1, 1, 1, 2)]),
            context("2026_Free_Agent", "Free_Agent", "d2", [traded("2026", 1, 1, 1, 2)]),
        ]
        items = [tx("1", picks=[provider_pick("2026", 1, 1, 1, 2)])]
        report = resolve_pick_identities(items, contexts, CONFIGS, 2026)
        self.assertEqual(1, len(report))
        self.assertIsNone(items[0]["DraftPicks"][0]["DraftKey"])

    def test_sibling_manual_pick_claims_its_draft_key(self):
        contexts = [
            context("2026_Rookie", "Rookie", "d1", [traded("2026", 1, 1, 1, 2)]),
            context("2026_Free_Agent", "Free_Agent", "d2", [traded("2026", 1, 1, 1, 2)]),
        ]
        manual = provider_pick("2026", 1, 1, 1, 2)
        manual.update(DraftSource="Manual", DraftKey="2026_Free_Agent", DraftType="Free_Agent", DraftInstance=1, DraftCode="Free_Agent")
        del manual["SleeperDraftID"]
        items = [tx("1", picks=[provider_pick("2026", 1, 1, 1, 2), manual])]
        self.assertEqual([], resolve_pick_identities(items, contexts, CONFIGS, 2026))
        provider = next(p for p in items[0]["DraftPicks"] if p["DraftSource"] == "Sleeper")
        self.assertEqual("2026_Rookie", provider["DraftKey"])

    def test_future_pick_uses_the_future_pool_draft_type(self):
        items = [tx("1", picks=[provider_pick("2028", 2, 3, 3, 1)])]
        self.assertEqual([], resolve_pick_identities(items, [], CONFIGS, 2026))
        pick = items[0]["DraftPicks"][0]
        self.assertEqual(("2028_Rookie", None), (pick["DraftKey"], pick["SleeperDraftID"]))

    def test_current_or_past_season_pick_without_context_stays_unresolved(self):
        items = [tx("1", picks=[provider_pick("2026", 2, 3, 3, 1)])]
        self.assertEqual(1, len(resolve_pick_identities(items, [], CONFIGS, 2026)))

    def test_two_future_pool_configs_fail_closed(self):
        configs = [dict(CONFIGS[0]), dict(CONFIGS[1], SleeperFuturePickPool=True)]
        items = [tx("1", picks=[provider_pick("2028", 2, 3, 3, 1)])]
        with self.assertRaises(TransactionHistoryError):
            resolve_pick_identities(items, [], configs, 2026)


class EnrichmentTests(unittest.TestCase):
    def draft(self, key, draft_type, draft_id, picks):
        return {"DraftKey": key, "DraftType": draft_type, "DraftInstance": 1, "DraftCode": draft_type,
                "SleeperDraftID": draft_id, "Picks": picks}

    def draft_pick(self, key, round_no, original, history=(), **extra):
        pick = {"PickKey": f"{key}_R{round_no}_OO{original}", "Season": key.split("_")[0], "Round": round_no,
                "OriginalOwnerRosterID": original, "PositionInRound": 2, "OverallPick": 2, "PlayerID": "p9",
                "PlayerName": "A B", "Status": "Picked", "SleeperPickNo": 2, "TradeHistory": list(history)}
        pick.update(extra)
        return pick

    def test_trade_history_selects_between_equal_round_picks_of_two_drafts(self):
        entry = {"TransactionID": "1", "PreviousOwnerRosterID": 1, "NewOwnerRosterID": 2}
        drafts = [
            self.draft("2026_Rookie", "Rookie", "d1", [self.draft_pick("2026_Rookie", 1, 1)]),
            self.draft("2026_Free_Agent", "Free_Agent", "d2", [self.draft_pick("2026_Free_Agent", 1, 1, [entry])]),
        ]
        items = [tx("1", picks=[provider_pick("2026", 1, 1, 1, 2)])]
        enrich_pick_details(items, drafts)
        pick = items[0]["DraftPicks"][0]
        self.assertEqual(("2026_Free_Agent", "2026_Free_Agent_R1_OO1", "Picked", 2), (pick["DraftKey"], pick["PickKey"], pick["PickStatus"], pick["OverallPick"]))

    def test_identity_fallback_uses_the_transaction_pick_hints_to_break_ties(self):
        drafts = [
            self.draft("2026_Rookie", "Rookie", "d1", [self.draft_pick("2026_Rookie", 1, 1)]),
            self.draft("2026_Free_Agent", "Free_Agent", "d2", [self.draft_pick("2026_Free_Agent", 1, 1)]),
        ]
        pick_dict = provider_pick("2026", 1, 1, 1, 2)
        pick_dict["DraftKey"] = "2026_Rookie"
        pick_dict["SleeperDraftID"] = "d1"
        items = [tx("1", picks=[pick_dict])]
        enrich_pick_details(items, drafts)
        self.assertEqual("2026_Rookie_R1_OO1", items[0]["DraftPicks"][0]["PickKey"])

    def test_unmatched_pick_is_left_unchanged(self):
        items = [tx("1", picks=[provider_pick("2031", 1, 1, 1, 2)])]
        enrich_pick_details(items, [])
        self.assertNotIn("PickKey", items[0]["DraftPicks"][0])

    def test_conflicting_duplicate_draft_pick_identity_fails_closed(self):
        a = self.draft("2026_Rookie", "Rookie", "d1", [self.draft_pick("2026_Rookie", 1, 1)])
        b = self.draft("2026_Rookie", "Rookie", "d1", [self.draft_pick("2026_Rookie", 1, 1, PlayerID="other")])
        items = [tx("1", picks=[provider_pick("2026", 1, 1, 1, 2)])]
        with self.assertRaises(TransactionHistoryError):
            enrich_pick_details(items, [a, b])


def provider_draft(draft_id, season, status, created, name="", rounds=2, slots=(1, 2)):
    return {
        "draft_id": draft_id, "season": season, "type": "linear", "status": status, "start_time": created,
        "created": created, "settings": {"rounds": rounds}, "metadata": {"name": name},
        "draft_order": {}, "slot_to_roster_id": {str(i + 1): rid for i, rid in enumerate(slots)},
    }


class StageTests(unittest.TestCase):
    def inputs(self, transactions, payloads, manual=()):
        return LeagueHistoryInputs(
            league_id="L", league_year=2026, seasons=[2025, 2026],
            provider_league_ids={2025: "p25", 2026: "p26"}, draft_configs=CONFIGS, open_draft_count=3,
            owners=OWNERS, canonical_transactions=transactions, payloads=payloads, manual_rows=list(manual),
        )

    def test_historical_stage_corrects_a_pick_to_the_completed_draft_classification(self):
        d25 = provider_draft("d25", "2025", "complete", 1, name="rookie draft")
        payloads = {
            2025: {"Drafts": [d25], "PicksByDraftID": {"d25": []}, "TradedPicksByDraftID": {"d25": [traded("2025", 1, 1, 1, 2)]}},
            2026: {"Drafts": [], "PicksByDraftID": {}, "TradedPicksByDraftID": {}},
        }
        transactions = {2025: [tx("1", "2025", picks=[provider_pick("2025", 1, 1, 1, 2)])], 2026: []}
        stage = build_transaction_stage(self.inputs(transactions, payloads))
        pick = stage.transactions[2025][0]["DraftPicks"][0]
        self.assertEqual(("2025_Rookie", "d25"), (pick["DraftKey"], pick["SleeperDraftID"]))
        self.assertEqual([], stage.unresolved)

    def test_unidentified_provider_pick_is_reported(self):
        payloads = {2025: {"Drafts": [], "PicksByDraftID": {}, "TradedPicksByDraftID": {}},
                    2026: {"Drafts": [], "PicksByDraftID": {}, "TradedPicksByDraftID": {}}}
        transactions = {2025: [tx("1", "2025", picks=[provider_pick("2025", 1, 1, 1, 2)])], 2026: []}
        stage = build_transaction_stage(self.inputs(transactions, payloads))
        self.assertEqual(1, len(stage.unresolved))

    def test_duplicate_transaction_id_across_seasons_fails_closed(self):
        payloads = {2025: {"Drafts": []}, 2026: {"Drafts": []}}
        transactions = {2025: [tx("1", "2025")], 2026: [tx("1", "2026")]}
        with self.assertRaises(TransactionHistoryError):
            build_transaction_stage(self.inputs(transactions, payloads))

    def test_document_lists_player_identities_of_the_file(self):
        def ref(player, season, name):
            cid = None if player == "p2" else f"C-{player}"
            return {"CanonicalPlayerID": cid, "Name": name, "Position": None, "Picture": None,
                    "ResolutionStatus": "resolved" if cid else "unmapped", "Provenance": {}}
        document = transactions_document("L", 2026, [tx("1", adds={"p1": 1}, drops={"p2": 2})], ref)
        self.assertEqual({"p1": "C-p1", "p2": None}, document["PlayerIdentities"])
        self.assertEqual(2, document["ContractVersion"])
        self.assertEqual("C-p1", document["PlayerRefs"]["p1"]["CanonicalPlayerID"])


class HistoricalPlayerReferenceTests(unittest.TestCase):
    """Issue #1100: old players do not depend on the current Players.json population."""

    def resolver(self):
        identity = SleeperIdentityResolver(
            {"Mappings": [
                {"Provider": "Sleeper", "ExternalID": "3321", "CanonicalPlayerID": "NFLP-tyreek",
                 "FirstObservedSeason": 2021, "LastObservedSeason": 2026},
                {"Provider": "Sleeper", "ExternalID": "167", "CanonicalPlayerID": "NFLP-brady",
                 "FirstObservedSeason": 2021, "LastObservedSeason": 2026},
                {"Provider": "Sleeper", "ExternalID": "9", "CanonicalPlayerID": "NFLP-old",
                 "FirstObservedSeason": 2020, "LastObservedSeason": 2024},
                {"Provider": "Sleeper", "ExternalID": "9", "CanonicalPlayerID": "NFLP-new",
                 "FirstObservedSeason": 2026, "LastObservedSeason": 2026},
            ], "Conflicts": [
                {"Provider": "Sleeper", "ExternalID": "42", "CanonicalPlayerIDs": ["NFLP-brady", "NFLP-tyreek"],
                 "FirstObservedSeason": 2024, "LastObservedSeason": 2026},
            ]},
            {"Players": [{"CanonicalPlayerID": cid, "IDs": {"Sleeper": cid}} for cid in
                         ("NFLP-tyreek", "NFLP-brady", "NFLP-old", "NFLP-new")]},
        )
        return LeaguePlayerReferenceResolver(
            identity,
            [{"CanonicalPlayerID": "NFLP-tyreek", "DisplayName": "Tyreek Hill", "Position": "WR",
              "Headshot": "https://images.example/tyreek.png"},
             {"CanonicalPlayerID": "NFLP-brady", "DisplayName": "Tom Brady", "Position": "QB", "Headshot": None},
             {"CanonicalPlayerID": "NFLP-old", "DisplayName": "Old Player", "Position": "RB", "Headshot": None}],
            [{"SleeperPlayerID": "3321", "CanonicalPlayerID": "NFLP-tyreek",
              "FullName": "Tyreek Hill", "Position": "WR"},
             {"SleeperPlayerID": "167", "CanonicalPlayerID": "NFLP-brady",
              "FullName": "Tom Brady", "Position": "QB"},
             {"SleeperPlayerID": "9", "CanonicalPlayerID": "NFLP-new",
              "FullName": "New Player", "Position": "TE"}],
        )

    def test_tyreek_drop_survives_absent_current_player_and_brady_draft_is_resolved(self):
        resolver = self.resolver()
        transaction = tx("1417280596463394816", drops={"3321": 3})
        moves = transactions_document("nfl-reise", 2026, [transaction], resolver.resolve)
        tyreek = moves["PlayerRefs"]["3321"]
        self.assertEqual(("NFLP-tyreek", "Tyreek Hill", "WR", "resolved"),
                         (tyreek["CanonicalPlayerID"], tyreek["Name"], tyreek["Position"], tyreek["ResolutionStatus"]))
        self.assertEqual({"3321": "NFLP-tyreek"}, moves["PlayerIdentities"])
        self.assertNotIn("Team", tyreek)
        self.assertEqual("nflverse.players", tyreek["Provenance"]["Picture"])

        picks = [{"PlayerID": "167", "PlayerName": "Tom Brady"}]
        draft = {"DraftKey": "2024_Free_Agent", "Picks": picks}
        names = provider_draft_names([draft])
        result = drafts_document("nfl-reise", 2024, [draft], resolver.resolve, names)
        self.assertEqual(("Tom Brady", "QB", "resolved"),
                         (result["PlayerRefs"]["167"]["Name"], result["PlayerRefs"]["167"]["Position"],
                          result["PlayerRefs"]["167"]["ResolutionStatus"]))
        self.assertEqual("Tom Brady", result["Drafts"][0]["Picks"][0]["PlayerName"])

    def test_nfl_headshot_in_player_refs_is_sized(self):
        unsized = "https://static.www.nfl.com/image/upload/f_auto,q_auto/league/abc123"
        resolver = self.resolver()
        resolver.profiles["NFLP-tyreek"]["Headshot"] = unsized
        self.assertEqual("https://static.www.nfl.com/image/upload/f_auto,q_auto,w_160/league/abc123",
                         resolver.resolve("3321", 2026)["Picture"])

    def test_published_history_has_no_unsized_nfl_headshots(self):
        """Persisted-state guard: an NFL image link without a width serves a multi-MB original."""
        import re
        root = Path(__file__).resolve().parents[2] / "public" / "data"
        pattern = re.compile(r'https://static\.www\.nfl\.com/image/(?:upload|private)/([^/"]+)/')
        files = [root / "Drafts.json", root / "Transactions.json",
                 *(root / "past_seasons" / "Drafts").glob("*.json"),
                 *(root / "past_seasons" / "Transactions").glob("*.json")]
        for file in files:
            for transform in pattern.findall(file.read_text(encoding="utf-8")):
                self.assertIn("w_", transform, f"{file.name}: unsized NFL headshot")

    def test_known_fantasy_position_wins_over_non_fantasy_profile_position(self):
        identity = SleeperIdentityResolver(
            {"Mappings": [{"Provider": "Sleeper", "ExternalID": "5", "CanonicalPlayerID": "NFLP-dual",
                           "FirstObservedSeason": 2024, "LastObservedSeason": 2026}], "Conflicts": []},
            {"Players": [{"CanonicalPlayerID": "NFLP-dual", "IDs": {"Sleeper": "5"}}]},
        )
        profile = {"CanonicalPlayerID": "NFLP-dual", "DisplayName": "Dual Player", "Position": "CB", "Headshot": None}
        snapshot = {"SleeperPlayerID": "5", "CanonicalPlayerID": "NFLP-dual", "FullName": "Dual Player",
                    "Position": "DB", "FantasyPositions": ["DB", "WR"]}
        ref = LeaguePlayerReferenceResolver(identity, [profile], [snapshot]).resolve("5", 2025)
        self.assertEqual("WR", ref["Position"])
        self.assertEqual("sleeper.players.fantasy-position", ref["Provenance"]["Position"])
        # Without a fantasy position anywhere the profile position stays the fallback.
        snapshot = {**snapshot, "Position": "DB", "FantasyPositions": ["DB"]}
        ref = LeaguePlayerReferenceResolver(identity, [profile], [snapshot]).resolve("5", 2025)
        self.assertEqual(("CB", "nflverse.players"), (ref["Position"], ref["Provenance"]["Position"]))

    def test_temporal_id_reuse_does_not_leak_current_sleeper_snapshot(self):
        old = self.resolver().resolve("9", 2024)
        self.assertEqual(("NFLP-old", "Old Player", "RB"), (old["CanonicalPlayerID"], old["Name"], old["Position"]))
        self.assertNotEqual("New Player", old["Name"])
        gap = self.resolver().resolve("9", 2025)
        self.assertEqual("unmapped", gap["ResolutionStatus"])
        self.assertIsNone(gap["Position"])

    def test_unknown_ambiguous_and_provider_name_fallback(self):
        resolver = self.resolver()
        unknown = resolver.resolve("missing", 2024, "Original Draft Name")
        self.assertIsNone(unknown["CanonicalPlayerID"])
        self.assertEqual("Original Draft Name", unknown["Name"])
        self.assertEqual("league.draft.pick.PlayerName", unknown["Provenance"]["Name"])
        self.assertIsNone(unknown["Position"])
        self.assertIsNone(unknown["Picture"])
        ambiguous = resolver.resolve("42", 2024)
        self.assertEqual("ambiguous", ambiguous["ResolutionStatus"])
        self.assertIsNone(ambiguous["Name"])
        self.assertIsNone(ambiguous["CanonicalPlayerID"])

    def test_conflicting_provider_pick_names_do_not_become_shared_identity(self):
        drafts = [{"Picks": [{"PlayerID": "q", "PlayerName": "One"},
                             {"PlayerID": "q", "PlayerName": "Another"}]}]
        self.assertNotIn("q", provider_draft_names(drafts))
        self.assertEqual("One", drafts[0]["Picks"][0]["PlayerName"])
        self.assertEqual("Another", drafts[0]["Picks"][1]["PlayerName"])

    def test_duplicate_snapshot_player_id_is_not_arbitrarily_selected(self):
        identity = self.resolver().identity
        with self.assertRaisesRegex(ValueError, "Duplicate Sleeper snapshot identity"):
            LeaguePlayerReferenceResolver(identity, [], [
                {"SleeperPlayerID": "x"}, {"SleeperPlayerID": "x"},
            ])


class RepositoryInvariantTests(unittest.TestCase):
    """Invariants of the real canonical data; no concrete player, transaction or draft is asserted."""

    def test_materialization_is_idempotent_and_every_provider_pick_is_identified(self):
        with tempfile.TemporaryDirectory() as out:
            command = [sys.executable, str(TOOLS / "derived_data.py"), "materialize", "--product", "league-transactions", "--out-root", out]
            first = subprocess.run(command, capture_output=True, text=True, cwd=REPO)
            self.assertEqual(0, first.returncode, first.stderr)
            second = subprocess.run(command + ["--check"], capture_output=True, text=True, cwd=REPO)
            self.assertEqual(0, second.returncode, second.stdout + second.stderr)
            ids = []
            for path in sorted(Path(out, "league-transactions").rglob("*.json")):
                payload = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(2, payload["ContractVersion"])
                self.assertIn("PlayerRefs", payload)
                for transaction in payload["Transactions"]:
                    ids.append(transaction["TransactionID"])
                    for pick in transaction["DraftPicks"]:
                        self.assertTrue(pick["DraftKey"], (path.name, transaction["TransactionID"]))
            self.assertEqual(len(ids), len(set(ids)))

            # Exact source-level regression: the drop still exists after the
            # current Players.json population no longer contains Sleeper 3321.
            current = json.loads((Path(out) / "league-transactions/nfl-reise/2026.json").read_text(encoding="utf-8"))
            self.assertTrue(any("3321" in row["Drops"] for row in current["Transactions"]))
            ref = current["PlayerRefs"]["3321"]
            self.assertEqual("NFLP-3e3947dc88db6fc570fc", ref["CanonicalPlayerID"])
            self.assertEqual("Tyreek Hill", ref["Name"])


if __name__ == "__main__":
    unittest.main()
