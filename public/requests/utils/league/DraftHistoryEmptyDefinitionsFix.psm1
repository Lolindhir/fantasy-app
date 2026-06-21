# ===========================================================================
# Draft History: Empty Definitions Fix
# ===========================================================================
#
# This module provides safe wrappers for completed draft history generation.
# It handles seasons that have Sleeper drafts, but no completed drafts yet.

function Set-DraftHistoryTypeOccurrencesSafe {
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [array]$definitions
    )

    if ($definitions.Count -eq 0) {
        return @()
    }

    foreach ($group in ($definitions | Group-Object -Property Season, DraftType)) {
        $groupItems = @($group.Group | Sort-Object DraftNo, DraftKey)
        $typeCount = $groupItems.Count

        for ($i = 0; $i -lt $groupItems.Count; $i++) {
            $groupItems[$i] | Add-Member -NotePropertyName TypeOccurrence -NotePropertyValue ($i + 1) -Force
            $groupItems[$i] | Add-Member -NotePropertyName TypeCount -NotePropertyValue $typeCount -Force
        }
    }

    return $definitions
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
        $draftType = Resolve-DraftHistoryTypeFromSleeperDraft -sleeperDraft $draft -draftTypeConfigs $draftTypeConfigs -fallbackDraftTypeConfig $fallbackDraftTypeConfig
        if ([string]::IsNullOrWhiteSpace($draftType)) { $draftType = "Veteran" }

        $draftSeason = [string](Get-DraftObjectProperty -object $draft -propertyName "season" -defaultValue $season)
        if ([string]::IsNullOrWhiteSpace($draftSeason)) { $draftSeason = $season }

        $rounds = Get-DraftHistoryConfiguredRoundsFromSleeperDraft -sleeperDraft $draft
        if ($null -eq $rounds -or $rounds -le 0) { $rounds = 0 }

        $draftTypeConfig = Get-DraftHistoryConfiguredDraftTypeOrDefault -draftType $draftType -draftTypeConfigs $draftTypeConfigs -defaultDraftNo $completedIndex -defaultRounds ([int]$rounds)
        $draftKey = New-DraftHistoryDraftKey -season $draftSeason -draftNo $completedIndex -draftType $draftType

        $definitions += [PSCustomObject][ordered]@{
            LeagueID        = $leagueID
            Season          = $draftSeason
            DraftType       = $draftType
            DraftNo         = $completedIndex
            DraftKey        = $draftKey
            DraftTypeConfig = $draftTypeConfig
            SleeperDraft    = $draft
            TypeOccurrence  = 1
            TypeCount       = 1
        }
    }

    if ($definitions.Count -eq 0) {
        return @()
    }

    $definitions = Set-DraftHistoryTypeOccurrencesSafe -definitions $definitions

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

function Normalize-DraftHistoryOwnerIdsSafe {
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
        $normalization = Normalize-DraftHistoryOwnerIdsSafe -drafts $seasonDrafts
        Save-DraftsHistoricalSeason -season $season -drafts @($normalization.Drafts) -Force:($ForceHistory -or $normalization.Changed)
    }

    Write-Host "Completed draft history update finished." -ForegroundColor DarkCyan

    return @($draftsBySeason.Values | ForEach-Object { $_ })
}
