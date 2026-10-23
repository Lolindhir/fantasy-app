"""Fast, synthetic safety checks for the read-only clean-root probe (#471)."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
import derived_clean_root_audit as probe  # noqa: E402


class CleanRootProbeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / "data-source").mkdir()
        (self.root / "data-meta").mkdir()
        self.calls = []

    def fake_valuation(self, root, out_root, league, seasons, check_only):
        self.assertEqual(league, "nfl-reise")
        self.assertTrue((root / "data-source").is_symlink())
        self.assertTrue((root / "data-meta").is_symlink())
        self.assertFalse((root / "public/data/Standings.json").exists())
        self.assertFalse((root / "public/data/Players.json").exists())
        self.assertNotEqual(root.resolve(), self.root.resolve())
        target = out_root / "player-valuation/nfl-reise/2024/week-00.json"
        was_different = not target.exists() or target.read_text() != '{"salary":1}\n'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('{"salary":1}\n')
        self.calls.append("valuation")
        return {"Seasons": [{"Written": int(was_different), "HeldRowsAcrossSnapshots": 0}]}

    def fake_history(self, root, out_root, league, product, seasons, check_only):
        self.assertFalse((root / "public/data/Standings.json").exists())
        target = out_root / product / league / "2024.json"
        was_different = not target.exists()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('{"items":[]}\n')
        self.calls.append(product)
        return {"Seasons": [{"Written": int(was_different)}]}

    def test_empty_derived_and_app_stay_isolated_and_second_pass_is_noop(self):
        with patch.object(probe, "materialize_player_valuation", side_effect=self.fake_valuation), \
             patch.object(probe, "materialize_league_history", side_effect=self.fake_history):
            result = probe.audit(self.root)
        self.assertTrue(result["ReadyForFullRestore"])
        self.assertTrue(result["ReadOnly"])
        self.assertFalse(result["Published"])
        self.assertEqual([], result["BlockedProducts"])
        self.assertEqual(2, self.calls.count("valuation"))
        for product in probe.PRODUCTS:
            self.assertEqual(1, result["Products"][product]["RebuiltCount"])
            self.assertEqual(0, result["Products"][product]["SecondPassWrites"])
        self.assertFalse((self.root / "data-derived").exists())
        self.assertFalse((self.root / "public").exists())

    def test_published_snapshot_drift_fails_closed(self):
        original = self.root / "data-derived/player-valuation/nfl-reise/2024/week-00.json"
        original.parent.mkdir(parents=True)
        original.write_text('{"salary":99}\n')
        with patch.object(probe, "materialize_player_valuation", side_effect=self.fake_valuation), \
             patch.object(probe, "materialize_league_history", side_effect=self.fake_history):
            result = probe.audit(self.root)
        self.assertFalse(result["ReadyForFullRestore"])
        valuation = result["Products"]["player-valuation"]
        self.assertEqual("blocked", valuation["Status"])
        self.assertEqual(1, valuation["ExistingMismatchCount"])
        self.assertEqual(original.read_text(), '{"salary":99}\n')

    def test_standings_dependency_blocks_only_history(self):
        def needs_standings(root, out_root, league, product, seasons, check_only):
            if not (root / "public/data/Standings.json").exists():
                raise ValueError("Draft order needs transitional Standings input")
            return self.fake_history(root, out_root, league, product, seasons, check_only)

        with patch.object(probe, "materialize_player_valuation", side_effect=self.fake_valuation), \
             patch.object(probe, "materialize_league_history", side_effect=needs_standings):
            result = probe.audit(self.root)
        self.assertEqual(["league-drafts", "league-transactions"], result["BlockedProducts"])
        self.assertEqual("ready", result["Products"]["player-valuation"]["Status"])
        self.assertIn("Standings", result["Products"]["league-drafts"]["Reason"])

    def test_second_pass_changed_bytes_blocks_without_publishing(self):
        count = 0
        def drift(root, out_root, league, seasons, check_only):
            nonlocal count
            count += 1
            target = out_root / "player-valuation/nfl-reise/2024/week-00.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(str(count))
            return {"Seasons": [{"Written": 1}]}
        with patch.object(probe, "materialize_player_valuation", side_effect=drift), \
             patch.object(probe, "materialize_league_history", side_effect=self.fake_history):
            result = probe.audit(self.root)
        self.assertIn("player-valuation", result["BlockedProducts"])
        self.assertFalse((self.root / "data-derived").exists())

    def test_missing_canonical_root_denies_execution(self):
        (self.root / "data-meta").rmdir()
        with self.assertRaisesRegex(ValueError, "Missing required canonical root"):
            probe.audit(self.root)


if __name__ == "__main__":
    unittest.main()
