from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Any

from tools.nfl_source_data_lib import common as common_mod
from tools.nfl_source_data_lib.common import CANONICAL_SCHEMA_VERSION, write_json_if_changed
from tools.nfl_source_data_lib.identity import build_identities
from tools.nfl_source_data_lib.mapping_history import (
    build_historical_app_mapping_claims,
    extend_provider_mapping_payload,
)
from tools.nfl_source_data_lib.materialize import _observation_season
from tools.nfl_source_data_lib.provider_mappings import build_provider_mapping_payload
from tools.nfl_source_data_lib.provisional_reconciliation import (
    reconcile_provisional_app_mappings,
)


class RealProviderMappingDiagnostics(unittest.TestCase):
    def test_real_full_history_provider_mapping_convergence_diagnostic(self) -> None:
        """Emit the exact real-data provider-mapping churn without blocking CI.

        Pull-request CI uses a shallow checkout and skips this diagnostic. The
        production NFL source workflow uses full history, so the test makes a
        local shared clone, replays only identity + provider-mapping stages twice,
        and prints a compact semantic diff when pass two still changes the payload.
        This file is temporary and must be removed with the resulting fix.
        """

        repo_root = Path(__file__).resolve().parents[2]
        shallow = subprocess.run(
            ["git", "rev-parse", "--is-shallow-repository"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if shallow == "true" or os.environ.get("GITHUB_ACTIONS") != "true":
            self.skipTest("real mapping diagnostic requires full-history GitHub Actions checkout")

        with tempfile.TemporaryDirectory() as tmp:
            clone_root = Path(tmp) / "repo"
            subprocess.run(
                ["git", "clone", "--shared", "--quiet", str(repo_root), str(clone_root)],
                check=True,
            )
            datasets = {
                dataset.id: dataset for dataset in common_mod.load_registry(clone_root)
            }

            def replay() -> dict[str, Any]:
                canonical, _, _, provider_claims, mapping_conflicts = build_identities(
                    clone_root, datasets
                )
                observation_season = _observation_season(clone_root)
                payload = build_provider_mapping_payload(
                    clone_root,
                    provider_claims,
                    mapping_conflicts,
                    observation_season,
                )
                historical_claims, resolution_conflicts, _ = (
                    build_historical_app_mapping_claims(clone_root, canonical)
                )
                payload = extend_provider_mapping_payload(
                    payload,
                    historical_claims,
                    resolution_conflicts,
                )
                payload = reconcile_provisional_app_mappings(payload, historical_claims)

                identity_payload = {
                    "SchemaVersion": CANONICAL_SCHEMA_VERSION,
                    "IdentityPolicy": {
                        "InternalKey": "CanonicalPlayerID",
                        "CanonicalPlayerIDNamespace": "fantasy-app",
                        "CanonicalPlayerIDIsApplicationDefined": True,
                        "ExternalIDsAreMappings": True,
                        "ProviderMappingsAreHistorical": True,
                        "CurrentAppPlayerIDProvider": "Sleeper",
                        "ExistingCanonicalPlayerIDIsStable": True,
                        "NameMatchingIsAuthoritative": False,
                    },
                    "Players": canonical,
                }
                write_json_if_changed(
                    clone_root / "source-data/nfl/identities/players.json",
                    identity_payload,
                )
                write_json_if_changed(
                    clone_root / "source-data/nfl/identities/provider-mappings.json",
                    payload,
                )
                return payload

            first = replay()
            second = replay()
            if first == second:
                print("REAL_PROVIDER_MAPPING_DIAGNOSTIC: payload converged on pass two")
                return

            def grouped_mappings(payload: dict[str, Any]) -> dict[tuple[str, str, str], list[dict[str, Any]]]:
                grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
                for item in payload.get("Mappings", []):
                    key = (
                        str(item.get("Provider") or ""),
                        str(item.get("ExternalID") or ""),
                        str(item.get("CanonicalPlayerID") or ""),
                    )
                    grouped.setdefault(key, []).append(item)
                for values in grouped.values():
                    values.sort(
                        key=lambda item: (
                            int(item.get("FirstObservedSeason") or 0),
                            int(item.get("LastObservedSeason") or 0),
                            tuple(str(value) for value in item.get("Sources") or []),
                        )
                    )
                return grouped

            first_groups = grouped_mappings(first)
            second_groups = grouped_mappings(second)
            mapping_changes = []
            for key in sorted(set(first_groups) | set(second_groups)):
                before = first_groups.get(key, [])
                after = second_groups.get(key, [])
                if before != after:
                    mapping_changes.append(
                        {
                            "Provider": key[0],
                            "ExternalID": key[1],
                            "CanonicalPlayerID": key[2],
                            "before": before,
                            "after": after,
                        }
                    )

            top_level_changes = {
                key: {
                    "beforeCount": len(first.get(key, [])) if isinstance(first.get(key), list) else None,
                    "afterCount": len(second.get(key, [])) if isinstance(second.get(key), list) else None,
                }
                for key in sorted(set(first) | set(second))
                if first.get(key) != second.get(key) and key != "Mappings"
            }
            diagnostic = {
                "mappingChangeCount": len(mapping_changes),
                "mappingChanges": mapping_changes[:20],
                "topLevelChanges": top_level_changes,
            }
            print(
                "REAL_PROVIDER_MAPPING_DIAGNOSTIC: "
                + json.dumps(diagnostic, ensure_ascii=False, sort_keys=True)
            )


if __name__ == "__main__":
    unittest.main()
