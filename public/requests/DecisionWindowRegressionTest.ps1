$ErrorActionPreference = 'Stop'

& "$PSScriptRoot\DecisionWindowRegressionLegacyTest.ps1"
& "$PSScriptRoot\FantasyGameContextRegressionTest.ps1"
& "$PSScriptRoot\FantasyGameContextSleeperShapeRegressionTest.ps1"
& "$PSScriptRoot\FantasyRelevanceV2RegressionTest.ps1"
& "$PSScriptRoot\GameFinalityRegressionTest.ps1"
& "$PSScriptRoot\FantasyMatchupPreviewRegressionTest.ps1"
Write-Host 'Decision Window + FantasyGameContext regression suite passed.' -ForegroundColor Green
