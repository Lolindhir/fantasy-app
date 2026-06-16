# ===========================================================================
# Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\..\ConfigUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\general\FileUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\league\TeamUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\invoke\SleeperUtils.psm1" -ErrorAction Stop -Force
}
catch {
    Write-Error "Fehler beim Laden der Module: $_"
    throw $_
}

# ===========================================================================
# Draft Pick Build Utils
# ===========================================================================

function Get-DraftPickOutput {
    param(
        [Parameter(Mandatory = $true)][object]$pick,
        [Parameter(Mandatory = $true)][string]$draftType,
        [Parameter(Mandatory = $true)][ValidateSet("Sleeper", "Manual")][string]$draftSource,
        [string]$transactionID = $null
    )

    $season = [string]$pick.season
    $round = [int]$pick.round

    return [PSCustomObject][ordered]@{
        DraftType             = $draftType
        DraftSource           = $draftSource
        DraftKey              = "$($season)_$($draftType)"
        Season                = $season
        Round                 = $round
        OriginalOwnerRosterID = [int]$pick.roster_id
        PreviousOwnerRosterID = [int]$pick.previous_owner_id
        NewOwnerRosterID      = [int]$pick.owner_id
    }
}

function Get-DraftPickOutputFromSleeper {
    param([Parameter(Mandatory = $true)][object]$sleeperPick)

    return Get-DraftPickOutput -pick $sleeperPick -draftType "Rookie" -draftSource "Sleeper"
}

function Get-DraftPickOutputFromManual {
    param([Parameter(Mandatory = $true)][object]$manualPick)

    $normalizedPick = [PSCustomObject]@{
        season            = $manualPick.Season
        round             = $manualPick.Round
        roster_id         = Get-OwnerIDByName -ownerName $manualPick.Original
        previous_owner_id = Get-OwnerIDByName -ownerName $manualPick.From
        owner_id          = Get-OwnerIDByName -ownerName $manualPick.To
    }

    return Get-DraftPickOutput -pick $normalizedPick -draftType "Free_Agent" -draftSource "Manual"
}

function ConvertTo-DraftSafeArray {
    param([AllowNull()]$value)

    if ($null -eq $value) { return @() }
    if ($value -is [array]) { return $value }
    return @($value)
}

# ===========================================================================
# Draft Generation: Generic Helpers
# ===========================================================================

function Test-DraftPropertyExists {
    param(
        [AllowNull()]$object,
        [Parameter(Mandatory = $true)][string]$propertyName
    )

    if ($null -eq $object) { return $false }
    return ($object.PSObject.Properties.Name -contains $propertyName)
}

function Get-DraftObjectProperty {
    param(
        [AllowNull()]$object,
        [Parameter(Mandatory = $true)][string]$propertyName,
        [AllowNull()]$defaultValue = $null
    )

    if (Test-DraftPropertyExists -object $object -propertyName $propertyName) {
        return $object.PSObject.Properties[$propertyName].Value
    }

    return $defaultValue
}

function ConvertTo-DraftHashtable {
    param([AllowNull()]$object)

    $hash = @{}
    if ($null -eq $object) { return $hash }

    if ($object -is [System.Collections.IDictionary]) {
        foreach ($key in $object.Keys) { $hash[[string]$key] = $object[$key] }
        return $hash
    }

    foreach ($prop in $object.PSObject.Properties) { $hash[[string]$prop.Name] = $prop.Value }
    return $hash
}

function New-DraftKey {
    param(
        [Parameter(Mandatory = $true)][string]$season,
        [Parameter(Mandatory = $true)][string]$draftType
    )

    return "$($season)_$($draftType)"
}

function New-DraftPickKey {
    param(
        [Parameter(Mandatory = $true)][string]$draftKey,
        [Parameter(Mandatory = $true)][int]$round,
        [Parameter(Mandatory = $true)][int]$originalOwnerRosterID
    )

    return "$($draftKey)_R$($round)_OO$($originalOwnerRosterID)"
}

function Get-DraftTypeDisplayName {
    param([Parameter(Mandatory = $true)][string]$draftType)

    return (($draftType -replace "_", " ").Trim())
}

