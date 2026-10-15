"""Temporary read-only Week 3 PWF rebuild/export gate. Do not merge this audit test.

Runs exact productive materializer, verifies scoring, checks independent projections
unchanged, prints serialized bytes split into JSON-escaped chunks for a data-only PR.
It never writes to the repository.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from data_roots import DATA_SOURCE_ROOT, DATA_DERIVED_ROOT  # noqa: E402
from player_week_fantasy_materialize import build_player_week_fantasy_dataset  # noqa: E402

LEAGUE = "nfl-reise"
SEASON = 2026
WEEK = 3


class Week3ExactExportAudit(unittest.TestCase):
    def test_rebuild_w03_verify_only_actual_changes_and_export(self) -> None:
        path = ROOT / DATA_DERIVED_ROOT / "player-week-fantasy" / LEAGUE / str(SEASON) / f"{WEEK:02d}.json"
        existing = json.loads(path.read_text(encoding="utf-8"))
        produced = build_player_week_fantasy_dataset(
            ROOT, league_id=LEAGUE, season=SEASON, week=WEEK
        )
        self.assertEqual(existing["ScoringProfile"], produced["ScoringProfile"])
        # Old W03 predates the additive multi-interval contract; preserve all old fields.
        legacy_model = {key: value for key, value in produced["ProjectionModel"].items()
                        if key != "IntervalLevels"}
        self.assertEqual(existing["ProjectionModel"], legacy_model)
        self.assertEqual(produced["ProjectionModel"]["IntervalLevels"], [0.5, 0.8, 0.9])
        old_records = {row["CanonicalPlayerID"]: row for row in existing["Records"]}
        new_records = {row["CanonicalPlayerID"]: row for row in produced["Records"]}
        self.assertEqual(old_records.keys(), new_records.keys())
        projection_changed = [
            pid for pid, rec in new_records.items()
            if {k: v for k, v in rec["Projection"].items() if k != "PredictionRanges"}
            != old_records[pid]["Projection"]
        ]
        self.assertEqual(projection_changed, [],
                         f"Unexpected existing projection metric drift, first: {projection_changed[:5]}")
        multirange_added = sum(
            "PredictionRanges" in rec["Projection"]
            and "PredictionRanges" not in old_records[pid]["Projection"]
            for pid, rec in new_records.items()
        )
        for rec in new_records.values():
            p = rec["Projection"]
            if "PredictionRanges" in p:
                self.assertEqual([v["Level"] for v in p["PredictionRanges"]],
                                 [0.5, 0.8, 0.9])
                self.assertIn(p["PredictionRange"], p["PredictionRanges"])
        owned = json.loads(
            (ROOT / DATA_SOURCE_ROOT / "leagues" / LEAGUE / "seasons" / str(SEASON)
             / "matchups" / f"week-{WEEK}.json").read_text(encoding="utf-8")
        )
        compared = 0
        missing_zero = 0
        seen: set[str] = set()
        for team in owned:
            for value in team["PlayerPoints"]:
                pid = value["Player"]["CanonicalPlayerID"]
                self.assertNotIn(pid, seen)
                seen.add(pid)
                row = new_records.get(pid)
                actual = float(value["Points"])
                if row is None:
                    self.assertEqual(actual, 0, f"Absent nonzero fantasy scorer: {pid}")
                    missing_zero += 1
                    continue
                self.assertEqual(row["Actual"]["State"], "final", pid)
                self.assertTrue(math.isfinite(float(row["Actual"]["Points"])))
                self.assertLessEqual(abs(float(row["Actual"]["Points"]) - actual), 0.010001, pid)
                compared += 1
        self.assertTrue(produced["Materialization"]["ActualScoringEvidenceFinalized"])
        self.assertEqual(produced["Materialization"]["ActualStateCounts"], {"final": 820})
        self.assertEqual(existing["Materialization"]["ActualStateCounts"], {"unavailable": 820})
        self.assertEqual(len(produced["Records"]), 820)
        self.assertEqual(compared + missing_zero, 202)
        # No third, hidden mutated contract section.
        self.assertEqual(existing.keys(), produced.keys())
        for key in existing:
            if key not in {"Records", "Materialization"}:
                self.assertEqual(existing[key], produced[key], f"Top-level drift: {key}")
        old_meta = dict(existing["Materialization"])
        new_meta = dict(produced["Materialization"])
        for key in {"ActualStateCounts", "ActualScoringEvidenceFinalized"}:
            old_meta.pop(key)
            new_meta.pop(key)
        self.assertEqual(old_meta, new_meta)
        payload = (json.dumps(produced, indent=2, ensure_ascii=False,
                              sort_keys=True) + "\n")
        encoded = payload.encode("utf-8")
        object_id = hashlib.sha1(f"blob {len(encoded)}\0".encode("ascii") + encoded).hexdigest()
        report = {
            "RecordCount": 820, "FantasyMatchupCompared": compared,
            "MissingZero": missing_zero,
            "ExistingProjectionsChanged": len(projection_changed),
            "MultiRangeEnrichedRecords": multirange_added,
            "OldActualState": existing["Materialization"]["ActualStateCounts"],
            "NewActualState": produced["Materialization"]["ActualStateCounts"],
            "ActualChangedRows": sum(old_records[pid]["Actual"] != rec["Actual"]
                                     for pid, rec in new_records.items()),
            "GitBlobSha": object_id, "UTF8Bytes": len(encoded),
        }
        print("PWF_W03_EXPORT_REPORT=" + json.dumps(report, sort_keys=True), flush=True)
        # JSON string escaping yields source bytes exactly when concatenated.
        # Chunks are intentionally short enough not to be truncated by job logs.
        for index, start in enumerate(range(0, len(payload), 2500)):
            chunk = payload[start:start + 2500]
            print(f"PWF_W03_EXPORT_CHUNK_{index:04d}=" +
                  json.dumps(chunk, ensure_ascii=True), flush=True)


if __name__ == "__main__":
    unittest.main()
