"""Fast, synthetic safety checks for the read-only three-way restore probe (#471)."""
from __future__ import annotations

import sys
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

    def fake_valuation(self, root, out_root, league, seasons, check_only, hold_seed=None):
        self.check_isolation(root)
        self.calls.append(("player-valuation", league, hold_seed is not None))
        target = out_root / "player-valuation" / league / "2024/week-00.json"
        existing = target.read_text() if target.is_file() else None
        written = emit(target, self.body("player-valuation", root, existing, hold_seed))
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

    def run_audit(self, **kwargs):
        with ExitStack() as stack:
            for name, fake in (
                ("materialize_player_valuation", self.fake_valuation),
                ("materialize_league_history", self.fake_history),
                ("materialize_league_standings", self.fake_standings),
                ("materialize_historical", self.fake_pwf),
                ("materialize_all_finalized", self.fake_twp),
                ("materialize_nfl_games", self.fake_nfl_games),
            ):
                stack.enter_context(patch.object(probe, name, side_effect=fake))
            stack.enter_context(patch.object(probe, "discover_seasons", return_value=[2024]))
            return probe.audit(self.root, **kwargs)

    def publish_all_stable(self):
        for relative in (
            f"player-valuation/{LEAGUE}/2024/week-00.json", f"league-transactions/{LEAGUE}/2024.json",
            f"league-drafts/{LEAGUE}/2024.json", f"league-standings/{LEAGUE}/2024.json", f"player-week-fantasy/{LEAGUE}/2024/01.json",
            f"team-week-performance/{LEAGUE}/2024/01.json", "nfl-games/2024.json",
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
            {f"{p}/{LEAGUE}" for p in probe.PRODUCTS if p not in probe.GLOBAL_PRODUCTS} | {"nfl-games"},
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

    def test_hold_seed_only_in_the_productive_like_root(self):
        self.publish_all_stable()
        (self.root / "public/data").mkdir(parents=True)
        (self.root / "public/data/Players.json").write_text("[]")
        self.hooks["player-valuation"] = lambda root, existing, seed: "seeded" if seed is not None else "stable"
        with patch.object(probe, "load_hold_seed", return_value={"1": {}}):
            result = self.run_audit()
        self.assertEqual("restore-defect", result["Products"][f"player-valuation/{LEAGUE}"]["Status"])
        self.assertIn((("player-valuation", LEAGUE, True)), self.calls)
        self.assertIn((("player-valuation", LEAGUE, False)), self.calls)

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
        result = self.run_audit()
        self.assertEqual([LEAGUE, "league-b"], result["Leagues"])
        self.assertTrue(result["ReadyForFullRestore"])
        for product in ("player-valuation", "league-transactions", "league-drafts", "league-standings",
                        "player-week-fantasy", "team-week-performance"):
            self.assertIn(f"{product}/league-b", result["Products"])
        self.assertEqual(3, self.calls.count(("nfl-games", None)))  # global product: once per pass, not per league

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


if __name__ == "__main__":
    unittest.main()
