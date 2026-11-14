from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from data_roots import DATA_SOURCE_ROOT
from derived_data_lib.nfl_games import build_nfl_games
from nfl_games_materialize import materialize, discover_seasons


def inputs():
    game = "2026_06_HOU_JAX"
    schedule = {
        "Season": 2026, "SourceDataset": "nflverse.schedules",
        "Games": [{
            "GameID": game, "GameType": "REG", "Week": 6,
            "GameDay": "2026-10-18", "GameTime": "09:30",
            "AwayTeam": "HOU", "HomeTeam": "JAX", "AwayScore": None, "HomeScore": None,
        }],
    }
    finality = {
        "Season": 2026, "SourceDataset": "nflverse.game-finality",
        "Games": [{"GameID": game, "GameType": "REG", "Week": 6, "Final": False}],
    }
    odds = {
        "Season": 2026, "SourceDataset": "nflverse.schedule-odds",
        "SpreadConvention": "away spread; positive favors home",
        "Games": [{
            "GameID": game, "GameType": "REG", "Week": 6,
            "SpreadLine": 3.5, "TotalLine": 44.5,
            "AwayMoneyline": 200, "HomeMoneyline": -250,
            "UnderOdds": -110, "OverOdds": -110,
        }],
    }
    return schedule, finality, odds


