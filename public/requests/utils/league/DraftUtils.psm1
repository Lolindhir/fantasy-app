# ===========================================================================
# Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\..\ConfigUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\general\FileUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\general\ProviderJoinUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\league\TeamUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\invoke\SleeperUtils.psm1" -ErrorAction Stop -Force
}
catch {
    Write-Error "Fehler beim Laden der Module: $_"
    throw $_
}

# ===========================================================================
# Generic helpers
# ===========================================================================

function ConvertTo-DraftSafeArray {
    param([AllowNull()]$value)

    if ($null -eq $value) { return @() }
    if ($value -is [array]) { return $value }
    return @($value)
}

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

# ===========================================================================
# Draft identity
# ===========================================================================

function Get-DraftInstanceFromConfig {
    param([Parameter(Mandatory = $true)][object]$draftTypeConfig)

    $draftInstance = Get-DraftObjectProperty -object $draftTypeConfig -propertyName "DraftInstance" -defaultValue 1
    $draftInstance = [int]$draftInstance
    if ($draftInstance -lt 1) { throw "DraftInstance must be at least 1 for draft type '$($draftTypeConfig.DraftType)'." }
    return $draftInstance
}

function New-DraftCode {
    param(
        [Parameter(Mandatory = $true)][string]$draftType,
        [int]$draftInstance = 1
    )

    if ($draftInstance -lt 1) { throw "DraftInstance must be at least 1 for draft type '$draftType'." }
    if ($draftInstance -eq 1) { return $draftType }
    return "$($draftType)_$draftInstance"
}

function New-DraftKey {
    param(
        [Parameter(Mandatory = $true)][string]$season,
        [Parameter(Mandatory = $true)][string]$draftType,
        [int]$draftInstance = 1
    )

    $draftCode = New-DraftCode -draftType $draftType -draftInstance $draftInstance
    return "$($season)_$draftCode"
}

function Get-DraftIdentityFromKey {
    param(
        [Parameter(Mandatory = $true)][string]$draftKey,
        [AllowNull()][array]$draftTypeConfigs = $null
    )

    if ([string]::IsNullOrWhiteSpace($draftKey)) { throw "DraftKey must not be empty." }
    $separatorIndex = $draftKey.IndexOf('_')
    if ($separatorIndex -le 0) { throw "DraftKey '$draftKey' does not contain a season prefix." }

    $season = $draftKey.Substring(0, $separatorIndex)
    if ($null -eq $draftTypeConfigs) {
        $config = Get-Config
        $draftTypeConfigs = ConvertTo-DraftSafeArray -value $config.DraftsConfig.Types
    }

    $matches = @()
    foreach ($draftTypeConfig in $draftTypeConfigs) {
        $draftType = [string]$draftTypeConfig.DraftType
        $draftInstance = Get-DraftInstanceFromConfig -draftTypeConfig $draftTypeConfig
        $expectedKey = New-DraftKey -season $season -draftType $draftType -draftInstance $draftInstance
        if ([string]$expectedKey -eq [string]$draftKey) {
            $matches += [PSCustomObject][ordered]@{
                Season        = $season
                DraftType     = $draftType
                DraftInstance = $draftInstance
                DraftCode     = New-DraftCode -draftType $draftType -draftInstance $draftInstance
                DraftKey      = $expectedKey
            }
        }
    }

    if ($matches.Count -ne 1) {
        throw "DraftKey '$draftKey' could not be resolved to exactly one configured draft instance."
    }

    return $matches[0]
}

function Get-ConfiguredSleeperDraftID {
    param(
        [Parameter(Mandatory = $true)][object]$draftTypeConfig,
        [Parameter(Mandatory = $true)][string]$season
    )

    $bindings = Get-DraftObjectProperty -object $draftTypeConfig -propertyName "SleeperDraftIDs" -defaultValue $null
    if ($null -eq $bindings) { return $null }

    $binding = Get-DraftObjectProperty -object $bindings -propertyName $season -defaultValue $null
    if ($null -eq $binding -or [string]::IsNullOrWhiteSpace([string]$binding)) { return $null }
    return [string]$binding
}

