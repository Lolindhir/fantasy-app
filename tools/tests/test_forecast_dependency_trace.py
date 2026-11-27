"""AC6A read-trace foundation: actual Python boundary calls on scratch fixtures."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

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
