# ===========================================================================
# Draft Order Aware Utils
# ===========================================================================
#
# Builds exact draft picks using the draft order type while generating picks.
# Snake drafts reverse the base owner order in even rounds; linear drafts keep
# the base owner order for every round.

try {
    Import-Module "$PSScriptRoot\DraftPickResultUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\DraftCompareUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\general\FileUtils.psm1" -ErrorAction Stop -Force
}
catch {
    Write-Error "Fehler beim Laden der Module: $_"
    throw $_
}

function Get-DraftTypeSettingFromSleeperDraftOrDefault {
    param([AllowNull()]$sleeperDraft)

    if ($null -eq $sleeperDraft) { return "linear" }

    $sleeperDraftType = Get-DraftObjectProperty -object $sleeperDraft -propertyName "type" -defaultValue $null
    if ([string]::IsNullOrWhiteSpace([string]$sleeperDraftType)) { return "linear" }

    return [string]$sleeperDraftType
}

function Get-DraftRoundOwnerOrder {
    param(
        [Parameter(Mandatory = $true)][array]$baseOwnerOrder,
        [Parameter(Mandatory = $true)][int]$round,
        [AllowNull()][string]$draftTypeSetting = "linear"
    )

    $roundOwnerOrder = @($baseOwnerOrder)
    $type = ([string]$draftTypeSetting).Trim().ToLowerInvariant()

    if ($type -eq "snake" -and $round % 2 -eq 0) {
        [array]::Reverse($roundOwnerOrder)
    }

    return $roundOwnerOrder
}

