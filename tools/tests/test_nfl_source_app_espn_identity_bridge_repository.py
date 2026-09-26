from __future__ import annotations

import json
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
            rebuilt_row["CanonicalPlayerID"] = rebuilt_by_sleeper.get(sleeper_id)
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
        print(
            "6Z.5 unresolved current identity-gap details: "
            + json.dumps(unresolved, ensure_ascii=False, sort_keys=True)
        )

        app_players = {
            str(row.get("ID")): row
            for row in original_load_json(ROOT / "public/data" / "Players.json")
            if row.get("ID") is not None
        }
        persisted_identities = original_load_json(canonical_identity_path)
        persisted_by_id = {
            str(row.get("CanonicalPlayerID")): row
            for row in persisted_identities.get("Players", [])
            if row.get("CanonicalPlayerID")
        }
        evidence_rows = []
        for row in unresolved:
            player_id = str(row["player_id"])
            app_row = app_players.get(player_id, {})
            target_id = (
                row.get("identity_diagnostic", {})
                .get("current_season", {})
                .get("unique_other_canonical_id")
            )
            target = persisted_by_id.get(str(target_id), {}) if target_id else {}
            provisional = persisted_by_id.get(str(row.get("canonical_player_id")), {})
            evidence_rows.append(
                {
                    "player_id": player_id,
                    "name": row.get("name"),
                    "app": {
                        "TankID": app_row.get("TankID"),
                        "ESPNID": app_row.get("ESPNID"),
                        "ESPN": app_row.get("ESPN"),
                        "Team": app_row.get("Team"),
                        "TeamID": app_row.get("TeamID"),
                    },
                    "provisional_ids": provisional.get("IDs"),
                    "target_canonical_player_id": target_id,
                    "target_ids": target.get("IDs"),
                    "target_aliases": target.get("IDAliases"),
                    "target_sources": target.get("Sources"),
                }
            )
        print(
            "6Z.5 unresolved provider evidence: "
            + json.dumps(evidence_rows, ensure_ascii=False, sort_keys=True)
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
