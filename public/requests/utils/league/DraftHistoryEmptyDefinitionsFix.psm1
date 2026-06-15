# ===========================================================================
# Draft History: Empty Definitions Fix
# ===========================================================================
#
# This file intentionally overrides two DraftHistoryUtils functions after that
# module is imported. It keeps completed draft history updates quiet for seasons
# that have no completed drafts yet.

function Set-DraftHistoryTypeOccurrences {
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

function Get-SleeperCompletedDraftDefinitionsForLeague {
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

    $definitions = Set-DraftHistoryTypeOccurrences -definitions $definitions

    return @($definitions | Sort-Object @{ Expression = { [int]$_.Season }; Ascending = $true }, DraftNo, DraftKey)
}
