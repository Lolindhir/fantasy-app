import csv
import gzip
import hashlib
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

from nfl_source_data_lib import common as common_mod
import nfl_pbp_source_archive as pbp_archive
import nfl_pbp_source_auto as pbp_auto
import nfl_pbp_source_history as pbp_history
from nfl_source_data_lib.pbp_original import audit_original_pbp
import nfl_pbp_2025_quality_report as pbp_quality
import nfl_pbp_revision_readonly as pbp_revision
from nfl_source_data_lib.draft import classify_draft_status
from nfl_source_data_lib.materialize import materialize


def write_csv(path: Path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


class NflSourceDataTests(unittest.TestCase):
    def test_pbp_2025_revision_readonly_detects_compression_only_change(self):
        original_csv = b"game_id,play_id\n2025_01_ARI_NO,1\n"
        with tempfile.TemporaryDirectory() as tmp:
            accepted = Path(tmp) / "accepted.csv.gz"
            revised = Path(tmp) / "revised.csv.gz"
            accepted.write_bytes(gzip.compress(original_csv, compresslevel=1, mtime=0))
            revised.write_bytes(gzip.compress(original_csv, compresslevel=9, mtime=0))
            pinned = {
                "ARCHIVED_SHA": hashlib.sha256(accepted.read_bytes()).hexdigest(),
                "ARCHIVED_BYTES": accepted.stat().st_size,
                "PROVIDER_SHA": hashlib.sha256(revised.read_bytes()).hexdigest(),
                "PROVIDER_BYTES": revised.stat().st_size,
            }
            with patch.multiple(pbp_revision, **pinned):
                result = pbp_revision.compare_files(accepted, revised)
            self.assertTrue(result["DecompressedCSVBytesIdentical"])
            self.assertEqual(1, result["Accepted"]["SourceRows"])
            self.assertEqual(2, result["OfficialRevision"]["CSVColumns"])
            self.assertFalse(result["SemanticRowOrMetricDiffCertified"])
            self.assertFalse(result["ProductionSourceChanged"])

    def test_pbp_2025_revision_readonly_rejects_bad_gzip_crc_and_csv_width(self):
        with tempfile.TemporaryDirectory() as tmp:
            corrupted = Path(tmp) / "crc.csv.gz"
            raw = bytearray(gzip.compress(b"a,b\n1,2\n", mtime=0))
            raw[-8] ^= 1
            corrupted.write_bytes(raw)
            with self.assertRaises(OSError):
                pbp_revision.inspect_gzip(
                    corrupted, expected_sha=hashlib.sha256(raw).hexdigest(),
                    expected_bytes=len(raw),
                )
            invalid_csv = Path(tmp) / "invalid.csv.gz"
            raw_csv = gzip.compress(b"a,b\n1\n", mtime=0)
            invalid_csv.write_bytes(raw_csv)
            with self.assertRaisesRegex(ValueError, "invalid width"):
                pbp_revision.inspect_gzip(
                    invalid_csv, expected_sha=hashlib.sha256(raw_csv).hexdigest(),
                    expected_bytes=len(raw_csv),
                )

    def test_pbp_2025_revision_readonly_rejects_source_or_asset_drift(self):
        manifest = {
            "SchemaVersion": 1, "Status": "accepted-original-byte-identity",
            "Season": 2025, "UpstreamSHA256": pbp_revision.ARCHIVED_SHA,
            "CompressedBytes": pbp_revision.ARCHIVED_BYTES,
            "ArchiveAssetID": pbp_revision.ARCHIVED_ASSET_ID,
            "ArchiveURL": pbp_revision.ARCHIVED_URL,
            "SourceCompletenessCertified": False,
        }
        pbp_revision.validate_manifest(manifest)
        with self.assertRaises(ValueError):
            pbp_revision.validate_manifest({**manifest, "ArchiveURL": "https://example.invalid"})
        asset = {
            "id": pbp_revision.PROVIDER_ASSET_ID, "name": pbp_revision.BASENAME,
            "size": pbp_revision.PROVIDER_BYTES,
            "digest": "sha256:" + pbp_revision.PROVIDER_SHA,
            "state": "uploaded", "browser_download_url": pbp_revision.PROVIDER_URL,
        }
        pbp_revision.validate_release_asset(
            asset, asset_id=pbp_revision.PROVIDER_ASSET_ID,
            size=pbp_revision.PROVIDER_BYTES,
            digest=pbp_revision.PROVIDER_SHA, url=pbp_revision.PROVIDER_URL,
        )
        with self.assertRaises(ValueError):
            pbp_revision.validate_release_asset(
                {**asset, "digest": "sha256:" + "0" * 64},
                asset_id=pbp_revision.PROVIDER_ASSET_ID,
                size=pbp_revision.PROVIDER_BYTES,
                digest=pbp_revision.PROVIDER_SHA, url=pbp_revision.PROVIDER_URL,
            )

    def test_stable_internal_id_is_deterministic(self):
        self.assertEqual(
            common_mod.stable_internal_id("GSIS:00-123"),
            common_mod.stable_internal_id("GSIS:00-123"),
        )
        self.assertNotEqual(
            common_mod.stable_internal_id("GSIS:00-123"),
            common_mod.stable_internal_id("GSIS:00-124"),
        )

    def test_draft_status_does_not_treat_zero_year_as_udfa(self):
        evidence = {"NFLP-x": {"DraftYear": 0, "Round": None, "PositionInRound": None, "OverallPick": None}}
        status, _ = classify_draft_status("NFLP-x", evidence, set(), 2026)
        self.assertEqual("unknown", status)

    def test_draft_status_requires_concrete_year_for_udfa(self):
        evidence = {"NFLP-x": {"DraftYear": 2025, "Round": None, "PositionInRound": None, "OverallPick": None}}
        status, year = classify_draft_status("NFLP-x", evidence, set(), 2026)
        self.assertEqual(("undrafted", 2025), (status, year))

    def test_future_draft_year_is_not_yet_drafted(self):
        evidence = {"NFLP-x": {"DraftYear": 2027, "Round": None, "PositionInRound": None, "OverallPick": None}}
        status, year = classify_draft_status("NFLP-x", evidence, set(), 2026)
        self.assertEqual(("not_yet_drafted", 2027), (status, year))

    def test_csv_validation_fails_closed_on_missing_column(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.csv"
            write_csv(path, [{"a": "1"}], ["a"])
            with self.assertRaises(ValueError):
                common_mod.inspect_csv(path, ["a", "b"], 1)

    def test_end_to_end_materialization_uses_identity_bridge_and_draft_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data-source").mkdir(parents=True)
            registry = {
                "schemaVersion": 1,
                "datasets": [
                    {
                        "id": "nflverse.players", "provider": "nflverse", "upstream": "test",
                        "sourceUrl": "https://example.invalid/players.csv", "sourceFormat": "csv",
                        "rawPath": "providers/nflverse/players/raw-latest.csv",
                        "metadataPath": "providers/nflverse/players/metadata.json",
                        "requiredColumns": ["gsis_id", "display_name", "pfr_id", "position"],
                        "minimumRows": 1, "kind": "identity", "refreshPolicy": "periodic",
                        "retentionPolicy": "latest", "license": "test", "attribution": "test"
                    },
                    {
                        "id": "nflverse.ff-player-ids", "provider": "ffverse", "upstream": "test",
                        "sourceUrl": "https://example.invalid/ids.csv", "sourceFormat": "csv",
                        "rawPath": "providers/nflverse/ff-player-ids/raw-latest.csv",
                        "metadataPath": "providers/nflverse/ff-player-ids/metadata.json",
                        "requiredColumns": ["mfl_id", "gsis_id", "sleeper_id", "espn_id", "pfr_id", "name", "draft_year", "draft_round", "draft_pick", "draft_ovr"],
                        "minimumRows": 1, "kind": "identity-mapping", "refreshPolicy": "periodic",
                        "retentionPolicy": "latest", "license": "test", "attribution": "test"
                    },
                    {
                        "id": "nflverse.draft-picks", "provider": "nflverse", "upstream": "test",
                        "sourceUrl": "https://example.invalid/draft.csv", "sourceFormat": "csv",
                        "rawPath": "providers/nflverse/draft-picks/raw-latest.csv",
                        "metadataPath": "providers/nflverse/draft-picks/metadata.json",
                        "requiredColumns": ["season", "round", "pick", "team", "gsis_id", "pfr_player_id", "pfr_player_name", "position"],
                        "minimumRows": 1, "kind": "historical-event", "refreshPolicy": "periodic",
                        "retentionPolicy": "permanent", "license": "test", "attribution": "test"
                    }
                ]
            }
            (root / "data-source/registry.json").write_text(json.dumps(registry), encoding="utf-8")
            write_csv(
                root / "data-source/providers/nflverse/players/raw-latest.csv",
                [
                    {"gsis_id": "00-1", "display_name": "Drafted Player", "pfr_id": "DrafPl00", "position": "WR", "espn_id": "111", "nfl_id": "41405", "birth_date": "2000-01-01"},
                    {"gsis_id": "00-2", "display_name": "Undrafted Player", "pfr_id": "UndrPl00", "position": "RB", "espn_id": "22", "birth_date": "2001-01-01"},
                ],
                ["gsis_id", "display_name", "pfr_id", "position", "espn_id", "nfl_id", "birth_date"]
            )
            write_csv(
                root / "data-source/providers/nflverse/ff-player-ids/raw-latest.csv",
                [
                    {"mfl_id": "1", "gsis_id": "00-1", "sleeper_id": "S1", "espn_id": "11", "pfr_id": "DrafPl00", "nfl_id": "2543774", "cbs_id": "shared-cbs", "name": "Drafted Player", "birthdate": "2000-01-01", "position": "WR", "draft_year": "2025", "draft_round": "2", "draft_pick": "5", "draft_ovr": "37"},
                    {"mfl_id": "2", "gsis_id": "00-2", "sleeper_id": "S2", "espn_id": "22", "pfr_id": "UndrPl00", "cbs_id": "shared-cbs", "name": "Undrafted Player", "birthdate": "2001-01-01", "position": "RB", "draft_year": "2025", "draft_round": "", "draft_pick": "", "draft_ovr": ""},
                    {"mfl_id": "99", "gsis_id": "00-1", "sleeper_id": "S1", "espn_id": "11", "pfr_id": "DrafPl00", "nfl_id": "2543774", "name": "Legacy Homonym", "birthdate": "1970-01-01", "position": "DL", "draft_year": "1990", "draft_round": "1", "draft_pick": "10", "draft_ovr": "10"},
                ],
                ["mfl_id", "gsis_id", "sleeper_id", "espn_id", "pfr_id", "nfl_id", "cbs_id", "name", "birthdate", "position", "draft_year", "draft_round", "draft_pick", "draft_ovr"]
            )
            write_csv(
                root / "data-source/providers/nflverse/draft-picks/raw-latest.csv",
                [{"season": "2025", "round": "2", "pick": "37", "team": "ABC", "gsis_id": "00-1", "pfr_player_id": "DrafPl00", "pfr_player_name": "Drafted Player", "position": "WR"}],
                ["season", "round", "pick", "team", "gsis_id", "pfr_player_id", "pfr_player_name", "position"]
            )
            (root / "public/data").mkdir(parents=True)
            # public/data/Players.json is a consumer output and no identity evidence (#347 H1a).
            players = [
                {"ID": "S1", "TankID": "T1", "Name": "Drafted Player", "Position": "WR"},
                {"ID": "S2", "TankID": "T2", "Name": "Undrafted Player", "Position": "RB"},
            ]
            (root / "public/data/Players.json").write_text(json.dumps(players), encoding="utf-8")

            datasets = {d.id: d for d in common_mod.load_registry(root)}
            result = materialize(root, datasets)

            self.assertEqual(3, result["identityCount"])
            self.assertEqual(1, result["identitySourceMappingConflictCount"])
            self.assertEqual(1, result["audit"]["identitySourceMappingConflictCount"])
            self.assertEqual(1, result["audit"]["identityAliasCount"])
            self.assertEqual({"ESPN": 1}, result["audit"]["identityAliasesByProvider"])
            self.assertEqual(1, result["audit"]["identityWeakProviderCollisionCount"])
            self.assertEqual({"CBS": ["shared-cbs"]}, result["audit"]["identityWeakProviderCollisions"])
            self.assertEqual({"drafted": 1, "undrafted": 1}, result["audit"]["draftStatusCoverage"])
            conflict = result["audit"]["identitySourceMappingConflicts"][0]
            self.assertEqual("99", conflict["MFLID"])
            self.assertEqual("birthdate_conflict_with_nflverse_players", conflict["Reason"])
            self.assertIn("Sleeper", conflict["SuppressedIDs"])

            canonical = json.loads((root / "data-source/nfl/identities/players.json").read_text())
            self.assertEqual(common_mod.CANONICAL_SCHEMA_VERSION, canonical["SchemaVersion"])
            self.assertEqual("CanonicalPlayerID", canonical["IdentityPolicy"]["InternalKey"])
            self.assertEqual("fantasy-app", canonical["IdentityPolicy"]["CanonicalPlayerIDNamespace"])
            self.assertTrue(canonical["IdentityPolicy"]["CanonicalPlayerIDIsApplicationDefined"])
            by_sleeper = {row["IDs"]["Sleeper"]: row for row in canonical["Players"] if row["IDs"].get("Sleeper")}
            self.assertNotIn("Tank01", by_sleeper["S1"]["IDs"])
            self.assertEqual("41405", by_sleeper["S1"]["IDs"]["NFL"])
            self.assertEqual("2543774", by_sleeper["S1"]["IDs"]["NFLCom"])
            self.assertEqual("11", by_sleeper["S1"]["IDs"]["ESPN"])
            self.assertEqual(["111"], by_sleeper["S1"]["IDAliases"]["ESPN"])
            self.assertEqual("shared-cbs", by_sleeper["S1"]["IDs"]["CBS"])
            self.assertEqual("shared-cbs", by_sleeper["S2"]["IDs"]["CBS"])
            quarantined = next(row for row in canonical["Players"] if row["IDs"].get("MFL") == "99")
            self.assertNotIn("Sleeper", quarantined["IDs"])
            self.assertNotIn("GSIS", quarantined["IDs"])
            self.assertTrue(all("CanonicalPlayerID" in row for row in canonical["Players"]))
            self.assertTrue(all("NFLPlayerID" not in row for row in canonical["Players"]))

            draft = json.loads((root / "data-source/nfl/draft/2025.json").read_text())
            self.assertEqual(by_sleeper["S1"]["CanonicalPlayerID"], draft["Picks"][0]["CanonicalPlayerID"])
            self.assertNotIn("NFLPlayerID", draft["Picks"][0])
            self.assertEqual(1, draft["Picks"][0]["PositionInRound"])

            second = materialize(root, datasets)
            self.assertFalse(second["identityChanged"])
            self.assertFalse(second["providerMappingsChanged"])
            self.assertEqual(0, second["draftFilesChanged"])
            self.assertFalse(second["auditChanged"])

    def test_write_json_if_changed_avoids_timestampless_churn(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.json"
            self.assertTrue(common_mod.write_json_if_changed(path, {"a": 1}))
            self.assertFalse(common_mod.write_json_if_changed(path, {"a": 1}))


class NflPbpArchiveSourcePilotTests(unittest.TestCase):
    """Existing registered NFL Source Fast test module; never touches network."""

    def _asset(self, *, digest=None):
        return {
            "id": 987,
            "name": pbp_archive.ARCHIVE_NAME,
            "size": pbp_archive.EXPECTED_SIZE,
            "digest": digest or "sha256:" + pbp_archive.EXPECTED_SHA256,
            "state": "uploaded",
            "browser_download_url": "https://github.com/Lolindhir/fantasy-app/releases/download/test/pbp.gz",
        }

    def _upstream(self, *, digest=None):
        return {
            "id": pbp_archive.UPSTREAM_ASSET_ID,
            "name": pbp_archive.ARCHIVE_NAME,
            "digest": digest or "sha256:" + pbp_archive.EXPECTED_SHA256,
            "size": pbp_archive.EXPECTED_SIZE,
            "browser_download_url": pbp_archive.SOURCE_URL,
        }

    def test_2025_initial_archive_then_noop_without_downloading_or_git_gzip(self):
        import hashlib
        original = b"pinned-2025-original-bytes-test"
        expected = hashlib.sha256(original).hexdigest()
        release = {"upload_url": (
            "https://uploads.github.com/repos/Lolindhir/fantasy-app/"
            "releases/123/assets{?name,label}"
        ), "assets": []}
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(pbp_archive, "EXPECTED_SHA256", expected), \
             patch.object(pbp_archive, "EXPECTED_SIZE", len(original)), \
             patch.object(pbp_archive, "upstream_evidence", return_value={
                 "digest": "sha256:" + expected,
                 "size": len(original),
             }), \
             patch.object(pbp_archive, "read_only_audits", return_value={
                 "SourceRowCount": 100,
                 "PBPMetricValidationStatus": "research-only-not-certified-full-source",
             }) as audit, \
             patch.object(pbp_archive, "download") as download, \
             patch.object(pbp_archive, "get_release", side_effect=[
                 None, {"assets": [dict(self._asset(), size=len(original),
                                         digest="sha256:" + expected)]}
             ]) as get_release, \
             patch.object(pbp_archive, "create_release", return_value=release), \
             patch.object(pbp_archive, "upload_asset", return_value=dict(
                 self._asset(), size=len(original), digest="sha256:" + expected,
             )) as upload:
            download.side_effect = lambda url, path: path.write_bytes(original)
            root = Path(tmp)
            first = pbp_archive.run(root, "Lolindhir/fantasy-app", "test-token", weekday=1)
            self.assertEqual(first["Status"], "original-archived-audited")
            self.assertTrue(first["Changed"])
            manifest = json.loads((root / pbp_archive.MANIFEST_PATH).read_text())
            self.assertEqual(manifest["UpstreamSHA256"], expected)
            self.assertFalse(manifest["SourceCompletenessCertified"])
            self.assertFalse(manifest["GameDetailV2Published"])
            self.assertFalse(list(root.rglob("*.gz")))
            second = pbp_archive.run(root, "Lolindhir/fantasy-app", "test-token", weekday=1)
            self.assertEqual(second, {"Status": "already-archived-verified-noop",
                                      "Changed": False})
            self.assertEqual(download.call_count, 1)
            self.assertEqual(get_release.call_count, 2)
            audit.assert_called_once()
            upload.assert_called_once()

    def test_wrong_upstream_digest_fails_before_download_or_publication(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(pbp_archive, "upstream_evidence",
                          return_value=self._upstream(digest="sha256:" + "0" * 64)), \
             patch.object(pbp_archive, "download") as download, \
             patch.object(pbp_archive, "create_release") as release:
            with self.assertRaisesRegex(ValueError, "separate repair review"):
                pbp_archive.run(Path(tmp), "Lolindhir/fantasy-app", "test-token")
            download.assert_not_called()
            release.assert_not_called()
            self.assertFalse((Path(tmp) / pbp_archive.MANIFEST_PATH).exists())

    def test_missing_archived_asset_fails_closed_without_source_replacement(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(pbp_archive, "get_release", return_value=None), \
             patch.object(pbp_archive, "download") as download:
            path = Path(tmp) / pbp_archive.MANIFEST_PATH
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({
                "Status": "accepted-original-byte-identity",
                "UpstreamSHA256": pbp_archive.EXPECTED_SHA256,
                "ReleaseTag": pbp_archive.ARCHIVE_TAG,
            }))
            with self.assertRaisesRegex(ValueError, "missing release asset"):
                pbp_archive.run(Path(tmp), "Lolindhir/fantasy-app", "test-token", weekday=1)
            download.assert_not_called()

    def test_weekly_upstream_drift_reports_review_without_rewriting_frozen_source(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(pbp_archive, "get_release", return_value={
                 "assets": [self._asset()]
             }), \
             patch.object(pbp_archive, "upstream_evidence", return_value=self._upstream(
                 digest="sha256:" + "0" * 64,
             )), \
             patch.object(pbp_archive, "download") as download:
            path = Path(tmp) / pbp_archive.MANIFEST_PATH
            path.parent.mkdir(parents=True)
            original = {
                "Status": "accepted-original-byte-identity",
                "UpstreamSHA256": pbp_archive.EXPECTED_SHA256,
                "ReleaseTag": pbp_archive.ARCHIVE_TAG,
            }
            path.write_text(json.dumps(original))
            result = pbp_archive.run(
                Path(tmp), "Lolindhir/fantasy-app", "test-token", weekday=0,
            )
            self.assertEqual(result, {"Status": "upstream-revision-review-required",
                                      "Changed": False})
            self.assertEqual(json.loads(path.read_text()), original)
            download.assert_not_called()

    def test_downloaded_bytes_must_match_pinned_sha_even_with_matching_size(self):
        import hashlib
        expected = b"authentic-asset"
        corrupted = b"corrupted-asset"
        self.assertEqual(len(expected), len(corrupted))
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(pbp_archive, "EXPECTED_SIZE", len(expected)), \
             patch.object(pbp_archive, "EXPECTED_SHA256", hashlib.sha256(expected).hexdigest()), \
             patch.object(pbp_archive, "upstream_evidence", return_value={
                 "digest": "sha256:" + hashlib.sha256(expected).hexdigest(),
                 "size": len(expected),
             }), \
             patch.object(pbp_archive, "download",
                          side_effect=lambda _url, path: path.write_bytes(corrupted)), \
             patch.object(pbp_archive, "read_only_audits") as audit, \
             patch.object(pbp_archive, "create_release") as release:
            with self.assertRaisesRegex(ValueError, "does not match official SHA256"):
                pbp_archive.run(Path(tmp), "Lolindhir/fantasy-app", "test-token")
            audit.assert_not_called()
            release.assert_not_called()

    def test_source_workflow_restricts_pilot_to_unfiltered_full_and_isolates_failure(self):
        workflow = (TOOLS.parent / ".github/workflows/sync-nfl-source-data.yml").read_text()
        self.assertIn(
            'if [[ "$materialization_scope" == "full" && -z "${DATASET:-}" && -z "${SEASON:-}" ]]; then',
            workflow,
        )
        self.assertIn("PBP_ARCHIVE_TOKEN: ${{ github.token }}", workflow)
        self.assertIn("tools/nfl_pbp_source_auto.py", workflow)
        self.assertIn("Original PBP archive blocked:", workflow)
        self.assertIn("git add -- data-source/providers", workflow)

    def test_archive_asset_hash_mismatch_is_never_an_accepted_noop(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(pbp_archive, "get_release", return_value={
                 "assets": [self._asset(digest="sha256:" + "0" * 64)]
             }):
            path = Path(tmp) / pbp_archive.MANIFEST_PATH
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({
                "Status": "accepted-original-byte-identity",
                "UpstreamSHA256": pbp_archive.EXPECTED_SHA256,
                "ReleaseTag": pbp_archive.ARCHIVE_TAG,
            }))
            with self.assertRaisesRegex(ValueError, "digest/size/status mismatch"):
                pbp_archive.run(Path(tmp), "Lolindhir/fantasy-app", "test-token", weekday=1)



class NflPbpHistoricalFranchiseSourceAuditTests(unittest.TestCase):
    """Original PBP may use modern franchise tokens against era-specific GameIDs."""

    def test_source_aliases_are_symmetric_only_within_historical_windows(self):
        from nfl_source_data_lib.pbp_original import _team_matches

        for season in (2017, 2018, 2019):
            with self.subTest(season=season, franchise="OAK/LV"):
                self.assertTrue(_team_matches("LV", "OAK", season))
                self.assertTrue(_team_matches("OAK", "LV", season))
        self.assertTrue(_team_matches("LAC", "SD", 2016))
        self.assertTrue(_team_matches("SD", "LAC", 2016))
        self.assertTrue(_team_matches("LA", "STL", 2015))
        self.assertTrue(_team_matches("STL", "LA", 2015))
        for observed, canonical, season in (
            ("LV", "OAK", 2020), ("OAK", "LV", 2020),
            ("LAC", "SD", 2017), ("SD", "LAC", 2017),
            ("LA", "STL", 2016), ("STL", "LA", 2016),
            ("LV", "SD", 2016), ("LAC", "OAK", 2019),
            ("UNKNOWN", "OAK", 2018),
        ):
            with self.subTest(observed=observed, canonical=canonical, season=season):
                self.assertFalse(_team_matches(observed, canonical, season))

    def test_historical_game_id_with_modern_pbp_team_tokens_passes_full_source_audit(self):
        from io import BytesIO

        for season, game_id, away, home, pbp_away, pbp_home in (
            (2019, "2019_01_DEN_OAK", "DEN", "OAK", "DEN", "LV"),
            (2018, "2018_01_LA_OAK", "LA", "OAK", "LA", "LV"),
            (2017, "2017_01_OAK_TEN", "OAK", "TEN", "LV", "TEN"),
            (2016, "2016_01_SD_KC", "SD", "KC", "LAC", "KC"),
            (2015, "2015_01_STL_SEA", "STL", "SEA", "LA", "SEA"),
        ):
            with self.subTest(season=season), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                schedule = root / f"data-source/nfl/schedules/{season}.json"
                schedule.parent.mkdir(parents=True)
                schedule.write_text(json.dumps({
                    "SchemaVersion": 2,
                    "SourceDataset": "nflverse.schedules",
                    "Season": season,
                    "Games": [{
                        "GameID": game_id, "Week": 1, "GameType": "REG",
                        "AwayTeam": away, "HomeTeam": home,
                    }],
                }))
                compressed = BytesIO()
                with gzip.open(compressed, "wt", encoding="utf-8", newline="") as out:
                    writer = csv.DictWriter(out, fieldnames=[
                        "game_id", "play_id", "season", "week", "season_type",
                        "away_team", "home_team", "posteam", "defteam", "play_type",
                    ])
                    writer.writeheader()
                    writer.writerow({
                        "game_id": game_id, "play_id": "1", "season": str(season),
                        "week": "1", "season_type": "REG",
                        "away_team": pbp_away, "home_team": pbp_home,
                        "posteam": pbp_away, "defteam": pbp_home, "play_type": "run",
                    })
                path = root / "original.csv.gz"
                payload = compressed.getvalue()
                path.write_bytes(payload)
                audit = audit_original_pbp(
                    root, season, path, hashlib.sha256(payload).hexdigest(),
                )
                self.assertEqual(audit["SourceRowCount"], 1)
                self.assertEqual(audit["ObservedGameIDs"], 1)
                self.assertEqual(audit["UnmatchedCanonicalGameRows"], 0)

class NflPbpCurrentSourceTests(unittest.TestCase):
    """Mocked regression of real Source boundaries; no network or binary commits."""

    def _official(self, season, data):
        import hashlib
        return {
            "id": 42, "name": f"play_by_play_{season}.csv.gz",
            "size": len(data), "digest": "sha256:" + hashlib.sha256(data).hexdigest(),
            "state": "uploaded", "updated_at": "2026-11-18T19:00:00Z",
            "browser_download_url": (
                "https://github.com/nflverse/nflverse-data/releases/download/"
                f"pbp/play_by_play_{season}.csv.gz"
            ),
        }

    def _archived(self, season, data):
        import hashlib
        sha = hashlib.sha256(data).hexdigest()
        return {
            "id": 62, "name": f"play_by_play_{season}.csv.gz",
            "size": len(data), "digest": "sha256:" + sha,
            "state": "uploaded",
            "browser_download_url": pbp_auto._archive_url(season, sha),
        }

    def test_current_source_accepts_new_revisions_without_overwriting_old_bytes(self):
        import hashlib
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first, second = b"2026-source-snapshot-a", b"2026-source-snapshot-b"
            versions = [first, second, second]
            saved = {}
            def release(_token, season, sha):
                return {"assets": [saved[sha]]} if sha in saved else None
            def upload(_token, _release, path, season, sha, size):
                data = path.read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(), sha)
                asset = self._archived(season, data)
                saved[sha] = asset
                return asset
            def download(_url, target):
                target.write_bytes(versions[len(saved)])
            def audit(_root, _season, _file, _digest):
                return {"SourceRowCount": 100, "ObservedGameIDs": 1,
                        "OriginalColumnCount": 372, "PBPMetricCandidateCount": 17,
                        "PBPMetricMVPCount": 10}
            upstream = [self._official(2026, data) for data in versions]
            with patch.object(pbp_auto, "current_source_season", return_value=2026), \
                 patch.object(pbp_auto, "upstream_asset", side_effect=upstream), \
                 patch.object(pbp_auto, "_get_release", side_effect=release), \
                 patch.object(pbp_auto, "_create_release",
                              return_value={"upload_url": "https://uploads.github.com/repos/Lolindhir/fantasy-app/releases/111/assets{?name,label}"}), \
                 patch.object(pbp_auto, "_upload", side_effect=upload), \
                 patch.object(pbp_auto, "download", side_effect=download), \
                 patch.object(pbp_auto, "_audit", side_effect=audit):
                one = pbp_auto.run(root, "Lolindhir/fantasy-app", "token")
                self.assertEqual(one["SnapshotRevision"], 1)
                metadata = root / "data-source/providers/nflverse/play-by-play-original/metadata-2026.json"
                self.assertFalse(list(root.rglob("*.gz")))
                old = json.loads(metadata.read_text())
                two = pbp_auto.run(root, "Lolindhir/fantasy-app", "token")
                self.assertEqual(two["SnapshotRevision"], 2)
                current = json.loads(metadata.read_text())
                self.assertEqual(current["PreviousAcceptedSHA256"], old["UpstreamSHA256"])
                self.assertNotEqual(current["UpstreamSHA256"], old["UpstreamSHA256"])
                self.assertEqual(len(saved), 2)
                stable = metadata.read_bytes()
                third = pbp_auto.run(root, "Lolindhir/fantasy-app", "token")
                self.assertEqual(third["Status"], "original-current-noop")
                self.assertEqual(metadata.read_bytes(), stable)

    @staticmethod
    def _identity_schedule(root):
        path = root / "data-source/nfl/schedules/2026.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "SchemaVersion": 2, "Season": 2026,
            "SourceDataset": "nflverse.schedules",
            "Games": [
                {"GameID": "2026_01_ARI_LAC", "GameType": "REG",
                 "Week": 1, "AwayTeam": "ARI", "HomeTeam": "LAC"},
                {"GameID": "2026_18_ARI_LAC", "GameType": "REG",
                 "Week": 18, "AwayTeam": "ARI", "HomeTeam": "LAC"},
            ],
        }), encoding="utf-8")

    @staticmethod
    def _identity_original(rows):
        import io
        stream = io.BytesIO()
        with gzip.open(stream, "wt", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=[
                "game_id", "play_id", "season", "week", "season_type",
                "away_team", "home_team", "posteam", "defteam", "play_type",
                "epa", "pass_attempt",
            ])
            writer.writeheader()
            for row in rows:
                writer.writerow({
                    "game_id": "2026_01_ARI_LAC", "play_id": "1",
                    "season": "2026", "week": "1", "season_type": "REG",
                    "away_team": "ARI", "home_team": "LAC",
                    "posteam": "ARI", "defteam": "LAC",
                    "play_type": "pass", "epa": "0.25", "pass_attempt": "1",
                    **row,
                })
        return stream.getvalue()

    def test_real_source_intake_accepts_active_partial_season_without_derived_or_future_stats(self):
        """A W18 schedule must not require W18 PlayerStats or Derived games."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._identity_schedule(root)
            data = self._identity_original([{}, {"play_id": "2"}])
            official = self._official(2026, data)
            def download(_url, target):
                target.write_bytes(data)
            def upload(_token, _release, _file, season, _sha, _size):
                return self._archived(season, data)
            with patch.object(pbp_auto, "current_source_season", return_value=2026), \
                 patch.object(pbp_auto, "upstream_asset", return_value=official), \
                 patch.object(pbp_auto, "download", side_effect=download), \
                 patch.object(pbp_auto, "_get_release", return_value=None), \
                 patch.object(pbp_auto, "_create_release", return_value={
                     "upload_url": "https://uploads.github.com/repos/Lolindhir/fantasy-app/releases/111/assets{?name,label}"
                 }), \
                 patch.object(pbp_auto, "_upload", side_effect=upload):
                result = pbp_auto.run(root, "Lolindhir/fantasy-app", "token")
            self.assertEqual(result["Status"], "original-current-accepted")
            manifest = json.loads((root / (
                "data-source/providers/nflverse/play-by-play-original/metadata-2026.json"
            )).read_text())
            self.assertEqual(manifest["Audit"]["SourceRowCount"], 2)
            self.assertEqual(manifest["Audit"]["ObservedGameIDs"], 1)
            self.assertEqual(manifest["Audit"]["UnmatchedCanonicalGameRows"], 0)
            self.assertEqual(
                manifest["Audit"]["SourceValidationStatus"],
                "original-byte-and-source-game-identity-accepted",
            )
            self.assertFalse(manifest["SourceCompletenessCertified"])
            self.assertNotIn("PBPMetricMVPCount", manifest["Audit"])
            self.assertFalse((root / "data-derived").exists())
            self.assertFalse((root / "data-source/nfl/player-stats").exists())

    def test_original_source_identity_rejects_unknown_game_context_and_duplicate_play(self):
        cases = (
            ([{"game_id": "2026_02_ARI_LAC"}], "unknown Source GameID"),
            ([{"week": "18"}], "mismatched Source week"),
            ([{"season": "2025"}], "wrong season"),
            ([{"home_team": "SEA"}], "mismatched Source teams"),
            ([{"play_id": "1"}, {"play_id": "1"}], "Duplicate original PBP GameID/PlayID"),
        )
        for rows, error in cases:
            with self.subTest(error=error), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                self._identity_schedule(root)
                path = root / "original.csv.gz"
                data = self._identity_original(rows)
                path.write_bytes(data)
                with self.assertRaisesRegex(ValueError, error):
                    audit_original_pbp(
                        root, 2026, path, hashlib.sha256(data).hexdigest(),
                    )

    def test_original_source_identity_rejects_malformed_bytes_before_archive(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._identity_schedule(root)
            path = root / "original.csv.gz"
            path.write_bytes(b"not gzip")
            with self.assertRaises(OSError):
                audit_original_pbp(
                    root, 2026, path, hashlib.sha256(b"not gzip").hexdigest(),
                )
            valid = self._identity_original([{}])
            path.write_bytes(valid)
            with self.assertRaisesRegex(ValueError, "pinned SHA256"):
                audit_original_pbp(root, 2026, path, "0" * 64)

    def test_source_digest_mismatch_fails_before_any_release_or_manifest(self):
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(pbp_auto, "current_source_season", return_value=2026), \
             patch.object(pbp_auto, "upstream_asset",
                          return_value=self._official(2026, b"original")), \
             patch.object(pbp_auto, "download",
                          side_effect=lambda _url, path: path.write_bytes(b"forged!!")), \
             patch.object(pbp_auto, "_create_release") as release:
            with self.assertRaisesRegex(ValueError, "official asset SHA256/size"):
                pbp_auto.run(Path(temp), "Lolindhir/fantasy-app", "token")
            release.assert_not_called()
            self.assertFalse(list(Path(temp).rglob("metadata-*.json")))

    def test_frozen_season_does_not_enter_live_source_writes(self):
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(pbp_auto, "current_source_season", return_value=2026), \
             patch.object(pbp_auto, "upstream_asset") as upstream:
            with self.assertRaisesRegex(ValueError, "current Source season only"):
                pbp_auto.run(Path(temp), "Lolindhir/fantasy-app", "token", season=2025)
            upstream.assert_not_called()

    def test_existing_source_missing_archive_blocks_before_upstream(self):
        import hashlib
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(pbp_auto, "current_source_season", return_value=2026), \
             patch.object(pbp_auto, "_get_release", return_value=None), \
             patch.object(pbp_auto, "upstream_asset") as upstream:
            root = Path(temp)
            sha = hashlib.sha256(b"previous").hexdigest()
            path = root / "data-source/providers/nflverse/play-by-play-original/metadata-2026.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            previous = {"Status": "accepted-original-byte-identity", "Season": 2026,
                        "UpstreamSHA256": sha, "CompressedBytes": 8,
                        "ArchiveURL": pbp_auto._archive_url(2026, sha)}
            path.write_text(json.dumps(previous))
            with self.assertRaisesRegex(ValueError, "archive is missing"):
                pbp_auto.run(root, "Lolindhir/fantasy-app", "token")
            self.assertEqual(json.loads(path.read_text()), previous)
            upstream.assert_not_called()

    def test_missing_source_stays_unknown_and_unsupported_digest_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(pbp_auto, "current_source_season", return_value=2026), \
             patch.object(pbp_auto, "upstream_asset", return_value=None):
            result = pbp_auto.run(Path(temp), "Lolindhir/fantasy-app", "token")
            self.assertEqual(result["Status"], "upstream-season-not-released")
            self.assertFalse(result["Changed"])
        with patch.object(pbp_auto, "api_json", side_effect=[
            {"id": 1234}, [dict(self._official(2026, b"original"), digest=None)],
        ]):
            with self.assertRaisesRegex(ValueError, "trusted identity/SHA256"):
                pbp_auto.upstream_asset("token", 2026)

    def test_official_inventory_lookup_is_dynamic(self):
        older = self._official(2025, b"old")
        current = self._official(2026, b"current")
        with patch.object(pbp_auto, "api_json", side_effect=[
            {"id": 1234}, [older, current],
        ]) as request:
            self.assertEqual(pbp_auto.upstream_asset("token", 2026), current)
            self.assertEqual(request.call_count, 2)



class NflPbpOriginalResearchReportTests(unittest.TestCase):
    def test_research_report_retains_exact_ten_metrics_and_missing_denominators(self):
        ids = pbp_quality.MVP_METRICS
        fields = {
            "play_type": {
                "HeaderPresent": True,
                "Cohorts": {name: {"Rows": 10, "NonNull": 7, "Missing": 3}
                            for name in ("AllRows", "PassPlayType",
                                         "RunPlayType", "QBDropback")},
            }
        }
        field = {
            "SourceAssetSHA256": "a" * 64,
            "SourceAssetCompressedBytes": 19,
            "RawSeasonRowCount": 10,
            "CsvColumnCount": 372,
            "DistinctGameIDs": 1,
            "GameRowCounts": [{"GameID": "2025_01_XXX_YYY", "RowCount": 10}],
            "CanonicalGameContextReconciliation": {
                "ExactContextRows": 10, "HistoricalAliasContextRows": 0,
                "UnknownGameIDRows": 0, "MismatchedContextRows": 0,
                "MatchedNonFinalGameRows": 0,
            },
            "MetricFieldCoverage": [{"MetricID": metric,
                                     "Status": "fields-observed-in-gzip-unverified-eligibility-and-completeness"}
                                    for metric in ids],
            "FieldCoverage": fields,
            "CohortRowCounts": {"AllRows": 10},
            "MonitoredFieldsAbsent": [],
            "BinaryFieldInvalidCounts": {},
            "DictionarySemanticCrosschecks": {},
            "ArchivedProjectionComparison": None,
        }
        evidence = {
            "ObservedTeamGames": 2, "MissingTeamGames": 0,
            "UnknownFlagRows": 3, "UnknownFlagTeamGames": 1,
            "EligibleOutcomeRows": 5, "ObservedOutcomeRows": 4,
            "MissingOutcomeRows": 1, "ZeroOutcomeDenominatorTeamGames": 0,
            "ObservedDenominator": 4, "ObservedWeightedMeanApprox": 0.375,
            "MinGameValue": 0.25, "MaxGameValue": 0.5,
        }
        metrics = {
            "PBPAssetSHA256": "a" * 64,
            "CanonicalGames": 1,
            "MissingOriginalGameIDs": [],
            "GameTeamCandidateRows": 2,
            "EligibleScrimmagePlays": 5,
            "TeamMetricResearchCoverage": {metric: evidence for metric in ids},
            "PlayerStatsBaseline": {"Rows": 2},
            "Reconciliation": {},
        }
        with patch.object(pbp_quality, "_catalog", return_value=(
            [{"MetricID": metric, "Fields": ["play_type"]} for metric in ids], set()
        )):
            result = pbp_quality.summarize(field, metrics)
        self.assertEqual(len(result["MVPMetricEvidence"]), 10)
        self.assertFalse(result["ProductionReady"])
        self.assertEqual(result["GameTeamCandidates"], 2)
        self.assertEqual(result["MVPMetricEvidence"][0]["UnknownEligibilityFlagRows"], 3)
        self.assertEqual(result["MVPMetricEvidence"][0]["MissingOutcomeRows"], 1)
        self.assertEqual(result["MVPMetricEvidence"][0]["Fields"][0]["NonNullRate"], 0.7)

    def test_missing_mvp_metric_fails_closed(self):
        with patch.object(pbp_quality, "_catalog", return_value=([], set())):
            with self.assertRaisesRegex(ValueError, "ten approved MVP metrics"):
                pbp_quality.summarize(
                    {"MetricFieldCoverage": [], "SourceAssetSHA256": "a"}, {
                        "TeamMetricResearchCoverage": {}, "PBPAssetSHA256": "a"
                    }
                )



class NflPbpHistoricalReconciliationTests(unittest.TestCase):
    """Source-only dynamic discovery, pinned batches and frozen history."""

    @staticmethod
    def _asset(year, payload=b"original", *, official_digest=True):
        sha = hashlib.sha256(payload).hexdigest()
        return {
            "id": year, "name": f"play_by_play_{year}.csv.gz",
            "size": len(payload),
            "digest": "sha256:" + sha if official_digest else None,
            "state": "uploaded", "updated_at": "2026-11-20T00:00:00Z",
            "browser_download_url": (
                f"https://github.com/nflverse/nflverse-data/releases/download/"
                f"pbp/play_by_play_{year}.csv.gz"
            ),
        }

    @staticmethod
    def _root(root, years):
        base = root / "data-source/nfl/schedules"
        base.mkdir(parents=True)
        for year in years:
            (base / f"{year}.json").write_text("{}")

    def test_current_original_manifest_does_not_block_historical_discovery(self):
        """Real main has metadata-2026 beside the accepted historical manifests."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._root(root, [2024, 2026])
            live = (root /
                "data-source/providers/nflverse/play-by-play-original/metadata-2026.json"
            )
            live.parent.mkdir(parents=True)
            live.write_text(json.dumps({"Season": 2026, "ManagedBy": "current importer"}))
            with patch.object(pbp_history, "current_source_season", return_value=2026), \
                 patch.object(pbp_history, "official_inventory", return_value={
                     2024: self._asset(2024),
                 }):
                report, _ = pbp_history.plan(root, "token")
            self.assertEqual(report["Seasons"], [2024])
            self.assertEqual(report["AcceptedSeasons"], [])

    def test_dynamic_inventory_accepts_digestless_1999_but_rejects_bad_metadata(self):
        first = self._asset(1999, b"legacy", official_digest=False)
        second = self._asset(2000)
        with patch.object(pbp_history, "api_json",
                          side_effect=[{"id": 123}, [first, second]]) as api:
            result = pbp_history.official_inventory("token")
        self.assertEqual(sorted(result), [1999, 2000])
        self.assertIsNone(result[1999]["digest"])
        self.assertEqual(api.call_count, 2)
        with patch.object(pbp_history, "api_json",
                          side_effect=[{"id": 123}, [first, first]]):
            with self.assertRaisesRegex(ValueError, "duplicate"):
                pbp_history.official_inventory("token")
        with patch.object(pbp_history, "api_json",
                          side_effect=[{"id": 123}, [dict(first, size=0)]]):
            with self.assertRaisesRegex(ValueError, "Invalid"):
                pbp_history.official_inventory("token")

    def test_bounded_pinned_ingestion_is_idempotent_and_stages_only_source(self):
        years = (2000, 2001, 2002, 2003)
        bytes_by_year = {year: (f"source-{year}".encode()) for year in years}
        official = {year: self._asset(year, data)
                    for year, data in bytes_by_year.items()}
        archived = {}
        def release(_token, year, sha):
            return {"assets": [archived[(year, sha)]]} if (year, sha) in archived else None
        def upload(_token, _release, source, year, sha, size):
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), sha)
            asset = {
                "id": year * 2, "name": f"play_by_play_{year}.csv.gz",
                "size": size, "digest": f"sha256:{sha}", "state": "uploaded",
                "browser_download_url": pbp_auto._archive_url(year, sha),
            }
            archived[(year, sha)] = asset
            return asset
        def download(url, target):
            year = int(url.rsplit("_", 1)[-1].split(".")[0])
            target.write_bytes(bytes_by_year[year])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._root(root, years)
            pin = root / "selection.json"
            with patch.object(pbp_history, "current_source_season", return_value=2026), \
                 patch.object(pbp_history, "official_inventory", return_value=official), \
                 patch.object(pbp_history, "_get_release", side_effect=release), \
                 patch.object(pbp_history, "_create_release", return_value={"id": 30}), \
                 patch.object(pbp_history, "_upload", side_effect=upload), \
                 patch.object(pbp_history, "download", side_effect=download), \
                 patch.object(pbp_history, "_audit", return_value={
                     "SourceRowCount": 2, "ObservedGameIDs": 1,
                 }):
                result = pbp_history.run(root, "Lolindhir/fantasy-app", "token",
                                         pin_path=pin, write=True)
                self.assertEqual(result["NewlyAccepted"], [2003, 2002, 2001])
                self.assertEqual(json.loads(pin.read_text())["Seasons"],
                                 [2003, 2002, 2001])
                again = pbp_history.run(root, "Lolindhir/fantasy-app", "token",
                                        pin_path=pin, write=True)
                self.assertFalse(again["Changed"])
                self.assertEqual(again["NewlyAccepted"], [])
                next_batch = pbp_history.run(root, "Lolindhir/fantasy-app",
                                             "token", write=True)
                self.assertEqual(next_batch["NewlyAccepted"], [2000])
                manifests = sorted(root.glob(
                    "data-source/providers/nflverse/play-by-play-original/*.json"
                ))
                self.assertEqual(len(manifests), 4)
                self.assertFalse(list(root.rglob("*.gz")))
                self.assertEqual(len(archived), 4)

    def test_batch_digest_failure_blocks_release_and_partial_manifest(self):
        years = (2000, 2001)
        official = {year: self._asset(year, b"expected") for year in years}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._root(root, years)
            with patch.object(pbp_history, "current_source_season", return_value=2026), \
                 patch.object(pbp_history, "official_inventory", return_value=official), \
                 patch.object(pbp_history, "download",
                              side_effect=lambda _url, path: path.write_bytes(b"forged!!")), \
                 patch.object(pbp_history, "_create_release") as release, \
                 patch.object(pbp_history, "_upload") as upload:
                report = pbp_history.run(root, "Lolindhir/fantasy-app", "token", write=True)
                self.assertEqual(report["Status"], "historical-pbp-blocked")
                self.assertEqual([x["Season"] for x in report["BlockedSeasons"]], [2001, 2000])
                release.assert_not_called()
                upload.assert_not_called()
                self.assertFalse(list(root.rglob("metadata-*.json")))

    def test_invalid_legacy_season_does_not_block_other_verified_sources(self):
        payloads = {2000: b"original-2000", 2001: b"original-2001",
                    2002: b"original-2002"}
        official = {year: self._asset(year, data)
                    for year, data in payloads.items()}
        uploaded = {}
        def upload(_token, _release, path, year, sha, size):
            result = {
                "id": year, "size": size, "digest": f"sha256:{sha}",
                "name": f"play_by_play_{year}.csv.gz", "state": "uploaded",
                "browser_download_url": pbp_auto._archive_url(year, sha),
            }
            uploaded[year] = result
            return result
        def download(url, path):
            year = int(url.rsplit("_", 1)[-1].split(".")[0])
            path.write_bytes(b"malformed----" if year == 2001 else payloads[year])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._root(root, payloads)
            with patch.object(pbp_history, "current_source_season", return_value=2026), \
                 patch.object(pbp_history, "official_inventory", return_value=official), \
                 patch.object(pbp_history, "download", side_effect=download), \
                 patch.object(pbp_history, "_audit", return_value={"SourceRowCount": 1}), \
                 patch.object(pbp_history, "_get_release", return_value=None), \
                 patch.object(pbp_history, "_create_release", return_value={"id": 4}), \
                 patch.object(pbp_history, "_upload", side_effect=upload):
                result = pbp_history.run(root, "Lolindhir/fantasy-app", "token", write=True)
            self.assertEqual(result["Status"], "historical-pbp-partial")
            self.assertEqual(result["NewlyAccepted"], [2002, 2000])
            self.assertEqual([x["Season"] for x in result["BlockedSeasons"]], [2001])
            self.assertEqual(sorted(uploaded), [2000, 2002])
            self.assertFalse((root /
                "data-source/providers/nflverse/play-by-play-original/metadata-2001.json"
            ).exists())

    def test_digestless_original_keeps_source_and_hash_provenance_distinct(self):
        year, data = 1999, b"1999-source-bytes"
        official = {year: self._asset(year, data, official_digest=False)}
        sha = hashlib.sha256(data).hexdigest()
        archived = {
            "id": 11, "name": "play_by_play_1999.csv.gz", "size": len(data),
            "digest": f"sha256:{sha}", "state": "uploaded",
            "browser_download_url": pbp_auto._archive_url(year, sha),
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._root(root, [year])
            with patch.object(pbp_history, "current_source_season", return_value=2026), \
                 patch.object(pbp_history, "official_inventory", return_value=official), \
                 patch.object(pbp_history, "download",
                              side_effect=lambda _url, path: path.write_bytes(data)), \
                 patch.object(pbp_history, "_audit", return_value={"SourceRowCount": 1}), \
                 patch.object(pbp_history, "_get_release", return_value={
                     "assets": [archived],
                 }):
                result = pbp_history.run(root, "Lolindhir/fantasy-app", "token", write=True)
                self.assertEqual(result["NewlyAccepted"], [year])
                meta = json.loads((root /
                    "data-source/providers/nflverse/play-by-play-original/metadata-1999.json"
                ).read_text())
                self.assertIsNone(meta["UpstreamSHA256"])
                self.assertEqual(meta["OriginalSHA256"], sha)
                self.assertEqual(meta["SourceDigestAuthority"],
                                 "self-sha256-official-asset-no-digest")

    def test_pinned_provider_asset_drift_blocks_before_source_admission(self):
        year = 2024
        original = self._asset(year, b"2024-original")
        revised = self._asset(year, b"2024-revised")
        pinned = {
            "Seasons": [year],
            "Assets": {str(year): {
                key: original.get(key) for key in (
                    "id", "size", "digest", "updated_at", "browser_download_url"
                )
            }},
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._root(root, [year])
            path = root / "pin.json"
            path.write_text(json.dumps(pinned))
            with patch.object(pbp_history, "current_source_season", return_value=2026), \
                 patch.object(pbp_history, "official_inventory", return_value={
                     year: revised,
                 }), \
                 patch.object(pbp_history, "download") as download:
                with self.assertRaisesRegex(ValueError, "Pinned historical PBP official asset identity changed"):
                    pbp_history.run(root, "Lolindhir/fantasy-app", "token",
                                    write=True, pin_path=path)
                download.assert_not_called()
                self.assertFalse(list(root.rglob("metadata-*.json")))

    def test_frozen_2025_upstream_revision_is_review_not_overwrite(self):
        year = 2025
        old = hashlib.sha256(b"accepted").hexdigest()
        official = {year: self._asset(year, b"provider-revision")}
        archived = {
            "id": 42, "name": "play_by_play_2025.csv.gz",
            "size": len(b"accepted"), "digest": f"sha256:{old}",
            "state": "uploaded",
            "browser_download_url": pbp_auto._archive_url(year, old),
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._root(root, [year])
            path = (root /
                "data-source/providers/nflverse/play-by-play-original/metadata-2025.json"
            )
            path.parent.mkdir(parents=True)
            data = {
                "SchemaVersion": 1, "Status": "accepted-original-byte-identity",
                "Season": year, "UpstreamSHA256": old,
                "SourceAssetID": year, "CompressedBytes": len(b"accepted"),
                "ReleaseTag": pbp_auto._archive_tag(year, old),
                "ArchiveURL": pbp_auto._archive_url(year, old),
            }
            path.write_text(json.dumps(data))
            saved = path.read_bytes()
            with patch.object(pbp_history, "current_source_season", return_value=2026), \
                 patch.object(pbp_history, "official_inventory", return_value=official), \
                 patch.object(pbp_history, "_get_release", return_value={
                     "assets": [archived],
                 }), \
                 patch.object(pbp_history, "download") as download, \
                 patch.object(pbp_history, "_upload") as upload:
                report = pbp_history.run(root, "Lolindhir/fantasy-app", "token",
                                         write=True)
                self.assertEqual(report["NewlyAccepted"], [])
                self.assertEqual(report["FrozenRevisionReview"], [{
                    "Season": 2025, "Reason": "official-provider-digest-changed",
                }])
                self.assertEqual(saved, path.read_bytes())
                download.assert_not_called()
                upload.assert_not_called()

    def test_history_and_weekly_derived_use_existing_workflow_only(self):
        workflow = (TOOLS.parent / ".github/workflows/sync-nfl-source-data.yml").read_text()
        self.assertIn("tools/nfl_pbp_source_history.py", workflow)
        self.assertIn("--pin-path", workflow)
        self.assertIn("--limit 3", workflow)
        self.assertIn("historical_pbp_due", workflow)
        self.assertIn("original-PBP archive cache", workflow.lower().replace("original-pbp", "original-PBP"))
        self.assertIn("python3 tools/nfl_game_details_materialize.py --historical-seasons --write", workflow)


class NflPbpDerivedCacheTests(unittest.TestCase):
    def test_verified_file_cache_survives_eviction_without_second_download(self):
        import os
        from derived_data_lib import nfl_pbp_accepted_season as reader
        def manifest(_root, year):
            sha = hashlib.sha256(f"{year}".encode()).hexdigest()
            return {"Season": year, "UpstreamSHA256": sha,
                    "CompressedBytes": 4,
                    "ArchiveURL": "https://example.invalid/original"}
        calls = []
        def download(_url, path):
            calls.append(path)
            path.write_bytes(b"dummy")
        with tempfile.TemporaryDirectory() as tmp, \
             patch.dict(os.environ, {"NFL_PBP_ARCHIVE_CACHE_DIR": tmp}), \
             patch.object(reader, "_manifest", side_effect=manifest), \
             patch.object(reader, "download", side_effect=download), \
             patch.object(reader, "_verified_rows", return_value={}):
            store = reader.AcceptedPBPSeasons(Path(tmp))
            store.get(1999, {})
            store.get(2000, {})
            self.assertEqual(len(store._cache), 1)
            store.get(1999, {})
            self.assertEqual(len(calls), 2)
            self.assertIn(1999, store._cache)

if __name__ == "__main__":
    unittest.main()
