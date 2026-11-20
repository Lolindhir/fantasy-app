"""Synthetic Fast cases for nfl-player-availability-v1 (Issue #1590). No real players or seasons are wired in."""
from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from derived_data_lib.nfl_player_availability import AvailabilityError, derive_nfl_player_availability  # noqa: E402
import nfl_player_availability_materialize as materializer  # noqa: E402

SEASON = 2031


def game(week, away, home, gtype="REG"):
    return {"GameID": f"{SEASON}_{week:02d}_{away}_{home}", "GameType": gtype, "Week": week, "AwayTeam": away, "HomeTeam": home}


def player(n):
    return f"NFLP-test-{n}"


def report(pid, week, status=None, practice=None, reasons=("Knee",), team="AAA", gtype="REG", identity=True):
    return {
        "CanonicalPlayerID": pid if identity else None, "Week": week, "SourceTeams": [team], "ObservedReportCount": 1,
        "Observations": [{"ReportStatus": status or "", "PracticeStatus": practice or "", "GameType": gtype, "SourceTeam": team,
                          "Reasons": {"report_primary_injury": reasons[0] if reasons else "", "report_secondary_injury": "",
                                      "practice_primary_injury": "", "practice_secondary_injury": ""}}],
    }


def roster(pid, team, status="ACT", code="A01", gtype="REG"):
    return {"CanonicalPlayerID": pid, "Team": team, "Status": status, "StatusDescription": code, "GameType": gtype}


def snaps(game_id, played=(), idle=(), unresolved_team=None):
    rows = [{"CanonicalPlayerID": p, "GameID": game_id, "Team": "AAA", "OffenseSnaps": 10, "DefenseSnaps": 0, "SpecialTeamsSnaps": 0} for p in played]
    rows += [{"CanonicalPlayerID": p, "GameID": game_id, "Team": "AAA", "OffenseSnaps": 0, "DefenseSnaps": 0, "SpecialTeamsSnaps": 0} for p in idle]
    if unresolved_team:
        rows.append({"CanonicalPlayerID": None, "GameID": game_id, "Team": unresolved_team, "OffenseSnaps": 5, "DefenseSnaps": 0, "SpecialTeamsSnaps": 0})
    return rows


def build(reports=(), rosters=None, snap_rows=None, stats=None, games=None, final=True, season=SEASON):
    games = games if games is not None else [game(1, "AAA", "BBB"), game(2, "CCC", "BBB"), game(3, "AAA", "BBB"), game(4, "AAA", "CCC")]
    injuries = {"Season": season, "ProductVersion": "nfl-injuries-v1", "SourceAssetSha256": "x", "IdentityGraphFingerprint": "y",
                "ObservedPlayerWeeks": list(reports)}
    final_games = [{"GameID": g["GameID"], "Final": final} for g in games]
    return derive_nfl_player_availability(
        season, injuries=injuries,
        rosters={w: {"Week": w, "Records": r} for w, r in (rosters or {}).items()},
        snap_counts={w: {"Week": w, "Records": r} for w, r in (snap_rows or {}).items()},
        player_stats={w: {"Week": w, "Records": r} for w, r in (stats or {}).items()},
        schedule={"Season": season, "Games": games}, finality={"Season": season, "Games": final_games},
    )


def one(document, week, pid):
    matches = [r for r in document["Records"] if r["Week"] == week and r["CanonicalPlayerID"] == pid]
    assert len(matches) == 1, matches
    return matches[0]


