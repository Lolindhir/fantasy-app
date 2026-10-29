"""Focused parity and safe-publication guard tests for TeamWeekPerformance #355."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from team_week_performance_materialize import (  # noqa: E402
    discover_finalized_weeks, materialize_all_finalized, materialize, verify_pwf_actual_parity,
)
from data_roots import DATA_DERIVED_ROOT, DATA_SOURCE_ROOT, DATA_META_ROOT  # noqa: E402


class MaterializerParityTests(unittest.TestCase):
    def setUp(self) -> None:
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        self.model = {
            "CanonicalLeagueID": "nfl-reise",
            "Season": 2026,
            "Week": 5,
            "ScoringProfile": {"SettingsHash": "sha256:abc"},
        }
        self.matchups = [{"PlayerPoints": [
            {"Player": {"CanonicalPlayerID": "a"}, "Points": 9.5},
            {"Player": {"CanonicalPlayerID": "b"}, "Points": 0},
            {"Player": {"CanonicalPlayerID": "c"}, "Points": -2.25},
        ]}]
        self.path = (self.root / DATA_DERIVED_ROOT / "player-week-fantasy"
                     / "nfl-reise/2026/05.json")
        self.path.parent.mkdir(parents=True)

    def write_pwf(self, records: list[dict], *, fingerprint: str = "sha256:abc") -> None:
        self.path.write_text(json.dumps({
            "CanonicalLeagueID": "nfl-reise", "Season": 2026, "Week": 5,
            "ScoringProfile": {"SettingsHash": fingerprint},
            "Records": records,
        }), encoding="utf-8")

    @staticmethod
    def actual(player_id: str, score: float, state: str = "final") -> dict:
        return {"CanonicalPlayerID": player_id,
                "Actual": {"State": state, "Points": score}}

    def test_missing_pwf_can_be_optional_or_explicitly_required(self) -> None:
        self.assertEqual(
            verify_pwf_actual_parity(self.root, self.model, self.matchups)["State"],
            "not-available",
        )
        with self.assertRaisesRegex(ValueError, "Required PlayerWeekFantasy"):
            verify_pwf_actual_parity(self.root, self.model, self.matchups, require_pwf=True)

    def test_valid_snapshot_keeps_zero_missing_and_negative_scores(self) -> None:
        self.write_pwf([self.actual("a", 9.5), self.actual("c", -2.25)])
        self.assertEqual(
            verify_pwf_actual_parity(self.root, self.model, self.matchups, require_pwf=True),
            {"State": "verified", "Compared": 2, "MissingZeroPoints": 1},
        )

    def test_missing_nonzero_cannot_be_called_zero(self) -> None:
        self.write_pwf([self.actual("c", -2.25)])
        with self.assertRaisesRegex(ValueError, "missing nonzero scorer a"):
            verify_pwf_actual_parity(self.root, self.model, self.matchups)

    def test_stale_final_zero_and_nonfinal_actual_fail(self) -> None:
        self.write_pwf([self.actual("a", 0), self.actual("c", -2.25)])
        with self.assertRaisesRegex(ValueError, "scoring mismatch"):
            verify_pwf_actual_parity(self.root, self.model, self.matchups)
        self.write_pwf([self.actual("a", 9.5, state="pending"),
                        self.actual("c", -2.25)])
        with self.assertRaisesRegex(ValueError, "not final"):
            verify_pwf_actual_parity(self.root, self.model, self.matchups)

    def test_stale_fingerprint_and_duplicate_identity_fail(self) -> None:
        self.write_pwf([self.actual("a", 9.5)], fingerprint="sha256:other")
        with self.assertRaisesRegex(ValueError, "scoring fingerprint mismatch"):
            verify_pwf_actual_parity(self.root, self.model, self.matchups)
        self.write_pwf([self.actual("a", 9.5), self.actual("a", 9.5)])
        with self.assertRaisesRegex(ValueError, "duplicate PlayerWeekFantasy"):
            verify_pwf_actual_parity(self.root, self.model, self.matchups)

    def test_duplicate_canonical_player_points_rejected(self) -> None:
        self.write_pwf([self.actual("a", 9.5), self.actual("c", -2.25)])
        self.matchups[0]["PlayerPoints"].append(
            {"Player": {"CanonicalPlayerID": "a"}, "Points": 9.5}
        )
        with self.assertRaisesRegex(ValueError, "duplicate canonical matchup"):
            verify_pwf_actual_parity(self.root, self.model, self.matchups)



    def test_official_sleeper_awards_publish_despite_independent_nfl_parity_mismatch(self) -> None:
        # The scorer already uses canonical Sleeper PlayerPoints/StarterPoints;
        # NFL-based PlayerWeekFantasy is an optional quality signal, not a veto.
        model = {
            **self.model,
            "Teams": [{"CanonicalLeagueRosterID": "roster-a"}],
            "Awards": {"BestManagerRosterIDs": ["roster-a"],
                       "BestCoachRosterIDs": ["roster-a"]},
            "LineupDefinitionHash": "sha256:slots",
        }
        with patch("team_week_performance_materialize.load_verified_week_inputs",
                   return_value={"matchup_rows": self.matchups}), patch(
                       "team_week_performance_materialize.build_team_week_performance",
                       return_value=model), patch(
                       "team_week_performance_materialize.verify_pwf_actual_parity",
                       side_effect=ValueError("scoring mismatch: Sleeper=26.28 PWF=26.18")), patch(
                       "team_week_performance_materialize.save_team_week_performance",
                       return_value=True) as save:
            result = materialize(self.root, "nfl-reise", 2026, 5, write=True)
            self.assertTrue(result["Changed"])
            self.assertEqual(result["BestManagerRosterIDs"], ["roster-a"])
            self.assertEqual(result["PlayerWeekFantasyParity"], {
                "State": "mismatch",
                "Reason": "scoring mismatch: Sleeper=26.28 PWF=26.18",
            })
            save.assert_called_once_with(self.root, model)
            with self.assertRaisesRegex(ValueError, "scoring mismatch"):
                materialize(self.root, "nfl-reise", 2026, 5,
                            write=False, require_pwf=True)
            self.assertEqual(save.call_count, 1)


class BatchMaterializerTests(unittest.TestCase):
    def setUp(self) -> None:
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)

    def season(self, year: int, start: int, end: int, scored: int) -> None:
        folder = self.root / DATA_SOURCE_ROOT / "leagues/nfl-reise/seasons" / str(year)
        folder.mkdir(parents=True)
        (folder / "league.json").write_text(json.dumps({
            "CanonicalLeagueID": "nfl-reise", "Season": year,
            "RosterPositions": ["QB"], "ScoringSettings": {},
            "WeekStructure": {"Season": year, "StartWeek": start,
                              "ExpectedLastLeagueWeek": end,
                              "LastScoredLeg": scored},
        }), encoding="utf-8")

    def manifest(self, *years: int) -> None:
        meta = self.root / DATA_META_ROOT / "nfl-reise"
        meta.mkdir(parents=True)
        (meta / "metadata.json").write_text("{}", encoding="utf-8")
        folder = self.root / DATA_SOURCE_ROOT / "leagues/nfl-reise"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "manifest.json").write_text(json.dumps({
            "CanonicalLeagueID": "nfl-reise", "Seasons": [{"Season": year} for year in years],
        }), encoding="utf-8")

    def test_discovery_uses_canonical_manifest_and_scored_bounds_not_derived(self) -> None:
        self.manifest(2025, 2024, 2026)
        self.season(2024, 1, 17, 2)
        self.season(2025, 1, 17, 0)
        self.season(2026, 2, 17, 3)
        scored = {2024: 2, 2025: 0, 2026: 3}
        with patch("team_week_performance_materialize.load_league_metadata",
                   return_value={}), patch(
                       "team_week_performance_materialize.validate_against_manifest"), patch(
                       "team_week_performance_materialize.resolve_week_finality",
                       side_effect=lambda root, league, year: {"LeagueScoredWeek": scored[year]}):
            self.assertEqual(discover_finalized_weeks(self.root), [
                ("nfl-reise", 2024, 1), ("nfl-reise", 2024, 2),
                ("nfl-reise", 2026, 2), ("nfl-reise", 2026, 3),
            ])
            # The shared milestone, not LastScoredLeg alone, limits the weeks
            # (league scored but NFL games not final yet -> not listed).
            scored[2026] = 2
            self.assertEqual(discover_finalized_weeks(
                self.root, seasons=[2026]), [("nfl-reise", 2026, 2)])
            self.assertEqual(discover_finalized_weeks(
                self.root, league_id="nfl-reise", seasons=[2025]), [])
            with self.assertRaisesRegex(ValueError, "do not exist"):
                discover_finalized_weeks(self.root, seasons=[2027])

    def test_discovery_rejects_invalid_finalized_bounds(self) -> None:
        self.manifest(2026)
        self.season(2026, 1, 17, 18)
        with patch("team_week_performance_materialize.load_league_metadata",
                   return_value={}), patch(
                       "team_week_performance_materialize.validate_against_manifest"):
            with self.assertRaisesRegex(ValueError, "Invalid finalized-week bounds"):
                discover_finalized_weeks(self.root)

    @staticmethod
    def model(week: int) -> dict:
        return {"CanonicalLeagueID": "nfl-reise", "Season": 2026, "Week": week,
                "Teams": [{"CanonicalLeagueRosterID": "one"}]}

    def test_batch_fails_closed_before_first_write_when_week_blocked(self) -> None:
        targets = [("nfl-reise", 2026, 1), ("nfl-reise", 2026, 2)]
        with patch("team_week_performance_materialize.discover_finalized_weeks",
                   return_value=targets), patch(
                       "team_week_performance_materialize._checked_week",
                       side_effect=[(self.model(1), {"State": "verified"}),
                                    ValueError("PWF Actual not final")]), patch(
                       "team_week_performance_materialize.save_team_week_performance") as save:
            result = materialize_all_finalized(self.root, write=True)
            self.assertEqual((result["TargetCount"], result["ReadyCount"],
                              result["BlockedCount"], result["ChangedCount"]), (2, 1, 1, 0))
            self.assertTrue(result["WriteAborted"])
            self.assertEqual([w["Status"] for w in result["Weeks"]], ["ready", "blocked"])
            save.assert_not_called()

    def test_readonly_and_idempotent_write(self) -> None:
        targets = [("nfl-reise", 2026, 1), ("nfl-reise", 2026, 2)]
        models = [(self.model(1), {"State": "not-available"}),
                  (self.model(2), {"State": "verified"})]
        with patch("team_week_performance_materialize.discover_finalized_weeks",
                   return_value=targets), patch(
                       "team_week_performance_materialize._checked_week",
                       side_effect=models), patch(
                       "team_week_performance_materialize.save_team_week_performance") as save:
            report = materialize_all_finalized(self.root)
            self.assertFalse(report["WriteRequested"])
            self.assertEqual(report["ReadyCount"], 2)
            self.assertEqual(report["Weeks"][0]["PlayerWeekFantasyParity"]["State"],
                             "not-available")
            save.assert_not_called()
        with patch("team_week_performance_materialize.discover_finalized_weeks",
                   return_value=targets), patch(
                       "team_week_performance_materialize._checked_week",
                       side_effect=models), patch(
                       "team_week_performance_materialize.save_team_week_performance",
                       side_effect=[True, False]) as save:
            report = materialize_all_finalized(self.root, write=True)
            self.assertEqual(report["ChangedCount"], 1)
            self.assertFalse(report["WriteAborted"])
            self.assertEqual([w["Changed"] for w in report["Weeks"]], [True, False])
            self.assertEqual(save.call_count, 2)

    def test_unexpected_errors_are_not_converted_to_unavailable_data(self) -> None:
        with patch("team_week_performance_materialize.discover_finalized_weeks",
                   return_value=[("nfl-reise", 2026, 1)]), patch(
                       "team_week_performance_materialize._checked_week",
                       side_effect=RuntimeError("unexpected code problem")):
            with self.assertRaisesRegex(RuntimeError, "unexpected code problem"):
                materialize_all_finalized(self.root, write=True)


if __name__ == "__main__":
    unittest.main()
