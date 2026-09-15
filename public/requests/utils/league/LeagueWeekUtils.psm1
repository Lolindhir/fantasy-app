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

Export-ModuleMember -Function Resolve-LeagueWeekState
