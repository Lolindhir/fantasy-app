$ErrorActionPreference = 'Stop'

& "$PSScriptRoot\NflTeamRegistryRegressionTest.ps1"
& "$PSScriptRoot\NflTeamKeyJoinRegressionTest.ps1"
& "$PSScriptRoot\NflTeamsReadModelRegressionTest.ps1"
& "$PSScriptRoot\DecisionWindowRegressionLegacyTest.ps1"
& "$PSScriptRoot\LeagueWeekBoundaryRegressionTest.ps1"
& "$PSScriptRoot\GameFinalityRegressionTest.ps1"
& "$PSScriptRoot\NflByeWeekRegressionTest.ps1"
& "$PSScriptRoot\PlayerLeagueScoringRegressionTest.ps1"
& "$PSScriptRoot\PlayerPopulationRegressionTest.ps1"
& "$PSScriptRoot\CanonicalScheduleRegressionTest.ps1"
& "$PSScriptRoot\WeeklyRecapRegressionTest.ps1"
Write-Host 'Decision Window legacy + NFL Bye Weeks + League Week Boundary + Game Finality + WeeklyRecaps regression suite passed.' -ForegroundColor Green
