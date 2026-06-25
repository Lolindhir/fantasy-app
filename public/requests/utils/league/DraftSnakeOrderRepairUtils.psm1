# ===========================================================================
# Draft Snake Order Repair Utils
# ===========================================================================
#
# Repairs generated exact draft pick owner metadata for Sleeper snake drafts.
# Sleeper exposes slot_to_roster_id as the base order and pick.roster_id as the
# final owner of a completed pick. The generated OriginalOwnerRosterID must use
# the reversed base order in even snake rounds before trade flags are derived.

function Get-DraftSnakeRoundOwnerOrder {
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

function Repair-DraftSnakeOriginalOwners {
    param([Parameter(Mandatory = $true)][array]$drafts)

    $changed = $false

    foreach ($draft in $drafts) {
        $settingsType = [string](Get-DraftObjectProperty -object $draft.Settings -propertyName "Type" -defaultValue "linear")
        $orderMode = [string](Get-DraftObjectProperty -object $draft -propertyName "OrderMode" -defaultValue "")
        if ($settingsType.Trim().ToLowerInvariant() -ne "snake" -or $orderMode -ne "Exact") { continue }

        $picks = ConvertTo-DraftSafeArray -value $draft.Picks
        $roundOnePicks = @($picks | Where-Object { [int]$_.Round -eq 1 } | Sort-Object PositionInRound)
        if ($roundOnePicks.Count -eq 0) { continue }

        $baseOwnerOrder = @($roundOnePicks | ForEach-Object { [int]$_.OriginalOwnerRosterID })
        if ($baseOwnerOrder.Count -eq 0) { continue }

        foreach ($roundGroup in ($picks | Group-Object -Property Round)) {
            $round = [int]$roundGroup.Name
            $roundOwnerOrder = Get-DraftSnakeRoundOwnerOrder -baseOwnerOrder $baseOwnerOrder -round $round -draftTypeSetting $settingsType
            $roundPicks = @($roundGroup.Group | Sort-Object PositionInRound)

            for ($i = 0; $i -lt $roundPicks.Count -and $i -lt $roundOwnerOrder.Count; $i++) {
                $pick = $roundPicks[$i]
                $expectedOriginalOwnerRosterID = [int]$roundOwnerOrder[$i]
                $oldOriginalOwnerRosterID = [int]$pick.OriginalOwnerRosterID

                if ($oldOriginalOwnerRosterID -eq $expectedOriginalOwnerRosterID) { continue }

                $pick.OriginalOwnerRosterID = $expectedOriginalOwnerRosterID
                $pick.PickKey = New-DraftPickKey -draftKey ([string]$pick.DraftKey) -round $round -originalOwnerRosterID $expectedOriginalOwnerRosterID

                $tradeHistory = ConvertTo-DraftSafeArray -value $pick.TradeHistory
                if ($tradeHistory.Count -eq 0 -and [int]$pick.CurrentOwnerRosterID -eq $oldOriginalOwnerRosterID) {
                    $pick.CurrentOwnerRosterID = $expectedOriginalOwnerRosterID
                }

                $pick.IsCurrentlyTraded = ([int]$pick.CurrentOwnerRosterID -ne [int]$pick.OriginalOwnerRosterID)
                if ($tradeHistory.Count -eq 0) {
                    $pick.WasTraded = $pick.IsCurrentlyTraded
                    if (-not $pick.IsCurrentlyTraded) { $pick.TradeSource = $null }
                }

                $changed = $true
            }
        }
    }

    return [PSCustomObject][ordered]@{
        Drafts  = $drafts
        Changed = $changed
    }
}

function Update-DraftsWithSnakeOrderRepair {
    param([string]$leagueID = (Get-Config).LeagueID)

    $drafts = Update-Drafts -leagueID $leagueID
    if (-not $drafts) { return $drafts }

    $repair = Repair-DraftSnakeOriginalOwners -drafts @($drafts)
    if ($repair.Changed) {
        Save-Drafts -drafts @($repair.Drafts)
    }

    return @($repair.Drafts)
}

function Update-DraftsHistoricalSeasonsWithSnakeOrderRepair {
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
        $repair = Repair-DraftSnakeOriginalOwners -drafts $seasonDrafts
        $seasonDrafts = @($repair.Drafts)
        $seasonDrafts = Add-DraftHistoryTradeHistorySafe -drafts $seasonDrafts -transactions $transactions
        $normalization = ConvertTo-DraftHistoryNumericOwnerIdsSafe -drafts $seasonDrafts
        Save-DraftsHistoricalSeason -season $season -drafts @($normalization.Drafts) -Force:$ForceHistory
    }

    Write-Host "Completed draft history update finished." -ForegroundColor DarkCyan

    return @($draftsBySeason.Values | ForEach-Object { $_ })
}
