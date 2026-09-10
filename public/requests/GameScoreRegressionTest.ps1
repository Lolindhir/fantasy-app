$ErrorActionPreference = 'Stop'

Import-Module "$PSScriptRoot\utils\general\GameScoreUtils.psm1" -ErrorAction Stop -Force

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw $Message }
}

$schedule = @(
    [PSCustomObject]@{ gameID = '20260909_NE@SEA'; gameStatus = 'Final'; gameWeek = 'Week 1' },
    [PSCustomObject]@{ gameID = '20260910_SF@LAR'; gameStatus = 'Scheduled'; gameWeek = 'Week 1' },
    [PSCustomObject]@{ gameID = '20260913_TB@CIN'; gameStatus = 'Final'; gameWeek = 'Week 1' }
)

$scoreBody = [PSCustomObject]@{
    '20260909_NE@SEA' = [PSCustomObject]@{ awayPts = '24'; homePts = '0'; gameStatus = 'Scheduled' }
    '20260910_SF@LAR' = [PSCustomObject]@{ awayPts = '17'; homePts = '20'; gameStatus = 'Final' }
    '20260913_TB@CIN' = [PSCustomObject]@{ awayPts = '21'; homePts = $null; gameStatus = 'Final' }
}

$scoreRows = @(Get-Tank01ScoreRows -Value $scoreBody)
Assert-True ($scoreRows.Count -eq 3) 'Expected keyed Tank01 score body to flatten to three rows.'

$result = @(Merge-GameScoresIntoSchedule -Schedule $schedule -ScoreRows $scoreRows)
$finalGame = $result | Where-Object gameID -eq '20260909_NE@SEA'
$futureGame = $result | Where-Object gameID -eq '20260910_SF@LAR'
$partialScore = $result | Where-Object gameID -eq '20260913_TB@CIN'

Assert-True (Test-GameHasScorePair -Game $finalGame) 'Final game should receive a complete score pair.'
Assert-True ([double]$finalGame.awayPts -eq 24 -and [double]$finalGame.homePts -eq 0) 'Zero must remain a valid NFL score.'
Assert-True ($finalGame.gameStatus -eq 'Final') 'Score evidence must not alter canonical Finality.'
Assert-True (-not (Test-GameHasScorePair -Game $futureGame)) 'A non-final game must not be enriched even when provider score/status claims Final.'
Assert-True (-not (Test-GameHasScorePair -Game $partialScore)) 'Incomplete score evidence must remain unknown rather than defaulting to zero.'

$conflictingRows = @(
    [PSCustomObject]@{ gameID = '20260909_NE@SEA'; awayPts = 24; homePts = 20 },
    [PSCustomObject]@{ gameID = '20260909_NE@SEA'; awayPts = 27; homePts = 20 }
)
$threw = $false
try {
    Merge-GameScoresIntoSchedule -Schedule @([PSCustomObject]@{ gameID = '20260909_NE@SEA'; gameStatus = 'Final' }) -ScoreRows $conflictingRows | Out-Null
} catch {
    $threw = $true
}
Assert-True $threw 'Conflicting score evidence for the same game must fail closed.'

Write-Host 'Game score regression test passed.' -ForegroundColor Green
