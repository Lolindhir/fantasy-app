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

function ConvertTo-LeagueMatchupSnapshot {
    param(
        [AllowNull()][array]$Matchups,
        [Parameter(Mandatory = $true)][int]$Week,
        [Parameter(Mandatory = $true)][string]$Season
    )

    if ($Week -le 0) {
        return $null
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
            Sort-Object { [int]$_.roster_id } |
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
