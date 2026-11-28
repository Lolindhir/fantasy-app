import csv
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TOOLS = Path(__file__).resolve().parents[1]
REPO_ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

from canonical_routing import FamilyRouting, RouteMode
from data_roots import DATA_CANONICAL_ROOT, DATA_SOURCE_ROOT
from nfl_source_data_lib.combine import build_combine_files
from nfl_source_data_lib.combine_admission import plan_combine_shadow
from nfl_source_data_lib.common import (
    CANONICAL_SCHEMA_VERSION,
    Dataset,
    REGISTRY_SCHEMA_VERSION,
    load_registry,
    load_registry_manifest,
    planned_dataset_ids,
)
from nfl_source_data_lib.lifecycle import effective_partition_payload
from nfl_source_data_lib.materialize import materialize, _materialize


COMBINE_FIELDS = [
    "season", "draft_year", "draft_team", "draft_round", "draft_ovr",
    "pfr_id", "cfb_id", "player_name", "pos", "school", "ht", "wt",
    "forty", "bench", "vertical", "broad_jump", "cone", "shuttle",
]


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COMBINE_FIELDS if fields is None else fields)
        writer.writeheader()
        writer.writerows(rows)


def combine_dataset(raw_path: Path) -> Dataset:
    return Dataset(
        "nflverse.combine",
        "nflverse",
        "test",
        "https://example.invalid/combine.csv",
        raw_path,
        Path("metadata.json"),
        tuple(COMBINE_FIELDS),
        1,
        "athletic-measurement-history",
        "discover-new-partitions",
        "permanent-by-season",
        "test",
        "test",
        "immutable-history",
        "season",
        "freeze-prior-seasons",
        "explicit-force",
    )


class CombineAdmissionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.git("init", "-q")
        self.git("config", "user.name", "Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        source = self.root / DATA_SOURCE_ROOT
        registry = load_registry_manifest(REPO_ROOT)
        entry = next(item for item in registry["datasets"] if item["id"] == "nflverse.combine")
        entry = dict(entry, minimumRows=1)
        self.raw = source / entry["rawPath"]
        self.meta = source / entry["metadataPath"]
        self.rows = [
            {"season": "2024", "pfr_id": "OldPfr", "player_name": "Old"},
            {"season": "2027", "pfr_id": "NewPfr", "player_name": "New"},
        ]
        self.metadata = {
            key: entry[key] for key in ("provider", "upstream", "sourceUrl", "sourceFormat",
                                       "kind", "refreshPolicy", "retentionPolicy", "lifecycle")
        }
        self.metadata.update(dataset=entry["id"], retrievedAtUtc="2027-03-01T00:00:00Z")
        self.write_source()
        (source / "registry.json").write_text(json.dumps({
            "schemaVersion": REGISTRY_SCHEMA_VERSION, "datasets": [entry],
        }))
        self.old = self.root / DATA_CANONICAL_ROOT / "nfl/combine/2024.json"
        self.old.parent.mkdir(parents=True)
        self.old.write_text(json.dumps({"Season": 2024, "Finalized": True, "Records": []}))
        self.base = self.commit()

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.root), *args]).decode().strip()

    def commit(self):
        self.git("add", "-A")
        self.git("commit", "-qm", "fixture")
        return self.git("rev-parse", "HEAD")

    def write_source(self):
        write_csv(self.raw, self.rows)
        self.metadata.update(contentHashSha256=hashlib.sha256(self.raw.read_bytes()).hexdigest(),
                             rowCount=len(self.rows), columns=COMBINE_FIELDS)
        self.meta.write_text(json.dumps(self.metadata))

    def plan(self, approved=frozenset({2027})):
        return plan_combine_shadow(
            self.root, self.base, FamilyRouting(RouteMode.TRANSITION),
            [{"CanonicalPlayerID": "NFLP-new", "IDs": {"PFR": "NewPfr"}}], {},
            approved_new_seasons=approved,
        )

    def test_verified_new_partition_plan_is_read_only(self):
        plan = self.plan()
        self.assertEqual(frozenset({2027}), plan.new_seasons)
        self.assertEqual(self.old, plan.paths[2024])
        self.assertEqual(self.old.with_name("2027.json"), plan.paths[2027])
        self.assertEqual("NFLP-new", plan.grouped[2027][0]["CanonicalPlayerID"])
        self.assertEqual("unresolved", plan.grouped[2024][0]["IdentityResolution"]["Status"])
        self.assertFalse(plan.paths[2027].exists())
        self.assertEqual("", self.git("status", "--porcelain"))

    def test_scope_and_missing_accepted_partition_rejected(self):
        with self.assertRaisesRegex(ValueError, "exact approved shadow scope"):
            self.plan(frozenset())
        self.old.unlink()
        with self.assertRaises(FileNotFoundError):
            self.plan()
        self.assertFalse(self.old.exists())

    def test_untracked_revision_or_bad_digest_rejected(self):
        self.raw.write_bytes(self.raw.read_bytes() + b"\n")
        with self.assertRaisesRegex(ValueError, "accepted Git blob"):
            self.plan()
        self.metadata["contentHashSha256"] = "0" * 64
        self.meta.write_text(json.dumps(self.metadata))
        self.base = self.commit()
        with self.assertRaisesRegex(ValueError, "does not attest"):
            self.plan()

    def test_missing_source_coverage_and_future_season_rejected(self):
        self.rows = self.rows[1:]
        self.write_source()
        self.base = self.commit()
        with self.assertRaisesRegex(ValueError, "missing from source candidates"):
            self.plan()
        self.rows.append({"season": "2024", "pfr_id": "OldPfr"})
        self.metadata["retrievedAtUtc"] = "2026-03-01T00:00:00Z"
        self.write_source()
        self.base = self.commit()
        with self.assertRaisesRegex(ValueError, "later than the source observation"):
            self.plan()

    def test_revalidate_detects_source_race(self):
        plan = self.plan()
        self.meta.write_bytes(self.meta.read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "accepted Git blob"):
            plan.revalidate_inputs()


    def seed_full_shadow(self):
        # Exercise the actual full materializer, not mocked identities or Draft.
        source = self.root / DATA_SOURCE_ROOT
        registry = load_registry_manifest(REPO_ROOT)
        ids = {"nflverse.players", "nflverse.ff-player-ids",
               "nflverse.draft-picks", "nflverse.combine"}
        entries = [dict(item, minimumRows=1) for item in registry["datasets"]
                   if item["id"] in ids]
        (source / "registry.json").write_text(json.dumps({
            "schemaVersion": REGISTRY_SCHEMA_VERSION, "datasets": entries,
        }))
        datasets = {item.id: item for item in load_registry(self.root)}

        write_csv(datasets["nflverse.players"].raw_path, [
            {"gsis_id": "00-1", "display_name": "Old", "pfr_id": "OldPfr",
             "position": "WR"},
            {"gsis_id": "00-2", "display_name": "New", "pfr_id": "NewPfr",
             "position": "RB"},
        ], list(datasets["nflverse.players"].required_columns))
        write_csv(datasets["nflverse.ff-player-ids"].raw_path, [
            {"mfl_id": "1", "gsis_id": "00-1", "sleeper_id": "S1",
             "pfr_id": "OldPfr", "name": "Old", "draft_year": "2024",
             "draft_round": "1", "draft_pick": "1", "draft_ovr": "1"},
            {"mfl_id": "2", "gsis_id": "00-2", "sleeper_id": "S2",
             "pfr_id": "NewPfr", "name": "New", "draft_year": "2027",
             "draft_round": "1", "draft_pick": "1", "draft_ovr": "1"},
        ], list(datasets["nflverse.ff-player-ids"].required_columns))
        write_csv(datasets["nflverse.draft-picks"].raw_path, [
            {"season": "2024", "round": "1", "pick": "1", "team": "ABC",
             "gsis_id": "00-1", "pfr_player_id": "OldPfr",
             "pfr_player_name": "Old", "position": "WR"},
            {"season": "2027", "round": "1", "pick": "1", "team": "ABC",
             "gsis_id": "00-2", "pfr_player_id": "NewPfr",
             "pfr_player_name": "New", "position": "RB"},
        ], list(datasets["nflverse.draft-picks"].required_columns))
        players = self.root / "public/data/Players.json"
        players.parent.mkdir(parents=True)
        players.write_text(json.dumps([
            {"ID": "S1", "Name": "Old", "Position": "WR"},
            {"ID": "S2", "Name": "New", "Position": "RB"},
        ]))
        self.old.unlink()
        with mock.patch("nfl_source_data_lib.materialize._observation_season",
                        return_value=2027):
            materialize(self.root, datasets)
            baseline = materialize(self.root, datasets)
        self.assert_noop(baseline)
        self.base = self.commit()
        legacy = source / "nfl/combine/2024.json"
        original = legacy.read_bytes()
        legacy.rename(self.old)
        self.base = self.commit()
        self.assertEqual(original, self.old.read_bytes())
        return datasets, FamilyRouting(RouteMode.TRANSITION, frozenset({2027})), legacy

    def assert_noop(self, result):
        for key in ("identityChanged", "providerMappingsChanged", "auditChanged"):
            self.assertIs(result[key], False, key)
        for key in ("draftFilesChanged", "combineFilesChanged", "phase1FilesChanged"):
            self.assertEqual(0, result[key], key)

    def test_full_shadow_materializer_byte_parity_and_second_pass(self):
        datasets, routing, legacy = self.seed_full_shadow()
        before = self.old.read_bytes()
        with mock.patch("nfl_source_data_lib.materialize._observation_season",
                        return_value=2027):
            for _ in range(2):
                result = _materialize(self.root, datasets, shadow_commit=self.base,
                                      shadow_routing=routing)
                self.assert_noop(result)
                self.assertEqual(1, result["combinePartitionsPreserved"])
                self.assertEqual("", self.git("status", "--porcelain"))
                self.assertEqual(before, self.old.read_bytes())
                self.assertFalse(legacy.exists())

    def test_full_shadow_missing_partition_fails_before_any_write_even_force(self):
        datasets, routing, legacy = self.seed_full_shadow()
        self.old.unlink()
        before = self.git("status", "--porcelain")
        with mock.patch("nfl_source_data_lib.materialize.write_json_if_changed") as writer:
            for force in (False, True):
                with self.assertRaises(FileNotFoundError):
                    _materialize(self.root, datasets, shadow_commit=self.base,
                                 shadow_routing=routing, force=force)
            writer.assert_not_called()
        self.assertEqual(before, self.git("status", "--porcelain"))
        self.assertFalse(self.old.exists())
        self.assertFalse(legacy.exists())

    def test_full_shadow_rejects_dirty_audit_input_before_any_write(self):
        datasets, routing, _ = self.seed_full_shadow()
        players = self.root / "public/data/Players.json"
        players.write_bytes(players.read_bytes() + b" ")
        with mock.patch("nfl_source_data_lib.materialize.write_json_if_changed") as writer:
            with self.assertRaisesRegex(ValueError, "clean pinned worktree"):
                _materialize(self.root, datasets, shadow_commit=self.base,
                             shadow_routing=routing)
            writer.assert_not_called()


