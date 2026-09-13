# ===========================================================================
# 1. Functions
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
