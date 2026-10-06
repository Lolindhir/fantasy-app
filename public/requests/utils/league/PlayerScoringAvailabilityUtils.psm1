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

function ConvertTo-PsaUtcTimestamp {
    param([AllowNull()][object]$Value)

    if ($null -eq $Value) { return $null }

    try {
        if ($Value -is [DateTimeOffset]) {
            return ([DateTimeOffset]$Value).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss'Z'")
        }

        if ($Value -is [DateTime]) {
            $date = [DateTime]$Value
            if ($date.Kind -eq [DateTimeKind]::Unspecified) {
                $date = [DateTime]::SpecifyKind($date, [DateTimeKind]::Utc)
            }
            return $date.ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss'Z'")
        }

        $text = ([string]$Value).Trim()
        if ([string]::IsNullOrWhiteSpace($text)) { return $null }

        $parsed = [DateTimeOffset]::Parse(
            $text,
            [System.Globalization.CultureInfo]::InvariantCulture,
            [System.Globalization.DateTimeStyles]::AssumeUniversal
        )
        return $parsed.ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss'Z'")
    }
    catch {
        return $null
    }
}

function Resolve-PlayerScoringAvailabilityObservationTimes {
    param(
        [AllowNull()][object[]]$CurrentObservations,
        [AllowNull()][object[]]$PreviousObservations
    )

    $previousByPlayer = @{}
    $ambiguousPrevious = @{}
    foreach ($previous in @(Get-PsaCollection $PreviousObservations)) {
        if ($null -eq $previous) { continue }
        $playerID = ConvertTo-PsaPlayerID (Get-PsaValue -Object $previous -Names @('PlayerID'))
        if ($null -eq $playerID) { continue }

        if ($previousByPlayer.ContainsKey($playerID) -or $ambiguousPrevious.ContainsKey($playerID)) {
            $previousByPlayer.Remove($playerID)
            $ambiguousPrevious[$playerID] = $true
            continue
        }
        $previousByPlayer[$playerID] = $previous
    }

    $resolved = @()
    foreach ($current in @(Get-PsaCollection $CurrentObservations)) {
        if ($null -eq $current) { continue }

        $playerID = ConvertTo-PsaPlayerID (Get-PsaValue -Object $current -Names @('PlayerID'))
        $currentObservedAtUtc = ConvertTo-PsaUtcTimestamp (Get-PsaValue -Object $current -Names @('ObservedAtUtc'))
        $firstObservedAtUtc = $currentObservedAtUtc

        if ($null -ne $playerID -and $previousByPlayer.ContainsKey($playerID)) {
            $previous = $previousByPlayer[$playerID]
            $sameProviderStatus = (
                [string](Get-PsaValue -Object $previous -Names @('ESPNPlayerID')) -eq [string](Get-PsaValue -Object $current -Names @('ESPNPlayerID')) -and
                [string](Get-PsaValue -Object $previous -Names @('Source')) -eq [string](Get-PsaValue -Object $current -Names @('Source')) -and
                [string](Get-PsaValue -Object $previous -Names @('ProviderStatus')) -eq [string](Get-PsaValue -Object $current -Names @('ProviderStatus')) -and
                [string](Get-PsaValue -Object $previous -Names @('State')) -eq [string](Get-PsaValue -Object $current -Names @('State'))
            )
            if ($sameProviderStatus) {
                $previousFirstObservedAtUtc = ConvertTo-PsaUtcTimestamp (Get-PsaValue -Object $previous -Names @('FirstObservedAtUtc'))
                if ($null -eq $previousFirstObservedAtUtc) {
                    $previousFirstObservedAtUtc = ConvertTo-PsaUtcTimestamp (Get-PsaValue -Object $previous -Names @('ObservedAtUtc'))
                }
                if (-not [string]::IsNullOrWhiteSpace([string]$previousFirstObservedAtUtc)) {
                    $firstObservedAtUtc = [string]$previousFirstObservedAtUtc
                }
            }
        }

        $stableObservedAtUtc = if ([string]::IsNullOrWhiteSpace([string]$firstObservedAtUtc)) { $null } else { [string]$firstObservedAtUtc }
        $resolved += [PSCustomObject][ordered]@{
            PlayerID = [string](Get-PsaValue -Object $current -Names @('PlayerID'))
            ESPNPlayerID = [string](Get-PsaValue -Object $current -Names @('ESPNPlayerID'))
            State = [string](Get-PsaValue -Object $current -Names @('State'))
            ProviderStatus = Get-PsaValue -Object $current -Names @('ProviderStatus')
            Source = [string](Get-PsaValue -Object $current -Names @('Source'))
            FirstObservedAtUtc = $stableObservedAtUtc
            ObservedAtUtc = $stableObservedAtUtc
        }
    }

    return @($resolved)
}

