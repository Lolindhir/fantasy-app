# Canonical matchup facts and neutral team order for the Weekly Recaps generator.
# Remainder of the retired FantasyGameContext/Matchups PowerShell (ADR-075, Issue #1199 section 3 step 8): only what
# WeeklyRecapUtils.psm1 still calls. It disappears with the Weekly Recaps migration (Issue #1199 section 4).
Import-Module "$PSScriptRoot\..\general\SleeperPlayerIdUtils.psm1" -ErrorAction Stop -Force
Import-Module "$PSScriptRoot\StandingUtils.psm1" -ErrorAction Stop -Force
Import-Module "$PSScriptRoot\FantasyTeamOrderUtils.psm1" -ErrorAction Stop -Force

function Get-FgcPropertyValue {
    param([AllowNull()][object]$Object, [Parameter(Mandatory = $true)][string[]]$Names)

    if ($null -eq $Object) { return $null }
    foreach ($name in $Names) {
        if ($Object.PSObject.Properties.Name -contains $name) {
            return $Object.$name
        }
    }
    return $null
}

function Get-FgcCollection {
    param([AllowNull()][object]$Value)
    if ($null -eq $Value) { return @() }
    if ($Value -is [string] -or $Value -isnot [System.Collections.IEnumerable]) { return @($Value) }
    return @($Value)
}

function ConvertTo-FgcPlayerID {
    param([AllowNull()][object]$Player)

    if ($null -eq $Player) { return $null }
    if ($Player -is [string] -or $Player -is [ValueType]) {
        return ConvertTo-SleeperPlayerID -Value $Player
    }

    $direct = Get-FgcPropertyValue -Object $Player -Names @('PlayerID','ID','SleeperID')
    if ($null -ne $direct) {
        $text = ConvertTo-SleeperPlayerID -Value $direct
        if ($null -ne $text) { return $text }
    }

    foreach ($mapping in @(Get-FgcCollection (Get-FgcPropertyValue -Object $Player -Names @('ProviderMappings')))) {
        if ([string](Get-FgcPropertyValue -Object $mapping -Names @('Provider')) -ne 'Sleeper') { continue }
        $providerID = Get-FgcPropertyValue -Object $mapping -Names @('ProviderPlayerID','PlayerID')
        if ($null -ne $providerID -and -not [string]::IsNullOrWhiteSpace([string]$providerID)) {
            return ([string]$providerID).Trim()
        }
    }

    return $null
}

function ConvertTo-FgcCanonicalPlayerID {
    param([AllowNull()][object]$Player)
    if ($null -eq $Player -or $Player -is [string] -or $Player -is [ValueType]) { return $null }
    $value = Get-FgcPropertyValue -Object $Player -Names @('CanonicalPlayerID')
    if ($null -eq $value -or [string]::IsNullOrWhiteSpace([string]$value)) { return $null }
    return ([string]$value).Trim()
}

function New-FantasyGameContextMatchupID {
    param(
        [Parameter(Mandatory = $true)][string]$Season,
        [Parameter(Mandatory = $true)][int]$Week,
        [Parameter(Mandatory = $true)][string[]]$FantasyTeamIDs
    )

    $teamIDs = @($FantasyTeamIDs | ForEach-Object { ([string]$_).Trim() } | Sort-Object)
    if ($teamIDs.Count -ne 2 -or @($teamIDs | Where-Object { [string]::IsNullOrWhiteSpace($_) }).Count -gt 0) {
        throw "Fantasy matchup identity requires exactly two stable fantasy team IDs."
    }

    $material = "$Season|$Week|$($teamIDs -join '|')"
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($material)
        $hash = $sha.ComputeHash($bytes)
        $hex = -join ($hash | ForEach-Object { $_.ToString('x2') })
        return "fgm-$($hex.Substring(0, 24))"
    }
    finally {
        $sha.Dispose()
    }
}


