import csv
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TOKENS = {"BRO628728", "BrowBo03", "BrowRo02"}


def rows_containing(path: Path):
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [
            row
            for row in csv.DictReader(handle)
            if TOKENS.intersection({str(value) for value in row.values() if value is not None})
        ]


class Issue184Bro628728Diagnostic(unittest.TestCase):
    def test_print_exact_conflict_evidence(self):
        players_rows = rows_containing(
            ROOT / "source-data/providers/nflverse/players/raw-latest.csv"
        )
        ff_rows = rows_containing(
            ROOT / "source-data/providers/nflverse/ff-player-ids/raw-latest.csv"
        )

        identity_payload = json.loads(
            (ROOT / "source-data/nfl/identities/players.json").read_text(encoding="utf-8-sig")
        )
        canonical_rows = []
        for row in identity_payload.get("Players", []):
            ids = row.get("IDs") or {}
            aliases = row.get("IDAliases") or {}
            values = {str(value) for value in ids.values() if value is not None}
            for alias_values in aliases.values():
                values.update(str(value) for value in alias_values or [])
            if TOKENS.intersection(values):
                canonical_rows.append(row)

        mapping_payload = json.loads(
            (ROOT / "source-data/nfl/identities/provider-mappings.json").read_text(
                encoding="utf-8-sig"
            )
        )
        mapping_rows = [
            row
            for row in mapping_payload.get("Mappings", [])
            if str(row.get("ExternalID")) in TOKENS
        ]
        conflict_rows = [
            row
            for row in mapping_payload.get("Conflicts", [])
            if str(row.get("ExternalID")) in TOKENS
        ]

        evidence = {
            "nflverse.players": players_rows,
            "nflverse.ff-player-ids": ff_rows,
            "canonical": canonical_rows,
            "providerMappings": mapping_rows,
            "providerConflicts": conflict_rows,
        }
        self.fail("ISSUE184_BRO628728_EVIDENCE=" + json.dumps(evidence, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
