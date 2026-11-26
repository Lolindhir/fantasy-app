"""Synthetic Fast cases for nfl-player-availability-v3 (Issues #1590, #1610, #1612). No real players or seasons are wired in."""
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
from derived_data_lib.nfl_player_availability import (  # noqa: E402
    BYE_CARRY_STATUSES, RESERVE_STATUSES, expected_population_keys, population_keys_sha256,
    verify_population_witness,
)

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


def roster(pid, team, status="ACT", code="A01", gtype="REG", position=None):
    return {"CanonicalPlayerID": pid, "Team": team, "Status": status, "StatusDescription": code, "GameType": gtype, "Position": position}


def snaps(game_id, played=(), idle=(), unresolved_team=None, token="TOKEN-X"):
    rows = [{"CanonicalPlayerID": p, "GameID": game_id, "Team": "AAA", "OffenseSnaps": 10, "DefenseSnaps": 0, "SpecialTeamsSnaps": 0} for p in played]
    rows += [{"CanonicalPlayerID": p, "GameID": game_id, "Team": "AAA", "OffenseSnaps": 0, "DefenseSnaps": 0, "SpecialTeamsSnaps": 0} for p in idle]
    if unresolved_team:
        rows.append({"CanonicalPlayerID": None, "SourceIDs": {"PFR": token} if token else {}, "GameID": game_id, "Team": unresolved_team, "OffenseSnaps": 5, "DefenseSnaps": 0, "SpecialTeamsSnaps": 0})
    return rows


def build(reports=(), rosters=None, snap_rows=None, stats=None, games=None, final=True, season=SEASON, tokens=None, **options):
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
        player_pfr_tokens=tokens, **options,
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
        self.assertEqual(rec["Participation"], {"State": "not-played", "Evidence": "snap-counts", "Plays": None})

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

    def test_inactive_without_report_outside_position_cut_is_not_recorded(self):
        p = player(1)
        doc = build([], {1: [roster(p, "AAA", "INA", "I01", position="OL")]}, {1: snaps(game(1, "AAA", "BBB")["GameID"], played=[player(9)])})
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
        self.assertEqual(rec["Participation"], {"State": "unknown", "Evidence": None, "Plays": None})

    def test_stats_row_is_participation_evidence_without_snaps(self):
        p = player(1)
        gid = game(1, "AAA", "BBB")["GameID"]
        doc = build([report(p, 1, "Questionable")], {1: [roster(p, "AAA")]}, stats={1: [{"CanonicalPlayerID": p, "Stats": {"game_id": gid}}]})
        self.assertEqual(one(doc, 1, p)["Participation"], {"State": "played", "Evidence": "player-stats", "Plays": None})

    def test_unresolved_snap_row_of_same_team_blocks_not_played_claim(self):
        p = player(1)
        gid = game(1, "AAA", "BBB")["GameID"]
        doc = build([report(p, 1, "Out")], {1: [roster(p, "AAA")]}, {1: snaps(gid, played=[player(9)], unresolved_team="AAA")})
        self.assertEqual(one(doc, 1, p)["State"], "unknown")
        doc = build([report(p, 1, "Out")], {1: [roster(p, "AAA")]}, {1: snaps(gid, played=[player(9)], unresolved_team="BBB")})
        self.assertEqual(one(doc, 1, p)["State"], "not-played-reported")

    def test_own_pfr_token_not_among_unresolved_tokens_excludes_the_gap(self):
        p = player(1)
        gid = game(1, "AAA", "BBB")["GameID"]
        rows = {1: snaps(gid, played=[player(9)], unresolved_team="AAA")}
        doc = build([report(p, 1, "Out")], {1: [roster(p, "AAA")]}, rows, tokens={p: ["OWN-1", "OWN-ALIAS"]})
        rec = one(doc, 1, p)
        self.assertEqual(rec["State"], "not-played-reported")
        self.assertEqual(rec["Participation"], {"State": "not-played", "Evidence": "snap-counts-token-excluded", "Plays": None})
        doc = build([], {1: [roster(p, "AAA", "RES", "R01")]}, rows, tokens={p: ["OWN-1"]})
        self.assertEqual(one(doc, 1, p)["State"], "not-played-reserve")

    def test_unresolved_token_equal_to_players_own_token_stays_unknown(self):
        p = player(1)
        gid = game(1, "AAA", "BBB")["GameID"]
        rows = {1: snaps(gid, played=[player(9)], unresolved_team="AAA", token="OWN-ALIAS")}
        doc = build([report(p, 1, "Out")], {1: [roster(p, "AAA")]}, rows, tokens={p: ["OWN-1", "OWN-ALIAS"]})
        rec = one(doc, 1, p)
        self.assertEqual(rec["State"], "unknown")
        self.assertEqual(rec["Participation"], {"State": "unknown", "Evidence": "snap-counts-identity-gap", "Plays": None})

    def test_player_without_pfr_token_or_row_without_token_stays_unknown(self):
        p = player(1)
        gid = game(1, "AAA", "BBB")["GameID"]
        rows = {1: snaps(gid, played=[player(9)], unresolved_team="AAA")}
        for tokens in (None, {}, {player(2): ["OTHER"]}):
            doc = build([report(p, 1, "Out")], {1: [roster(p, "AAA")]}, rows, tokens=tokens)
            self.assertEqual(one(doc, 1, p)["State"], "unknown")
        tokenless = {1: snaps(gid, played=[player(9)], unresolved_team="AAA", token=None)}
        doc = build([report(p, 1, "Out")], {1: [roster(p, "AAA")]}, tokenless, tokens={p: ["OWN-1"]})
        self.assertEqual(one(doc, 1, p)["State"], "unknown")

    def test_reserve_player_with_snap_identity_gap_is_not_played_reserve(self):
        p = player(1)
        gid = game(1, "AAA", "BBB")["GameID"]
        doc = build([], {1: [roster(p, "AAA", "RES", "R01")]}, {1: snaps(gid, played=[player(9)], unresolved_team="AAA")})
        rec = one(doc, 1, p)
        self.assertEqual(rec["State"], "not-played-reserve")
        self.assertEqual(rec["Participation"], {"State": "unknown", "Evidence": "snap-counts-identity-gap", "Plays": None})
        doc = build([report(p, 1, None, "Did Not Participate In Practice")], {1: [roster(p, "AAA", "RES", "R01")]}, {1: snaps(gid, played=[player(9)], unresolved_team="AAA")})
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