function Assert-DraftTypeConfigs {
    param([Parameter(Mandatory = $true)][array]$draftTypeConfigs)

    $identityKeys = @{}
    $draftNos = @{}
    $sleeperBindings = @{}

    foreach ($draftTypeConfig in $draftTypeConfigs) {
        $draftType = [string]$draftTypeConfig.DraftType
        if ([string]::IsNullOrWhiteSpace($draftType)) { throw "DraftType must not be empty." }

        $draftInstance = Get-DraftInstanceFromConfig -draftTypeConfig $draftTypeConfig
        $identityKey = "$draftType|$draftInstance"
        if ($identityKeys.ContainsKey($identityKey)) {
            throw "Duplicate draft identity configured: DraftType '$draftType', DraftInstance '$draftInstance'."
        }
        $identityKeys[$identityKey] = $true

        $draftNo = [int]$draftTypeConfig.DraftNo
        if ($draftNo -lt 1) { throw "DraftNo must be at least 1 for draft '$identityKey'." }
        if ($draftNos.ContainsKey([string]$draftNo)) { throw "Duplicate DraftNo '$draftNo' in Metadata.json." }
        $draftNos[[string]$draftNo] = $true

        $bindings = Get-DraftObjectProperty -object $draftTypeConfig -propertyName "SleeperDraftIDs" -defaultValue $null
        if ($null -ne $bindings) {
            foreach ($property in $bindings.PSObject.Properties) {
                $draftID = [string]$property.Value
                if ([string]::IsNullOrWhiteSpace($draftID)) { continue }
                if ($sleeperBindings.ContainsKey($draftID)) {
                    throw "Sleeper draft '$draftID' is bound to multiple configured draft instances."
                }
                $sleeperBindings[$draftID] = $identityKey
            }
        }
    }
}

# ===========================================================================
# Draft Pick Build Utils
# ===========================================================================

function Get-DraftPickOutput {
    param(
        [Parameter(Mandatory = $true)][object]$pick,
        [Parameter(Mandatory = $true)][ValidateSet("Sleeper", "Manual")][string]$draftSource,
        [AllowNull()]$draftIdentity = $null,
        [string]$transactionID = $null
    )

    $season = [string]$pick.season
    $round = [int]$pick.round

    return [PSCustomObject][ordered]@{
        DraftType             = if ($null -ne $draftIdentity) { [string]$draftIdentity.DraftType } else { $null }
        DraftInstance         = if ($null -ne $draftIdentity) { [int]$draftIdentity.DraftInstance } else { $null }
        DraftCode             = if ($null -ne $draftIdentity) { [string]$draftIdentity.DraftCode } else { $null }
        DraftSource           = $draftSource
        DraftKey              = if ($null -ne $draftIdentity) { [string]$draftIdentity.DraftKey } else { $null }
        Season                = $season
        Round                 = $round
        OriginalOwnerRosterID = [int]$pick.roster_id
        PreviousOwnerRosterID = [int]$pick.previous_owner_id
        NewOwnerRosterID      = [int]$pick.owner_id
    }
}

function Get-DraftPickOutputFromSleeper {
    param([Parameter(Mandatory = $true)][object]$sleeperPick)

    # A Sleeper league transaction identifies the movement, but not reliably the
    # concrete draft instance. Resolution happens against the mapped draft contexts.
    return Get-DraftPickOutput -pick $sleeperPick -draftSource "Sleeper"
}

