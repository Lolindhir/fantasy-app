function Get-EsaValue {
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

function Get-EsaCollection {
    param([AllowNull()][object]$Value)

    if ($null -eq $Value) { return @() }
    if ($Value -is [string] -or $Value -isnot [System.Collections.IEnumerable]) { return @($Value) }
    return @($Value)
}

function ConvertTo-EsaPlayerID {
    param([AllowNull()][object]$Value)

    if ($null -eq $Value) { return $null }
    $text = ([string]$Value).Trim()
    if ([string]::IsNullOrWhiteSpace($text) -or $text -eq '0') { return $null }
    return $text
}

function ConvertTo-EspnScoringAvailabilityObservation {
    param(
        [Parameter(Mandatory = $true)][string]$ProviderPlayerID,
        [AllowNull()][object]$Status,
        [AllowNull()][object]$ProviderDate = $null
    )

    $providerStatus = ([string]$Status).Trim()
    if ([string]::IsNullOrWhiteSpace($providerStatus)) { return $null }

    $key = ($providerStatus -replace '[^A-Za-z0-9]+', '_').Trim('_').ToUpperInvariant()
    $state = 'unknown'
    $reason = 'provider-status-unmapped'

    switch ($key) {
        'ACTIVE' {
            $state = 'available'
            $reason = 'active'
        }
        'PROBABLE' {
            $state = 'uncertain'
            $reason = 'probable'
        }
        'QUESTIONABLE' {
            $state = 'uncertain'
            $reason = 'questionable'
        }
        'DOUBTFUL' {
            $state = 'uncertain'
            $reason = 'doubtful'
        }
        'OUT' {
            $state = 'unavailable'
            $reason = 'out'
        }
        'INACTIVE' {
            $state = 'unavailable'
            $reason = 'inactive'
        }
        'INJURY_RESERVE' {
            $state = 'unavailable'
            $reason = 'injury-reserve'
        }
        'INJURED_RESERVE' {
            $state = 'unavailable'
            $reason = 'injury-reserve'
        }
        'IR' {
            $state = 'unavailable'
            $reason = 'injury-reserve'
        }
        'SUSPENDED' {
            $state = 'unavailable'
            $reason = 'suspended'
        }
    }

    $dateText = ([string]$ProviderDate).Trim()
    return [PSCustomObject][ordered]@{
        State            = $state
        Reason           = $reason
        Source           = 'ESPN'
        Provider         = 'ESPN_SITE_INJURIES'
        ProviderPlayerID = $ProviderPlayerID
        ProviderStatus   = $providerStatus
        ProviderDate     = if ([string]::IsNullOrWhiteSpace($dateText)) { $null } else { $dateText }
    }
}

function Test-EspnScoringAvailabilityTerminal {
    param([AllowNull()][object]$Observation)

    if ($null -eq $Observation) { return $false }
    return [string](Get-EsaValue -Object $Observation -Names @('State')) -eq 'unavailable'
}

function Get-EspnScoringAvailabilityInjuryItems {
    param([AllowNull()][object]$Response)

    $items = @()
    foreach ($teamGroup in @(Get-EsaCollection -Value (Get-EsaValue -Object $Response -Names @('injuries')))) {
        if ($null -eq $teamGroup) { continue }

        $nested = Get-EsaValue -Object $teamGroup -Names @('injuries')
        if ($null -ne $nested) {
            $items += @(Get-EsaCollection -Value $nested)
            continue
        }

        if ($null -ne (Get-EsaValue -Object $teamGroup -Names @('athlete'))) {
            $items += $teamGroup
        }
    }
    return $items
}

function Get-EspnScoringAvailabilityBySleeperID {
    param(
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$Players,
        [AllowNull()][object]$InjuryResponse = $null,
        [string]$Endpoint = 'https://site.api.espn.com/apis/site/v2/sports/football/nfl/injuries'
    )

    if ($null -eq $InjuryResponse) {
        try {
            $InjuryResponse = Invoke-RestMethod -Uri $Endpoint -Method Get -TimeoutSec 20 -ErrorAction Stop
        }
        catch {
            Write-Warning "ESPN scoring availability unavailable: $($_.Exception.Message)"
            return @{}
        }
    }

    $byEspnID = @{}
    $ambiguousEspnIDs = @{}
    foreach ($injury in @(Get-EspnScoringAvailabilityInjuryItems -Response $InjuryResponse)) {
        if ($null -eq $injury) { continue }

        $athlete = Get-EsaValue -Object $injury -Names @('athlete')
        $espnID = ConvertTo-EsaPlayerID -Value (Get-EsaValue -Object $athlete -Names @('id'))
        if ($null -eq $espnID) { continue }

        $status = Get-EsaValue -Object $injury -Names @('status')
        if ($null -eq $status) {
            $fantasy = Get-EsaValue -Object $injury -Names @('fantasy')
            $status = Get-EsaValue -Object $fantasy -Names @('status')
        }

        $observation = ConvertTo-EspnScoringAvailabilityObservation -ProviderPlayerID $espnID -Status $status -ProviderDate (Get-EsaValue -Object $injury -Names @('date'))

        if ($null -eq $observation) { continue }
        if ($ambiguousEspnIDs.ContainsKey($espnID)) { continue }

        if ($byEspnID.ContainsKey($espnID)) {
            $existing = $byEspnID[$espnID]
            if (
                [string]$existing.ProviderStatus -ne [string]$observation.ProviderStatus -or
                [string]$existing.State -ne [string]$observation.State
            ) {
                $byEspnID.Remove($espnID)
                $ambiguousEspnIDs[$espnID] = $true
            }
            continue
        }

        $byEspnID[$espnID] = $observation
    }

    $result = @{}
    foreach ($player in @($Players)) {
        if ($null -eq $player) { continue }

        $sleeperID = ConvertTo-EsaPlayerID -Value (Get-EsaValue -Object $player -Names @('ID','PlayerID','SleeperID'))
        $espnID = ConvertTo-EsaPlayerID -Value (Get-EsaValue -Object $player -Names @('ESPNID','EspnID','espn_id'))
        if ($null -eq $sleeperID -or $null -eq $espnID) { continue }
        if (-not $byEspnID.ContainsKey($espnID)) { continue }

        if ($result.ContainsKey($sleeperID)) {
            throw "Duplicate Sleeper player identity '$sleeperID' while joining ESPN scoring availability."
        }
        $result[$sleeperID] = $byEspnID[$espnID]
    }

    return $result
}

Export-ModuleMember -Function ConvertTo-EspnScoringAvailabilityObservation, Test-EspnScoringAvailabilityTerminal, Get-EspnScoringAvailabilityBySleeperID
