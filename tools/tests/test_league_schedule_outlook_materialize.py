"""Incremental Schedule Outlook materializer: fingerprints, no-op, recovery, consistency, guards (#1519 I6).

Synthetic season facts only (no hard-wired league data); one repository smoke test proves the
materialized product equals the restore candidate's assembled documents.
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
import league_schedule_outlook_materialize as mat  # noqa: E402
import league_schedule_outlook_preview as source  # noqa: E402
from derived_data_lib.league_schedule_outlook import assemble  # noqa: E402

MODEL = "schedule-outlook-v1"
ODDS = "playoff-odds-v1"
LEAGUE, SEASON = "test-league", 2030
ROSTERS = ["r1", "r2", "r3", "r4"]


def facts() -> dict:
    data = _facts()
    data["results"] = played(data["pairings"])
    return data


def _facts() -> dict:
    def game(i, a, b):
        return {"CanonicalLeagueMatchupID": f"m{i}", "Team1CanonicalLeagueRosterID": a, "Team2CanonicalLeagueRosterID": b}
    rating = lambda i: {"RelativeScoringStrength": 0.8 + i / 10, "ProjectedBestBallStrength": 100.0 + i}
    return {
        "scored": 5,
        "structure": {"PlayoffStartWeek": 4, "PlayoffRoundCount": 2, "PlayoffRoundType": 0, "PlayoffTeams": 4},
        "pairings": {
            1: [game("a", "r1", "r2"), game("b", "r3", "r4")],
            2: [game("c", "r1", "r3"), game("d", "r2", "r4")],
            3: [game("e", "r1", "r4"), game("f", "r2", "r3")],
        },
        "stats": {"Product": "season-statistics", "CanonicalLeagueID": LEAGUE, "Season": SEASON,
                  "Models": {"SeasonStats": "season-stats-v1"}, "AsOf": {"CompletedWeeks": 3},
                  "Weeks": [{"Week": w, "Teams": [{"TeamID": i + 1, **rating(i + w)} for i in range(4)]} for w in (1, 2, 3)]},
        "winners": [
            {"Match": 1, "Round": 1, "Placement": None, "Team1Source": None, "Team2Source": None,
             "Team1CanonicalLeagueRosterID": "r1", "Team2CanonicalLeagueRosterID": "r4",
             "WinnerCanonicalLeagueRosterID": "r1", "LoserCanonicalLeagueRosterID": "r4"},
            {"Match": 2, "Round": 1, "Placement": None, "Team1Source": None, "Team2Source": None,
             "Team1CanonicalLeagueRosterID": "r2", "Team2CanonicalLeagueRosterID": "r3",
             "WinnerCanonicalLeagueRosterID": "r2", "LoserCanonicalLeagueRosterID": "r3"},
            {"Match": 3, "Round": 2, "Placement": 1,
             "Team1Source": {"Match": 1, "Outcome": "Winner"}, "Team2Source": {"Match": 2, "Outcome": "Winner"},
             "Team1CanonicalLeagueRosterID": "r1", "Team2CanonicalLeagueRosterID": "r2",
             "WinnerCanonicalLeagueRosterID": "r1", "LoserCanonicalLeagueRosterID": "r2"},
        ],
        "losers": [],
    }


def played(pairings: dict) -> dict:
    out = {}
    for week, rows in pairings.items():
        out[week] = {}
        for g in rows:
            for n, key in enumerate(("Team1CanonicalLeagueRosterID", "Team2CanonicalLeagueRosterID")):
                out[week][g[key]] = (g["CanonicalLeagueMatchupID"], 100.0 + 10 * ROSTERS.index(g[key]) + week + n)
    return out


def inputs_from(data: dict) -> source.SeasonInputs:
    teams = [{"TeamID": i + 1, "CanonicalLeagueRosterID": rid} for i, rid in enumerate(ROSTERS)]
    result = source.SeasonInputs(Path("."), LEAGUE, SEASON, Path("."), f"{LEAGUE}-{SEASON}",
                                 copy.deepcopy(data["structure"]), 3, teams, data["scored"])
    result._pairings = {w: copy.deepcopy(rows) for w, rows in data["pairings"].items()}
    result._results = copy.deepcopy(data["results"])
    result._stats = copy.deepcopy(data["stats"])
    result._brackets = (copy.deepcopy(data["winners"]), copy.deepcopy(data["losers"]))
    result._previous = copy.deepcopy(data.get("previous", {}))
    return result


def stripped(doc: dict) -> str:
    doc = copy.deepcopy(doc)
    doc["Provenance"].pop("InputFingerprint", None)
    return json.dumps(doc, sort_keys=True)


class Harness(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "repo"
        self.out = Path(self.tmp.name) / "out"
        self.data = facts()
        patcher = mock.patch.object(source, "load_season_inputs", side_effect=lambda *a: inputs_from(self.data))
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_season(self, **kwargs):
        return mat.materialize_season(self.root, self.out, LEAGUE, SEASON, MODEL, odds_model_id=ODDS, **kwargs)

    def folder(self) -> Path:
        return mat.product_dir(self.out, LEAGUE, SEASON)

    def read(self, week: int) -> str:
        return (self.folder() / mat.snapshot_name(week)).read_text(encoding="utf-8")


class FactStrengthModelTests(Harness):
    """schedule-outlook-v2 (#1589): previous-season strength is an input; projection strengths are not."""

    def setUp(self):
        super().setUp()
        self.data["previous"] = {1: 1.2, 2: 1.0, 3: 0.9, 4: 0.9}

    def run_season(self, **kwargs):
        return mat.materialize_season(self.root, self.out, LEAGUE, SEASON, "schedule-outlook-v2", odds_model_id=ODDS, **kwargs)

    def test_documents_carry_the_v2_shape_and_noop_on_rerun(self):
        self.run_season()
        doc = json.loads(self.read(0))
        self.assertEqual("schedule-outlook-v2", doc["Models"]["ScheduleOutlook"])
        self.assertEqual(1.2, doc["RegularSeason"]["Teams"][0]["Strength"]["Value"])
        self.assertEqual(3, doc["RegularSeason"]["StrengthParams"]["CurrentSeasonWeightK"])
        again = self.run_season()
        self.assertEqual((6, 0, 0), (again["Unchanged"], again["Recomputed"], again["Written"]))

    def test_previous_season_change_dirties_every_cutoff(self):
        self.run_season()
        before = [self.read(w) for w in range(6)]
        self.data["previous"][1] = 1.5
        summary = self.run_season()
        self.assertEqual(6, summary["Recomputed"])
        self.assertTrue(all(self.read(w) != before[w] for w in range(3)))  # strength blends the previous season
        self.assertNotEqual(before[0], self.read(0))

    def test_projection_strength_change_does_not_invalidate_v2(self):
        self.run_season()
        self.data["stats"]["Weeks"][0]["Teams"][1]["ProjectedBestBallStrength"] = 55.5
        self.assertEqual(0, self.run_season()["Recomputed"])

    def test_no_previous_season_gives_unknown_strength_at_week_zero(self):
        self.data["previous"] = {}
        self.run_season()
        doc = json.loads(self.read(0))
        self.assertTrue(all(t["Strength"]["Value"] is None and t["RemainingSoS"] is None
                            for t in doc["RegularSeason"]["Teams"]))
        self.assertIsNotNone(json.loads(self.read(1))["RegularSeason"]["Teams"][0]["Strength"]["Value"])


class StrengthOddsTests(Harness):
    """playoff-odds-v2 (#1607) inside the materializer: strength comes from the outlook, points and spread are inputs."""

    def setUp(self):
        super().setUp()
        self.data["previous"] = {1: 1.2, 2: 1.0, 3: 0.9, 4: 0.9}
        self.previous_points = [90.0 + (i * 7) % 30 for i in range(24)]
        patcher = mock.patch.object(source.SeasonInputs, "previous_points", side_effect=lambda *_: list(self.previous_points))
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_season(self, **kwargs):
        return mat.materialize_season(self.root, self.out, LEAGUE, SEASON, "schedule-outlook-v2",
                                      odds_model_id="playoff-odds-v2", **kwargs)

    def test_document_carries_strength_basis_and_per_game_probabilities(self):
        self.run_season()
        doc = json.loads(self.read(1))
        odds = doc["PlayoffOdds"]
        self.assertEqual("playoff-odds-v2", doc["Models"]["PlayoffOdds"])
        self.assertEqual("outlook-strength", odds["Provenance"]["StrengthBasis"])
        outlook = {t["CanonicalLeagueRosterID"]: t["Strength"]["Value"] for t in doc["RegularSeason"]["Teams"]}
        mean = odds["Scoring"]["LeagueMeanPoints"]
        for team in odds["Teams"]:  # expected points are exactly league mean times the outlook strength
            self.assertAlmostEqual(mean * outlook[team["CanonicalLeagueRosterID"]], team["ExpectedPoints"], places=2)
        self.assertTrue(all(0 < g["WinProbability"] < 1 for t in odds["Teams"] for g in t["Upcoming"]))
        again = self.run_season()
        self.assertEqual((6, 0, 0), (again["Unchanged"], again["Recomputed"], again["Written"]))

    def test_changed_strength_changes_the_odds_without_touching_the_odds_model(self):
        self.run_season()
        before = json.loads(self.read(1))["PlayoffOdds"]
        self.data["previous"][1] = 0.5
        self.run_season()
        after = json.loads(self.read(1))["PlayoffOdds"]
        self.assertNotEqual(before["Teams"][0]["PlaceProbabilities"], after["Teams"][0]["PlaceProbabilities"])

    def test_points_and_previous_season_scores_dirty_the_cutoffs_that_use_them(self):
        self.run_season()
        before = [self.read(w) for w in range(6)]
        self.previous_points[0] += 5.0
        summary = self.run_season()
        self.assertEqual(6, summary["Recomputed"])  # spread estimate of every cutoff reads the previous season
        self.assertNotEqual(before[1], self.read(1))

    def test_fingerprint_is_sound_for_points_perturbations(self):
        changed = facts()
        changed["previous"] = dict(self.data["previous"])
        changed["results"][2]["r1"] = (changed["results"][2]["r1"][0], changed["results"][2]["r1"][1] + 3.0)
        left, right = inputs_from(self.data), inputs_from(changed)
        for week in range(6):
            a = mat.build_document(left, week, "schedule-outlook-v2", "0" * 64, "playoff-odds-v2")
            b = mat.build_document(right, week, "schedule-outlook-v2", "0" * 64, "playoff-odds-v2")
            if stripped(a) != stripped(b):
                self.assertNotEqual(mat.input_fingerprint(left, week, "schedule-outlook-v2", "playoff-odds-v2"),
                                    mat.input_fingerprint(right, week, "schedule-outlook-v2", "playoff-odds-v2"), f"week {week}")
        self.assertNotEqual(stripped(mat.build_document(left, 3, "schedule-outlook-v2", "0" * 64, "playoff-odds-v2")),
                            stripped(mat.build_document(right, 3, "schedule-outlook-v2", "0" * 64, "playoff-odds-v2")))


class IncrementalTests(Harness):
    def test_cold_then_incremental_is_a_true_noop(self):
        first = self.run_season()
        self.assertEqual((6, 6, 7), (first["Snapshots"], first["Recomputed"], first["Written"]))
        before = {p.name: p.read_bytes() for p in self.folder().iterdir()}
        second = self.run_season()
        self.assertEqual((6, 0, 0), (second["Unchanged"], second["Recomputed"], second["Written"]))
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.folder().iterdir()})
        full = self.run_season(mode="full")
        self.assertEqual((6, 0), (full["Recomputed"], full["Written"]))

    def changed_weeks(self, mutate) -> list[int]:
        self.run_season()
        before = {w: self.read(w) for w in range(6)}
        mutate(self.data)
        summary = self.run_season()
        self.assertEqual(6 - summary["Recomputed"], summary["Unchanged"])
        return [w for w in range(6) if self.read(w) != before[w]]

    def test_played_result_only_dirties_cutoffs_that_count_it(self):
        def mutate(d):
            # flip who won week 3 (r1/r2 swap points); earlier cutoffs must not notice it
            week = d["results"][3]
            for a, b in (("r1", "r2"), ("r3", "r4")):
                week[a], week[b] = (week[a][0], week[b][1]), (week[b][0], week[a][1])
        self.assertEqual([3, 4, 5], self.changed_weeks(mutate))

    def test_documents_carry_the_playoff_odds_block_and_model(self):
        self.run_season()
        doc = json.loads(self.read(2))
        self.assertEqual(ODDS, doc["Models"]["PlayoffOdds"])
        self.assertEqual(ODDS, doc["PlayoffOdds"]["Model"])
        self.assertTrue(doc["PlayoffOdds"]["Available"])
        self.assertEqual(4, len(doc["PlayoffOdds"]["Teams"][0]["PlaceProbabilities"]))
        self.assertAlmostEqual(4.0, sum(t["PlayoffProbability"] for t in doc["PlayoffOdds"]["Teams"]), places=8)
        self.assertTrue(json.loads(self.read(5))["PlayoffOdds"]["Provenance"]["RegularSeasonComplete"])

    def test_future_pairing_change_only_dirties_earlier_cutoffs(self):
        def mutate(d):
            d["pairings"][3] = [{"CanonicalLeagueMatchupID": "e", "Team1CanonicalLeagueRosterID": "r1", "Team2CanonicalLeagueRosterID": "r2"},
                                {"CanonicalLeagueMatchupID": "f", "Team1CanonicalLeagueRosterID": "r3", "Team2CanonicalLeagueRosterID": "r4"}]
        self.assertEqual([0, 1, 2], self.changed_weeks(mutate))

    def test_newer_rating_week_only_dirties_cutoffs_that_use_it(self):
        def mutate(d):
            d["stats"]["Weeks"][2]["Teams"][0]["RelativeScoringStrength"] = 9.0
        # Week-3 ratings are the rating week for after-weeks 3, 4 and 5; their regular-season
        # remainders are empty, so only the unchanged rating evidence differs in the fingerprint.
        self.run_season()
        before = [self.read(w) for w in range(6)]
        mutate(self.data)
        summary = self.run_season()
        self.assertEqual(3, summary["Recomputed"])
        self.assertEqual(before[:3], [self.read(w) for w in range(3)])

    def test_playoff_result_visibility_follows_round_completion(self):
        def round_two_result(d):
            d["winners"][2]["WinnerCanonicalLeagueRosterID"], d["winners"][2]["LoserCanonicalLeagueRosterID"] = "r2", "r1"
        self.assertEqual([5], self.changed_weeks(round_two_result))

        def round_one_result(d):
            d["winners"][0]["WinnerCanonicalLeagueRosterID"], d["winners"][0]["LoserCanonicalLeagueRosterID"] = "r4", "r1"
            d["winners"][2]["WinnerCanonicalLeagueRosterID"], d["winners"][2]["LoserCanonicalLeagueRosterID"] = "r4", "r2"
        self.assertEqual([4, 5], self.changed_weeks(round_one_result))

    def test_seed_changes_are_masked_before_the_regular_season_ends(self):
        def mutate(d):
            d["winners"][1]["Team1CanonicalLeagueRosterID"] = "r3"
            d["winners"][1]["Team2CanonicalLeagueRosterID"] = "r2"
            d["winners"][1]["WinnerCanonicalLeagueRosterID"] = "r3"
            d["winners"][1]["LoserCanonicalLeagueRosterID"] = "r2"
            d["winners"][2]["WinnerCanonicalLeagueRosterID"], d["winners"][2]["LoserCanonicalLeagueRosterID"] = "r1", "r3"
        changed = self.changed_weeks(mutate)
        self.assertEqual([3, 4, 5], [w for w in changed if w >= 3])
        self.assertTrue(all(w >= 3 for w in changed))

    def test_fingerprint_is_sound_for_every_perturbation(self):
        # Whenever a cutoff's document content differs, its fingerprint must differ too.
        perturbations = []
        perturbations.append(lambda d: d["pairings"].__setitem__(2, d["pairings"][2][::-1] and [
            {"CanonicalLeagueMatchupID": "c", "Team1CanonicalLeagueRosterID": "r1", "Team2CanonicalLeagueRosterID": "r4"},
            {"CanonicalLeagueMatchupID": "d", "Team1CanonicalLeagueRosterID": "r2", "Team2CanonicalLeagueRosterID": "r3"}]))
        perturbations.append(lambda d: d["stats"]["Weeks"][0]["Teams"][1].__setitem__("ProjectedBestBallStrength", 55.5))
        perturbations.append(lambda d: d["winners"][2].__setitem__("Placement", 3))
        perturbations.append(lambda d: d["winners"][0].__setitem__("WinnerCanonicalLeagueRosterID", "r4"))
        perturbations.append(lambda d: d["structure"].__setitem__("ProjectedPlayoffFormat", "x"))
        perturbations.append(lambda d: d["winners"][1].__setitem__("Team1CanonicalLeagueRosterID", "r4"))
        for index, perturb in enumerate(perturbations):
            changed = facts()
            perturb(changed)
            left, right = inputs_from(self.data), inputs_from(changed)
            for week in range(6):
                try:
                    a = mat.build_document(left, week, MODEL, "0" * 64)
                    b = mat.build_document(right, week, MODEL, "0" * 64)
                except Exception:  # fail-closed inputs are not a content comparison
                    continue
                if stripped(a) != stripped(b):
                    self.assertNotEqual(mat.input_fingerprint(left, week, MODEL),
                                        mat.input_fingerprint(right, week, MODEL),
                                        f"perturbation {index} week {week} changed content but not the fingerprint")


