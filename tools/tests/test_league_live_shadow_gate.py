"""Fail-closed and no-skip regression cases for League Live shadow observation (#1263 G5)."""
from __future__ import annotations

import json

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from tools import league_live_shadow_gate as shadow
from tools import league_live_output_revision_audit as output_audit


class ShadowDecisionTests(unittest.TestCase):
    def evidence(self, stage: str = "league") -> tuple[dict, dict]:
        inputs = {path: path + "-fingerprint" for path in shadow.STAGE_INPUTS[stage]}
        current = {
            "schemaVersion": 1, "stage": stage, "scope": "all-leagues-seasons",
            "atUtc": "2026-11-03T19:30:00Z", "inputTrees": inputs,
            "missingOutputs": [], "sourceStatus": "success", "upstreamStatus": "success",
            "raceFree": True, "recoveryClean": True,
        }
        prior = {
            "schemaVersion": 1, "stage": stage, "scope": "all-leagues-seasons",
            "processedAtUtc": "2026-11-03T19:20:00Z", "validUntilUtc": "2026-11-03T19:40:00Z",
            "clockBoundaryProof": True, "completedSuccessfully": True,
            "outputsValidated": True, "raceFree": True, "recoveryClean": True,
            "inputTrees": dict(inputs),
        }
        return current, prior

    def test_positive_requires_every_proof_and_never_enforces_skip(self):
        for stage in shadow.STAGE_INPUTS:
            with self.subTest(stage=stage):
                current, prior = self.evidence(stage)
                result = shadow.decide(current, prior)
                self.assertEqual("would-skip", result["decision"])
                self.assertFalse(result["enforced"])
                self.assertEqual([], result["reasonCodes"])

    def test_missing_prior_never_skips(self):
        current, _ = self.evidence()
        result = shadow.decide(current, None)
        self.assertEqual("would-run", result["decision"])
        self.assertIn("missing-previous-successful-attestation", result["reasonCodes"])

    def test_nfl_finality_source_correction_and_derived_changes_invalidate(self):
        for stage in shadow.STAGE_INPUTS:
            for path in ("data-source", "data-derived", "data-meta"):
                with self.subTest(stage=stage, path=path):
                    current, prior = self.evidence(stage)
                    current["inputTrees"][path] = "changed"
                    self.assertIn("input-revision-changed-or-unknown",
                                  shadow.decide(current, prior)["reasonCodes"])

    def test_app_code_market_salary_and_model_change_invalidate(self):
        for path in ("public/data", "public/requests", "tools", ".github/workflows"):
            current, prior = self.evidence("league")
            current["inputTrees"][path] = "changed"
            self.assertEqual("would-run", shadow.decide(current, prior)["decision"])

    def test_kickoff_waiver_and_week_boundaries_invalidate(self):
        for key, value in (
            ("validUntilUtc", "2026-11-03T19:30:00Z"),
            ("validUntilUtc", None),
            ("processedAtUtc", "2026-11-03T19:35:00Z"),
            ("clockBoundaryProof", False),
        ):
            with self.subTest(key=key, value=value):
                current, prior = self.evidence()
                prior[key] = value
                self.assertEqual("would-run", shadow.decide(current, prior)["decision"])

    def test_races_fail_soft_recovery_errors_missing_outputs_and_unknowns_invalidate(self):
        for owner, key, value in (
            ("current", "sourceStatus", "failure"),
            ("current", "upstreamStatus", "unknown"),
            ("current", "raceFree", None),
            ("current", "recoveryClean", False),
            ("current", "missingOutputs", ["public/data/League.json"]),
            ("prior", "raceFree", False),
            ("prior", "recoveryClean", None),
            ("prior", "completedSuccessfully", False),
            ("prior", "outputsValidated", None),
            ("prior", "scope", "one-league-only"),
        ):
            with self.subTest(owner=owner, key=key):
                current, prior = self.evidence()
                (current if owner == "current" else prior)[key] = value
                self.assertEqual("would-run", shadow.decide(current, prior)["decision"])

    def test_missing_input_or_one_league_scope_invalidates(self):
        current, prior = self.evidence()
        current["inputTrees"].pop("data-source")
        self.assertIn("incomplete-current-input-fingerprints",
                      shadow.decide(current, prior)["reasonCodes"])
        current, prior = self.evidence()
        current["scope"] = "nfl-reise/2026"
        self.assertIn("incomplete-multi-league-scope",
                      shadow.decide(current, prior)["reasonCodes"])

    def test_current_live_probe_does_not_invent_positive_race_or_recovery_proof(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            for path in shadow.STAGE_OUTPUTS["standings"]:
                target = repo / path
                if path.endswith(".json"):
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text("{}")
                else:
                    target.mkdir(parents=True)
            with patch.object(shadow, "sha_for", return_value="test-fingerprint"), patch.object(
                shadow.subprocess, "run",
                return_value=type("Result", (), {"stdout": "a" * 40})(),
            ):
                current = shadow.collect(repo, "standings", "2026-11-03T19:30:00Z", "success", "success")
            self.assertIsNone(current["raceFree"])
            self.assertIsNone(current["recoveryClean"])
            self.assertEqual([], current["missingOutputs"])
            self.assertEqual("would-run", shadow.decide(current, None)["decision"])

    def test_decision_logs_annotate_no_enforcement(self):
        current, prior = self.evidence()
        result = {**shadow.decide(current, prior), "inputFingerprint": shadow.fingerprint(current["inputTrees"])}
        with tempfile.TemporaryDirectory() as temp:
            summary = Path(temp) / "summary.md"
            with patch.dict("os.environ", {"GITHUB_STEP_SUMMARY": str(summary)}):
                with patch("builtins.print") as printed:
                    shadow.publish_observation(result)
            self.assertIn("would-skip", summary.read_text())
            self.assertIn("(no jobs skipped)", summary.read_text())
            self.assertIn("LEAGUE_LIVE_SHADOW", printed.call_args[0][0])

    def test_workflow_preserves_publishers_and_adds_only_nonblocking_observers(self):
        workflow = (Path(__file__).resolve().parents[2] / ".github/workflows/league-live.yml").read_text()
        self.assertEqual(2, workflow.count("tools/league_live_shadow_gate.py"))
        self.assertIn("--stage standings", workflow)
        self.assertIn("--stage league", workflow)
        self.assertEqual(2, workflow.count("--source-status"))
        self.assertEqual(2, workflow.count("continue-on-error: true"))
        self.assertIn("Rebuild and publish Standings data", workflow)
        self.assertIn("Rebuild and publish League, PlayerWeekFantasy", workflow)
        self.assertIn("cancel-in-progress: false", workflow)



    def test_league_shadow_inventory_includes_future_draft_contract_surfaces(self):
        required = {
            "public/data/Drafts.json",
            "public/data/Transactions.json",
            "data-derived/league-drafts",
            "data-derived/league-transactions",
        }
        self.assertTrue(required <= set(shadow.STAGE_OUTPUTS["league"]))
        # A directory existing is not proof that all configured future seasons
        # have coherent partitions; that remains a separate production gate.

    def test_missing_draft_partition_root_or_app_drafts_forces_offline_run(self):
        for missing in ("data-derived/league-drafts", "public/data/Drafts.json",
                        "data-derived/league-transactions", "public/data/Transactions.json"):
            with self.subTest(missing=missing):
                current, prior = self.evidence("league")
                current["missingOutputs"] = [missing]
                result = shadow.decide(current, prior)
                self.assertEqual("would-run", result["decision"])
                self.assertIn("missing-or-unknown-output", result["reasonCodes"])
                self.assertFalse(result["enforced"])

    def test_forged_finality_race_and_attestation_cannot_authorize_skip(self):
        cases = (
            ("prior", "completedSuccessfully", "success"),
            ("prior", "outputsValidated", 1),
            ("prior", "clockBoundaryProof", "true"),
            ("prior", "raceFree", 1),
            ("prior", "recoveryClean", "yes"),
            ("current", "raceFree", "true"),
            ("current", "recoveryClean", 1),
        )
        for owner, field, bad in cases:
            with self.subTest(owner=owner, field=field):
                current, prior = self.evidence("league")
                (current if owner == "current" else prior)[field] = bad
                result = shadow.decide(current, prior)
                self.assertEqual("would-run", result["decision"])
                self.assertFalse(result["enforced"])

    def test_prior_revision_clock_and_league_scope_must_match(self):
        cases = (
            ("schemaVersion", 2),
            ("stage", "standings"),
            ("scope", "nfl-reise/2026"),
            ("processedAtUtc", "2026-11-03T19:31:00Z"),
            ("validUntilUtc", "2026-11-03T19:29:59Z"),
        )
        for key, bad in cases:
            with self.subTest(key=key):
                current, prior = self.evidence("league")
                prior[key] = bad
                self.assertEqual("would-run", shadow.decide(current, prior)["decision"])






class OfflinePreflightProtocolTests(unittest.TestCase):
    """Finite synthetic protocol evidence only; no production attestation."""

    def evidence(self, stage="league"):
        sha = lambda char: char * 40
        trees = {name: sha("a") for name in shadow.STAGE_INPUTS[stage]}
        outputs = {
            path if path.endswith(".json") else path + "/nfl-reise/2026.json": sha("b")
            for path in shadow.OFFLINE_REQUIRED_SURFACES[stage]
        }
        if stage == "league":
            # Dynamic future Draft seasons must be supplied by canonical metadata,
            # never inferred from a hard-coded current+one-year horizon.
            outputs["data-derived/league-drafts/nfl-reise/2032.json"] = sha("c")
        scope = [{"league": "nfl-reise", "season": 2026}]
        receipt = {
            "schemaVersion": 1, "stage": stage, "scope": scope,
            "revision": sha("d"), "sourceRevision": sha("e"),
            "inputTrees": trees, "publishedOutputs": outputs,
            "publishedAtUtc": "2026-11-05T10:00:00Z",
            "acquisitionId": "sleeper-2026-11-05-10",
            "producer": {"success": True, "attempt": 1,
                         "outputsComplete": True, "recoveryDebt": []},
        }
        current = {
            "stage": stage, "scope": list(scope),
            "revision": receipt["revision"],
            "sourceRevision": receipt["sourceRevision"],
            "inputTrees": dict(trees),
            "requiredOutputs": dict(outputs),
            "observedOutputs": dict(outputs),
            "asOfUtc": "2026-11-05T10:05:00Z",
            "providerEvidence": {
                "status": "verified", "sourceRevision": sha("e"),
                "acquisitionId": receipt["acquisitionId"],
                "observedAtUtc": "2026-11-05T10:04:00Z",
                "expiresAtUtc": "2026-11-05T10:10:00Z",
            },
            "finalityEvidence": {"status": "verified",
                                 "sourceRevision": sha("e"),
                                 "activeNonfinal": False,
                                 "unknownKickoffs": False},
            "clockEvidence": {"status": "clear",
                              "fromUtc": "2026-11-05T10:00:00Z",
                              "toUtc": "2026-11-05T10:05:00Z",
                              "crossedBoundaries": []},
        }
        trace = [
            {"action": "acquire", "sha": sha("d")},
            {"action": "compare", "sha": sha("d")},
            {"action": "skip", "sha": sha("d")},
            {"action": "release", "sha": sha("d")},
        ]
        return receipt, current, trace

    def assert_run(self, receipt, current, trace, reason):
        result = shadow.assess_offline_preflight_protocol(receipt, current, trace)
        self.assertEqual("would-run", result["decision"])
        self.assertIn(reason, result["reasonCodes"])
        self.assertIs(result["safeToSkip"], False)
        self.assertIs(result["enforced"], False)
        self.assertIs(result["independentEvidenceVerified"], False)

    def test_synthetic_complete_case_is_only_would_skip_not_activation(self):
        for stage in shadow.STAGE_INPUTS:
            with self.subTest(stage=stage):
                receipt, current, trace = self.evidence(stage)
                result = shadow.assess_offline_preflight_protocol(receipt, current, trace)
                self.assertEqual("would-skip", result["decision"])
                self.assertTrue(result["syntheticProtocolConsistent"])
                self.assertFalse(result["safeToSkip"])
                self.assertFalse(result["raceFree"])
                self.assertFalse(result["recoveryClean"])
                self.assertFalse(result["independentEvidenceVerified"])
                self.assertFalse(result["enforced"])

    def test_missing_or_wrong_receipts_fail_closed(self):
        for mutation, reason in [
            (lambda r,c: r.update(schemaVersion=2), "unknown-or-mismatched-stage-contract"),
            (lambda r,c: r.update(stage="standings"), "unknown-or-mismatched-stage-contract"),
            (lambda r,c: c.update(revision="f"*40), "unbound-or-different-publication-revision"),
            (lambda r,c: c.update(sourceRevision="f"*40), "unbound-or-different-publication-revision"),
            (lambda r,c: r.update(revision="not-sha"), "unbound-or-different-publication-revision"),
        ]:
            with self.subTest(mutation=reason):
                r,c,t=self.evidence()
                mutation(r,c)
                self.assert_run(r,c,t,reason)
        _,c,t=self.evidence()
        self.assert_run(None,c,t,"missing-or-malformed-protocol-evidence")

    def test_full_canonical_league_season_scope_must_match(self):
        cases=[
            (lambda r,c: r["scope"].clear()),
            (lambda r,c: c["scope"].append({"league":"nfl-reise","season":2027})),
            (lambda r,c: c["scope"].append({"league":"nfl-reise","season":2026})),
            (lambda r,c: c["scope"][0].update(season="2026")),
            (lambda r,c: c["scope"][0].update(league="../escape")),
            (lambda r,c: r["scope"].append({"league":"other","season":2024})),
        ]
        for index, mutation in enumerate(cases):
            with self.subTest(case=index):
                r,c,t=self.evidence()
                mutation(r,c)
                self.assert_run(r,c,t,"canonical-league-season-scope-unverified")

    def test_dependency_tree_changes_and_missing_roots_fail_closed(self):
        for path in shadow.STAGE_INPUTS["league"]:
            with self.subTest(path=path):
                r,c,t=self.evidence()
                c["inputTrees"][path]="f"*40
                self.assert_run(r,c,t,"changed-or-incomplete-dependency-trees")
        r,c,t=self.evidence()
        c["inputTrees"].pop("data-meta")
        self.assert_run(r,c,t,"changed-or-incomplete-dependency-trees")

    def test_future_draft_partitions_and_outputs_are_exact(self):
        path="data-derived/league-drafts/nfl-reise/2032.json"
        for owner in ("requiredOutputs","observedOutputs"):
            with self.subTest(owner=owner):
                r,c,t=self.evidence()
                c[owner].pop(path)
                self.assert_run(r,c,t,"incomplete-or-stale-published-output-manifest")
        r,c,t=self.evidence()
        r["publishedOutputs"].pop(path)
        self.assert_run(r,c,t,"incomplete-or-stale-published-output-manifest")
        r,c,t=self.evidence()
        c["observedOutputs"][path]="f"*40
        self.assert_run(r,c,t,"incomplete-or-stale-published-output-manifest")
        r,c,t=self.evidence()
        c["requiredOutputs"]["data-derived/league-drafts/../forged"]="f"*40
        self.assert_run(r,c,t,"incomplete-or-stale-published-output-manifest")
        r,c,t=self.evidence()
        for source in (r["publishedOutputs"],c["requiredOutputs"],c["observedOutputs"]):
            for path in list(source):
                if path.startswith("data-derived/team-week-performance"):
                    source.pop(path)
        self.assert_run(r,c,t,"required-output-surface-missing")

    def test_prior_fail_soft_and_ambiguous_producer_never_qualify(self):
        for name, value in [
            ("success", False), ("success", "true"),
            ("attempt", 2), ("attempt", True),
            ("outputsComplete", None),
            ("recoveryDebt", [{"product":"team-week-performance","status":"blocked"}]),
            ("recoveryDebt", [{"product":"team-week-performance","status":"no-scored-week"}]),
            ("recoveryDebt", [{"product":"league-drafts","status":"blocked"}]),
            ("recoveryDebt", [{"product":"team-week-performance","parity":"accepted-divergence"}]),
        ]:
            with self.subTest(name=name,value=value):
                r,c,t=self.evidence()
                r["producer"][name]=value
                self.assert_run(r,c,t,"prior-producer-or-fail-soft-recovery-not-proven")

    def test_provider_freshness_gaps_expiry_and_silent_change(self):
        cases=[
            ("status","unknown"),
            ("sourceRevision","f"*40),
            ("acquisitionId","different"),
            ("observedAtUtc","2026-11-05T10:06:00Z"),
            ("expiresAtUtc","2026-11-05T10:05:00Z"),
        ]
        for key,value in cases:
            with self.subTest(key=key):
                r,c,t=self.evidence()
                c["providerEvidence"][key]=value
                self.assert_run(r,c,t,"provider-freshness-window-unverified")
        r,c,t=self.evidence()
        c.pop("providerEvidence")
        self.assert_run(r,c,t,"missing-or-malformed-temporal-evidence")

    def test_nfl_finality_unknown_or_active_forces_run(self):
        for key,value in [
            ("status","unknown"), ("sourceRevision","f"*40),
            ("activeNonfinal",True), ("activeNonfinal",None),
            ("unknownKickoffs",True),
        ]:
            with self.subTest(key=key):
                r,c,t=self.evidence()
                c["finalityEvidence"][key]=value
                self.assert_run(r,c,t,"nfl-finality-state-unverified")

    def test_waiver_kickoff_cap_and_rollover_crossings_force_run(self):
        for boundary in ("WaiverRun","NflGameKickoff","CapWindowEnd","SeasonWindowStart"):
            with self.subTest(boundary=boundary):
                r,c,t=self.evidence()
                c["clockEvidence"]["crossedBoundaries"]=[boundary]
                self.assert_run(r,c,t,"clock-waiver-or-rollover-window-unverified")
        r,c,t=self.evidence()
        c["clockEvidence"]["fromUtc"]="2026-11-05T10:01:00Z"
        self.assert_run(r,c,t,"clock-waiver-or-rollover-window-unverified")
        r,c,t=self.evidence()
        c["asOfUtc"]="2026-11-05T09:59:00Z"
        self.assert_run(r,c,t,"non-forward-observation-clock")

    def test_race_while_locked_or_between_check_and_skip_is_rejected(self):
        for position in (1,2,3):
            with self.subTest(position=position):
                r,c,t=self.evidence()
                t.insert(position,{"action":"commit","sha":"f"*40})
                self.assert_run(r,c,t,"cross-writer-commit-inside-critical-section")
        r,c,t=self.evidence()
        t.insert(0,{"action":"commit","sha":"f"*40})
        self.assert_run(r,c,t,"input-commit-before-skip-linearization")

    def test_post_skip_invalidation_loss_or_missing_rebuild_is_rejected(self):
        for extra in [
            [{"action":"commit","sha":"f"*40}],
            [{"action":"commit","sha":"f"*40},{"action":"enqueue","sha":"f"*40}],
            [{"action":"commit","sha":"f"*40},{"action":"rebuild","sha":"f"*40}],
        ]:
            with self.subTest(extra=extra):
                r,c,t=self.evidence()
                t.extend(extra)
                self.assert_run(r,c,t,"dependency-commit-not-reconciled")
        r,c,t=self.evidence()
        t.extend([{"action":"commit","sha":"f"*40},
                  {"action":"enqueue","sha":"f"*40},
                  {"action":"rebuild","sha":"f"*40}])
        result=shadow.assess_offline_preflight_protocol(r,c,t)
        self.assertEqual("would-skip",result["decision"])
        self.assertFalse(result["safeToSkip"])  # Finite trace is NOT live race safety.

    def test_race_missing_lock_release_and_unknown_events_rejected(self):
        cases=[
            ([{"action":"compare","sha":"d"*40},{"action":"skip","sha":"d"*40},
              {"action":"release","sha":"d"*40}],"invalid-or-incomplete-synthetic-race-trace"),
            ([{"action":"acquire","sha":"d"*40},{"action":"compare","sha":"d"*40},
              {"action":"skip","sha":"d"*40},{"action":"skip","sha":"d"*40}],"skip-outside-verified-critical-section"),
            ([{"action":"acquire","sha":"d"*40},{"action":"compare","sha":"d"*40},
              {"action":"skip","sha":"d"*40},{"action":"mystery","sha":"d"*40},
              {"action":"release","sha":"d"*40}],"unknown-synthetic-race-action"),
            ([{"action":"acquire","sha":"d"*40},{"action":"compare","sha":"d"*40},
              {"action":"skip","sha":"d"*40},{"action":"release","sha":"d"*40},
              {"action":"commit","sha":"bad"}],"malformed-synthetic-race-event"),
        ]
        for event_trace,reason in cases:
            with self.subTest(reason=reason):
                r,c,_=self.evidence()
                self.assert_run(r,c,event_trace,reason)

    def test_offline_fixture_has_no_live_executor_or_skip_path(self):
        workflow=(Path(__file__).resolve().parents[2]/".github/workflows/league-live.yml").read_text()
        self.assertNotIn("assess_offline_preflight_protocol",workflow)
        self.assertNotIn("replay_offline_skip_race",workflow)
        r,c,t=self.evidence()
        self.assertEqual("would-skip",shadow.assess_offline_preflight_protocol(r,c,t)["decision"])
        self.assertFalse(shadow.assess_offline_preflight_protocol(r,c,t)["safeToSkip"])




class ImmutableOutputRevisionAuditTests(unittest.TestCase):
    """Read-only fake Git object graph, with actual canonical blob SHA-1 checks."""

    class Fixture:
        def __init__(self, leagues=("nfl-reise",), horizon=3):
            import hashlib
            self.files = {}
            self.horizon = horizon
            self.leagues = leagues
            for league in leagues:
                season = 2026
                self.put_json(f"data-meta/{league}/metadata.json", {
                    "SchemaVersion": 1, "CanonicalLeagueID": league,
                    "CurrentProviderLeagueID": "1354177383984267264",
                    "Drafts": {"UpcomingDraftCount": horizon,
                               "UpcomingDraftCountMode": "PerDraftType",
                               "Types": [{"DraftType": "Rookie"}]},
                })
                self.put_json(f"data-source/leagues/{league}/manifest.json", {
                    "CanonicalLeagueID": league,
                    "CurrentCanonicalLeagueSeasonID": f"{league}-{season}",
                    "CurrentProviderLeagueID": "1354177383984267264",
                    "Seasons": [{"Season": 2024}, {"Season": 2025},
                                {"Season": 2026}],
                })
                for year in range(2024, 2027 + horizon):
                    self.files[f"data-derived/league-drafts/{league}/{year}.json"] = b"{}"
                for year in (2024, 2025, 2026):
                    self.files[f"data-derived/league-transactions/{league}/{year}.json"] = b"{}"
                for product in ("team-week-performance", "player-week-fantasy"):
                    for week in (1, 8):
                        self.files[f"data-derived/{product}/{league}/2026/{week:02}.json"] = b"{}"
            for path in output_audit.APP_FILES:
                self.files[path] = b"{}"
            self.compile()

        def put_json(self, path, value):
            self.files[path] = json.dumps(value, sort_keys=True).encode("utf-8")

        def compile(self):
            import hashlib
            import base64
            root = {}
            self.blobs = {}
            self.trees = {}
            for path, data in sorted(self.files.items()):
                blob = hashlib.sha1(b"blob " + str(len(data)).encode() +
                                    b"\x00" + data).hexdigest()
                self.blobs[blob] = {
                    "sha": blob, "encoding": "base64", "size": len(data),
                    "content": base64.b64encode(data).decode("ascii"),
                }
                node = root
                parts = path.split("/")
                for part in parts[:-1]:
                    node = node.setdefault(part, {})
                node[parts[-1]] = ("blob", blob)
            def seal(node):
                entries = []
                for name, value in sorted(node.items()):
                    typ, sha = value if isinstance(value, tuple) else ("tree", seal(value))
                    entries.append({"path": name, "type": typ, "sha": sha})
                tree_sha = hashlib.sha1(
                    json.dumps(entries, sort_keys=True).encode("utf-8")
                ).hexdigest()
                self.trees[tree_sha] = {"sha": tree_sha, "truncated": False,
                                        "tree": entries}
                return tree_sha
            root_sha = seal(root)
            self.sha = hashlib.sha1(("commit:" + root_sha).encode()).hexdigest()
            self.commit = {"sha": self.sha, "commit": {"tree": {"sha": root_sha}}}

        def fetch(self, resource, params):
            if params:
                raise AssertionError("Unexpected params")
            if resource == f"commits/{self.sha}":
                return self.commit
            if resource.startswith("git/trees/"):
                return self.trees[resource.split("/")[-1]]
            if resource.startswith("git/blobs/"):
                return self.blobs[resource.split("/")[-1]]
            raise AssertionError("Unexpected Git API path " + resource)

        def report(self):
            return output_audit.audit_immutable_outputs(self.fetch, self.sha)

    def assert_blocked(self, fixture, fragment):
        result = fixture.report()
        self.assertEqual("blocked", result["status"])
        self.assertTrue(any(fragment in code for code in result["reasonCodes"]),
                        result["reasonCodes"])
        self.assertFalse(result["selectedGitOutputBlobIdsVerified"])
        self.assertFalse(result["safeToSkip"])
        self.assertFalse(result["enforced"])

    def test_realistic_selected_tree_proof_remains_no_go(self):
        f = self.Fixture()
        result = f.report()
        self.assertTrue(result["selectedGitOutputBlobIdsVerified"])
        self.assertTrue(result["metadataMinimumDraftYearsVerified"])
        self.assertEqual("immutable-selected-output-blobs-observed", result["status"])
        self.assertEqual([2026, 2027, 2028, 2029],
                         result["leagueCoverage"][0]["minimumConfiguredDraftYears"])
        self.assertIn("data-derived/league-drafts/nfl-reise/2029.json",
                      result["selectedOutputBlobs"])
        for flag in ("completeOutputInventoryVerified", "providerDraftHorizonVerified",
                     "outputSemanticParityVerified", "successfulProducerRunVerified",
                     "independentProviderFreshnessVerified", "independentNflFinalityVerified",
                     "recoveryClean", "raceFree", "safeToSkip", "enforced"):
            self.assertIs(result[flag], False, flag)

    def test_two_leagues_are_discovered_not_hard_coded(self):
        f = self.Fixture(leagues=("alpha", "nfl-reise"))
        result = f.report()
        self.assertEqual(["alpha", "nfl-reise"], result["canonicalLeagueIDs"])
        self.assertEqual(2, len(result["leagueCoverage"]))
        self.assertFalse(result["safeToSkip"])

    def test_missing_dynamic_future_draft_file_fails_closed(self):
        f = self.Fixture()
        f.files.pop("data-derived/league-drafts/nfl-reise/2029.json")
        f.compile()
        self.assert_blocked(f, "metadata-minimum-future-drafts-missing")

    def test_increasing_metadata_horizon_discovers_new_required_draft(self):
        f = self.Fixture()
        f.put_json("data-meta/nfl-reise/metadata.json", {
            "SchemaVersion": 1, "CanonicalLeagueID": "nfl-reise",
            "CurrentProviderLeagueID": "1354177383984267264",
            "Drafts": {"UpcomingDraftCount": 6,
                       "UpcomingDraftCountMode": "PerDraftType",
                       "Types": [{"DraftType": "Rookie"}]},
        })
        f.compile()
        self.assert_blocked(f, "metadata-minimum-future-drafts-missing")

    def test_extra_actual_future_partitions_are_collected_not_suppressed(self):
        f = self.Fixture()
        f.files["data-derived/league-drafts/nfl-reise/2035.json"] = b"{}"
        f.compile()
        result = f.report()
        self.assertTrue(result["selectedGitOutputBlobIdsVerified"])
        self.assertIn(2035, result["leagueCoverage"][0]["observedDraftYears"])
        self.assertFalse(result["providerDraftHorizonVerified"])
        self.assertFalse(result["safeToSkip"])

    def test_missing_current_transactions_or_pwf_twp_fails_closed(self):
        cases = (
            ("data-derived/league-transactions/nfl-reise/2026.json",
             "current-product-season-missing"),
            ("data-derived/team-week-performance/nfl-reise/2026/01.json",
             "missing"),
            ("data-derived/player-week-fantasy/nfl-reise/2026/08.json",
             "missing"),
        )
        for path, _ in cases:
            with self.subTest(path=path):
                f = self.Fixture()
                if path.endswith("/2026.json"):
                    f.files.pop(path)
                else:
                    parent = path.rsplit("/", 1)[0]
                    for current in list(f.files):
                        if current.startswith(parent + "/"):
                            f.files.pop(current)
                f.compile()
                self.assert_blocked(f, "current-product-season-missing" if
                                    path.endswith("/2026.json") else
                                    "required-git-entry-missing")

    def test_missing_app_output_fails_closed(self):
        f = self.Fixture()
        f.files.pop(output_audit.APP_FILES[0])
        f.compile()
        self.assert_blocked(f, "required-git-entry-missing")

    def test_invalid_week_partition_fails_closed(self):
        for name in ("00.json", "24.json", "week-8.json"):
            with self.subTest(name=name):
                f = self.Fixture()
                f.files[f"data-derived/team-week-performance/nfl-reise/2026/{name}"] = b"{}"
                f.compile()
                self.assert_blocked(f, "invalid-week-partition")

    def test_stray_derived_league_without_metadata_fails_closed(self):
        f = self.Fixture()
        f.files["data-derived/league-drafts/rogue/2026.json"] = b"{}"
        f.compile()
        self.assert_blocked(f, "missing-or-extra-derived-league")

    def test_missing_manifest_and_identity_drift_fail_closed(self):
        f = self.Fixture()
        f.files.pop("data-source/leagues/nfl-reise/manifest.json")
        f.compile()
        self.assert_blocked(f, "required-git-entry-missing")
        f = self.Fixture()
        f.put_json("data-source/leagues/nfl-reise/manifest.json", {
            "CanonicalLeagueID": "nfl-reise",
            "CurrentCanonicalLeagueSeasonID": "nfl-reise-2025",
            "CurrentProviderLeagueID": "other",
            "Seasons": [{"Season": 2025}],
        })
        f.compile()
        self.assert_blocked(f, "metadata-manifest-season-identity-mismatch")

    def test_corrupt_canonical_blob_digest_and_wrong_ref_fail_closed(self):
        f = self.Fixture()
        meta = f.files["data-meta/nfl-reise/metadata.json"]
        import hashlib
        blob_sha = hashlib.sha1(b"blob " + str(len(meta)).encode() + b"\0" + meta).hexdigest()
        f.blobs[blob_sha]["content"] = "e30="  # different bytes, same claimed SHA
        self.assert_blocked(f, "canonical-blob-digest-mismatch")
        result = output_audit.audit_immutable_outputs(f.fetch, "not-a-sha")
        self.assertFalse(result["selectedGitOutputBlobIdsVerified"])
        self.assertFalse(result["safeToSkip"])

    def test_wrong_or_truncated_tree_fail_closed(self):
        f = self.Fixture()
        root_sha = f.commit["commit"]["tree"]["sha"]
        f.trees[root_sha]["truncated"] = True
        self.assert_blocked(f, "incomplete-or-wrong-git-tree")
        f = self.Fixture()
        f.commit["commit"]["tree"]["sha"] = "x" * 40
        self.assert_blocked(f, "commit-tree-not-independently-resolved")

    def test_duplicate_git_tree_entry_fails_closed(self):
        f = self.Fixture()
        root_sha = f.commit["commit"]["tree"]["sha"]
        f.trees[root_sha]["tree"].append(dict(f.trees[root_sha]["tree"][0]))
        self.assert_blocked(f, "invalid-or-duplicate-git-tree-entry")

    def test_result_fingerprint_is_stable_and_changes_with_output(self):
        a = self.Fixture()
        left = a.report()
        self.assertEqual(left["selectedOutputFingerprint"], a.report()["selectedOutputFingerprint"])
        a.files["public/data/League.json"] = b'{"changed":true}'
        a.compile()
        right = a.report()
        self.assertTrue(right["selectedGitOutputBlobIdsVerified"])
        self.assertNotEqual(left["selectedOutputFingerprint"], right["selectedOutputFingerprint"])
        self.assertFalse(right["safeToSkip"])

    def test_no_production_workflow_invocation_or_skip_authorization(self):
        workflow = (Path(__file__).resolve().parents[2] / ".github/workflows/league-live.yml").read_text()
        self.assertNotIn("league_live_output_revision_audit.py", workflow)
        result = self.Fixture().report()
        self.assertFalse(result["safeToSkip"])
        self.assertFalse(result["enforced"])



class DraftContentAuditTests(unittest.TestCase):
    def fixture(self):
        drafts = [
            {"DraftKey": "2026_Rookie", "Season": "2026",
             "Picks": [{"PickKey": "2026_Rookie_R1_OO1", "CurrentOwnerRosterID": 2}]},
            {"DraftKey": "2031_Rookie", "Season": "2031",
             "Picks": [{"PickKey": "2031_Rookie_R1_OO2", "CurrentOwnerRosterID": 1}]},
            {"DraftKey": "2032_Free_Agent", "Season": "2032",
             "Picks": [{"PickKey": "2032_Free_Agent_R1_OO1", "CurrentOwnerRosterID": 2}]},
        ]
        teams = [
            {"TeamID": 1, "DraftPicks": ["2031_Rookie_R1_OO2"]},
            {"TeamID": 2, "DraftPicks": ["2026_Rookie_R1_OO1", "2032_Free_Agent_R1_OO1"]},
        ]
        return drafts, teams

    def test_owner_projection_has_dynamic_future_years_and_trades(self):
        drafts, teams = self.fixture()
        self.assertEqual([], shadow.compare_draft_owner_membership(drafts, teams))
        self.assertEqual({2026, 2031, 2032}, {int(d["Season"]) for d in drafts})

    def test_owner_projection_rejects_missing_extra_duplicate_and_wrong_team(self):
        drafts, teams = self.fixture()
        wrong = [{"TeamID": 1, "DraftPicks": [
            "2031_Rookie_R1_OO2", "2026_Rookie_R1_OO1", "extraneous"]},
                 {"TeamID": 2, "DraftPicks": [
                     "2026_Rookie_R1_OO1", "2032_Free_Agent_R1_OO1"]}]
        result = shadow.compare_draft_owner_membership(drafts, wrong)
        self.assertIn("league-owner-mismatch:2026_Rookie_R1_OO1", result)
        self.assertIn("duplicate-league-pick-key:2026_Rookie_R1_OO1", result)
        self.assertIn("league-extra-pick:extraneous", result)
        missing = [{"TeamID": 1, "DraftPicks": []}, {"TeamID": 2, "DraftPicks": []}]
        self.assertIn("league-missing-pick:2031_Rookie_R1_OO2",
                      shadow.compare_draft_owner_membership(drafts, missing))
        duplicate_drafts = list(drafts) + [drafts[0]]
        self.assertIn("duplicate-app-pick-key:2026_Rookie_R1_OO1",
                      shadow.compare_draft_owner_membership(duplicate_drafts, teams))

    def test_owner_projection_rejects_unknown_team_and_malformed_inputs(self):
        drafts, teams = self.fixture()
        drafts[0]["Picks"][0]["CurrentOwnerRosterID"] = 99
        self.assertIn("owner-has-no-team:2026_Rookie_R1_OO1",
                      shadow.compare_draft_owner_membership(drafts, teams))
        self.assertTrue(shadow.compare_draft_owner_membership([], teams))
        self.assertTrue(shadow.compare_draft_owner_membership(drafts, [{"TeamID": 1, "DraftPicks": "not-list"}]))

    def test_offline_audit_reuses_history_and_never_authorizes_live_skip(self):
        drafts, teams = self.fixture()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = root / "public/data"
            data.mkdir(parents=True)
            (data / "Drafts.json").write_text(json.dumps(drafts), encoding="utf-8")
            (data / "League.json").write_text(json.dumps({"Teams": teams}), encoding="utf-8")
            with patch("tools.league_history_app_publish.load_inputs",
                       return_value=SimpleNamespace(league_year=2026)), patch(
                       "tools.league_history_app_publish.build_history",
                       return_value=SimpleNamespace(unresolved=[])), patch(
                       "tools.league_history_app_publish.verified_product_history",
                       return_value=(object(), None)), patch(
                       "tools.league_history_app_publish.render",
                       return_value={"Drafts": {"current": drafts}}):
                result = shadow.audit_draft_content(root, "nfl-reise")
                self.assertEqual("verified", result["status"])
                self.assertEqual([2026, 2031, 2032], result["draftSeasons"])
                self.assertEqual(3, result["picks"])
                self.assertTrue(result["contentParityVerified"])
                self.assertFalse(result["safeToSkip"])
                self.assertFalse(result["enforced"])
                (data / "Drafts.json").write_text("[]", encoding="utf-8")
                invalid = shadow.audit_draft_content(root, "nfl-reise")
                self.assertEqual("blocked", invalid["status"])
                self.assertFalse(invalid["contentParityVerified"])

    def test_offline_audit_missing_future_derived_partition_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("tools.league_history_app_publish.load_inputs",
                       return_value=SimpleNamespace(league_year=2026)), patch(
                       "tools.league_history_app_publish.build_history",
                       return_value=SimpleNamespace(unresolved=[])), patch(
                       "tools.league_history_app_publish.verified_product_history",
                       side_effect=ValueError("Stale Shared Derived league-drafts/2031")):
                result = shadow.audit_draft_content(Path(tmp), "nfl-reise")
                self.assertEqual("blocked", result["status"])
                self.assertFalse(result["contentParityVerified"])
                self.assertFalse(result["safeToSkip"])
                self.assertIn("2031", result["errors"][0])

    def test_offline_audit_cli_is_separate_from_live_and_requires_league(self):
        with patch.object(shadow, "audit_draft_content", return_value={
            "contentParityVerified": True, "safeToSkip": False, "enforced": False,
        }) as audit:
            with patch("builtins.print"):
                self.assertEqual(0, shadow.main(["--audit-draft-content", "--league", "nfl-reise"]))
            audit.assert_called_once()
        with self.assertRaises(SystemExit):
            shadow.main(["--audit-draft-content"])
        with self.assertRaises(SystemExit):
            shadow.main(["--audit-draft-content", "--league", "nfl-reise", "--stage", "league"])


class ShadowLogComparisonTests(unittest.TestCase):
    def log(self, stage: str = "league", at: str = "2026-11-03T20:17:31Z",
            changed_path: str | None = None, no_op: bool = True) -> str:
        trees = {name: "a" * 40 for name in shadow.STAGE_INPUTS[stage]}
        if changed_path:
            trees[changed_path] = "b" * 40
        row = {
            "schemaVersion": shadow.SCHEMA, "stage": stage, "atUtc": at,
            "checkedOutHead": "c" * 40, "decision": "would-run", "enforced": False,
            "inputTrees": trees, "inputFingerprint": shadow.fingerprint(trees),
            "missingOutputs": [], "reasonCodes": ["missing-previous-successful-attestation"],
        }
        return ("20:01 log before\n20:02 LEAGUE_LIVE_SHADOW " + json.dumps(row)
                + "\n" + ("Generator produced no repository changes. Nothing to publish."
                          if no_op else "Generator produced changes"))

    def test_equal_input_evidence_never_authorizes_skip(self):
        observed = shadow.compare_observed_logs(self.log(), self.log(at="2026-11-03T20:31:30Z"))
        self.assertEqual("same-observed-inputs", observed["classification"])
        self.assertEqual([], observed["changedPaths"])
        self.assertTrue(observed["previousPublisherNoOpLogMarker"])
        self.assertTrue(observed["currentPublisherNoOpLogMarker"])
        self.assertFalse(observed["safeToSkip"])
        self.assertFalse(observed["enforced"])
        self.assertIn("temporal-boundary-safety", observed["unproven"])

    def test_source_finality_derived_meta_changes_invalidate_input_equality(self):
        for path in ("data-source", "data-derived", "data-meta"):
            with self.subTest(path=path):
                observed = shadow.compare_observed_logs(
                    self.log(), self.log(at="2026-11-03T20:31:30Z", changed_path=path))
                self.assertEqual("changed-input-revision", observed["classification"])
                self.assertEqual([path], observed["changedPaths"])
                self.assertFalse(observed["safeToSkip"])

    def test_different_stages_rejected(self):
        with self.assertRaisesRegex(ValueError, "stages"):
            shadow.compare_observed_logs(self.log("standings"), self.log("league"))

    def test_duplicate_missing_malformed_observations_are_rejected(self):
        good = self.log()
        for text in (good + "\n" + good, "no shadow record", "LEAGUE_LIVE_SHADOW {bad-json"):
            with self.subTest(text=text[:25]):
                with self.assertRaises(ValueError):
                    shadow.compare_observed_logs(text, good)

    def test_nonmonotonic_time_bad_signature_and_missing_output_fail_closed(self):
        earlier = self.log()
        reversed_order = shadow.compare_observed_logs(
            earlier, self.log(at="2026-11-03T20:00:00Z"))
        self.assertEqual("unverifiable", reversed_order["classification"])
        bad = self.log(at="2026-11-03T20:31:30Z").replace('"inputFingerprint": "', '"inputFingerprint": "bad')
        self.assertEqual("unverifiable", shadow.compare_observed_logs(earlier, bad)["classification"])
        absent = self.log(at="2026-11-03T20:31:30Z").replace('"missingOutputs": []', '"missingOutputs": ["public/data/League.json"]')
        self.assertEqual("unverifiable", shadow.compare_observed_logs(earlier, absent)["classification"])

    def test_publisher_noop_is_only_log_marker_not_asserted_success(self):
        result = shadow.compare_observed_logs(
            self.log(), self.log(at="2026-11-03T20:31:30Z", no_op=False))
        self.assertEqual("same-observed-inputs", result["classification"])
        self.assertFalse(result["currentPublisherNoOpLogMarker"])
        self.assertFalse(result["safeToSkip"])

    def test_compare_log_files_cli_keeps_existing_live_stage_separate(self):
        with tempfile.TemporaryDirectory() as temp:
            earlier, later = Path(temp) / "earlier.log", Path(temp) / "later.log"
            earlier.write_text(self.log(), encoding="utf-8")
            later.write_text(self.log(at="2026-11-03T20:31:30Z"), encoding="utf-8")
            with patch("builtins.print") as printed:
                rc = shadow.main(["--compare-log-files", str(earlier), str(later)])
            self.assertEqual(0, rc)
            self.assertEqual("same-observed-inputs", json.loads(printed.call_args[0][0])["classification"])
            self.assertFalse(json.loads(printed.call_args[0][0])["safeToSkip"])
            self.assertEqual(2, shadow.main(["--compare-log-files", str(earlier), str(Path(temp) / "missing")]))

if __name__ == "__main__":
    unittest.main()
