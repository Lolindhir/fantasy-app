function Get-LeagueWeekPropertyValue {
    param(
        [AllowNull()][object]$Object,
        [Parameter(Mandatory = $true)][string]$Name
    )

    if ($null -eq $Object -or -not ($Object.PSObject.Properties.Name -contains $Name)) {
        return $null
    }

    return $Object.$Name
}

function ConvertTo-LeagueWeekPositiveInt {
    param(
        [AllowNull()][object]$Value,
        [Parameter(Mandatory = $true)][string]$Source
    )

    if ($null -eq $Value -or [string]::IsNullOrWhiteSpace([string]$Value)) { return 0 }

    $parsed = 0
    if (-not [int]::TryParse([string]$Value, [ref]$parsed) -or $parsed -lt 1) {
        throw "$Source must be a positive integer when present."
    }

    return $parsed
}

function Resolve-LeagueWeekState {
    param(
        [Parameter(Mandatory = $true)][object]$League,
        [Parameter(Mandatory = $true)][string]$CanonicalLeagueSourceFile
    )

    $settings = Get-LeagueWeekPropertyValue -Object $League -Name 'settings'
    if ($null -eq $settings) {
        throw 'League settings are required to resolve league week state.'
    }

    $lastScoredLeg = ConvertTo-LeagueWeekPositiveInt `
        -Value (Get-LeagueWeekPropertyValue -Object $settings -Name 'last_scored_leg') `
        -Source 'League.settings.last_scored_leg'

    if ([string]::IsNullOrWhiteSpace($CanonicalLeagueSourceFile) -or -not (Test-Path $CanonicalLeagueSourceFile)) {
        throw "Canonical league source is required to resolve the structural last league week: $CanonicalLeagueSourceFile"
    }

    try {
        $canonicalLeague = Get-Content $CanonicalLeagueSourceFile -Raw | ConvertFrom-Json
    }
    catch {
        throw "Could not read canonical league source '$CanonicalLeagueSourceFile': $_"
    }

    $weekStructure = Get-LeagueWeekPropertyValue -Object $canonicalLeague -Name 'WeekStructure'
    if ($null -eq $weekStructure) {
        throw "Canonical league source '$CanonicalLeagueSourceFile' has no WeekStructure."
    }

    $lastLeagueWeek = ConvertTo-LeagueWeekPositiveInt `
        -Value (Get-LeagueWeekPropertyValue -Object $weekStructure -Name 'ExpectedLastLeagueWeek') `
        -Source 'WeekStructure.ExpectedLastLeagueWeek'
    $boundarySource = 'ExpectedLastLeagueWeek'

    if ($lastLeagueWeek -le 0) {
        $lastLeagueWeek = ConvertTo-LeagueWeekPositiveInt `
            -Value (Get-LeagueWeekPropertyValue -Object $weekStructure -Name 'FinalLeagueWeek') `
            -Source 'WeekStructure.FinalLeagueWeek'
        $boundarySource = 'FinalLeagueWeek'
    }

    if ($lastLeagueWeek -le 0) {
        throw "Canonical league source '$CanonicalLeagueSourceFile' cannot resolve a structural last league week."
    }

    if ($lastScoredLeg -gt $lastLeagueWeek) {
        throw "League last scored leg $lastScoredLeg exceeds structural last league week $lastLeagueWeek."
    }

    return [PSCustomObject][ordered]@{
        LastScoredLeg  = $lastScoredLeg
        LastLeagueWeek = $lastLeagueWeek
        BoundarySource = $boundarySource
    }
}

function Resolve-FantasyMatchupLoadWeek {
    param(
        [AllowNull()][object]$DecisionWindows,
        [Parameter(Mandatory = $true)][int]$LastLeagueWeek,
        [bool]$LeagueComplete = $false
    )

    if ($LeagueComplete -or $LastLeagueWeek -le 0 -or $null -eq $DecisionWindows) {
        return 0
    }

    $lineupWeek = ConvertTo-LeagueWeekPositiveInt `
        -Value (Get-LeagueWeekPropertyValue -Object $DecisionWindows -Name 'LineupWeek') `
        -Source 'DecisionWindows.LineupWeek'

    if ($lineupWeek -le 0) { return 0 }
    return [Math]::Min($lineupWeek, $LastLeagueWeek)
}

# FinalScoredWeek of League.json: the shared LeagueScoredWeek milestone (ADR-071, Issue #897).
# A week counts only when every NFL game is final AND the league provider has scored it; the rule
# lives in tools/derived_data_lib/week_finality.py and is not re-implemented here. Fails closed.
function Get-LeagueScoredWeek {
    param(
        [Parameter(Mandatory = $true)][string]$CanonicalLeagueID,
        [Parameter(Mandatory = $true)][int]$Season,
        [Parameter(Mandatory = $true)][string]$RepoRoot
    )

    $toolPath = Join-Path $RepoRoot "tools/week_finality.py"
    if (-not (Test-Path $toolPath)) {
        throw "Week-finality tool missing at '$toolPath'."
    }

    $python = $null
    foreach ($name in @("python3", "python")) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($command) { $python = $command.Source; break }
    }
    if (-not $python) { throw "Python is required for the shared week-final definition." }

    $output = & $python $toolPath --repo-root $RepoRoot bounds --league $CanonicalLeagueID --season $Season 2>&1
    $exitCode = $LASTEXITCODE
    $outputText = (@($output) | ForEach-Object { [string]$_ }) -join [Environment]::NewLine
    if ($exitCode -ne 0) {
        throw "Shared week-final definition failed with exit code $exitCode. $outputText"
    }

    try {
        $result = $outputText | ConvertFrom-Json
    }
    catch {
        throw "Shared week-final definition returned invalid JSON. $outputText"
    }
    if ($null -eq $result.LeagueScoredWeek -or [int]$result.LeagueScoredWeek -lt 0) {
        throw "Shared week-final definition lacks a valid LeagueScoredWeek."
    }
    return [int]$result.LeagueScoredWeek
}

Export-ModuleMember -Function Resolve-LeagueWeekState, Resolve-FantasyMatchupLoadWeek, Get-LeagueScoredWeek
