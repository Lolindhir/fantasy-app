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
from external_source.snapshot_discovery import discover_snapshots  # noqa: E402
from external_source.snapshot_plan import (  # noqa: E402
    SnapshotCollisionError, inspect_planned_snapshot, plan_snapshot,
)

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

    def test_legacy_and_intraday_discovery_is_ordered_and_preserves_unknown_time(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "snapshots"
            legacy = root / "2026-10-01"
            legacy.mkdir(parents=True)
            (legacy / "ranking.csv").write_text("sleeper_id\n1\n", encoding="utf-8")
            for instant, hash8 in (("090000", "11111111"), ("180000", "22222222")):
                folder = legacy / f"{instant}Z-{hash8}"
                folder.mkdir(parents=True)
                (folder / "ranking.csv").write_text("sleeper_id\n1\n", encoding="utf-8")
                (folder / "metadata.json").write_text(
                    json.dumps({"fetched_at": f"2026-10-01T{instant[:2]}:{instant[2:4]}:{instant[4:]}Z"}),
                    encoding="utf-8",
                )
            found = discover_snapshots(root)
            self.assertEqual([s.key for s in found], [
                "2026-10-01", "2026-10-01/090000Z-11111111", "2026-10-01/180000Z-22222222",
            ])
            self.assertIsNone(found[0].observed_at)
            self.assertEqual(found[-1].observed_at.isoformat(), "2026-10-01T18:00:00+00:00")
            self.assertEqual(found[-1].ranking_file, legacy / "180000Z-22222222" / "ranking.csv")
            self.assertEqual(found, discover_snapshots(root))

    def test_intraday_and_legacy_identity_share_season_and_noop(self) -> None:
        dataset = reg.get_dataset(real_registry(), "fantasycalc.value.dynasty-superflex-ppr-8-team")
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            root = reg.dataset_dir(repo, dataset) / "snapshots"
            day = root / "2026-10-01"
            early = day / "110000Z-12345678"
            late = day / "170000Z-abcdef12"
            for folder, rows in (
                (day, [["100", "player"]]),
                (early, [["3", "player"], ["200", "player"]]),
                (late, [["2027-1", "draft_pick"], ["300", "player"]]),
            ):
                folder.mkdir(parents=True, exist_ok=True)
                with (folder / "ranking.csv").open("w", encoding="utf-8", newline="") as handle:
                    writer = csv.writer(handle)
                    writer.writerow(["sleeper_id", "asset_type"])
                    writer.writerows(rows)
                if folder != day:
                    (folder / "metadata.json").write_text(
                        json.dumps({"fetched_at": "2026-10-01T17:00:00+00:00"}), encoding="utf-8"
                    )
            index = ident.MappingIndex([
                {"Provider": "Sleeper", "ExternalID": "100", "CanonicalPlayerID": "c100",
                 "FirstObservedSeason": 2026, "LastObservedSeason": 2026},
                {"Provider": "Sleeper", "ExternalID": "3", "CanonicalPlayerID": "c3",
                 "FirstObservedSeason": 2026, "LastObservedSeason": 2026},
                {"Provider": "Sleeper", "ExternalID": "3", "CanonicalPlayerID": "other",
                 "FirstObservedSeason": 2026, "LastObservedSeason": 2026},
            ])
            with patch.object(ident, "resolve_season_for_date", return_value=2026) as season:
                result = ident.build_identity(repo, dataset, index)
                self.assertEqual(season.call_count, 3)
                self.assertEqual({call.args[1] for call in season.call_args_list}, {"2026-10-01"})
            statuses = {row["ProviderPlayerID"]: row["Status"] for row in result["Entries"]}
            self.assertEqual(statuses, {
                "100": "resolved", "3": "ambiguous", "200": "unresolved",
                "300": "unresolved", "2027-1": "not-a-player",
            })
            self.assertTrue(ident.write_if_changed(repo, dataset, result))
            self.assertFalse(ident.write_if_changed(repo, dataset, result))

    def test_intraday_missing_metadata_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "snapshots" / "2026-10-01" / "120000Z-12345678"
            folder.mkdir(parents=True)
            (folder / "ranking.csv").write_text("sleeper_id\n1\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "metadata missing"):
                discover_snapshots(Path(tmp) / "snapshots")

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



class SnapshotPlanTests(unittest.TestCase):
    def test_same_content_same_instant_is_identical_deterministic_plan(self) -> None:
        from datetime import datetime, timezone
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "snapshots"
            instant = datetime(2026, 10, 16, 17, 20, 3, tzinfo=timezone.utc)
            first = plan_snapshot(root, observed_at=instant, csv_content="name,Rank\\nA,1\\n", schema_version=4)
            second = plan_snapshot(root, observed_at=instant, csv_content="name,Rank\\nA,1\\n", schema_version=4)
            self.assertEqual(first, second)
            self.assertEqual(first.directory.parent.name, "2026-10-16")
            self.assertRegex(first.directory.name, r"^172003Z-[0-9a-f]{8}$")
            self.assertEqual(len(first.semantic_sha256), 64)
            self.assertEqual(inspect_planned_snapshot(first, csv_content="name,Rank\\nA,1\\n"), "absent")
            self.assertFalse(root.exists(), "Read-only planner must not create directories")

    def test_same_second_modified_content_or_schema_gets_distinct_paths(self) -> None:
        from datetime import datetime, timezone
        instant = datetime(2026, 10, 16, 17, 20, 3, tzinfo=timezone.utc)
        root = Path("snapshots")
        a = plan_snapshot(root, observed_at=instant, csv_content="name,Rank\\nA,1\\n", schema_version=4)
        b = plan_snapshot(root, observed_at=instant, csv_content="name,Rank\\nB,1\\n", schema_version=4)
        c = plan_snapshot(root, observed_at=instant, csv_content="name,Rank\\nA,1\\n", schema_version=5)
        self.assertEqual(3, len({a.key, b.key, c.key}))
        self.assertNotEqual(a.semantic_sha256, c.semantic_sha256)

    def test_timezone_is_normalized_and_naive_clock_fails(self) -> None:
        from datetime import datetime, timedelta, timezone
        utc = datetime(2026, 10, 16, 17, 20, 3, tzinfo=timezone.utc)
        cet = datetime(2026, 10, 16, 19, 20, 3, tzinfo=timezone(timedelta(hours=2)))
        a = plan_snapshot(Path("snapshots"), observed_at=utc, csv_content="a\\n", schema_version=1)
        b = plan_snapshot(Path("snapshots"), observed_at=cet, csv_content="a\\n", schema_version=1)
        self.assertEqual(a.key, b.key)
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            plan_snapshot(Path("snapshots"), observed_at=utc.replace(tzinfo=None), csv_content="a\\n", schema_version=1)
        with self.assertRaisesRegex(ValueError, "positive integer"):
            plan_snapshot(Path("snapshots"), observed_at=utc, csv_content="a\\n", schema_version=0)

    def test_existing_identical_immutable_snapshot_is_reusable_without_write(self) -> None:
        from datetime import datetime, timezone
        with tempfile.TemporaryDirectory() as tmp:
            content = "name,Rank\\nA,1\\n"
            plan = plan_snapshot(
                Path(tmp) / "snapshots",
                observed_at=datetime(2026, 10, 16, 17, 20, 3, tzinfo=timezone.utc),
                csv_content=content, schema_version=4,
            )
            plan.directory.mkdir(parents=True)
            plan.ranking_file.write_text(content, encoding="utf-8")
            plan.metadata_file.write_text(
                json.dumps({"other_source_metadata": True, **plan.metadata_identity()}),
                encoding="utf-8",
            )
            self.assertEqual("identical", inspect_planned_snapshot(plan, csv_content=content))
            self.assertEqual(content, plan.ranking_file.read_text(encoding="utf-8"))

    def test_collision_never_overwrites_wrong_or_partial_evidence(self) -> None:
        from datetime import datetime, timezone
        with tempfile.TemporaryDirectory() as tmp:
            content = "name,Rank\\nA,1\\n"
            plan = plan_snapshot(
                Path(tmp) / "snapshots",
                observed_at=datetime(2026, 10, 16, 17, 20, 3, tzinfo=timezone.utc),
                csv_content=content, schema_version=4,
            )
            plan.directory.mkdir(parents=True)
            plan.ranking_file.write_text(content, encoding="utf-8")
            with self.assertRaisesRegex(SnapshotCollisionError, "Incomplete"):
                inspect_planned_snapshot(plan, csv_content=content)
            metadata = plan.metadata_identity()
            plan.metadata_file.write_text(json.dumps(metadata), encoding="utf-8")
            plan.ranking_file.write_text(content + "B,2\\n", encoding="utf-8")
            with self.assertRaisesRegex(SnapshotCollisionError, "collision"):
                inspect_planned_snapshot(plan, csv_content=content)
            self.assertIn("B,2", plan.ranking_file.read_text(encoding="utf-8"))
            plan.ranking_file.write_text(content, encoding="utf-8")
            metadata["snapshot_semantic_sha256"] = "0" * 64
            plan.metadata_file.write_text(json.dumps(metadata), encoding="utf-8")
            with self.assertRaisesRegex(SnapshotCollisionError, "collision"):
                inspect_planned_snapshot(plan, csv_content=content)


if __name__ == "__main__":
    unittest.main()