class ParticipationTests(unittest.TestCase):
    """v3 (Issue #1612): participation is positive-only evidence; absence is never evidence."""

    GID = game(1, "AAA", "BBB")["GameID"]

    def run_case(self, plays, snap_rows=None, **kw):
        p = player(1)
        doc = build([], {1: [roster(p, "AAA", position="WR")]}, snap_rows, participation_plays=({self.GID: {p: plays}} if plays is not None else None), **kw)
        return doc, one(doc, 1, p)

    def test_unknown_with_plays_becomes_played(self):
        doc, rec = self.run_case(7)
        self.assertEqual((rec["State"], rec["Played"], rec["Participation"]), ("played", True, {"State": "played", "Evidence": "participation", "Plays": 7}))

    def test_absent_participation_stays_unknown(self):
        _, rec = self.run_case(None)
        self.assertEqual((rec["State"], rec["Played"], rec["Participation"]["Plays"]), ("unknown", None, None))

    def test_conflict_with_snap_not_played_becomes_unknown(self):
        _, rec = self.run_case(26, {1: snaps(self.GID, played=[player(9)])})
        self.assertEqual((rec["State"], rec["Played"], rec["Participation"]["Evidence"]), ("unknown", None, "participation-conflict"))

    def test_single_play_does_not_override_not_played(self):
        _, rec = self.run_case(1, {1: snaps(self.GID, played=[player(9)])})
        self.assertEqual((rec["State"], rec["Played"], rec["Participation"]["Plays"]), ("healthy-scratch", False, 1))

    def test_snap_evidence_wins_and_keeps_plays(self):
        _, rec = self.run_case(3, {1: snaps(self.GID, played=[player(1)])})
        self.assertEqual((rec["State"], rec["Participation"]["Evidence"], rec["Participation"]["Plays"]), ("played", "snap-counts", 3))

    def test_parameters_are_recorded_in_the_document(self):
        doc, _ = self.run_case(7)
        self.assertEqual(doc["ProductVersion"], "nfl-player-availability-v3")
        self.assertEqual(doc["Inputs"]["ParticipationParameters"], {"MinPlaysUnknownToPlayed": 1, "MinPlaysConflict": 5})
        self.assertTrue(doc["Inputs"]["ParticipationAvailable"])


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
            (nfl / "identities").mkdir(parents=True)
            (nfl / "identities" / "players.json").write_text(json.dumps({"Players": [
                {"CanonicalPlayerID": player(1), "IDs": {"PFR": "OWN-1"}, "IDAliases": {"PFR": ["OWN-ALIAS"]}},
                {"CanonicalPlayerID": player(2), "IDs": {}, "IDAliases": {}}]}))
            self.assertEqual(materializer.pfr_tokens(nfl), {player(1): ["OWN-1", "OWN-ALIAS"]})
            first = materializer.materialize(root, SEASON, write=True)
            second = materializer.materialize(root, SEASON, write=True)
            self.assertTrue(first["Written"])
            self.assertFalse(second["Written"])
            self.assertEqual(materializer.discover_seasons(root), [SEASON])


