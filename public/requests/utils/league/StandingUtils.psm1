
# ===========================================================================
# Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\..\ConfigUtils.psm1" -ErrorAction Stop -Force
}
catch {
    Write-Error "Fehler beim Laden der Module: $_"
    throw $_
}


# ===========================================================================
# Helper Utils
# ===========================================================================

function Get-Ordinal {
    param([int]$number)

    switch ($number) {
        0 { "none" }
        1 { "1st" }
        2 { "2nd" }
        3 { "3rd" }
        default { "$number" + "th" }
    }
}

# ===========================================================================
# Standings Product Utils
# ===========================================================================


# Consumer read of the league-standings product (Issue #987, ADR-072): the App-shaped standings are rendered from the
# persisted data-derived product by tools/league_standings_app_publish.py render, never read back from Standings.json.
# Fails closed (missing tool, product or output).
function Get-LeagueStandingsProduct {
    param(
        [Parameter(Mandatory = $true)][string]$CanonicalLeagueID,
        [Parameter(Mandatory = $true)][string]$RepoRoot
    )

    $toolPath = Join-Path $RepoRoot "tools/league_standings_app_publish.py"
    if (-not (Test-Path $toolPath)) {
        throw "League standings render tool missing at '$toolPath'."
    }

    $python = $null
    foreach ($name in @("python3", "python")) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($command) { $python = $command.Source; break }
    }
    if (-not $python) { throw "Python is required to render the league-standings product." }

    $output = & $python $toolPath --repo-root $RepoRoot render --league $CanonicalLeagueID 2>&1
    $exitCode = $LASTEXITCODE
    $outputText = (@($output) | ForEach-Object { [string]$_ }) -join [Environment]::NewLine
    if ($exitCode -ne 0) {
        throw "League standings render failed with exit code $exitCode. $outputText"
    }

    try {
        $standings = $outputText | ConvertFrom-Json
    }
    catch {
        throw "League standings render returned invalid JSON. $outputText"
    }
    $standings = @($standings)
    if ($standings.Count -eq 0) {
        throw "League standings product for '$CanonicalLeagueID' rendered no seasons."
    }
    return $standings
}
