from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPT_DIRECTORY = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIRECTORY))

from validate_automation import (  # noqa: E402
    Report,
    entity_fingerprint,
    validate_automation,
    validate_observation_state_targets,
    validate_target_sets,
)


class AutomationValidatorTests(unittest.TestCase):
    def test_repository_automation_configuration_is_valid(self) -> None:
        root = Path(__file__).resolve().parents[4]
        report = validate_automation(root)
        self.assertEqual([], report.errors, report.to_json())

    def test_entity_fingerprint_prefers_sleeper_id(self) -> None:
        entity = {
            "type": "player",
            "display_name": "Example Player",
            "identifiers": {
                "nfl_team": "PHI",
                "sleeper_id": "9225",
            },
        }
        self.assertEqual(
            "player:sleeper_id:9225",
            entity_fingerprint(entity),
        )

    def test_conflicting_target_id_is_rejected(self) -> None:
        profile = {
            "applicable_entity_types": ["player"],
        }
        profiles = {
            "role-opportunity": (Path("role-opportunity.json"), profile),
        }
        defaults = {
            "profile_bindings": [
                {
                    "profile_ref": "role-opportunity",
                    "enabled": True,
                }
            ]
        }
        first = {
            "defaults": defaults,
            "manual_targets": [
                {
                    "id": "same-target",
                    "entity": {
                        "type": "player",
                        "identifiers": {"sleeper_id": "1"},
                    },
                    "profile_bindings": [],
                }
            ],
            "selectors": [],
        }
        second = {
            "defaults": defaults,
            "manual_targets": [
                {
                    "id": "same-target",
                    "entity": {
                        "type": "player",
                        "identifiers": {"sleeper_id": "2"},
                    },
                    "profile_bindings": [],
                }
            ],
            "selectors": [],
        }
        report = Report()
        validate_target_sets(
            {
                "first": (Path("first.json"), first),
                "second": (Path("second.json"), second),
            },
            profiles,
            report,
        )
        self.assertTrue(
            any("resolves to both" in issue.message for issue in report.errors),
            report.to_json(),
        )

    def test_unknown_profile_reference_is_rejected(self) -> None:
        target_set = {
            "defaults": {
                "profile_bindings": [
                    {
                        "profile_ref": "missing-profile",
                        "enabled": True,
                    }
                ]
            },
            "manual_targets": [
                {
                    "id": "target",
                    "entity": {
                        "type": "player",
                        "identifiers": {"sleeper_id": "1"},
                    },
                    "profile_bindings": [],
                }
            ],
            "selectors": [],
        }
        report = Report()
        validate_target_sets(
            {"targets": (Path("targets.json"), target_set)},
            {},
            report,
        )
        self.assertTrue(
            any("unknown profile" in issue.message for issue in report.errors),
            report.to_json(),
        )

    def test_selector_profile_applicability_is_validated(self) -> None:
        target_set = {
            "enabled": True,
            "defaults": {"profile_bindings": []},
            "manual_targets": [],
            "selectors": [
                {
                    "id": "players",
                    "enabled": True,
                    "entity_type": "player",
                    "profile_bindings": [
                        {
                            "profile_ref": "team-profile",
                            "enabled": True,
                        }
                    ],
                }
            ],
        }
        profiles = {
            "team-profile": (
                Path("team-profile.json"),
                {"applicable_entity_types": ["fantasy_team"]},
            )
        }
        report = Report()
        validate_target_sets(
            {"managed-roster": (Path("managed-roster.json"), target_set)},
            profiles,
            report,
        )
        self.assertTrue(
            any("does not support entity type" in issue.message for issue in report.errors),
            report.to_json(),
        )

    def test_dynamic_state_target_is_accepted_by_selector_contract(self) -> None:
        state_targets = {
            "managed-roster-player-1": {
                "entity_fingerprint": "player:sleeper_id:1",
                "target_set_ids": ["managed-roster-health"],
                "observations": {
                    "injury-status": {},
                    "role-opportunity": {},
                },
            }
        }
        selector_contracts = [
            {
                "target_set_id": "managed-roster-health",
                "selector_id": "managed-team-roster-players",
                "entity_type": "player",
                "profile_refs": {"injury-status", "role-opportunity"},
                "enabled": True,
            }
        ]
        report = Report()
        validate_observation_state_targets(
            state_targets,
            {},
            selector_contracts,
            report,
            Path("state.json"),
        )
        self.assertEqual([], report.errors, report.to_json())

    def test_dynamic_state_target_rejects_unbound_profile(self) -> None:
        state_targets = {
            "managed-roster-player-1": {
                "entity_fingerprint": "player:sleeper_id:1",
                "target_set_ids": ["managed-roster-health"],
                "observations": {
                    "injury-status": {},
                    "unknown-profile": {},
                },
            }
        }
        selector_contracts = [
            {
                "target_set_id": "managed-roster-health",
                "selector_id": "managed-team-roster-players",
                "entity_type": "player",
                "profile_refs": {"injury-status"},
                "enabled": True,
            }
        ]
        report = Report()
        validate_observation_state_targets(
            state_targets,
            {},
            selector_contracts,
            report,
            Path("state.json"),
        )
        self.assertTrue(
            any("allowed by matching selectors" in issue.message for issue in report.errors),
            report.to_json(),
        )


if __name__ == "__main__":
    unittest.main()
