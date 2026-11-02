from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import jsonschema

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import resolve_weekly_review_trigger as weekly  # noqa: E402


class WeeklyReviewTriggerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.trigger = {
            "type": "league_week_finalized",
            "source_type": "canonical_lifecycle",
            "canonical_league_id": "test",
            "final_week_field": "FinalScoredWeek",
            "minimum_data_age_minutes": 60,
            "retry_when_not_ready": True,
        }

    def manifest(self, root: Path) -> None:
        path = root / "data-source/leagues/test/manifest.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "CanonicalLeagueID": "test",
            "CurrentCanonicalLeagueSeasonID": "test-2026",
            "Seasons": [{"CanonicalLeagueSeasonID": "test-2026", "Season": 2026}],
        }) + "\n", encoding="utf-8")

    def mock_lifecycle(self, final_week: object, season: int = 2026) -> dict:
        return {
            "CanonicalLeagueID": "test",
            "Season": season,
            "FinalScoredWeek": final_week,
        }

    def test_advancement_uses_canonical_lifecycle_at_explicit_instant(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.manifest(root)
            with mock.patch.object(weekly, "resolve_lifecycle_state", return_value=self.mock_lifecycle(7)) as resolver:
                result = weekly.resolve_trigger(root, self.trigger, at_utc="2026-11-01T20:00:00Z",
                                                last_processed_key="2026-week-6")
                self.assertEqual(result["final_scored_week"], 7)
                self.assertEqual(result["candidate_key"], "2026-week-7")
                self.assertTrue(result["advanced_beyond_last_processed"])
                self.assertTrue(result["freshness_gate_evaluated"])
                self.assertEqual(result["source_refresh_gate_state"], "blocked")
                self.assertTrue(result["source_refresh_gate_reason"].startswith("source_refresh_"))
                self.assertFalse(result["job_activation_or_write_authorized"])
                resolver.assert_called_once()
                self.assertEqual(resolver.call_args.args[1:3], ("test", 2026))
                self.assertEqual(resolver.call_args.args[3].isoformat(), "2026-11-01T20:00:00+00:00")
                self.assertFalse(weekly.resolve_trigger(
                    root, self.trigger, at_utc="2026-11-01T20:00:00Z",
                    last_processed_key="2026-week-7"
                )["advanced_beyond_last_processed"])

    def test_zero_and_previous_season_are_handled_without_false_week_zero_event(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.manifest(root)
            with mock.patch.object(weekly, "resolve_lifecycle_state", return_value=self.mock_lifecycle(0)):
                data = weekly.resolve_trigger(root, self.trigger, at_utc="2026-09-01T12:00:00+00:00")
                self.assertFalse(data["advanced_beyond_last_processed"])
                self.assertIsNone(data["candidate_key"])
                self.assertFalse(data["freshness_gate_evaluated"])
                self.assertEqual(data["source_refresh_gate_state"], "not_applicable")
            with mock.patch.object(weekly, "resolve_lifecycle_state", return_value=self.mock_lifecycle(1)):
                data = weekly.resolve_trigger(root, self.trigger, at_utc="2026-09-01T12:00:00+00:00",
                                              last_processed_key="2025-week-17")
                self.assertTrue(data["advanced_beyond_last_processed"])

    def test_invalid_config_state_and_unavailable_evidence_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.manifest(root)
            with mock.patch.object(weekly, "resolve_lifecycle_state", return_value=self.mock_lifecycle(7)):
                for changes in (
                    {"source_type": "app_league"},
                    {"league_source": "public/data/League.json"},
                    {"final_week_field": "CurrentWeek"},
                    {"canonical_league_id": "../escape"},
                    {"minimum_data_age_minutes": -1},
                    {"retry_when_not_ready": False},
                ):
                    with self.subTest(changes=changes), self.assertRaises(weekly.WeeklyReviewTriggerUnavailable):
                        weekly.resolve_trigger(root, {**self.trigger, **changes}, at_utc="2026-11-01T20:00:00Z")
                for last in ("wrong", "2026-week-99", "2027-week-1"):
                    with self.subTest(last=last), self.assertRaises(weekly.WeeklyReviewTriggerUnavailable):
                        weekly.resolve_trigger(root, self.trigger, at_utc="2026-11-01T20:00:00Z",
                                               last_processed_key=last)
                with self.assertRaisesRegex(weekly.WeeklyReviewTriggerUnavailable, "timezone-aware"):
                    weekly.resolve_trigger(root, self.trigger, at_utc="2026-11-01T20:00:00")
            with mock.patch.object(weekly, "resolve_lifecycle_state", return_value=self.mock_lifecycle(7, 2025)):
                with self.assertRaisesRegex(weekly.WeeklyReviewTriggerUnavailable, "identity mismatch"):
                    weekly.resolve_trigger(root, self.trigger, at_utc="2026-11-01T20:00:00Z")
            with mock.patch.object(weekly, "resolve_lifecycle_state", return_value=self.mock_lifecycle(True)):
                with self.assertRaisesRegex(weekly.WeeklyReviewTriggerUnavailable, "invalid"):
                    weekly.resolve_trigger(root, self.trigger, at_utc="2026-11-01T20:00:00Z")
            with mock.patch.object(weekly, "resolve_lifecycle_state",
                                   side_effect=weekly.LeagueLifecycleUnavailable("missing game finality")):
                with self.assertRaisesRegex(weekly.WeeklyReviewTriggerUnavailable, "missing game finality"):
                    weekly.resolve_trigger(root, self.trigger, at_utc="2026-11-01T20:00:00Z")
            (root / "data-source/leagues/test/manifest.json").unlink()
            with self.assertRaises(weekly.WeeklyReviewTriggerUnavailable):
                weekly.resolve_trigger(root, self.trigger, at_utc="2026-11-01T20:00:00Z")


    def test_full_witness_readiness_requires_60_min_verified_source_evidence(self) -> None:
        candidate = {
            "CanonicalLeagueID": "test",
            "CanonicalLeagueSeasonID": "test-2026",
            "ProviderLeagueID": "12345",
            "Season": 2026,
            "Week": 7,
            "FinalityFingerprint": "finalized-week-fingerprint",
        }
        inputs = [
            {"path": "data-source/leagues/test/seasons/2026/league.json", "sha256": "a" * 64},
            {"path": "data-source/providers/sleeper/leagues/12345/matchups/week-7.json", "sha256": "b" * 64},
        ]
        path_rel = "data-source/_sync/league-refresh-witnesses/test/2026-week-07.json"
        witness = {
            "schemaVersion": 1,
            **candidate,
            "Scope": "full",
            "SucceededAtUtc": "2026-11-02T10:00:00Z",
            "Inputs": inputs,
            "InputsFingerprint": weekly._digest({"identity": candidate, "inputs": inputs}),
        }
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.manifest(root)
            path = root / path_rel
            path.parent.mkdir(parents=True)
            def put(value):
                path.write_text(json.dumps(value), encoding="utf-8")
            put(witness)
            with (
                mock.patch.object(weekly, "resolve_lifecycle_state", return_value=self.mock_lifecycle(7)),
                mock.patch.object(weekly, "_current_candidates", return_value=[candidate]),
                mock.patch.object(weekly, "_inputs", return_value=inputs),
            ):
                def check(instant: str) -> dict:
                    result = weekly.resolve_trigger(
                        root, self.trigger, at_utc=instant, last_processed_key="2026-week-6"
                    )
                    self.assertTrue(result["advanced_beyond_last_processed"])
                    self.assertTrue(result["freshness_gate_evaluated"])
                    self.assertFalse(result["job_activation_or_write_authorized"])
                    return result

                waiting = check("2026-11-02T10:59:59Z")
                self.assertEqual(waiting["source_refresh_gate_reason"], "source_refresh_minimum_age_not_met")
                self.assertEqual(check("2026-11-02T09:00:00Z")["source_refresh_gate_reason"],
                                 "source_refresh_from_future")
                ready = check("2026-11-02T11:00:00Z")
                self.assertEqual(ready["source_refresh_gate_state"], "ready")
                self.assertEqual(ready["source_refresh_gate_reason"], "validated_full_refresh_after_finality")
                self.assertEqual(ready["source_refresh_succeeded_at_utc"], "2026-11-02T10:00:00+00:00")
                self.assertTrue(check("2026-11-03T12:00:00Z")["source_refresh_gate_state"] == "ready")

                bad = [
                    ("Scope", "current", "source_refresh_identity_or_finality_mismatch"),
                    ("Week", 6, "source_refresh_identity_or_finality_mismatch"),
                    ("Season", 2025, "source_refresh_identity_or_finality_mismatch"),
                    ("ProviderLeagueID", "9999", "source_refresh_identity_or_finality_mismatch"),
                    ("CanonicalLeagueSeasonID", "test-2025", "source_refresh_identity_or_finality_mismatch"),
                    ("FinalityFingerprint", "stale", "source_refresh_identity_or_finality_mismatch"),
                    ("InputsFingerprint", "0" * 64, "source_refresh_inputs_changed"),
                    ("Inputs", [], "source_refresh_inputs_changed"),
                    ("SucceededAtUtc", "not-a-date", "source_refresh_witness_unverifiable:WeeklyReviewTriggerUnavailable"),
                ]
                for field, value, reason in bad:
                    with self.subTest(field=field):
                        put({**witness, field: value})
                        result = check("2026-11-02T12:00:00Z")
                        self.assertEqual(result["source_refresh_gate_state"], "blocked")
                        self.assertEqual(result["source_refresh_gate_reason"], reason)
                put(witness)
                with mock.patch.object(weekly, "_inputs", side_effect=ValueError("forged metadata")):
                    self.assertEqual(
                        check("2026-11-02T12:00:00Z")["source_refresh_gate_reason"],
                        "source_refresh_witness_unverifiable:ValueError",
                    )
                with mock.patch.object(weekly, "_current_candidates", return_value=[{**candidate, "Week": 8}]):
                    self.assertEqual(
                        check("2026-11-02T12:00:00Z")["source_refresh_gate_reason"],
                        "canonical_finality_or_season_mismatch",
                    )
                path.unlink()
                self.assertEqual(
                    check("2026-11-02T12:00:00Z")["source_refresh_gate_reason"],
                    "source_refresh_witness_missing",
                )

    def test_repository_job_schema_and_canonical_parity(self) -> None:
        root = SCRIPTS.parents[2]
        job = json.loads((root / "fantasy-management/automation/jobs/weekly-league-review.json").read_text(encoding="utf-8"))
        schema = json.loads((root / "fantasy-management/_ai/schemas/automation-job.schema.json").read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(schema).validate(job)
        self.assertFalse(job["enabled"])
        self.assertEqual(job["trigger"]["minimum_data_age_minutes"], 60)
        self.assertEqual(job["execution"]["write_scope"], [
            "fantasy-management/analyses/{season}/weekly-reviews/",
            "fantasy-management/automation/state/weekly-league-review.json",
        ])
        self.assertNotIn("public/data/League.json", json.dumps(job))
        old = {**job, "trigger": {
            "type": "league_week_finalized",
            "league_source": "public/data/League.json",
            "final_week_field": "FinalScoredWeek",
            "minimum_data_age_minutes": 60,
            "retry_when_not_ready": True,
        }}
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(schema).validate(old)

        observed_at = json.loads((root / "fantasy-management/generated/operations/managed-roster-signals.json")
                                 .read_text(encoding="utf-8"))["generated_at"]
        result = weekly.resolve_trigger(root, job["trigger"], at_utc=observed_at)
        published_app_week = json.loads((root / "public/data/League.json").read_text(encoding="utf-8"))["FinalScoredWeek"]
        self.assertEqual(result["final_scored_week"], published_app_week,
                         "Canonical lifecycle and current published App FinalScoredWeek must agree.")
        self.assertTrue(result["advanced_beyond_last_processed"] if published_app_week > 0 else not result["advanced_beyond_last_processed"])
        self.assertIn(result["source_refresh_gate_state"], {"ready", "blocked", "not_applicable"})
        self.assertFalse(result["job_activation_or_write_authorized"])
        self.assertNotIn("public/data/Timestamps.json", json.dumps(job))


if __name__ == "__main__":
    unittest.main()