class StateTests(unittest.TestCase):
    def test_out_did_not_play_is_not_played_reported(self):
        p, q = player(1), player(2)
        doc = build([report(p, 1, "Out")], {1: [roster(p, "AAA")]}, {1: snaps(game(1, "AAA", "BBB")["GameID"], played=[q])})
        rec = one(doc, 1, p)
        self.assertEqual(rec["State"], "not-played-reported")
        self.assertEqual(rec["Report"][0]["Game"], "Out")
        self.assertEqual(rec["Participation"], {"State": "not-played", "Evidence": "snap-counts"})

    def test_out_but_played_stays_visible_as_played(self):
        p = player(1)
        doc = build([report(p, 1, "Out")], {1: [roster(p, "AAA")]}, {1: snaps(game(1, "AAA", "BBB")["GameID"], played=[p])})
        self.assertEqual(one(doc, 1, p)["State"], "played")
        self.assertEqual(one(doc, 1, p)["Report"][0]["Game"], "Out")

    def test_questionable_played(self):
        p = player(1)
        doc = build([report(p, 1, "Questionable")], {1: [roster(p, "AAA")]}, {1: snaps(game(1, "AAA", "BBB")["GameID"], played=[p])})
        self.assertEqual(one(doc, 1, p)["State"], "played")

    def test_reserve_without_report(self):
        p = player(1)
        doc = build([], {1: [roster(p, "AAA", "RES", "R01")]}, {1: snaps(game(1, "AAA", "BBB")["GameID"], played=[player(9)])})
        rec = one(doc, 1, p)
        self.assertEqual(rec["State"], "not-played-reserve")
        self.assertIsNone(rec["Report"])
        self.assertEqual(rec["Roster"], {"Status": "RES", "Code": "R01"})

    def test_inactive_without_report_is_outside_population(self):
        p = player(1)
        doc = build([], {1: [roster(p, "AAA", "INA", "I01")]}, {1: snaps(game(1, "AAA", "BBB")["GameID"], played=[player(9)])})
        self.assertEqual(doc["Records"], [])

    def test_inactive_with_report_keeps_roster_status(self):
        p = player(1)
        doc = build([report(p, 1, "Doubtful")], {1: [roster(p, "AAA", "INA", "I01")]}, {1: snaps(game(1, "AAA", "BBB")["GameID"], played=[player(9)])})
        rec = one(doc, 1, p)
        self.assertEqual(rec["State"], "not-played-reported")
        self.assertEqual(rec["Roster"]["Status"], "INA")

    def test_bye_week(self):
        p = player(1)
        doc = build([report(p, 2, "Questionable", team="AAA")], {2: [roster(p, "AAA")]})
        rec = one(doc, 2, p)
        self.assertEqual(rec["State"], "bye")
        self.assertIsNone(rec["GameID"])

    def test_missing_roster_row_uses_report_team(self):
        p = player(1)
        doc = build([report(p, 1, "Out", team="AAA")], {}, {1: snaps(game(1, "AAA", "BBB")["GameID"], played=[player(9)])})
        rec = one(doc, 1, p)
        self.assertEqual(rec["State"], "not-played-reported")
        self.assertIsNone(rec["Roster"])
        self.assertEqual(rec["Team"], "AAA")

    def test_cancelled_game_is_unknown_not_bye(self):
        games = [game(16, "BUF", "NYJ"), game(18, "BUF", "NYJ")]
        p = player(1)
        doc = build([report(p, 17, "Out", team="BUF")], {17: [roster(p, "BUF")]}, games=games, season=2022)
        rec = one(doc, 17, p)
        self.assertEqual(rec["State"], "unknown")
        self.assertEqual(rec["Participation"]["Evidence"], "cancelled-game")

    def test_report_without_identity_is_counted_not_recorded(self):
        doc = build([report(None, 1, "Out", identity=False)], {1: []}, {1: []})
        self.assertEqual(doc["Records"], [])
        self.assertEqual(doc["Quality"]["ReportObservationsWithoutIdentity"], 1)

    def test_game_not_final_is_unknown(self):
        p = player(1)
        doc = build([report(p, 1, "Questionable")], {1: [roster(p, "AAA")]}, final=False)
        self.assertEqual(one(doc, 1, p)["State"], "unknown")

    def test_no_snap_coverage_without_stats_is_unknown(self):
        p = player(1)
        doc = build([report(p, 1, "Out")], {1: [roster(p, "AAA")]})
        rec = one(doc, 1, p)
        self.assertEqual(rec["State"], "unknown")
        self.assertEqual(rec["Participation"], {"State": "unknown", "Evidence": None})

    def test_stats_row_is_participation_evidence_without_snaps(self):
        p = player(1)
        gid = game(1, "AAA", "BBB")["GameID"]
        doc = build([report(p, 1, "Questionable")], {1: [roster(p, "AAA")]}, stats={1: [{"CanonicalPlayerID": p, "Stats": {"game_id": gid}}]})
        self.assertEqual(one(doc, 1, p)["Participation"], {"State": "played", "Evidence": "player-stats"})

    def test_unresolved_snap_row_of_same_team_blocks_not_played_claim(self):
        p = player(1)
        gid = game(1, "AAA", "BBB")["GameID"]
        doc = build([report(p, 1, "Out")], {1: [roster(p, "AAA")]}, {1: snaps(gid, played=[player(9)], unresolved_team="AAA")})
        self.assertEqual(one(doc, 1, p)["State"], "unknown")
        doc = build([report(p, 1, "Out")], {1: [roster(p, "AAA")]}, {1: snaps(gid, played=[player(9)], unresolved_team="BBB")})
        self.assertEqual(one(doc, 1, p)["State"], "not-played-reported")

    def test_postseason_week_without_game_is_skipped(self):
        games = [game(1, "AAA", "BBB"), game(19, "CCC", "BBB", "WC")]
        p = player(1)
        doc = build([report(p, 19, "Out", team="AAA", gtype="WC")], {}, games=games)
        self.assertEqual(doc["Records"], [])

    def test_roster_status_without_season_data_is_not_a_signal(self):
        p = player(1)
        doc = build([], {1: [roster(p, "AAA", None, "A01")]}, {1: snaps(game(1, "AAA", "BBB")["GameID"], played=[player(9)])})
        self.assertEqual(doc["Records"], [])
        self.assertFalse(doc["Inputs"]["RosterStatusAvailable"])


