function Get-PsaValue {
    param([AllowNull()][object]$Object, [Parameter(Mandatory = $true)][string[]]$Names)
    if ($null -eq $Object) { return $null }
    foreach ($name in $Names) {
        if ($Object.PSObject.Properties.Name -contains $name) { return $Object.$name }
    }
    return $null
}

function Get-PsaCollection {
    param([AllowNull()][object]$Value)
    if ($null -eq $Value) { return @() }
    if ($Value -is [string] -or $Value -isnot [System.Collections.IEnumerable]) { return @($Value) }
    return @($Value)
}

function ConvertTo-PsaPlayerID {
    param([AllowNull()][object]$Value)
    if ($null -eq $Value) { return $null }
    $text = ([string]$Value).Trim()
    if ([string]::IsNullOrWhiteSpace($text) -or $text -eq '0') { return $null }
    return $text
}

function ConvertTo-PsaNormalizedState {
    param([AllowNull()][string]$ProviderStatus)
    $status = if ($null -eq $ProviderStatus) { '' } else { $ProviderStatus.Trim().ToUpperInvariant() }
    switch ($status) {
        'OUT' { return 'out' }
        'QUESTIONABLE' { return 'uncertain' }
        'DOUBTFUL' { return 'uncertain' }
        'ACTIVE' { return 'available' }
        default { return 'unknown' }
    }
}

function Get-EspnScoringAvailabilityObservations {
    param(
        [Parameter(Mandatory = $true)][int]$Season,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$Teams,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$Players,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$CanonicalIdentities,
        [int]$TimeoutSec = 15
    )

    $playerBySleeper = @{}
    foreach ($player in @($Players)) {
        $sleeperID = ConvertTo-PsaPlayerID (Get-PsaValue -Object $player -Names @('ID','PlayerID','SleeperID'))
        if ($null -ne $sleeperID) { $playerBySleeper[$sleeperID] = $player }
    }

    $espnBySleeper = @{}
    $ambiguousSleeper = @{}
    $ambiguousEspn = @{}
    foreach ($identity in @($CanonicalIdentities)) {
        $ids = Get-PsaValue -Object $identity -Names @('IDs')
        $sleeperID = ConvertTo-PsaPlayerID (Get-PsaValue -Object $ids -Names @('Sleeper'))
        $espnID = ConvertTo-PsaPlayerID (Get-PsaValue -Object $ids -Names @('ESPN'))
        if ($null -eq $sleeperID -or $null -eq $espnID) { continue }

        if ($espnBySleeper.ContainsKey($sleeperID) -and $espnBySleeper[$sleeperID] -ne $espnID) {
            $ambiguousSleeper[$sleeperID] = $true
            continue
        }
        $existingSleeper = @($espnBySleeper.Keys | Where-Object { $espnBySleeper[$_] -eq $espnID -and $_ -ne $sleeperID })
        if ($existingSleeper.Count -gt 0) {
            $ambiguousEspn[$espnID] = $true
            continue
        }
        $espnBySleeper[$sleeperID] = $espnID
    }

    foreach ($sleeperID in @($ambiguousSleeper.Keys)) {
        $espnBySleeper.Remove($sleeperID)
        Write-Warning "Canonical scoring-availability identity has multiple ESPN IDs for Sleeper '$sleeperID'; skipping."
    }
    foreach ($espnID in @($ambiguousEspn.Keys)) {
        foreach ($sleeperID in @($espnBySleeper.Keys | Where-Object { $espnBySleeper[$_] -eq $espnID })) {
            $espnBySleeper.Remove($sleeperID)
        }
        Write-Warning "Canonical scoring-availability ESPN ID '$espnID' maps to multiple Sleeper players; skipping."
    }

    $targetByEspn = @{}
    foreach ($team in @($Teams)) {
        foreach ($rawStarterID in @(Get-PsaCollection (Get-PsaValue -Object $team -Names @('Starter','StarterIDs','Starters')))) {
            $starterID = ConvertTo-PsaPlayerID $rawStarterID
            if ($null -eq $starterID -or -not $playerBySleeper.ContainsKey($starterID)) { continue }
            if (-not $espnBySleeper.ContainsKey($starterID)) { continue }
            $espnID = [string]$espnBySleeper[$starterID]
            $targetByEspn[$espnID] = $starterID
        }
    }

    $espnIDs = @($targetByEspn.Keys | Where-Object { $null -ne $targetByEspn[$_] } | Sort-Object -Unique)
    if ($espnIDs.Count -eq 0) { return @() }

    $filter = @{
        players = @{
            filterIds = @{ value = @($espnIDs | ForEach-Object { [int64]$_ }) }
            sortPercOwned = @{ sortPriority = 1; sortAsc = $false }
            limit = [Math]::Max(1, $espnIDs.Count)
        }
    } | ConvertTo-Json -Depth 8 -Compress

    $uri = "https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/$Season/segments/0/leaguedefaults/3?view=kona_player_info"
    try {
        $response = Invoke-RestMethod -Method Get -Uri $uri -Headers @{
            'Accept' = 'application/json'
            'X-Fantasy-Filter' = $filter
            'User-Agent' = 'fantasy-app/espn-scoring-availability'
        } -TimeoutSec $TimeoutSec
    }
    catch {
        Write-Warning "ESPN scoring-availability request failed; availability remains unknown. $_"
        return @()
    }

    $observedAtUtc = [DateTimeOffset]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ss'Z'")
    $observations = @()
    foreach ($entry in @(Get-PsaCollection (Get-PsaValue -Object $response -Names @('players','Players')))) {
        $player = Get-PsaValue -Object $entry -Names @('player','Player')
        if ($null -eq $player) { $player = $entry }

        $espnID = ([string](Get-PsaValue -Object $player -Names @('id','ID'))).Trim()
        if ([string]::IsNullOrWhiteSpace($espnID)) {
            $espnID = ([string](Get-PsaValue -Object $entry -Names @('id','ID'))).Trim()
        }
        if ([string]::IsNullOrWhiteSpace($espnID) -or -not $targetByEspn.ContainsKey($espnID)) { continue }

        $sleeperID = $targetByEspn[$espnID]
        if ($null -eq $sleeperID) { continue }

        $providerStatus = ([string](Get-PsaValue -Object $player -Names @('injuryStatus','InjuryStatus'))).Trim()
        $observations += [PSCustomObject][ordered]@{
            PlayerID = [string]$sleeperID
            ESPNPlayerID = [string]$espnID
            State = ConvertTo-PsaNormalizedState -ProviderStatus $providerStatus
            ProviderStatus = if ([string]::IsNullOrWhiteSpace($providerStatus)) { $null } else { $providerStatus.ToUpperInvariant() }
            Source = 'ESPN'
            ObservedAtUtc = $observedAtUtc
        }
    }
    return @($observations)
}

