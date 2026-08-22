# ===========================================================================
# Draft Compare Utils
# ===========================================================================

function ConvertTo-DraftCompareSafeArray {
    param([AllowNull()]$Value)

    if ($null -eq $Value) { return @() }
    if ($Value -is [array]) { return $Value }
    return @($Value)
}

function Get-DraftCompareProperty {
    param(
        [AllowNull()]$Object,
        [Parameter(Mandatory = $true)][string]$PropertyName,
        [AllowNull()]$DefaultValue = $null
    )

    if ($null -eq $Object) { return $DefaultValue }
    if ($Object.PSObject.Properties.Name -contains $PropertyName) {
        return $Object.PSObject.Properties[$PropertyName].Value
    }

    return $DefaultValue
}

function ConvertTo-DraftCompareValue {
    param(
        [AllowNull()]$Value,
        [Parameter(Mandatory = $true)][string]$PropertyName
    )

    if ($null -eq $Value) { return $null }

    if ($PropertyName -eq "DraftStartTimeUtc") {
        if ($Value -is [DateTimeOffset]) { return $Value.UtcDateTime.ToString("o") }
        if ($Value -is [DateTime]) { return $Value.ToUniversalTime().ToString("o") }

        $dateText = [string]$Value
        if ([string]::IsNullOrWhiteSpace($dateText)) { return $null }

        try {
            return ([DateTimeOffset]::Parse($dateText, [System.Globalization.CultureInfo]::InvariantCulture)).UtcDateTime.ToString("o")
        }
        catch { return $dateText.Trim() }
    }

    $numericProperties = @(
        "DraftNo", "DraftInstance", "SleeperStartTime", "Rounds", "Teams", "Round", "PositionInRound", "OverallPick",
        "OriginalOwnerRosterID", "CurrentOwnerRosterID", "CreatedAt", "SleeperPickNo", "PreviousOwnerRosterID", "NewOwnerRosterID"
    )

    if ($PropertyName -in $numericProperties) {
        $numberText = [string]$Value
        if ([string]::IsNullOrWhiteSpace($numberText)) { return $null }

        try { return [Int64]$numberText }
        catch { return $numberText.Trim() }
    }

    $booleanProperties = @("WasTraded", "IsCurrentlyTraded")
    if ($PropertyName -in $booleanProperties) {
        if ($Value -is [bool]) { return [bool]$Value }
        $boolText = ([string]$Value).Trim()
        if ([string]::IsNullOrWhiteSpace($boolText)) { return $null }

        try { return [bool]::Parse($boolText) }
        catch { return $boolText }
    }

    return [string]$Value
}

function Compare-DraftCompareProperty {
    param(
        [AllowNull()]$OldObject,
        [AllowNull()]$NewObject,
        [Parameter(Mandatory = $true)][string]$PropertyName,
        [Parameter(Mandatory = $true)][string]$Context
    )

    $oldValue = ConvertTo-DraftCompareValue `
        -Value (Get-DraftCompareProperty -Object $OldObject -PropertyName $PropertyName -DefaultValue $null) `
        -PropertyName $PropertyName
    $newValue = ConvertTo-DraftCompareValue `
        -Value (Get-DraftCompareProperty -Object $NewObject -PropertyName $PropertyName -DefaultValue $null) `
        -PropertyName $PropertyName

    if ($oldValue -ne $newValue) {
        Write-Host "$Context property '$PropertyName' changed: '$oldValue' -> '$newValue'"
        return $true
    }

    return $false
}

function ConvertTo-DraftCompareMap {
    param(
        [AllowNull()]$Items,
        [Parameter(Mandatory = $true)][string]$KeyProperty,
        [Parameter(Mandatory = $true)][string]$Context
    )

    $map = @{}
    foreach ($item in (ConvertTo-DraftCompareSafeArray -Value $Items)) {
        $key = [string](Get-DraftCompareProperty -Object $item -PropertyName $KeyProperty -DefaultValue $null)
        if ([string]::IsNullOrWhiteSpace($key)) {
            Write-Host "$Context item missing key property '$KeyProperty'."
            continue
        }

        if ($map.ContainsKey($key)) {
            Write-Host "$Context duplicate key '$key'."
            continue
        }

        $map[$key] = $item
    }

    return $map
}

