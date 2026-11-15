from __future__ import annotations

import copy
import csv
import gzip
import hashlib
import json
import sys
import subprocess
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from data_roots import DATA_SOURCE_ROOT
from derived_data_lib.nfl_games import build_nfl_games
from derived_data_lib.nfl_team_snap_usage import infer_team_snap_volumes
from nfl_games_materialize import materialize, discover_seasons
from nfl_pbp_metric_field_audit import audit as audit_pbp_catalog_fields, reconcile_original_game_row
from nfl_pbp_team_metric_reconcile import (
    reconcile as reconcile_pbp_team_season,
    _delta_distribution,
    _unknown_comparison_eligibility,
)


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
        self.assertEqual(detail["SnapCounts"]["Players"][0]["CanonicalPlayerID"], "NFLP-a")
        self.assertEqual(detail["SnapCounts"]["Players"][0]["Snaps"]["OffenseSnaps"], 35)
        self.assertIsNone(detail["SnapCounts"]["Teams"][0]["Offense"]["TotalSnaps"])
        self.assertEqual(detail["SnapCounts"]["Teams"][0]["Offense"]["Status"],
                         "insufficient-participants")
        self.assertFalse(detail["PlayByPlay"]["FullPlayByPlayAvailable"])

    def test_absent_week_sources_remain_unavailable_not_zero(self):
        detail = build_nfl_game_detail(build_nfl_games(*inputs()), "2026_06_HOU_JAX")
        for key in ("PlayerStats", "TeamStats", "SnapCounts"):
            self.assertEqual(detail[key]["Status"], "unavailable")
        self.assertIsNone(detail["PlayerStats"]["Players"])
        self.assertIsNone(detail["TeamStats"]["Teams"])
        self.assertIsNone(detail["SnapCounts"]["Players"])
        self.assertIsNone(detail["SnapCounts"]["Teams"])
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


    def test_team_snap_totals_only_when_shares_identify_one_denominator(self):
        def row(team, offense, defense, special):
            return {
                "Team": team,
                "Snaps": {
                    "OffenseSnaps": offense[0], "OffensePct": offense[1],
                    "DefenseSnaps": defense[0], "DefensePct": defense[1],
                    "SpecialTeamsSnaps": special[0], "SpecialTeamsPct": special[1],
                },
            }
        players = [
            row("HOU", (35, .5), (40, .5), (9, .3)),
            row("HOU", (70, 1.), (80, 1.), (15, .5)),
            row("JAX", (40, .5), (35, .5), (6, .2)),
            row("JAX", (80, 1.), (70, 1.), (21, .7)),
        ]
        result = infer_team_snap_volumes(players, "HOU", "JAX")
        self.assertEqual([[r[u]["TotalSnaps"] for u in
                           ("Offense", "Defense", "SpecialTeams")] for r in result],
                         [[70, 80, 30], [80, 70, 30]])
        self.assertNotEqual(result[0]["Offense"]["ObservedPlayerSnapSum"], 70)
        self.assertIsNone(infer_team_snap_volumes(None, "HOU", "JAX"))
        altered = copy.deepcopy(players)
        altered[0]["Snaps"]["OffensePct"] = None
        unavailable = infer_team_snap_volumes(altered, "HOU", "JAX")
        self.assertEqual(unavailable[0]["Offense"]["Status"], "missing-player-fields")
        self.assertIsNone(unavailable[0]["Offense"]["TotalSnaps"])
        altered = copy.deepcopy(players)
        altered[0]["Snaps"]["OffenseSnaps"] = 1
        altered[0]["Snaps"]["OffensePct"] = .01
        altered[1]["Snaps"]["OffenseSnaps"] = 1
        altered[1]["Snaps"]["OffensePct"] = .01
        unavailable = infer_team_snap_volumes(altered, "HOU", "JAX")
        self.assertEqual(unavailable[0]["Offense"]["Status"], "ambiguous-rounded-shares")
        altered = copy.deepcopy(players)
        altered[2]["Snaps"]["DefenseSnaps"] = 71
        altered[2]["Snaps"]["DefensePct"] = 1.
        altered[3]["Snaps"]["DefenseSnaps"] = 71
        altered[3]["Snaps"]["DefensePct"] = 1.
        unavailable = infer_team_snap_volumes(altered, "HOU", "JAX")
        self.assertEqual(unavailable[0]["Offense"]["Status"],
                         "opponent-offense-defense-mismatch")
        self.assertIsNone(unavailable[1]["Defense"]["TotalSnaps"])

    def test_real_2025_week_one_team_snap_totals_are_unique(self):
        root = TOOLS.parent
        index_file = root / DATA_DERIVED_ROOT / "nfl-games" / "2025.json"
        snaps_file = root / DATA_SOURCE_ROOT / "nfl" / "snap-counts" / "2025" / "01.json"
        if not index_file.is_file() or not snaps_file.is_file():
            self.skipTest("2025 Week 1 canonical game index / snap source unavailable")
        index = json.loads(index_file.read_text(encoding="utf-8"))
        source = json.loads(snaps_file.read_text(encoding="utf-8"))
        self.assertEqual(source["SourceDataset"], "nflverse.snap-counts")
        game_ids = sorted({r["GameID"] for r in source["Records"]})
        self.assertEqual(len(game_ids), 16)
        observed = 0
        for gid in game_ids:
            detail = build_nfl_game_detail(index, gid, snap_counts=source)
            self.assertFalse(detail["SnapCounts"]["TeamTotalsAreOfficiallyVerified"])
            team_rows = detail["SnapCounts"]["Teams"]
            for team in team_rows:
                for unit in ("Offense", "Defense", "SpecialTeams"):
                    self.assertEqual(team[unit]["Status"],
                                     "unique-rounded-share-denominator")
                    self.assertIsInstance(team[unit]["TotalSnaps"], int)
                    observed += 1
            if gid == "2025_01_ARI_NO":
                self.assertEqual(
                    [[t[k]["TotalSnaps"] for k in ("Offense", "Defense", "SpecialTeams")]
                     for t in team_rows],
                    [[66, 75, 27], [75, 66, 27]],
                )
        self.assertEqual(observed, 96)

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



# PBP CP3 tests use a synthetic nflverse-shaped gzip, NOT a claim that a
# real season release was downloaded or that a game's completeness was proven.
_PBP_CSV_FIELDS = [
    "game_id", "play_id", "season", "season_type", "week",
    "home_team", "away_team", "qtr", "drive", "down",
    "ydstogo", "yardline_100", "game_seconds_remaining",
    "posteam", "defteam", "play_type", "desc", "epa", "success",
    "qb_dropback", "pass_attempt", "passer_player_id", "future_provider_field",
    "two_point_attempt", "third_down_converted", "yards_gained",
]


def _pbp_row(**overrides):
    row = {
        "game_id": "2026_06_HOU_JAX", "play_id": "33", "season": "2026",
        "season_type": "REG", "week": "6", "home_team": "JAX",
        "away_team": "HOU", "qtr": "1", "drive": "1", "down": "1",
        "ydstogo": "10", "yardline_100": "78", "game_seconds_remaining": "3450",
        "posteam": "HOU", "defteam": "JAX", "play_type": "pass",
        "desc": "Pass complete for first down", "epa": "1.257",
        "success": "1", "qb_dropback": "1", "pass_attempt": "1",
        "passer_player_id": "00-0031234", "future_provider_field": "preserved",
        "two_point_attempt": "0", "third_down_converted": "0",
        "yards_gained": "12",
    }
    row.update(overrides)
    return row