class GlobalNflGamesTests(unittest.TestCase):
    def test_derived_points_and_source_price_exclusion(self):
        result = build_nfl_games(*inputs())
        self.assertEqual(result["SourceDatasets"],
                         ["nflverse.schedules", "nflverse.game-finality", "nflverse.schedule-odds"])
        row = result["Games"][0]
        self.assertEqual((20.5, 24.0),
                         (row["Market"]["ImpliedAwayPoints"], row["Market"]["ImpliedHomePoints"]))
        self.assertIsNone(row["AwayScore"])
        self.assertFalse(row["Final"])
        self.assertNotIn("HomeMoneyline", row["Market"])
        self.assertNotIn("UnderOdds", row["Market"])

    def test_pure_price_change_is_semantic_noop(self):
        source = inputs()
        changed = copy.deepcopy(source)
        changed[2]["Games"][0]["HomeMoneyline"] = -500
        changed[2]["Games"][0]["OverOdds"] = -120
        self.assertEqual(build_nfl_games(*source), build_nfl_games(*changed))

    def test_historical_missing_game_time_is_preserved_as_null(self):
        rows = inputs()
        rows[0]["Games"][0]["GameTime"] = None
        game = build_nfl_games(*rows)["Games"][0]
        self.assertIsNone(game["GameTime"])
        rows[0]["Games"][0]["GameTime"] = ""
        with self.assertRaisesRegex(ValueError, "invalid GameTime"):
            build_nfl_games(*rows)

    def test_nullable_lines_are_unknown_not_zero(self):
        rows = inputs()
        rows[2]["Games"][0]["SpreadLine"] = None
        market = build_nfl_games(*rows)["Games"][0]["Market"]
        self.assertIsNone(market["ImpliedHomePoints"])
        self.assertIsNone(market["ImpliedAwayPoints"])

    def test_changes_to_total_or_spread_recompute(self):
        schedule, finality, odds = inputs()
        base = build_nfl_games(schedule, finality, odds)["Games"][0]["Market"]
        odds["Games"][0]["TotalLine"] = 45.5
        new = build_nfl_games(schedule, finality, odds)["Games"][0]["Market"]
        self.assertEqual((base["ImpliedAwayPoints"] + .5, base["ImpliedHomePoints"] + .5),
                         (new["ImpliedAwayPoints"], new["ImpliedHomePoints"]))

    def test_final_game_uses_canonical_finality(self):
        schedule, finality, odds = inputs()
        schedule["Games"][0]["AwayScore"] = 30
        schedule["Games"][0]["HomeScore"] = 17
        finality["Games"][0]["Final"] = True
        row = build_nfl_games(schedule, finality, odds)["Games"][0]
        self.assertTrue(row["Final"])
        self.assertEqual((30, 17), (row["AwayScore"], row["HomeScore"]))

    def test_missing_or_duplicate_game_ids_fail_closed(self):
        for target in (1, 2):
            with self.subTest(target=target):
                arr = inputs()
                arr[target]["Games"] = []
                with self.assertRaises(ValueError):
                    build_nfl_games(*arr)
                arr = inputs()
                arr[target]["Games"].append(copy.deepcopy(arr[target]["Games"][0]))
                with self.assertRaises(ValueError):
                    build_nfl_games(*arr)

    def test_bad_join_week_and_spread_convention(self):
        arr = inputs()
        arr[2]["Games"][0]["Week"] = 7
        with self.assertRaises(ValueError):
            build_nfl_games(*arr)
        arr = inputs()
        arr[2]["SpreadConvention"] = "home spread"
        with self.assertRaises(ValueError):
            build_nfl_games(*arr)

    def test_invalid_scores_lines_finals_fail_closed(self):
        for path, val in ((("Games", 0, "SpreadLine"), float("nan")),
                          (("Games", 0, "TotalLine"), -2)):
            arr = inputs()
            arr[2][path[0]][path[1]][path[2]] = val
            with self.assertRaises(ValueError):
                build_nfl_games(*arr)
        arr = inputs()
        arr[1]["Games"][0]["Final"] = True
        with self.assertRaises(ValueError):
            build_nfl_games(*arr)

    def test_materializer_preflight_write_and_second_noop(self):
        with tempfile.TemporaryDirectory() as root_text:
            root = Path(root_text)
            for subdir, doc in zip(("schedules", "game-finality", "schedule-odds"), inputs()):
                target = root / DATA_SOURCE_ROOT / "nfl" / subdir / "2026.json"
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(json.dumps(doc), encoding="utf-8")
            self.assertEqual(discover_seasons(root), [2026])
            preview = materialize(root, 2026)
            self.assertTrue(preview["WouldWrite"])
            self.assertFalse(preview["Written"])
            target = root / "data-derived" / "nfl-games" / "2026.json"
            self.assertFalse(target.exists())
            write = materialize(root, 2026, write=True)
            self.assertTrue(write["Written"])
            self.assertEqual(materialize(root, 2026, write=True)["Unchanged"], True)
            self.assertEqual(materialize(root, 2026)["WithCompleteMarketLines"], 1)
            # An isolated clean derived root is fully restorable from canonical inputs.
            other = root / "isolated-derived"
            materialize(root, 2026, out_root=other, write=True)
            self.assertEqual(target.read_bytes(), (other / "nfl-games" / "2026.json").read_bytes())
            # Price-only changes neither rewrite nor invalidate global NFL Game.
            input_path = root / DATA_SOURCE_ROOT / "nfl" / "schedule-odds" / "2026.json"
            payload = json.loads(input_path.read_text(encoding="utf-8"))
            payload["Games"][0]["AwayMoneyline"] += 50
            input_path.write_text(json.dumps(payload), encoding="utf-8")
            self.assertTrue(materialize(root, 2026)["Unchanged"])

    def test_missing_odds_source_fails_no_empty_guess(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "Source unavailable"):
                materialize(Path(tmp), 2026)


from derived_data_lib.nfl_game_detail import build_nfl_game_detail
from nfl_game_detail_preview import preview


def _preview_gains(game_id="2026_06_HOU_JAX"):
    return {
        "SchemaVersion": 2,
        "Season": 2026,
        "SourceDataset": "nflverse.player-game-long-gains",
        "Games": [{"GameID": game_id, "SeasonType": "REG", "Week": 6}],
        "Records": [{
            "GameID": game_id,
            "SeasonType": "REG",
            "Week": 6,
            "CanonicalPlayerID": "NFLP-test",
            "GainType": "LongRush",
            "Yards": 21,
            "PlayID": 120,
            "Team": "HOU",
        }],
    }


