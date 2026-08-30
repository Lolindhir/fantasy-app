import csv
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GSIS_ID = "00-0041330"


def csv_matches(path: Path):
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [row for row in csv.DictReader(handle) if row.get("gsis_id") == GSIS_ID]


class Issue184GsisDiagnostic(unittest.TestCase):
    def test_print_exact_conflict_evidence(self):
        players_rows = csv_matches(
            ROOT / "source-data/providers/nflverse/players/raw-latest.csv"
        )
        ff_rows = csv_matches(
            ROOT / "source-data/providers/nflverse/ff-player-ids/raw-latest.csv"
        )

        identity_payload = json.loads(
            (ROOT / "source-data/nfl/identities/players.json").read_text(encoding="utf-8-sig")
        )
        canonical_rows = [
            row
            for row in identity_payload.get("Players", [])
            if (row.get("IDs") or {}).get("GSIS") == GSIS_ID
            or GSIS_ID in ((row.get("IDAliases") or {}).get("GSIS") or [])
        ]

        mapping_payload = json.loads(
            (ROOT / "source-data/nfl/identities/provider-mappings.json").read_text(
                encoding="utf-8-sig"
            )
        )
        mapping_rows = [
            row
            for row in mapping_payload.get("Mappings", [])
            if row.get("Provider") == "GSIS" and str(row.get("ExternalID")) == GSIS_ID
        ]
        conflict_rows = [
            row
            for row in mapping_payload.get("Conflicts", [])
            if row.get("Provider") == "GSIS" and str(row.get("ExternalID")) == GSIS_ID
        ]

        evidence = {
            "nflverse.players": players_rows,
            "nflverse.ff-player-ids": ff_rows,
            "canonical": canonical_rows,
            "providerMappings": mapping_rows,
            "providerConflicts": conflict_rows,
        }
        self.fail("ISSUE184_GSIS_EVIDENCE=" + json.dumps(evidence, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
