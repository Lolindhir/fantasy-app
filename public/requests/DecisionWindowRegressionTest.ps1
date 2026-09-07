$ErrorActionPreference = 'Stop'

& "$PSScriptRoot\DecisionWindowRegressionLegacyTest.ps1"
& "$PSScriptRoot\FantasyGameContextRegressionTest.ps1"

Write-Host 'Decision Window + FantasyGameContext regression suite passed.' -ForegroundColor Green
