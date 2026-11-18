"""Fast, synthetic safety checks for the read-only three-way restore probe (#471)."""
from __future__ import annotations

import sys
import subprocess
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
import derived_clean_root_audit as probe  # noqa: E402

LEAGUE = "league-a"
STANDINGS_ERROR = "Draft order needs the transitional Standings input, but none is available."


def emit(path: Path, text: str) -> int:
    """Write like a materializer: return 1 when the file changed, else 0."""
    if path.is_file() and path.read_text() == text:
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return 1


class CleanRootProbeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / "data-source").mkdir()
        self.add_league(LEAGUE)
        self.calls: list[tuple] = []
        self.hooks: dict = {}

    def add_league(self, league: str):
        meta = self.root / "data-meta" / league
        meta.mkdir(parents=True, exist_ok=True)
        (meta / "metadata.json").write_text("{}")

    def publish(self, relative: str, text: str):
        path = self.root / "data-derived" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    # --- fake generators -------------------------------------------------
    def body(self, key: str, root: Path, existing: str | None, extra=None) -> str:
        """Default deterministic content; hooks[key] may override it."""
        hook = self.hooks.get(key)
        return hook(root, existing, extra) if hook else "stable"

    def check_isolation(self, root: Path):
        self.assertTrue((root / "data-source").is_symlink())
        self.assertTrue((root / "data-meta").is_symlink())
        self.assertNotEqual(root.resolve(), self.root.resolve())

    def fake_valuation(self, root, out_root, league, seasons, check_only):
        self.check_isolation(root)
        self.calls.append(("player-valuation", league))
        target = out_root / "player-valuation" / league / "2024/week-00.json"
        existing = target.read_text() if target.is_file() else None
        written = emit(target, self.body("player-valuation", root, existing))
        return {"Seasons": [{"Written": written, "HeldRowsAcrossSnapshots": 0}]}

    def fake_history(self, root, out_root, league, product, seasons, check_only):
        self.check_isolation(root)
        self.calls.append((product, league))
        target = out_root / product / league / "2024.json"
        existing = target.read_text() if target.is_file() else None
        written = emit(target, self.body(product, root, existing))
        return {"Seasons": [{"Written": written}]}

    def fake_standings(self, root, out_root, league, seasons, check_only):
        self.check_isolation(root)
        self.calls.append(("league-standings", league))
        target = out_root / "league-standings" / league / "2024.json"
        existing = target.read_text() if target.is_file() else None
        written = emit(target, self.body("league-standings", root, existing))
        return {"Seasons": [{"Written": written}]}

    def fake_season_statistics(self, root, out_root, league, seasons, check_only):
        self.check_isolation(root)
        self.calls.append(("season-statistics", league))
        target = out_root / "season-statistics" / league / "2024.json"
        existing = target.read_text() if target.is_file() else None
        written = emit(target, self.body("season-statistics", root, existing))
        return {"Seasons": [{"Written": written}]}

    def fake_league_rivalry(self, root, out_root, league, seasons, check_only):
        self.check_isolation(root)
        self.calls.append(("league-rivalry", league))
        target = out_root / "league-rivalry" / f"{league}.json"
        existing = target.read_text() if target.is_file() else None
        written = emit(target, self.body("league-rivalry", root, existing))
        return {"Seasons": [{"Written": written}]}

    def fake_pwf(self, root, *, league_id, write):
        self.calls.append(("player-week-fantasy", league_id))
        target = root / "data-derived/player-week-fantasy" / league_id / "2024/01.json"
        existing = target.read_text() if target.is_file() else None
        if "player-week-fantasy" in self.hooks and self.hooks["player-week-fantasy"] == "blocked":
            return {"BlockedCount": 1, "Weeks": [{"Status": "blocked", "Reason": "week not final"}]}
        written = emit(target, self.body("player-week-fantasy", root, existing))
        return {"BlockedCount": 0, "ChangedCount": written, "Weeks": []}

    def fake_twp(self, root, *, league_id, write, require_pwf):
        self.assertFalse(require_pwf)  # Official Sleeper awards must restore without PWF.
        self.calls.append(("team-week-performance", league_id))
        target = root / "data-derived/team-week-performance" / league_id / "2024/01.json"
        existing = target.read_text() if target.is_file() else None
        written = emit(target, self.body("team-week-performance", root, existing))
        return {"BlockedCount": 0, "ChangedCount": written, "Weeks": []}

    def fake_nfl_games(self, root, season, *, write):
        self.calls.append(("nfl-games", None))
        target = root / "data-derived/nfl-games" / f"{season}.json"
        existing = target.read_text() if target.is_file() else None
        return {"Written": bool(emit(target, self.body("nfl-games", root, existing)))}

    def fake_injuries(self, source_root, season, phase):
        # The canonical producer is called against the real Source root, not
        # against a shadow symlink or a previously published Derived product.
        self.assertEqual("derived", phase)
        self.assertEqual(self.root.resolve(), source_root.resolve())
        self.calls.append(("nfl-injuries", None))
        if self.hooks.get("nfl-injuries") == "blocked":
            raise ValueError("canonical Injury manifest is missing or invalid")
        content = self.body("nfl-injuries", source_root, None)
        return {f"data-derived/nfl-injuries/{season}.json": content.encode("utf-8")}

    def run_audit(self, **kwargs):
        with ExitStack() as stack:
            for name, fake in (
                ("materialize_player_valuation", self.fake_valuation),
                ("materialize_league_history", self.fake_history),
                ("materialize_league_standings", self.fake_standings),
                ("materialize_season_statistics", self.fake_season_statistics),
                ("materialize_league_rivalry", self.fake_league_rivalry),
                ("materialize_historical", self.fake_pwf),
                ("materialize_all_finalized", self.fake_twp),
                ("materialize_nfl_games", self.fake_nfl_games),
                ("plan_injury_phase", self.fake_injuries),
            ):
                stack.enter_context(patch.object(probe, name, side_effect=fake))
            stack.enter_context(patch.object(probe, "discover_seasons", return_value=[2024]))
            stack.enter_context(patch.object(probe, "discover_injury_seasons", return_value=[2024]))
            return probe.audit(self.root, **kwargs)

    def publish_all_stable(self):
        for relative in (
            f"player-valuation/{LEAGUE}/2024/week-00.json", f"league-transactions/{LEAGUE}/2024.json",
            f"league-drafts/{LEAGUE}/2024.json", f"league-standings/{LEAGUE}/2024.json", f"season-statistics/{LEAGUE}/2024.json", f"league-rivalry/{LEAGUE}.json", f"player-week-fantasy/{LEAGUE}/2024/01.json",
            f"team-week-performance/{LEAGUE}/2024/01.json", "nfl-games/2024.json", "nfl-injuries/2024.json",
        ):
            self.publish(relative, "stable")

    # --- tests ---------------------------------------------------------------
    def test_all_products_ready_and_repository_untouched(self):
        self.publish_all_stable()
        result = self.run_audit()
        self.assertTrue(result["ReadyForFullRestore"])
        self.assertTrue(result["ReadOnly"])
        self.assertFalse(result["Published"])
        self.assertEqual([], result["FailedProducts"])
        self.assertEqual({}, result["HintProducts"])
        self.assertEqual(
            {f"{p}/{LEAGUE}" for p in probe.PRODUCTS if p not in probe.GLOBAL_PRODUCTS} | {"nfl-games", "nfl-injuries"},
            set(result["Products"]),
        )
        for entry in result["Products"].values():
            self.assertEqual("ready", entry["Status"])
            self.assertEqual(1, entry["RebuiltCount"])
            self.assertEqual(0, entry["SecondPassWrites"])
        self.assertEqual("stable", (self.root / f"data-derived/league-drafts/{LEAGUE}/2024.json").read_text())
        self.assertFalse((self.root / "public").exists())

    def test_published_behind_is_a_hint_not_a_failure(self):
        self.publish_all_stable()
        self.publish(f"player-valuation/{LEAGUE}/2024/week-00.json", "old")
        self.publish(f"league-transactions/{LEAGUE}/2023.json", "orphan")  # nothing builds this file
        (self.root / "data-derived" / "nfl-games" / "2024.json").unlink()  # missing in published
        result = self.run_audit()
        self.assertTrue(result["ReadyForFullRestore"])
        self.assertEqual(
            {
                f"player-valuation/{LEAGUE}": "stale-published",
                f"league-transactions/{LEAGUE}": "stale-published",
                "nfl-games": "stale-published",
            },
            result["HintProducts"],
        )
        valuation = result["Products"][f"player-valuation/{LEAGUE}"]
        self.assertEqual(1, valuation["ChangedVsPublishedCount"])
        self.assertEqual(1, result["Products"]["nfl-games"]["MissingInPublishedCount"])
        self.assertEqual(1, result["Products"][f"league-transactions/{LEAGUE}"]["OrphanedPublishedCount"])
        self.assertEqual("old", (self.root / f"data-derived/player-valuation/{LEAGUE}/2024/week-00.json").read_text())

    def test_hidden_dependency_on_existing_output_is_a_restore_defect(self):
        self.publish_all_stable()
        # Keeps whatever exists, builds "fresh" from nothing: empty and normal root diverge.
        self.hooks["league-drafts"] = lambda root, existing, extra: existing or "fresh"
        self.publish(f"league-drafts/{LEAGUE}/2024.json", "carried-over")
        result = self.run_audit()
        entry = result["Products"][f"league-drafts/{LEAGUE}"]
        self.assertEqual("restore-defect", entry["Status"])
        self.assertEqual(["2024.json"], entry["RestoreDefectExamples"]["Differing"])
        self.assertEqual([f"league-drafts/{LEAGUE}"], result["FailedProducts"])
        self.assertFalse(result["ReadyForFullRestore"])

    def test_corrupted_published_players_cannot_seed_normal_restore(self):
        self.publish_all_stable()
        (self.root / "public/data").mkdir(parents=True)
        (self.root / "public/data/Players.json").write_text("{poisoned")
        self.hooks["player-valuation"] = lambda root, existing, extra: (
            "seeded" if (root / "public/data/Players.json").exists() else "stable"
        )
        result = self.run_audit()
        self.assertEqual("ready", result["Products"][f"player-valuation/{LEAGUE}"]["Status"])
        self.assertEqual(3, self.calls.count(("player-valuation", LEAGUE)))

    def test_second_pass_change_is_nondeterministic(self):
        self.publish_all_stable()
        counter = {"n": 0}

        def drift(root, existing, extra):
            counter["n"] += 1
            return f"run-{counter['n']}"

        self.hooks["nfl-games"] = drift
        result = self.run_audit()
        entry = result["Products"]["nfl-games"]
        self.assertEqual("nondeterministic", entry["Status"])
        self.assertEqual(["nfl-games"], result["FailedProducts"])

    def test_injury_restore_detects_stale_published_and_does_not_overwrite(self):
        self.publish_all_stable()
        self.publish("nfl-injuries/2024.json", "stale")
        result = self.run_audit()
        self.assertTrue(result["ReadyForFullRestore"])
        self.assertEqual("stale-published", result["Products"]["nfl-injuries"]["Status"])
        self.assertEqual(1, result["Products"]["nfl-injuries"]["ChangedVsPublishedCount"])
        self.assertEqual("stale", (self.root / "data-derived/nfl-injuries/2024.json").read_text())
        self.assertEqual(3, self.calls.count(("nfl-injuries", None)))

    def test_missing_injury_canonical_input_fails_closed(self):
        self.publish_all_stable()
        self.hooks["nfl-injuries"] = "blocked"
        result = self.run_audit()
        self.assertEqual("blocked", result["Products"]["nfl-injuries"]["Status"])
        self.assertIn("canonical Injury manifest", result["Products"]["nfl-injuries"]["Reason"])
        self.assertIn("nfl-injuries", result["FailedProducts"])

    def test_nondeterministic_injury_restore_is_not_green(self):
        self.publish_all_stable()
        counter = {"n": 0}

        def drift(root, existing, extra):
            counter["n"] += 1
            return f"revision-{counter['n']}"

        self.hooks["nfl-injuries"] = drift
        result = self.run_audit()
        self.assertEqual("nondeterministic", result["Products"]["nfl-injuries"]["Status"])
        self.assertIn("nfl-injuries", result["FailedProducts"])

    def test_failed_pwf_build_does_not_block_official_sleeper_award_restore(self):
        self.publish_all_stable()
        self.hooks["player-week-fantasy"] = "blocked"
        result = self.run_audit()
        pwf = result["Products"][f"player-week-fantasy/{LEAGUE}"]
        self.assertEqual("blocked", pwf["Status"])
        self.assertIn("week not final", pwf["Reason"])
        twp = result["Products"][f"team-week-performance/{LEAGUE}"]
        self.assertEqual("ready", twp["Status"])
        self.assertEqual([f"player-week-fantasy/{LEAGUE}"], result["FailedProducts"])

    def test_latent_standings_dependency_is_reported_as_hint_for_issue_987(self):
        self.publish_all_stable()
        (self.root / "public/data").mkdir(parents=True)
        (self.root / "public/data/Standings.json").write_text("{}")

        def needs_standings(root, existing, extra):
            if not (root / "public/data/Standings.json").exists():
                raise ValueError(STANDINGS_ERROR)
            return "stable"

        self.hooks["league-drafts"] = needs_standings
        result = self.run_audit()
        entry = result["Products"][f"league-drafts/{LEAGUE}"]
        self.assertEqual("latent-blocker", entry["Status"])
        self.assertEqual("#987", entry["LatentBlocker"])
        self.assertIn("Standings", entry["Reason"])
        self.assertEqual({f"league-drafts/{LEAGUE}": "latent-blocker"}, result["HintProducts"])
        self.assertTrue(result["ReadyForFullRestore"])
        self.assertEqual("ready", result["Products"][f"league-transactions/{LEAGUE}"]["Status"])

    def test_standings_error_without_published_standings_stays_blocked(self):
        self.publish_all_stable()
        self.hooks["league-drafts"] = lambda root, existing, extra: (_ for _ in ()).throw(ValueError(STANDINGS_ERROR))
        result = self.run_audit()
        self.assertEqual("blocked", result["Products"][f"league-drafts/{LEAGUE}"]["Status"])
        self.assertFalse(result["ReadyForFullRestore"])

    def test_every_league_in_data_meta_is_audited(self):
        self.add_league("league-b")
        for league in (LEAGUE, "league-b"):
            for relative in (
                f"player-valuation/{league}/2024/week-00.json", f"league-transactions/{league}/2024.json",
                f"league-drafts/{league}/2024.json", f"league-standings/{league}/2024.json", f"player-week-fantasy/{league}/2024/01.json",
                f"team-week-performance/{league}/2024/01.json",
            ):
                self.publish(relative, "stable")
        self.publish("nfl-games/2024.json", "stable")
        self.publish("nfl-injuries/2024.json", "stable")
        result = self.run_audit()
        self.assertEqual([LEAGUE, "league-b"], result["Leagues"])
        self.assertTrue(result["ReadyForFullRestore"])
        for product in ("player-valuation", "league-transactions", "league-drafts", "league-standings",
                        "player-week-fantasy", "team-week-performance"):
            self.assertIn(f"{product}/league-b", result["Products"])
        self.assertEqual(3, self.calls.count(("nfl-games", None)))  # global product: once per pass, not per league
        self.assertEqual(3, self.calls.count(("nfl-injuries", None)))

    def test_explicit_league_selection(self):
        self.add_league("league-b")
        self.publish_all_stable()
        result = self.run_audit(leagues=[LEAGUE])
        self.assertEqual([LEAGUE], result["Leagues"])
        self.assertFalse(any(key.endswith("league-b") for key in result["Products"]))

    def test_summary_lists_errors_first_and_names_hints(self):
        result = {
            "Leagues": [LEAGUE], "FailedProducts": ["b/league-a"],
            "HintProducts": {"c/league-a": "stale-published"},
            "Products": {
                "a/league-a": {"Status": "ready"},
                "b/league-a": {"Status": "restore-defect", "Reason": "differs | here"},
                "c/league-a": {"Status": "stale-published", "Reason": "behind"},
            },
        }
        text = probe.render_summary(result)
        self.assertIn("**FAIL**", text)
        self.assertLess(text.index("b/league-a"), text.index("a/league-a"))
        self.assertIn("c/league-a = stale-published", text)
        self.assertNotIn("differs | here", text)
        result.update(FailedProducts=[], HintProducts={})
        self.assertIn("**PASS**", probe.render_summary(result))

    def test_missing_canonical_root_denies_execution(self):
        (self.root / "data-meta" / LEAGUE / "metadata.json").unlink()
        (self.root / "data-meta" / LEAGUE).rmdir()
        (self.root / "data-meta").rmdir()
        with self.assertRaisesRegex(ValueError, "Missing required canonical root"):
            probe.audit(self.root)

    def test_no_league_denies_execution(self):
        (self.root / "data-meta" / LEAGUE / "metadata.json").unlink()
        with self.assertRaisesRegex(ValueError, "No league found"):
            probe.audit(self.root)