function Get-DraftTypeAbbreviation {
    param([Parameter(Mandatory = $true)][string]$draftType)

    $parts = @($draftType -split "_" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    if ($parts.Count -eq 0) { return $draftType.ToUpperInvariant() }
    return (($parts | ForEach-Object { $_.Substring(0, 1).ToUpperInvariant() }) -join "")
}

function Get-DisplayDraftKey {
    param(
        [Parameter(Mandatory = $true)][string]$season,
        [Parameter(Mandatory = $true)][string]$draftType
    )

    return "$season $(Get-DraftTypeDisplayName -draftType $draftType)"
}

function Get-DisplayAbrDraftKey {
    param(
        [Parameter(Mandatory = $true)][string]$season,
        [Parameter(Mandatory = $true)][string]$draftType
    )

    return "$season $(Get-DraftTypeAbbreviation -draftType $draftType)"
}

function Format-DraftDisplayPick {
    param(
        [Parameter(Mandatory = $true)][int]$round,
        [AllowNull()][Nullable[int]]$positionInRound
    )

    if ($null -eq $positionInRound) { return "Round $round" }
    return ("{0}.{1:00}" -f $round, $positionInRound)
}

function Get-DraftStatus {
    param([AllowNull()]$sleeperDraft)

    if ($null -eq $sleeperDraft) { return "Virtual" }

    switch ([string]$sleeperDraft.status) {
        "complete"  { return "Complete" }
        "drafting"  { return "Drafting" }
        "pre_draft" { return "PreDraft" }
        default     { return [string]$sleeperDraft.status }
    }
}

function Get-DraftDisplayStatus {
    param(
        [Parameter(Mandatory = $true)][string]$status,
        [AllowNull()][string]$season = $null,
        [int]$leagueYear = 0
    )

    switch ($status) {
        "PreDraft" { return "Upcoming" }
        "Drafting" { return "Live" }
        "Complete" { return "Completed" }
        "Virtual"  {
            $seasonNumber = 0
            if (
                -not [string]::IsNullOrWhiteSpace($season) -and
                [int]::TryParse($season, [ref]$seasonNumber) -and
                $leagueYear -gt 0 -and
                $seasonNumber -eq $leagueYear
            ) {
                return "Upcoming"
            }

            return "Future"
        }
        default     { return $status }
    }
}

function Test-SleeperDraftComplete {
    param([AllowNull()]$sleeperDraft)

    if ($null -eq $sleeperDraft) { return $false }
    return ([string]$sleeperDraft.status -eq "complete")
}

# ===========================================================================
# Draft Generation: Local Data
# ===========================================================================

function Get-DraftJsonFileContent {
    param(
        [Parameter(Mandatory = $true)][string]$filePath,
        [string]$description = "data"
    )

    if (-not (Test-Path $filePath)) {
        Write-Warning "$description file not found at $filePath. Returning empty array."
        return @()
    }

    try {
        $raw = Get-Content $filePath -Raw
        if ([string]::IsNullOrWhiteSpace($raw)) { return @() }
        return $raw | ConvertFrom-Json
    }
    catch {
        Write-Warning "Could not read $description file at $filePath. $_"
        return @()
    }
}

function Get-DraftLeagueLocal {
    $config = Get-Config
    return Get-DraftJsonFileContent -filePath $config.LeagueFile -description "League"
}

function Get-DraftStandingsLocal {
    $config = Get-Config
    return ConvertTo-DraftSafeArray -value (Get-DraftJsonFileContent -filePath $config.StandingsFile -description "Standings")
}

function Get-DraftTransactionsLocal {
    $config = Get-Config
    return ConvertTo-DraftSafeArray -value (Get-DraftJsonFileContent -filePath $config.TransactionsFile -description "Transactions")
}

function Get-DraftTeamIDsFromLeague {
    param([Parameter(Mandatory = $true)][object]$league)

    $teams = ConvertTo-DraftSafeArray -value $league.Teams
    return @($teams | Where-Object { $null -ne $_.TeamID } | Sort-Object TeamID | ForEach-Object { [int]$_.TeamID })
}

function Get-DraftStandingBySeason {
    param(
        [Parameter(Mandatory = $true)][array]$standings,
        [Parameter(Mandatory = $true)][string]$season
    )

    return $standings | Where-Object { [string]$_.Season -eq [string]$season } | Select-Object -First 1
}

# ===========================================================================
# Draft Generation: Sleeper Mapping
# ===========================================================================

function Resolve-DraftTypeFromSleeperDraft {
    param(
        [Parameter(Mandatory = $true)][object]$sleeperDraft,
        [Parameter(Mandatory = $true)][array]$draftTypeConfigs
    )

    $textParts = @()

    foreach ($propertyName in @("type", "name", "status", "season")) {
        if (Test-DraftPropertyExists -object $sleeperDraft -propertyName $propertyName) {
            $textParts += [string]$sleeperDraft.$propertyName
        }
    }

    if ($sleeperDraft.metadata) {
        foreach ($prop in $sleeperDraft.metadata.PSObject.Properties) { $textParts += [string]$prop.Value }
    }

    $text = (($textParts | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }) -join " ").ToLowerInvariant()

    if ($text -match "free[_\s-]?agent|freeagent|waiver|\bfa\b") {
        $match = $draftTypeConfigs | Where-Object { [string]$_.DraftType -eq "Free_Agent" } | Select-Object -First 1
        if ($match) { return [string]$match.DraftType }
    }

    if ($text -match "rookie") {
        $match = $draftTypeConfigs | Where-Object { [string]$_.DraftType -eq "Rookie" } | Select-Object -First 1
        if ($match) { return [string]$match.DraftType }
    }

    return $null
}

