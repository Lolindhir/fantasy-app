"""Tests for the league-standings product: sources, pure assembly and materializer (ADR-072, Issue #987 step 2).

The fixtures are constructed leagues written to temporary directories; the repository integration test asserts
invariants only and wires no team, owner or season result in.
"""
from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TOOLS = Path(__file__).resolve().parents[1]
REPO_ROOT = TOOLS.parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import derived_data  # noqa: E402
import league_standings_sources as sources  # noqa: E402
from derived_data_lib.league_standings import add_validated_weekly_streaks, build_season  # noqa: E402
from derived_data_lib.models import registry  # noqa: E402

LEAGUE = "test-league"
STANDINGS = registry.get_model("standings-v1", "standings")
AWARDS = registry.get_model("awards-v1", "awards")


def write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def member(index: int, **meta):
    return {
        "CanonicalLeagueMemberID": f"clm-{index}", "DisplayName": f"owner{index}", "Avatar": f"av{index} " if index % 2 else None,
        "Metadata": {"team_name": f" Team {index} " if index != 2 else "   ", **meta},
        "ProviderMappings": [{"Provider": "Sleeper", "ProviderUserID": f"u{index}"}],
    }


def roster(index: int, wins: int, losses: int, ties: int, points: float, against: float, record: str):
    return {
        "CanonicalLeagueRosterID": f"clr-{index}", "CanonicalLeagueMemberID": f"clm-{index}", "ProviderOwnerUserID": f"u{index}",
        "ProviderMappings": [{"Provider": "Sleeper", "ProviderRosterID": str(index)}],
        "Settings": {"wins": wins, "losses": losses, "ties": ties, "fpts": int(points), "fpts_decimal": round((points % 1) * 100),
                     "fpts_against": int(against), "fpts_against_decimal": round((against % 1) * 100)},
        "Metadata": {"record": record, "streak": "1W"},
    }


def matchup(roster_index: int, matchup_id: int, points: float, week: int):
    return {"Week": week, "Points": points, "ProviderMappings": [{"Provider": "Sleeper", "ProviderMatchupID": matchup_id, "ProviderRosterID": str(roster_index)}]}


def bracket_match(place, winner, loser):
    to_id = lambda i: f"clr-{i}" if i else None
    return {"Round": 2, "Match": 1, "Placement": place, "Team1CanonicalLeagueRosterID": to_id(winner), "Team2CanonicalLeagueRosterID": to_id(loser),
            "WinnerCanonicalLeagueRosterID": to_id(winner), "LoserCanonicalLeagueRosterID": to_id(loser), "Team1Source": None, "Team2Source": None}


# Three regular-season games, four teams. Results per week: (winner, winner points, loser, loser points) for two matchups.
WEEKS = [
    [(1, 120.0, 2, 100.0), (4, 110.0, 3, 90.0)],
    [(3, 95.0, 1, 80.0), (2, 130.0, 4, 60.0)],
    [(1, 101.0, 4, 100.5), (2, 70.0, 3, 69.5)],
]


def season_fixture(root: Path, season: int, status: str, weeks: int, results=WEEKS, playoffs=True) -> None:
    directory = root / "data-source" / "leagues" / LEAGUE / "seasons" / str(season)
    played = results[:weeks]
    record = {i: "" for i in range(1, 5)}
    stats = {i: [0, 0, 0, 0.0, 0.0] for i in range(1, 5)}
    for week_index, games in enumerate(played, start=1):
        for matchup_id, (winner, win_points, loser, lose_points) in enumerate(games, start=1):
            record[winner] += "W"
            record[loser] += "L"
            stats[winner][0] += 1
            stats[loser][1] += 1
            stats[winner][3] += win_points
            stats[winner][4] += lose_points
            stats[loser][3] += lose_points
            stats[loser][4] += win_points
        write(directory / "matchups" / f"week-{week_index}.json", [
            matchup(i, matchup_id, points, week_index)
            for matchup_id, (winner, win_points, loser, lose_points) in enumerate(games, start=1)
            for i, points in ((winner, win_points), (loser, lose_points))
        ])
    write(directory / "league.json", {"Season": season, "Status": status, "Settings": {"playoff_week_start": 4}})
    write(directory / "members.json", [member(i) for i in range(1, 5)])
    write(directory / "rosters.json", [roster(i, stats[i][0], stats[i][1], stats[i][2], round(stats[i][3], 2), round(stats[i][4], 2), record[i]) for i in range(1, 5)])
    write(directory / "winners-bracket.json", [bracket_match(1, 1, 2), bracket_match(3, 3, 4)] if playoffs else [bracket_match(1, None, None)])
    write(directory / "losers-bracket.json", [])


