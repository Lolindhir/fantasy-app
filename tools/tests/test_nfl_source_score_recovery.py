from pathlib import Path
import os
import re
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[2]
REQUEST_GAMES = ROOT / "public" / "requests" / "RequestSchedule.ps1"


class RequestScheduleScoreRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = REQUEST_GAMES.read_text(encoding="utf-8")

    def test_scores_come_from_canonical_schedule_not_tank01(self):
        # #347 G2: the Tank01 score endpoint and its post-game retry loop are retired.
        self.assertIn("Get-CanonicalAppSchedule", self.source)
        self.assertNotIn("getNFLScoresOnly", self.source)
        self.assertNotIn("getNFLGamesForWeek", self.source)
        self.assertNotIn("$scoreRetryDelaysSeconds", self.source)
        self.assertNotIn("Merge-GameScoresIntoSchedule", self.source)

    def test_no_provider_call_key_or_games_artifact_remains(self):
        # #347 G4: Tank01 pipeline, keys and Games.json are retired.
        self.assertNotIn("Tank01", self.source)
        self.assertNotIn("RapidAPI", self.source)
        for base in ("public/requests", "public/data/examples", ".github"):
            for path in (ROOT / base).rglob("*"):
                if path.is_file() and path.suffix in {".ps1", ".psm1", ".yml", ".json"} and "RegressionTest" not in path.name:
                    text = path.read_text(encoding="utf-8", errors="ignore").lower()
                    self.assertNotIn("rapidapi", text, str(path))
        for retired in (
            "public/requests/RequestGames.ps1",
            "public/requests/RequestGamesSeason.ps1",
            "public/requests/RequestPlayersSeason.ps1",
            "public/requests/utils/general/GameScoreUtils.psm1",
            "public/data/Games.json",
        ):
            self.assertFalse((ROOT / retired).exists(), retired)
        self.assertEqual(list((ROOT / "public" / "data" / "past_seasons").glob("Games_*.json")), [])

    def test_workflow_calls_request_schedule(self):
        workflow = (ROOT / ".github" / "workflows" / "update-games.yml").read_text(encoding="utf-8")
        self.assertIn("pwsh ./public/requests/RequestSchedule.ps1", workflow)
        self.assertNotIn("RequestGames.ps1", workflow)

    def test_missing_canonical_score_stays_unknown(self):
        self.assertIn("score stays unknown", self.source)
        self.assertNotRegex(self.source, re.compile(r"awayPts\s*=\s*0"))

    def test_schedule_failure_aborts_before_publication(self):
        build = self.source.split("Get-CanonicalAppSchedule", 1)[1].split("Schedule built", 1)[0]
        self.assertIn("exit 1", build)

    def test_request_games_has_valid_powershell_syntax(self):
        env = dict(os.environ)
        env["REQUEST_GAMES_PATH"] = str(REQUEST_GAMES)
        command = (
            "$tokens = $null; $errors = $null; "
            "[System.Management.Automation.Language.Parser]::ParseFile("
            "$env:REQUEST_GAMES_PATH, [ref]$tokens, [ref]$errors) | Out-Null; "
            "if ($errors.Count -gt 0) { "
            "$errors | ForEach-Object { Write-Error $_.Message }; exit 1 }"
        )
        completed = subprocess.run(
            ["pwsh", "-NoProfile", "-Command", command],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(
            completed.returncode,
            0,
            msg=f"PowerShell parser errors:\n{completed.stdout}\n{completed.stderr}",
        )


if __name__ == "__main__":
    unittest.main()
