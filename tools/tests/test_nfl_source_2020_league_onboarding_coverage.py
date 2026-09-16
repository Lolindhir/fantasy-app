from __future__ import annotations

import csv
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

from league_source_data_lib.materialize import PlayerMappingResolver  # noqa: E402
from nfl_source_data_lib.common import clean  # noqa: E402
from nfl_source_data_lib.historical_crosswalk import (  # noqa: E402
    iter_historical_crosswalk_snapshots,
)


class HistoricalLeagueOnboardingCoverageTests(unittest.TestCase):
    def test_every_2020_historical_sleeper_id_resolves_uniquely(self) -> None:
        snapshots = [
            item
            for item in iter_historical_crosswalk_snapshots(ROOT)
            if int(item["season"]) == 2020
        ]
        self.assertTrue(snapshots, "Expected persisted historical identity snapshots for 2020")
        self.assertEqual(
            {"opening", "closing"},
            {str(item["role"]) for item in snapshots},
            "2020 onboarding coverage requires both opening and closing evidence",
        )

        sleeper_ids: set[str] = set()
        rows_by_sleeper: dict[str, list[dict[str, str | None]]] = {}
        observation_count = 0
        for snapshot in snapshots:
            path = Path(snapshot["path"])
            with path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertIn("sleeper_id", reader.fieldnames or [], str(path))
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
            f"snapshots={len(snapshots)}, observations={observation_count}, "
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

            evidence = rows_by_sleeper.get(sleeper_id, [])
            mapping_spans = [
                {
                    "canonical": item.get("CanonicalPlayerID"),
                    "first": item.get("FirstObservedSeason"),
                    "last": item.get("LastObservedSeason"),
                    "sources": item.get("Sources"),
                }
                for item in mapping_records
            ]
            unresolved_details.append(
                {
                    "sleeper": sleeper_id,
                    "evidence": evidence,
                    "mappingSpans": mapping_spans,
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


if __name__ == "__main__":
    unittest.main()
