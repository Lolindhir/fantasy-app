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
                f"2020 historical identity coverage requires opening + closing evidence, found {sorted(roles)}"
            )
        return snapshots

    @classmethod
    def _2020_evidence(cls) -> tuple[set[str], dict[str, set[tuple[str, str]]], int]:
        sleeper_ids: set[str] = set()
        anchors_by_sleeper: dict[str, set[tuple[str, str]]] = {}
        observation_count = 0

        for snapshot in cls._2020_snapshots():
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
                    anchors = anchors_by_sleeper.setdefault(sleeper_id, set())
                    for field, provider in (
                        ("gsis_id", "GSIS"),
                        ("espn_id", "ESPN"),
                        ("pfr_id", "PFR"),
                    ):
                        external_id = clean(row.get(field))
                        if external_id:
                            anchors.add((provider, external_id))

        return sleeper_ids, anchors_by_sleeper, observation_count

    def test_unresolved_2020_crosswalk_ids_have_no_safe_seasonal_corroboration(self) -> None:
        """Fail if persisted evidence could safely resolve a Sleeper ID but did not.

        The DynastyProcess snapshot is a provider-wide identity universe, not this
        fantasy league's roster universe. Missing Sleeper mappings are therefore
        allowed when evidence is insufficient or conflicting. What is *not*
        allowed is leaving a Sleeper ID unresolved when two independent
        non-Sleeper IDs are already mapped to the same CanonicalPlayerID in the
        exact observed season.

        Later-only mappings are deliberately ignored here: using them would
        back-project today's/later identity state into 2020 and violate the
        historical identity contract.
        """

        sleeper_ids, anchors_by_sleeper, observation_count = self._2020_evidence()
        self.assertGreater(
            len(sleeper_ids),
            1000,
            "2020 historical identity evidence unexpectedly contains too few Sleeper IDs",
        )
        self.assertGreater(
            observation_count,
            4000,
            "2020 opening/closing evidence unexpectedly contains too few observations",
        )

        resolver = PlayerMappingResolver.load(ROOT)
        safe_but_unresolved: list[dict[str, object]] = []

        for sleeper_id in sorted(sleeper_ids):
            try:
                current = resolver.resolve("Sleeper", sleeper_id, 2020)
            except ValueError:
                # Ambiguous Sleeper mappings are already fail-closed and must not
                # be auto-repaired from a provider-wide crosswalk.
                continue
            if current is not None:
                continue

            resolved_anchors: list[tuple[str, str, str]] = []
            anchor_conflict = False
            for provider, external_id in sorted(anchors_by_sleeper.get(sleeper_id, set())):
                try:
                    canonical_id = resolver.resolve(provider, external_id, 2020)
                except ValueError:
                    anchor_conflict = True
                    break
                if canonical_id:
                    resolved_anchors.append((provider, external_id, canonical_id))

            owners = {item[2] for item in resolved_anchors}
            if not anchor_conflict and len(resolved_anchors) >= 2 and len(owners) == 1:
                safe_but_unresolved.append(
                    {
                        "SleeperID": sleeper_id,
                        "CanonicalPlayerID": next(iter(owners)),
                        "SeasonValidAnchors": resolved_anchors,
                    }
                )

        self.assertEqual(
            [],
            safe_but_unresolved,
            "Historical replay missed 2020 Sleeper IDs despite two agreeing, "
            "season-valid non-Sleeper anchors. These are materializer bugs, not "
            f"evidence gaps: {safe_but_unresolved[:50]}",
        )


if __name__ == "__main__":
    unittest.main()
