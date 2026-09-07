$ErrorActionPreference = 'Stop'

Import-Module "$PSScriptRoot\utils\league\FantasyGameContextUtils.psm1" -Force

function Assert-Equal {
    param($Expected, $Actual, [string]$Message)
    if ($Expected -ne $Actual) {
        throw "ASSERTION FAILED: $Message. Expected '$Expected', got '$Actual'."
    }
}

$rows = @(
    [PSCustomObject]@{
        matchup_id = 12
        roster_id = 1
        players = @('p1', 'p2')
        starters = @('p1')
        players_points = [PSCustomObject]@{ p1 = 18.5; p2 = 4.25 }
        starters_points = @(18.5)
        points = 22.75
        custom_points = $null
    },
    [PSCustomObject]@{
        matchup_id = 12
        roster_id = 2
        players = @('p3', 'p4')
        starters = @('p3')
        players_points = [PSCustomObject]@{ p3 = 9.75; p4 = 2.0 }
        starters_points = @(9.75)
        points = 11.75
        custom_points = $null
    }
)

$facts = @(ConvertTo-FgcCurrentMatchupFacts -Season '2026' -Week 1 -MatchupRows $rows)
Assert-Equal 1 $facts.Count 'real Sleeper-shaped matchup rows must materialize one pairing'

$teamOne = @($facts[0].Teams | Where-Object { [string]$_.FantasyTeamID -eq '1' })[0]
$starter = @($teamOne.Players | Where-Object { $_.PlayerID -eq 'p1' })[0]
$bench = @($teamOne.Players | Where-Object { $_.PlayerID -eq 'p2' })[0]

Assert-Equal $true $starter.IsStarter 'starter identity must survive the real Sleeper shape'
Assert-Equal 18.5 $starter.Points 'starter points must come from keyed players_points when starters_points is positional'
Assert-Equal 4.25 $bench.Points 'bench player points must remain available from keyed players_points'

Write-Host 'FantasyGameContext Sleeper shape regression test passed.' -ForegroundColor Green