class ConsistencyTests(Harness):
    def test_source_change_during_run_writes_nothing(self):
        calls = []

        def drifting(*_):
            calls.append(1)
            data = facts()
            if len(calls) > 1:
                data["pairings"][3][0]["CanonicalLeagueMatchupID"] = "changed"
            return inputs_from(data)
        with mock.patch.object(source, "load_season_inputs", side_effect=drifting):
            with self.assertRaisesRegex(mat.ScheduleOutlookMaterializeError, "changed during the run"):
                self.run_season()
        self.assertFalse(self.folder().exists())

    def test_interrupted_run_is_healed_without_trusting_partial_state(self):
        self.run_season()
        (self.folder() / mat.INDEX_NAME).unlink()
        (self.folder() / mat.snapshot_name(2)).unlink()
        (self.folder() / mat.snapshot_name(4)).write_text('{"truncated":', encoding="utf-8")
        summary = self.run_season()
        self.assertEqual(2, summary["Recomputed"])
        self.assertEqual(3, summary["Written"])  # two snapshots + the index
        index = json.loads((self.folder() / mat.INDEX_NAME).read_text(encoding="utf-8"))
        self.assertEqual(list(range(6)), [s["AfterWeek"] for s in index["Snapshots"]])
        for entry in index["Snapshots"]:
            body = (self.folder() / entry["File"]).read_bytes()
            self.assertEqual(entry["Sha256"], hashlib.sha256(body).hexdigest())
            self.assertEqual(entry["InputFingerprint"], json.loads(body)["Provenance"]["InputFingerprint"])

    def test_full_mode_rederives_a_tampered_snapshot_with_a_valid_fingerprint(self):
        self.run_season()
        path = self.folder() / mat.snapshot_name(1)
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc["RegularSeason"]["Teams"][0]["RemainingGames"] = 99
        path.write_text(mat.serialize(doc), encoding="utf-8")
        self.assertEqual(0, self.run_season()["Recomputed"])  # incremental trusts the fingerprint by design
        repaired = self.run_season(mode="full")
        self.assertEqual(2, repaired["Written"])  # the snapshot and its index digest
        self.assertNotIn(99, [t["RemainingGames"] for t in json.loads(self.read(1))["RegularSeason"]["Teams"]])

    def test_orphans_are_reported_and_never_deleted(self):
        self.run_season()
        orphan = self.folder() / "after-week-09.json"
        orphan.write_text("{}\n", encoding="utf-8")
        summary = self.run_season()
        self.assertEqual(["after-week-09.json"], summary["Orphans"])
        self.assertTrue(orphan.is_file())

    def test_check_mode_never_writes(self):
        summary = self.run_season(check_only=True)
        self.assertEqual(7, summary["WouldWrite"])
        self.assertFalse(self.out.exists())

    def test_unfinished_statistics_fail_the_whole_season_untouched(self):
        self.data["stats"]["AsOf"]["CompletedWeeks"] = 2
        with self.assertRaisesRegex(source.ScheduleOutlookSourceError, "not final"):
            self.run_season()
        self.assertFalse(self.out.exists())

    def test_unknown_or_unselected_model_fails_closed(self):
        with self.assertRaises(Exception):
            mat.materialize_season(self.root, self.out, LEAGUE, SEASON, "schedule-outlook-v0")
        with self.assertRaises(mat.ScheduleOutlookMaterializeError):
            self.run_season(mode="bogus")

    def test_model_comes_from_data_meta_and_fails_closed(self):
        repo = TOOLS.parent
        league = "nfl-reise"
        selected = "schedule-outlook-v3"
        self.assertEqual(selected, mat.selected_model_id(repo, league, 2025))
        self.assertEqual(selected, mat.selected_model_id(repo, league, 2025, asserted=selected))
        with self.assertRaisesRegex(mat.ScheduleOutlookMaterializeError, "not the asserted"):
            mat.selected_model_id(repo, league, 2025, asserted="schedule-outlook-v0")
        with self.assertRaisesRegex(mat.ScheduleOutlookMaterializeError, "No usable"):
            mat.selected_model_id(repo, league, 1999)


