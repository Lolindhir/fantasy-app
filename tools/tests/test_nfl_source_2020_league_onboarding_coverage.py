from __future__ import annotations

import csv
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

from league_source_data_lib.materialize import PlayerMappingResolver  # noqa: E402
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
        observation_count = 0
        for snapshot in snapshots:
            path = Path(snapshot["path"])
            with path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertIn("sleeper_id", reader.fieldnames or [], str(path))
                for row in reader:
                    sleeper_id = str(row.get("sleeper_id") or "").strip()
                    if not sleeper_id:
                        continue
                    sleeper_ids.add(sleeper_id)
                    observation_count += 1

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
        self.assertFalse(
            unresolved,
            "2020 historical Sleeper IDs without a seasonal CanonicalPlayerID; "
            f"{detail}; count={len(unresolved)}; first={unresolved[:100]}",
        )


if __name__ == "__main__":
    unittest.main()
