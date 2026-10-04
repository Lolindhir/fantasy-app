# Team abbreviations that differ between Tank01 (Players.json team) and the canonical NFL schedule (nflverse).
$script:NflScheduleTeamAliases = @{
    'LAR' = 'LA'
    'WSH' = 'WAS'
}

function ConvertTo-CanonicalNflScheduleTeam {
    param([AllowNull()][string]$Team)

    if ([string]::IsNullOrWhiteSpace($Team)) { return $null }
    $value = $Team.Trim().ToUpperInvariant()
    if ($script:NflScheduleTeamAliases.ContainsKey($value)) { return $script:NflScheduleTeamAliases[$value] }
    return $value
}

# Returns a hashtable canonical team -> bye week (the single REG week without a game for that team).
# Fails closed when the schedule is missing, has an unexpected source, or a team does not have exactly one bye.
function Get-CanonicalNflTeamByeWeeks {
    param(
        [Parameter(Mandatory = $true)][int]$Season,
        [Parameter(Mandatory = $true)][string]$RepoRoot
    )

    $path = Join-Path $RepoRoot "source-data/nfl/schedules/$Season.json"
    if (-not (Test-Path $path)) {
        throw "Canonical NFL schedule is required for bye weeks: $path"
    }

    $schedule = Get-Content $path -Raw | ConvertFrom-Json
    if ([int]$schedule.Season -ne $Season) {
        throw "Canonical NFL schedule season mismatch: expected $Season, got $($schedule.Season)."
    }
    if ([string]$schedule.SourceDataset -ne 'nflverse.schedules') {
        throw "Unexpected canonical NFL schedule source '$($schedule.SourceDataset)'."
    }

    $regGames = @($schedule.Games | Where-Object { [string]$_.GameType -eq 'REG' })
    if ($regGames.Count -eq 0) {
        throw "Canonical NFL schedule $Season has no REG games."
    }

    $maxWeek = ($regGames | ForEach-Object { [int]$_.Week } | Measure-Object -Maximum).Maximum
    $weeksByTeam = @{}
    foreach ($game in $regGames) {
        foreach ($team in @([string]$game.HomeTeam, [string]$game.AwayTeam)) {
            if ([string]::IsNullOrWhiteSpace($team)) {
                throw "Canonical NFL schedule $Season has a REG game without both teams: $($game.GameID)."
            }
            if (-not $weeksByTeam.ContainsKey($team)) { $weeksByTeam[$team] = @{} }
            if ($weeksByTeam[$team].ContainsKey([int]$game.Week)) {
                throw "Canonical NFL schedule $Season lists $team twice in week $($game.Week)."
            }
            $weeksByTeam[$team][[int]$game.Week] = $true
        }
    }

    $byeWeeks = @{}
    foreach ($team in $weeksByTeam.Keys) {
        $missing = @(1..$maxWeek | Where-Object { -not $weeksByTeam[$team].ContainsKey($_) })
        if ($missing.Count -ne 1) {
            throw "Canonical NFL schedule ${Season}: team $team has $($missing.Count) REG weeks without a game (expected exactly one bye)."
        }
        $byeWeeks[$team] = [int]$missing[0]
    }
    return $byeWeeks
}

Export-ModuleMember -Function ConvertTo-CanonicalNflScheduleTeam, Get-CanonicalNflTeamByeWeeks
