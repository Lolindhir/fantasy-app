"""Synthetic fail-closed and no-op contracts for C9c.3 League full refresh witness."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from league_full_refresh_witness_audit import audit_full_witness  # noqa: E402

from league_source_refresh_witness import (  # noqa: E402
    WITNESS_ROOT, _digest, complete, prepare,
)


class LeagueRefreshWitnessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.provider = "12345"
        self.league = "test-league"
        self.season = 2026
        self.week = 1
        self.canon = self.root / f"data-source/leagues/{self.league}/seasons/{self.season}"
        self.raw = self.root / f"data-source/providers/sleeper/leagues/{self.provider}"
        self._write("data-source/nfl/game-finality/2026.json", {
            "Season": 2026,
            "Weeks": [
                {"GameType": "REG", "Week": 1, "WeekFinal": True,
                 "ApplicableGameCount": 1, "FinalGameCount": 1},
                {"GameType": "REG", "Week": 2, "WeekFinal": False,
                 "ApplicableGameCount": 1, "FinalGameCount": 0},
            ],
            "Games": [
                {"GameID": "g1", "GameType": "REG", "Week": 1, "Final": True},
                {"GameID": "g2", "GameType": "REG", "Week": 2, "Final": False},
            ],
        })
        self._write(f"data-source/leagues/{self.league}/manifest.json", {
            "CanonicalLeagueID": self.league,
            "CurrentCanonicalLeagueSeasonID": "test-league-2026",
            "CurrentProviderLeagueID": self.provider,
            "Seasons": [{"CanonicalLeagueSeasonID": "test-league-2026", "Season": 2026,
                         "ProviderMappings": [{"Provider": "Sleeper", "ProviderLeagueID": self.provider}]}],
        })
        self._write(f"data-source/leagues/{self.league}/seasons/2026/league.json", {
            "WeekStructure": {"StartWeek": 1, "ExpectedLastLeagueWeek": 2, "LastScoredLeg": 1},
        })
        for name in ("members.json", "rosters.json", "winners-bracket.json", "losers-bracket.json",
                     "matchups/week-1.json", "transactions/week-1.json"):
            self._write(f"data-source/leagues/{self.league}/seasons/2026/{name}", [])
        datasets = {
            "league": ("league.json", {}),
            "league-members": ("members.json", []),
            "league-rosters": ("rosters.json", []),
            "matchups": ("matchups/week-1.json", []),
            "transactions": ("transactions/week-1.json", []),
        }
        for suffix, (path, payload) in datasets.items():
            self._write(f"data-source/providers/sleeper/leagues/{self.provider}/{path}", payload)
            p = Path(path)
            self._write(
                f"data-source/providers/sleeper/leagues/{self.provider}/{p.parent}/{p.stem}.metadata.json",
                {"Dataset": f"sleeper.{suffix}", "Provider": "Sleeper",
                 "ProviderLeagueID": self.provider, "Season": 2026,
                 "Week": 1 if suffix in ("matchups", "transactions") else None,
                 "ContentSha256": _digest(payload)},
            )
        self.raw_result = {"Leagues": [{"CanonicalLeagueID": self.league, "DatasetPartitions": 12}]}
        self.canonical_result = {"Leagues": [{"CanonicalLeagueID": self.league,
                                              "MaterializationScope": "full", "CanonicalFiles": 10}]}
        self.at = datetime(2026, 11, 2, 7, tzinfo=timezone.utc)

    def _write(self, path, payload):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    def _witness(self):
        return self.root / WITNESS_ROOT / self.league / "2026-week-01.json"

    def _commit_audit_fixture(self, *, complete_witness=True):
        if complete_witness:
            preflight = prepare(self.root)
            complete(self.root, preflight, self.raw_result, self.canonical_result,
                     completed_at=self.at)
        commands = [
            ("init", "-q"),
            ("config", "user.email", "test@example.com"),
            ("config", "user.name", "Fixture"),
            ("add", "-A"),
            ("commit", "-qm", "test: immutable source fixture"),
        ]
        for args in commands:
            subprocess.run(["git", *args], cwd=self.root, check=True,
                           capture_output=True, text=True)

    def _audit_full(self, *, age_hours=2, at=None):
        result = audit_full_witness(
            self.root, self.league, observed_at=at or datetime(
                2026, 11, 2, 9, tzinfo=timezone.utc
            ), max_age_hours=age_hours,
        )
        self.assertIs(result["safeToSkip"], False)
        self.assertIs(result["enforced"], False)
        self.assertIs(result["currentScopeNoOpVerified"], False)
        self.assertIs(result["lastSuccessfulRunVerified"], False)
        self.assertIs(result["providerFreshnessVerified"], False)
        self.assertIs(result["timeAndFinalityVerified"], False)
        return result

    def test_offline_full_week_witness_pinned_to_clean_commit(self):
        self._commit_audit_fixture()
        r = self._audit_full()
        self.assertEqual("historical-full-week-content-confirmed", r["status"])
        self.assertTrue(r["sourceWitnessVerified"])
        self.assertTrue(r["contentRevisionVerified"])
        self.assertTrue(r["observedAgeBoundVerified"])
        self.assertEqual(1, r["finalizedWeek"])
        self.assertEqual(2026, r["season"])
        self.assertEqual(40, len(r["observedCommitSha"]))
        self.assertEqual(18, r["coveredInputCount"])
        self.assertEqual([], r["reasonCodes"])

    def test_offline_witness_missing_or_wrong_identity_fails_closed(self):
        self._commit_audit_fixture(complete_witness=False)
        self.assertFalse(self._audit_full()["sourceWitnessVerified"])
        r = audit_full_witness(
            self.root, "other-league", observed_at=datetime(
                2026, 11, 2, 9, tzinfo=timezone.utc
            ),
        )
        self.assertFalse(r["sourceWitnessVerified"])
        self.assertFalse(r["safeToSkip"])

    def test_offline_witness_dirty_or_untracked_root_fails_closed(self):
        self._commit_audit_fixture()
        self._write("untracked.json", {"untrusted": True})
        self.assertIn("clean Git revision", self._audit_full()["reasonCodes"][0])
        (self.root / "untracked.json").unlink()
        self._write(f"data-source/leagues/{self.league}/seasons/2026/rosters.json",
                    [{"different": True}])
        self.assertFalse(self._audit_full()["sourceWitnessVerified"])

    def test_offline_witness_canonical_raw_or_finality_change_after_commit(self):
        for kind in ("canonical", "raw-metadata", "finality"):
            with self.subTest(kind=kind):
                # Each subtest uses its own test fixture root because setUp is
                # called only once; save/restore the bytes and commit changes.
                if kind == "canonical":
                    path = self.canon / "rosters.json"
                    original = path.read_bytes()
                    path.write_text('[{"changed":true}]', encoding="utf-8")
                elif kind == "raw-metadata":
                    path = self.raw / "rosters.metadata.json"
                    original = path.read_bytes()
                    data = json.loads(original)
                    data["ContentSha256"] = "0" * 64
                    path.write_text(json.dumps(data), encoding="utf-8")
                else:
                    path = self.root / "data-source/nfl/game-finality/2026.json"
                    original = path.read_bytes()
                    data = json.loads(original)
                    data["Games"][0]["GameID"] = "other-game"
                    path.write_text(json.dumps(data), encoding="utf-8")
                if not (self.root / ".git").exists():
                    self._commit_audit_fixture(complete_witness=False)
                subprocess.run(["git", "add", "-A"], cwd=self.root, check=True)
                subprocess.run(["git", "commit", "-qm", kind], cwd=self.root,
                               check=True)
                self.assertFalse(self._audit_full()["sourceWitnessVerified"])
                path.write_bytes(original)
                subprocess.run(["git", "add", "-A"], cwd=self.root, check=True)
                subprocess.run(["git", "commit", "-qm", "restore"], cwd=self.root,
                               check=True)

    def test_offline_witness_tampered_scope_input_fingerprint_and_future_clock(self):
        self._commit_audit_fixture()
        path = self._witness()
        original = json.loads(path.read_text(encoding="utf-8"))
        for key, value in (
            ("Scope", "current"),
            ("InputsFingerprint", "0" * 64),
            ("Inputs", []),
            ("SucceededAtUtc", "2030-01-01T00:00:00Z"),
        ):
            with self.subTest(key=key):
                data = {**original, key: value}
                path.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")
                subprocess.run(["git", "add", "-A"], cwd=self.root, check=True)
                subprocess.run(["git", "commit", "-qm", "tamper"], cwd=self.root,
                               check=True)
                self.assertFalse(self._audit_full()["sourceWitnessVerified"])
                path.write_text(json.dumps(original, sort_keys=True), encoding="utf-8")
                subprocess.run(["git", "add", "-A"], cwd=self.root, check=True)
                subprocess.run(["git", "commit", "-qm", "restore"], cwd=self.root,
                               check=True)

    def test_offline_witness_expired_age_and_invalid_clock(self):
        self._commit_audit_fixture()
        self.assertFalse(self._audit_full(age_hours=0.5)["sourceWitnessVerified"])
        self.assertFalse(self._audit_full(age_hours=0)["sourceWitnessVerified"])
        self.assertFalse(audit_full_witness(
            self.root, self.league,
            observed_at=datetime(2026, 11, 2, 9),
        )["sourceWitnessVerified"])

    def test_full_after_prior_finality_writes_once_and_noops(self):
        before = prepare(self.root)
        self.assertEqual([1], [x["Week"] for x in before["candidates"]])
        self.assertEqual({"candidates": 1, "changed": 1},
                         complete(self.root, before, self.raw_result, self.canonical_result,
                                  completed_at=self.at))
        payload = json.loads(self._witness().read_text(encoding="utf-8"))
        self.assertEqual("full", payload["Scope"])
        self.assertEqual("2026-11-02T07:00:00Z", payload["SucceededAtUtc"])
        original = self._witness().read_bytes()
        later = datetime(2026, 11, 3, tzinfo=timezone.utc)
        self.assertEqual({"candidates": 1, "changed": 0},
                         complete(self.root, before, self.raw_result, self.canonical_result,
                                  completed_at=later))
        self.assertEqual(original, self._witness().read_bytes())

    def test_changed_canonical_source_generates_new_proof(self):
        before = prepare(self.root)
        complete(self.root, before, self.raw_result, self.canonical_result, completed_at=self.at)
        old = json.loads(self._witness().read_text(encoding="utf-8"))
        self._write(f"data-source/leagues/{self.league}/seasons/2026/rosters.json", [{"id": 1}])
        complete(self.root, before, self.raw_result, self.canonical_result,
                 completed_at=datetime(2026, 11, 3, tzinfo=timezone.utc))
        new = json.loads(self._witness().read_text(encoding="utf-8"))
        self.assertNotEqual(old["InputsFingerprint"], new["InputsFingerprint"])
        self.assertNotEqual(old["SucceededAtUtc"], new["SucceededAtUtc"])

    def test_current_scope_or_partial_failure_cannot_publish(self):
        before = prepare(self.root)
        for raw, canonical in [
            ({"Leagues": [{**self.raw_result["Leagues"][0], "DatasetPartitions": 0}]},
             self.canonical_result),
            (self.raw_result, {"Leagues": [{**self.canonical_result["Leagues"][0],
                                           "MaterializationScope": "current"}]}),
        ]:
            with self.assertRaisesRegex(ValueError, "full League"):
                complete(self.root, before, raw, canonical, completed_at=self.at)
        self.assertFalse(self._witness().exists())

    def test_missing_or_forged_raw_metadata_fails_closed(self):
        before = prepare(self.root)
        metadata = self.raw / "matchups/week-1.metadata.json"
        payload = json.loads(metadata.read_text(encoding="utf-8"))
        payload["ContentSha256"] = "0" * 64
        self._write(str(metadata.relative_to(self.root)), payload)
        with self.assertRaisesRegex(ValueError, "metadata"):
            complete(self.root, before, self.raw_result, self.canonical_result,
                     completed_at=self.at)
        self.assertFalse(self._witness().exists())

    def test_failed_first_witness_cleanup_does_not_restore_untracked_prefix(self):
        workflow = (TOOLS.parent / ".github/workflows/sync-league-source-data.yml").read_text(
            encoding="utf-8"
        )
        guard = re.search(
            r"# On the first failed witness attempt.*?git clean -fd -- "
            r"data-source/_sync/league-refresh-witnesses",
            workflow, flags=re.DOTALL,
        )
        self.assertIsNotNone(guard, "Production witness-cleanup script must remain covered")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            untracked = root / WITNESS_ROOT / "test-league" / "2026-week-01.json"
            untracked.parent.mkdir(parents=True)
            untracked.write_text('{"partial": true}', encoding="utf-8")
            subprocess.run(
                ["bash", "-e", "-c", guard.group(0)], cwd=root,
                check=True, capture_output=True, text=True,
            )
            self.assertFalse(untracked.exists(), "Failed witness candidate must be cleaned")

    def test_new_finality_during_run_denies_witness(self):
        before = prepare(self.root)
        league_path = f"data-source/leagues/{self.league}/seasons/2026/league.json"
        self._write(league_path, {
            "WeekStructure": {"StartWeek": 1, "ExpectedLastLeagueWeek": 2, "LastScoredLeg": 2},
        })
        finality = self.root / "data-source/nfl/game-finality/2026.json"
        data = json.loads(finality.read_text(encoding="utf-8"))
        data["Weeks"][1]["WeekFinal"] = True
        data["Weeks"][1]["FinalGameCount"] = 1
        data["Games"][1]["Final"] = True
        self._write(str(finality.relative_to(self.root)), data)
        with self.assertRaisesRegex(ValueError, "changed during full acquisition"):
            complete(self.root, before, self.raw_result, self.canonical_result,
                     completed_at=self.at)
        self.assertFalse(self._witness().exists())

    def test_no_final_week_yields_no_writes(self):
        self._write(f"data-source/leagues/{self.league}/seasons/2026/league.json", {
            "WeekStructure": {"StartWeek": 1, "ExpectedLastLeagueWeek": 2, "LastScoredLeg": 0},
        })
        p = prepare(self.root)
        self.assertEqual([], p["candidates"])
        self.assertEqual({"candidates": 0, "changed": 0},
                         complete(self.root, p, self.raw_result, self.canonical_result,
                                  completed_at=self.at))
        self.assertFalse(self._witness().exists())


if __name__ == "__main__":
    unittest.main()