function Compare-DraftSettingsFieldBased {
    param(
        [AllowNull()]$OldSettings,
        [AllowNull()]$NewSettings,
        [Parameter(Mandatory = $true)][string]$Context
    )

    foreach ($propertyName in @("Rounds", "Teams", "Type")) {
        if (Compare-DraftCompareProperty -OldObject $OldSettings -NewObject $NewSettings -PropertyName $propertyName -Context "$Context settings") {
            return $true
        }
    }

    return $false
}

function Compare-DraftTradeHistoryFieldBased {
    param(
        [AllowNull()]$OldHistory,
        [AllowNull()]$NewHistory,
        [Parameter(Mandatory = $true)][string]$Context
    )

    $oldEntries = @(ConvertTo-DraftCompareSafeArray -Value $OldHistory | Sort-Object CreatedAt, TransactionID, Source, PreviousOwnerRosterID, NewOwnerRosterID)
    $newEntries = @(ConvertTo-DraftCompareSafeArray -Value $NewHistory | Sort-Object CreatedAt, TransactionID, Source, PreviousOwnerRosterID, NewOwnerRosterID)

    if ($oldEntries.Count -ne $newEntries.Count) {
        Write-Host "$Context trade history count changed: $($oldEntries.Count) -> $($newEntries.Count)"
        return $true
    }

    $propertiesToCheck = @("TransactionID", "Source", "CreatedAt", "CreatedDate", "DraftSource", "PreviousOwnerRosterID", "NewOwnerRosterID")
    for ($i = 0; $i -lt $oldEntries.Count; $i++) {
        foreach ($propertyName in $propertiesToCheck) {
            if (Compare-DraftCompareProperty -OldObject $oldEntries[$i] -NewObject $newEntries[$i] -PropertyName $propertyName -Context "$Context trade history entry $($i + 1)") {
                return $true
            }
        }
    }

    return $false
}

