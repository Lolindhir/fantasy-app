# ===========================================================================
# 1. Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\..\ConfigUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\invoke\SleeperUtils.psm1" -ErrorAction Stop -Force
}
catch {
    Write-Error "Fehler beim Laden der Module: $_"
    throw $_
}

# ===========================================================================
# 2. Funktionen
# ===========================================================================

function Get-LeagueRaw {
    param (
        [string]$leagueID = (Get-Config).LeagueID
    )

    try {
        $leagueData = Get-SleeperLeague -leagueID $leagueID
        Write-Host "Raw Sleeper League data fetched." -ForegroundColor Yellow

        return $leagueData
    }
    catch {
         throw $_
    }    
}

function Get-LeaguesRecursive {
    param(
        [string]$leagueID = (Get-Config).LeagueID,
        [array]$accumulatedLeagues = @()
    )

    $league = Get-SleeperLeague -leagueID $leagueID

    if ($league.previous_league_id -and $league.previous_league_id -ne "") {
        $accumulatedLeagues = Get-LeaguesRecursive `
            -leagueID $league.previous_league_id `
            -accumulatedLeagues $accumulatedLeagues
    }

    $accumulatedLeagues += $league

    return $accumulatedLeagues
}

function Test-LeagueDeadlineReached {
    param([AllowNull()][string]$Deadline)

    if ([string]::IsNullOrWhiteSpace($Deadline)) { return $true }

    $deadlineDate = ([datetime]::Parse($Deadline)).Date
    return (Get-Date).Date -ge $deadlineDate
}

function Test-LeagueCapDeadlineBufferOpen {
    param(
        [AllowNull()][string]$Deadline,
        [int]$BufferDays = 3
    )

    if ([string]::IsNullOrWhiteSpace($Deadline)) { return $false }

    $deadlineDate = ([datetime]::Parse($Deadline)).Date
    $bufferEndDate = $deadlineDate.AddDays($BufferDays)

    return (Get-Date).Date -le $bufferEndDate
}

function Test-LeagueSeasonWindowStarted {
    param(
        [AllowNull()][array]$Schedule,
        [int]$DaysBeforeFirstGame = 7
    )

    if (-not $Schedule -or @($Schedule).Count -eq 0) { return $false }

    $regularSeasonGames = @($Schedule | Where-Object {
        $_.seasonType -eq "Regular Season" -and
        -not [string]::IsNullOrWhiteSpace([string]$_.gameTime_epoch)
    })

    if ($regularSeasonGames.Count -eq 0) { return $false }

    $firstGame = $regularSeasonGames |
        Sort-Object { [double]$_.gameTime_epoch } |
        Select-Object -First 1

    $firstKickoffUtc = [DateTimeOffset]::FromUnixTimeSeconds([int64][double]$firstGame.gameTime_epoch).UtcDateTime
    $seasonWindowStartUtc = $firstKickoffUtc.AddDays(-1 * $DaysBeforeFirstGame)

    return (Get-Date).ToUniversalTime() -ge $seasonWindowStartUtc
}

function Get-CurrentSeasonDrafts {
    param(
        [Parameter(Mandatory = $true)][array]$Drafts,
        [Parameter(Mandatory = $true)][int]$LeagueYear
    )

    return @($Drafts | Where-Object { [int]$_.Season -eq $LeagueYear })
}

function Test-CurrentSeasonDraftOpen {
    param(
        [Parameter(Mandatory = $true)][array]$Drafts,
        [Parameter(Mandatory = $true)][int]$LeagueYear
    )

    $openDrafts = @(Get-CurrentSeasonDrafts -Drafts $Drafts -LeagueYear $LeagueYear | Where-Object {
        [string]$_.Status -in @("Virtual", "PreDraft", "Drafting")
    })

    return $openDrafts.Count -gt 0
}

function Test-CurrentSeasonDraftsComplete {
    param(
        [Parameter(Mandatory = $true)][array]$Drafts,
        [Parameter(Mandatory = $true)][int]$LeagueYear
    )

    $currentSeasonDrafts = Get-CurrentSeasonDrafts -Drafts $Drafts -LeagueYear $LeagueYear
    if ($currentSeasonDrafts.Count -eq 0) { return $false }

    $incompleteDrafts = @($currentSeasonDrafts | Where-Object { [string]$_.Status -ne "Complete" })
    return $incompleteDrafts.Count -eq 0
}

function Test-CurrentSeasonDraftStarted {
    param(
        [Parameter(Mandatory = $true)][array]$Drafts,
        [Parameter(Mandatory = $true)][int]$LeagueYear
    )

    $startedDrafts = @(Get-CurrentSeasonDrafts -Drafts $Drafts -LeagueYear $LeagueYear | Where-Object {
        [string]$_.Status -in @("Drafting", "Complete")
    })

    return $startedDrafts.Count -gt 0
}

