"""Tests for the team-injury-impact materializer and App renderer (Issue #1584 CP5): layout, byte no-op, scope, fail modes."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import injury_impact_app_publish as pub  # noqa: E402
import team_injury_impact_materialize as mat  # noqa: E402
from derived_data_lib.team_injury_impact import TeamInjuryImpactError  # noqa: E402

LEAGUE = "test-league"
DOC = {"Season": 2025, "Models": {"InjuryImpact": "m"}, "AsOf": {}, "UnavailableWeeks": [], "SeasonTotals": [{"CanonicalLeagueRosterID": "r1", "Impact": 1.5}], "Weeks": []}


class MaterializeTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def test_written_once_then_byte_no_op_and_no_clock(self):
        with mock.patch.object(mat, "resolve_team_injury_impact", return_value=DOC):
            first = mat.materialize_season(self.root, self.root, LEAGUE, 2025)
            second = mat.materialize_season(self.root, self.root, LEAGUE, 2025)
        self.assertEqual((1, 0), (first["Written"], second["Written"]))
        self.assertEqual(self.root / "team-injury-impact" / LEAGUE / "2025.json", mat.product_path(self.root, LEAGUE, 2025))
        self.assertEqual(DOC, json.loads(mat.product_path(self.root, LEAGUE, 2025).read_text(encoding="utf-8")))
        self.assertNotIn("AsOfUtc", mat.serialize(DOC))

    def test_check_only_writes_nothing(self):
        with mock.patch.object(mat, "resolve_team_injury_impact", return_value=DOC):
            summary = mat.materialize_season(self.root, self.root, LEAGUE, 2025, check_only=True)
        self.assertEqual(1, summary["WouldWrite"])
        self.assertFalse(mat.product_path(self.root, LEAGUE, 2025).exists())

    def test_scope_selects_current_and_completed_seasons(self):
        with mock.patch.object(mat, "manifest", return_value={}), mock.patch.object(mat, "current_season", return_value=2026), \
                mock.patch.object(mat, "manifest_seasons", return_value=[2024, 2025, 2026]), \
                mock.patch.object(mat, "completed_seasons", return_value=[2024, 2025]):
            self.assertEqual((2026, [2026]), mat.seasons_for_scope(self.root, LEAGUE, "current"))
            self.assertEqual((2026, [2024, 2025]), mat.seasons_for_scope(self.root, LEAGUE, "history"))
            self.assertEqual((2026, [2024, 2025, 2026]), mat.seasons_for_scope(self.root, LEAGUE, "all"))

    def test_history_error_is_skipped_but_running_season_fails_with_flag(self):
        with mock.patch.object(mat, "seasons_for_scope", return_value=(2026, [2025, 2026])), \
                mock.patch.object(mat, "materialize_season", side_effect=TeamInjuryImpactError("source not ready")):
            self.assertEqual([], mat.materialize(self.root, self.root, LEAGUE, "all"))
            with self.assertRaises(TeamInjuryImpactError):
                mat.materialize(self.root, self.root, LEAGUE, "all", fail_on_error=True)


class RenderTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        profiles = self.root / "data-source" / "nfl" / "player-profiles" / "nflverse.json"
        profiles.parent.mkdir(parents=True, exist_ok=True)
        profiles.write_text(json.dumps({"SourceDataset": "nflverse.players", "Records": []}), encoding="utf-8")

    def _put(self, season: int, document: dict) -> None:
        path = self.root / "data-derived" / "team-injury-impact" / LEAGUE / f"{season}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(document), encoding="utf-8")

    def _inputs(self):
        team = {"CanonicalLeagueRosterID": "r1", "TeamID": 7, "Owner": "Owner", "Team": "Team"}
        return mock.Mock(teams=[team])

    def _patches(self):
        return (mock.patch.object(pub, "manifest", return_value={}), mock.patch.object(pub, "current_season", return_value=2026),
                mock.patch.object(pub, "manifest_seasons", return_value=[2025, 2026]),
                mock.patch.object(pub, "load_season_inputs", return_value=self._inputs()))

    def test_renders_seasons_with_team_identity_and_leaves_documents_unchanged(self):
        self._put(2025, DOC)
        self._put(2026, {**DOC, "Season": 2026})
        a, b, c, d = self._patches()
        with a, b, c, d:
            out = pub.render(self.root, LEAGUE)
        self.assertEqual([2025, 2026], [s["Season"] for s in out["Seasons"]])
        self.assertEqual([{"CanonicalLeagueRosterID": "r1", "TeamID": 7, "Owner": "Owner", "TeamName": "Team"}], out["Seasons"][0]["Teams"])
        self.assertEqual([{**DOC["SeasonTotals"][0], "CostlyPlayersPerWeek": None}], out["Seasons"][0]["SeasonTotals"])

    def test_missing_history_season_warns_but_missing_current_season_fails(self):
        self._put(2026, {**DOC, "Season": 2026})
        a, b, c, d = self._patches()
        with a, b, c, d:
            self.assertEqual([2026], [s["Season"] for s in pub.render(self.root, LEAGUE)["Seasons"]])
        (self.root / "data-derived" / "team-injury-impact" / LEAGUE / "2026.json").unlink()
        self._put(2025, DOC)
        a, b, c, d = self._patches()
        with a, b, c, d, self.assertRaises(TeamInjuryImpactError):
            pub.render(self.root, LEAGUE)

    def test_unknown_roster_fails_closed(self):
        self._put(2025, {**DOC, "SeasonTotals": [{"CanonicalLeagueRosterID": "ghost", "Impact": 0}]})
        self._put(2026, DOC)
        a, b, c, d = self._patches()
        with a, b, c, d, self.assertRaises(TeamInjuryImpactError):
            pub.render(self.root, LEAGUE)

    def test_more_than_one_league_without_flag_fails_closed(self):
        with mock.patch.object(pub, "list_league_ids", return_value=["a", "b"]), self.assertRaises(TeamInjuryImpactError):
            pub.leagues(None)


if __name__ == "__main__":
    unittest.main()
