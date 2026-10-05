$ErrorActionPreference = 'Stop'

Import-Module "$PSScriptRoot\utils\player\PlayerLeagueScoringUtils.psm1" -Force

function Assert-PlsTrue {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw "ASSERTION FAILED: $Message" }
}

function Assert-PlsEqual {
    param($Actual, $Expected, [string]$Message)
    if ($Actual -ne $Expected) { throw "ASSERTION FAILED: $Message (expected '$Expected', got '$Actual')." }
}

function New-PlsRow {
    param([double]$Points, [double]$Snaps = 0, [double]$KickAttempts = 0, [double]$Attempts = 0, [int]$TdPass = 0, [int]$TdRec = 0, [int]$TdRush = 0)
    return @{ Points = $Points; Snaps = $Snaps; KickAttempts = $KickAttempts; Attempts = $Attempts; TdPass = $TdPass; TdRec = $TdRec; TdRush = $TdRush }
}

# 1. Played games: offensive snaps, kickers need a kick attempt; weeks after LastWeek are ignored.
$rows = @{
    '1'  = New-PlsRow -Points 10.005 -Snaps 40 -Attempts 12 -TdRec 1
    '2'  = New-PlsRow -Points 3.0 -Snaps 0
    '3'  = New-PlsRow -Points 5.5 -Snaps 25 -Attempts 4 -TdRush 1
    '18' = New-PlsRow -Points 99 -Snaps 60
}
$playedWr = @(Get-PlayerLeagueScoringPlayedRows -SeasonRows $rows -Position 'WR' -LastWeek 17)
Assert-PlsEqual $playedWr.Count 2 'Only weeks with offensive snaps up to LastWeek count for field players.'
$kickRows = @{ '1' = New-PlsRow -Points 8 -Snaps 0 -KickAttempts 3; '2' = New-PlsRow -Points 0 -Snaps 5 }
Assert-PlsEqual @(Get-PlayerLeagueScoringPlayedRows -SeasonRows $kickRows -Position 'K' -LastWeek 17).Count 1 'Kickers play with a kick attempt, not with snaps.'
Assert-PlsEqual @(Get-PlayerLeagueScoringPlayedRows -SeasonRows $null -Position 'QB' -LastWeek 17).Count 0 'A missing season has no played rows.'

# 2. Prior-season aggregates: PotentialGames is LastWeek - 1, rounding follows [math]::Round.
$history = Get-PlayerLeagueScoringSeasonStats -SeasonRows $rows -Position 'WR' -LastWeek 17
Assert-PlsEqual $history.GamesPlayed 2 'History games played.'
Assert-PlsEqual $history.PotentialGames 16 'History potential games.'
Assert-PlsEqual $history.Total ([math]::Round(10.005 + 5.5, 2)) 'History total is rounded to two decimals.'
Assert-PlsEqual $history.AvgGame ([math]::Round($history.Total / 2, 2)) 'History average per game.'
Assert-PlsEqual $history.AvgPotentialGame ([math]::Round($history.Total / 16, 2)) 'History average per potential game.'
$empty = Get-PlayerLeagueScoringSeasonStats -SeasonRows $null -Position 'WR' -LastWeek 17
Assert-PlsEqual $empty.Total 0 'Empty history total.'
Assert-PlsEqual $empty.GamesPlayed 0 'Empty history games.'

# 3. Current-season aggregates.
$current = Get-PlayerLeagueScoringCurrentStats -SeasonRows $rows -Position 'WR' -LastWeek 17 -GamesPotential 3
$sum = 10.005 + 5.5
Assert-PlsEqual $current.GamesPlayed 2 'Current games played.'
Assert-PlsEqual $current.SnapsTotal 65 'Current snaps total.'
Assert-PlsEqual $current.AttemptsTotal 16 'Current attempts total.'
Assert-PlsEqual $current.FantasyPointsTotal ([math]::Round($sum, 2)) 'Current points total.'
Assert-PlsEqual $current.FantasyPointsAvgPotentialGame ([math]::Round($sum / 3, 2)) 'Current average per potential game.'
Assert-PlsEqual $current.FantasyPointsAvgSnap ([math]::Round($sum / 65, 5)) 'Current average per snap.'
Assert-PlsEqual $current.TouchdownsTotal 2 'Touchdowns are summed over played games.'
Assert-PlsEqual $current.TouchdownsRushing 1 'Rushing touchdowns.'
$noPotential = Get-PlayerLeagueScoringCurrentStats -SeasonRows $rows -Position 'WR' -LastWeek 17 -GamesPotential 0
Assert-PlsEqual $noPotential.FantasyPointsAvgPotentialGame 0 'No potential games gives a zero average.'
$kicker = Get-PlayerLeagueScoringCurrentStats -SeasonRows $kickRows -Position 'K' -LastWeek 17 -GamesPotential 2
Assert-PlsEqual $kicker.SnapsTotal 3 'Kickers count kick attempts as snaps.'