if __name__ == "__main__":
    unittest.main()


class HealthyWeekTests(unittest.TestCase):
    """v2 (Issue #1610): every roster week of the position cut is a record with separate Available and Played fields."""

    def _g(self, week=1):
        return game(week, "AAA", "BBB")["GameID"]

    def test_healthy_played_week_is_recorded(self):
        p = player(1)
        doc = build([], {1: [roster(p, "AAA", position="WR")]}, {1: snaps(self._g(), played=[p])})
        rec = one(doc, 1, p)
        self.assertEqual((rec["State"], rec["Available"], rec["Played"]), ("played", "yes", True))
        self.assertIsNone(rec["Report"])

    def test_healthy_scratch_is_available_and_not_played(self):
        p = player(1)
        doc = build([], {1: [roster(p, "AAA", "INA", "I01", position="RB")]}, {1: snaps(self._g(), played=[player(9)])})
        rec = one(doc, 1, p)
        self.assertEqual((rec["State"], rec["Available"], rec["Played"]), ("healthy-scratch", "yes", False))
        self.assertEqual(doc["Quality"]["StateCounts"]["healthy-scratch"], 1)

    def test_bye_week_has_no_played_value(self):
        p = player(1)
        doc = build([report(p, 2, "Questionable")], {2: [roster(p, "AAA", position="QB")]})
        rec = one(doc, 2, p)
        self.assertEqual((rec["State"], rec["Available"], rec["Played"]), ("bye", "bye", None))

    def test_reserve_without_report_is_unavailable(self):
        p = player(1)
        doc = build([], {1: [roster(p, "AAA", "RES", "R01", position="OL")]}, {1: snaps(self._g(), played=[player(9)])})
        rec = one(doc, 1, p)
        self.assertEqual((rec["State"], rec["Available"], rec["Played"]), ("not-played-reserve", "no", False))

    def test_out_but_played_keeps_available_and_played_separate(self):
        p = player(1)
        doc = build([report(p, 1, "Out")], {1: [roster(p, "AAA", position="TE")]}, {1: snaps(self._g(), played=[p])})
        rec = one(doc, 1, p)
        self.assertEqual((rec["State"], rec["Available"], rec["Played"]), ("played", "no", True))

    def test_questionable_and_played_is_available(self):
        p = player(1)
        doc = build([report(p, 1, "Questionable")], {1: [roster(p, "AAA", position="K")]}, {1: snaps(self._g(), played=[p])})
        rec = one(doc, 1, p)
        self.assertEqual((rec["Available"], rec["Played"]), ("yes", True))

    def test_doubtful_is_unavailable(self):
        p = player(1)
        doc = build([report(p, 1, "Doubtful")], {1: [roster(p, "AAA", position="WR")]}, {1: snaps(self._g(), played=[player(9)])})
        self.assertEqual(one(doc, 1, p)["Available"], "no")

    def test_unknown_participation_keeps_played_null(self):
        p = player(1)
        not_final = build([], {1: [roster(p, "AAA", position="WR")]}, final=False)
        rec = one(not_final, 1, p)
        self.assertEqual((rec["State"], rec["Available"], rec["Played"]), ("unknown", "yes", None))
        gap = build([], {1: [roster(p, "AAA", position="WR")]}, {1: snaps(self._g(), played=[player(9)], unresolved_team="AAA", token=None)})
        rec = one(gap, 1, p)
        self.assertEqual((rec["State"], rec["Played"]), ("unknown", None))

    def test_cancelled_game_has_no_played_value(self):
        p = player(1)
        games = [game(16, "BUF", "NYJ"), game(18, "BUF", "NYJ")]
        doc = build([], {17: [roster(p, "BUF", position="WR")]}, games=games, season=2022)
        rec = one(doc, 17, p)
        self.assertEqual((rec["State"], rec["Played"]), ("unknown", None))

    def test_other_roster_status_outside_position_cut_is_not_recorded(self):
        p = player(1)
        doc = build([], {1: [roster(p, "AAA", "DEV", "P01", position="OL")]}, {1: snaps(self._g(), played=[player(9)])})
        self.assertEqual(doc["Records"], [])
        doc = build([report(p, 1, "Questionable")], {1: [roster(p, "AAA", "DEV", "P01", position="OL")]}, {1: snaps(self._g(), played=[player(9)])})
        self.assertEqual(one(doc, 1, p)["Available"], "no")

    def test_position_cut_is_configurable_and_does_not_limit_signal_weeks(self):
        p, q = player(1), player(2)
        rosters = {1: [roster(p, "AAA", position="OL"), roster(q, "AAA", "RES", "R01", position="OL")]}
        snap_rows = {1: snaps(self._g(), played=[p])}
        fantasy = build([], rosters, snap_rows)
        self.assertEqual({(r["Week"], r["CanonicalPlayerID"]) for r in fantasy["Records"]}, {(1, q), (2, q)})  # reserve week (and its bye) of any position stays
        everyone = build([], rosters, snap_rows, healthy_positions=None)
        self.assertEqual({r["CanonicalPlayerID"] for r in everyone["Records"]}, {p, q})
        self.assertIsNone(everyone["Quality"]["Population"]["Positions"])

    def test_no_gaps_every_roster_week_of_the_cut_has_one_record(self):
        ids = [player(i) for i in range(6)]
        rosters = {w: [roster(pid, "AAA", "INA" if i % 2 else "ACT", position="WR") for i, pid in enumerate(ids)] for w in (1, 3, 4)}
        rosters[4][0] = roster(ids[0], "AAA", "CUT", "C01", position="WR")  # not on the game-day roster in week 4 (G2: recorded as such)
        doc = build([], rosters, {1: snaps(self._g(1), played=ids[:3]), 3: snaps(self._g(3), played=ids[:3]), 4: snaps(game(4, "AAA", "CCC")["GameID"], played=ids[1:3])})
        keys = [(r["Week"], r["CanonicalPlayerID"]) for r in doc["Records"]]
        self.assertEqual(len(keys), len(set(keys)))
        expected = {(w, r["CanonicalPlayerID"]) for w, rows in rosters.items() for r in rows}
        expected |= {(2, pid) for pid in ids[1:]}  # G1: bye of AAA in week 2 for the players still attached to the team (not the one cut in week 4)
        expected.add((2, ids[0]))
        self.assertEqual(set(keys), expected)
        for rec in doc["Records"]:
            self.assertIn(rec["Available"], ("yes", "no", "unknown", "bye"))
            self.assertIn("Played", rec)

    def test_population_is_documented_in_quality(self):
        doc = build([], {1: [roster(player(1), "AAA", position="WR")]}, {1: snaps(self._g(), played=[player(1)])})
        population = doc["Quality"]["Population"]
        self.assertTrue(population["RosterWeeksIncluded"])
        self.assertEqual(population["Positions"], ["K", "QB", "RB", "TE", "WR"])
        statusless = build([report(player(1), 1, "Out")], {1: [{**roster(player(1), "AAA"), "Status": None}]}, {1: snaps(self._g(), played=[player(9)])})
        self.assertFalse(statusless["Quality"]["Population"]["RosterWeeksIncluded"])