function Get-SleeperDraftMap {
    param(
        [Parameter(Mandatory = $true)][array]$draftTypeConfigs,
        [string]$leagueID = (Get-Config).LeagueID
    )

    $map = @{}

    try { $sleeperDrafts = ConvertTo-DraftSafeArray -value (Get-SleeperDrafts -leagueID $leagueID) }
    catch {
        Write-Warning "Could not load Sleeper drafts. Upcoming drafts will be generated as virtual drafts. $_"
        return $map
    }

    if ($sleeperDrafts.Count -eq 0) { return $map }

    $fallbackTypes = @($draftTypeConfigs | Sort-Object DraftNo)
    $draftsBySeason = $sleeperDrafts | Group-Object -Property season

    foreach ($seasonGroup in $draftsBySeason) {
        $seasonDrafts = @($seasonGroup.Group | Sort-Object @{ Expression = "created"; Ascending = $true }, @{ Expression = "draft_id"; Ascending = $true })

        for ($i = 0; $i -lt $seasonDrafts.Count; $i++) {
            $draft = $seasonDrafts[$i]
            $season = [string]$draft.season
            if ([string]::IsNullOrWhiteSpace($season)) { $season = [string](Get-Config).LeagueYear }

            $draftType = Resolve-DraftTypeFromSleeperDraft -sleeperDraft $draft -draftTypeConfigs $draftTypeConfigs
            if ([string]::IsNullOrWhiteSpace($draftType) -and $i -lt $fallbackTypes.Count) { $draftType = [string]$fallbackTypes[$i].DraftType }

            if ([string]::IsNullOrWhiteSpace($draftType)) {
                Write-Warning "Could not resolve draft type for Sleeper draft '$($draft.draft_id)'. Skipping mapping."
                continue
            }

            $draftKey = New-DraftKey -season $season -draftType $draftType
            if (-not $map.ContainsKey($draftKey)) {
                $draftToStore = $draft
                $draftID = Get-DraftObjectProperty -object $draft -propertyName "draft_id" -defaultValue $null

                if (-not [string]::IsNullOrWhiteSpace($draftID)) {
                    try { $draftToStore = Get-SleeperDraft -draftID $draftID }
                    catch { Write-Warning "Could not load Sleeper draft detail for '$draftID'. Falling back to draft list object. $_" }
                }

                $map[$draftKey] = $draftToStore
            }
        }
    }

    return $map
}

# ===========================================================================
# Draft Generation: Order and Picks
# ===========================================================================

