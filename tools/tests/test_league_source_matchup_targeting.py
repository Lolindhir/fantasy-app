from __future__ import annotations

import json
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from league_source_data_lib.materialize import PlayerMappingResolver  # noqa: E402
from league_source_data_lib.matchup_materialize import (  # noqa: E402
    MATCHUP_SCOPE_DEPENDENCIES,
    plan_matchup_materialization,
    resolve_current_matchup_scope,
)
from league_source_data_lib.registry import load_league_registry  # noqa: E402
from league_source_data_lib.transaction_window import (  # noqa: E402
    load_persisted_current_league_payload,
    resolve_current_transaction_window,
)


class CurrentRepositoryMatchupScopeIntegrationTests(unittest.TestCase):
    def _current_context(self) -> tuple[str, str, dict, dict]:
        manifest_path = ROOT / "source-data" / "leagues" / "nfl-reise" / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        provider_league_id = str(manifest["CurrentProviderLeagueID"])
        payload = load_persisted_current_league_payload(ROOT, provider_league_id)
        scope = resolve_current_matchup_scope(
            ROOT,
            "nfl-reise",
            provider_league_id,
            payload,
        )
        return provider_league_id, str(scope["Season"]), payload, scope

    def test_current_scope_reuses_shared_current_week_resolution(self) -> None:
        provider_league_id, _, payload, scope = self._current_context()
        window = resolve_current_transaction_window(
            ROOT,
            "nfl-reise",
            provider_league_id,
            payload,
        )
        self.assertEqual(scope["Season"], window["Season"])
        self.assertEqual(scope["CurrentWeek"], window["CurrentWeek"])
        self.assertEqual(scope["WeekCeiling"], window["WeekCeiling"])
        self.assertEqual(scope["Evidence"], window["Evidence"])
        self.assertGreaterEqual(scope["CurrentWeek"], 1)
        self.assertLessEqual(scope["CurrentWeek"], scope["WeekCeiling"])

    def test_current_scope_materializes_exactly_one_existing_matchup_partition(self) -> None:
        _, season_text, _, scope = self._current_context()
        registry = load_league_registry(ROOT)
        resolver = PlayerMappingResolver.load(ROOT)
        outputs = plan_matchup_materialization(
            ROOT,
            "nfl-reise",
            registry,
            resolver,
            seasons={int(season_text)},
            weeks={int(scope["CurrentWeek"])},
        )
        self.assertEqual(len(outputs), 1)
        output = outputs[0]
        self.assertEqual(output.path.name, f"week-{scope['CurrentWeek']}.json")
        existing = json.loads(output.path.read_text(encoding="utf-8"))
        self.assertEqual(output.value, existing)

    def test_current_scope_refuses_provider_identity_drift(self) -> None:
        provider_league_id, _, payload, _ = self._current_context()
        broken = dict(payload)
        broken["league_id"] = "wrong-provider"
        with self.assertRaisesRegex(ValueError, "does not match the configured provider league"):
            resolve_current_matchup_scope(
                ROOT,
                "nfl-reise",
                provider_league_id,
                broken,
            )

    def test_matchup_materialization_rejects_non_positive_week(self) -> None:
        _, season_text, _, _ = self._current_context()
        registry = load_league_registry(ROOT)
        resolver = PlayerMappingResolver.load(ROOT)
        with self.assertRaisesRegex(ValueError, "positive integers"):
            plan_matchup_materialization(
                ROOT,
                "nfl-reise",
                registry,
                resolver,
                seasons={int(season_text)},
                weeks={0},
            )

    def test_scope_dependencies_are_bounded(self) -> None:
        self.assertEqual(
            MATCHUP_SCOPE_DEPENDENCIES,
            (
                "canonical-rosters",
                "nfl-player-provider-mappings",
                "raw-sleeper-matchups",
            ),
        )


if __name__ == "__main__":
    unittest.main()