class NonActiveAndByeTests(unittest.TestCase):
    """Issue #1616: G2 (other roster statuses are records) and G1 (bye weeks are records)."""

    def _g(self, week=1, away="AAA", home="BBB"):
        return game(week, away, home)["GameID"]

    def _status_week(self, status, code, position="WR", played=False):
        p = player(1)
        snap = snaps(self._g(), played=[p] if played else [player(9)])
        return p, one(build([], {1: [roster(p, "AAA", status, code, position=position)]}, {1: snap}), 1, p)

    def test_exempt_cut_and_practice_squad_are_not_on_active_roster(self):
        for status, code in (("EXE", "E02"), ("CUT", "R01"), ("DEV", "P01"), ("RET", "X01"), ("SUS", "S01")):
            _, rec = self._status_week(status, code)
            self.assertEqual((rec["State"], rec["Available"], rec["Played"]), ("not-on-active-roster", "no", False), status)
            self.assertEqual(rec["Roster"], {"Status": status, "Code": code})
            self.assertIsNone(rec["Report"])

    def test_non_active_status_respects_the_position_cut_and_playing_stays_visible(self):
        p = player(1)
        doc = build([], {1: [roster(p, "AAA", "DEV", "P01", position="OL")]}, {1: snaps(self._g(), played=[player(9)])})
        self.assertEqual(doc["Records"], [])
        _, rec = self._status_week("DEV", "P01", played=True)
        self.assertEqual((rec["State"], rec["Available"], rec["Played"]), ("played", "no", True))

    def test_non_active_status_with_report_keeps_the_report_state_and_unknown_stays_unknown(self):
        p = player(1)
        doc = build([report(p, 1, "Out")], {1: [roster(p, "AAA", "DEV", "P01", position="WR")]}, {1: snaps(self._g(), played=[player(9)])})
        self.assertEqual(one(doc, 1, p)["State"], "not-played-reported")
        not_final = build([], {1: [roster(p, "AAA", "CUT", "C01", position="WR")]}, final=False)
        self.assertEqual((one(not_final, 1, p)["State"], one(not_final, 1, p)["Played"]), ("unknown", None))

    def test_player_without_any_roster_row_has_no_record(self):
        doc = build([], {1: [roster(player(1), "AAA", position="WR")]}, {1: snaps(self._g(), played=[player(1)])})
        self.assertEqual({r["CanonicalPlayerID"] for r in doc["Records"]}, {player(1)})  # only the player with a roster row (week 1 and its bye week 2)
        self.assertEqual(len(doc["Records"]), 2)

    def test_bye_week_without_roster_row_is_a_record(self):
        p = player(1)
        doc = build([], {1: [roster(p, "AAA", position="WR")], 3: [roster(p, "AAA", position="WR")]},
                    {1: snaps(self._g(1), played=[p]), 3: snaps(self._g(3), played=[p])})
        rec = one(doc, 2, p)
        self.assertEqual((rec["State"], rec["Available"], rec["Played"]), ("bye", "bye", None))
        self.assertEqual(rec["Participation"], {"State": "no-game", "Evidence": "bye", "Plays": None})
        self.assertIsNone(rec["GameID"])
        self.assertIsNone(rec["Roster"])
        self.assertIsNone(rec["Report"])
        self.assertEqual((rec["Team"], rec["GameType"]), ("AAA", "REG"))

    def test_bye_follows_the_team_of_the_last_roster_week_before_the_bye(self):
        p = player(1)
        doc = build([], {1: [roster(p, "AAA", position="WR")], 3: [roster(p, "CCC", position="WR")]},
                    {1: snaps(self._g(1), played=[p]), 3: snaps(game(3, "CCC", "BBB")["GameID"], played=[p])},
                    games=[game(1, "AAA", "BBB"), game(2, "CCC", "BBB"), game(3, "CCC", "BBB"), game(4, "AAA", "CCC")])
        self.assertEqual(one(doc, 2, p)["Team"], "AAA")

    def test_no_bye_record_when_the_team_plays_or_the_attachment_ended(self):
        p, q, r = player(1), player(2), player(3)
        # week 1 -> week 2: AAA has the bye, CCC plays; q was cut (no bye); r is a practice squad player (stays attached).
        doc = build([], {1: [roster(p, "CCC", position="WR"), roster(q, "AAA", "CUT", "C01", position="WR"), roster(r, "AAA", "DEV", "P01", position="WR")]},
                    {1: snaps(self._g(1), played=[player(9)])},
                    games=[game(1, "AAA", "BBB"), game(2, "CCC", "BBB"), game(3, "AAA", "BBB"), game(4, "AAA", "CCC")])
        weeks = {(rec["Week"], rec["CanonicalPlayerID"]) for rec in doc["Records"]}
        self.assertNotIn((2, p), weeks)  # CCC plays in week 2 (and p simply has no row)
        self.assertNotIn((2, q), weeks)
        self.assertIn((2, r), weeks)

    def test_bye_needs_the_directly_preceding_roster_week_and_the_regular_season(self):
        p = player(1)
        gap = build([], {1: [roster(p, "AAA", position="WR")]}, {1: snaps(self._g(1), played=[p])},
                    games=[game(1, "AAA", "BBB"), game(2, "CCC", "BBB"), game(3, "AAA", "BBB"), game(4, "AAA", "CCC"), game(5, "AAA", "CCC")])
        self.assertIn(2, {rec["Week"] for rec in gap["Records"]})
        # postseason: the team has no game in the postseason week, last row was the final regular week -> no record
        post = build([], {4: [roster(p, "AAA", position="WR")]}, {4: snaps(game(4, "AAA", "CCC")["GameID"], played=[p])},
                     games=[game(1, "AAA", "BBB"), game(2, "CCC", "BBB"), game(3, "AAA", "BBB"), game(4, "AAA", "CCC"), game(5, "BBB", "CCC", "POST")])
        self.assertEqual({rec["Week"] for rec in post["Records"]}, {4})

    def test_bye_record_of_reserve_players_of_any_position(self):
        p = player(1)
        doc = build([], {1: [roster(p, "AAA", "RES", "R01", position="OL")]}, {1: snaps(self._g(1), played=[player(9)])})
        rec = one(doc, 2, p)
        self.assertEqual((rec["State"], rec["Played"]), ("bye", None))

    def test_bye_counts_and_population_are_documented(self):
        p = player(1)
        doc = build([], {1: [roster(p, "AAA", position="WR")]}, {1: snaps(self._g(1), played=[p])})
        self.assertEqual(doc["Quality"]["StateCounts"]["bye"], 1)
        self.assertTrue(doc["Quality"]["Population"]["ByeWeeksIncluded"])
        self.assertIn("not-on-active-roster", doc["Quality"]["StateCounts"])