function Get-DraftOrderRosterIDs {
    param(
        [Parameter(Mandatory = $true)][object]$draftTypeConfig,
        [Parameter(Mandatory = $true)][string]$season,
        [Parameter(Mandatory = $true)][array]$standings
    )

    $orderSource = [string]$draftTypeConfig.OrderSource
    $sourceSeason = $season

    switch ($orderSource) {
        "PreviousPlayoffs" {
            $sourceSeason = [string](([int]$season) - 1)
            $standing = Get-DraftStandingBySeason -standings $standings -season $sourceSeason
            $ranking = ConvertTo-DraftSafeArray -value $standing.Playoffs
        }
        "AllTime" {
            $standing = Get-DraftStandingBySeason -standings $standings -season "AllTime"
            $ranking = ConvertTo-DraftSafeArray -value $standing.Playoffs
        }
        default { throw "Unsupported draft order source '$orderSource' for draft type '$($draftTypeConfig.DraftType)'." }
    }

    if ($ranking.Count -eq 0) { throw "No ranking data found for order source '$orderSource' and source season '$sourceSeason'." }

    if (Test-DraftPropertyExists -object $draftTypeConfig -propertyName "OrderMap") {
        $orderMap = ConvertTo-DraftHashtable -object $draftTypeConfig.OrderMap
        return @($ranking | Where-Object { $orderMap.ContainsKey([string]$_.Place) } | Sort-Object @{ Expression = { [int]$orderMap[[string]$_.Place] }; Ascending = $true } | ForEach-Object { [int]$_.TeamID })
    }

    $order = [string](Get-DraftObjectProperty -object $draftTypeConfig -propertyName "Order" -defaultValue "Ascending")
    $descending = ($order -eq "Descending")

    return @($ranking | Sort-Object @{ Expression = "Place"; Descending = $descending } | ForEach-Object { [int]$_.TeamID })
}

function Get-DraftOrderRosterIDsFromSleeperDraft {
    param([Parameter(Mandatory = $true)][object]$sleeperDraft)

    $slotToRosterID = Get-DraftObjectProperty -object $sleeperDraft -propertyName "slot_to_roster_id" -defaultValue $null
    if ($null -eq $slotToRosterID) { return @() }

    $slotMap = ConvertTo-DraftHashtable -object $slotToRosterID
    if ($slotMap.Count -eq 0) { return @() }

    return @($slotMap.Keys | Sort-Object { [int]$_ } | ForEach-Object { [int]$slotMap[[string]$_] } | Where-Object { $_ -gt 0 })
}

function New-ProjectedDraftPicks {
    param(
        [Parameter(Mandatory = $true)][string]$leagueID,
        [Parameter(Mandatory = $true)][string]$draftKey,
        [Parameter(Mandatory = $true)][string]$season,
        [Parameter(Mandatory = $true)][string]$draftType,
        [Parameter(Mandatory = $true)][int]$rounds,
        [Parameter(Mandatory = $true)][array]$teamIDs,
        [Parameter(Mandatory = $true)][ValidateSet("Exact", "RoundOnly")][string]$orderMode
    )

    $picks = @()

    for ($round = 1; $round -le $rounds; $round++) {
        for ($i = 0; $i -lt $teamIDs.Count; $i++) {
            $originalOwnerRosterID = [int]$teamIDs[$i]
            $positionInRound = $null
            $overallPick = $null

            if ($orderMode -eq "Exact") {
                $positionInRound = $i + 1
                $overallPick = (($round - 1) * $teamIDs.Count) + $positionInRound
            }

            $picks += [PSCustomObject][ordered]@{
                PickKey               = New-DraftPickKey -draftKey $draftKey -round $round -originalOwnerRosterID $originalOwnerRosterID
                LeagueID              = $leagueID
                DraftKey              = $draftKey
                Season                = $season
                DraftType             = $draftType
                Round                 = $round
                PositionInRound       = $positionInRound
                OverallPick           = $overallPick
                DisplayPick           = Format-DraftDisplayPick -round $round -positionInRound $positionInRound
                OriginalOwnerRosterID = $originalOwnerRosterID
                CurrentOwnerRosterID  = $originalOwnerRosterID
                WasTraded             = $false
                IsCurrentlyTraded     = $false
                TradeSource           = $null
                TradeHistory          = @()
                PlayerID              = $null
                PlayerName            = $null
                Status                = "Open"
                SleeperPickNo         = $null
                SleeperPickedBy       = $null
            }
        }
    }

    return $picks
}