class RegistryCombineTests(unittest.TestCase):
    def test_repository_registry_uses_v2_lifecycle_contract(self):
        manifest = load_registry_manifest(REPO_ROOT)
        self.assertEqual(REGISTRY_SCHEMA_VERSION, manifest["schemaVersion"])
        active = {dataset.id: dataset for dataset in load_registry(REPO_ROOT)}
        self.assertEqual("immutable-history", active["nflverse.draft-picks"].lifecycle_class)
        self.assertEqual("immutable-history", active["nflverse.combine"].lifecycle_class)
        self.assertIn("nflverse.depth-charts", planned_dataset_ids(REPO_ROOT))

    def test_invalid_immutable_lifecycle_contract_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data-source").mkdir()
            registry = {
                "schemaVersion": REGISTRY_SCHEMA_VERSION,
                "datasets": [{
                    "id": "x.bad",
                    "provider": "x",
                    "upstream": "x",
                    "sourceUrl": "https://example.invalid/x.csv",
                    "rawPath": "providers/x/raw.csv",
                    "metadataPath": "providers/x/meta.json",
                    "requiredColumns": ["a"],
                    "minimumRows": 1,
                    "kind": "history",
                    "refreshPolicy": "discover-new-partitions",
                    "retentionPolicy": "permanent-by-season",
                    "lifecycle": {
                        "class": "immutable-history",
                        "partitionKey": "season",
                        "finalization": "never",
                        "repairPolicy": "normal",
                    },
                    "license": "test",
                    "attribution": "test",
                }],
            }
            (root / "data-source/registry.json").write_text(json.dumps(registry), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_registry(root)

    def test_prior_season_finalized_partition_is_preserved_without_explicit_force(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "2025.json"
            existing = {
                "SchemaVersion": CANONICAL_SCHEMA_VERSION,
                "Finalized": True,
                "Records": [{"value": "old"}],
            }
            path.write_text(json.dumps(existing), encoding="utf-8")
            dataset = combine_dataset(Path(tmp) / "combine.csv")
            candidate = {
                "SchemaVersion": CANONICAL_SCHEMA_VERSION,
                "Finalized": True,
                "Records": [{"value": "new"}],
            }

            effective, preserved = effective_partition_payload(
                dataset,
                path=path,
                candidate=candidate,
                partition_season=2025,
                observation_season=2026,
                force=False,
            )
            self.assertTrue(preserved)
            self.assertEqual(existing, effective)

            effective, preserved = effective_partition_payload(
                dataset,
                path=path,
                candidate=candidate,
                partition_season=2025,
                observation_season=2026,
                force=True,
            )
            self.assertFalse(preserved)
            self.assertEqual(candidate, effective)

    def test_frozen_legacy_partition_renames_identity_field_without_force(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "2025.json"
            path.write_text(
                json.dumps({
                    "SchemaVersion": 1,
                    "Finalized": True,
                    "Records": [{"NFLPlayerID": "NFLP-keep", "value": "old"}],
                }),
                encoding="utf-8",
            )
            dataset = combine_dataset(Path(tmp) / "combine.csv")
            candidate = {
                "SchemaVersion": CANONICAL_SCHEMA_VERSION,
                "Finalized": True,
                "Records": [{"CanonicalPlayerID": "NFLP-new", "value": "new"}],
            }

            effective, preserved = effective_partition_payload(
                dataset,
                path=path,
                candidate=candidate,
                partition_season=2025,
                observation_season=2026,
                force=False,
            )

            self.assertTrue(preserved)
            self.assertEqual(CANONICAL_SCHEMA_VERSION, effective["SchemaVersion"])
            self.assertEqual("NFLP-keep", effective["Records"][0]["CanonicalPlayerID"])
            self.assertNotIn("NFLPlayerID", effective["Records"][0])
            self.assertEqual("old", effective["Records"][0]["value"])

    def test_combine_resolves_only_pfr_and_links_canonical_draft(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "combine.csv"
            write_csv(raw, [{
                "season": "2025",
                "draft_year": "2025",
                "draft_team": "Test Team",
                "draft_round": "1",
                "draft_ovr": "5",
                "pfr_id": "PlayTe00",
                "cfb_id": "player-test",
                "player_name": "Test Player",
                "pos": "WR",
                "school": "Test U",
                "ht": "6-2",
                "wt": "205",
                "forty": "4.41",
                "bench": "12",
                "vertical": "38.5",
                "broad_jump": "124",
                "cone": "6.91",
                "shuttle": "4.12",
            }])
            canonical = [{"CanonicalPlayerID": "NFLP-1", "IDs": {"PFR": "PlayTe00"}}]
            drafts = {
                2025: {
                    "Picks": [{
                        "CanonicalPlayerID": "NFLP-1",
                        "Round": 1,
                        "PositionInRound": 5,
                        "OverallPick": 5,
                        "Team": "TT",
                    }]
                }
            }

            grouped, conflicts = build_combine_files(combine_dataset(raw), canonical, drafts)
            item = grouped[2025][0]
            self.assertEqual("NFLP-1", item["CanonicalPlayerID"])
            self.assertEqual(74, item["Measurements"]["HeightInches"])
            self.assertEqual(5, item["Draft"]["OverallPick"])
            self.assertEqual([], conflicts)

    def test_combine_links_same_canonical_player_to_each_draft_season(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "combine.csv"
            write_csv(raw, [
                {
                    "season": "1986",
                    "draft_year": "1986",
                    "draft_round": "1",
                    "draft_ovr": "1",
                    "pfr_id": "PlayTe00",
                    "player_name": "Test Player",
                },
                {
                    "season": "1987",
                    "draft_year": "1987",
                    "draft_round": "7",
                    "draft_ovr": "183",
                    "pfr_id": "PlayTe00",
                    "player_name": "Test Player",
                },
            ])
            canonical = [{"CanonicalPlayerID": "NFLP-1", "IDs": {"PFR": "PlayTe00"}}]
            drafts = {
                1986: {
                    "Picks": [{
                        "CanonicalPlayerID": "NFLP-1",
                        "Round": 1,
                        "PositionInRound": 1,
                        "OverallPick": 1,
                        "Team": "A",
                    }]
                },
                1987: {
                    "Picks": [{
                        "CanonicalPlayerID": "NFLP-1",
                        "Round": 7,
                        "PositionInRound": 15,
                        "OverallPick": 183,
                        "Team": "B",
                    }]
                },
            }

            grouped, conflicts = build_combine_files(combine_dataset(raw), canonical, drafts)
            self.assertEqual(1, grouped[1986][0]["Draft"]["OverallPick"])
            self.assertEqual(183, grouped[1987][0]["Draft"]["OverallPick"])
            self.assertEqual([], conflicts)

    def test_combine_rejects_multiple_draft_facts_for_same_player_in_one_season(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "combine.csv"
            write_csv(raw, [{
                "season": "2025",
                "pfr_id": "PlayTe00",
                "player_name": "Test Player",
            }])
            canonical = [{"CanonicalPlayerID": "NFLP-1", "IDs": {"PFR": "PlayTe00"}}]
            drafts = {
                2025: {
                    "Picks": [
                        {
                            "CanonicalPlayerID": "NFLP-1",
                            "Round": 1,
                            "PositionInRound": 5,
                            "OverallPick": 5,
                            "Team": "A",
                        },
                        {
                            "CanonicalPlayerID": "NFLP-1",
                            "Round": 2,
                            "PositionInRound": 5,
                            "OverallPick": 37,
                            "Team": "B",
                        },
                    ]
                }
            }

            with self.assertRaisesRegex(
                ValueError,
                "multiple NFL draft facts in season 2025",
            ):
                build_combine_files(combine_dataset(raw), canonical, drafts)

    def test_combine_never_name_matches_without_pfr(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "combine.csv"
            write_csv(raw, [{
                "season": "2025",
                "player_name": "Same Name",
                "pos": "RB",
            }])
            canonical = [{"CanonicalPlayerID": "NFLP-1", "Name": "Same Name", "IDs": {}}]
            grouped, _ = build_combine_files(combine_dataset(raw), canonical, {})
            self.assertIsNone(grouped[2025][0]["CanonicalPlayerID"])

    def test_combine_draft_disagreement_is_audited_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "combine.csv"
            write_csv(raw, [{
                "season": "2025",
                "draft_year": "2025",
                "draft_round": "2",
                "draft_ovr": "50",
                "pfr_id": "PlayTe00",
                "player_name": "Test Player",
            }])
            canonical = [{"CanonicalPlayerID": "NFLP-1", "IDs": {"PFR": "PlayTe00"}}]
            drafts = {
                2025: {
                    "Picks": [{
                        "CanonicalPlayerID": "NFLP-1",
                        "Round": 1,
                        "PositionInRound": 5,
                        "OverallPick": 5,
                        "Team": "TT",
                    }]
                }
            }

            grouped, conflicts = build_combine_files(combine_dataset(raw), canonical, drafts)
            self.assertEqual(5, grouped[2025][0]["Draft"]["OverallPick"])
            self.assertEqual(50, grouped[2025][0]["SourceDraftEvidence"]["OverallPick"])
            self.assertEqual(1, len(conflicts))
            self.assertEqual(
                {"combine": 50, "canonicalDraft": 5},
                conflicts[0]["Differences"]["OverallPick"],
            )


if __name__ == "__main__":
    unittest.main()
