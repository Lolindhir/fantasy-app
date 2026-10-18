"""Deterministic player-level Sleeper/PWF comparison and exact exception gate."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from data_roots import DATA_DERIVED_ROOT, DATA_META_ROOT
from player_scoring_reconciliation import reconcile, persist_verified, output_path
from team_week_performance_materialize import verify_pwf_actual_parity

REPO_ROOT = TOOLS.parent


class PlayerScoringReconciliationTests(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name)
        self.model = {
            "CanonicalLeagueID": "nfl-reise", "Season": 2025, "Week": 6,
            "ScoringProfile": {"SettingsHash": "sha256:test"},
        }
        self.matchups = [{
            "PlayerPoints": [
                {"Player": {"CanonicalPlayerID": "caleb"}, "Points": 19.88},
                {"Player": {"CanonicalPlayerID": "zero"}, "Points": 0},
            ],
        }]
        self.pwf_path = (self.root / DATA_DERIVED_ROOT /
                         "player-week-fantasy/nfl-reise/2025/06.json")
        self.pwf_path.parent.mkdir(parents=True)
        self.write_pwf(20.38)

    def write_pwf(self, points=20.38, actual_state="final"):
        rows = [{
            "CanonicalPlayerID": "caleb",
            "Actual": {"Points": points, "State": actual_state},
        }, {
            "CanonicalPlayerID": "free-agent",
            "Actual": {"Points": 4.5, "State": "final"},
        }]
        self.pwf_path.write_text(json.dumps({
            "CanonicalLeagueID": "nfl-reise", "Season": 2025, "Week": 6,
            "ScoringProfile": {"SettingsHash": "sha256:test"}, "Records": rows,
        }), encoding="utf-8")

    def policy(self, expected_league=19.88, expected_calc=20.38):
        p = self.root / DATA_META_ROOT / "nfl-reise/scoring-divergences.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({
            "ContractVersion": 1,
            "Exceptions": [{
                "Season": 2025, "Week": 6, "CanonicalPlayerID": "caleb",
                "LeaguePoints": expected_league, "CalculatedPoints": expected_calc,
                "Reference": "#698", "Reason": "Known third-party stat divergence",
            }],
        }), encoding="utf-8")

    def test_missing_exception_is_a_hard_mismatch(self):
        r = reconcile(self.root, self.model, self.matchups, require_pwf=True)
        self.assertEqual(r["State"], "mismatch")
        self.assertEqual(r["AcceptedDivergences"], 0)
        self.assertEqual(r["Records"][0]["Difference"], 0.5)
        self.assertIn("scoring mismatch", r["Errors"][0])
        with self.assertRaisesRegex(ValueError, "scoring mismatch"):
            verify_pwf_actual_parity(self.root, self.model, self.matchups)
        with self.assertRaisesRegex(ValueError, "Cannot publish unverified"):
            persist_verified(self.root, r)

    def test_exact_policy_accepts_but_retains_both_values_and_provenance(self):
        self.policy()
        r = reconcile(self.root, self.model, self.matchups, require_pwf=True)
        self.assertEqual((r["State"], r["Compared"], r["AcceptedDivergences"]),
                         ("accepted-divergence", 1, 1))
        caleb = next(x for x in r["Records"] if x["CanonicalPlayerID"] == "caleb")
        self.assertEqual((caleb["LeaguePoints"], caleb["CalculatedPoints"],
                          caleb["Difference"], caleb["Status"]),
                         (19.88, 20.38, 0.5, "accepted-divergence"))
        self.assertEqual(caleb["ExceptionReference"], "#698")
        free = next(x for x in r["Records"] if x["CanonicalPlayerID"] == "free-agent")
        self.assertEqual((free["LeaguePoints"], free["CalculatedPoints"],
                          free["Status"]), (None, 4.5, "unavailable"))
        zero = next(x for x in r["Records"] if x["CanonicalPlayerID"] == "zero")
        self.assertEqual((zero["LeaguePoints"], zero["CalculatedPoints"],
                          zero["Status"]), (0, None, "unavailable"))
        self.assertEqual(r["MissingZeroPoints"], 1)
        self.assertEqual(
            verify_pwf_actual_parity(self.root, self.model, self.matchups),
            {"State": "accepted-divergence", "Compared": 1,
             "MissingZeroPoints": 1, "AcceptedDivergences": 1},
        )
        self.assertTrue(persist_verified(self.root, r))
        self.assertFalse(persist_verified(self.root, r))
        persisted = json.loads(output_path(self.root, r).read_text(encoding="utf-8"))
        self.assertEqual(persisted, r)

    def test_policy_does_not_mask_drift_or_other_players(self):
        self.policy()
        self.write_pwf(20.39)
        r = reconcile(self.root, self.model, self.matchups)
        self.assertEqual(r["State"], "mismatch")
        self.assertIn("scoring mismatch", r["Errors"][0])
        self.assertTrue(any("Stale" in x for x in r["Errors"]))
        self.write_pwf()
        self.matchups[0]["PlayerPoints"].append(
            {"Player": {"CanonicalPlayerID": "other"}, "Points": 5.0})
        r = reconcile(self.root, self.model, self.matchups)
        self.assertEqual(r["State"], "mismatch")
        self.assertTrue(any("missing nonzero scorer" in x for x in r["Errors"]))

    def test_stale_exception_cannot_be_silently_preserved(self):
        self.policy()
        self.write_pwf(19.88)
        r = reconcile(self.root, self.model, self.matchups)
        self.assertEqual(r["State"], "mismatch")
        self.assertTrue(any("Stale" in x for x in r["Errors"]))

    def test_unavailable_pwf_never_invents_zero(self):
        self.pwf_path.unlink()
        r = reconcile(self.root, self.model, self.matchups)
        self.assertEqual(r["State"], "not-available")
        self.assertEqual(r["Compared"], 0)
        self.assertTrue(all(x["CalculatedPoints"] is None for x in r["Records"]))
        with self.assertRaisesRegex(ValueError, "Required PlayerWeekFantasy"):
            reconcile(self.root, self.model, self.matchups, require_pwf=True)
        with self.assertRaisesRegex(ValueError, "Cannot publish unverified"):
            persist_verified(self.root, r)

    def test_nonfinal_fingerprint_and_duplicate_player_fail_closed(self):
        self.policy()
        self.write_pwf(actual_state="pending")
        r = reconcile(self.root, self.model, self.matchups)
        self.assertTrue(any("not final" in x for x in r["Errors"]))
        self.write_pwf()
        self.model["ScoringProfile"]["SettingsHash"] = "sha256:other"
        with self.assertRaisesRegex(ValueError, "scoring fingerprint mismatch"):
            reconcile(self.root, self.model, self.matchups)
        self.model["ScoringProfile"]["SettingsHash"] = "sha256:test"
        self.matchups[0]["PlayerPoints"].append(self.matchups[0]["PlayerPoints"][0])
        with self.assertRaisesRegex(ValueError, "duplicate canonical matchup"):
            reconcile(self.root, self.model, self.matchups)

    def test_policy_duplicate_and_missing_reason_fail_closed(self):
        self.policy()
        policy_path = self.root / DATA_META_ROOT / "nfl-reise/scoring-divergences.json"
        data = json.loads(policy_path.read_text(encoding="utf-8"))
        data["Exceptions"].append(dict(data["Exceptions"][0]))
        policy_path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Duplicate scoring divergence"):
            reconcile(self.root, self.model, self.matchups)
        data["Exceptions"].pop()
        data["Exceptions"][0]["Reason"] = ""
        policy_path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "requires an audit reference"):
            reconcile(self.root, self.model, self.matchups)


class RealCanonicalLeagueEvidenceTest(unittest.TestCase):
    def test_2025_w06_caleb_canonical_nfl_scoring_matches_expected_exception(self):
        if not (REPO_ROOT / "data-source/nfl/player-stats/2025").exists():
            self.skipTest("Full canonical NFL source not mounted")
        from historical_fantasy_scoring_parity import build_parity_report

        audit = build_parity_report(
            REPO_ROOT, league_id="nfl-reise", nfl_season=2025,
            scoring_season=2025, first_week=6, last_week=6,
        )
        matches = [
            x for x in audit["Mismatches"]
            if x["CanonicalPlayerID"] == "NFLP-3c5ddc5072f6fe8f9b77"
        ]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["LeaguePoints"], 19.88)
        self.assertEqual(matches[0]["DerivedPoints"], 20.38)
        self.assertEqual(matches[0]["Difference"], 0.5)

    def test_2025_w06_caleb_sleeper_source_matches_exception_exactly(self):
        matchup_path = (REPO_ROOT /
                        "data-source/leagues/nfl-reise/seasons/2025/matchups/week-6.json")
        if not matchup_path.is_file():
            self.skipTest("Full canonical league source not mounted")
        source = json.loads(matchup_path.read_text(encoding="utf-8"))
        matching = [
            (team, row) for team in source for row in team["PlayerPoints"]
            if row["Player"]["CanonicalPlayerID"] == "NFLP-3c5ddc5072f6fe8f9b77"
        ]
        self.assertEqual(len(matching), 1)
        team, player = matching[0]
        self.assertEqual(player["Points"], 19.88)
        self.assertNotIn("NFLP-3c5ddc5072f6fe8f9b77",
                         [row["CanonicalPlayerID"] for row in team["Starters"]])


if __name__ == "__main__":
    unittest.main()
