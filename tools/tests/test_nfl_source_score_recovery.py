from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
REQUEST_GAMES = ROOT / "public" / "requests" / "RequestGames.ps1"


class RequestGamesScoreRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = REQUEST_GAMES.read_text(encoding="utf-8")

    def test_weekly_score_endpoint_uses_game_week(self):
        self.assertIn(
            "getNFLScoresOnly?gameWeek=$scoreWeek&season=$year",
            self.source,
        )
        self.assertNotIn("getNFLScoresOnly?week=$scoreWeek", self.source)

    def test_postgame_retry_is_bounded_and_recent_only(self):
        self.assertRegex(
            self.source,
            re.compile(r"\$scoreRetryDelaysSeconds\s*=\s*@\(0,\s*60,\s*120,\s*180\)"),
        )
        self.assertRegex(self.source, re.compile(r"\$scoreRetryWindowHours\s*=\s*12"))
        self.assertIn("function Test-GameEligibleForScoreRetry", self.source)
        self.assertIn("function Get-MissingFinalScoreGamesForWeek", self.source)
        self.assertIn("Start-Sleep -Seconds $retryDelay", self.source)
        self.assertIn("outside the bounded post-game retry window", self.source)

    def test_retries_never_promote_finality(self):
        retry_section = self.source.split(
            "# Fetch lightweight score evidence only for canonical-Final games",
            1,
        )[1].split("Write-Host \"Schedule retrieved", 1)[0]
        self.assertIn("gameStatus -match '^Final'", self.source)
        self.assertNotRegex(retry_section, re.compile(r"gameStatus\s*="))
        self.assertNotRegex(retry_section, re.compile(r"gameStatusCode\s*="))


if __name__ == "__main__":
    unittest.main()
