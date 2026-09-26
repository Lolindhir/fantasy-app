from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.nfl_source_data_lib.common import load_registry
from tools.nfl_source_data_lib.identity import build_identities

ROOT = Path(__file__).resolve().parents[2]
FM_SCRIPTS = ROOT / "fantasy-management" / "_ai" / "scripts"
if str(FM_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(FM_SCRIPTS))

import audit_player_signal_population_policy as population_policy  # noqa: E402


class AppEspnIdentityBridgeRepositoryTests(unittest.TestCase):
    def test_rebuilt_identities_reduce_current_population_identity_gap(self) -> None:
        config_path = (
            ROOT
            / "fantasy-management"
            / "automation"
            / "player-signal-materialization.json"
        )

        baseline = population_policy.build(ROOT, config_path)
        baseline_gap = int(baseline["current_identity_gap_candidates"]["count"])
        self.assertGreater(
            baseline_gap,
            0,
            "Repository baseline unexpectedly has no current identity-gap candidates",
        )

        datasets = {dataset.id: dataset for dataset in load_registry(ROOT)}
        rebuilt_players, _, _, _, _ = build_identities(ROOT, datasets)
        rebuilt_document = {
            "SchemaVersion": 2,
            "Players": rebuilt_players,
        }

        canonical_identity_path = (
            ROOT / "source-data" / "nfl" / "identities" / "players.json"
        ).resolve()
        original_load_json = population_policy.ops.load_json

        def load_json_with_rebuilt_identity(path: Path):
            if Path(path).resolve() == canonical_identity_path:
                return rebuilt_document
            return original_load_json(path)

        with patch.object(
            population_policy.ops,
            "load_json",
            side_effect=load_json_with_rebuilt_identity,
        ):
            rebuilt = population_policy.build(ROOT, config_path)

        rebuilt_gap = int(rebuilt["current_identity_gap_candidates"]["count"])
        unresolved = rebuilt["current_identity_gap_candidates"]["players"]
        print(
            "6Z.5 identity-gap audit: "
            f"before={baseline_gap}, after={rebuilt_gap}, "
            f"resolved={baseline_gap - rebuilt_gap}"
        )
        print(
            "6Z.5 unresolved current identity-gap player IDs: "
            + ", ".join(str(row["player_id"]) for row in unresolved)
        )

        self.assertLess(
            rebuilt_gap,
            baseline_gap,
            "Corroborated ESPN bridge did not reduce the current identity-gap cohort",
        )
        self.assertLessEqual(
            rebuilt_gap,
            10,
            "Too many current identity-gap candidates remain for the bounded 6Z.5 repair",
        )


if __name__ == "__main__":
    unittest.main()
