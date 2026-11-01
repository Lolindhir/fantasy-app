from __future__ import annotations

import sys
import json
import tempfile
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
    validate_pretty_json,
    validate_target_sets,
    validate_managed_team_source,
)


class AutomationValidatorTests(unittest.TestCase):
    def test_repository_automation_configuration_is_valid(self) -> None:
        root = Path(__file__).resolve().parents[4]
        report = validate_automation(root)
        self.assertEqual([], report.errors, report.to_json())

    def test_managed_team_source_has_canonical_identity_and_exact_membership(self) -> None:
        root = Path(__file__).resolve().parents[4]
        config = json.loads((root / "fantasy-management/automation/runner-config.json").read_text(encoding="utf-8"))
        report = Report()
        validate_managed_team_source(root, config["managed_team"], report, root / "runner-config.json")
        self.assertEqual([], report.errors, report.to_json())
        signals = json.loads((root / config["managed_team"]["source"]).read_text(encoding="utf-8"))
        self.assertEqual(1, signals["managed_team"]["team_id"])
        self.assertEqual(37, len(signals["players"]))
        self.assertEqual(37, len({p["player_id"] for p in signals["players"]}))

    def test_managed_team_source_rejects_missing_wrong_identity_or_partial_roster(self) -> None:
        relative = "fantasy-management/generated/operations/managed-roster-signals.json"
        config = {"source": relative, "identity_field": "managed_team.team_id", "team_id": 1}
        original = {
            "schema_version": 1,
            "dataset_id": "managed-roster-signals",
            "managed_team": {"team_id": 1, "name": "Test Team", "player_count": 2},
            "players": [
                {"player_id": "a", "roster_sections": ["roster", "reserve"]},
                {"player_id": "b", "roster_sections": ["roster", "taxi"]},
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / relative
            source.parent.mkdir(parents=True)
            def check(payload: dict | None, cfg: dict | None = None) -> list[str]:
                if payload is None:
                    source.unlink(missing_ok=True)
                else:
                    source.write_text(json.dumps(payload) + "\n", encoding="utf-8")
                report = Report()
                validate_managed_team_source(root, cfg or config, report, root / "runner-config.json")
                return [item.message for item in report.errors]

            self.assertEqual([], check(original))
            self.assertTrue(any("Missing JSON file" in s for s in check(None)))
            self.assertTrue(any("team_id" in s for s in check({
                **original, "managed_team": {**original["managed_team"], "team_id": 2}
            })))
            self.assertTrue(any("player_count" in s for s in check({
                **original, "managed_team": {**original["managed_team"], "player_count": 3}
            })))
            self.assertTrue(any("duplicate player_id" in s for s in check({
                **original, "players": [original["players"][0], original["players"][0]]
            })))
            self.assertTrue(any("roster_sections" in s for s in check({
                **original, "players": [original["players"][0], {"player_id": "b"}]
            })))
            self.assertTrue(any("identity_field" in s for s in check(original, {
                **config, "identity_field": "TeamID"
            })))
            self.assertTrue(any("managed_team.source" in s for s in check(original, {
                **config, "source": "public/data/League.json"
            })))

    def test_state_json_must_be_pretty_printed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "state.json"
            data = {"job_id": "example", "revision": 1}
            path.write_text('{"job_id":"example","revision":1}\n', encoding="utf-8")
            report = Report()

            validate_pretty_json(path, data, report)

            self.assertTrue(
                any("2-space indentation" in issue.message for issue in report.errors),
                report.to_json(),
            )

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