function Get-AppliedDraftPickTrades {
    param(
        [Parameter(Mandatory = $true)][array]$picks,
        [Parameter(Mandatory = $true)][array]$transactions,
        [Parameter(Mandatory = $true)][string]$draftKey
    )

    $pickByKey = @{}
    foreach ($pick in $picks) { $pickByKey[$pick.PickKey] = $pick }

    $movements = @()

    foreach ($transaction in $transactions) {
        if ([string]$transaction.Status -ne "complete") { continue }

        $draftPicks = ConvertTo-DraftSafeArray -value $transaction.DraftPicks
        foreach ($draftPick in $draftPicks) {
            if ([string]$draftPick.DraftKey -ne [string]$draftKey) { continue }

            if (-not (Test-DraftPropertyExists -object $draftPick -propertyName "OriginalOwnerRosterID")) {
                Write-Warning "Draft pick movement in transaction '$($transaction.TransactionID)' has no OriginalOwnerRosterID. Skipping."
                continue
            }

            $movements += [PSCustomObject][ordered]@{
                TransactionID         = [string]$transaction.TransactionID
                Source                = [string]$transaction.Source
                CreatedAt             = [Int64]$transaction.CreatedAt
                CreatedDate           = [string]$transaction.CreatedDate
                DraftSource           = [string]$draftPick.DraftSource
                DraftKey              = [string]$draftPick.DraftKey
                Season                = [string]$draftPick.Season
                Round                 = [int]$draftPick.Round
                OriginalOwnerRosterID = [int]$draftPick.OriginalOwnerRosterID
                PreviousOwnerRosterID = [int]$draftPick.PreviousOwnerRosterID
                NewOwnerRosterID      = [int]$draftPick.NewOwnerRosterID
            }
        }
    }

    $movements = @($movements | Sort-Object CreatedAt, TransactionID)

    foreach ($movement in $movements) {
        $pickKey = New-DraftPickKey -draftKey $movement.DraftKey -round $movement.Round -originalOwnerRosterID $movement.OriginalOwnerRosterID

        if (-not $pickByKey.ContainsKey($pickKey)) {
            Write-Warning "Could not find pick '$pickKey' for transaction '$($movement.TransactionID)'."
            continue
        }

        $targetPick = $pickByKey[$pickKey]
        $targetPick.CurrentOwnerRosterID = [int]$movement.NewOwnerRosterID
        $targetPick.WasTraded = $true
        $targetPick.IsCurrentlyTraded = ([int]$targetPick.CurrentOwnerRosterID -ne [int]$targetPick.OriginalOwnerRosterID)
        $targetPick.TradeSource = [string]$movement.Source
        $targetPick.TradeHistory = @($targetPick.TradeHistory) + [PSCustomObject][ordered]@{
            TransactionID         = $movement.TransactionID
            Source                = $movement.Source
            CreatedAt             = $movement.CreatedAt
            CreatedDate           = $movement.CreatedDate
            DraftSource           = $movement.DraftSource
            PreviousOwnerRosterID = $movement.PreviousOwnerRosterID
            NewOwnerRosterID      = $movement.NewOwnerRosterID
        }
    }

    foreach ($pick in $picks) { $pick.IsCurrentlyTraded = ([int]$pick.CurrentOwnerRosterID -ne [int]$pick.OriginalOwnerRosterID) }

    return $picks
}

# ===========================================================================
# Draft Generation: Draft Objects
# ===========================================================================

