from pathlib import Path
import os
import re
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[2]
REQUEST_GAMES = ROOT / "public" / "requests" / "RequestGames.ps1"


class RequestGamesScoreRecoveryTests(unittest.TestCase):
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