function New-ProjectedDraftPicksOrderAware {
    param(
        [Parameter(Mandatory = $true)][string]$leagueID,
        [Parameter(Mandatory = $true)][string]$draftKey,
        [Parameter(Mandatory = $true)][string]$season,
        [Parameter(Mandatory = $true)][string]$draftType,
        [Parameter(Mandatory = $true)][int]$draftInstance,
        [Parameter(Mandatory = $true)][string]$draftCode,
        [Parameter(Mandatory = $true)][int]$rounds,
        [Parameter(Mandatory = $true)][array]$teamIDs,
        [Parameter(Mandatory = $true)][ValidateSet("Exact", "RoundOnly")][string]$orderMode,
        [AllowNull()][string]$draftTypeSetting = "linear"
    )

    $picks = @()

    for ($round = 1; $round -le $rounds; $round++) {
        $roundOwnerOrder = if ($orderMode -eq "Exact") {
            Get-DraftRoundOwnerOrder -baseOwnerOrder $teamIDs -round $round -draftTypeSetting $draftTypeSetting
        }
        else {
            @($teamIDs)
        }

        for ($i = 0; $i -lt $roundOwnerOrder.Count; $i++) {
            $originalOwnerRosterID = [int]$roundOwnerOrder[$i]
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
                DraftInstance         = $draftInstance
                DraftCode             = $draftCode
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

function New-DraftOutputOrderAware {
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
    $draftInstance = [int]$definition.DraftInstance
    $draftCode = [string]$definition.DraftCode
    $draftKey = [string]$definition.DraftKey
    $draftTypeConfig = $definition.DraftTypeConfig
    $sleeperDraft = $definition.SleeperDraft
    $isCurrentSeason = ([int]$season -eq $leagueYear)
    $orderMode = if ($isCurrentSeason) { "Exact" } else { "RoundOnly" }
    $orderSource = "UnknownFuture"
    $pickSource = "GeneratedFromUnknownFuture"
    $teamIDs = @()
    $draftTypeSetting = Get-DraftTypeSettingFromSleeperDraftOrDefault -sleeperDraft $sleeperDraft

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
    $picks = New-ProjectedDraftPicksOrderAware `
        -leagueID $leagueID `
        -draftKey $draftKey `
        -season $season `
        -draftType $draftType `
        -draftInstance $draftInstance `
        -draftCode $draftCode `
        -rounds $rounds `
        -teamIDs $teamIDs `
        -orderMode $orderMode `
        -draftTypeSetting $draftTypeSetting
    $picks = Get-AppliedDraftPickTrades -picks $picks -transactions $transactions -draftKey $draftKey

    if ($null -ne $sleeperDraft -and $orderMode -eq "Exact") {
        $sleeperPicks = Get-DraftSleeperPicksSafe -sleeperDraft $sleeperDraft
        if ($sleeperPicks.Count -gt 0) {
            $picks = Get-AppliedDraftPickResults -picks $picks -sleeperDraft $sleeperDraft -sleeperPicks $sleeperPicks
            $pickSource = "GeneratedFromSleeperOrderTradesAndResults"
        }
    }

    $draftSource = if ($null -ne $sleeperDraft) { "Sleeper" } else { "Virtual" }
    $sleeperDraftID = if ($null -ne $sleeperDraft) { [string]$sleeperDraft.draft_id } else { $null }
    $sleeperStatus = if ($null -ne $sleeperDraft) { [string]$sleeperDraft.status } else { $null }
    $sleeperStartTime = $null
    $draftStartTimeUtc = $null
    if ($null -ne $sleeperDraft -and $null -ne $sleeperDraft.start_time -and [string]$sleeperDraft.start_time -ne "") {
        $sleeperStartTime = [int64]$sleeperDraft.start_time
        if ($sleeperStartTime -gt 0) {
            $draftStartTimeUtc = [DateTimeOffset]::FromUnixTimeMilliseconds($sleeperStartTime).UtcDateTime.ToString("o")
        }
    }
    $draftStatus = Get-DraftStatus -sleeperDraft $sleeperDraft

    return [PSCustomObject][ordered]@{
        LeagueID           = $leagueID
        DraftKey           = $draftKey
        DisplayDraftKey    = Get-DisplayDraftKey -season $season -draftType $draftType -draftInstance $draftInstance
        DisplayAbrDraftKey = Get-DisplayAbrDraftKey -season $season -draftType $draftType -draftInstance $draftInstance
        Season             = $season
        DraftType          = $draftType
        DraftInstance      = $draftInstance
        DraftCode          = $draftCode
        DisplayDraftType   = Get-DraftTypeDisplayName -draftType $draftType
        DraftNo            = [int]$definition.DraftNo
        DraftSource        = $draftSource
        SleeperDraftID     = $sleeperDraftID
        SleeperStatus      = $sleeperStatus
        SleeperStartTime   = $sleeperStartTime
        DraftStartTimeUtc  = $draftStartTimeUtc
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

function Get-CurrentAndOpenDraftDefinitionsOrderAware {
    param(
        [Parameter(Mandatory = $true)][array]$draftTypeConfigs,
        [Parameter(Mandatory = $true)][hashtable]$sleeperDraftMap,
        [Parameter(Mandatory = $true)][int]$leagueYear,
        [Parameter(Mandatory = $true)][int]$openDraftCountPerType
    )

    Assert-DraftTypeConfigs -draftTypeConfigs $draftTypeConfigs
    $definitions = @()

    foreach ($draftTypeConfig in ($draftTypeConfigs | Sort-Object DraftNo)) {
        $openDraftCount = 0
        $season = $leagueYear
        $guard = 0

        while ($openDraftCount -lt $openDraftCountPerType) {
            $guard++
            if ($guard -gt 30) { throw "Draft generation guard reached for draft type '$($draftTypeConfig.DraftType)'." }

            $draftType = [string]$draftTypeConfig.DraftType
            $draftInstance = Get-DraftInstanceFromConfig -draftTypeConfig $draftTypeConfig
            $draftCode = New-DraftCode -draftType $draftType -draftInstance $draftInstance
            $draftKey = New-DraftKey -season ([string]$season) -draftType $draftType -draftInstance $draftInstance
            $sleeperDraft = $null
            if ($sleeperDraftMap.ContainsKey($draftKey)) { $sleeperDraft = $sleeperDraftMap[$draftKey] }

            $isCurrentSeason = ($season -eq $leagueYear)
            $isComplete = Test-SleeperDraftComplete -sleeperDraft $sleeperDraft

            if ($isCurrentSeason -or -not $isComplete) {
                $definitions += [PSCustomObject][ordered]@{
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

            if (-not $isComplete) { $openDraftCount++ }
            $season++
        }
    }

    return @($definitions | Sort-Object @{ Expression = { [int]$_.Season }; Ascending = $true }, DraftNo)
}

function Update-DraftsOrderAware {
    param([string]$leagueID = (Get-Config).LeagueID)

    Write-Host "Update current and open drafts..." -ForegroundColor Yellow

    $config = Get-Config
    $draftsConfig = $config.DraftsConfig
    if ($null -eq $draftsConfig) { throw "Metadata Drafts configuration missing." }

    $upcomingDraftCountMode = [string](Get-DraftObjectProperty -object $draftsConfig -propertyName "UpcomingDraftCountMode" -defaultValue "PerDraftType")
    if ($upcomingDraftCountMode -ne "PerDraftType") { throw "Unsupported UpcomingDraftCountMode '$upcomingDraftCountMode'. Only 'PerDraftType' is supported." }

    $openDraftCountPerType = [int]$draftsConfig.UpcomingDraftCount
    if ($openDraftCountPerType -lt 1) { throw "UpcomingDraftCount must be at least 1." }

    $draftTypeConfigs = @(ConvertTo-DraftSafeArray -value $draftsConfig.Types | Sort-Object DraftNo)
    if ($draftTypeConfigs.Count -eq 0) { throw "No draft types configured in Metadata.json." }
    Assert-DraftTypeConfigs -draftTypeConfigs $draftTypeConfigs

    $league = Get-DraftLeagueLocal
    $standings = Get-DraftStandingsLocal
    $transactions = Get-DraftTransactionsLocal
    $sleeperDraftMap = Get-SleeperDraftMap -draftTypeConfigs $draftTypeConfigs -leagueID $leagueID
    $definitions = Get-CurrentAndOpenDraftDefinitionsOrderAware -draftTypeConfigs $draftTypeConfigs -sleeperDraftMap $sleeperDraftMap -leagueYear ([int]$config.LeagueYear) -openDraftCountPerType $openDraftCountPerType
    $drafts = @()

    foreach ($definition in $definitions) {
        $drafts += New-DraftOutputOrderAware -definition $definition -league $league -standings $standings -transactions $transactions
    }

    $drafts = @($drafts | Sort-Object @{ Expression = { [int]$_.Season }; Ascending = $true }, DraftNo)
    $compare = ${function:Compare-DraftsFieldBased}
    Save-JsonFile -Type "Drafts" -Data $drafts -CompareScript $compare -CreateBackup -UpdateTimestamp

    Write-Host "Current and open drafts update finished." -ForegroundColor DarkCyan

    return $drafts
}

function New-DraftHistoryPicksOrderAware {
    param(
        [Parameter(Mandatory = $true)][string]$leagueID,
        [Parameter(Mandatory = $true)][string]$draftKey,
        [Parameter(Mandatory = $true)][string]$season,
        [Parameter(Mandatory = $true)][string]$draftType,
        [Parameter(Mandatory = $true)][int]$draftInstance,
        [Parameter(Mandatory = $true)][string]$draftCode,
        [Parameter(Mandatory = $true)][int]$rounds,
        [Parameter(Mandatory = $true)][array]$teamIDs,
        [AllowNull()][string]$draftTypeSetting = "linear"
    )

    return New-ProjectedDraftPicksOrderAware `
        -leagueID $leagueID `
        -draftKey $draftKey `
        -season $season `
        -draftType $draftType `
        -draftInstance $draftInstance `
        -draftCode $draftCode `
        -rounds $rounds `
        -teamIDs $teamIDs `
        -orderMode "Exact" `
        -draftTypeSetting $draftTypeSetting
}

function New-DraftHistoryOutputOrderAware {
    param(
        [Parameter(Mandatory = $true)][object]$definition,
        [Parameter(Mandatory = $true)][array]$transactions
    )

    $leagueID = [string]$definition.LeagueID
    $season = [string]$definition.Season
    $draftType = [string]$definition.DraftType
    $draftInstance = [int]$definition.DraftInstance
    $draftCode = [string]$definition.DraftCode
    $draftNo = [int]$definition.DraftNo
    $draftKey = [string]$definition.DraftKey
    $typeOccurrence = [int]$definition.TypeOccurrence
    $typeCount = [int]$definition.TypeCount
    $draftTypeConfig = $definition.DraftTypeConfig
    $sleeperDraft = $definition.SleeperDraft
    $teamIDs = Get-DraftHistoryOrderRosterIDsFromSleeperDraft -sleeperDraft $sleeperDraft
    $sleeperPicks = Get-DraftSleeperPicksSafe -sleeperDraft $sleeperDraft
    $draftTypeSetting = Get-DraftTypeSettingFromSleeperDraftOrDefault -sleeperDraft $sleeperDraft

    if ($teamIDs.Count -eq 0) { throw "No Sleeper draft order found for completed draft '$draftKey'." }

    $rounds = Get-DraftHistoryRounds -sleeperDraft $sleeperDraft -sleeperPicks $sleeperPicks -teamCount $teamIDs.Count -fallbackRounds ([int]$draftTypeConfig.Rounds)
    if ($rounds -le 0) { throw "No valid round count found for completed draft '$draftKey'." }

    $picks = New-DraftHistoryPicksOrderAware `
        -leagueID $leagueID `
        -draftKey $draftKey `
        -season $season `
        -draftType $draftType `
        -draftInstance $draftInstance `
        -draftCode $draftCode `
        -rounds $rounds `
        -teamIDs $teamIDs `
        -draftTypeSetting $draftTypeSetting
    $picks = Get-AppliedDraftPickTrades -picks $picks -transactions $transactions -draftKey $draftKey
    $picks = Get-AppliedDraftPickResults -picks $picks -sleeperDraft $sleeperDraft -sleeperPicks $sleeperPicks
    $draftStatus = Get-DraftStatus -sleeperDraft $sleeperDraft

    return [PSCustomObject][ordered]@{
        LeagueID           = $leagueID
        DraftKey           = $draftKey
        DisplayDraftKey    = Get-DraftHistoryDisplayDraftKey -season $season -draftType $draftType -typeOccurrence $typeOccurrence -typeCount $typeCount
        DisplayAbrDraftKey = Get-DraftHistoryDisplayAbrDraftKey -season $season -draftType $draftType -typeOccurrence $typeOccurrence -typeCount $typeCount
        Season             = $season
        DraftType          = $draftType
        DraftInstance      = $draftInstance
        DraftCode          = $draftCode
        DisplayDraftType   = Get-DraftTypeDisplayName -draftType $draftType
        DraftNo            = $draftNo
        DraftSource        = "Sleeper"
        SleeperDraftID     = [string]$sleeperDraft.draft_id
        SleeperStatus      = [string]$sleeperDraft.status
        Status             = $draftStatus
        DisplayStatus      = Get-DraftDisplayStatus -status $draftStatus
        PickSource         = "GeneratedFromSleeperOrderTradesAndResults"
        OrderSource        = "Sleeper"
        OrderMode          = "Exact"
        Settings           = [PSCustomObject][ordered]@{
            Rounds = $rounds
            Teams  = [int]$teamIDs.Count
            Type   = $draftTypeSetting
        }
        Picks              = @($picks)
    }
}

function Update-DraftsHistoricalSeasonsSafeOrderAware {
    param(
        [string]$leagueID = (Get-Config).LeagueID,
        [switch]$ForceHistory
    )

    Write-Host "Update completed draft history..." -ForegroundColor Yellow

    $draftTypeConfigs = Get-DraftHistoryTypeConfigs
    $transactions = Get-DraftHistoryTransactionsAllLocal
    $leagues = Get-LeaguesRecursive -leagueID $leagueID
    $draftsBySeason = @{}

    foreach ($league in $leagues) {
        $season = [string]$league.season
        if ([string]::IsNullOrWhiteSpace($season)) {
            Write-Warning "League '$($league.league_id)' has no season. Skipping completed draft history."
            continue
        }

        $definitions = Get-SleeperCompletedDraftDefinitionsForLeagueSafe -league $league -draftTypeConfigs $draftTypeConfigs
        foreach ($definition in $definitions) {
            $draftSeason = [string]$definition.Season
            if (-not $draftsBySeason.ContainsKey($draftSeason)) { $draftsBySeason[$draftSeason] = @() }
            $draftsBySeason[$draftSeason] += New-DraftHistoryOutputOrderAware -definition $definition -transactions $transactions
        }
    }

    foreach ($season in ($draftsBySeason.Keys | Sort-Object { [int]$_ })) {
        $seasonDrafts = @($draftsBySeason[$season] | Sort-Object DraftNo, DraftKey)
        $seasonDrafts = Add-DraftHistoryTradeHistorySafe -drafts $seasonDrafts -transactions $transactions
        $normalization = ConvertTo-DraftHistoryNumericOwnerIdsSafe -drafts $seasonDrafts
        Save-DraftsHistoricalSeason -season $season -drafts @($normalization.Drafts) -Force:$ForceHistory
    }

    Write-Host "Completed draft history update finished." -ForegroundColor DarkCyan

    return @($draftsBySeason.Values | ForEach-Object { $_ })
}
