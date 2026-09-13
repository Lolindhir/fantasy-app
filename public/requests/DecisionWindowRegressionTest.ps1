$ErrorActionPreference = 'Stop'

& "$PSScriptRoot\DecisionWindowRegressionLegacyTest.ps1"
& "$PSScriptRoot\FantasyGameContextRegressionTest.ps1"
& "$PSScriptRoot\FantasyGameContextSleeperShapeRegressionTest.ps1"
& "$PSScriptRoot\FantasyRelevanceV2RegressionTest.ps1"
& "$PSScriptRoot\LineupRepairabilityRegressionTest.ps1"
& "$PSScriptRoot\FantasyWeeklyWatchRegressionTest.ps1"
& "$PSScriptRoot\GameFinalityRegressionTest.ps1"
& "$PSScriptRoot\GameScoreRegressionTest.ps1"
& "$PSScriptRoot\FantasyGameContextScoreRegressionTest.ps1"
& "$PSScriptRoot\FantasyMatchupPreviewRegressionTest.ps1"
& "$PSScriptRoot\MatchupReadModelRegressionTest.ps1"
Write-Host 'Decision Window + FantasyGameContext + Matchups regression suite passed.' -ForegroundColor Green