function Get-UpcomingDraftDefinitions {
    param(
        [Parameter(Mandatory = $true)][array]$draftTypeConfigs,
        [Parameter(Mandatory = $true)][hashtable]$sleeperDraftMap,
        [Parameter(Mandatory = $true)][int]$leagueYear,
        [Parameter(Mandatory = $true)][int]$upcomingDraftCountPerType
    )

    $definitions = @()

    foreach ($draftTypeConfig in ($draftTypeConfigs | Sort-Object DraftNo)) {
        $typeDefinitions = @()
        $season = $leagueYear
        $guard = 0

        while ($typeDefinitions.Count -lt $upcomingDraftCountPerType) {
            $guard++
            if ($guard -gt 30) { throw "Upcoming draft generation guard reached for draft type '$($draftTypeConfig.DraftType)'." }

            $draftType = [string]$draftTypeConfig.DraftType
            $draftKey = New-DraftKey -season ([string]$season) -draftType $draftType
            $sleeperDraft = $null
            if ($sleeperDraftMap.ContainsKey($draftKey)) { $sleeperDraft = $sleeperDraftMap[$draftKey] }

            if (-not (Test-SleeperDraftComplete -sleeperDraft $sleeperDraft)) {
                $typeDefinitions += [PSCustomObject][ordered]@{
                    Season          = [string]$season
                    DraftType       = $draftType
                    DraftNo         = [int]$draftTypeConfig.DraftNo
                    DraftKey        = $draftKey
                    DraftTypeConfig = $draftTypeConfig
                    SleeperDraft    = $sleeperDraft
                }
            }

            $season++
        }

        $definitions += $typeDefinitions
    }

    return @($definitions | Sort-Object @{ Expression = { [int]$_.Season }; Ascending = $true }, DraftNo)
}

function New-DraftOutput {
    param(
        [Parameter(Mandatory = $true)][object]$definition,
        [Parameter(Mandatory = $true)][object]$league,
        [Parameter(Mandatory = $true)][array]$standings,
        [Parameter(Mandatory = $true)][array]$transactions
    )

    $config = Get-Config
    $leagueID = [string]$config.LeagueID
    $leagueYear = [int]$config.LeagueYear
    $season = [string]$definition.Season
    $draftType = [string]$definition.DraftType
    $draftKey = [string]$definition.DraftKey
    $draftTypeConfig = $definition.DraftTypeConfig
    $sleeperDraft = $definition.SleeperDraft
    $isCurrentSeason = ([int]$season -eq $leagueYear)
    $orderMode = if ($isCurrentSeason) { "Exact" } else { "RoundOnly" }
    $orderSource = "UnknownFuture"
    $pickSource = "GeneratedFromUnknownFuture"
    $teamIDs = @()

    if ($orderMode -eq "Exact") {
        $sleeperOrderRosterIDs = @()
        if ($null -ne $sleeperDraft) { $sleeperOrderRosterIDs = Get-DraftOrderRosterIDsFromSleeperDraft -sleeperDraft $sleeperDraft }

        if ($sleeperOrderRosterIDs.Count -gt 0) {
            $teamIDs = $sleeperOrderRosterIDs
            $orderSource = "Sleeper"
            $pickSource = "GeneratedFromSleeperOrderAndTrades"
        }
        else {
            $teamIDs = Get-DraftOrderRosterIDs -draftTypeConfig $draftTypeConfig -season $season -standings $standings
            $orderSource = [string]$draftTypeConfig.OrderSource
            $pickSource = "GeneratedFromConfiguredOrderAndTrades"
        }
    }
    else {
        $teamIDs = Get-DraftTeamIDsFromLeague -league $league
        $orderSource = "UnknownFuture"
        $pickSource = "GeneratedFromRoundOnlyAndTrades"
    }

    if ($teamIDs.Count -eq 0) { throw "No teams found for draft '$draftKey'." }

    $rounds = [int]$draftTypeConfig.Rounds
    $picks = New-ProjectedDraftPicks -leagueID $leagueID -draftKey $draftKey -season $season -draftType $draftType -rounds $rounds -teamIDs $teamIDs -orderMode $orderMode
    $picks = Get-AppliedDraftPickTrades -picks $picks -transactions $transactions -draftKey $draftKey
    $draftSource = if ($null -ne $sleeperDraft) { "Sleeper" } else { "Virtual" }
    $sleeperDraftID = if ($null -ne $sleeperDraft) { [string]$sleeperDraft.draft_id } else { $null }
    $sleeperStatus = if ($null -ne $sleeperDraft) { [string]$sleeperDraft.status } else { $null }
    $draftStatus = Get-DraftStatus -sleeperDraft $sleeperDraft
    $draftTypeSetting = "linear"

    if ($null -ne $sleeperDraft) {
        $sleeperDraftType = Get-DraftObjectProperty -object $sleeperDraft -propertyName "type" -defaultValue $null
        if (-not [string]::IsNullOrWhiteSpace($sleeperDraftType)) { $draftTypeSetting = [string]$sleeperDraftType }
    }

    return [PSCustomObject][ordered]@{
        LeagueID           = $leagueID
        DraftKey           = $draftKey
        DisplayDraftKey    = Get-DisplayDraftKey -season $season -draftType $draftType
        DisplayAbrDraftKey = Get-DisplayAbrDraftKey -season $season -draftType $draftType
        Season             = $season
        DraftType          = $draftType
        DisplayDraftType   = Get-DraftTypeDisplayName -draftType $draftType
        DraftNo            = [int]$definition.DraftNo
        DraftSource        = $draftSource
        SleeperDraftID     = $sleeperDraftID
        SleeperStatus      = $sleeperStatus
        Status             = $draftStatus
        DisplayStatus      = Get-DraftDisplayStatus -status $draftStatus -season $season -leagueYear $leagueYear
        PickSource         = $pickSource
        OrderSource        = $orderSource
        OrderMode          = $orderMode
        Settings           = [PSCustomObject][ordered]@{
            Rounds = $rounds
            Teams  = [int]$teamIDs.Count
            Type   = $draftTypeSetting
        }
        Picks              = @($picks)
    }
}

