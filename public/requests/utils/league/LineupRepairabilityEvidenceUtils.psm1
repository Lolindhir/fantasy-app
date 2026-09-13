Import-Module "$PSScriptRoot\LineupRepairabilityUtils.psm1" -ErrorAction Stop -Force

function Get-LreValue {
    param(
        [AllowNull()][object]$Object,
        [Parameter(Mandatory = $true)][string[]]$Names
    )

    if ($null -eq $Object) { return $null }
    foreach ($name in $Names) {
        if ($Object.PSObject.Properties.Name -contains $name) { return $Object.$name }
    }
    return $null
}

function Get-LreCollection {
    param([AllowNull()][object]$Value)

    if ($null -eq $Value) { return @() }
    if ($Value -is [string] -or $Value -isnot [System.Collections.IEnumerable]) { return @($Value) }
    return @($Value)
}

function ConvertTo-LrePlayerID {
    param([AllowNull()][object]$Value)

    if ($null -eq $Value) { return $null }
    $text = ([string]$Value).Trim()
    if ([string]::IsNullOrWhiteSpace($text) -or $text -eq '0') { return $null }
    return $text
}

function ConvertTo-LreUtc {
    param([AllowNull()][object]$Value)

    if ($null -eq $Value -or [string]::IsNullOrWhiteSpace([string]$Value)) { return $null }
    try {
        return [DateTimeOffset]::Parse(
            [string]$Value,
            [System.Globalization.CultureInfo]::InvariantCulture,
            [System.Globalization.DateTimeStyles]::AssumeUniversal
        ).ToUniversalTime()
    }
    catch {
        return $null
    }
}

function Get-LreWeek {
    param([AllowNull()][object]$Game)

    $text = ([string](Get-LreValue -Object $Game -Names @('Week','gameWeek'))).Trim()
    if ($text -match '^(\d+)$') { return [int]$matches[1] }
    if ($text -match '^Week\s+(\d+)$') { return [int]$matches[1] }
    return $null
}

function Get-LreStartUtc {
    param([AllowNull()][object]$Game)

    $direct = ConvertTo-LreUtc -Value (Get-LreValue -Object $Game -Names @('StartsAtUtc','startsAtUtc'))
    if ($null -ne $direct) { return $direct }

    $raw = Get-LreValue -Object $Game -Names @('gameTime_epoch','GameTimeEpoch')
    if ($null -eq $raw) { return $null }
    try {
        $epoch = [double]::Parse([string]$raw, [System.Globalization.CultureInfo]::InvariantCulture)
        return [DateTimeOffset]::FromUnixTimeSeconds([int64][Math]::Floor($epoch)).ToUniversalTime()
    }
    catch {
        return $null
    }
}

