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
        rebuilt_identity_document = {
            "SchemaVersion": 2,
            "Players": rebuilt_players,
        }
        rebuilt_by_sleeper = {
            str((row.get("IDs") or {})["Sleeper"]): str(row["CanonicalPlayerID"])
            for row in rebuilt_players
            if (row.get("IDs") or {}).get("Sleeper") and row.get("CanonicalPlayerID")
        }

        canonical_identity_path = (
            ROOT / "source-data" / "nfl" / "identities" / "players.json"
        ).resolve()
        canonical_sleeper_path = (
            ROOT / "source-data" / "nfl" / "platform" / "sleeper" / "players.json"
        ).resolve()
        original_load_json = population_policy.ops.load_json
        persisted_sleeper_document = original_load_json(canonical_sleeper_path)
        self.assertIsInstance(persisted_sleeper_document, dict)
        self.assertIsInstance(persisted_sleeper_document.get("Records"), list)

        rebuilt_sleeper_records = []
        for row in persisted_sleeper_document["Records"]:
            rebuilt_row = dict(row)
            sleeper_id = str(row.get("SleeperPlayerID") or "")
            if sleeper_id in rebuilt_by_sleeper:
                rebuilt_row["CanonicalPlayerID"] = rebuilt_by_sleeper[sleeper_id]
            rebuilt_sleeper_records.append(rebuilt_row)
        rebuilt_sleeper_document = {
            **persisted_sleeper_document,
            "Records": rebuilt_sleeper_records,
        }

        def load_json_with_rebuilt_canonical_inputs(path: Path):
            resolved = Path(path).resolve()
            if resolved == canonical_identity_path:
                return rebuilt_identity_document
            if resolved == canonical_sleeper_path:
                return rebuilt_sleeper_document
            return original_load_json(path)

        with patch.object(
            population_policy.ops,
            "load_json",
            side_effect=load_json_with_rebuilt_canonical_inputs,
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