function Test-CurrentSeasonDraftStartTimeSet {
    param(
        [Parameter(Mandatory = $true)][array]$Drafts,
        [Parameter(Mandatory = $true)][int]$LeagueYear
    )

    # TODO: Verify the exact Sleeper draft start-time field before using it as
    # the Draft-Season / Pre Draft transition. Drafts.json does not expose a
    # stable draft start time yet, so this intentionally stays false for now.
    return $false
}

function New-LeagueStatusState {
    param(
        [Parameter(Mandatory = $true)][string]$Status,
        [AllowNull()][string]$Phase = ""
    )

    if ($null -eq $Phase) { $Phase = "" }

    return [PSCustomObject][ordered]@{
        Status = $Status
        Phase  = $Phase
    }
}

function Resolve-LeagueStatusState {
    param(
        [Parameter(Mandatory = $true)][object]$League,
        [Parameter(Mandatory = $true)][array]$Drafts,
        [AllowNull()][array]$Schedule,
        [Parameter(Mandatory = $true)][int]$LeagueYear,
        [AllowNull()][string]$CapDeadline,
        [int]$CapDeadlineBufferDays = 3,
        [bool]$TradesOpen = $true,
        [int]$FinalScoredWeek = 0,
        [int]$PlayoffStartWeek = 0,
        [int]$SeasonStartBufferDays = 7
    )

    $sleeperStatus = [string]$League.status

    if ($sleeperStatus -eq "complete") { return New-LeagueStatusState -Status "Completed" }

    if ($sleeperStatus -eq "playoffs" -or ($PlayoffStartWeek -gt 0 -and $FinalScoredWeek -ge $PlayoffStartWeek)) {
        return New-LeagueStatusState -Status "Playoffs"
    }

    $seasonWindowStarted = Test-LeagueSeasonWindowStarted -Schedule $Schedule -DaysBeforeFirstGame $SeasonStartBufferDays
    $hasOpenCurrentDrafts = Test-CurrentSeasonDraftOpen -Drafts $Drafts -LeagueYear $LeagueYear
    $allCurrentDraftsComplete = Test-CurrentSeasonDraftsComplete -Drafts $Drafts -LeagueYear $LeagueYear
    $currentSeasonDraftStarted = Test-CurrentSeasonDraftStarted -Drafts $Drafts -LeagueYear $LeagueYear
    $currentSeasonDraftStartTimeSet = Test-CurrentSeasonDraftStartTimeSet -Drafts $Drafts -LeagueYear $LeagueYear

    if ($allCurrentDraftsComplete) {
        if (-not $seasonWindowStarted) { return New-LeagueStatusState -Status "Pre-Season" }
        return New-LeagueStatusState -Status "In-Season"
    }

    if ($hasOpenCurrentDrafts -and $currentSeasonDraftStarted) {
        return New-LeagueStatusState -Status "Draft-Season" -Phase "In Draft"
    }

    if ($TradesOpen -and (Test-LeagueCapDeadlineBufferOpen -Deadline $CapDeadline -BufferDays $CapDeadlineBufferDays)) {
        return New-LeagueStatusState -Status "Off-Season" -Phase "Cap Deadline Open"
    }

    if ($hasOpenCurrentDrafts -and -not $TradesOpen) {
        return New-LeagueStatusState -Status "Off-Season" -Phase "Cap Check"
    }

    if ($hasOpenCurrentDrafts -and $TradesOpen -and -not $currentSeasonDraftStartTimeSet) {
        return New-LeagueStatusState -Status "Off-Season" -Phase "Post Cap Check"
    }

    if ($hasOpenCurrentDrafts -and $TradesOpen -and $currentSeasonDraftStartTimeSet) {
        return New-LeagueStatusState -Status "Draft-Season" -Phase "Pre Draft"
    }

    if (-not $seasonWindowStarted) { return New-LeagueStatusState -Status "Pre-Season" }

    return New-LeagueStatusState -Status "In-Season"
}

function Resolve-LeagueStatus {
    param(
        [Parameter(Mandatory = $true)][object]$League,
        [Parameter(Mandatory = $true)][array]$Drafts,
        [AllowNull()][array]$Schedule,
        [Parameter(Mandatory = $true)][int]$LeagueYear,
        [AllowNull()][string]$CapDeadline,
        [int]$FinalScoredWeek = 0,
        [int]$PlayoffStartWeek = 0,
        [int]$SeasonStartBufferDays = 7
    )

    $state = Resolve-LeagueStatusState `
        -League $League `
        -Drafts $Drafts `
        -Schedule $Schedule `
        -LeagueYear $LeagueYear `
        -CapDeadline $CapDeadline `
        -FinalScoredWeek $FinalScoredWeek `
        -PlayoffStartWeek $PlayoffStartWeek `
        -SeasonStartBufferDays $SeasonStartBufferDays

    return $state.Status
}