function ConvertTo-FgcPointMapFromRows {
    param([AllowNull()][object]$Rows)
    $map = @{}
    foreach ($row in @(Get-FgcCollection $Rows)) {
        if ($null -eq $row) { continue }
        $player = Get-FgcPropertyValue -Object $row -Names @('Player')
        $playerID = ConvertTo-FgcPlayerID -Player $player
        if ([string]::IsNullOrWhiteSpace($playerID)) { continue }
        $points = Get-FgcPropertyValue -Object $row -Names @('Points')
        if ($null -ne $points) { $map[$playerID] = [double]$points }
    }
    return $map
}


function Get-FgcCanonicalTeamID {
    param([AllowNull()][object]$Row)
    foreach ($mapping in @(Get-FgcCollection (Get-FgcPropertyValue -Object $Row -Names @('ProviderMappings')))) {
        if ([string](Get-FgcPropertyValue -Object $mapping -Names @('Provider')) -ne 'Sleeper') { continue }
        $id = Get-FgcPropertyValue -Object $mapping -Names @('ProviderRosterID','RosterID')
        if ($null -ne $id -and -not [string]::IsNullOrWhiteSpace([string]$id)) { return ([string]$id).Trim() }
    }
    return $null
}

function Get-FgcCanonicalProviderMatchupID {
    param([AllowNull()][object]$Row)
    foreach ($mapping in @(Get-FgcCollection (Get-FgcPropertyValue -Object $Row -Names @('ProviderMappings')))) {
        if ([string](Get-FgcPropertyValue -Object $mapping -Names @('Provider')) -ne 'Sleeper') { continue }
        $id = Get-FgcPropertyValue -Object $mapping -Names @('ProviderMatchupID','MatchupID')
        if ($null -ne $id -and -not [string]::IsNullOrWhiteSpace([string]$id)) { return ([string]$id).Trim() }
    }
    return $null
}

function ConvertTo-FgcCanonicalMatchupFacts {
    param(
        [Parameter(Mandatory = $true)][string]$Season,
        [Parameter(Mandatory = $true)][int]$Week,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$MatchupRows
    )

    $normalizedRows = @()
    foreach ($row in @($MatchupRows)) {
        $providerMatchupID = Get-FgcCanonicalProviderMatchupID -Row $row
        $fantasyTeamID = Get-FgcCanonicalTeamID -Row $row
        if ([string]::IsNullOrWhiteSpace($providerMatchupID) -or [string]::IsNullOrWhiteSpace($fantasyTeamID)) { continue }

        $playerPoints = ConvertTo-FgcPointMapFromRows -Rows (Get-FgcPropertyValue -Object $row -Names @('PlayerPoints'))
        $starterPoints = ConvertTo-FgcPointMapFromRows -Rows (Get-FgcPropertyValue -Object $row -Names @('StarterPoints'))
        $starterIDs = @(
            Get-FgcCollection (Get-FgcPropertyValue -Object $row -Names @('Starters')) |
                ForEach-Object { ConvertTo-FgcPlayerID -Player $_ } |
                Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
                Sort-Object -Unique
        )
        $players = @()
        foreach ($playerRef in @(Get-FgcCollection (Get-FgcPropertyValue -Object $row -Names @('Players')))) {
            $playerID = ConvertTo-FgcPlayerID -Player $playerRef
            if ([string]::IsNullOrWhiteSpace($playerID)) { continue }
            $isStarter = $starterIDs -contains $playerID
            $hasPoints = $playerPoints.ContainsKey($playerID)
            $points = if ($hasPoints) { [double]$playerPoints[$playerID] } else { $null }
            if ($isStarter -and $starterPoints.ContainsKey($playerID)) {
                $hasPoints = $true
                $points = [double]$starterPoints[$playerID]
            }
            $players += [PSCustomObject][ordered]@{
                PlayerID          = $playerID
                CanonicalPlayerID = ConvertTo-FgcCanonicalPlayerID -Player $playerRef
                IsStarter         = $isStarter
                HasPoints         = $hasPoints
                Points            = $points
            }
        }

        foreach ($starterID in $starterIDs) {
            if (@($players | Where-Object { $_.PlayerID -eq $starterID }).Count -eq 0) {
                throw "Historical fantasy matchup Week $Week Team '$fantasyTeamID' has starter '$starterID' outside the rostered player set."
            }
        }

        $normalizedRows += [PSCustomObject][ordered]@{
            ProviderMatchupID = $providerMatchupID
            FantasyTeamID     = $fantasyTeamID
            Players           = @($players | Sort-Object PlayerID -Unique)
            FinalScore        = [double](Get-FgcPropertyValue -Object $row -Names @('Points'))
            HasCustomPoints   = $null -ne (Get-FgcPropertyValue -Object $row -Names @('CustomPoints'))
        }
    }

    return ConvertTo-FgcPairedMatchupFacts -Season $Season -Week $Week -Rows $normalizedRows
}