class PopulationRevisionTests(unittest.TestCase):
    def test_revised_existing_roster_changes_future_bye_without_new_partition(self):
        p, q, r = player(1), player(2), player(3)
        games = [game(1, "AAA", "BBB"), game(1, "CCC", "DDD"), game(2, "CCC", "BBB"), game(3, "AAA", "CCC")]
        before = build([], {1: [roster(p, "CCC", "DEV", position="QB"),
                                roster(q, "AAA", "ACT", position="DL")]}, games=games)
        after_rows = {1: [roster(p, "AAA", "ACT", position="QB"),
                          roster(q, "AAA", "RES", position="DL"),
                          roster(r, "AAA", "DEV", position="TE")]}
        after = build([], after_rows, games=games)
        self.assertEqual(before["Quality"]["WeekCoverage"], after["Quality"]["WeekCoverage"])
        old_keys = verify_population_witness(before)
        new_keys = verify_population_witness(after)
        self.assertNotIn((2, p), old_keys)
        self.assertNotIn((2, q), old_keys)
        for pid in (p, q, r):
            self.assertIn((2, pid), new_keys)
            rec = one(after, 2, pid)
            self.assertEqual((rec["State"], rec["Available"], rec["Played"]), ("bye", "bye", None))
        self.assertNotEqual(before["Quality"]["Population"]["RecordKeysSha256"],
                            after["Quality"]["Population"]["RecordKeysSha256"])
        expected = expected_population_keys(SEASON, injuries=None,
            rosters={1: {"Week": 1, "Records": after_rows[1]}}, schedule={"Season": SEASON, "Games": games})
        self.assertEqual(expected, new_keys)
        self.assertEqual(materializer.serialize(after), materializer.serialize(build([], after_rows, games=games)))
        # A stale, internally complete snapshot is different from a corrupted one.
        damaged = copy.deepcopy(before)
        damaged["Records"].pop()
        damaged["Quality"]["RecordCount"] -= 1
        with self.assertRaises(AvailabilityError):
            verify_population_witness(damaged)

    def test_same_size_key_substitution_is_not_a_valid_snapshot(self):
        doc = build([], {1: [roster(player(1), "AAA", position="WR")]})
        doc["Records"][0]["CanonicalPlayerID"] = player(99)
        with self.assertRaises(AvailabilityError):
            verify_population_witness(doc)

    def test_full_source_sync_reuses_availability_writer_without_live_or_odds_trigger(self):
        import yaml
        repo = Path(__file__).resolve().parents[2]
        workflow = yaml.safe_load((repo / ".github/workflows/sync-nfl-source-data.yml").read_text(encoding="utf-8"))
        job = workflow["jobs"]["nfl_injuries_derived"]
        self.assertEqual(job["needs"], "sync")
        self.assertIn("needs.sync.result == 'success'", job["if"])
        self.assertIn("inputs.materialization_scope == 'full' || !inputs.materialization_scope", job["if"])
        self.assertIn("inputs.materialization_scope == 'injuries'", job["if"])
        self.assertIn("needs.sync.outputs.injury_history_due == 'true'", job["if"])
        self.assertNotIn("'game-finality'", job["if"])
        self.assertNotIn("'schedule-odds'", job["if"])
        step = next(s for s in job["steps"] if s["name"].startswith("Rebuild and publish NFL Player Availability"))
        self.assertIn("--scope nfl-availability-derived", step["run"])
        self.assertIn("--path data-derived/nfl-player-availability", step["run"])
        self.assertIn("--all-seasons --write", step["run"])
        self.assertIn("--all-seasons --check", step["run"])


