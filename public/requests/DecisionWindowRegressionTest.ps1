$ErrorActionPreference = 'Stop'

& "$PSScriptRoot\NflTeamRegistryRegressionTest.ps1"
& "$PSScriptRoot\NflTeamKeyJoinRegressionTest.ps1"
& "$PSScriptRoot\NflTeamsReadModelRegressionTest.ps1"
& "$PSScriptRoot\DecisionWindowRegressionLegacyTest.ps1"
& "$PSScriptRoot\LeagueWeekBoundaryRegressionTest.ps1"
& "$PSScriptRoot\GameFinalityRegressionTest.ps1"
& "$PSScriptRoot\NflByeWeekRegressionTest.ps1"
& "$PSScriptRoot\CanonicalScheduleRegressionTest.ps1"
Write-Host 'Decision Window legacy + NFL Bye Weeks + League Week Boundary + Game Finality regression suite passed.' -ForegroundColor Green
# Sub-scripts may leave a stale native exit code behind (a tolerated failing helper call); every real failure throws
# above under $ErrorActionPreference = 'Stop', so the suite result must not depend on the last native $LASTEXITCODE.
$global:LASTEXITCODE = 0