function Get-DraftPickOutputFromManual {
    param([Parameter(Mandatory = $true)][object]$manualPick)

    $draftKey = [string](Get-DraftObjectProperty -object $manualPick -propertyName "DraftKey" -defaultValue "")
    if ([string]::IsNullOrWhiteSpace($draftKey)) {
        throw "Manual transaction picks must define an explicit DraftKey."
    }

    $draftIdentity = Get-DraftIdentityFromKey -draftKey $draftKey
    $normalizedPick = [PSCustomObject]@{
        season            = [string]$draftIdentity.Season
        round             = $manualPick.Round
        roster_id         = Get-OwnerIDByName -ownerName $manualPick.Original
        previous_owner_id = Get-OwnerIDByName -ownerName $manualPick.From
        owner_id          = Get-OwnerIDByName -ownerName $manualPick.To
    }

    return Get-DraftPickOutput -pick $normalizedPick -draftSource "Manual" -draftIdentity $draftIdentity
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

function Get-DraftInstanceDisplaySuffix {
    param([int]$draftInstance = 1)
    if ($draftInstance -le 1) { return "" }
    return " #$draftInstance"
}

function Get-DisplayDraftKey {
    param(
        [Parameter(Mandatory = $true)][string]$season,
        [Parameter(Mandatory = $true)][string]$draftType,
        [int]$draftInstance = 1
    )

    return "$season $(Get-DraftTypeDisplayName -draftType $draftType)$(Get-DraftInstanceDisplaySuffix -draftInstance $draftInstance)"
}

function Get-DisplayAbrDraftKey {
    param(
        [Parameter(Mandatory = $true)][string]$season,
        [Parameter(Mandatory = $true)][string]$draftType,
        [int]$draftInstance = 1
    )

    return "$season $(Get-DraftTypeAbbreviation -draftType $draftType)$(Get-DraftInstanceDisplaySuffix -draftInstance $draftInstance)"
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

    $matches = @($standings | Where-Object { [string]$_.Season -eq [string]$season })
    if ($matches.Count -gt 1) {
        throw "Duplicate standing identity for season '$season'. Expected at most one standing record, found $($matches.Count)."
    }

    if ($matches.Count -eq 0) { return $null }
    return $matches[0]
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

function New-SleeperDraftSourceLookup {
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [array]$SleeperDrafts
    )

    return New-UniqueObjectLookup `
        -Items $SleeperDrafts `
        -KeyProperty "draft_id" `
        -SourceLabel "Sleeper league drafts" `
        -KeyLabel "draft_id" `
        -DescriptionProperties @("draft_id", "season", "type", "status", "created")
}

function Get-ConfiguredSleeperDraftMatch {
    param(
        [Parameter(Mandatory = $true)][array]$UnboundDrafts,
        [Parameter(Mandatory = $true)][string]$ConfiguredDraftID,
        [Parameter(Mandatory = $true)][string]$Season
    )

    $matches = @($UnboundDrafts | Where-Object { [string]$_.draft_id -eq [string]$ConfiguredDraftID })
    if ($matches.Count -ne 1) {
        throw "Configured Sleeper draft '$ConfiguredDraftID' for season '$Season' was not found exactly once in the provider response; explicit bindings are authoritative and will not fall back to another draft."
    }

    return $matches[0]
}

function Get-SleeperDraftMap {
    param(
        [Parameter(Mandatory = $true)][array]$draftTypeConfigs,
        [string]$leagueID = (Get-Config).LeagueID
    )

    Assert-DraftTypeConfigs -draftTypeConfigs $draftTypeConfigs
    $map = @{}

    try { $sleeperDrafts = ConvertTo-DraftSafeArray -value (Get-SleeperDrafts -leagueID $leagueID) }
    catch {
        Write-Warning "Could not load Sleeper drafts. Upcoming drafts will be generated as virtual drafts. $_"
        return $map
    }

    if ($sleeperDrafts.Count -eq 0) { return $map }

    New-SleeperDraftSourceLookup -SleeperDrafts $sleeperDrafts | Out-Null
    $draftsBySeason = $sleeperDrafts | Group-Object -Property season

    foreach ($seasonGroup in $draftsBySeason) {
        $season = [string]$seasonGroup.Name
        if ([string]::IsNullOrWhiteSpace($season)) { $season = [string](Get-Config).LeagueYear }

        $seasonDrafts = @($seasonGroup.Group | Sort-Object @{ Expression = "created"; Ascending = $true }, @{ Expression = "draft_id"; Ascending = $true })
        $unboundConfigs = @($draftTypeConfigs | Sort-Object DraftNo)
        $unboundDrafts = @($seasonDrafts)

        # Explicit bindings are authoritative and keep already-known Sleeper IDs stable.
        foreach ($draftTypeConfig in @($draftTypeConfigs | Sort-Object DraftNo)) {
            $configuredDraftID = Get-ConfiguredSleeperDraftID -draftTypeConfig $draftTypeConfig -season $season
            if ([string]::IsNullOrWhiteSpace($configuredDraftID)) { continue }

            $draftToStore = Get-ConfiguredSleeperDraftMatch `
                -UnboundDrafts $unboundDrafts `
                -ConfiguredDraftID $configuredDraftID `
                -Season $season

            $draftInstance = Get-DraftInstanceFromConfig -draftTypeConfig $draftTypeConfig
            $draftKey = New-DraftKey -season $season -draftType ([string]$draftTypeConfig.DraftType) -draftInstance $draftInstance
            try { $draftToStore = Get-SleeperDraft -draftID $configuredDraftID }
            catch { Write-Warning "Could not load Sleeper draft detail for '$configuredDraftID'. Falling back to draft list object. $_" }

            $map[$draftKey] = $draftToStore
            $unboundDrafts = @($unboundDrafts | Where-Object { [string]$_.draft_id -ne $configuredDraftID })
            $unboundConfigs = @($unboundConfigs | Where-Object { $_ -ne $draftTypeConfig })
        }

        # Remaining drafts are bound deterministically by classified type and instance order.
        foreach ($draft in @($unboundDrafts)) {
            $draftID = [string](Get-DraftObjectProperty -object $draft -propertyName "draft_id" -defaultValue "")
            $draftType = Resolve-DraftTypeFromSleeperDraft -sleeperDraft $draft -draftTypeConfigs $unboundConfigs
            $candidateConfigs = @()

            if (-not [string]::IsNullOrWhiteSpace($draftType)) {
                $candidateConfigs = @(
                    $unboundConfigs |
                        Where-Object { [string]$_.DraftType -eq $draftType } |
                        Sort-Object @{ Expression = { Get-DraftInstanceFromConfig -draftTypeConfig $_ }; Ascending = $true }, DraftNo
                )
            }

            if ($candidateConfigs.Count -eq 0) {
                $candidateConfigs = @($unboundConfigs | Sort-Object DraftNo)
            }

            if ($candidateConfigs.Count -eq 0) {
                Write-Warning "No configured draft instance remains for Sleeper draft '$draftID' in season '$season'."
                continue
            }

            $draftTypeConfig = $candidateConfigs[0]
            $draftInstance = Get-DraftInstanceFromConfig -draftTypeConfig $draftTypeConfig
            $draftKey = New-DraftKey -season $season -draftType ([string]$draftTypeConfig.DraftType) -draftInstance $draftInstance
            $draftToStore = $draft

            if (-not [string]::IsNullOrWhiteSpace($draftID)) {
                try { $draftToStore = Get-SleeperDraft -draftID $draftID }
                catch { Write-Warning "Could not load Sleeper draft detail for '$draftID'. Falling back to draft list object. $_" }
            }

            $map[$draftKey] = $draftToStore
            $unboundConfigs = @($unboundConfigs | Where-Object { $_ -ne $draftTypeConfig })
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

function Get-AppliedDraftPickTrades {
    param(
        [Parameter(Mandatory = $true)][array]$picks,
        [Parameter(Mandatory = $true)][array]$transactions,
        [Parameter(Mandatory = $true)][string]$draftKey
    )

    $pickByKey = New-UniqueObjectLookup `
        -Items $picks `
        -KeyProperty "PickKey" `
        -SourceLabel "generated picks for draft '$draftKey'" `
        -KeyLabel "PickKey" `
        -DescriptionProperties @("PickKey", "Season", "Round", "OriginalOwnerRosterID", "CurrentOwnerRosterID")

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

    Assert-DraftTypeConfigs -draftTypeConfigs $draftTypeConfigs
    $definitions = @()

    foreach ($draftTypeConfig in ($draftTypeConfigs | Sort-Object DraftNo)) {
        $typeDefinitions = @()
        $season = $leagueYear
        $guard = 0

        while ($typeDefinitions.Count -lt $upcomingDraftCountPerType) {
            $guard++
            if ($guard -gt 30) { throw "Upcoming draft generation guard reached for draft type '$($draftTypeConfig.DraftType)'." }

            $draftType = [string]$draftTypeConfig.DraftType
            $draftInstance = Get-DraftInstanceFromConfig -draftTypeConfig $draftTypeConfig
            $draftCode = New-DraftCode -draftType $draftType -draftInstance $draftInstance
            $draftKey = New-DraftKey -season ([string]$season) -draftType $draftType -draftInstance $draftInstance
            $sleeperDraft = $null
            if ($sleeperDraftMap.ContainsKey($draftKey)) { $sleeperDraft = $sleeperDraftMap[$draftKey] }

            if (-not (Test-SleeperDraftComplete -sleeperDraft $sleeperDraft)) {
                $typeDefinitions += [PSCustomObject][ordered]@{
                    Season          = [string]$season
                    DraftType       = $draftType
                    DraftInstance   = $draftInstance
                    DraftCode       = $draftCode
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