def finality(scored_week):
    """Patch the week basis: one value for every season or a ``{season: week}`` mapping."""
    def resolve(repo_root, league_id, season):
        return {"LeagueScoredWeek": scored_week[season] if isinstance(scored_week, dict) else scored_week}

    return mock.patch.object(sources, "resolve_week_finality", resolve)


class SourceTests(unittest.TestCase):
    def test_teams_are_ordered_by_roster_id_with_normalized_names_and_avatars(self):
        members = [member(i) for i in (3, 1, 2, 4)]
        rosters = [roster(i, 1, 0, 0, 10.25, 5.5, "W") for i in (4, 2, 1, 3)]
        teams = sources.build_teams(members, rosters)
        self.assertEqual([1, 2, 3, 4], [t["TeamID"] for t in teams])
        self.assertEqual("Team 1", teams[0]["Team"])  # trimmed
        self.assertEqual("Team owner2", teams[1]["Team"])  # blank team name falls back to the owner
        self.assertEqual("av1", teams[0]["OwnerAvatarID"])
        self.assertIsNone(teams[1]["OwnerAvatarID"])
        self.assertEqual(10.25, teams[0]["Points"])
        self.assertEqual("clr-1", teams[0]["CanonicalLeagueRosterID"])

    def test_inconsistent_members_and_rosters_fail_closed(self):
        members = [member(i) for i in (1, 2)]
        rosters = [roster(i, 0, 0, 0, 0.0, 0.0, "") for i in (1, 2)]
        broken = {
            "duplicate roster id": lambda m, r: r.append(copy.deepcopy(r[0])),
            "owner mismatch": lambda m, r: r[0].update(ProviderOwnerUserID="u99"),
            "unknown member": lambda m, r: r[0].update(CanonicalLeagueMemberID="clm-99"),
            "missing roster mapping": lambda m, r: r[0].update(ProviderMappings=[]),
            "missing member mapping": lambda m, r: m[0].update(ProviderMappings=[]),
            "missing display name": lambda m, r: m[0].update(DisplayName=" "),
            "missing owner user": lambda m, r: r[0].update(ProviderOwnerUserID=""),
        }
        for label, mutate in broken.items():
            with self.subTest(label):
                m, r = copy.deepcopy(members), copy.deepcopy(rosters)
                mutate(m, r)
                with self.assertRaises(sources.StandingsSourceError):
                    sources.build_teams(m, r)

    def test_bracket_conversion_uses_provider_roster_ids(self):
        ids = {"clr-1": 1, "clr-2": 2}
        converted = sources.convert_bracket([bracket_match(1, 1, 2)], ids)
        self.assertEqual([{"r": 2, "m": 1, "t1": 1, "t2": 2, "w": 1, "l": 2, "p": 1}], converted)
        self.assertEqual(None, sources.convert_bracket([bracket_match(1, None, None)], ids)[0]["w"])
        with self.assertRaises(sources.StandingsSourceError):
            sources.convert_bracket([bracket_match(1, 3, 2)], ids)

    def test_missing_weekly_files_are_omitted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            season_fixture(root, 2030, "in_season", weeks=2)
            directory = root / "data-source/leagues" / LEAGUE / "seasons/2030"
            weeks = sources.weekly_matchups(directory, 3)
            self.assertEqual([1, 2], [w["Week"] for w in weeks])
            self.assertEqual({"TeamID": 1, "MatchupID": 1, "Points": 120.0}, weeks[0]["Entries"][0])

    def test_load_season_inputs_applies_the_status_rules(self):
        with tempfile.TemporaryDirectory() as tmp, finality(3):
            root = Path(tmp)
            season_fixture(root, 2030, "in_season", weeks=3)
            season_fixture(root, 2031, "complete", weeks=3)
            inputs = sources.load_season_inputs(root, LEAGUE, 2030, current=2030)
            self.assertFalse(inputs.is_completed)
            self.assertEqual((3, 3), (inputs.regular_season_games, inputs.league_scored_week))
            self.assertTrue(sources.load_season_inputs(root, LEAGUE, 2031, current=2030).is_completed)
            with self.assertRaisesRegex(sources.StandingsSourceError, "current season"):
                sources.load_season_inputs(root, LEAGUE, 2030, current=2031)

    def test_missing_files_and_invalid_week_settings_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp, finality(3):
            root = Path(tmp)
            season_fixture(root, 2030, "complete", weeks=3)
            directory = root / "data-source/leagues" / LEAGUE / "seasons/2030"
            write(directory / "league.json", {"Season": 2030, "Status": "complete", "Settings": {"playoff_week_start": 1}})
            with self.assertRaisesRegex(sources.StandingsSourceError, "playoff_week_start"):
                sources.load_season_inputs(root, LEAGUE, 2030, current=2030)
            write(directory / "league.json", {"Season": 1999, "Status": "complete", "Settings": {"playoff_week_start": 4}})
            with self.assertRaisesRegex(sources.StandingsSourceError, "mismatch"):
                sources.load_season_inputs(root, LEAGUE, 2030, current=2030)
            (directory / "losers-bracket.json").unlink()
            with self.assertRaisesRegex(sources.StandingsSourceError, "missing"):
                sources.load_season_inputs(root, LEAGUE, 2030, current=2030)
            with self.assertRaisesRegex(sources.StandingsSourceError, "directory missing"):
                sources.load_season_inputs(root, LEAGUE, 1990, current=2030)


