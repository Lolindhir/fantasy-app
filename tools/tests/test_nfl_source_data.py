import csv
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
import nfl_pbp_2025_quality_report as pbp_quality
from nfl_source_data_lib.draft import classify_draft_status
from nfl_source_data_lib.materialize import materialize


def write_csv(path: Path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


class NflSourceDataTests(unittest.TestCase):
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
        self.assertIn(
            "2025 original PBP pilot blocked; no source archive accepted",
            workflow,
        )
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


if __name__ == "__main__":
    unittest.main()
