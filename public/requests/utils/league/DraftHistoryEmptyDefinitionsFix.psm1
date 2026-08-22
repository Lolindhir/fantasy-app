# ===========================================================================
# Draft History: Empty Definitions Fix
# ===========================================================================
#
# Safe wrappers for historical draft generation. The identity semantics are
# intentionally delegated to the canonical DraftHistory/DraftUtils helpers so
# current and historical drafts cannot drift into different key schemes.

function Set-DraftHistoryTypeOccurrencesSafe {
    param(
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$definitions,
        [Parameter(Mandatory = $true)][array]$draftTypeConfigs
    )

    if ($definitions.Count -eq 0) { return @() }
    return Set-DraftHistoryTypeOccurrences -definitions $definitions -draftTypeConfigs $draftTypeConfigs
}

function Get-SleeperCompletedDraftDefinitionsForLeagueSafe {
    param(
        [Parameter(Mandatory = $true)][object]$league,
        [Parameter(Mandatory = $true)][array]$draftTypeConfigs
    )

    $leagueID = [string]$league.league_id
    $season = [string]$league.season
    $definitions = @()

    try { $sleeperDrafts = ConvertTo-DraftSafeArray -value (Get-SleeperDrafts -leagueID $leagueID) }
    catch {
        Write-Warning "Could not load Sleeper drafts for league '$leagueID' / season '$season'. $_"
        return @()
    }

    if ($sleeperDrafts.Count -eq 0) { return @() }

    $fallbackTypes = @($draftTypeConfigs | Sort-Object DraftNo)
    $seasonDrafts = @($sleeperDrafts | Sort-Object @{ Expression = "created"; Ascending = $true }, @{ Expression = "draft_id"; Ascending = $true })
    $completedIndex = 0

    for ($i = 0; $i -lt $seasonDrafts.Count; $i++) {
        $draft = Get-SleeperDraftDetailOrDefault -sleeperDraft $seasonDrafts[$i]
        if (-not (Test-SleeperDraftComplete -sleeperDraft $draft)) { continue }

        $completedIndex++
        $fallbackDraftTypeConfig = if (($completedIndex - 1) -lt $fallbackTypes.Count) { $fallbackTypes[$completedIndex - 1] } else { $null }
        $draftType = Resolve-DraftHistoryTypeFromSleeperDraft `
            -sleeperDraft $draft `
            -draftTypeConfigs $draftTypeConfigs `
            -fallbackDraftTypeConfig $fallbackDraftTypeConfig
        if ([string]::IsNullOrWhiteSpace($draftType)) { $draftType = "Veteran" }

        $draftSeason = [string](Get-DraftObjectProperty -object $draft -propertyName "season" -defaultValue $season)
        if ([string]::IsNullOrWhiteSpace($draftSeason)) { $draftSeason = $season }

        $rounds = Get-DraftHistoryConfiguredRoundsFromSleeperDraft -sleeperDraft $draft
        if ($null -eq $rounds -or $rounds -le 0) { $rounds = 0 }

        $draftTypeConfig = Get-DraftHistoryConfiguredDraftTypeOrDefault `
            -draftType $draftType `
            -draftTypeConfigs $draftTypeConfigs `
            -defaultDraftNo $completedIndex `
            -defaultRounds ([int]$rounds)

        $definitions += [PSCustomObject][ordered]@{
            LeagueID        = $leagueID
            Season          = $draftSeason
            DraftType       = $draftType
            DraftInstance   = 1
            DraftCode       = $draftType
            DraftNo         = $completedIndex
            DraftKey        = New-DraftKey -season $draftSeason -draftType $draftType
            DraftTypeConfig = $draftTypeConfig
            SleeperDraft    = $draft
            TypeOccurrence  = 1
            TypeCount       = 1
        }
    }

    if ($definitions.Count -eq 0) { return @() }

    $definitions = Set-DraftHistoryTypeOccurrencesSafe `
        -definitions $definitions `
        -draftTypeConfigs $draftTypeConfigs

    return @($definitions | Sort-Object @{ Expression = { [int]$_.Season }; Ascending = $true }, DraftNo, DraftKey)
}

function ConvertTo-DraftHistoryNumericOwnerIdSafe {
    param(
        [AllowNull()]$value,
        [ref]$changed
    )

    if ($null -eq $value) { return $value }
    if ([string]::IsNullOrWhiteSpace([string]$value)) { return $value }

    $numericValue = [int]$value

    if (-not ($value -is [int] -or $value -is [long])) {
        $changed.Value = $true
    }

    return $numericValue
}

function ConvertTo-DraftHistoryNumericOwnerIdsSafe {
    param([Parameter(Mandatory = $true)][array]$drafts)

    $changed = $false

    foreach ($draft in $drafts) {
        foreach ($pick in (ConvertTo-DraftSafeArray -value $draft.Picks)) {
            $pick.OriginalOwnerRosterID = ConvertTo-DraftHistoryNumericOwnerIdSafe -value $pick.OriginalOwnerRosterID -changed ([ref]$changed)
            $pick.CurrentOwnerRosterID = ConvertTo-DraftHistoryNumericOwnerIdSafe -value $pick.CurrentOwnerRosterID -changed ([ref]$changed)

            foreach ($tradeEntry in (ConvertTo-DraftSafeArray -value $pick.TradeHistory)) {
                $tradeEntry.PreviousOwnerRosterID = ConvertTo-DraftHistoryNumericOwnerIdSafe -value $tradeEntry.PreviousOwnerRosterID -changed ([ref]$changed)
                $tradeEntry.NewOwnerRosterID = ConvertTo-DraftHistoryNumericOwnerIdSafe -value $tradeEntry.NewOwnerRosterID -changed ([ref]$changed)
            }
        }
    }

    return [PSCustomObject][ordered]@{
        Drafts  = $drafts
        Changed = $changed
    }
}

function Add-DraftHistoryTradeHistorySafe {
    param(
        [Parameter(Mandatory = $true)][array]$drafts,
        [Parameter(Mandatory = $true)][array]$transactions
    )

    foreach ($draft in $drafts) {
        $pickByKey = @{}
        foreach ($pick in (ConvertTo-DraftSafeArray -value $draft.Picks)) {
            $pickByKey[[string]$pick.PickKey] = $pick
        }

        foreach ($transaction in $transactions) {
            if ([string]$transaction.Status -ne "complete") { continue }

            foreach ($draftPick in (ConvertTo-DraftSafeArray -value $transaction.DraftPicks)) {
                if ([string]$draftPick.DraftKey -ne [string]$draft.DraftKey) { continue }

                $round = Get-DraftObjectProperty -object $draftPick -propertyName "Round" -defaultValue $null
                $originalOwnerRosterID = Get-DraftObjectProperty -object $draftPick -propertyName "OriginalOwnerRosterID" -defaultValue $null
                if ($null -eq $round -or $null -eq $originalOwnerRosterID) { continue }

                $pickKey = New-DraftPickKey `
                    -draftKey ([string]$draft.DraftKey) `
                    -round ([int]$round) `
                    -originalOwnerRosterID ([int]$originalOwnerRosterID)
                if (-not $pickByKey.ContainsKey($pickKey)) { continue }

                $targetPick = $pickByKey[$pickKey]
                $history = @(ConvertTo-DraftSafeArray -value $targetPick.TradeHistory)
                $alreadyExists = $false

                foreach ($entry in $history) {
                    if (
                        [string]$entry.TransactionID -eq [string]$transaction.TransactionID -and
                        [int]$entry.PreviousOwnerRosterID -eq [int]$draftPick.PreviousOwnerRosterID -and
                        [int]$entry.NewOwnerRosterID -eq [int]$draftPick.NewOwnerRosterID
                    ) {
                        $alreadyExists = $true
                        break
                    }
                }

                if (-not $alreadyExists) {
                    $history += [PSCustomObject][ordered]@{
                        TransactionID         = [string]$transaction.TransactionID
                        Source                = [string]$transaction.Source
                        CreatedAt             = [Int64]$transaction.CreatedAt
                        CreatedDate           = [string]$transaction.CreatedDate
                        DraftSource           = [string]$draftPick.DraftSource
                        PreviousOwnerRosterID = [int]$draftPick.PreviousOwnerRosterID
                        NewOwnerRosterID      = [int]$draftPick.NewOwnerRosterID
                    }
                }

                $targetPick.TradeHistory = @($history | Sort-Object CreatedAt, TransactionID)
                if ($targetPick.TradeHistory.Count -gt 0) {
                    $targetPick.WasTraded = $true
                    $targetPick.IsCurrentlyTraded = ([int]$targetPick.CurrentOwnerRosterID -ne [int]$targetPick.OriginalOwnerRosterID)
                    if ([string]::IsNullOrWhiteSpace([string]$targetPick.TradeSource)) {
                        $targetPick.TradeSource = [string]$transaction.Source
                    }
                }
            }
        }
    }

    return $drafts
}

function Update-DraftsHistoricalSeasonsSafe {
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
            $draftsBySeason[$draftSeason] += New-DraftHistoryOutput -definition $definition -transactions $transactions
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
