"""External source registry and identity index (ADR-060): schema, fail-closed behavior, resolution."""
from __future__ import annotations

import copy
import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[1]
REPO_ROOT = TOOLS.parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from external_source import identity as ident  # noqa: E402
from external_source import registry as reg  # noqa: E402

PROVIDERS = {"fantasypros", "fantasycalc", "fantasy-football-calculator", "fftoday", "cbs-sports", "sleeper"}


def real_registry() -> dict:
    return reg.load_registry(REPO_ROOT)


class RegistryTests(unittest.TestCase):
    def test_repository_registry_is_valid_and_covers_all_providers(self) -> None:
        registry = real_registry()
        self.assertEqual({d["provider"] for d in registry["datasets"]}, PROVIDERS)
        self.assertEqual({d["domain"] for d in registry["datasets"]}, {"market"})

    def test_rights_are_mandatory_and_unknown_publication_is_explicit(self) -> None:
        for dataset in real_registry()["datasets"]:
            self.assertIn(dataset["rights"]["publication"], reg.RIGHTS_STATES)
            self.assertEqual(dataset["rights"]["publication"], "unknown", dataset["id"])

    def test_league_context_is_not_part_of_the_format(self) -> None:
        for dataset in real_registry()["datasets"]:
            self.assertNotIn("actual_league_team_count", dataset["format"])

    def mutated(self, mutate) -> dict:
        registry = copy.deepcopy(real_registry())
        mutate(registry)
        return registry

    def test_fail_closed_cases(self) -> None:
        cases = {
            "duplicate id": lambda r: r["datasets"].append(copy.deepcopy(r["datasets"][0])),
            "unknown key": lambda r: r["datasets"][0].update(extra=1),
            "missing rights": lambda r: r["datasets"][0].pop("rights"),
            "unknown identity provider key": lambda r: r["datasets"][0]["identity"].update(providerKey="Nope"),
            "unknown kind": lambda r: r["datasets"][0].update(kind="other"),
            "unknown domain": lambda r: r["datasets"][0].update(domain="other"),
            "bad season policy": lambda r: r["datasets"][0]["seasonPolicy"].update(regular_season="maybe"),
            "missing phase": lambda r: r["datasets"][0]["seasonPolicy"].pop("postseason"),
            "bad minimum rows": lambda r: r["datasets"][0]["quality"].update(minimumRows=0),
            "id without provider prefix": lambda r: r["datasets"][0].update(provider="fftoday"),
            "bad schema version": lambda r: r.update(schemaVersion=2),
        }
        for name, mutate in cases.items():
            with self.subTest(name), self.assertRaises(reg.ExternalRegistryError):
                reg.validate_registry(self.mutated(mutate))

    def test_missing_file_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(reg.ExternalRegistryError):
            reg.load_registry(Path(tmp))

    def test_dataset_directory_layout_matches_contract(self) -> None:
        dataset = reg.get_dataset(real_registry(), "fantasypros.ecr.dynasty-superflex-ppr")
        self.assertEqual(
            reg.dataset_dir(Path("r"), dataset).as_posix(),
            "r/data-source/market/expert-consensus/fantasypros/dynasty-superflex-ppr",
        )
        trending = reg.get_dataset(real_registry(), "sleeper.trending.add")
        self.assertEqual(reg.dataset_dir(Path("r"), trending).as_posix(), "r/data-source/market/roster-activity/sleeper/add")


class IdentityTests(unittest.TestCase):
    def index(self) -> ident.MappingIndex:
        return ident.MappingIndex([
            {"Provider": "FantasyPros", "ExternalID": "1", "CanonicalPlayerID": "NFLP-a", "FirstObservedSeason": 2024, "LastObservedSeason": 2026},
            {"Provider": "FantasyPros", "ExternalID": "2", "CanonicalPlayerID": "NFLP-b", "FirstObservedSeason": 2024, "LastObservedSeason": 2025},
            {"Provider": "FantasyPros", "ExternalID": "3", "CanonicalPlayerID": "NFLP-c", "FirstObservedSeason": 2024, "LastObservedSeason": 2026},
            {"Provider": "FantasyPros", "ExternalID": "3", "CanonicalPlayerID": "NFLP-d", "FirstObservedSeason": 2026, "LastObservedSeason": 2026},
        ])

    def test_resolution_states(self) -> None:
        index = self.index()
        resolved = ident.resolve_entry("FantasyPros", "1", "player", 2026, index)
        self.assertEqual((resolved["Status"], resolved["CanonicalPlayerID"], resolved["Method"]), ("resolved", "NFLP-a", "provider-mapping"))
        self.assertEqual(ident.resolve_entry("FantasyPros", "2", "player", 2026, index)["Status"], "unresolved")
        self.assertEqual(ident.resolve_entry("FantasyPros", "2", "player", 2025, index)["CanonicalPlayerID"], "NFLP-b")
        self.assertEqual(ident.resolve_entry("FantasyPros", "9", "player", 2026, index)["Status"], "unresolved")
        ambiguous = ident.resolve_entry("FantasyPros", "3", "player", 2026, index)
        self.assertEqual((ambiguous["Status"], ambiguous["CanonicalPlayerID"]), ("ambiguous", None))
        self.assertEqual(ident.resolve_entry("FantasyPros", "3", "player", 2025, index)["CanonicalPlayerID"], "NFLP-c")
        self.assertEqual(ident.resolve_entry("FantasyPros", "pick-1", "draft_pick", 2026, index)["Status"], "not-a-player")
        no_key = ident.resolve_entry(None, "1", "player", 2026, index)
        self.assertEqual((no_key["Status"], no_key["CanonicalPlayerID"]), ("no-provider-key", None))

    def test_build_identity_from_snapshots_is_deterministic_and_written_only_on_change(self) -> None:
        dataset = reg.get_dataset(real_registry(), "fantasycalc.value.dynasty-superflex-ppr-8-team")
        index = ident.MappingIndex([
            {"Provider": "Sleeper", "ExternalID": "100", "CanonicalPlayerID": "NFLP-a", "FirstObservedSeason": 2026, "LastObservedSeason": 2026},
        ])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot = reg.dataset_dir(root, dataset) / "snapshots" / "2026-10-01"
            snapshot.mkdir(parents=True)
            with (snapshot / "ranking.csv").open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["sleeper_id", "asset_type"])
                writer.writerows([["200", "player"], ["100", "player"], ["2027-1", "draft_pick"], ["100", "player"]])
            with patch.object(ident, "resolve_season_for_date", return_value=2026):
                built = ident.build_identity(root, dataset, index)
                self.assertEqual([e["ProviderPlayerID"] for e in built["Entries"]], ["100", "200", "2027-1"])
                self.assertEqual([e["Status"] for e in built["Entries"]], ["resolved", "unresolved", "not-a-player"])
                self.assertTrue(ident.write_if_changed(root, dataset, built))
                self.assertFalse(ident.write_if_changed(root, dataset, ident.build_identity(root, dataset, index)))

    def test_missing_identity_column_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "ranking.csv").write_text("other\n1\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                ident.snapshot_rows(Path(tmp), "sleeper_id")

    def test_dataset_without_snapshots_has_no_index(self) -> None:
        dataset = real_registry()["datasets"][0]
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(ident.build_identity(Path(tmp), dataset, self.index()))

    def test_repository_provider_mappings_load(self) -> None:
        index = ident.MappingIndex.load(REPO_ROOT)
        self.assertIsInstance(index.candidates("Sleeper", "0", 2026), list)


if __name__ == "__main__":
    unittest.main()