# 4. Per-game points: only final regular-season weeks are rescored, a final week without a row scores 0.
function New-PlsGame { param([int]$Week, [double]$Points, [bool]$Playoff = $false)
    return [ordered]@{ GameID = "g$Week"; GameDetails = [ordered]@{ Week = $Week; WeekPlayoff = $Playoff }; FantasyPoints = $Points }
}
$games = @((New-PlsGame 1 99), (New-PlsGame 2 99), (New-PlsGame 3 99), (New-PlsGame 4 99), (New-PlsGame 3 99 $true))
$count = Update-PlayerGameHistoryLeaguePoints -GameHistory $games -SeasonRows $rows -FinalWeeks @(1, 2, 3)
Assert-PlsEqual $count 3 'Only final regular-season games are rescored.'
Assert-PlsEqual $games[0].FantasyPoints 10.01 'Week 1 takes the league points rounded to two decimals.'
Assert-PlsEqual $games[1].FantasyPoints 3 'Week 2 keeps a zero-snap game with its points.'
Assert-PlsEqual $games[3].FantasyPoints 99 'A non-final week keeps the provider points.'
Assert-PlsEqual $games[4].FantasyPoints 99 'A playoff game keeps the provider points.'
$missing = @((New-PlsGame 2 99))
Update-PlayerGameHistoryLeaguePoints -GameHistory $missing -SeasonRows @{} -FinalWeeks @(2) | Out-Null
Assert-PlsEqual $missing[0].FantasyPoints 0 'A final week without a stat row scores zero.'

# 5. Identity hold keeps the last published values, zeros for a player that was never published.
$old = [PSCustomObject]@{
    GamesPlayed = 4; SnapsTotal = 120; FantasyPointsTotal = 33.3
    PointHistory = [PSCustomObject]@{ SeasonMinus1 = [PSCustomObject]@{ Total = 50.5; AvgGame = 5; AvgPotentialGame = 3; GamesPlayed = 10; PotentialGames = 16 } }
}
$held = Get-PlayerLeagueScoringHeldStats -OldPlayer $old
Assert-PlsEqual $held.Current.GamesPlayed 4 'Held player keeps the published games played.'
Assert-PlsEqual $held.Current.FantasyPointsTotal 33.3 'Held player keeps the published points.'
Assert-PlsEqual $held.PointHistory.SeasonMinus1.Total 50.5 'Held player keeps the published history.'
Assert-PlsEqual $held.PointHistory.SeasonMinus2.Total 0 'Held player has zero history where nothing was published.'
$never = Get-PlayerLeagueScoringHeldStats -OldPlayer $null
Assert-PlsEqual $never.Current.GamesPlayed 0 'A never published held player starts at zero.'

# 6. Real export: expectations are derived from the repository data, no hardwired players.
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$players = @(Get-Content (Join-Path $repoRoot 'public/data/Players.json') -Raw | ConvertFrom-Json)
$league = Get-Content (Join-Path $repoRoot 'public/data/League.json') -Raw | ConvertFrom-Json
$season = [int]$league.Season
$lastWeek = [int]$league.LastLeagueWeek
$export = Invoke-PlayerLeagueScoringExport -SleeperIDs @($players | ForEach-Object { [string]$_.ID }) -Season $season
Assert-PlsEqual ([int]$export.Season) $season 'Export season.'
Assert-PlsTrue (@($export.FinalRegularWeeksCurrent).Count -gt 0) 'Export lists the final regular weeks of the current season.'
$sampled = 0
for ($i = 0; $i -lt $players.Count; $i += 25) {
    $player = $players[$i]
    $entry = $export.Players[[string]$player.ID]
    Assert-PlsTrue ($null -ne $entry) "Export has an entry for player $($player.ID)."
    if ($entry.Status -ne 'resolved') { continue }
    $rowsOfSeason = $entry.Seasons[[string]$season]
    $expectedGames = 0
    foreach ($key in @($rowsOfSeason.Keys)) {
        $row = $rowsOfSeason[$key]
        $played = if ($player.Position -eq 'K') { $row.KickAttempts -gt 0 } else { $row.Snaps -gt 0 }
        if ($played -and [int]$key -le $lastWeek) { $expectedGames++ }
    }
    $stats = Get-PlayerLeagueScoringCurrentStats -SeasonRows $rowsOfSeason -Position $player.Position -LastWeek $lastWeek -GamesPotential ([int]$player.GamesPotential)
    Assert-PlsEqual $stats.GamesPlayed $expectedGames "Games played of player $($player.ID) follow the exported rows."
    $sampled++
}
Assert-PlsTrue ($sampled -gt 0) 'At least one sampled player resolved.'

Write-Host "PlayerLeagueScoringRegressionTest passed ($sampled sampled players)." -ForegroundColor Green
