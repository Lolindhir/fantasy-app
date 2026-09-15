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
    $activeSourceFile = Join-Path $tempRoot 'active-league.json'
    [PSCustomObject][ordered]@{
        WeekStructure = [PSCustomObject][ordered]@{
            ExpectedLastLeagueWeek = 17
            FinalLeagueWeek = $null
        }
    } | ConvertTo-Json -Depth 5 | Set-Content $activeSourceFile -Encoding UTF8

    $activeLeague = [PSCustomObject][ordered]@{
        settings = [PSCustomObject][ordered]@{
            last_scored_leg = 1
        }
    }

    $activeState = Resolve-LeagueWeekState `
        -League $activeLeague `
        -CanonicalLeagueSourceFile $activeSourceFile

    Assert-Equal -Expected 1 -Actual $activeState.LastScoredLeg -Message 'Latest scored leg must remain progression evidence.'
    Assert-Equal -Expected 17 -Actual $activeState.LastLeagueWeek -Message 'Structural last league week must not collapse to last_scored_leg.'
    Assert-Equal -Expected 'ExpectedLastLeagueWeek' -Actual $activeState.BoundarySource -Message 'Active seasons must use the projected canonical boundary.'

    $completedSourceFile = Join-Path $tempRoot 'completed-league.json'
    [PSCustomObject][ordered]@{
        WeekStructure = [PSCustomObject][ordered]@{
            ExpectedLastLeagueWeek = $null
            FinalLeagueWeek = 17
        }
    } | ConvertTo-Json -Depth 5 | Set-Content $completedSourceFile -Encoding UTF8

    $completedLeague = [PSCustomObject][ordered]@{
        settings = [PSCustomObject][ordered]@{
            last_scored_leg = 17
        }
    }

    $completedState = Resolve-LeagueWeekState `
        -League $completedLeague `
        -CanonicalLeagueSourceFile $completedSourceFile

    Assert-Equal -Expected 17 -Actual $completedState.LastScoredLeg -Message 'Completed-season scored leg must remain intact.'
    Assert-Equal -Expected 17 -Actual $completedState.LastLeagueWeek -Message 'Completed season must fall back to canonical FinalLeagueWeek.'
    Assert-Equal -Expected 'FinalLeagueWeek' -Actual $completedState.BoundarySource -Message 'Completed-season fallback source mismatch.'

    $invalidLeague = [PSCustomObject][ordered]@{
        settings = [PSCustomObject][ordered]@{
            last_scored_leg = 18
        }
    }

    $threw = $false
    try {
        Resolve-LeagueWeekState -League $invalidLeague -CanonicalLeagueSourceFile $activeSourceFile | Out-Null
    }
    catch {
        $threw = $true
    }
    Assert-Equal -Expected $true -Actual $threw -Message 'Scored leg beyond the structural boundary must fail closed.'
}
finally {
    Remove-Item $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host 'League week boundary regression tests passed.' -ForegroundColor Green
