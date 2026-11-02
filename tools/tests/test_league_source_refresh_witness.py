"""Synthetic fail-closed and no-op contracts for C9c.3 League full refresh witness."""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

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
