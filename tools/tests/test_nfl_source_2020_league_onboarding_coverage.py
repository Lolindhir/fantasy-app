from __future__ import annotations

import csv
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

from league_source_data_lib.materialize import PlayerMappingResolver  # noqa: E402
from nfl_source_data_lib.canonical_identity import (  # noqa: E402
    identity_lookup,
    provider_mapping_lookup,
)
from nfl_source_data_lib.common import clean, iter_csv  # noqa: E402
from nfl_source_data_lib.historical_crosswalk import (  # noqa: E402
    iter_historical_crosswalk_snapshots,
)
from nfl_source_data_lib.mapping_history import (  # noqa: E402
    _resolve_historical_crosswalk_row,
    extend_provider_mapping_payload,
)


class HistoricalLeagueOnboardingCoverageTests(unittest.TestCase):
    @staticmethod
    def _2020_snapshots() -> list[dict[str, object]]:
        snapshots = [
            item
            for item in iter_historical_crosswalk_snapshots(ROOT)
            if int(item["season"]) == 2020
        ]
        if not snapshots:
            raise AssertionError("Expected persisted historical identity snapshots for 2020")
        roles = {str(item["role"]) for item in snapshots}
        if roles != {"opening", "closing"}:
            raise AssertionError(
                f"2020 onboarding coverage requires opening + closing evidence, found {sorted(roles)}"
            )
        return snapshots

    @classmethod
    def _2020_evidence(cls) -> tuple[set[str], dict[str, list[dict[str, str | None]]], int, int]:
        snapshots = cls._2020_snapshots()
        sleeper_ids: set[str] = set()
        rows_by_sleeper: dict[str, list[dict[str, str | None]]] = {}
        observation_count = 0
        for snapshot in snapshots:
            path = Path(snapshot["path"])
            with path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                if "sleeper_id" not in (reader.fieldnames or []):
                    raise AssertionError(f"Missing sleeper_id in {path}")
                for row in reader:
                    sleeper_id = clean(row.get("sleeper_id"))
                    if not sleeper_id:
                        continue
                    sleeper_ids.add(sleeper_id)
                    observation_count += 1
                    rows_by_sleeper.setdefault(sleeper_id, []).append(
                        {
                            "name": clean(row.get("name")) or clean(row.get("player_name")),
                            "gsis_id": clean(row.get("gsis_id")),
                            "espn_id": clean(row.get("espn_id")),
                            "pfr_id": clean(row.get("pfr_id")),
                        }
                    )
        return sleeper_ids, rows_by_sleeper, observation_count, len(snapshots)

    def test_every_2020_historical_sleeper_id_resolves_uniquely(self) -> None:
        sleeper_ids, rows_by_sleeper, observation_count, snapshot_count = self._2020_evidence()
        self.assertGreater(
            len(sleeper_ids),
            1000,
            "2020 historical identity evidence unexpectedly contains too few Sleeper IDs",
        )

        resolver = PlayerMappingResolver.load(ROOT)
        unresolved: list[str] = []
        ambiguous: list[str] = []

        for sleeper_id in sorted(sleeper_ids):
            try:
                canonical_id = resolver.resolve("Sleeper", sleeper_id, 2020)
            except ValueError as exc:
                ambiguous.append(f"{sleeper_id}: {exc}")
                continue
            if canonical_id is None:
                unresolved.append(sleeper_id)

        detail = (
            f"snapshots={snapshot_count}, observations={observation_count}, "
            f"uniqueSleeperIDs={len(sleeper_ids)}"
        )
        self.assertFalse(
            ambiguous,
            "2020 historical Sleeper IDs with ambiguous seasonal mappings; "
            f"{detail}; first={ambiguous[:50]}",
        )

        no_mapping_record: list[str] = []
        mapping_outside_2020: list[str] = []
        unresolved_details: list[dict[str, object]] = []
        for sleeper_id in unresolved:
            mapping_records = resolver.mappings.get(("Sleeper", sleeper_id), [])
            if mapping_records:
                mapping_outside_2020.append(sleeper_id)
            else:
                no_mapping_record.append(sleeper_id)

            unresolved_details.append(
                {
                    "sleeper": sleeper_id,
                    "evidence": rows_by_sleeper.get(sleeper_id, []),
                    "mappingSpans": [
                        {
                            "canonical": item.get("CanonicalPlayerID"),
                            "first": item.get("FirstObservedSeason"),
                            "last": item.get("LastObservedSeason"),
                            "sources": item.get("Sources"),
                        }
                        for item in mapping_records
                    ],
                }
            )

        self.assertFalse(
            unresolved,
            "2020 historical Sleeper IDs without a seasonal CanonicalPlayerID; "
            f"{detail}; count={len(unresolved)}; "
            f"noMappingRecord={len(no_mapping_record)}; "
            f"mappingOutside2020={len(mapping_outside_2020)}; "
            f"first={unresolved_details[:40]}",
        )

    def test_current_2020_replay_explains_or_repairs_gap(self) -> None:
        sleeper_ids, rows_by_sleeper, _, _ = self._2020_evidence()
        canonical_payload = json.loads(
            (ROOT / "source-data/nfl/identities/players.json").read_text(encoding="utf-8-sig")
        )
        mapping_payload = json.loads(
            (ROOT / "source-data/nfl/identities/provider-mappings.json").read_text(
                encoding="utf-8-sig"
            )
        )
        lookup = identity_lookup(canonical_payload.get("Players") or [])

        claims: list[dict[str, object]] = []
        conflicts: list[dict[str, object]] = []
        resolved_rows = 0
        insufficient_rows = 0
        conflicting_rows = 0
        for snapshot in self._2020_snapshots():
            source = (
                f"{snapshot['sourceId']}.git.2020.{snapshot['role']}"
                f"@{str(snapshot['commitSha'])[:12]}"
            )
            for row in iter_csv(Path(snapshot["path"])):
                row_claims, conflict, status = _resolve_historical_crosswalk_row(
                    row,
                    season=2020,
                    lookup=lookup,
                    source=source,
                )
                if status == "resolved":
                    resolved_rows += 1
                    claims.extend(row_claims)
                elif status == "conflict":
                    conflicting_rows += 1
                    if conflict is not None:
                        conflicts.append(conflict)
                else:
                    insufficient_rows += 1

        sleeper_claims_2020 = {
            str(claim["ExternalID"]): str(claim["CanonicalPlayerID"])
            for claim in claims
            if claim.get("Provider") == "Sleeper"
        }
        extended = extend_provider_mapping_payload(mapping_payload, claims, conflicts)

        unresolved_before = [
            sleeper_id
            for sleeper_id in sorted(sleeper_ids)
            if provider_mapping_lookup(mapping_payload, "Sleeper", sleeper_id, 2020) is None
        ]
        unresolved_after = [
            sleeper_id
            for sleeper_id in sorted(sleeper_ids)
            if provider_mapping_lookup(extended, "Sleeper", sleeper_id, 2020) is None
        ]
        claimable_before = [
            sleeper_id for sleeper_id in unresolved_before if sleeper_id in sleeper_claims_2020
        ]
        unclaimable_before = [
            sleeper_id for sleeper_id in unresolved_before if sleeper_id not in sleeper_claims_2020
        ]

        detail = {
            "unresolvedBefore": len(unresolved_before),
            "claimableBefore": len(claimable_before),
            "unclaimableBefore": len(unclaimable_before),
            "unresolvedAfterReplay": len(unresolved_after),
            "resolvedRows2020": resolved_rows,
            "insufficientRows2020": insufficient_rows,
            "conflictingRows2020": conflicting_rows,
            "examplesClaimable": [
                {
                    "sleeper": sleeper_id,
                    "canonical": sleeper_claims_2020.get(sleeper_id),
                    "evidence": rows_by_sleeper.get(sleeper_id, []),
                }
                for sleeper_id in claimable_before[:12]
            ],
            "examplesUnclaimable": [
                {
                    "sleeper": sleeper_id,
                    "evidence": rows_by_sleeper.get(sleeper_id, []),
                }
                for sleeper_id in unclaimable_before[:12]
            ],
            "examplesStillUnresolved": unresolved_after[:40],
        }

        self.assertFalse(
            unresolved_after,
            "2020-only in-memory historical replay still leaves onboarding gaps; "
            f"diagnostics={detail}",
        )
        self.assertGreater(
            len(unresolved_before),
            0,
            "Diagnostic expected the currently persisted mapping payload to expose the known gap",
        )
        self.assertEqual(
            unresolved_before,
            claimable_before,
            "All currently persisted 2020 gaps should be repairable by the current 2020 replay; "
            f"diagnostics={detail}",
        )


if __name__ == "__main__":
    unittest.main()