function Add-PlayerScoringAvailabilityDecisionFacts {
    param(
        [Parameter(Mandatory = $true)][object]$BaseReadModel,
        [AllowNull()][object[]]$Observations
    )

    $relevance = Get-PsaValue -Object $BaseReadModel -Names @('FantasyRelevance')
    if ($null -eq $relevance) { return $BaseReadModel }

    $byPlayer = @{}
    foreach ($observation in @(Get-PsaCollection $Observations)) {
        if ($null -eq $observation) { continue }
        $playerID = ConvertTo-PsaPlayerID (Get-PsaValue -Object $observation -Names @('PlayerID'))
        if ($null -ne $playerID) { $byPlayer[$playerID] = $observation }
    }

    foreach ($team in @(Get-PsaCollection (Get-PsaValue -Object $relevance -Names @('Teams')))) {
        if ($null -eq $team) { continue }

        $slotByStarter = @{}
        foreach ($slot in @(Get-PsaCollection (Get-PsaValue -Object $team -Names @('Slots')))) {
            if ($null -eq $slot) { continue }
            $starterID = ConvertTo-PsaPlayerID (Get-PsaValue -Object $slot -Names @('CurrentStarterID'))
            if ($null -ne $starterID) { $slotByStarter[$starterID] = $slot }
            $slot | Add-Member -NotePropertyName ScoringAvailability -NotePropertyValue $null -Force
        }

        foreach ($player in @(Get-PsaCollection (Get-PsaValue -Object $team -Names @('Players')))) {
            if ($null -eq $player) { continue }
            $playerID = ConvertTo-PsaPlayerID (Get-PsaValue -Object $player -Names @('PlayerID'))
            $observation = if ($null -ne $playerID -and $byPlayer.ContainsKey($playerID)) { $byPlayer[$playerID] } else { $null }
            $availability = if ($null -eq $observation) {
                [PSCustomObject][ordered]@{
                    State = 'unknown'
                    ProviderStatus = $null
                    Source = 'ESPN'
                    ObservedAtUtc = $null
                }
            } else {
                [PSCustomObject][ordered]@{
                    State = [string](Get-PsaValue -Object $observation -Names @('State'))
                    ProviderStatus = Get-PsaValue -Object $observation -Names @('ProviderStatus')
                    Source = [string](Get-PsaValue -Object $observation -Names @('Source'))
                    ObservedAtUtc = Get-PsaValue -Object $observation -Names @('ObservedAtUtc')
                }
            }
            $player | Add-Member -NotePropertyName ScoringAvailability -NotePropertyValue $availability -Force

            if ($null -ne $playerID -and $slotByStarter.ContainsKey($playerID)) {
                $slotByStarter[$playerID].ScoringAvailability = $availability
            }

            if (
                [string](Get-PsaValue -Object $player -Names @('Placement')) -eq 'starter' -and
                [string](Get-PsaValue -Object $availability -Names @('State')) -eq 'out' -and
                [string](Get-PsaValue -Object $player -Names @('GameState')) -ne 'completed'
            ) {
                $player.HasDirectScoringPath = $false
            }
        }

        $players = @(Get-PsaCollection (Get-PsaValue -Object $team -Names @('Players')))
        $team.UnlockedStarterCount = @($players | Where-Object {
            $_.Placement -eq 'starter' -and $_.GameState -eq 'unlocked' -and $_.HasDirectScoringPath
        }).Count
        $team.LockedActiveStarterCount = @($players | Where-Object {
            $_.Placement -eq 'starter' -and $_.GameState -eq 'locked-active' -and $_.HasDirectScoringPath
        }).Count
        $team.HasRemainingScoringPath = @($players | Where-Object {
            $_.HasDirectScoringPath -or $_.HasAlternativePath
        }).Count -gt 0
    }

    $BaseReadModel | Add-Member -NotePropertyName ScoringAvailabilityObservations -NotePropertyValue @($Observations) -Force
    if ($relevance.PSObject.Properties.Name -contains 'Version') {
        $relevance.Version = [Math]::Max(4, [int]$relevance.Version)
    }
    if ($BaseReadModel.PSObject.Properties.Name -contains 'SchemaVersion') {
        $BaseReadModel.SchemaVersion = [Math]::Max(3, [int]$BaseReadModel.SchemaVersion)
    }
    return $BaseReadModel
}

Export-ModuleMember -Function Get-EspnScoringAvailabilityObservations, Add-PlayerScoringAvailabilityDecisionFacts