class DeterminismTests(unittest.TestCase):
    def test_same_inputs_same_bytes_and_input_not_mutated(self):
        p = player(1)
        reports = [report(p, 1, "Out")]
        frozen = copy.deepcopy(reports)
        args = (reports, {1: [roster(p, "AAA")]}, {1: snaps(game(1, "AAA", "BBB")["GameID"], played=[player(9)])})
        first, second = build(*args), build(*args)
        self.assertEqual(materializer.serialize(first), materializer.serialize(second))
        self.assertEqual(reports, frozen)
        json.loads(materializer.serialize(first))

    def test_season_mismatch_fails_closed(self):
        with self.assertRaises(AvailabilityError):
            derive_nfl_player_availability(SEASON, injuries=None, rosters={}, snap_counts={}, player_stats={},
                                           schedule={"Season": SEASON + 1, "Games": []}, finality={"Season": SEASON, "Games": []})

    def test_materializer_semantic_no_op(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nfl = root / "data-source" / "nfl"
            (nfl / "schedules").mkdir(parents=True)
            (nfl / "game-finality").mkdir(parents=True)
            games = [game(1, "AAA", "BBB")]
            (nfl / "schedules" / f"{SEASON}.json").write_text(json.dumps({"Season": SEASON, "Games": games}))
            (nfl / "game-finality" / f"{SEASON}.json").write_text(json.dumps({"Season": SEASON, "Games": [{"GameID": games[0]["GameID"], "Final": True}]}))
            (nfl / "weekly-rosters" / str(SEASON)).mkdir(parents=True)
            (nfl / "weekly-rosters" / str(SEASON) / "01.json").write_text(json.dumps({"Week": 1, "Records": [roster(player(1), "AAA", "RES", "R01")]}))
            first = materializer.materialize(root, SEASON, write=True)
            second = materializer.materialize(root, SEASON, write=True)
            self.assertTrue(first["Written"])
            self.assertFalse(second["Written"])
            self.assertEqual(materializer.discover_seasons(root), [SEASON])


if __name__ == "__main__":
    unittest.main()
