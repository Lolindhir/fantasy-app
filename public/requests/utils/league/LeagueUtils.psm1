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

function Test-CurrentSeasonDraftOpen {
    param(
        [Parameter(Mandatory = $true)][array]$Drafts,
        [Parameter(Mandatory = $true)][int]$LeagueYear
    )

    $openDrafts = @($Drafts | Where-Object {
        [int]$_.Season -eq $LeagueYear -and
        [string]$_.Status -in @("Virtual", "PreDraft", "Drafting")
    })

    return $openDrafts.Count -gt 0
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

    $sleeperStatus = [string]$League.status

    if ($sleeperStatus -eq "complete") { return "Completed" }

    if ($sleeperStatus -eq "playoffs" -or ($PlayoffStartWeek -gt 0 -and $FinalScoredWeek -ge $PlayoffStartWeek)) {
        return "Playoffs"
    }

    if (-not (Test-LeagueDeadlineReached -Deadline $CapDeadline)) { return "Off-Season" }
    if (Test-CurrentSeasonDraftOpen -Drafts $Drafts -LeagueYear $LeagueYear) { return "Draft-Season" }
    if (-not (Test-LeagueSeasonWindowStarted -Schedule $Schedule -DaysBeforeFirstGame $SeasonStartBufferDays)) { return "Pre-Season" }

    return "In-Season"
}