class ScheduleOutlookCandidateRestoreTests(unittest.TestCase):
    """Candidate contract is tested without adding a live Derived writer."""

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        (self.root / "data-source").mkdir()
        (self.root / "data-meta" / LEAGUE).mkdir(parents=True)
        (self.root / "data-meta" / LEAGUE / "metadata.json").write_text("{}")

    def run_candidate(self, *, poisoned_snapshot=False, fake_second_write=False, seasons=None):
        if poisoned_snapshot:
            old = self.root / "data-derived/league-schedule-outlook" / LEAGUE / "2024/after-week-00.json"
            old.parent.mkdir(parents=True, exist_ok=True)
            old.write_text('{"stale":"poison"}')
        else:
            old = None

        def build(shadow, league, years):
            self.assertEqual(LEAGUE, league)
            self.assertEqual([2024], years)
            changed = 0
            for product_name in ("player-week-fantasy", "team-week-performance", "season-statistics"):
                target = shadow / "data-derived" / product_name / LEAGUE / "2024.json"
                changed += emit(target, "fresh-from-source")
            return 3 if fake_second_write else changed

        def preview(shadow, league, year):
            self.assertEqual(LEAGUE, league)
            self.assertEqual(2024, year)
            self.assertTrue((shadow / "data-source").is_symlink())
            self.assertTrue((shadow / "data-meta").is_symlink())
            self.assertFalse((shadow / "public/data/Players.json").exists())
            self.assertEqual(
                "fresh-from-source",
                (shadow / "data-derived/season-statistics" / LEAGUE / "2024.json").read_text(),
            )
            poisoned = (shadow / "data-derived/league-schedule-outlook" / LEAGUE
                        / "2024/after-week-00.json").is_file()
            return {"LastLeagueScoredWeek": 1,
                    "Snapshots": [{"Season": year, "AsOf": {"AfterWeek": w},
                                   "Poisoned": poisoned} for w in range(2)]}

        def assemble(row, *, selected_model_id):
            self.assertEqual("schedule-outlook-v1", selected_model_id)
            return {"Season": row["Season"], "AsOf": row["AsOf"], "Poisoned": row["Poisoned"]}

        with ExitStack() as stack:
            stack.enter_context(patch.object(probe, "get_model", return_value=object()))
            stack.enter_context(patch.object(probe, "load_league_metadata",
                                             return_value={"Seasons": {"2024": {}, "2025": {}}}))
            stack.enter_context(patch.object(probe, "_build_schedule_outlook_candidate_upstream", side_effect=build))
            stack.enter_context(patch.object(probe, "preview_all", side_effect=preview))
            stack.enter_context(patch.object(probe, "assemble", side_effect=assemble))
            report = probe.audit_schedule_outlook_candidate(
                self.root, LEAGUE, seasons=[2024] if seasons is None else seasons,
                selected_model_id="schedule-outlook-v1")
        return report, old

    def test_source_only_rebuild_noop_and_canonical_repository_not_written(self):
        report, old = self.run_candidate()
        self.assertTrue(report["CandidatePass"])
        self.assertEqual("schedule-outlook-candidate-source-only-restore", report["Mode"])
        self.assertEqual(2, report["SnapshotCount"])
        self.assertFalse(report["CompleteConfiguredSeasonCoverage"])
        self.assertFalse(report["SourceRevisionVerified"])
        self.assertFalse(report["ReadyForPublication"])
        self.assertEqual(0, report["SecondPassUpstreamWrites"])
        self.assertTrue(report["SecondPassByteIdentical"])
        self.assertTrue(report["EmptyAndNormalIdentical"])
        self.assertFalse(report["Published"])
        self.assertFalse(report["ModelSelectedInDataMeta"])
        self.assertIsNone(old)
        self.assertFalse((self.root / "data-derived/league-schedule-outlook").exists())

    def test_published_old_outlook_is_not_allowed_to_affect_candidate(self):
        report, old = self.run_candidate(poisoned_snapshot=True)
        self.assertFalse(report["CandidatePass"])
        self.assertTrue(report["SecondPassByteIdentical"])
        self.assertFalse(report["EmptyAndNormalIdentical"])
        self.assertEqual(["2024/after-week-00.json", "2024/after-week-01.json"],
                         report["DigestDifferences"]["Differing"])
        self.assertEqual('{"stale":"poison"}', old.read_text())

    def test_upstream_second_pass_write_denies_noop(self):
        report, _ = self.run_candidate(fake_second_write=True)
        self.assertFalse(report["CandidatePass"])
        self.assertEqual(3, report["SecondPassUpstreamWrites"])
        self.assertFalse(report["SecondPassByteIdentical"])

    def test_candidate_upstream_only_materializes_selected_seasons_in_order(self):
        with patch.object(probe, "materialize_historical",
                          return_value={"BlockedCount": 0, "ChangedCount": 2}) as pwf, \
             patch.object(probe, "materialize_all_finalized",
                          return_value={"BlockedCount": 0, "ChangedCount": 3}) as twp, \
             patch.object(probe, "materialize_season_statistics",
                          return_value={"Seasons": [{"Written": 1}]}) as stats:
            writes = probe._build_schedule_outlook_candidate_upstream(self.root, LEAGUE, [2025])
        self.assertEqual(6, writes)
        pwf.assert_called_once_with(self.root, league_id=LEAGUE, seasons=[2025], write=True)
        twp.assert_called_once_with(self.root, league_id=LEAGUE, seasons=[2025],
                                    write=True, require_pwf=False)
        stats.assert_called_once_with(self.root, self.root / "data-derived", LEAGUE, [2025], False)

    def test_missing_pwf_source_fails_closed_before_downstream(self):
        with patch.object(probe, "materialize_historical",
                          return_value={"BlockedCount": 1, "Weeks": [
                              {"Status": "blocked", "Reason": "missing week"}]}) as pwf, \
             patch.object(probe, "materialize_all_finalized") as twp:
            with self.assertRaisesRegex(ValueError, "missing week"):
                probe._build_schedule_outlook_candidate_upstream(self.root, LEAGUE, [2026])
        pwf.assert_called_once()
        twp.assert_not_called()

    def test_git_witness_requires_committed_clean_source_and_metadata(self):
        def git(*args):
            return subprocess.run(["git", "-C", str(self.root), *args],
                                  capture_output=True, text=True, check=True)
        git("init", "-q")
        (self.root / "data-source" / "sample.json").write_text("{}")
        git("add", "data-source", "data-meta")
        git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
            "commit", "-qm", "fixture")
        witness = probe._schedule_outlook_source_witness(self.root)
        self.assertIsNotNone(witness)
        self.assertEqual(40, len(witness["SourceTree"]))
        self.assertEqual(witness, probe._schedule_outlook_source_witness(self.root))
        (self.root / "data-source" / "untracked.json").write_text("{}")
        self.assertIsNone(probe._schedule_outlook_source_witness(self.root))
        (self.root / "data-source" / "untracked.json").unlink()
        (self.root / "data-meta" / LEAGUE / "metadata.json").write_text('{"changed":true}')
        self.assertIsNone(probe._schedule_outlook_source_witness(self.root))

    def test_unconfigured_season_and_missing_candidate_model_fail_closed(self):
        with patch.object(probe, "get_model", return_value=object()), \
             patch.object(probe, "load_league_metadata", return_value={"Seasons": {"2024": {}}}):
            with self.assertRaisesRegex(ValueError, "not configured"):
                probe.audit_schedule_outlook_candidate(
                    self.root, LEAGUE, seasons=[2025], selected_model_id="schedule-outlook-v1")
            with self.assertRaisesRegex(ValueError, "explicit candidate"):
                probe.audit_schedule_outlook_candidate(
                    self.root, LEAGUE, seasons=[2024], selected_model_id="")


if __name__ == "__main__":
    unittest.main()