class PersistedStateGuard(unittest.TestCase):
    """Persisted v2/v3 season files have a record with Available and Played for every roster week of the position cut (no gaps).

    Seasons still persisted as v1 are skipped until the existing writer regenerates them; nothing is wired to real players.
    """

    def test_every_roster_week_of_the_cut_is_recorded(self):
        from derived_data_lib.nfl_player_availability import FANTASY_POSITIONS, ROSTER_WEEK_STATUSES

        repo = Path(__file__).resolve().parents[2]
        checked = 0
        for path in sorted((repo / "data-derived" / "nfl-player-availability").glob("*.json")):
            document = json.loads(path.read_text(encoding="utf-8"))
            if document.get("ProductVersion") not in ("nfl-player-availability-v2", "nfl-player-availability-v3"):
                continue
            checked += 1
            season = document["Season"]
            population = document["Quality"]["Population"]
            positions = None if population["Positions"] is None else frozenset(population["Positions"])
            self.assertEqual(positions, FANTASY_POSITIONS, f"{season}: position cut changed without a decision")
            recorded = {(r["Week"], r["CanonicalPlayerID"]) for r in document["Records"]}
            self.assertEqual(len(recorded), len(document["Records"]), f"{season}: duplicate player-week")
            for record in document["Records"]:
                self.assertIn(record["Available"], ("yes", "no", "unknown", "bye"))
                self.assertIn(record["Played"], (True, False, None))
                if record["State"] == "bye":
                    self.assertEqual((record["Available"], record["Played"]), ("bye", None))
                    self.assertEqual(record["Participation"]["State"], "no-game")
                    self.assertIsNone(record["GameID"])
            nfl = repo / "data-source" / "nfl"
            injuries_path = repo / "data-derived" / "nfl-injuries" / f"{season}.json"
            injuries = json.loads(injuries_path.read_text(encoding="utf-8")) if injuries_path.is_file() else None
            schedule = json.loads((nfl / "schedules" / f"{season}.json").read_text(encoding="utf-8"))
            rosters = {int(p.stem): json.loads(p.read_text(encoding="utf-8"))
                       for p in sorted((nfl / "weekly-rosters" / str(season)).glob("*.json"))}
            expected = expected_population_keys(season, injuries=injuries, rosters=rosters, schedule=schedule,
                                                healthy_positions=positions)
            witness = population.get("RecordKeysSha256")
            # Validate a new snapshot against its own exact, independently
            # source-validated population. Compare current source expectation
            # separately: an already-covered partition can still be revised.
            if "RecordKeysSha256" in population:
                self.assertEqual(recorded, verify_population_witness(document))
                if witness == population_keys_sha256(expected):
                    self.assertEqual(recorded, expected)
            # A fresh population-only derivation covers every current source
            # partition, including legacy-file rollout and source revisions.
            # This checks the actual producer, not merely the stored checksum.
            if witness != population_keys_sha256(expected):
                current = derive_nfl_player_availability(
                    season, injuries=injuries, rosters=rosters, snap_counts={}, player_stats={},
                    schedule=schedule, finality={"Season": season, "Games": []}, healthy_positions=positions,
                )
                self.assertEqual(verify_population_witness(current), expected)
            if "RecordKeysSha256" in population:
                continue
            # Legacy v2/v3 snapshots retain the original persisted-state guard until
            # the existing writer first publishes the source-validated witness.
            if not population["RosterWeeksIncluded"]:
                continue
            if not population.get("ByeWeeksIncluded"):
                continue  # persisted before Issue #1616 (G1/G2)
            played = {(int(g["Week"]), t) for g in schedule["Games"] for t in (g["AwayTeam"], g["HomeTeam"])}
            last_regular = max(int(g["Week"]) for g in schedule["Games"] if g.get("GameType") == "REG")
            covered = {int(c["Week"]) for c in document["Quality"]["WeekCoverage"] if c["RosterPartition"]}
            rows_by_key = {}
            for week, partition in sorted(rosters.items()):
                if week not in covered:
                    continue
                for row in partition.get("Records", []):
                    if row.get("CanonicalPlayerID"):
                        rows_by_key[(week, row["CanonicalPlayerID"])] = row
            for (week, pid), row in rows_by_key.items():
                nxt = (week + 1, pid)
                if (row.get("Status") in BYE_CARRY_STATUSES and row.get("GameType") == "REG" and week + 1 <= last_regular and nxt not in rows_by_key
                        and (row.get("Status") in RESERVE_STATUSES or row.get("Position") in positions)
                        and (week + 1, row.get("Team")) not in played):
                    self.assertIn(nxt, recorded, f"{season} week {week + 1}: bye without a record")
            for week, partition in sorted(rosters.items()):
                if week not in covered:
                    continue
                for row in partition.get("Records", []):
                    pid = row.get("CanonicalPlayerID")
                    if pid and row.get("Status") is not None and row.get("Position") in positions:
                        if row.get("GameType") != "REG" and (week, pid) not in recorded:
                            continue  # postseason week without a game of the team is not a record
                        self.assertIn((week, pid), recorded, f"{season} week {week}: roster week without a record")
        self.assertGreaterEqual(checked, 0)
