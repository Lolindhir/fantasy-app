$ErrorActionPreference = 'Stop'

Import-Module "$PSScriptRoot\utils\league\LeagueWeekUtils.psm1" -ErrorAction Stop -Force

function Assert-Equal {
    param(
        [Parameter(Mandatory = $true)]$Expected,
        [Parameter(Mandatory = $true)]$Actual,
        [Parameter(Mandatory = $true)][string]$Message
    )

    if ($Expected -ne $Actual) {
        throw "$Message Expected '$Expected', got '$Actual'."
    }
}

$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("league-week-boundary-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null

try {
    $rolloverDecisionWindows = [PSCustomObject][ordered]@{
        LineupWeek = 2
    }
    $rolloverMatchupWeek = Resolve-FantasyMatchupLoadWeek `
        -DecisionWindows $rolloverDecisionWindows `
        -LastLeagueWeek 17
    Assert-Equal -Expected 2 -Actual $rolloverMatchupWeek -Message 'Fantasy matchup loading must follow DecisionWindows.LineupWeek during NFL week rollover.'

    $completedMatchupWeek = Resolve-FantasyMatchupLoadWeek `
        -DecisionWindows $rolloverDecisionWindows `
        -LastLeagueWeek 17 `
        -LeagueComplete $true
    Assert-Equal -Expected 0 -Actual $completedMatchupWeek -Message 'Completed leagues must not request a current fantasy matchup week.'

    $scoredWeek = Get-LeagueScoredWeek -CanonicalLeagueID 'nfl-reise' -Season 2026 -RepoRoot (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
    Assert-Equal -Expected $true -Actual ($scoredWeek -ge 0 -and $scoredWeek -le 18) -Message 'Shared LeagueScoredWeek must be a valid week number.'

    $threw = $false
    try {
        Get-LeagueScoredWeek -CanonicalLeagueID 'unknown-league' -Season 2026 -RepoRoot (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path | Out-Null
    }
    catch {
        $threw = $true
    }
    Assert-Equal -Expected $true -Actual $threw -Message 'Unknown league must fail closed in the shared week-final definition.'
}
finally {
    Remove-Item $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host 'League week boundary regression tests passed.' -ForegroundColor Green