class NflGameDetailReadOnlyPreviewTests(unittest.TestCase):
    def test_existing_long_gain_evidence_is_partial_not_full_pbp(self):
        index = build_nfl_games(*inputs())
        result = build_nfl_game_detail(index, "2026_06_HOU_JAX", _preview_gains())
        self.assertEqual(result["GameID"], "2026_06_HOU_JAX")
        self.assertEqual(result["PlayByPlay"]["Coverage"], "partial")
        self.assertFalse(result["PlayByPlay"]["FullPlayByPlayAvailable"])
        self.assertEqual(result["PlayByPlay"]["LongGains"]["Records"][0]["PlayID"], 120)

    def test_missing_source_and_missing_game_evidence_are_unavailable_not_zero(self):
        index = build_nfl_games(*inputs())
        missing = build_nfl_game_detail(index, "2026_06_HOU_JAX")
        self.assertEqual(missing["PlayByPlay"]["Coverage"], "unavailable")
        self.assertIsNone(missing["PlayByPlay"]["LongGains"]["Records"])
        source = _preview_gains()
        source["Games"] = []
        source["Records"] = []
        absent = build_nfl_game_detail(index, "2026_06_HOU_JAX", source)
        self.assertEqual(absent["PlayByPlay"]["Coverage"], "unavailable")
        self.assertIsNone(absent["PlayByPlay"]["LongGains"]["Records"])
        source["Games"] = _preview_gains()["Games"]
        covered_but_empty = build_nfl_game_detail(index, "2026_06_HOU_JAX", source)
        self.assertEqual(covered_but_empty["PlayByPlay"]["LongGains"]["Records"], [])
        self.assertFalse(covered_but_empty["PlayByPlay"]["FullPlayByPlayAvailable"])

    def test_join_and_duplicate_regressions_fail_closed(self):
        index = build_nfl_games(*inputs())
        for mutation in ("duplicate", "week", "team", "play_id", "unknown"):
            with self.subTest(mutation=mutation):
                source = _preview_gains()
                if mutation == "duplicate":
                    source["Records"].append(copy.deepcopy(source["Records"][0]))
                elif mutation == "week":
                    source["Games"][0]["Week"] = 5
                elif mutation == "team":
                    source["Records"][0]["Team"] = "SEA"
                elif mutation == "play_id":
                    source["Records"][0]["PlayID"] = None
                else:
                    source["Records"][0]["GameID"] = "2026_06_FAKE_FAKE"
                with self.assertRaises(ValueError):
                    build_nfl_game_detail(index, "2026_06_HOU_JAX", source)

    def test_readonly_preview_from_existing_roots(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            index_path = root / "data-derived" / "nfl-games" / "2026.json"
            source_path = root / DATA_SOURCE_ROOT / "nfl" / "player-game-long-gains" / "2026.json"
            index_path.parent.mkdir(parents=True)
            source_path.parent.mkdir(parents=True)
            index_path.write_text(json.dumps(build_nfl_games(*inputs())), encoding="utf-8")
            source_path.write_text(json.dumps(_preview_gains()), encoding="utf-8")
            before = sorted(p.relative_to(root) for p in root.rglob("*"))
            result = preview(root, 2026, "2026_06_HOU_JAX")
            self.assertEqual(result["PlayByPlay"]["Coverage"], "partial")
            self.assertEqual(sorted(p.relative_to(root) for p in root.rglob("*")), before)

    def test_canonical_2026_existing_source_preview(self):
        root = TOOLS.parent
        source = root / DATA_SOURCE_ROOT / "nfl" / "player-game-long-gains" / "2026.json"
        if not source.exists():
            self.skipTest("Canonical 2026 long-gains not in this checkout")
        game_id = json.loads(source.read_text(encoding="utf-8"))["Games"][0]["GameID"]
        detail = preview(root, 2026, game_id)
        self.assertEqual(detail["PlayByPlay"]["Coverage"], "partial")
        self.assertFalse(detail["PlayByPlay"]["FullPlayByPlayAvailable"])
        self.assertTrue(all(row["CanonicalPlayerID"] for row in detail["PlayByPlay"]["LongGains"]["Records"]))



def _week_stats():
    def player(cid, team, opp, yards, targets):
        return {
            "CanonicalPlayerID": cid, "Team": team, "OpponentTeam": opp,
            "PlayerName": cid, "Position": "RB", "SeasonType": "REG",
            "Week": 6, "Stats": {
                "game_id": "2026_06_HOU_JAX",
                "carries": 4, "rushing_yards": yards,
                "targets": targets, "receptions": targets,
                "receiving_yards": 10, "passing_yards": 0,
            },
        }
    return {
        "SchemaVersion": 2, "Season": 2026, "Week": 6,
        "SourceDataset": "nflverse.player-stats", "Finalized": False,
        "Records": [player("NFLP-a", "HOU", "JAX", 21, 2),
                    player("NFLP-b", "JAX", "HOU", -2, 1)],
    }


def _week_snaps():
    def player(cid, team, opp, offense):
        return {
            "CanonicalPlayerID": cid, "Team": team, "OpponentTeam": opp,
            "PlayerName": cid, "Position": "RB", "GameType": "REG", "Week": 6,
            "GameID": "2026_06_HOU_JAX", "OffenseSnaps": offense,
            "OffensePct": .5, "DefenseSnaps": 0, "DefensePct": 0.0,
            "SpecialTeamsSnaps": 3, "SpecialTeamsPct": .1,
        }
    return {
        "SchemaVersion": 2, "Season": 2026, "Week": 6,
        "SourceDataset": "nflverse.snap-counts", "Finalized": False,
        "Records": [player("NFLP-a", "HOU", "JAX", 35),
                    player("NFLP-b", "JAX", "HOU", 42)],
    }


class NflGameDetailCanonicalWeekGroupsTests(unittest.TestCase):
    def test_player_stats_team_totals_and_snaps_use_canonical_player_identity(self):
        detail = build_nfl_game_detail(
            build_nfl_games(*inputs()), "2026_06_HOU_JAX",
            _preview_gains(), _week_stats(), _week_snaps(),
        )
        self.assertEqual(detail["SchemaVersion"], 2)
        self.assertEqual(detail["PlayerStats"]["Status"], "available")
        self.assertEqual(detail["SnapCounts"]["Status"], "available")
        self.assertIs(detail["PlayerStats"]["SourceFinalized"], False)
        self.assertEqual(
            [t["Team"] for t in detail["TeamStats"]["Teams"]], ["HOU", "JAX"],
        )
        self.assertEqual(
            [t["Stats"]["rushing_yards"] for t in detail["TeamStats"]["Teams"]],
            [21, -2],
        )
        self.assertEqual(detail["TeamStats"]["Teams"][0]["Stats"]["carries"], 4)
        self.assertIsNone(detail["TeamStats"]["Teams"][0]["Stats"]["fg_att"])
        self.assertEqual(detail["SnapCounts"]["Players"][0]["CanonicalPlayerID"], "NFLP-b")
        self.assertEqual(detail["SnapCounts"]["Players"][1]["Snaps"]["OffenseSnaps"], 35)
        self.assertFalse(detail["PlayByPlay"]["FullPlayByPlayAvailable"])

    def test_absent_week_sources_remain_unavailable_not_zero(self):
        detail = build_nfl_game_detail(build_nfl_games(*inputs()), "2026_06_HOU_JAX")
        for key in ("PlayerStats", "TeamStats", "SnapCounts"):
            self.assertEqual(detail[key]["Status"], "unavailable")
        self.assertIsNone(detail["PlayerStats"]["Players"])
        self.assertIsNone(detail["TeamStats"]["Teams"])
        self.assertIsNone(detail["SnapCounts"]["Players"])
        empty = _week_stats()
        empty["Records"] = []
        detail = build_nfl_game_detail(
            build_nfl_games(*inputs()), "2026_06_HOU_JAX",
            player_stats=empty,
        )
        self.assertEqual(detail["PlayerStats"]["Status"], "unavailable")
        self.assertIsNone(detail["PlayerStats"]["Players"])

    def test_one_team_in_source_is_partial_without_fabricating_other_team(self):
        stats = _week_stats()
        stats["Records"] = stats["Records"][:1]
        detail = build_nfl_game_detail(
            build_nfl_games(*inputs()), "2026_06_HOU_JAX",
            player_stats=stats,
        )
        self.assertEqual(detail["PlayerStats"]["Status"], "partial")
        self.assertEqual(detail["TeamStats"]["Status"], "partial")
        self.assertEqual(detail["TeamStats"]["Teams"][0]["Stats"]["rushing_yards"], 21)
        self.assertEqual(detail["TeamStats"]["Teams"][1]["Status"], "unavailable")
        self.assertIsNone(detail["TeamStats"]["Teams"][1]["Stats"])

    def test_stats_and_snap_week_identity_and_metrics_fail_closed(self):
        for mutation in ("stats-week", "stats-team", "stats-duplicate",
                         "stats-negative", "stats-bad-type", "snap-week",
                         "snap-pct", "snap-duplicate", "snap-team", "cross-team"):
            with self.subTest(mutation=mutation):
                stats, snaps = _week_stats(), _week_snaps()
                if mutation == "stats-week":
                    stats["Week"] = 7
                elif mutation == "stats-team":
                    stats["Records"][0]["Team"] = "NYG"
                elif mutation == "stats-duplicate":
                    stats["Records"].append(copy.deepcopy(stats["Records"][0]))
                elif mutation == "stats-negative":
                    stats["Records"][0]["Stats"]["targets"] = -1
                elif mutation == "stats-bad-type":
                    stats["Records"][0]["Stats"]["carries"] = 1.5
                elif mutation == "snap-week":
                    snaps["Records"][0]["Week"] = 7
                elif mutation == "snap-pct":
                    snaps["Records"][0]["OffensePct"] = float("nan")
                elif mutation == "snap-duplicate":
                    snaps["Records"].append(copy.deepcopy(snaps["Records"][0]))
                elif mutation == "snap-team":
                    snaps["Records"][0]["Team"] = "NYG"
                elif mutation == "cross-team":
                    snaps["Records"][0]["Team"] = "JAX"
                    snaps["Records"][0]["OpponentTeam"] = "HOU"
                with self.assertRaises(ValueError):
                    build_nfl_game_detail(
                        build_nfl_games(*inputs()), "2026_06_HOU_JAX",
                        player_stats=stats, snap_counts=snaps,
                    )

    def test_readonly_cli_uses_only_matching_week_and_does_not_write(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            docs = {
                root / "data-derived" / "nfl-games" / "2026.json": build_nfl_games(*inputs()),
                root / DATA_SOURCE_ROOT / "nfl" / "player-stats" / "2026" / "06.json": _week_stats(),
                root / DATA_SOURCE_ROOT / "nfl" / "snap-counts" / "2026" / "06.json": _week_snaps(),
            }
            for path, doc in docs.items():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(doc), encoding="utf-8")
            files_before = {p.relative_to(root): p.read_bytes() for p in root.rglob("*.json")}
            result = preview(root, 2026, "2026_06_HOU_JAX")
            self.assertEqual(result["PlayerStats"]["Status"], "available")
            self.assertEqual(result["SnapCounts"]["Status"], "available")
            files_after = {p.relative_to(root): p.read_bytes() for p in root.rglob("*.json")}
            self.assertEqual(files_before, files_after)

    def test_real_canonical_2026_week_10_complete_game_join(self):
        root = TOOLS.parent
        stats = root / DATA_SOURCE_ROOT / "nfl" / "player-stats" / "2026" / "10.json"
        snaps = root / DATA_SOURCE_ROOT / "nfl" / "snap-counts" / "2026" / "10.json"
        if not stats.is_file() or not snaps.is_file():
            self.skipTest("2026 week 10 canonical source partitions not available")
        detail = preview(root, 2026, "2026_10_WAS_NYG")
        self.assertEqual(detail["PlayerStats"]["Status"], "available")
        self.assertEqual(detail["SnapCounts"]["Status"], "available")
        self.assertEqual([x["Team"] for x in detail["TeamStats"]["Teams"]], ["WAS", "NYG"])
        self.assertTrue(all(x["CanonicalPlayerID"] for x in detail["PlayerStats"]["Players"]))
        self.assertTrue(all(x["CanonicalPlayerID"] for x in detail["SnapCounts"]["Players"]))
        self.assertFalse(detail["PlayByPlay"]["FullPlayByPlayAvailable"])



if __name__ == "__main__":
    unittest.main()
