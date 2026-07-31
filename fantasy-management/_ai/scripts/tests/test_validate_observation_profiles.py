from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIRECTORY = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIRECTORY))

from validate_automation import Report  # noqa: E402
from validate_observation_profiles import (  # noqa: E402
    validate_observation_profiles,
    validate_profile_source_bindings,
)


def base_profile() -> dict:
    return {
        "signals": [
            {
                "id": "market.rank",
                "source_types": ["external_ranking"],
            },
            {
                "id": "evidence.confidence",
                "source_types": ["derived"],
            },
        ],
        "source_bindings": [
            {
                "id": "ranking",
                "source_type": "external_ranking",
                "role": "primary",
                "access": {
                    "type": "repo_file",
                    "location": "source.json",
                },
                "entity_join": ["sleeper_id"],
                "signal_mappings": {
                    "market.rank": "Rank",
                },
            },
            {
                "id": "derived",
                "source_type": "derived",
                "role": "derived",
                "access": {
                    "type": "derived",
                    "location": None,
                },
                "entity_join": [],
                "signal_mappings": {
                    "evidence.confidence": "derived",
                },
            },
        ],
    }


class ObservationProfileValidatorTests(unittest.TestCase):
    def test_repository_observation_profiles_are_valid(self) -> None:
        root = Path(__file__).resolve().parents[4]
        report = validate_observation_profiles(root)
        self.assertEqual([], report.errors, report.to_json())

    def test_unknown_signal_mapping_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "source.json").write_text("{}", encoding="utf-8")
            profile = base_profile()
            profile["source_bindings"][0]["signal_mappings"] = {
                "market.missing": "Rank"
            }
            report = Report()
            validate_profile_source_bindings(
                Path("profile.json"),
                profile,
                root,
                report,
            )
            self.assertTrue(
                any("unknown signal" in issue.message for issue in report.errors),
                report.to_json(),
            )

    def test_duplicate_primary_binding_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "source.json").write_text("{}", encoding="utf-8")
            profile = base_profile()
            duplicate = dict(profile["source_bindings"][0])
            duplicate["id"] = "ranking-copy"
            duplicate["signal_mappings"] = {"market.rank": "Rank"}
            profile["source_bindings"].append(duplicate)
            report = Report()
            validate_profile_source_bindings(
                Path("profile.json"),
                profile,
                root,
                report,
            )
            self.assertTrue(
                any("exactly one primary binding" in issue.message for issue in report.errors),
                report.to_json(),
            )

    def test_disjoint_conditional_primary_bindings_are_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "source.json").write_text("{}", encoding="utf-8")
            profile = base_profile()
            primary = profile["source_bindings"][0]
            primary["format_context"] = {
                "primary_for_positions": "RB,WR,TE",
            }
            duplicate = dict(primary)
            duplicate["id"] = "ranking-qb"
            duplicate["format_context"] = {
                "primary_for_positions": "QB",
            }
            duplicate["signal_mappings"] = {"market.rank": "Rank"}
            profile["source_bindings"].append(duplicate)
            report = Report()
            validate_profile_source_bindings(
                Path("profile.json"),
                profile,
                root,
                report,
            )
            self.assertFalse(
                any("exactly one primary binding" in issue.message for issue in report.errors),
                report.to_json(),
            )

    def test_overlapping_conditional_primary_bindings_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "source.json").write_text("{}", encoding="utf-8")
            profile = base_profile()
            primary = profile["source_bindings"][0]
            primary["format_context"] = {
                "primary_for_positions": "QB,RB",
            }
            duplicate = dict(primary)
            duplicate["id"] = "ranking-overlap"
            duplicate["format_context"] = {
                "primary_for_positions": "RB,WR",
            }
            duplicate["signal_mappings"] = {"market.rank": "Rank"}
            profile["source_bindings"].append(duplicate)
            report = Report()
            validate_profile_source_bindings(
                Path("profile.json"),
                profile,
                root,
                report,
            )
            self.assertTrue(
                any("exactly one primary binding" in issue.message for issue in report.errors),
                report.to_json(),
            )

    def test_missing_repository_location_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profile = base_profile()
            report = Report()
            validate_profile_source_bindings(
                Path("profile.json"),
                profile,
                root,
                report,
            )
            self.assertTrue(
                any("missing repository source" in issue.message for issue in report.errors),
                report.to_json(),
            )


if __name__ == "__main__":
    unittest.main()
