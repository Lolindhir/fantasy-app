# ===========================================================================
# Canonical current matchup adapter
# ===========================================================================

function Get-CmuRepoRoot {
    return (Resolve-Path (Join-Path $PSScriptRoot "../../../..")).Path
}

function Get-CmuPropertyValue {
    param(
        [AllowNull()]$Object,
        [Parameter(Mandatory = $true)][string]$PropertyName,
        [AllowNull()]$DefaultValue = $null
    )
    if ($null -eq $Object) { return $DefaultValue }
    $property = $Object.PSObject.Properties[$PropertyName]
    if ($null -eq $property) { return $DefaultValue }
    return $property.Value
}

function Get-CmuSleeperMapping {
    param(
        [AllowNull()]$Mappings,
        [Parameter(Mandatory = $true)][string]$Label
    )
    $matches = @(
        @($Mappings) |
            Where-Object { [string](Get-CmuPropertyValue -Object $_ -PropertyName "Provider" -DefaultValue "") -eq "Sleeper" }
    )
    if ($matches.Count -ne 1) {
        throw "$Label must contain exactly one Sleeper provider mapping; found $($matches.Count)."
    }
    return $matches[0]
}

function Get-CmuProviderPlayerID {
    param(
        [AllowNull()]$PlayerRef,
        [Parameter(Mandatory = $true)][string]$Label
    )
    if ($null -eq $PlayerRef) {
        throw "$Label is missing a player reference."
    }
    $mapping = Get-CmuSleeperMapping -Mappings (Get-CmuPropertyValue -Object $PlayerRef -PropertyName "ProviderMappings" -DefaultValue @()) -Label $Label
    $playerID = [string](Get-CmuPropertyValue -Object $mapping -PropertyName "ProviderPlayerID" -DefaultValue "")
    if ([string]::IsNullOrWhiteSpace($playerID)) {
        throw "$Label Sleeper mapping is missing ProviderPlayerID."
    }
    return $playerID.Trim()
}

function ConvertTo-CmuPointMap {
    param(
        [AllowNull()]$Entries,
        [Parameter(Mandatory = $true)][string]$Label
    )
    $result = [ordered]@{}
    foreach ($entry in @($Entries)) {
        if ($null -eq $entry) { continue }
        $player = Get-CmuPropertyValue -Object $entry -PropertyName "Player"
        $playerID = Get-CmuProviderPlayerID -PlayerRef $player -Label "$Label.Player"
        if ($result.Contains($playerID)) {
            throw "$Label contains duplicate Sleeper PlayerID '$playerID'."
        }
        $result[$playerID] = Get-CmuPropertyValue -Object $entry -PropertyName "Points"
    }
    return $result
}

