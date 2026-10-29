"""League metadata loader (ADR-054): schema, fail-closed behavior, multi-league."""
from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
REPO_ROOT = TOOLS.parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import league_metadata as lm  # noqa: E402

LEAGUE = "nfl-reise"


def real_metadata() -> dict:
    return lm.load_league_metadata(LEAGUE)


class LeagueMetadataLoaderTests(unittest.TestCase):
    def write_league(self, root: Path, league_id: str, mutate=None) -> None:
        data = copy.deepcopy(real_metadata())
        data["CanonicalLeagueID"] = league_id
        if mutate:
            mutate(data)
        directory = root / league_id
        directory.mkdir(parents=True)
        (directory / "metadata.json").write_text(json.dumps(data), encoding="utf-8")

    def test_repository_metadata_is_valid_and_matches_manifest(self) -> None:
        manifest = json.loads((REPO_ROOT / "data-source/leagues" / LEAGUE / "manifest.json").read_text(encoding="utf-8"))
        lm.validate_against_manifest(real_metadata(), manifest)

    def test_models_cap_deadline_and_legacy_paths_are_retired(self) -> None:
        meta = real_metadata()
        manifest = json.loads((REPO_ROOT / "data-source/leagues" / LEAGUE / "manifest.json").read_text(encoding="utf-8"))
        current = int(manifest["CurrentCanonicalLeagueSeasonID"].rsplit("-", 1)[1])
        self.assertTrue(all(lm.cap_deadline(meta, current)))
        for kind, expected in (("Salary", "salary-v1"), ("SalaryCap", "salary-cap-v1"), ("Grading", "grading-v1"),
                               ("Standings", "standings-v1"), ("Awards", "awards-v1")):
            for season in meta["Seasons"]:
                self.assertEqual(expected, lm.model_for(meta, season, kind))
        self.assertFalse((REPO_ROOT / "public/data/Metadata.json").exists())
        self.assertFalse((REPO_ROOT / "public/data/Metadata.ai-doc.yaml").exists())
        self.assertFalse((REPO_ROOT / "data-source/leagues/_bootstrap").exists())
        self.assertFalse((REPO_ROOT / "public/requests/config.ps1").exists())

    def test_multiple_leagues_are_iterated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_league(root, "alpha")
            self.write_league(root, "beta")
            self.assertEqual(["alpha", "beta"], sorted(lm.load_all_league_metadata(root)))

    def test_missing_file_season_and_root_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_league(root, "alpha")
            with self.assertRaises(lm.LeagueMetadataError):
                lm.load_league_metadata("gamma", root)
            with self.assertRaises(lm.LeagueMetadataError):
                lm.model_for(lm.load_league_metadata("alpha", root), 1999, "Salary")
            with self.assertRaises(lm.LeagueMetadataError):
                lm.cap_deadline(lm.load_league_metadata("alpha", root), 2024)
            with self.assertRaises(lm.LeagueMetadataError):
                lm.list_league_ids(root / "missing")

    def test_invalid_content_fails_closed(self) -> None:
        def unknown_model(d): d["Seasons"]["2026"]["Models"]["Salary"] = "salary-v99"
        def missing_model(d): del d["Seasons"]["2026"]["Models"]["Grading"]
        def unknown_key(d): d["SalaryRelevantTeamSize"] = 20
        def half_deadline(d): del d["Seasons"]["2026"]["CapDeadlineBufferDays"]
        def duplicate_slot(d): d["Drafts"]["Types"].append(copy.deepcopy(d["Drafts"]["Types"][0]))
        def duplicate_owner(d): d["Owners"]["Marcel"] = d["Owners"]["Robert"]
        def bad_timezone(d): d["LeagueTimeZone"] = "Nowhere/Land"
        def wrong_id(d): d["CanonicalLeagueID"] = "other"
        for mutate in (unknown_model, missing_model, unknown_key, half_deadline, duplicate_slot, duplicate_owner, bad_timezone, wrong_id):
            with self.subTest(mutate.__name__), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.write_league(root, "alpha", mutate)
                path = root / "alpha" / "metadata.json"
                if mutate is wrong_id:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    data["CanonicalLeagueID"] = "other"
                    path.write_text(json.dumps(data), encoding="utf-8")
                with self.assertRaises(lm.LeagueMetadataError):
                    lm.load_league_metadata("alpha", root)

    def test_manifest_season_without_model_choice_fails(self) -> None:
        meta = copy.deepcopy(real_metadata())
        manifest = json.loads((REPO_ROOT / "data-source/leagues" / LEAGUE / "manifest.json").read_text(encoding="utf-8"))
        del meta["Seasons"]["2024"]
        with self.assertRaises(lm.LeagueMetadataError):
            lm.validate_against_manifest(meta, manifest)

    @unittest.skipUnless(shutil.which("pwsh"), "pwsh not available")
    def test_powershell_loader_regression(self) -> None:
        result = subprocess.run(
            ["pwsh", "-NoProfile", "-File", str(REPO_ROOT / "public/requests/LeagueMetadataRegressionTest.ps1")],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