def _write_original_pbp_gzip(path: Path, rows: list[dict], fields=None) -> None:
    with gzip.open(path, "wt", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fields or _PBP_CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


class NflOriginalPbpGamePreviewTests(unittest.TestCase):
    def test_original_game_plays_selected_sorted_and_all_source_columns_retained(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            index_file = root / "data-derived" / "nfl-games" / "2026.json"
            index_file.parent.mkdir(parents=True)
            index_file.write_text(json.dumps(build_nfl_games(*inputs())), encoding="utf-8")
            pbp = root / "play_by_play_2026.csv.gz"
            rows = [
                _pbp_row(play_id="90", qtr="2", down="", ydstogo="", epa="",
                         success="", play_type="kickoff", posteam="", defteam="",
                         future_provider_field="special,quoted"),
                _pbp_row(play_id="33.0", future_provider_field="äöü"),
                _pbp_row(play_id="50", play_type="run", epa="-0.25", success="0"),
                _pbp_row(game_id="2026_06_OTHER_MATCH", play_id="7"),
            ]
            _write_original_pbp_gzip(pbp, rows)
            before = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            expected = hashlib.sha256(pbp.read_bytes()).hexdigest()
            result = preview(root, 2026, "2026_06_HOU_JAX", pbp, expected)
            self.assertEqual(result["SchemaVersion"], 3)
            self.assertEqual(result["PlayerStats"]["Status"], "unavailable")
            self.assertEqual(result["SnapCounts"]["Status"], "unavailable")
            block = result["PlayByPlay"]["OriginalPlays"]
            self.assertEqual(block["SourceAssetSHA256"], expected)
            self.assertEqual([p["PlayID"] for p in block["Plays"]], [33, 50, 90])
            self.assertEqual(block["PlayCount"], 3)
            self.assertEqual(block["Plays"][0]["SourceRow"]["future_provider_field"], "äöü")
            self.assertEqual(block["Plays"][2]["SourceRow"]["future_provider_field"], "special,quoted")
            self.assertIsNone(block["Plays"][2]["Down"])
            self.assertIsNone(block["Plays"][2]["EPA"])
            self.assertIs(block["Plays"][0]["Success"], True)
            self.assertIs(block["Plays"][1]["Success"], False)
            self.assertEqual(block["Plays"][0]["EPA"], 1.257)
            self.assertFalse(result["PlayByPlay"]["FullPlayByPlayAvailable"])
            self.assertFalse(block["CompletenessVerified"])
            self.assertEqual(block["Status"], "present-unverified-completeness")
            scan = block["SourceReadAudit"]
            self.assertEqual(scan["SeasonSourceRowsScanned"], 4)
            self.assertEqual(scan["DistinctGameIDsInAsset"], 2)
            self.assertEqual(scan["MatchedGameRowCount"], 3)
            self.assertEqual(scan["UniqueValidatedPlayIDs"], 3)
            self.assertEqual([scan["FirstPlayID"], scan["LastPlayID"]], [33, 90])
            self.assertTrue(scan["GzipStreamReadToEOF"])
            self.assertTrue(scan["ExpectedSHA256Matched"])
            self.assertFalse(scan["OriginalAssetCompletenessVerified"])
            self.assertFalse(scan["GamePlayCompletenessVerified"])
            self.assertEqual(block["Analytics"]["SourcePlayCount"], 3)
            after = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            self.assertEqual(before, after)

    def test_gameid_unknown_digest_and_missing_csv_columns_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            index_file = root / "data-derived" / "nfl-games" / "2026.json"
            index_file.parent.mkdir(parents=True)
            index_file.write_text(json.dumps(build_nfl_games(*inputs())), encoding="utf-8")
            pbp = root / "season.csv.gz"
            _write_original_pbp_gzip(pbp, [_pbp_row(game_id="2026_06_SF_LA")])
            with self.assertRaisesRegex(ValueError, "not found"):
                preview(root, 2026, "2026_06_HOU_JAX", pbp)
            _write_original_pbp_gzip(pbp, [_pbp_row()])
            with self.assertRaisesRegex(ValueError, "SHA256"):
                preview(root, 2026, "2026_06_HOU_JAX", pbp, "f" * 64)
            with self.assertRaisesRegex(ValueError, "requires"):
                preview(root, 2026, "2026_06_HOU_JAX", expected_sha256="f" * 64)
            fields = [f for f in _PBP_CSV_FIELDS if f != "play_id"]
            with gzip.open(pbp, "wt", encoding="utf-8", newline="") as output:
                writer = csv.DictWriter(output, fieldnames=fields)
                writer.writeheader()
                writer.writerow({name: "" for name in fields})
            with self.assertRaisesRegex(ValueError, "Missing original PBP columns"):
                preview(root, 2026, "2026_06_HOU_JAX", pbp)

    def test_invalid_original_pbp_game_and_play_rows_are_rejected(self):
        idx = build_nfl_games(*inputs())
        for mutation in (
            "duplicate-play", "missing-id", "fractional-id", "wrong-week",
            "wrong-season", "wrong-type", "wrong-home", "wrong-defense",
            "same-teams", "invalid-down", "invalid-ydstogo", "invalid-epa",
            "invalid-success", "invalid-quarter", "missing-source-row",
        ):
            with self.subTest(mutation=mutation):
                rows = [_pbp_row(), _pbp_row(play_id="37")]
                a = rows[0]
                if mutation == "duplicate-play":
                    rows[1]["play_id"] = "33.0"
                elif mutation == "missing-id":
                    a["play_id"] = ""
                elif mutation == "fractional-id":
                    a["play_id"] = "33.5"
                elif mutation == "wrong-week":
                    a["week"] = "7"
                elif mutation == "wrong-season":
                    a["season"] = "2025"
                elif mutation == "wrong-type":
                    a["season_type"] = "POST"
                elif mutation == "wrong-home":
                    a["home_team"] = "NYG"
                elif mutation == "wrong-defense":
                    a["defteam"] = "DAL"
                elif mutation == "same-teams":
                    a["defteam"] = "HOU"
                elif mutation == "invalid-down":
                    a["down"] = "5"
                elif mutation == "invalid-ydstogo":
                    a["ydstogo"] = "-8"
                elif mutation == "invalid-epa":
                    a["epa"] = "Infinity"
                elif mutation == "invalid-success":
                    a["success"] = "2"
                elif mutation == "invalid-quarter":
                    a["qtr"] = "0"
                elif mutation == "missing-source-row":
                    rows[0] = None
                with self.assertRaises(ValueError):
                    build_nfl_game_detail(idx, "2026_06_HOU_JAX", pbp_rows=rows)

    def test_large_complete_game_shape_does_not_truncate_at_longgain_rows(self):
        idx = build_nfl_games(*inputs())
        rows = [
            _pbp_row(play_id=str(n), qtr=str(1 + n // 70),
                     play_type="pass" if n % 2 else "run", 
                     epa=str((n % 7 - 3) / 10))
            for n in range(1, 271)
        ]
        detail = build_nfl_game_detail(idx, "2026_06_HOU_JAX", pbp_rows=rows)
        plays = detail["PlayByPlay"]["OriginalPlays"]["Plays"]
        self.assertEqual(len(plays), 270)
        self.assertEqual(plays[0]["PlayID"], 1)
        self.assertEqual(plays[-1]["PlayID"], 270)
        self.assertEqual(len({p["PlayID"] for p in plays}), 270)
        self.assertFalse(detail["PlayByPlay"]["FullPlayByPlayAvailable"])



    def test_provisional_pbp_metrics_use_only_source_plays_and_observed_denominators(self):
        rows = [
            _pbp_row(play_id="1", down="3", play_type="pass", posteam="HOU", defteam="JAX",
                     epa="1.5", success="1", yards_gained="25", third_down_converted="1"),
            _pbp_row(play_id="2", down="1", play_type="run", posteam="HOU", defteam="JAX",
                     epa="-0.5", success="0", yards_gained="12"),
            _pbp_row(play_id="3", down="3", play_type="pass", posteam="JAX", defteam="HOU",
                     epa="-2", success="0", yards_gained="0", third_down_converted="0"),
            _pbp_row(play_id="4", down="3", play_type="run", posteam="JAX", defteam="HOU",
                     epa="", success="", yards_gained="", third_down_converted=""),
            _pbp_row(play_id="5", down="3", play_type="pass", two_point_attempt="1",
                     epa="0.5", third_down_converted="1"),
            _pbp_row(play_id="6", down="", play_type="kickoff", posteam="", defteam="",
                     epa="", success=""),
            _pbp_row(play_id="7", play_type="pass", two_point_attempt="", epa="9.5"),
            _pbp_row(play_id="8", play_type="pass", posteam="", defteam="", epa="1"),
        ]
        detail = build_nfl_game_detail(
            build_nfl_games(*inputs()), "2026_06_HOU_JAX", pbp_rows=rows,
        )
        analytics = detail["PlayByPlay"]["OriginalPlays"]["Analytics"]
        self.assertEqual(analytics["DefinitionVersion"], 1)
        self.assertEqual(analytics["Status"], "provisional-unverified-game-completeness")
        self.assertEqual(analytics["SourcePlayCount"], 8)
        self.assertEqual(analytics["EligiblePlayCount"], 4)
        self.assertEqual(analytics["ExcludedNonScrimmageCount"], 1)
        self.assertEqual(analytics["ExcludedTwoPointAttemptCount"], 1)
        self.assertEqual(analytics["ExcludedUnknownTwoPointFlagCount"], 1)
        self.assertEqual(analytics["ExcludedUnassignedTeamCount"], 1)
        hou, jax = analytics["ByOffenseTeam"]
        self.assertEqual(hou["Team"], "HOU")
        self.assertEqual(hou["All"]["PlayCount"], 2)
        self.assertEqual(hou["All"]["EPA"], {
            "Observed": 2, "Missing": 0, "Sum": 1.0, "PerPlay": 0.5,
        })
        self.assertEqual(hou["All"]["Success"]["Rate"], 0.5)
        self.assertEqual(hou["All"]["Explosive"]["Rate"], 1.0)
        self.assertEqual(hou["ThirdDown"]["Conversions"]["Rate"], 1.0)
        self.assertEqual(jax["All"]["EPA"]["Observed"], 1)
        self.assertEqual(jax["All"]["EPA"]["Missing"], 1)
        self.assertEqual(jax["All"]["EPA"]["PerPlay"], -2.0)
        self.assertEqual(jax["All"]["Success"]["Observed"], 1)
        self.assertEqual(jax["All"]["Success"]["Rate"], 0.0)
        self.assertEqual(jax["All"]["Explosive"]["Missing"], 1)
        self.assertEqual(jax["ThirdDown"]["Conversions"]["Rate"], 0.0)
        self.assertEqual(analytics["ByDefenseTeam"][1]["Team"], "JAX")
        self.assertEqual(
            analytics["ByDefenseTeam"][1]["OffenseAllowed"], hou["All"],
        )
        self.assertFalse(detail["PlayByPlay"]["FullPlayByPlayAvailable"])
        self.assertIsNone(detail["PlayerStats"]["Players"])
        self.assertIsNone(detail["SnapCounts"]["Players"])

    def test_no_observed_metrics_never_become_fake_zero(self):
        row = _pbp_row(play_id="1", epa="", success="", yards_gained="",
                       down="3", third_down_converted="")
        doc = build_nfl_game_detail(
            build_nfl_games(*inputs()), "2026_06_HOU_JAX", pbp_rows=[row],
        )
        offense = doc["PlayByPlay"]["OriginalPlays"]["Analytics"]["ByOffenseTeam"][0]
        self.assertEqual(offense["All"]["PlayCount"], 1)
        self.assertIsNone(offense["All"]["EPA"]["PerPlay"])
        self.assertIsNone(offense["All"]["EPA"]["Sum"])
        self.assertIsNone(offense["All"]["Success"]["Rate"])
        self.assertIsNone(offense["All"]["Explosive"]["Rate"])
        self.assertIsNone(offense["ThirdDown"]["Conversions"]["Rate"])
        self.assertEqual(offense["All"]["EPA"]["Observed"], 0)

    def test_bad_analysis_flags_fail_closed_and_do_not_change_original_fields(self):
        for field, bad in (
            ("two_point_attempt", "2"), ("two_point_attempt", "invalid"),
            ("third_down_converted", "2"), ("yards_gained", "Infinity"),
        ):
            with self.subTest(field=field, bad=bad):
                row = _pbp_row(play_id="1", **{field: bad})
                with self.assertRaises(ValueError):
                    build_nfl_game_detail(
                        build_nfl_games(*inputs()), "2026_06_HOU_JAX", pbp_rows=[row],
                    )
        row = _pbp_row(play_id="1", yards_gained="-2")
        doc = build_nfl_game_detail(
            build_nfl_games(*inputs()), "2026_06_HOU_JAX", pbp_rows=[row],
        )
        self.assertEqual(doc["PlayByPlay"]["OriginalPlays"]["Plays"][0]["SourceRow"], row)
        self.assertEqual(
            doc["PlayByPlay"]["OriginalPlays"]["Analytics"]["ByOffenseTeam"][0]
            ["All"]["Explosive"]["Count"], 0,
        )

    def test_cli_summary_reports_provenance_without_full_source_rows_or_writes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            index_file = root / "data-derived" / "nfl-games" / "2026.json"
            index_file.parent.mkdir(parents=True)
            index_file.write_text(json.dumps(build_nfl_games(*inputs())), encoding="utf-8")
            gz = root / "play_by_play_2026.csv.gz"
            _write_original_pbp_gzip(gz, [
                _pbp_row(play_id="20", down="3", third_down_converted="1"),
                _pbp_row(play_id="30", down="3", third_down_converted="0"),
                _pbp_row(play_id="40", game_id="2026_06_OTHER_MATCH"),
            ])
            digest = hashlib.sha256(gz.read_bytes()).hexdigest()
            before = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            result = subprocess.run(
                [
                    sys.executable, str(TOOLS / "nfl_game_detail_preview.py"),
                    "--repo-root", str(root), "--season", "2026",
                    "--game-id", "2026_06_HOU_JAX", "--pbp-csv-gz", str(gz),
                    "--expected-sha256", digest, "--summary",
                ], check=True, text=True, capture_output=True,
            )
            report = json.loads(result.stdout)
            self.assertEqual(report["PlayCount"], 2)
            self.assertTrue(report["SourceReadAudit"]["GzipStreamReadToEOF"])
            self.assertEqual(report["SourceReadAudit"]["SeasonSourceRowsScanned"], 3)
            self.assertEqual(report["SourceReadAudit"]["DistinctGameIDsInAsset"], 2)
            self.assertEqual(report["Analytics"]["EligiblePlayCount"], 2)
            self.assertEqual(report["Analytics"]["ByOffenseTeam"][0]
                             ["ThirdDown"]["Conversions"]["Rate"], 0.5)
            self.assertNotIn('"SourceRow":', result.stdout)
            self.assertNotIn("Plays", report)
            after = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            self.assertEqual(before, after)

    def test_truncated_gzip_fails_before_producing_false_scan_success(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            index_file = root / "data-derived" / "nfl-games" / "2026.json"
            index_file.parent.mkdir(parents=True)
            index_file.write_text(json.dumps(build_nfl_games(*inputs())), encoding="utf-8")
            gz = root / "play_by_play_2026.csv.gz"
            _write_original_pbp_gzip(gz, [_pbp_row()])
            gz.write_bytes(gz.read_bytes()[:-7])
            with self.assertRaises((OSError, EOFError)):
                preview(root, 2026, "2026_06_HOU_JAX", gz)



# P0 original PBP catalog coverage tests. These synthesize provider-shaped
# CSV.GZ rows; they NEVER claim a real nflverse season was downloaded.
_AUDIT_CSV_FIELDS = [
    "game_id", "play_id", "season", "season_type", "week", "home_team",
    "away_team", "posteam", "defteam", "play_type", "down",
    "qb_dropback", "qb_scramble", "pass_attempt", "rush_attempt", "sack",
    "qb_spike", "two_point_attempt", "epa", "success", "third_down_converted",
    "passer_player_id", "receiver_player_id", "rusher_player_id",
]


def _audit_row(**overrides):
    row = {
        "game_id": "2025_18_WAS_PHI", "play_id": "42", "season": "2025",
        "season_type": "REG", "week": "18", "home_team": "PHI",
        "away_team": "WAS", "posteam": "WAS", "defteam": "PHI",
        "play_type": "pass", "down": "3",
        "qb_dropback": "1", "qb_scramble": "0", "pass_attempt": "1",
        "rush_attempt": "0", "sack": "0", "qb_spike": "0",
        "two_point_attempt": "0", "epa": "1.2", "success": "1",
        "third_down_converted": "1", "passer_player_id": "00-0030001",
        "receiver_player_id": "00-0030002", "rusher_player_id": "",
    }
    row.update(overrides)
    return row


def _write_audit_fixture(root, rows, columns=None, catalog=None):
    from textwrap import dedent
    source = root / "play_by_play_2025.csv.gz"
    with gzip.open(source, "wt", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns or _AUDIT_CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    catalog_path = root / "nfl-games-pbp-metrics.yaml"
    catalog_path.write_text(catalog or dedent("""\
        schemaVersion: 1
        catalogVersion: 1
        metricFamilies:
          - family: passing-defense
            priority: P1
            candidates:
              - id: pass_epa
                sourceFields: [pass_attempt, sack, epa]
              - id: air_yards
                sourceFields: [air_yards, pass_attempt]
              - id: rb_targets
                sourceFields: [receiver_player_id, defteam]
                requiredJoin: historical-position
        """), encoding="utf-8")
    return source, catalog_path


class NflPbpMetricSourceFieldAuditTests(unittest.TestCase):
    def test_gzip_stream_provenance_field_nulls_and_catalog_missingness(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, catalog = _write_audit_fixture(root, [
                _audit_row(),
                _audit_row(play_id="43.0", play_type="run", down="1",
                           qb_dropback="1", qb_scramble="1",
                           pass_attempt="0", rush_attempt="1", sack="0",
                           epa="", success="", receiver_player_id="",
                           rusher_player_id="00-0030003"),
                _audit_row(game_id="2025_18_JAX_TEN", play_id="1", week="18",
                           home_team="TEN", away_team="JAX", posteam="JAX",
                           defteam="TEN", play_type="pass", down="2",
                           sack="1", epa="-0.7", success="0",
                           passer_player_id="legacy-not-gsis"),
            ])
            expected = hashlib.sha256(source.read_bytes()).hexdigest()
            metadata = root / "metadata.json"
            metadata.write_text(json.dumps({
                "provider": "nflverse", "partition": {"season": 2025},
                "upstreamContentHashSha256": expected,
                "upstreamByteSize": source.stat().st_size,
                "projectionStats": {"sourceRowCount": 3},
            }), encoding="utf-8")
            before = {p.name: p.read_bytes() for p in root.iterdir() if p.is_file()}
            result = audit_pbp_catalog_fields(
                path=source, season=2025, catalog_path=catalog,
                metadata_path=metadata, expected_sha256=expected,
            )
            self.assertEqual(result["Status"], "observed-source-asset-not-certified-full-pbp")
            self.assertEqual(result["RawSeasonRowCount"], 3)
            self.assertEqual(result["DistinctGameIDs"], 2)
            self.assertEqual(result["DistinctGamePlayKeys"], 3)
            self.assertEqual(result["CohortRowCounts"]["PassPlayType"], 2)
            self.assertEqual(result["CohortRowCounts"]["RunPlayType"], 1)
            self.assertEqual(result["CohortRowCounts"]["QBDropback"], 3)
            self.assertEqual(result["CohortRowCounts"]["ThirdDown"], 1)
            self.assertEqual(result["FieldCoverage"]["epa"]["Cohorts"]["AllRows"], {
                "Rows": 3, "NonNull": 2, "Missing": 1,
            })
            self.assertFalse(result["FieldCoverage"]["air_yards"]["HeaderPresent"])
            metric = {m["MetricID"]: m for m in result["MetricFieldCoverage"]}
            self.assertEqual(len(metric), 3)
            self.assertEqual(metric["air_yards"]["MissingSourceColumns"], ["air_yards"])
            self.assertEqual(metric["air_yards"]["Status"], "source-fields-missing")
            self.assertEqual(metric["pass_epa"]["MissingSourceColumns"], [])
            self.assertFalse(metric["pass_epa"]["ReadyToPublish"])
            self.assertTrue(metric["rb_targets"]["PositionJoinRequired"])
            self.assertEqual(result["ProviderPlayerIDCoverage"]
                             ["passer_player_id"]["NonGSISFormatOccurrences"], 1)
            checks = result["DictionarySemanticCrosschecks"]
            self.assertEqual(checks["PassAttemptAndSackRows"], 1)
            self.assertEqual(checks["QBDropbackAndScrambleRows"], 1)
            self.assertEqual(checks["SuccessEPAComparableRows"], 2)
            self.assertEqual(checks["SuccessPositiveEPAMismatches"], 0)
            self.assertTrue(result["ArchivedProjectionComparison"]["ArchivedSHA256Matches"])
            self.assertTrue(result["ArchivedProjectionComparison"]["ArchivedRowCountMatches"])
            self.assertTrue(result["GzipStreamReadToEOF"])
            self.assertFalse(result["UpstreamFullGameCompletenessVerified"])
            self.assertFalse(result["PlayerPositionHistoricalJoinVerified"])
            after = {p.name: p.read_bytes() for p in root.iterdir() if p.is_file()}
            self.assertEqual(before, after)

    def test_original_play_identity_and_integrity_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, catalog = _write_audit_fixture(root, [_audit_row()])
            with self.assertRaisesRegex(ValueError, "expected SHA256"):
                audit_pbp_catalog_fields(path=source, season=2025, catalog_path=catalog,
                                         expected_sha256="f" * 64)
            cases = (
                ([_audit_row(), _audit_row()], "Duplicate"),
                ([_audit_row(season="2024")], "wrong season"),
                ([_audit_row(play_id="1.5")], "Invalid play_id"),
                ([_audit_row(), _audit_row(play_id="50", home_team="NYG")], "conflicting"),
                ([_audit_row(season_type="PRE")], "invalid game context"),
            )
            for rows, error in cases:
                with self.subTest(error=error):
                    _write_audit_fixture(root, rows)
                    with self.assertRaisesRegex(ValueError, error):
                        audit_pbp_catalog_fields(path=source, season=2025, catalog_path=catalog)
            _write_audit_fixture(root, [_audit_row()])
            source.write_bytes(source.read_bytes()[:-6])
            with self.assertRaises((EOFError, OSError)):
                audit_pbp_catalog_fields(path=source, season=2025, catalog_path=catalog)

    def test_missing_core_fields_bad_csv_width_and_duplicate_catalog_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            columns = [f for f in _AUDIT_CSV_FIELDS if f != "play_id"]
            source, catalog = _write_audit_fixture(root, [{x: "" for x in columns}], columns)
            with self.assertRaisesRegex(ValueError, "Missing original PBP identity"):
                audit_pbp_catalog_fields(path=source, season=2025, catalog_path=catalog)
            with gzip.open(source, "wt", encoding="utf-8", newline="") as out:
                out.write(",".join(_AUDIT_CSV_FIELDS) + "\n")
                out.write("1,2,3,4\n")
            with self.assertRaisesRegex(ValueError, "row width"):
                audit_pbp_catalog_fields(path=source, season=2025, catalog_path=catalog)
            catalog.write_text(
                "catalogVersion: 1\nmetricFamilies:\n  - family: foo\n    candidates:\n"
                "      - id: duplicate\n        sourceFields: [game_id]\n"
                "      - id: duplicate\n        sourceFields: [play_id]\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "Duplicate or malformed"):
                audit_pbp_catalog_fields(path=source, season=2025, catalog_path=catalog)

    def test_snapshot_drift_and_invalid_flags_report_without_claiming_publication_ready(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, catalog = _write_audit_fixture(root, [
                _audit_row(play_id="1", pass_attempt="5"),
            ])
            metadata = root / "metadata.json"
            metadata.write_text(json.dumps({
                "provider": "nflverse", "partition": {"season": 2025},
                "upstreamContentHashSha256": "0" * 64,
                "upstreamByteSize": 99,
                "projectionStats": {"sourceRowCount": 99},
            }), encoding="utf-8")
            result = audit_pbp_catalog_fields(
                path=source, season=2025, catalog_path=catalog, metadata_path=metadata,
            )
            self.assertEqual(result["BinaryFieldInvalidCounts"]["pass_attempt"], 1)
            self.assertFalse(result["ArchivedProjectionComparison"]["ArchivedSHA256Matches"])
            self.assertFalse(result["ArchivedProjectionComparison"]["ArchivedByteCountMatches"])
            self.assertFalse(result["ArchivedProjectionComparison"]["ArchivedRowCountMatches"])
            self.assertFalse(result["MetricFieldCoverage"][0]["ReadyToPublish"])

    def test_cli_emits_only_aggregate_audit_json_and_no_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, catalog = _write_audit_fixture(root, [_audit_row()])
            before = {p.name: p.read_bytes() for p in root.iterdir() if p.is_file()}
            result = subprocess.run([
                sys.executable, str(TOOLS / "nfl_pbp_metric_field_audit.py"),
                "--repo-root", str(root), "--season", "2025",
                "--pbp-csv-gz", str(source), "--catalog", str(catalog),
            ], check=True, capture_output=True, text=True)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["RawSeasonRowCount"], 1)
            self.assertEqual(payload["MetricCandidateCount"], 3)
            self.assertNotIn('"SourceRow"', result.stdout)
            self.assertNotIn('"Plays"', result.stdout)
            after = {p.name: p.read_bytes() for p in root.iterdir() if p.is_file()}
            self.assertEqual(before, after)


    def test_original_pbp_game_index_reconciliation_context_alias_and_postseason(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            index = root / "2000.json"
            index.write_text(json.dumps({
                "SchemaVersion": 1, "Season": 2000, "Games": [
                    {"GameID": "2000_01_SD_OAK", "GameType": "REG",
                     "Week": 1, "AwayTeam": "SD", "HomeTeam": "OAK", "Final": True},
                    {"GameID": "2000_19_NYG_PHI", "GameType": "WC",
                     "Week": 19, "AwayTeam": "NYG", "HomeTeam": "PHI", "Final": True},
                ],
            }), encoding="utf-8")
            rows = [
                _audit_row(season="2000", game_id="2000_01_SD_OAK", week="1",
                           away_team="LAC", home_team="LV"),
                _audit_row(season="2000", game_id="2000_19_NYG_PHI",
                           season_type="POST", week="19", away_team="NYG",
                           home_team="PHI", play_id="43"),
            ]
            source, catalog = _write_audit_fixture(root, rows)
            result = audit_pbp_catalog_fields(
                path=source, season=2000, catalog_path=catalog,
                game_index_path=index,
            )
            context = result["CanonicalGameContextReconciliation"]
            self.assertEqual(context["SourceRowsCompared"], 2)
            self.assertEqual(context["HistoricalAliasContextRows"], 1)
            self.assertEqual(context["ExactContextRows"], 1)
            self.assertEqual(context["UnknownGameIDRows"], 0)
            self.assertEqual(context["MismatchedContextRows"], 0)
            self.assertTrue(context["AllObservedSourceRowsJoinCanonicalGames"])
            self.assertFalse(context["OriginalSeasonPlayCoverageVerified"])

            broken = _audit_row(season="2000", game_id="2000_01_SD_OAK",
                                week="1", away_team="DAL", home_team="LV")
            self.assertEqual(reconcile_original_game_row(
                broken, {g["GameID"]: g for g in json.loads(index.read_text())
                         ["Games"]}, 2000,
            )[0], "mismatched-context")
            unknown = _audit_row(game_id="2000_01_UNKNOWN")
            self.assertEqual(reconcile_original_game_row(
                unknown, {g["GameID"]: g for g in json.loads(index.read_text())
                          ["Games"]}, 2000,
            )[0], "unknown-game-id")

    def test_observed_canonical_game_context_from_real_persisted_pbp_subset(self):
        """Genuine repo PBP subset evidence, NOT upstream full-PBP verification."""
        from collections import Counter
        total = Counter()
        for season, expected_rows in ((2000, 148), (2024, 81),
                                      (2025, 71), (2026, 46)):
            with self.subTest(season=season):
                index_path = TOOLS.parent / "data-derived" / "nfl-games" / f"{season}.json"
                source_path = (TOOLS.parent / "data-source" / "providers" /
                               "nflverse" / "special-teams-fumble-events" /
                               f"raw-{season}.json")
                index = json.loads(index_path.read_text(encoding="utf-8"))
                source = json.loads(source_path.read_text(encoding="utf-8"))
                self.assertEqual(len(source["Records"]), expected_rows)
                known = {row["GameID"]: row for row in index["Games"]}
                for row in source["Records"]:
                    label, finalized = reconcile_original_game_row(row, known, season)
                    self.assertIn(label, ("exact-context", "historical-franchise-alias"))
                    self.assertTrue(finalized)
                    total[label] += 1
        self.assertEqual(total["exact-context"], 316)
        self.assertEqual(total["historical-franchise-alias"], 30)

    def test_original_game_context_reconciliation_never_hides_unresolved_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            idx = root / "game-index.json"
            idx.write_text(json.dumps({
                "SchemaVersion": 1, "Season": 2025, "Games": [
                    {"GameID": "2025_18_WAS_PHI", "GameType": "REG",
                     "Week": 18, "AwayTeam": "WAS", "HomeTeam": "PHI", "Final": True},
                    {"GameID": "2025_18_JAX_TEN", "GameType": "REG",
                     "Week": 18, "AwayTeam": "JAX", "HomeTeam": "TEN", "Final": False},
                    {"GameID": "2025_18_ATL_DAL", "GameType": "REG",
                     "Week": 18, "AwayTeam": "ATL", "HomeTeam": "DAL", "Final": True},
                ],
            }), encoding="utf-8")
            rows = [
                _audit_row(play_id="1"),
                _audit_row(play_id="2", game_id="2025_18_JAX_TEN",
                           away_team="JAX", home_team="TEN"),
                _audit_row(play_id="3", game_id="2025_18_ATL_DAL",
                           away_team="ATL", home_team="SEA"),
                _audit_row(play_id="4", game_id="2025_18_UNKNOWN",
                           away_team="ATL"),
            ]
            source, catalog = _write_audit_fixture(root, rows)
            doc = audit_pbp_catalog_fields(
                path=source, season=2025, catalog_path=catalog,
                game_index_path=idx,
            )
            audit = doc["CanonicalGameContextReconciliation"]
            self.assertEqual(audit["ExactContextRows"], 2)
            self.assertEqual(audit["MatchedNonFinalGameRows"], 1)
            self.assertEqual(audit["MismatchedContextRows"], 1)
            self.assertEqual(audit["UnknownGameIDRows"], 1)
            self.assertFalse(audit["AllObservedSourceRowsJoinCanonicalGames"])
            self.assertEqual(len(audit["Examples"]), 2)
            self.assertFalse(audit["OriginalSeasonPlayCoverageVerified"])




class NflPbpTeamMetricCandidateTests(unittest.TestCase):
    """No GSIS mapping is needed for the team-only research candidates."""

    @staticmethod
    def _metrics(rows):
        detail = build_nfl_game_detail(
            build_nfl_games(*inputs()), "2026_06_HOU_JAX", pbp_rows=rows,
        )
        return detail["PlayByPlay"]["OriginalPlays"]["Analytics"]["CatalogTeamMetricCandidates"]

    def test_all_17_team_only_candidates_are_separated_from_six_position_metrics(self):
        doc = self._metrics([_pbp_row(play_id="1")])
        self.assertEqual(len(doc["CandidateIDs"]), 17)
        self.assertEqual(len(doc["DeferredPositionDependentIDs"]), 6)
        import yaml
        catalog = yaml.safe_load(
            (TOOLS.parent / ".ai-context/manual/nfl-games-pbp-metrics.yaml").read_text(encoding="utf-8")
        )
        expected = {
            item["id"]
            for family in catalog["metricFamilies"]
            if family["family"] != "position-conditional"
            for item in family["candidates"]
            if not item.get("requiredJoin") and not family.get("sharedJoin")
        }
        self.assertEqual(set(doc["CandidateIDs"]), expected)
        self.assertFalse(doc["RequiredCanonicalPlayerID"])
        self.assertFalse(doc["CoverageVerified"])
        self.assertIn("not-publishable", doc["Status"])
        self.assertEqual(doc["ByDefenseTeam"][0]["Team"], "HOU")
        self.assertEqual(doc["ByDefenseTeam"][1]["Team"], "JAX")
        self.assertEqual(
            set(doc["CandidateIDs"]),
            set(doc["ByDefenseTeam"][1]["Metrics"]),
        )
        # This phase must not access canonical player IDs or position mappings.
        self.assertNotIn('"CanonicalPlayerID":', json.dumps(doc))

    def test_sacks_are_dropbacks_but_not_true_pass_attempts_and_incompletions_are_zero_explosives(self):
        plays = [
            _pbp_row(
                play_id="1", down="3", yardline_100="15", drive="1",
                epa="1.5", success="1", qb_dropback="1", pass_attempt="1",
                sack="0", qb_spike="0", rush_attempt="0", complete_pass="1",
                passing_yards="25", yards_after_catch="5", air_yards="20",
                third_down_converted="1", first_down="1",
            ),
            _pbp_row(
                play_id="2", down="2", yardline_100="60", drive="2",
                epa="-1.0", success="0", qb_dropback="1", pass_attempt="1",
                sack="1", qb_spike="0", rush_attempt="0", complete_pass="0",
                third_down_converted="0",
            ),
            _pbp_row(
                play_id="3", play_type="run", down="1", yardline_100="70",
                drive="3", epa="-0.5", success="0", qb_dropback="0",
                pass_attempt="0", rush_attempt="1", qb_scramble="0",
                rushing_yards="12", first_down="1",
            ),
            _pbp_row(
                play_id="4", down="1", yardline_100="40", drive="4",
                epa="-0.2", success="0", qb_dropback="1", pass_attempt="1",
                sack="0", qb_spike="0", rush_attempt="0", complete_pass="0",
                passing_yards="", air_yards="10",
            ),
        ]
        doc = self._metrics(plays)
        m = doc["ByDefenseTeam"][1]["Metrics"]
        self.assertEqual(doc["EligibleScrimmagePlayCount"], 4)
        self.assertEqual(m["offensive_dropbacks_faced"]["Value"], 3)
        self.assertEqual(m["pass_attempts_faced"]["Value"], 2)
        self.assertEqual(m["rush_attempts_faced"]["Value"], 1)
        self.assertEqual(m["rush_attempts_faced"]["ConfirmedQBScrambleCount"], 0)
        self.assertEqual(m["rush_attempts_faced"]["UnknownScrambleFlagCount"], 0)
        self.assertEqual(m["rush_epa_per_play_allowed"]["Value"], -0.5)
        self.assertEqual(m["rush_success_rate_allowed"]["Value"], 0.0)
        self.assertEqual(m["rush_explosive_10_rate_allowed"]["Value"], 1.0)
        self.assertEqual(m["rush_first_down_rate_allowed"]["Value"], 1.0)
        self.assertEqual(m["pass_epa_per_attempt_allowed"]["Value"], 0.65)
        self.assertEqual(m["dropback_epa_per_play_allowed"]["Value"], 0.1)
        self.assertEqual(m["dropback_success_rate_allowed"]["Value"], 0.3333)
        self.assertEqual(m["pass_explosive_20_rate_allowed"]["Value"], 0.5)
        self.assertEqual(m["pass_yac_per_completion_allowed"]["Value"], 5.0)
        self.assertEqual(m["air_yards_per_attempt_allowed"]["Value"], 15.0)
        self.assertEqual(m["third_down_conversion_rate_allowed"]["Value"], 1.0)
        self.assertEqual(m["red_zone_epa_and_success_allowed"]["EPA"]["Value"], 1.5)
        self.assertEqual(m["down_distance_efficiency_allowed"]["Bins"]["D3:7-10"]["EPA"]["Observed"], 1)
        self.assertEqual(m["drive_start_context"]["DistinctObservedDrives"], 4)
        self.assertFalse(doc["CoverageVerified"])

    def test_scramble_is_in_rush_and_dropback_and_unknown_scramble_is_not_zero(self):
        doc = self._metrics([
            _pbp_row(play_id="1", play_type="run", pass_attempt="0",
                     rush_attempt="1", qb_scramble="1", qb_dropback="1",
                     rushing_yards="8", epa="0.5"),
            _pbp_row(play_id="2", play_type="run", pass_attempt="0",
                     rush_attempt="1", qb_scramble="", qb_dropback="0",
                     rushing_yards="3", epa="-0.2"),
        ])
        metrics = doc["ByDefenseTeam"][1]["Metrics"]
        self.assertEqual(metrics["rush_attempts_faced"]["Value"], 2)
        self.assertEqual(metrics["rush_attempts_faced"]["ConfirmedQBScrambleCount"], 1)
        self.assertEqual(metrics["rush_attempts_faced"]["UnknownScrambleFlagCount"], 1)
        self.assertEqual(metrics["offensive_dropbacks_faced"]["Value"], 1)

    def test_missing_flags_remain_unknown_not_zero_or_false(self):
        doc = self._metrics([_pbp_row(
            play_id="1", pass_attempt="1", sack="", qb_spike="0",
            complete_pass="", qb_dropback="1", rush_attempt="",
            epa="", success="", yards_after_catch="",
        )])
        m = doc["ByDefenseTeam"][1]["Metrics"]
        self.assertIsNone(m["pass_attempts_faced"]["Value"])
        self.assertEqual(m["pass_attempts_faced"]["UnknownFlagCount"], 1)
        self.assertIsNone(m["pass_epa_per_attempt_allowed"]["Value"])
        self.assertEqual(m["dropback_epa_per_play_allowed"]["Missing"], 1)
        self.assertIsNone(m["rush_attempts_faced"]["Value"])
        self.assertIsNone(m["third_down_conversion_rate_allowed"]["Value"])

    def test_used_invalid_provider_flag_fails_closed(self):
        for field in ("pass_attempt", "qb_dropback", "rush_attempt",
                      "first_down", "two_point_attempt"):
            with self.subTest(field=field):
                row = _pbp_row(play_id="1", **{field: "2"})
                if field == "first_down":
                    row["rush_attempt"] = "1"
                # two_point_attempt is already rejected by the legacy CP4 guard;
                # the others are rejected by the additive team-only candidate guard.
                with self.assertRaises(ValueError):
                    self._metrics([row])



class NflPbpOriginalSeasonReconciliationTests(unittest.TestCase):
    """The synthetic fixture never proves that the real 2025 release was read."""

    def test_delta_distribution_is_signed_and_never_imputes_missing(self):
        self.assertEqual(_delta_distribution([])["Compared"], 0)
        self.assertIsNone(_delta_distribution([])["Sum"])
        self.assertIsNone(_delta_distribution([])["Mean"])
        self.assertIsNone(_delta_distribution([])["AbsoluteP90"])
        value = _delta_distribution([-3, 0, 1, 7])
        self.assertEqual((value["Positive"], value["Negative"], value["Zero"]),
                         (2, 1, 1))
        self.assertEqual(value["Sum"], 5)
        self.assertEqual(value["Median"], 0.5)
        self.assertEqual(value["Mean"], 1.25)
        self.assertEqual(value["MeanAbsolute"], 2.75)
        self.assertEqual(value["AbsoluteP50"], 1)
        self.assertEqual(value["AbsoluteP90"], 7)
        self.assertEqual(value["AbsoluteP99"], 7)

    def test_unknown_source_eligibility_is_metric_specific(self):
        base = {"posteam": "ARI", "two_point_attempt": "0",
                "play_type": "pass", "pass_attempt": "1",
                "rush_attempt": "0", "sack": "0", "qb_spike": "0"}
        def status(**changes):
            return _unknown_comparison_eligibility([{**base, **changes}], "ARI")
        self.assertEqual(status()["attempts"], 0)
        self.assertEqual(status()["passing_yards"], 0)
        self.assertEqual(status(two_point_attempt="")["attempts"], 1)
        self.assertEqual(status(two_point_attempt="")["carries"], 0)
        self.assertEqual(status(pass_attempt="")["passing_yards"], 1)
        self.assertEqual(status(sack="")["attempts"], 1)
        self.assertEqual(status(qb_spike="")["attempts"], 1)
        self.assertEqual(status(two_point_attempt="", sack="1")["attempts"], 0)
        self.assertEqual(status(two_point_attempt="", sack="1",
                                pass_attempt="")["attempts"], 0)
        self.assertEqual(status(two_point_attempt="", qb_spike="1")["attempts"], 0)
        self.assertEqual(status(two_point_attempt="1", pass_attempt="")["attempts"], 0)
        self.assertEqual(status(play_type="pass", pass_attempt="0",
                                two_point_attempt="")["attempts"], 0)
        self.assertEqual(status(play_type="run", pass_attempt="0",
                                rush_attempt="1", two_point_attempt="")["carries"], 1)
        self.assertEqual(status(play_type="run", pass_attempt="0",
                                rush_attempt="", two_point_attempt="0")["carries"], 1)
        self.assertEqual(_unknown_comparison_eligibility([base], "NO")["attempts"], 0)

    def fixture(self, root):
        game = "2025_01_ARI_NO"
        index = root / "data-derived/nfl-games/2025.json"
        index.parent.mkdir(parents=True, exist_ok=True)
        index.write_text(json.dumps({
            "SchemaVersion": 1, "Season": 2025,
            "Games": [{
                "GameID": game, "GameType": "REG", "Week": 1,
                "AwayTeam": "ARI", "HomeTeam": "NO", "Final": True,
            }],
        }), encoding="utf-8")
        stats = root / "data-source/nfl/player-stats/2025/01.json"
        stats.parent.mkdir(parents=True, exist_ok=True)
        stats.write_text(json.dumps({
            "SchemaVersion": 2, "Season": 2025, "Week": 1,
            "SourceDataset": "nflverse.player-stats",
            "Records": [{
                "Team": "ARI", "SeasonType": "REG",
                "Stats": {"game_id": game, "attempts": 1, "carries": 1,
                          "passing_yards": 25, "rushing_yards": 10},
            }, {
                "Team": "NO", "SeasonType": "REG",
                "Stats": {"game_id": game, "attempts": 1, "carries": 0,
                          "passing_yards": 0, "rushing_yards": 0},
            }],
        }), encoding="utf-8")
        catalog = root / ".ai-context/manual/nfl-games-pbp-metrics.yaml"
        catalog.parent.mkdir(parents=True, exist_ok=True)
        catalog.write_bytes(
            (TOOLS.parent / ".ai-context/manual/nfl-games-pbp-metrics.yaml").read_bytes()
        )
        def row(play_id, posteam, defteam, play_type, **kwargs):
            values = {
                "game_id": game, "season": "2025", "week": "1",
                "away_team": "ARI", "home_team": "NO", "play_id": str(play_id),
                "posteam": posteam, "defteam": defteam, "play_type": play_type,
                "two_point_attempt": "0", "sack": "0", "qb_spike": "0",
                "rush_attempt": "0", "qb_scramble": "0",
                "first_down": "0", "complete_pass": "0",
                "passing_yards": "0", "rushing_yards": "0",
                "yards_after_catch": "0", "air_yards": "0",
            }
            values.update(kwargs)
            return _pbp_row(**values)
        pbp_rows = [
            row(1, "ARI", "NO", "pass", epa="1.5", success="1",
                pass_attempt="1", qb_dropback="1", complete_pass="1",
                passing_yards="25", yards_gained="25", air_yards="20",
                yards_after_catch="5", first_down="1"),
            row(2, "ARI", "NO", "run", epa="0.5", success="1",
                pass_attempt="0", qb_dropback="0", rush_attempt="1",
                rushing_yards="10", yards_gained="10", first_down="1"),
            row(3, "NO", "ARI", "pass", epa="-0.5", success="0",
                pass_attempt="1", qb_dropback="1", complete_pass="0",
                passing_yards="0", yards_gained="0"),
        ]
        fields = sorted(set(_PBP_CSV_FIELDS) | {
            "sack", "qb_spike", "rush_attempt", "qb_scramble", "first_down",
            "complete_pass", "passing_yards", "rushing_yards",
            "yards_after_catch", "air_yards",
        })
        source = root / "play_by_play_2025.csv.gz"
        _write_original_pbp_gzip(source, pbp_rows, fields=fields)
        return source, hashlib.sha256(source.read_bytes()).hexdigest(), stats

    def test_synthetic_season_reconciles_game_and_offense_baselines_without_player_id(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, digest, _ = self.fixture(root)
            before = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            report = reconcile_pbp_team_season(root, source, 2025, digest)
            self.assertTrue(report["ReadOnly"])
            self.assertFalse(report["IdentityOrPositionJoinPerformed"])
            self.assertEqual(report["PBPSourceRowsScanned"], 3)
            self.assertEqual(report["OriginalGamesObserved"], 1)
            self.assertEqual(report["CanonicalGames"], 1)
            self.assertEqual(report["GameTeamCandidateRows"], 2)
            self.assertEqual(len(report["TeamOnlyMetricCandidateIDs"]), 17)
            coverage = report["TeamMetricResearchCoverage"]
            self.assertEqual(coverage["pass_epa_per_attempt_allowed"]["ObservedTeamGames"], 2)
            self.assertEqual(coverage["pass_epa_per_attempt_allowed"]["ObservedDenominator"], 2)
            self.assertEqual(coverage["pass_epa_per_attempt_allowed"]["ObservedWeightedMeanApprox"], 0.5)
            self.assertEqual(coverage["rush_epa_per_play_allowed"]["ObservedTeamGames"], 1)
            self.assertEqual(coverage["red_zone_epa_and_success_allowed.EPA"]["MissingTeamGames"], 2)
            self.assertEqual(report["PlayerStatsBaseline"]["GameTeamBaselines"], 2)
            self.assertEqual(report["Reconciliation"]["attempts"]["Equal"], 2)
            self.assertEqual(report["Reconciliation"]["attempts"]["DeltaDistribution"]["Zero"], 2)
            self.assertEqual(report["Reconciliation"]["attempts"]["DeltaDistribution"]["Sum"], 0)
            self.assertEqual(report["Reconciliation"]["carries"]["Equal"], 2)
            self.assertEqual(report["Reconciliation"]["passing_yards"]["Equal"], 2)
            self.assertEqual(report["Reconciliation"]["rushing_yards"]["Equal"], 1)
            self.assertEqual(report["Reconciliation"]["rushing_yards"]["MissingPBP"], 1)
            self.assertFalse(report["ProductionReady"])
            self.assertFalse(report["FullUpstreamPlayCompletenessVerified"])
            after = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            self.assertEqual(before, after)

    def test_reconciliation_reports_signed_deltas_and_largest_outliers(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, digest, stats = self.fixture(root)
            body = json.loads(stats.read_text(encoding="utf-8"))
            body["Records"][0]["Stats"]["attempts"] = 4
            body["Records"][1]["Stats"]["attempts"] = 0
            stats.write_text(json.dumps(body), encoding="utf-8")
            report = reconcile_pbp_team_season(root, source, 2025, digest)
            comp = report["Reconciliation"]["attempts"]
            self.assertEqual((comp["Compared"], comp["Equal"], comp["Different"]), (2, 0, 2))
            summary = comp["DeltaDistribution"]
            self.assertEqual((summary["Positive"], summary["Negative"], summary["Zero"]),
                             (1, 1, 0))
            self.assertEqual((summary["Sum"], summary["Mean"], summary["Median"]),
                             (-2, -1, -1))
            self.assertEqual((summary["Min"], summary["Max"], summary["AbsoluteP90"]),
                             (-3, 1, 3))
            self.assertEqual([row["DeltaPBPMinusPlayerStats"] for row in comp["Examples"]],
                             [-3, 1])
            self.assertEqual(report["Reconciliation"]["carries"]["DeltaDistribution"]["Zero"], 2)
            self.assertFalse(report["ProductionReady"])

    def test_unknown_two_point_eligibility_does_not_fake_equal_baselines(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, digest, _ = self.fixture(root)
            with gzip.open(source, "rt", encoding="utf-8", newline="") as stream:
                reader = csv.DictReader(stream)
                fields = reader.fieldnames
                rows = list(reader)
            rows[0]["two_point_attempt"] = ""
            _write_original_pbp_gzip(source, rows, fields=fields)
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            report = reconcile_pbp_team_season(root, source, 2025, digest)
            attempts = report["Reconciliation"]["attempts"]
            passing = report["Reconciliation"]["passing_yards"]
            self.assertEqual(attempts["MissingPBP"], 1)
            self.assertEqual(attempts["UnknownSourceEligibilityTeamGames"], 1)
            self.assertEqual(attempts["UnknownSourceEligibilityRows"], 1)
            self.assertEqual(attempts["Equal"], 1)
            self.assertEqual(attempts["DeltaDistribution"]["Compared"], 1)
            self.assertEqual(passing["MissingPBP"], 1)
            self.assertEqual(passing["UnknownSourceEligibilityRows"], 1)
            self.assertEqual(report["Reconciliation"]["carries"]["Equal"], 2)
            self.assertFalse(report["ProductionReady"])

    def test_original_source_pin_and_playerstats_unknown_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, digest, stats = self.fixture(root)
            with self.assertRaisesRegex(ValueError, "pinned SHA256"):
                reconcile_pbp_team_season(root, source, 2025, "f" * 64)
            body = json.loads(stats.read_text(encoding="utf-8"))
            del body["Records"][0]["Stats"]["attempts"]
            stats.write_text(json.dumps(body), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unknown required baseline"):
                reconcile_pbp_team_season(root, source, 2025, digest)

    def test_unknown_source_game_or_missing_stat_partition_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, digest, stats = self.fixture(root)
            stats.unlink()
            with self.assertRaisesRegex(ValueError, "Missing canonical PlayerStats"):
                reconcile_pbp_team_season(root, source, 2025, digest)
            source, digest, stats = self.fixture(root)
            with gzip.open(source, "rt", encoding="utf-8", newline="") as stream:
                reader = csv.DictReader(stream)
                fields = reader.fieldnames
                rows = list(reader)
            rows[0]["game_id"] = "2025_01_UNKNOWN_GAME"
            _write_original_pbp_gzip(source, rows, fields=fields)
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError, "does not reconcile"):
                reconcile_pbp_team_season(root, source, 2025, digest)

if __name__ == "__main__":
    unittest.main()
