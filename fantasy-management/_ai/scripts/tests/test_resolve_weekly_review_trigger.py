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
                self.assertFalse(result["freshness_gate_evaluated"])
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


if __name__ == "__main__":
    unittest.main()