function Compare-DraftPicksFieldBased {
    param(
        [AllowNull()]$OldPicks,
        [AllowNull()]$NewPicks,
        [Parameter(Mandatory = $true)][string]$DraftKey
    )

    $oldPickArray = @(ConvertTo-DraftCompareSafeArray -Value $OldPicks)
    $newPickArray = @(ConvertTo-DraftCompareSafeArray -Value $NewPicks)

    if ($oldPickArray.Count -ne $newPickArray.Count) {
        Write-Host "Draft '$DraftKey' pick count changed: $($oldPickArray.Count) -> $($newPickArray.Count)"
        return $true
    }

    $oldPickMap = ConvertTo-DraftCompareMap -Items $oldPickArray -KeyProperty "PickKey" -Context "Draft '$DraftKey' pick"
    $newPickMap = ConvertTo-DraftCompareMap -Items $newPickArray -KeyProperty "PickKey" -Context "Draft '$DraftKey' pick"

    if ($oldPickMap.Count -ne $newPickMap.Count) {
        Write-Host "Draft '$DraftKey' keyed pick count changed: $($oldPickMap.Count) -> $($newPickMap.Count)"
        return $true
    }

    $propertiesToCheck = @(
        "PickKey", "LeagueID", "DraftKey", "Season", "DraftType", "DraftInstance", "DraftCode", "Round", "PositionInRound", "OverallPick", "DisplayPick",
        "OriginalOwnerRosterID", "CurrentOwnerRosterID", "WasTraded", "IsCurrentlyTraded", "TradeSource",
        "PlayerID", "PlayerName", "Status", "SleeperPickNo", "SleeperPickedBy"
    )

    foreach ($pickKey in @($oldPickMap.Keys | Sort-Object)) {
        if (-not $newPickMap.ContainsKey($pickKey)) {
            Write-Host "Draft '$DraftKey' missing pick '$pickKey' in new data."
            return $true
        }

        $oldPick = $oldPickMap[$pickKey]
        $newPick = $newPickMap[$pickKey]
        $context = "Draft '$DraftKey' pick '$pickKey'"

        foreach ($propertyName in $propertiesToCheck) {
            if (Compare-DraftCompareProperty -OldObject $oldPick -NewObject $newPick -PropertyName $propertyName -Context $context) {
                return $true
            }
        }

        if (Compare-DraftTradeHistoryFieldBased `
            -OldHistory (Get-DraftCompareProperty -Object $oldPick -PropertyName "TradeHistory" -DefaultValue @()) `
            -NewHistory (Get-DraftCompareProperty -Object $newPick -PropertyName "TradeHistory" -DefaultValue @()) `
            -Context $context) {
            return $true
        }
    }

    foreach ($pickKey in @($newPickMap.Keys | Sort-Object)) {
        if (-not $oldPickMap.ContainsKey($pickKey)) {
            Write-Host "Draft '$DraftKey' added pick '$pickKey'."
            return $true
        }
    }

    return $false
}

function Compare-DraftsFieldBased {
    param([AllowNull()]$OldData, [AllowNull()]$NewData)

    if (-not $OldData) { return $true }

    $oldDrafts = @(ConvertTo-DraftCompareSafeArray -Value $OldData)
    $newDrafts = @(ConvertTo-DraftCompareSafeArray -Value $NewData)

    if ($oldDrafts.Count -ne $newDrafts.Count) {
        Write-Host "Draft count changed: $($oldDrafts.Count) -> $($newDrafts.Count)"
        return $true
    }

    $oldDraftMap = ConvertTo-DraftCompareMap -Items $oldDrafts -KeyProperty "DraftKey" -Context "Draft"
    $newDraftMap = ConvertTo-DraftCompareMap -Items $newDrafts -KeyProperty "DraftKey" -Context "Draft"

    if ($oldDraftMap.Count -ne $newDraftMap.Count) {
        Write-Host "Keyed draft count changed: $($oldDraftMap.Count) -> $($newDraftMap.Count)"
        return $true
    }

    $draftPropertiesToCheck = @(
        "LeagueID", "DraftKey", "DisplayDraftKey", "DisplayAbrDraftKey", "Season", "DraftType", "DraftInstance", "DraftCode", "DisplayDraftType",
        "DraftNo", "DraftSource", "SleeperDraftID", "SleeperStatus", "SleeperStartTime", "DraftStartTimeUtc",
        "Status", "DisplayStatus", "PickSource", "OrderSource", "OrderMode"
    )

    foreach ($draftKey in @($oldDraftMap.Keys | Sort-Object)) {
        if (-not $newDraftMap.ContainsKey($draftKey)) {
            Write-Host "Draft '$draftKey' missing in new data."
            return $true
        }

        $oldDraft = $oldDraftMap[$draftKey]
        $newDraft = $newDraftMap[$draftKey]
        $context = "Draft '$draftKey'"

        foreach ($propertyName in $draftPropertiesToCheck) {
            if (Compare-DraftCompareProperty -OldObject $oldDraft -NewObject $newDraft -PropertyName $propertyName -Context $context) {
                return $true
            }
        }

        if (Compare-DraftSettingsFieldBased `
            -OldSettings (Get-DraftCompareProperty -Object $oldDraft -PropertyName "Settings" -DefaultValue $null) `
            -NewSettings (Get-DraftCompareProperty -Object $newDraft -PropertyName "Settings" -DefaultValue $null) `
            -Context $context) {
            return $true
        }

        if (Compare-DraftPicksFieldBased `
            -OldPicks (Get-DraftCompareProperty -Object $oldDraft -PropertyName "Picks" -DefaultValue @()) `
            -NewPicks (Get-DraftCompareProperty -Object $newDraft -PropertyName "Picks" -DefaultValue @()) `
            -DraftKey $draftKey) {
            return $true
        }
    }

    foreach ($draftKey in @($newDraftMap.Keys | Sort-Object)) {
        if (-not $oldDraftMap.ContainsKey($draftKey)) {
            Write-Host "Draft '$draftKey' added."
            return $true
        }
    }

    return $false
}