class RepositorySmokeTests(unittest.TestCase):
    def test_materialized_product_equals_the_restore_candidate_documents(self):
        repo = TOOLS.parent
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            year = max(source.preview_all.__globals__["data_source_dir"](repo).joinpath("leagues", "nfl-reise", "seasons").iterdir(),
                       key=lambda p: p.name).name
            season = int(year) - 1  # a completed season with a full history
            first = mat.materialize_season(repo, out, "nfl-reise", season, MODEL, odds_model_id=ODDS, mode="full")
            second = mat.materialize_season(repo, out, "nfl-reise", season, MODEL, odds_model_id=ODDS, mode="full")
            self.assertEqual(0, second["Written"])
            replay = source.preview_all(repo, "nfl-reise", season)
            for week, snapshot in enumerate(replay["Snapshots"]):
                persisted = json.loads((mat.product_dir(out, "nfl-reise", season) / mat.snapshot_name(week)).read_text(encoding="utf-8"))
                fingerprint = persisted["Provenance"].pop("InputFingerprint")
                self.assertEqual(64, len(fingerprint))
                self.assertEqual(assemble(source.snapshot(source.load_season_inputs(repo, 'nfl-reise', season), week, ODDS), selected_model_id=MODEL), persisted)
            self.assertEqual(len(replay["Snapshots"]), first["Snapshots"])


if __name__ == "__main__":
    unittest.main()