function Get-LineupExternalRepairEvidence {
    param(
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$Players,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$Teams,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$Schedule,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$MutableSlots,
        [AllowNull()][object]$AcquisitionCapability,
        [Parameter(Mandatory = $true)][int]$LineupWeek,
        [DateTimeOffset]$AsOfUtc = [DateTimeOffset]::UtcNow
    )

    $state = 'unknown'
    $nextRun = $null
    if (
        $null -ne $AcquisitionCapability -and
        [string](Get-LreValue -Object $AcquisitionCapability -Names @('State')) -eq 'known'
    ) {
        $allowed = Get-LreValue -Object $AcquisitionCapability -Names @('ExternalAddsAllowed')
        if ($null -eq $allowed) {
            $state = 'unknown'
        }
        elseif (-not [bool]$allowed) {
            $state = 'unavailable'
        }
        else {
            $nextRun = ConvertTo-LreUtc -Value (Get-LreValue -Object $AcquisitionCapability -Names @('NextWaiverRun'))
            $state = if ($null -ne $nextRun) { 'available' } else { 'unknown' }
        }
    }

    if ($state -ne 'available') {
        return [PSCustomObject][ordered]@{
            State                 = $state
            Candidates            = @()
            PlayerEvidenceUnknown = $false
        }
    }

    $owned = @{}
    $evidenceUnknown = $false
    foreach ($team in @($Teams)) {
        if ($null -eq $team) { continue }

        $names = @($team.PSObject.Properties.Name)
        $roster = if ($names -contains 'Roster') {
            $team.Roster
        }
        elseif ($names -contains 'PlayerIDs') {
            $team.PlayerIDs
        }
        else {
            $null
        }

        if ($null -eq $roster) {
            $evidenceUnknown = $true
            continue
        }

        foreach ($raw in @(Get-LreCollection -Value $roster)) {
            $id = ConvertTo-LrePlayerID -Value $raw
            if ($null -ne $id) { $owned[$id] = $true }
        }
    }

    $knownTeams = @{}
    $gamesByTeam = @{}
    foreach ($game in @($Schedule)) {
        if ($null -eq $game) { continue }

        $home = ([string](Get-LreValue -Object $game -Names @('teamIDHome','HomeTeamID','homeTeamID'))).Trim()
        $away = ([string](Get-LreValue -Object $game -Names @('teamIDAway','AwayTeamID','awayTeamID'))).Trim()
        foreach ($id in @($home, $away)) {
            if (-not [string]::IsNullOrWhiteSpace($id)) { $knownTeams[$id] = $true }
        }

        $week = Get-LreWeek -Game $game
        if ($null -eq $week -or [int]$week -ne $LineupWeek) { continue }

        foreach ($id in @($home, $away)) {
            if ([string]::IsNullOrWhiteSpace($id)) { continue }
            if (-not $gamesByTeam.ContainsKey($id)) { $gamesByTeam[$id] = @() }
            $gamesByTeam[$id] += $game
        }
    }

    $byID = @{}
    $ambiguous = @{}
    foreach ($player in @($Players)) {
        if ($null -eq $player) { continue }

        $id = ConvertTo-LrePlayerID -Value (Get-LreValue -Object $player -Names @('ID','PlayerID','SleeperID'))
        if ($null -eq $id) { continue }

        if ($byID.ContainsKey($id) -or $ambiguous.ContainsKey($id)) {
            $byID.Remove($id)
            $ambiguous[$id] = $true
        }
        else {
            $byID[$id] = $player
        }
    }
    if ($ambiguous.Count -gt 0) { $evidenceUnknown = $true }

    $candidates = @()
    foreach ($id in @($byID.Keys | Sort-Object)) {
        if ($owned.ContainsKey($id)) { continue }

        $player = $byID[$id]
        $position = ([string](Get-LreValue -Object $player -Names @('Position','FantasyPosition'))).Trim().ToUpperInvariant()
        $positionRelevant = -not [string]::IsNullOrWhiteSpace($position) -and @(
            $MutableSlots | Where-Object {
                Test-LineupRepairabilitySlotEligibility -Position $position -SlotType ([string]$_.SlotType)
            }
        ).Count -gt 0
        if (-not [string]::IsNullOrWhiteSpace($position) -and -not $positionRelevant) { continue }

        $nflTeam = ([string](Get-LreValue -Object $player -Names @('TeamID','NFLTeamID'))).Trim()
        if ([string]::IsNullOrWhiteSpace($nflTeam)) { continue }
        if (-not $knownTeams.ContainsKey($nflTeam)) {
            $evidenceUnknown = $true
            continue
        }

        $games = if ($gamesByTeam.ContainsKey($nflTeam)) { @($gamesByTeam[$nflTeam]) } else { @() }
        if ($games.Count -eq 0) { continue }
        if ($games.Count -ne 1) {
            $evidenceUnknown = $true
            continue
        }

        $game = $games[0]
        $start = Get-LreStartUtc -Game $game
        if ($null -eq $start) {
            $evidenceUnknown = $true
            continue
        }

        $status = [string](Get-LreValue -Object $game -Names @('gameStatus','Status'))
        $isFinal = -not [string]::IsNullOrWhiteSpace($status) -and $status -match '^Final'
        $isLocked = $start -le $AsOfUtc.ToUniversalTime()
        $waiverMissesLock = $nextRun -ge $start
        if ($isFinal -or $isLocked -or $waiverMissesLock) { continue }

        if ([string]::IsNullOrWhiteSpace($position)) {
            $evidenceUnknown = $true
            continue
        }

        $candidates += [PSCustomObject][ordered]@{
            PlayerID = $id
            Position = $position
        }
    }

    return [PSCustomObject][ordered]@{
        State                 = $state
        Candidates            = $candidates
        PlayerEvidenceUnknown = $evidenceUnknown
    }
}

Export-ModuleMember -Function Get-LineupExternalRepairEvidence