function ConvertTo-FgcPairedMatchupFacts {
    param(
        [Parameter(Mandatory = $true)][string]$Season,
        [Parameter(Mandatory = $true)][int]$Week,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$Rows
    )

    $playerOwner = @{}
    $result = @()
    foreach ($group in @($Rows | Group-Object ProviderMatchupID | Sort-Object Name)) {
        $participants = @($group.Group | Sort-Object { [string]$_.FantasyTeamID })
        if ($participants.Count -ne 2) {
            Write-Warning "Excluding malformed fantasy matchup '$($group.Name)' in Week $Week because it has $($participants.Count) participants."
            continue
        }
        $teamIDs = @($participants | ForEach-Object { [string]$_.FantasyTeamID })
        $matchupID = New-FantasyGameContextMatchupID -Season $Season -Week $Week -FantasyTeamIDs $teamIDs

        foreach ($participant in $participants) {
            foreach ($player in @($participant.Players)) {
                if ($playerOwner.ContainsKey($player.PlayerID) -and $playerOwner[$player.PlayerID] -ne [string]$participant.FantasyTeamID) {
                    throw "Fantasy matchup evidence assigns PlayerID '$($player.PlayerID)' to multiple fantasy teams in Week $Week."
                }
                $playerOwner[$player.PlayerID] = [string]$participant.FantasyTeamID
            }
        }

        $result += [PSCustomObject][ordered]@{
            FantasyMatchupID = $matchupID
            TeamIDs          = @($teamIDs)
            Teams            = @($participants | ForEach-Object {
                [PSCustomObject][ordered]@{
                    FantasyTeamID   = [string]$_.FantasyTeamID
                    Players         = @($_.Players | Sort-Object PlayerID)
                    FinalScore      = $_.FinalScore
                    HasCustomPoints = [bool]$_.HasCustomPoints
                }
            })
        }
    }
    return @($result | Sort-Object FantasyMatchupID)
}

function Get-MatchupParticipantOrderMap {
    param(
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$Standings,
        [Parameter(Mandatory = $true)][int]$Season,
        [switch]$HistoricalCutoff
    )

    $overall = $null
    if (-not $HistoricalCutoff) {
        $overall = @($Standings | Where-Object { [string]$_.Season -eq 'AllTime' }) | Select-Object -First 1
    }
    else {
        $seasonRows = @(
            $Standings | Where-Object {
                [string]$_.Season -match '^\d{4}$' -and [int]$_.Season -le $Season
            }
        )
        if ($seasonRows.Count -gt 0) {
            $overall = Get-OutputStandingsForAllTime -allSeasonStandings $seasonRows
        }
    }

    if ($null -eq $overall -or @($overall.Playoffs).Count -eq 0) {
        throw "Matchups $Season cannot resolve the All-Time Overall Standings order."
    }

    return Get-FantasyTeamNeutralOrderIndex -AllTimeOverallStandings @($overall.Playoffs)
}

Export-ModuleMember -Function ConvertTo-FgcCanonicalMatchupFacts, Get-MatchupParticipantOrderMap