function ConvertTo-CmuLegacyRow {
    param(
        [Parameter(Mandatory = $true)]$Row,
        [Parameter(Mandatory = $true)][int]$Week
    )

    $rowWeek = [int](Get-CmuPropertyValue -Object $Row -PropertyName "Week" -DefaultValue 0)
    if ($rowWeek -ne $Week) {
        throw "Canonical matchup row Week '$rowWeek' does not match requested Week '$Week'."
    }

    $mapping = Get-CmuSleeperMapping -Mappings (Get-CmuPropertyValue -Object $Row -PropertyName "ProviderMappings" -DefaultValue @()) -Label "Canonical matchup Week $Week"

    $rosterIDText = [string](Get-CmuPropertyValue -Object $mapping -PropertyName "ProviderRosterID" -DefaultValue "")
    $rosterID = 0
    if (-not [int]::TryParse($rosterIDText, [ref]$rosterID) -or $rosterID -lt 1) {
        throw "Canonical matchup Week $Week has invalid Sleeper ProviderRosterID '$rosterIDText'."
    }

    $matchupValue = Get-CmuPropertyValue -Object $mapping -PropertyName "ProviderMatchupID" -DefaultValue $null
    $matchupID = $null
    if ($null -ne $matchupValue -and -not [string]::IsNullOrWhiteSpace([string]$matchupValue)) {
        $parsedMatchupID = 0
        if (-not [int]::TryParse([string]$matchupValue, [ref]$parsedMatchupID) -or $parsedMatchupID -lt 1) {
            throw "Canonical matchup Week $Week roster $rosterID has invalid Sleeper ProviderMatchupID '$matchupValue'."
        }
        $matchupID = $parsedMatchupID
    }

    $players = @(
        @(Get-CmuPropertyValue -Object $Row -PropertyName "Players" -DefaultValue @()) |
            ForEach-Object { Get-CmuProviderPlayerID -PlayerRef $_ -Label "Canonical matchup Week $Week roster $rosterID Players" }
    )
    if (@($players | Sort-Object -Unique).Count -ne $players.Count) {
        throw "Canonical matchup Week $Week roster $rosterID contains duplicate Players."
    }

    $starters = @(
        @(Get-CmuPropertyValue -Object $Row -PropertyName "Starters" -DefaultValue @()) |
            ForEach-Object { Get-CmuProviderPlayerID -PlayerRef $_ -Label "Canonical matchup Week $Week roster $rosterID Starters" }
    )
    if (@($starters | Sort-Object -Unique).Count -ne $starters.Count) {
        throw "Canonical matchup Week $Week roster $rosterID contains duplicate Starters."
    }
    foreach ($starterID in $starters) {
        if ($players -notcontains $starterID) {
            throw "Canonical matchup Week $Week roster $rosterID starter '$starterID' is outside Players."
        }
    }

    $playerPoints = ConvertTo-CmuPointMap -Entries (Get-CmuPropertyValue -Object $Row -PropertyName "PlayerPoints" -DefaultValue @()) -Label "Canonical matchup Week $Week roster $rosterID PlayerPoints"
    $starterPointsMap = ConvertTo-CmuPointMap -Entries (Get-CmuPropertyValue -Object $Row -PropertyName "StarterPoints" -DefaultValue @()) -Label "Canonical matchup Week $Week roster $rosterID StarterPoints"

    $starterPoints = @()
    foreach ($starterID in $starters) {
        if ($starterPointsMap.Contains($starterID)) {
            $starterPoints += $starterPointsMap[$starterID]
        }
        elseif ($playerPoints.Contains($starterID)) {
            $starterPoints += $playerPoints[$starterID]
        }
        else {
            throw "Canonical matchup Week $Week roster $rosterID has no score evidence for starter '$starterID'."
        }
    }

    return [PSCustomObject][ordered]@{
        custom_points   = Get-CmuPropertyValue -Object $Row -PropertyName "CustomPoints" -DefaultValue $null
        matchup_id      = $matchupID
        players         = $players
        players_points  = [PSCustomObject]$playerPoints
        points          = Get-CmuPropertyValue -Object $Row -PropertyName "Points" -DefaultValue $null
        roster_id       = $rosterID
        starters        = $starters
        starters_points = $starterPoints
    }
}

function Get-CanonicalCurrentMatchupRows {
    param(
        [string]$CanonicalLeagueID = "nfl-reise",
        [Parameter(Mandatory = $true)][int]$Season,
        [Parameter(Mandatory = $true)][int]$Week
    )

    if ($Season -lt 1) { throw "Canonical current matchup Season must be positive." }
    if ($Week -lt 1) { throw "Canonical current matchup Week must be positive." }

    $repoRoot = Get-CmuRepoRoot
    $path = Join-Path $repoRoot "source-data/leagues/$CanonicalLeagueID/seasons/$Season/matchups/week-$Week.json"
    if (-not (Test-Path $path)) {
        throw "Canonical current matchup source is missing for $CanonicalLeagueID/$Season Week $Week at '$path'."
    }

    try {
        $raw = Get-Content $path -Raw
        if ([string]::IsNullOrWhiteSpace($raw)) {
            throw "Canonical current matchup source is empty for $CanonicalLeagueID/$Season Week $Week."
        }
        $rows = @($raw | ConvertFrom-Json)
    }
    catch {
        throw "Could not read canonical current matchup source '$path'. $_"
    }

    $seenRosters = @{}
    $result = @()
    foreach ($row in $rows) {
        $legacy = ConvertTo-CmuLegacyRow -Row $row -Week $Week
        $key = [string]$legacy.roster_id
        if ($seenRosters.ContainsKey($key)) {
            throw "Canonical current matchup source contains duplicate Sleeper roster_id '$key'."
        }
        $seenRosters[$key] = $true
        $result += $legacy
    }
    return @($result | Sort-Object { [int]$_.roster_id })
}

function Get-CanonicalCurrentMatchupLoad {
    param(
        [string]$CanonicalLeagueID = "nfl-reise",
        [Parameter(Mandatory = $true)][int]$Season,
        [Parameter(Mandatory = $true)][int]$Week
    )
    try {
        $rows = @(Get-CanonicalCurrentMatchupRows -CanonicalLeagueID $CanonicalLeagueID -Season $Season -Week $Week)
        return [PSCustomObject][ordered]@{ Success = $true; Rows = $rows }
    }
    catch {
        Write-Warning "Could not load canonical current matchup facts for $CanonicalLeagueID/$Season Week $Week. $_"
        return [PSCustomObject][ordered]@{ Success = $false; Rows = @() }
    }
}

Export-ModuleMember -Function @(
    "Get-CanonicalCurrentMatchupRows",
    "Get-CanonicalCurrentMatchupLoad"
)