# ===========================================================================
# Draft Generation: Save and Compare
# ===========================================================================

function ConvertTo-DraftComparableJson {
    param([AllowNull()]$value)

    if ($null -eq $value) { return $null }
    return ($value | ConvertTo-Json -Depth 50 -Compress)
}

function Compare-Drafts {
    param([AllowNull()]$oldData, [AllowNull()]$newData)

    $oldJson = ConvertTo-DraftComparableJson -value $oldData
    $newJson = ConvertTo-DraftComparableJson -value $newData
    return ($oldJson -ne $newJson)
}

function Save-Drafts {
    param([Parameter(Mandatory = $true)][array]$drafts)

    $compare = ${function:Compare-Drafts}
    Save-JsonFile -Type "Drafts" -Data $drafts -CompareScript $compare -CreateBackup -UpdateTimestamp
}

# ===========================================================================
# Draft Generation: Public Update Function
# ===========================================================================

function Update-Drafts {
    param([string]$leagueID = (Get-Config).LeagueID)

    Write-Host "Update upcoming drafts..." -ForegroundColor Yellow

    $config = Get-Config
    $draftsConfig = $config.DraftsConfig
    if ($null -eq $draftsConfig) { throw "Metadata Drafts configuration missing." }

    $upcomingDraftCountMode = [string](Get-DraftObjectProperty -object $draftsConfig -propertyName "UpcomingDraftCountMode" -defaultValue "PerDraftType")
    if ($upcomingDraftCountMode -ne "PerDraftType") { throw "Unsupported UpcomingDraftCountMode '$upcomingDraftCountMode'. Only 'PerDraftType' is supported." }

    $upcomingDraftCountPerType = [int]$draftsConfig.UpcomingDraftCount
    if ($upcomingDraftCountPerType -lt 1) { throw "UpcomingDraftCount must be at least 1." }

    $draftTypeConfigs = @(ConvertTo-DraftSafeArray -value $draftsConfig.Types | Sort-Object DraftNo)
    if ($draftTypeConfigs.Count -eq 0) { throw "No draft types configured in Metadata.json." }

    $league = Get-DraftLeagueLocal
    $standings = Get-DraftStandingsLocal
    $transactions = Get-DraftTransactionsLocal
    $sleeperDraftMap = Get-SleeperDraftMap -draftTypeConfigs $draftTypeConfigs -leagueID $leagueID
    $definitions = Get-UpcomingDraftDefinitions -draftTypeConfigs $draftTypeConfigs -sleeperDraftMap $sleeperDraftMap -leagueYear ([int]$config.LeagueYear) -upcomingDraftCountPerType $upcomingDraftCountPerType
    $drafts = @()

    foreach ($definition in $definitions) {
        $drafts += New-DraftOutput -definition $definition -league $league -standings $standings -transactions $transactions
    }

    $drafts = @($drafts | Sort-Object @{ Expression = { [int]$_.Season }; Ascending = $true }, DraftNo)
    Save-Drafts -drafts $drafts

    Write-Host "Upcoming drafts update finished." -ForegroundColor DarkCyan

    return $drafts
}
