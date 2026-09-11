from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import sys

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from league_source_data_lib.coverage import build_season_player_reference_coverage  # noqa: E402


def player_ref(sleeper_id: str, canonical: str | None) -> dict:
    return {
        "CanonicalPlayerID": canonical,
        "ProviderMappings": [
            {"Provider": "Sleeper", "ProviderPlayerID": sleeper_id}
        ],
    }


class LeagueSourcePlayerCoverageTests(unittest.TestCase):
    def _write(self, root: Path, relative: str, payload: object) -> None:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def test_counts_unresolved_player_references_across_all_league_domains(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            season_root = Path(tmp) / "source-data/leagues/nfl-reise/seasons/2025"
            self._write(
                season_root,
                "rosters.json",
                [{"Players": [player_ref("S1", None), player_ref("S2", "NFLP-2")]}],
            )
            self._write(
                season_root,
                "matchups/week-1.json",
                [{"Players": [player_ref("S1", None)]}],
            )
            self._write(
                season_root,
                "transactions/week-1.json",
                [{"Adds": [{"Player": player_ref("S3", None)}]}],
            )
            self._write(
                season_root,
                "drafts.json",
                [{"Picks": [{"Player": player_ref("S4", "NFLP-4")}]}],
            )

            coverage = build_season_player_reference_coverage(season_root)

            self.assertEqual(5, coverage["ReferenceCount"])
            self.assertEqual(2, coverage["ResolvedReferenceCount"])
            self.assertEqual(3, coverage["UnresolvedReferenceCount"])
            self.assertEqual(4, coverage["UniqueSleeperPlayerIDCount"])
            self.assertEqual(2, coverage["UnresolvedUniqueSleeperPlayerIDCount"])
            self.assertEqual(["S1", "S3"], coverage["UnresolvedSleeperPlayerIDs"])
            self.assertFalse(coverage["Ready"])
            self.assertEqual(2, coverage["ByDomain"]["Rosters"]["ReferenceCount"])
            self.assertEqual(1, coverage["ByDomain"]["Transactions"]["UnresolvedReferenceCount"])

    def test_empty_or_fully_resolved_season_is_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            season_root = Path(tmp) / "season"
            self._write(
                season_root,
                "rosters.json",
                [{"Players": [player_ref("S1", "NFLP-1")]}],
            )

            coverage = build_season_player_reference_coverage(season_root)

            self.assertTrue(coverage["Ready"])
            self.assertEqual(0, coverage["UnresolvedReferenceCount"])
            self.assertEqual([], coverage["UnresolvedSleeperPlayerIDs"])


if __name__ == "__main__":
    unittest.main()