function Get-CanonicalScoringAvailabilityObservations {
    param(
        [Parameter(Mandatory = $true)][int]$Season,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$Teams,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$Players,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$CanonicalIdentities,
        [Parameter(Mandatory = $true)][string]$SnapshotPath
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

    # Canonical source-data snapshot (espn.player-availability, #347); no network access here.
    if (-not (Test-Path -LiteralPath $SnapshotPath)) {
        Write-Warning "Canonical player-availability snapshot is missing; availability remains unknown."
        return @()
    }
    try {
        $snapshot = Get-Content -LiteralPath $SnapshotPath -Raw | ConvertFrom-Json
    }
    catch {
        Write-Warning "Canonical player-availability snapshot is unreadable; availability remains unknown. $_"
        return @()
    }
    if ([int](Get-PsaValue -Object $snapshot -Names @('Season')) -ne $Season) {
        Write-Warning "Canonical player-availability snapshot is not for season $Season; availability remains unknown."
        return @()
    }

    $rowByEspn = @{}
    foreach ($row in @(Get-PsaCollection (Get-PsaValue -Object $snapshot -Names @('Players')))) {
        if ($null -eq $row) { continue }
        $rowEspnID = ([string](Get-PsaValue -Object $row -Names @('ESPNPlayerID'))).Trim()
        if (-not [string]::IsNullOrWhiteSpace($rowEspnID)) { $rowByEspn[$rowEspnID] = $row }
    }

    $observations = @()
    foreach ($espnID in $espnIDs) {
        if (-not $rowByEspn.ContainsKey($espnID)) { continue }
        $row = $rowByEspn[$espnID]
        $sleeperID = $targetByEspn[$espnID]
        if ($null -eq $sleeperID) { continue }

        $providerStatus = ([string](Get-PsaValue -Object $row -Names @('ProviderStatus'))).Trim()
        $observations += [PSCustomObject][ordered]@{
            PlayerID = [string]$sleeperID
            ESPNPlayerID = [string]$espnID
            State = ConvertTo-PsaNormalizedState -ProviderStatus $providerStatus
            ProviderStatus = if ([string]::IsNullOrWhiteSpace($providerStatus)) { $null } else { $providerStatus.ToUpperInvariant() }
            Source = 'ESPN'
            ObservedAtUtc = ConvertTo-PsaUtcTimestamp (Get-PsaValue -Object $row -Names @('StatusSinceUtc'))
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
                    FirstObservedAtUtc = $null
                    ObservedAtUtc = $null
                }
            } else {
                [PSCustomObject][ordered]@{
                    State = [string](Get-PsaValue -Object $observation -Names @('State'))
                    ProviderStatus = Get-PsaValue -Object $observation -Names @('ProviderStatus')
                    Source = [string](Get-PsaValue -Object $observation -Names @('Source'))
                    FirstObservedAtUtc = Get-PsaValue -Object $observation -Names @('FirstObservedAtUtc','ObservedAtUtc')
                    ObservedAtUtc = Get-PsaValue -Object $observation -Names @('ObservedAtUtc','FirstObservedAtUtc')
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

Export-ModuleMember -Function Get-CanonicalScoringAvailabilityObservations, Resolve-PlayerScoringAvailabilityObservationTimes, Add-PlayerScoringAvailabilityDecisionFacts
