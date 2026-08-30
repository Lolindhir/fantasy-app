import csv
import json
import unittest
from collections import defaultdict
from pathlib import Path

from nfl_source_data_lib import identity as identity_mod
from nfl_source_data_lib.common import load_registry
from nfl_source_data_lib.identity_model import LINK_ID_KEYS


ROOT = Path(__file__).resolve().parents[2]
TOKENS = {"BRO628728", "BrowBo03", "BrowRo02"}


def rows_containing(path: Path):
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [
            row
            for row in csv.DictReader(handle)
            if TOKENS.intersection({str(value) for value in row.values() if value is not None})
        ]


def canonical_rows_containing(payload, tokens):
    result = []
    for row in payload:
        ids = row.get("IDs") or {}
        aliases = row.get("IDAliases") or {}
        values = {str(value) for value in ids.values() if value is not None}
        for alias_values in aliases.values():
            values.update(str(value) for value in alias_values or [])
        if tokens.intersection(values):
            result.append(row)
    return result


class Issue184Bro628728Diagnostic(unittest.TestCase):
    def test_print_exact_conflict_evidence_and_all_latent_link_collisions(self):
        players_rows = rows_containing(
            ROOT / "source-data/providers/nflverse/players/raw-latest.csv"
        )
        ff_rows = rows_containing(
            ROOT / "source-data/providers/nflverse/ff-player-ids/raw-latest.csv"
        )

        identity_payload = json.loads(
            (ROOT / "source-data/nfl/identities/players.json").read_text(encoding="utf-8-sig")
        )
        persisted_rows = canonical_rows_containing(identity_payload.get("Players", []), TOKENS)

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

        datasets = {dataset.id: dataset for dataset in load_registry(ROOT)}
        original_guard = identity_mod.identity_lookup
        identity_mod.identity_lookup = lambda canonical: {}
        try:
            canonical, *_ = identity_mod.build_identities(ROOT, datasets)
        finally:
            identity_mod.identity_lookup = original_guard

        owners = defaultdict(list)
        for row in canonical:
            canonical_id = row.get("CanonicalPlayerID")
            ids = row.get("IDs") or {}
            aliases = row.get("IDAliases") or {}
            for provider in LINK_ID_KEYS:
                values = []
                if ids.get(provider):
                    values.append(str(ids[provider]))
                values.extend(str(value) for value in aliases.get(provider, []) or [])
                for value in values:
                    owners[(provider, value)].append(canonical_id)

        duplicates = {
            f"{provider}:{external_id}": sorted(set(canonical_ids))
            for (provider, external_id), canonical_ids in sorted(owners.items())
            if len(set(canonical_ids)) > 1
        }
        duplicate_tokens = {token.split(":", 1)[1] for token in duplicates}
        duplicate_rows = canonical_rows_containing(canonical, duplicate_tokens)

        evidence = {
            "specific": {
                "nflverse.players": players_rows,
                "nflverse.ff-player-ids": ff_rows,
                "persistedCanonical": persisted_rows,
                "persistedProviderMappings": mapping_rows,
            },
            "latentDuplicateLinkIDs": duplicates,
            "latentDuplicateCanonicalRows": duplicate_rows,
        }
        self.fail("ISSUE184_LINK_COLLISION_EVIDENCE=" + json.dumps(evidence, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