class AssemblyTests(unittest.TestCase):
    def inputs(self, root: Path, season: int, status: str, weeks: int, scored: int, **kwargs):
        season_fixture(root, season, status, weeks, **kwargs)
        with finality(scored):
            return sources.load_season_inputs(root, LEAGUE, season, current=2031)

    def test_season_document_for_a_completed_season(self):
        with tempfile.TemporaryDirectory() as tmp:
            document = build_season(self.inputs(Path(tmp), 2030, "complete", 3, 17), STANDINGS, AWARDS, None, [])
        self.assertEqual("league-standings", document["Product"])
        self.assertEqual({"Standings": "standings-v1", "Awards": "awards-v1"}, document["Models"])
        self.assertEqual({"LeagueScoredWeek": 17, "CompletedWeeks": 3}, document["AsOf"])  # capped at the regular season
        self.assertEqual([1, 2, 3], [w["Week"] for w in document["Weeks"]])
        self.assertEqual([1, 2, 3, 4], [t["TeamID"] for t in document["Teams"]])
        self.assertEqual(4, len(document["RegularSeason"]))
        self.assertEqual([1, 2, 3, 4], [p["TeamID"] for p in document["Playoffs"]])  # placement matches 1 and 3 decide all four places
        self.assertEqual(["Winner"] * 4, [p["PlaceType"] for p in document["Playoffs"]])
        self.assertEqual(2030, document["AllTime"]["ThroughSeason"])  # a completed season counts in its own all-time standing
        self.assertEqual(["Best Performer", "Streaker", "Overperformer", "Brick Wall", "Clutch Peaker"], [a["Name"] for a in document["Awards"]])
        json.dumps(document)

    def test_weekly_streak_is_derived_from_validated_record_prefix_not_current_provider_streak(self):
        with tempfile.TemporaryDirectory() as tmp:
            document = build_season(self.inputs(Path(tmp), 2030, "complete", 3, 3), STANDINGS, AWARDS, None, [])
        expected = {
            1: {1: "1W", 2: "1L", 3: "1L", 4: "1W"},
            2: {1: "1L", 2: "1W", 3: "1W", 4: "1L"},
            3: {1: "1W", 2: "2W", 3: "1L", 4: "2L"},
        }
        for week in document["Weeks"]:
            self.assertEqual(expected[week["Week"]], {
                row["TeamID"]: row["Streak"] for row in week["Teams"]
            })

    def test_weekly_streak_handles_ties_and_does_not_mutate_validated_tables(self):
        tables = [
            {"Week": 1, "Teams": [{"TeamID": 1}, {"TeamID": 2}]},
            {"Week": 2, "Teams": [{"TeamID": 1}, {"TeamID": 2}]},
            {"Week": 3, "Teams": [{"TeamID": 1}, {"TeamID": 2}]},
        ]
        original = copy.deepcopy(tables)
        enriched = add_validated_weekly_streaks(
            tables, [{"TeamID": 1, "Record": "TTW"}, {"TeamID": 2, "Record": "TTL"}]
        )
        self.assertEqual(original, tables)
        self.assertEqual([["1T", "1T"], ["2T", "2T"], ["1W", "1L"]],
                         [[row["Streak"] for row in t["Teams"]] for t in enriched])

    def test_weekly_streak_never_infers_an_unvalidated_or_missing_week(self):
        with tempfile.TemporaryDirectory() as tmp:
            inputs = self.inputs(Path(tmp), 2031, "in_season", 2, 3, playoffs=False)
        document = build_season(inputs, STANDINGS, AWARDS, None, [])
        self.assertEqual([1, 2], [t["Week"] for t in document["Weeks"]])
        self.assertTrue(all(row["Streak"] for table in document["Weeks"] for row in table["Teams"]))
        self.assertEqual([], add_validated_weekly_streaks([], inputs.teams))
        with self.assertRaisesRegex(ValueError, "canonical Record"):
            add_validated_weekly_streaks(
                [{"Week": 3, "Teams": [{"TeamID": 1}]}],
                [{"TeamID": 1, "Record": "WL"}]
            )

    def test_the_weekly_history_feeds_the_row_movement_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            document = build_season(self.inputs(Path(tmp), 2030, "complete", 3, 3), STANDINGS, AWARDS, None, [])
        rows = {r["TeamID"]: r for r in document["RegularSeason"]}
        tables = {t["Week"]: {e["TeamID"]: e["Place"] for e in t["Teams"]} for t in document["Weeks"]}
        for team_id, row in rows.items():
            self.assertEqual(tables[2][team_id], row["PreviousWeekPlace"])
            self.assertEqual(row["PreviousWeekPlace"] - row["Place"], row["PlaceDelta"])
            self.assertEqual([2, 3], [m["Week"] for m in row["WeeklyMovements"]])
            self.assertEqual(tables[3][team_id], row["WeeklyMovements"][-1]["Place"])
        # the final weekly table agrees with the provider-published table of the fixture
        self.assertEqual({tid: r["Place"] for tid, r in rows.items()}, tables[3])

    def test_a_season_in_progress_is_not_part_of_its_own_all_time_and_follows_the_scored_weeks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = build_season(self.inputs(root, 2030, "complete", 3, 3), STANDINGS, AWARDS, None, [])
            second = build_season(self.inputs(root, 2031, "in_season", 2, 2, playoffs=False), STANDINGS, AWARDS, first, [first])
        self.assertFalse(second["IsCompleted"])
        self.assertEqual(2030, second["AllTime"]["ThroughSeason"])
        self.assertEqual(first["AllTime"]["RegularSeason"], second["AllTime"]["RegularSeason"])
        self.assertEqual([], second["Playoffs"])
        self.assertEqual({"LeagueScoredWeek": 2, "CompletedWeeks": 2}, second["AsOf"])
        self.assertEqual([1, 2], [w["Week"] for w in second["Weeks"]])
        self.assertIn("Most Improved", [a["Name"] for a in second["Awards"]])
        self.assertNotIn("Clutch Peaker", [a["Name"] for a in second["Awards"]])
        self.assertTrue(all("ImprovementScore" in r and "ClutchPeakerScore" not in r for r in second["RegularSeason"]))

    def test_a_scored_week_the_record_does_not_confirm_ends_the_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            inputs = self.inputs(Path(tmp), 2031, "in_season", 2, 3, playoffs=False)  # provider scored week 3, rosters only know 2
        document = build_season(inputs, STANDINGS, AWARDS, None, [])
        self.assertEqual(3, document["AsOf"]["CompletedWeeks"])
        self.assertEqual([1, 2], [w["Week"] for w in document["Weeks"]])
        self.assertTrue(all([m["Week"] for m in r["WeeklyMovements"]] == [2] for r in document["RegularSeason"]))
        self.assertTrue(all(r["PreviousWeekPlace"] is not None for r in document["RegularSeason"]))  # week 2 is validated

    def test_before_the_first_scored_week_there_are_no_weeks_and_no_awards(self):
        with tempfile.TemporaryDirectory() as tmp:
            inputs = self.inputs(Path(tmp), 2031, "in_season", 0, 0, playoffs=False)
        document = build_season(inputs, STANDINGS, AWARDS, None, [])
        self.assertEqual([], document["Weeks"])
        self.assertEqual([], document["Awards"])
        self.assertEqual(None, document["AllTime"]["ThroughSeason"])
        self.assertTrue(all(r["PreviousWeekPlace"] is None and r["WeeklyMovements"] == [] for r in document["RegularSeason"]))

    def test_assembly_is_deterministic_and_does_not_mutate_its_previous_season(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = build_season(self.inputs(root, 2030, "complete", 3, 3), STANDINGS, AWARDS, None, [])
            snapshot = copy.deepcopy(first)
            inputs = self.inputs(root, 2031, "in_season", 2, 2, playoffs=False)
            a = build_season(inputs, STANDINGS, AWARDS, first, [first])
            b = build_season(inputs, STANDINGS, AWARDS, first, [first])
        self.assertEqual(a, b)
        self.assertEqual(snapshot, first)


class MaterializerTests(unittest.TestCase):
    def make_repo(self, root: Path) -> None:
        season_fixture(root, 2030, "complete", 3)
        season_fixture(root, 2031, "in_season", 2, playoffs=False)
        league_dir = root / "data-source/leagues" / LEAGUE
        write(league_dir / "manifest.json", {
            "CanonicalLeagueID": LEAGUE, "CurrentCanonicalLeagueSeasonID": f"{LEAGUE}-2031", "CurrentProviderLeagueID": "123", "Provider": "Sleeper",
            "Seasons": [{"Season": 2030}, {"Season": 2031}],
        })
        real = json.loads((REPO_ROOT / "data-meta/nfl-reise/metadata.json").read_text(encoding="utf-8"))
        real["CanonicalLeagueID"] = LEAGUE
        real["CurrentProviderLeagueID"] = "123"
        models = next(iter(real["Seasons"].values()))["Models"]
        real["Seasons"] = {"2030": {"Models": dict(models)}, "2031": {"CapDeadline": "2031-06-30T23:59:59Z", "CapDeadlineBufferDays": 2, "Models": dict(models)}}
        write(root / "data-meta" / LEAGUE / "metadata.json", real)

    def run_materializer(self, root: Path, out: Path, seasons=None, check=False):
        with finality({2030: 17, 2031: 2}):
            return derived_data.materialize_league_standings(root, out, LEAGUE, seasons, check)

    def test_writes_one_file_per_season_and_a_second_run_is_a_no_op(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as out_tmp:
            root, out = Path(tmp), Path(out_tmp)
            self.make_repo(root)
            first = self.run_materializer(root, out)
            self.assertEqual([2030, 2031], [s["Season"] for s in first["Seasons"]])
            self.assertEqual([1, 1], [s["Written"] for s in first["Seasons"]])
            paths = sorted((out / "league-standings" / LEAGUE).glob("*.json"))
            self.assertEqual(["2030.json", "2031.json"], [p.name for p in paths])
            second = self.run_materializer(root, out)
            self.assertEqual([0, 0], [s["Written"] for s in second["Seasons"]])
            self.assertEqual([1, 1], [s["Unchanged"] for s in second["Seasons"]])
            for path in paths:
                text = path.read_text(encoding="utf-8")
                self.assertTrue(text.startswith('{"SchemaVersion":1,"Product":"league-standings"'))  # compact, fixed key order
                self.assertTrue(text.endswith("\n"))

    def test_check_mode_writes_nothing_and_a_season_filter_still_chains_the_previous_season(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as out_tmp:
            root, out = Path(tmp), Path(out_tmp)
            self.make_repo(root)
            checked = self.run_materializer(root, out, check=True)
            self.assertEqual([1, 1], [s["WouldWrite"] for s in checked["Seasons"]])
            self.assertEqual([], list(out.rglob("*.json")))
            only_current = self.run_materializer(root, out, seasons=[2031])
            self.assertEqual([2031], [s["Season"] for s in only_current["Seasons"]])
            document = json.loads((out / "league-standings" / LEAGUE / "2031.json").read_text(encoding="utf-8"))
            self.assertEqual(2030, document["AllTime"]["ThroughSeason"])  # chained although 2030 was not written
            self.assertIn("Most Improved", [a["Name"] for a in document["Awards"]])
            self.assertFalse((out / "league-standings" / LEAGUE / "2030.json").exists())

    def test_unknown_seasons_and_models_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as out_tmp:
            root, out = Path(tmp), Path(out_tmp)
            self.make_repo(root)
            with self.assertRaises(sources.StandingsSourceError):
                self.run_materializer(root, out, seasons=[1999])
            metadata_path = root / "data-meta" / LEAGUE / "metadata.json"
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            metadata["Seasons"]["2030"]["Models"]["Standings"] = "standings-v99"
            write(metadata_path, metadata)
            with self.assertRaises(Exception):
                self.run_materializer(root, out)

    def test_a_league_can_choose_the_model_per_season(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as out_tmp:
            root, out = Path(tmp), Path(out_tmp)
            self.make_repo(root)
            chosen: list[str] = []
            real_get = derived_data.get_model

            def spy(model_id, kind=None):
                chosen.append(f"{kind}:{model_id}")
                return real_get(model_id, kind)

            with mock.patch.object(derived_data, "get_model", spy):
                self.run_materializer(root, out)
        self.assertEqual(["standings:standings-v1", "awards:awards-v1"] * 2, chosen)  # resolved per season from data-meta


class RepositoryIntegrationTests(unittest.TestCase):
    """Invariants over the repository's canonical facts; no result of a real team is asserted."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name)
        cls.league = "nfl-reise"
        cls.summary = derived_data.materialize_league_standings(REPO_ROOT, cls.out, cls.league, None, False)
        cls.documents = {
            s["Season"]: json.loads((cls.out / "league-standings" / cls.league / f"{s['Season']}.json").read_text(encoding="utf-8"))
            for s in cls.summary["Seasons"]
        }

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_every_manifest_season_has_a_file_with_the_chosen_models(self):
        manifest = sources.manifest(REPO_ROOT, self.league)
        self.assertEqual(sources.manifest_seasons(manifest), sorted(self.documents))
        metadata = json.loads((REPO_ROOT / "data-meta" / self.league / "metadata.json").read_text(encoding="utf-8"))
        for season, document in self.documents.items():
            models = metadata["Seasons"][str(season)]["Models"]
            self.assertEqual({"Standings": models["Standings"], "Awards": models["Awards"]}, document["Models"])

    def test_tables_are_consistent_within_each_season(self):
        for season, document in self.documents.items():
            with self.subTest(season=season):
                team_ids = [t["TeamID"] for t in document["Teams"]]
                self.assertEqual(sorted(team_ids), sorted(r["TeamID"] for r in document["RegularSeason"]))
                self.assertLessEqual(document["AsOf"]["CompletedWeeks"], document["RegularSeasonGames"])
                self.assertLessEqual(len(document["Weeks"]), document["AsOf"]["CompletedWeeks"])
                for table in document["Weeks"]:
                    self.assertEqual(sorted(team_ids), [e["TeamID"] for e in table["Teams"]])
                    self.assertTrue(all(1 <= e["Place"] <= len(team_ids) for e in table["Teams"]))
                for row in document["RegularSeason"]:
                    self.assertEqual(row["Wins"] + row["Losses"] + row["Ties"], len(row["Record"]))
                    if row["PlaceDelta"] is not None:
                        self.assertEqual(row["PreviousWeekPlace"] - row["Place"], row["PlaceDelta"])

    def test_the_all_time_chain_follows_the_completed_seasons(self):
        completed = sorted(s for s, d in self.documents.items() if d["IsCompleted"])
        for season, document in self.documents.items():
            with self.subTest(season=season):
                through = [s for s in completed if s <= season]
                self.assertEqual(through[-1] if through else None, document["AllTime"]["ThroughSeason"])
                self.assertEqual(bool(through), bool(document["AllTime"]["RegularSeason"]))

    def test_a_second_run_changes_nothing(self):
        again = derived_data.materialize_league_standings(REPO_ROOT, self.out, self.league, None, True)
        self.assertEqual(0, sum(s["WouldWrite"] for s in again["Seasons"]))


if __name__ == "__main__":
    unittest.main()
