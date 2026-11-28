"""AC6A read-trace foundation: actual Python boundary calls on scratch fixtures."""
from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

from ci_tier import deep_only  # noqa: E402
from data_roots import DATA_DERIVED_ROOT, DATA_SOURCE_ROOT  # noqa: E402
from forecast_dependency_trace import (  # noqa: E402
    ROOTS, TraceError, classify_reads, load_rules, trace_python,
)

MANIFEST = Path(__file__).with_name("fixtures") / "forecast_dependency_manifest.json"


class ForecastTraceTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.rules = load_rules(MANIFEST)

    def put(self, path, value):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(value), encoding="utf-8")
        return target

    def run_code(self, code, *, rc=0):
        result = trace_python(self.root, ["-c", code])
        self.assertEqual(rc, result.process.returncode, result.process.stderr)
        return result

    def test_actual_historical_inputs_and_inherited_subprocess(self):
        for league, season in (("league-a", 2024), ("league-b", 2025)):
            self.put(Path(DATA_DERIVED_ROOT, "player-week-fantasy", league, str(season), "01.json"),
                     {"Records": [{"CanonicalPlayerID": "c", "Projection": {"Points": 17}}]})
            self.put(Path(DATA_DERIVED_ROOT, "team-week-performance", league, str(season), "01.json"),
                     {"Teams": [{"CanonicalLeagueRosterID": "r", "EfficiencyPercent": 75}]})
            self.put(Path(DATA_SOURCE_ROOT, "leagues", league, "seasons", str(season), "matchups", "week-1.json"),
                     [{"RosterID": 1}])
            self.put(Path(DATA_SOURCE_ROOT, "nfl", "weekly-rosters", str(season), "01.json"),
                     {"Records": [{"CanonicalPlayerID": "c"}]})
        child = (
            "from pathlib import Path; from derived_data_lib import season_statistics as s; "
            "assert s._efficiency_actual(Path.cwd(), 'league-b', 2025, 1) == {'r': 75.0}"
        )
        code = f"""
from pathlib import Path
from data_roots import DATA_SOURCE_ROOT
from derived_data_lib import weekly_recaps as w
import subprocess, sys
for league, year in (('league-a', 2024), ('league-b', 2025)):
    assert w._pwf_projections(Path.cwd(), league, year, 1) == {{'c': {{'Points': 17}}}}
    assert len(w._weekly_roster_rows(Path.cwd(), year, 1)) == 1
    season_dir = Path.cwd() / DATA_SOURCE_ROOT / 'leagues' / league / 'seasons' / str(year)
    assert w._load_matchup_rows(season_dir, 1) == [{{'RosterID': 1}}]
    assert w._pwf_projections(Path.cwd(), league, year, 2) == {{}}
subprocess.run([sys.executable, '-c', {child!r}], check=True)
"""
        result = self.run_code(code)
        rows = classify_reads(result.events, self.rules, own_product="weekly-recaps")
        self.assertEqual(2, result.processes)
        self.assertEqual(7, len(rows))
        self.assertEqual({"recaps-pwf", "recaps-roster", "recaps-matchups", "stats-twp"},
                         {row["rule"] for row in rows})
        self.assertTrue(all(row["role"] == "input" for row in rows))
        self.assertEqual(2, len({row["pid"] for row in rows}))
        self.assertFalse(any(event.get("write") for event in result.events))

    def test_noop_comparison_and_actual_write_are_separate(self):
        # The real resolver is replaced by a deterministic fixture here. This
        # validates the actual persistence/compare branch, not full replay.
        code = """
from pathlib import Path
from unittest.mock import patch
from data_roots import data_derived_dir
import weekly_recaps_materialize as m
root = Path.cwd()
with patch.object(m, 'resolve_weekly_recaps', return_value={'Season': '2025', 'Weeks': []}):
    assert m.materialize_season(root, data_derived_dir(root), 'league-a', 2025)['Written'] == 1
    assert m.materialize_season(root, data_derived_dir(root), 'league-a', 2025)['Written'] == 0
"""
        first = self.run_code(code)
        rows = classify_reads(first.events, self.rules, own_product="weekly-recaps")
        self.assertEqual(["recaps-noop"], [row["rule"] for row in rows])
        self.assertTrue(any(event.get("write") for event in first.events))
        path = self.root / DATA_DERIVED_ROOT / "weekly-recaps" / "league-a" / "2025.json"
        expected = path.read_bytes()
        path.write_text('{"wrong": true}', encoding="utf-8")
        seeded = self.run_code(code)
        self.assertEqual(expected, path.read_bytes())
        self.assertEqual(["comparison", "comparison"],
                         [row["role"] for row in classify_reads(seeded.events, self.rules,
                                                               own_product="weekly-recaps")])
        # Read via the actual App adaptation boundary in its separate stage.
        delivered = self.run_code("""
from pathlib import Path
from weekly_recaps_app_publish import _model
assert _model(Path.cwd(), 'league-a', 2025) == {'Season': '2025', 'Weeks': []}
""")
        self.assertEqual(["delivery"], [row["role"] for row in classify_reads(delivered.events, self.rules)])
        with self.assertRaises(TraceError):
            classify_reads(delivered.events, self.rules, own_product="weekly-recaps")
        wrong = tuple(replace(rule, role="input") if rule.id == "recaps-noop" else rule for rule in self.rules)
        with self.assertRaisesRegex(TraceError, "Forbidden producer feedback"):
            classify_reads(first.events, wrong, own_product="weekly-recaps")

    def test_app_output_comparison_is_not_a_computation_input(self):
        path = self.put(ROOTS["app"] / "PlayerWeekFantasy.json", {"stale": True})
        result = self.run_code("""
from pathlib import Path
from forecast_dependency_trace import ROOTS
from player_week_fantasy_app_publish import write_json_if_changed
path = Path.cwd() / ROOTS['app'] / 'PlayerWeekFantasy.json'
assert write_json_if_changed(path, {'new': True})
assert not write_json_if_changed(path, {'new': True})
""")
        rows = classify_reads(result.events, self.rules, own_product="player-week-fantasy")
        self.assertEqual(["comparison", "comparison"], [row["role"] for row in rows])
        self.assertEqual({"new": True}, json.loads(path.read_text(encoding="utf-8")))
        wrong = tuple(replace(rule, role="input") if rule.id == "pwf-app-noop" else rule for rule in self.rules)
        with self.assertRaisesRegex(TraceError, "Forbidden producer feedback"):
            classify_reads(result.events, wrong, own_product="league-forecast")
        unknown = self.run_code("""
from pathlib import Path
from forecast_dependency_trace import ROOTS
(Path.cwd() / ROOTS['app'] / 'PlayerWeekFantasy.json').read_text()
""")
        with self.assertRaisesRegex(TraceError, "Expected one read rule"):
            classify_reads(unknown.events, self.rules)

    def test_missing_roster_is_an_attempt_not_a_success(self):
        result = self.run_code("""
from pathlib import Path
from derived_data_lib.weekly_recaps import _weekly_roster_rows
_weekly_roster_rows(Path.cwd(), 2025, 1)
""", rc=1)
        self.assertIn("EvidenceGap", result.process.stderr)
        self.assertEqual(["recaps-roster"], [row["rule"] for row in classify_reads(result.events, self.rules)])
        self.assertFalse(any(event.get("write") for event in result.events))

    def metadata_fixture(self, league):
        source = sorted((TOOLS.parent / ROOTS["meta"]).glob("*/metadata.json"))
        self.assertTrue(source, "Need one configured metadata schema fixture")
        base = json.loads(source[0].read_text(encoding="utf-8-sig"))
        base["CanonicalLeagueID"] = league
        return base

    def test_players_game_history_projection_is_delivery_not_forecast_input(self):
        self.put(Path(DATA_DERIVED_ROOT, "player-week-fantasy", "league-a", "2025", "01.json"),
                 {"CanonicalLeagueID": "league-a", "Season": 2025, "Week": 1,
                  "Records": [{"CanonicalPlayerID": "c1", "Projection": {"Points": 17},
                               "Actual": {"State": "final"}},
                              {"CanonicalPlayerID": "c2", "Projection": {"Points": None}}]})
        result = self.run_code("""
from pathlib import Path
from derived_data_lib.players_read_model import load_projections, attach_projections
projections = load_projections(Path.cwd(), 'league-a', 2025)
assert projections == {('c1', 1): {'Points': 17.0, 'ActualFinal': True}}
games = [{'GameDetails': {'Week': 1, 'WeekFinal': True}, 'FantasyPoints': 18},
         {'GameDetails': {'Week': 2, 'WeekFinal': True}, 'FantasyPoints': 20}]
attach_projections(games, 'c1', projections)
assert games[0]['Projection']['Points'] == 17.0
assert games[1]['Projection'] is None
""")
        rows = classify_reads(result.events, self.rules)
        self.assertEqual(["players-pwf-delivery"], [row["rule"] for row in rows])
        with self.assertRaisesRegex(TraceError, "Delivery read in producer stage"):
            classify_reads(result.events, self.rules, own_product="league-forecast")

    def test_decision_windows_transitive_read_boundaries_at_fixed_clock(self):
        # Exercise the actual Decision Windows input assembly and actual
        # population roster/draft readers. Unrelated lifecycle, schedule,
        # identity resolver and provider profile dependencies are fixture mocks,
        # not claims of complete current-chain execution.
        metadata = self.metadata_fixture("league-a")
        year = sorted(metadata["Seasons"])[0]
        self.put(ROOTS["meta"] / "league-a" / "metadata.json", metadata)
        season_dir = ROOTS["source"] / "leagues" / "league-a" / "seasons" / year
        self.put(season_dir / "league.json", {"ProviderMappings": [{"Provider": "Sleeper",
                  "ProviderLeagueID": "provider-fixture"}], "RosterPositions": ["QB"]})
        player = {"CanonicalPlayerID": "c1", "ProviderMappings": [{"Provider": "Sleeper",
                  "ProviderPlayerID": "p1"}]}
        self.put(season_dir / "rosters.json", [{"CanonicalLeagueRosterID": "r1",
                 "ProviderMappings": [{"Provider": "Sleeper", "ProviderRosterID": "1"}],
                 "Players": [player], "Starters": [player]}])
        raw = ROOTS["source"] / "providers" / "sleeper" / "leagues" / "provider-fixture" / "rosters.json"
        self.put(raw, [{"roster_id": 1, "starters": ["p1", "0"]}])
        self.put(ROOTS["source"] / "nfl" / "identities" / "players.json", {"Players": []})
        availability = ROOTS["source"] / "nfl" / "player-availability" / "espn.json"
        self.put(availability, {"Records": []})
        self.put(ROOTS["source"] / "nfl" / "rosters" / (year + ".json"),
                 {"Records": [{"CanonicalPlayerID": "c1"}]})
        self.put(ROOTS["source"] / "nfl" / "weekly-rosters" / year / "01.json",
                 {"Records": [{"CanonicalPlayerID": "c1"}]})
        self.put(ROOTS["source"] / "nfl" / "draft" / (year + ".json"),
                 {"Picks": [{"CanonicalPlayerID": "c1"}]})
        code = f"""
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch, Mock
from contextlib import ExitStack
from derived_data_lib import decision_windows as d
import players_population as p
root = Path.cwd()
clock = datetime(int({year!r}), 9, 1, 12, tzinfo=timezone.utc)
resolver = Mock()
resolver.resolve.return_value = ('c1', 'resolved')
with ExitStack() as stack:
    for obj, name, value in [
        (d, 'resolve_lifecycle', {{'LineupWeek': 1, 'LastLeagueWeek': 17,
                                 'WaiversOpen': False, 'NextWaiverRun': None}}),
        (d, 'build_schedule', []),
        (p, 'load_snapshot', [{{'SleeperPlayerID': 'p1', 'Position': 'QB',
                               'BirthDate': '2000-01-01', 'FullName': 'Fixture Player'}}]),
        (p.NflTeamRegistry, 'load', None),
        (p.SleeperIdentityResolver, 'from_repo', resolver),
        (p, 'league_owned_sleeper_ids', set()),
        (p, 'provider_ids_by_canonical', {{}}),
        (p, 'load_profiles', {{}}),
    ]:
        stack.enter_context(patch.object(obj, name, return_value=value))
    inputs = d._inputs(root, 'league-a', int({year!r}), clock)
    assert inputs['rosters'][0]['StarterSlots'] == ['p1', None]
    assert inputs['players'][0]['PlayerID'] == 'p1'
    assert inputs['lineup_week'] == 1
    assert inputs['availability_snapshot'] == EXPECTED_AVAILABILITY
"""
        normal = self.run_code(code.replace("EXPECTED_AVAILABILITY", "{'Records': []}"))
        rows = classify_reads(normal.events, self.rules, own_product="league-forecast")
        expected = {"dw-league", "dw-canonical-rosters", "dw-raw-rosters", "dw-identities",
                    "dw-espn-availability", "population-nfl-rosters",
                    "population-weekly-rosters", "population-nfl-draft", "dw-metadata"}
        self.assertEqual(expected, {row["rule"] for row in rows})
        self.assertEqual(len(expected), len(rows))
        (self.root / availability).write_text("not JSON", encoding="utf-8")
        unknown = self.run_code(code.replace("EXPECTED_AVAILABILITY", "None"))
        self.assertEqual(expected, {row["rule"] for row in classify_reads(unknown.events, self.rules)})
        self.put(raw, [{"roster_id": 1, "starters": ["p2"]}])
        rejected = self.run_code(code.replace("EXPECTED_AVAILABILITY", "None"), rc=1)
        self.assertIn("contradict the canonical rosters", rejected.process.stderr)
        self.assertEqual({"dw-league", "dw-canonical-rosters", "dw-raw-rosters"},
                         {row["rule"] for row in classify_reads(rejected.events, self.rules)})

    def test_scratch_guard_rejects_linked_output_mutations(self):
        external = tempfile.TemporaryDirectory()
        self.addCleanup(external.cleanup)
        linked = Path(external.name)
        original = linked / "seed.json"
        original.write_text("unchanged", encoding="utf-8")
        derived = self.root / ROOTS["derived"]
        derived.mkdir()
        (derived / "linked-product").symlink_to(linked, target_is_directory=True)
        for action in ("path.write_text('mutated')", "path.unlink()",
                       "path.rename(path.with_name('renamed.json'))"):
            code = f"""
from pathlib import Path
from forecast_dependency_trace import ROOTS
path = Path.cwd() / ROOTS['derived'] / 'linked-product' / 'seed.json'
{action}
"""
            result = self.run_code(code, rc=1)
            self.assertIn("Write outside writable scratch data", result.process.stderr)
            self.assertEqual("unchanged", original.read_text(encoding="utf-8"))
            self.assertFalse((linked / "renamed.json").exists())

    def test_swallowed_scratch_violation_still_fails_classification(self):
        external = tempfile.TemporaryDirectory()
        self.addCleanup(external.cleanup)
        original = Path(external.name) / "seed.json"
        original.write_text("unchanged", encoding="utf-8")
        derived = self.root / ROOTS["derived"]
        derived.mkdir()
        (derived / "linked-product").symlink_to(original.parent, target_is_directory=True)
        result = self.run_code("""
from pathlib import Path
from forecast_dependency_trace import ROOTS
path = Path.cwd() / ROOTS['derived'] / 'linked-product' / 'seed.json'
try:
    path.write_text('mutated')
except ValueError:
    pass
""")
        self.assertEqual("unchanged", original.read_text(encoding="utf-8"))
        with self.assertRaisesRegex(TraceError, "Blocked data access"):
            classify_reads(result.events, self.rules)

    def test_context_and_injury_persistence_comparisons(self):
        # Actual writers, deterministic mocked calculations: cheap Fast
        # counterpart to the real-source Deep replay.
        code = """
from pathlib import Path
from unittest.mock import patch
from datetime import datetime, timezone
from data_roots import data_derived_dir
import matchup_context_materialize as c
import team_injury_impact_materialize as i
root = Path.cwd()
out = data_derived_dir(root)
with patch.object(c, 'build_documents', return_value={c.MATCHUPS: lambda: {'Week': 1}}):
    args = (root, out, 'league-a', 2025, 2025, datetime(2025, 11, 28, tzinfo=timezone.utc))
    assert c.materialize_season(*args)['Written'] == 1
    assert c.materialize_season(*args)['Written'] == 0
with patch.object(i, 'resolve_team_injury_impact', return_value={'Season': 2025}):
    args = (root, out, 'league-a', 2025)
    assert i.materialize_season(*args)['Written'] == 1
    assert i.materialize_season(*args)['Written'] == 0
"""
        result = self.run_code(code)
        rows = classify_reads(result.events, self.rules)
        self.assertEqual(["context-noop", "injury-noop"], [row["rule"] for row in rows])
        self.assertTrue(all(row["role"] == "comparison" for row in rows))

    def test_outlook_full_rebuild_ignores_poisoned_legacy_cache(self):
        # Reuse the repository's existing synthetic season inputs, while
        # exercising the real model, materializer, index and cache reader.
        code = f"""
from pathlib import Path
import sys
from unittest.mock import patch
from data_roots import data_derived_dir
sys.path.insert(0, {str(TOOLS / "tests")!r})
import test_league_schedule_outlook_materialize as f
import league_schedule_outlook_materialize as m
root = Path.cwd()
out = data_derived_dir(root)
folder = m.product_dir(out, f.LEAGUE, f.SEASON)
with patch.object(m.source, 'load_season_inputs', side_effect=lambda *a: f.inputs_from(f.facts())):
    args = (root, out, f.LEAGUE, f.SEASON, f.MODEL)
    first = m.materialize_season(*args, odds_model_id=f.ODDS, mode='full')
    second = m.materialize_season(*args, odds_model_id=f.ODDS)
    assert first['Written'] == 7 and second['Written'] == 0, (first, second)
"""
        # Split harness reads/writes from the actual producer trace: obtain the
        # initial bytes in the parent and poison them between invocations.
        initial = code
        first = self.run_code(initial)
        rows = classify_reads(first.events, self.rules, own_product="league-schedule-outlook")
        self.assertTrue(rows)
        self.assertTrue(all(row["role"] == "comparison" for row in rows))
        folder = self.root / ROOTS["derived"] / "league-schedule-outlook"
        paths = sorted(folder.rglob("*.json"))
        expected = {path: path.read_bytes() for path in paths}
        self.assertEqual(7, len(expected))
        path = next(p for p in paths if p.name == "after-week-00.json")
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc["Poison"] = True
        path.write_text(json.dumps(doc), encoding="utf-8")
        repair_code = initial.split("    first =")[0] + """
    repair = m.materialize_season(*args, odds_model_id=f.ODDS, mode='full')
    assert repair['Written'] >= 1, repair
"""
        repaired = self.run_code(repair_code)
        rows = classify_reads(repaired.events, self.rules, own_product="league-schedule-outlook")
        self.assertTrue(all(row["role"] == "comparison" for row in rows))
        self.assertEqual(expected, {p: p.read_bytes() for p in paths})

    @deep_only("Real multi-season materializer replay belongs to consumer restore")
    def test_real_historical_materializer_chain_without_prior_outputs(self):
        # Actual configured leagues and all their manifest seasons, no mocks
        # of the four materializers. PWF/TWP are fixed, accepted upstream
        # products here, not rebuilt. This is a partial clean-root proof
        # (target-output independence), not a full Source-only restore.
        from league_metadata import list_league_ids
        from league_standings_sources import manifest, manifest_seasons, current_season

        checkout = TOOLS.parent
        leagues = list_league_ids(checkout / ROOTS["meta"])
        self.assertTrue(leagues)
        seasons = {}
        for league in leagues:
            lineage = manifest(checkout, league)
            current = current_season(lineage)
            seasons[league] = [year for year in manifest_seasons(lineage) if year <= current]
            self.assertIn(current, seasons[league])
        self.assertTrue(any(len(years) > 1 for years in seasons.values()),
                        "Need at least one current and completed-season configuration")

        # Like the existing clean-root audit, keep Source and metadata linked
        # for disk efficiency. The trace guard prohibits Python mutation of
        # those roots and linked upstream products; generated targets are real
        # scratch directories. No repository publisher is invoked.
        for key in ("source", "canonical", "meta"):
            upstream = checkout / ROOTS[key]
            if upstream.is_dir():
                (self.root / ROOTS[key]).symlink_to(upstream, target_is_directory=True)
        out = self.root / ROOTS["derived"]
        out.mkdir()
        for product in ("player-week-fantasy", "team-week-performance"):
            upstream = checkout / ROOTS["derived"] / product
            self.assertTrue(upstream.is_dir(), product)
            (out / product).symlink_to(upstream, target_is_directory=True)

        def snapshot(product):
            folder = out / product
            return {p.relative_to(folder).as_posix(): p.read_bytes()
                    for p in sorted(folder.rglob("*.json"))}

        def run_stage(product):
            code = f"""
from pathlib import Path
import json
from data_roots import data_derived_dir
import derived_data as d
import weekly_recaps_materialize as w
import league_records_materialize as records
root = Path.cwd()
out = data_derived_dir(root)
summaries = []
for league, years in {seasons!r}.items():
    product = {product!r}
    if product == 'season-statistics':
        rows = d.materialize_season_statistics(root, out, league, years, False)['Seasons']
    elif product == 'league-standings':
        rows = d.materialize_league_standings(root, out, league, years, False)['Seasons']
    elif product == 'league-records':
        rows = [records.materialize(root, out, league, write=True)]
    else:
        rows = w.materialize(root, out, league, 'all', fail_on_error=True)
    if product != 'league-records':
        assert sorted(row['Season'] for row in rows) == years, (league, product, rows)
    summaries.extend(row['Written'] for row in rows)
print('AC6A_WRITES=' + json.dumps(summaries))
"""
            result = trace_python(self.root, ["-c", code], timeout=240)
            self.assertEqual(0, result.process.returncode,
                             result.process.stdout + result.process.stderr)
            # List all distinct missing/ambiguous call sites before failing;
            # never automatically promote an observed access to an input rule.
            uncovered = {}
            for event in result.events:
                if event["kind"] == "open" and event["read"]:
                    matches = [rule.id for rule in self.rules if rule.matches(event)]
                    if len(matches) != 1:
                        key = (event["root"], tuple(event["sites"][:2]), tuple(matches))
                        uncovered.setdefault(key, event["path"])
            self.assertFalse(uncovered, repr(uncovered))
            classified = classify_reads(result.events, self.rules, own_product=product)
            self.assertTrue(classified, product)
            self.assertTrue(any(row["role"] == "input" for row in classified))
            self.assertFalse(any(row["root"] == "app" for row in classified))
            writes = [event for event in result.events if event.get("write")]
            self.assertTrue(all(event["root"] == "derived"
                                and event["path"].split("/")[0] == product
                                for event in writes), writes[:10])
            summary = next(line.split("=", 1)[1] for line in result.process.stdout.splitlines()
                           if line.startswith("AC6A_WRITES="))
            return sum(json.loads(summary)), len(writes), classified

        for product in ("season-statistics", "league-standings", "league-records", "weekly-recaps"):
            with self.subTest(product=product):
                self.assertEqual({}, snapshot(product))
                first, attempts, first_reads = run_stage(product)
                expected = snapshot(product)
                self.assertTrue(expected)
                wanted = (set(f"{league}.json" for league in leagues)
                          if product == "league-records" else
                          set(f"{league}/{year}.json" for league, years in seasons.items() for year in years))
                self.assertEqual(wanted, set(expected))
                self.assertEqual(len(expected), first)
                self.assertGreater(attempts, 0)
                second, attempts, second_reads = run_stage(product)
                self.assertEqual((0, 0), (second, attempts))
                self.assertEqual(expected, snapshot(product))
                # An incorrect existing document, plus poisoned App copies,
                # must not influence the rebuilt model.
                for path in expected:
                    (out / product / path).write_text('{"poison": true}', encoding="utf-8")
                for name in ("SeasonStatistics.json", "Standings.json", "WeeklyRecaps.json"):
                    self.put(ROOTS["app"] / name, {"poison": True})
                repaired, attempts, repair_reads = run_stage(product)
                self.assertEqual(len(expected), repaired)
                self.assertGreater(attempts, 0)
                self.assertEqual(expected, snapshot(product))
                self.assertTrue(any(row["role"] == "comparison" for row in second_reads))
                self.assertTrue(any(row["role"] == "comparison" for row in repair_reads))
                # Published files may be stale; report the count, but never
                # mistake target-output independence for publication freshness.
                published = checkout / ROOTS["derived"] / product
                differences = sum(not (published / path).is_file()
                                  or (published / path).read_bytes() != content
                                  for path, content in expected.items())
                print(f"AC6A historical {product}: files={len(expected)} "
                      f"reads={len(first_reads)}/{len(second_reads)}/{len(repair_reads)} "
                      f"published_differences={differences}", flush=True)

    @deep_only("Real current/historical projection materializers and cache replay")
    def test_real_context_outlook_and_injury_materializer_chain(self):
        # The actual upstream products are held fixed. No App data is linked.
        # Full Source-only restoration is a different, existing Deep gate.
        from league_metadata import list_league_ids
        from league_standings_sources import manifest, manifest_seasons, current_season

        checkout = TOOLS.parent
        leagues = list_league_ids(checkout / ROOTS["meta"])
        self.assertTrue(leagues)
        seasons = {}
        for league in leagues:
            lineage = manifest(checkout, league)
            current = current_season(lineage)
            seasons[league] = [year for year in manifest_seasons(lineage) if year <= current]
            self.assertIn(current, seasons[league])
        for key in ("source", "canonical", "meta"):
            upstream = checkout / ROOTS[key]
            if upstream.is_dir():
                (self.root / ROOTS[key]).symlink_to(upstream, target_is_directory=True)
        out = self.root / ROOTS["derived"]
        out.mkdir()
        for product in ("player-week-fantasy", "team-week-performance", "season-statistics",
                        "league-standings", "league-drafts", "nfl-games", "nfl-player-availability"):
            upstream = checkout / ROOTS["derived"] / product
            self.assertTrue(upstream.is_dir(), product)
            (out / product).symlink_to(upstream, target_is_directory=True)
        for name in ("Matchups.json", "FantasyGameContext.json", "MatchupProjections.json",
                     "SeasonStatistics.json", "PlayerWeekFantasy.json", "League.json"):
            self.put(ROOTS["app"] / name, {"poison": True})

        def snapshot(product):
            folder = out / product
            return {p.relative_to(folder).as_posix(): p.read_bytes()
                    for p in sorted(folder.rglob("*.json"))}

        def run_stage(product, mode):
            code = f"""
from pathlib import Path
from datetime import datetime, timezone
import json
from data_roots import data_derived_dir
import matchup_context_materialize as c
import league_schedule_outlook_materialize as o
import team_injury_impact_materialize as i
root = Path.cwd()
out = data_derived_dir(root)
summaries = []
for league, years in {seasons!r}.items():
    current = max(years)
    product = {product!r}
    if product == 'matchup-context':
        # Explicit deterministic observation clock, not a reconstruction of
        # an actually observed historic forecast or the published clock.
        clock = datetime(current, 11, 28, 12, tzinfo=timezone.utc)
        rows = c.materialize(root, out, league, 'all', clock, fail_on_error=True)
        assert sorted(row['Season'] for row in rows) == years, rows
        assert all(not row['Skipped'] for row in rows), rows
    elif product == 'league-schedule-outlook':
        rows = [o.materialize_season(root, out, league, year,
                    o.selected_model_id(root, league, year), mode={mode!r})
                for year in years]
    else:
        rows = [i.materialize_season(root, out, league, year) for year in years]
    summaries.extend(row['Written'] for row in rows)
print('AC6A_WRITES=' + json.dumps(summaries))
"""
            result = trace_python(self.root, ["-c", code], timeout=480)
            self.assertEqual(0, result.process.returncode,
                             result.process.stdout + result.process.stderr)
            uncovered = {}
            for event in result.events:
                if event["kind"] == "open" and event["read"]:
                    matches = [rule.id for rule in self.rules if rule.matches(event)]
                    if len(matches) != 1:
                        key = (event["root"], tuple(event["sites"][:2]), tuple(matches))
                        uncovered.setdefault(key, event["path"])
            self.assertFalse(uncovered, repr(uncovered))
            classified = classify_reads(result.events, self.rules, own_product=product)
            self.assertTrue(any(row["role"] == "input" for row in classified))
            self.assertFalse(any(row["root"] == "app" for row in classified))
            writes = [event for event in result.events if event.get("write")]
            self.assertTrue(all(event["root"] == "derived"
                                and event["path"].split("/")[0] == product
                                for event in writes), writes[:10])
            summary = next(line.split("=", 1)[1] for line in result.process.stdout.splitlines()
                           if line.startswith("AC6A_WRITES="))
            return sum(json.loads(summary)), len(writes), classified

        for product in ("matchup-context", "league-schedule-outlook", "team-injury-impact"):
            with self.subTest(product=product):
                self.assertEqual({}, snapshot(product))
                first, attempts, first_reads = run_stage(product, "full")
                expected = snapshot(product)
                self.assertTrue(expected)
                self.assertEqual(len(expected), first)
                self.assertGreater(attempts, 0)
                for league, years in seasons.items():
                    if product == "matchup-context":
                        for year in years:
                            self.assertIn(f"{league}/{year}/matchups.json", expected)
                        current_path = f"{league}/{max(years)}/current.json"
                        self.assertIn(current_path, expected)
                        current_doc = json.loads(expected[current_path])
                        self.assertIsNotNone(current_doc["FantasyGameContext"],
                                             "Current context did not exercise active-week path")
                        self.assertIsNotNone(current_doc["MatchupProjections"],
                                             "Current projection did not exercise PWF path")
                    elif product == "league-schedule-outlook":
                        for year in years:
                            index_path = f"{league}/{year}/index.json"
                            self.assertIn(index_path, expected)
                            index = json.loads(expected[index_path])
                            self.assertEqual(index["LeagueScoredWeek"] + 1, len(index["Snapshots"]))
                            for row in index["Snapshots"]:
                                self.assertIn(f"{league}/{year}/{row['File']}", expected)
                    else:
                        for year in years:
                            self.assertIn(f"{league}/{year}.json", expected)
                # Check the real incremental/no-op path, then force a full
                # candidate computation on intentionally wrong prior output.
                second, attempts, second_reads = run_stage(product, "incremental")
                self.assertEqual((0, 0), (second, attempts))
                self.assertEqual(expected, snapshot(product))
                for path in expected:
                    (out / product / path).write_text('{"poison": true}', encoding="utf-8")
                repaired, attempts, repair_reads = run_stage(product, "full")
                self.assertEqual(len(expected), repaired)
                self.assertGreater(attempts, 0)
                self.assertEqual(expected, snapshot(product))
                self.assertTrue(any(row["role"] == "comparison" for row in second_reads))
                self.assertTrue(any(row["role"] == "comparison" for row in repair_reads))
                # Published current context is clock-dependent. Report, not
                # assert, differences to the persisted clock's snapshot.
                published = checkout / ROOTS["derived"] / product
                differences = sum(not (published / path).is_file()
                                  or (published / path).read_bytes() != content
                                  for path, content in expected.items())
                print(f"AC6A current/history {product}: files={len(expected)} "
                      f"reads={len(first_reads)}/{len(second_reads)}/{len(repair_reads)} "
                      f"published_differences={differences}", flush=True)

    @deep_only("Real PWF historical batch across seasons and independent official TWP replay")
    def test_real_pwf_batch_and_twp_optional_parity(self):
        # The PWF witness covers the first and last finalized week of each
        # actual league-season, including actual scoring and fitted state.
        # The existing full Restore Gate is responsible for all PWF weeks.
        # TWP is fully rebuilt with no PWF, then with PWF for optional parity.
        from historical_pwf_batch import discover_scored_weeks
        from league_metadata import list_league_ids

        checkout = TOOLS.parent
        targets = discover_scored_weeks(checkout)
        by_season = {}
        for league, year, week in targets:
            by_season.setdefault((league, year), []).append(week)
        self.assertTrue(by_season)
        selections = [(league, year, sorted({min(weeks), max(weeks)}))
                      for (league, year), weeks in sorted(by_season.items())]
        leagues = list_league_ids(checkout / ROOTS["meta"])
        for key in ("source", "canonical", "meta"):
            upstream = checkout / ROOTS[key]
            if upstream.is_dir():
                (self.root / ROOTS[key]).symlink_to(upstream, target_is_directory=True)
        out = self.root / ROOTS["derived"]
        out.mkdir()
        for name in ("PlayerWeekFantasy.json", "League.json", "Players.json"):
            self.put(ROOTS["app"] / name, {"poison": True})

        def snapshot(product):
            folder = out / product
            return {p.relative_to(folder).as_posix(): p.read_bytes()
                    for p in sorted(folder.rglob("*.json"))}

        def run_batch(product):
            code = f"""
from pathlib import Path
import json
from historical_pwf_batch import materialize_historical
from player_week_fantasy_materialize import memoized_model_state
from team_week_performance_materialize import materialize_all_finalized
root = Path.cwd()
reports = []
if {product!r} == 'player-week-fantasy':
    # The existing refresh memo is process-local, keyed by immutable source
    # and scoring settings. No persisted fitted state or output is used.
    with memoized_model_state():
        for league, year, weeks in {selections!r}:
            reports.append(materialize_historical(root, league_id=league,
                           seasons=[year], weeks=weeks, write=True))
else:
    for league in {leagues!r}:
        reports.append(materialize_all_finalized(root, league_id=league,
                       write=True, require_pwf=False))
for report in reports:
    assert report['BlockedCount'] == 0, report
    assert report['ReadyCount'] == report['TargetCount'] > 0, report
print('AC6A_WRITES=' + json.dumps([r['ChangedCount'] for r in reports]))
"""
            result = trace_python(self.root, ["-c", code], timeout=480)
            self.assertEqual(0, result.process.returncode,
                             result.process.stdout + result.process.stderr)
            uncovered = {}
            for event in result.events:
                if event["kind"] == "open" and event["read"]:
                    matches = [rule.id for rule in self.rules if rule.matches(event)]
                    if len(matches) != 1:
                        key = (event["root"], tuple(event["sites"][:2]), tuple(matches))
                        uncovered.setdefault(key, event["path"])
            self.assertFalse(uncovered, repr(uncovered))
            classified = classify_reads(result.events, self.rules, own_product=product)
            self.assertTrue(any(row["role"] == "input" for row in classified))
            self.assertFalse(any(row["root"] == "app" for row in classified))
            writes = [event for event in result.events if event.get("write")]
            self.assertTrue(all(event["root"] == "derived"
                                and event["path"].split("/")[0] == product
                                for event in writes), writes[:10])
            summary = next(line.split("=", 1)[1] for line in result.process.stdout.splitlines()
                           if line.startswith("AC6A_WRITES="))
            return sum(json.loads(summary)), len(writes), classified

        # No PWF is present: the official Sleeper-derived TWP product must
        # build independently of the optional cross-check.
        twp = "team-week-performance"
        first, writes, reads = run_batch(twp)
        official = snapshot(twp)
        self.assertTrue(official)
        self.assertEqual(len(official), first)
        self.assertGreater(writes, 0)
        self.assertFalse(any(row["rule"] == "twp-pwf-parity" for row in reads))

        pwf = "player-week-fantasy"
        first, writes, reads = run_batch(pwf)
        calculated = snapshot(pwf)
        wanted = {f"{league}/{year}/{week:02d}.json"
                  for league, year, weeks in selections for week in weeks}
        self.assertEqual(wanted, set(calculated))
        self.assertEqual(len(calculated), first)
        self.assertGreater(writes, 0)
        self.assertFalse(any(row["root"] == "derived" for row in reads))
        # Confirm newly calculated partitions agree byte-for-byte with the
        # accepted historical PWF (no activation or model correction).
        published = checkout / ROOTS["derived"] / pwf
        self.assertEqual(calculated, {path: (published / path).read_bytes() for path in wanted})
        # The actual batch writer must be a no-op on a second calculation.
        second, writes, reads = run_batch(pwf)
        self.assertEqual((0, 0), (second, writes))
        self.assertEqual(calculated, snapshot(pwf))
        self.assertTrue(any(row["rule"] == "pwf-batch-noop" for row in reads))

        # With actual PWF available in the scratch root, optional parity may
        # report differences, but cannot alter any official TWP result.
        second, writes, reads = run_batch(twp)
        self.assertEqual((0, 0), (second, writes))
        self.assertEqual(official, snapshot(twp))
        self.assertTrue(any(row["rule"] == "twp-pwf-parity" for row in reads))
        published_twp = checkout / ROOTS["derived"] / twp
        self.assertEqual(official, {path: (published_twp / path).read_bytes() for path in official})
        print(f"AC6A PWF/TWP: PWF sample partitions={len(calculated)}, "
              f"official TWP partitions={len(official)}, byte parity=true", flush=True)

    def test_real_powershell_metadata_read_boundary(self):
        pwsh = shutil.which("pwsh")
        if pwsh is None:
            if os.environ.get("CI", "").lower() == "true":
                self.fail("pwsh is required in CI for the AC6A native runtime witness")
            self.skipTest("pwsh is not installed locally; PowerShell evidence is incomplete")
        source = sorted((TOOLS.parent / ROOTS["meta"]).glob("*/metadata.json"))
        self.assertTrue(source, "Need one configured metadata schema fixture")
        base = json.loads(source[0].read_text(encoding="utf-8-sig"))
        season = sorted(base["Seasons"])[0]
        models = base["Seasons"][season]["Models"]
        for league in ("league-a", "league-b", "invalid"):
            fixture = copy.deepcopy(base)
            fixture["CanonicalLeagueID"] = league
            if league == "invalid":
                fixture["Seasons"][season]["Models"]["TeamRange"] = "unknown-fixture-model"
            self.put(ROOTS["meta"] / league / "metadata.json", fixture)
        events_path = self.root / "pwsh-events.json"
        script = MANIFEST.with_name("forecast_metadata_reader_trace.ps1")
        result = subprocess.run(
            [pwsh, "-NoProfile", "-NonInteractive", "-File", str(script),
             "-RepoRoot", str(TOOLS.parent), "-ScratchRoot", str(self.root),
             "-Season", season, "-ExpectedTeamRange", models["TeamRange"],
             "-ExpectedWinProb", models["WinProb"], "-EventFile", str(events_path)],
            cwd=self.root, capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        rows = classify_reads(json.loads(events_path.read_text(encoding="utf-8")), self.rules)
        self.assertEqual(["pwsh-league-metadata"] * 3, [row["rule"] for row in rows])
        self.assertEqual(["league-a/metadata.json", "league-b/metadata.json", "invalid/metadata.json"],
                         [row["path"] for row in rows])

    def test_ambiguous_manifest_and_uninstrumented_subprocess_fail_closed(self):
        self.put(Path(DATA_DERIVED_ROOT, "player-week-fantasy", "league-a", "2025", "01.json"),
                 {"Records": []})
        result = self.run_code("""
from pathlib import Path
from derived_data_lib.weekly_recaps import _pwf_projections
assert _pwf_projections(Path.cwd(), 'league-a', 2025, 1) == {}
""")
        duplicate = replace(next(rule for rule in self.rules if rule.id == "recaps-pwf"), id="duplicate")
        with self.assertRaisesRegex(TraceError, "got 2"):
            classify_reads(result.events, self.rules + (duplicate,))
        with self.assertRaisesRegex(TraceError, "Uncovered Python subprocess boundary"):
            trace_python(self.root, ["-c", "import subprocess,sys; subprocess.run([sys.executable,'-S','-c','pass'],check=True)"])


if __name__ == "__main__":
    unittest.main()
