# ===========================================================================
# 1. Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\..\ConfigUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\invoke\SleeperUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\StandingUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\FantasyTeamOrderUtils.psm1" -ErrorAction Stop -Force
}
catch {
    Write-Error "Fehler beim Laden der Module: $_"
    throw $_
}

# ===========================================================================
# 2. Functions
# ===========================================================================

function Resolve-LeagueTradeDeadlineWeek {
    param([AllowNull()]$TradeDeadline)

    if ($null -eq $TradeDeadline -or [string]::IsNullOrWhiteSpace([string]$TradeDeadline)) {
        return $null
    }

    $deadlineWeek = 0
    if (-not [int]::TryParse([string]$TradeDeadline, [ref]$deadlineWeek)) {
        return $null
    }

    # Sleeper publishes 99 when the league trade deadline is disabled. Keep the
    # raw provider value in League.Settings, but expose no app-facing deadline.
    if ($deadlineWeek -le 0 -or $deadlineWeek -eq 99) {
        return $null
    }

    return $deadlineWeek
}

function Get-LeagueSeasonKickoffUtc {
    param([AllowNull()][array]$Schedule)

    if (-not $Schedule -or @($Schedule).Count -eq 0) {
        return $null
    }

    $regularSeasonGames = @($Schedule | Where-Object {
        $_.seasonType -eq "Regular Season" -and
        -not [string]::IsNullOrWhiteSpace([string]$_.gameTime_epoch)
    })

    if ($regularSeasonGames.Count -eq 0) {
        return $null
    }

    $firstGame = $regularSeasonGames |
        Sort-Object { [double]$_.gameTime_epoch } |
        Select-Object -First 1

    try {
        return [DateTimeOffset]::FromUnixTimeSeconds([int64][double]$firstGame.gameTime_epoch).UtcDateTime
    }
    catch {
        Write-Warning "Could not parse first regular-season kickoff from schedule. $_"
        return $null
    }
}

function Get-LeaguePlayoffStartUtc {
    param(
        [AllowNull()][array]$Schedule,
        [Parameter(Mandatory = $true)][int]$PlayoffStartWeek
    )

    if (-not $Schedule -or @($Schedule).Count -eq 0 -or $PlayoffStartWeek -le 0) {
        return $null
    }

    $weekLabel = "Week $PlayoffStartWeek"
    $playoffWeekGames = @($Schedule | Where-Object {
        $_.seasonType -eq "Regular Season" -and
        [string]$_.gameWeek -eq $weekLabel -and
        -not [string]::IsNullOrWhiteSpace([string]$_.gameTime_epoch)
    })

    if ($playoffWeekGames.Count -eq 0) {
        return $null
    }

    $firstGame = $playoffWeekGames |
        Sort-Object { [double]$_.gameTime_epoch } |
        Select-Object -First 1

    try {
        return [DateTimeOffset]::FromUnixTimeSeconds([int64][double]$firstGame.gameTime_epoch).UtcDateTime
    }
    catch {
        Write-Warning "Could not parse first kickoff for fantasy playoff Week $PlayoffStartWeek from schedule. $_"
        return $null
    }
}

function Get-LeagueNeutralTeamOrderIndex {
    $allTimeStandings = @(Get-StandingsLocal | Where-Object { [string]$_.Season -eq "AllTime" })
    if ($allTimeStandings.Count -ne 1) {
        throw "Expected exactly one AllTime standings record for neutral fantasy-team ordering, found $($allTimeStandings.Count)."
    }

    return Get-FantasyTeamNeutralOrderIndex -AllTimeOverallStandings @($allTimeStandings[0].Playoffs)
}

function ConvertTo-LeagueMatchupSnapshot {
    param(
        [AllowNull()][array]$Matchups,
        [Parameter(Mandatory = $true)][int]$Week,
        [Parameter(Mandatory = $true)][string]$Season,
        [AllowNull()][System.Collections.IDictionary]$NeutralTeamOrderIndex = $null
    )

    if ($Week -le 0) {
        return $null
    }

    $resolvedNeutralOrderIndex = if ($null -ne $NeutralTeamOrderIndex) {
        $NeutralTeamOrderIndex
    }
    else {
        Get-LeagueNeutralTeamOrderIndex
    }

    $validRows = @($Matchups | Where-Object {
        $matchupID = 0
        $rosterID = 0
        [int]::TryParse([string]$_.matchup_id, [ref]$matchupID) -and
        $matchupID -gt 0 -and
        [int]::TryParse([string]$_.roster_id, [ref]$rosterID) -and
        $rosterID -gt 0
    })

    $mappedMatchups = @()
    foreach ($group in @($validRows | Group-Object { [int]$_.matchup_id } | Sort-Object { [int]$_.Name })) {
        $participants = @($group.Group)
        if ($participants.Count -ne 2) {
            Write-Warning "Skipping Sleeper matchup '$($group.Name)' for Week $Week because it contains $($participants.Count) participants instead of 2."
            continue
        }

        $participantRows = @($participants |
            Sort-Object { Get-FantasyTeamNeutralOrderPosition -NeutralOrderIndex $resolvedNeutralOrderIndex -TeamID $_.roster_id } |
            ForEach-Object {
                $points = 0.0
                if ($null -ne $_.points) {
                    $points = [double]$_.points
                }

                [PSCustomObject][ordered]@{
                    TeamID = [int]$_.roster_id
                    Points = $points
                }
            })

        $mappedMatchups += [PSCustomObject][ordered]@{
            MatchupID    = [int]$group.Name
            Participants = $participantRows
        }
    }

    return [PSCustomObject][ordered]@{
        Season   = $Season
        Week     = $Week
        Matchups = @($mappedMatchups)
    }
}

function Get-LeagueMatchupSnapshot {
    param(
        [string]$LeagueID = (Get-Config).LeagueID,
        [Parameter(Mandatory = $true)][int]$Week,
        [Parameter(Mandatory = $true)][string]$Season
    )

    if ($Week -le 0) {
        return $null
    }

    try {
        $matchups = Get-SleeperMatchups -leagueID $LeagueID -week $Week
        return ConvertTo-LeagueMatchupSnapshot -Matchups @($matchups) -Week $Week -Season $Season
    }
    catch {
        Write-Warning "Could not refresh Sleeper matchups for Week $Week. Keeping the previous generated snapshot when available. $_"
        return $null
    }
}
