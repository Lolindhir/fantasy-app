# ===========================================================================
# League-scoring Players inputs (#347 D4)
#
# Consumes the export of tools/players_league_scoring.py: canonical NFL stats scored
# with the league ScoringSettings, per Sleeper player ID and season, plus the current-season
# GameHistory entries (#347 G3, tools/players_game_history.py). It replaces Tank01 PPR points,
# the Tank01 past_seasons/Players_<year>.json archives and Games.json as inputs of RequestPlayers.ps1. Salary, ranking and grading formulas stay in
# RequestPlayers.ps1 / PlayerUtils.psm1 and are unchanged.
# ===========================================================================

function Get-PlayerLeagueScoringRepoRoot {
    return (Resolve-Path (Join-Path $PSScriptRoot "../../../..")).Path
}

function Get-PlayerLeagueScoringPythonCommand {
    foreach ($name in @("python3", "python")) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($command) { return $command.Source }
    }

    throw "Python is required for the league-scoring Players inputs."
}

# Returns the export as nested hashtables (Players -> Sleeper ID -> Seasons -> season -> week -> row).
function Invoke-PlayerLeagueScoringExport {
    param(
        [Parameter(Mandatory = $true)][string[]]$SleeperIDs,
        [Parameter(Mandatory = $true)][int]$Season,
        [string]$RepoRoot = (Get-PlayerLeagueScoringRepoRoot)
    )

    $toolPath = Join-Path $RepoRoot "tools/players_league_scoring.py"
    if (-not (Test-Path $toolPath)) {
        throw "League-scoring export tool missing at '$toolPath'."
    }

    $python = Get-PlayerLeagueScoringPythonCommand
    $idsFile = [System.IO.Path]::GetTempFileName()
    $outFile = [System.IO.Path]::GetTempFileName()
    try {
        ConvertTo-Json -InputObject @($SleeperIDs | Sort-Object -Unique) -Compress | Set-Content -Path $idsFile -Encoding UTF8
        $output = & $python $toolPath --repo-root $RepoRoot export --season $Season --sleeper-ids-file $idsFile --out $outFile 2>&1
        $exitCode = $LASTEXITCODE
        $outputText = (@($output) | ForEach-Object { [string]$_ }) -join [Environment]::NewLine
        if ($exitCode -ne 0) {
            throw "League-scoring export failed with exit code $exitCode. $outputText"
        }
        Write-Host $outputText -ForegroundColor Yellow

        try {
            return (Get-Content $outFile -Raw | ConvertFrom-Json -AsHashtable)
        }
        catch {
            throw "League-scoring export returned invalid JSON. $_"
        }
    }
    finally {
        Remove-Item $idsFile, $outFile -Force -ErrorAction SilentlyContinue
    }
}

# Week bounds (LastLeagueWeek, PlayoffStartWeek, FinalScoredWeek) from the canonical League-season
# WeekStructure and canonical NFL game finality (#347 I1). Fails closed; no League.json involved.
function Get-PlayerLeagueWeekBounds {
    param(
        [Parameter(Mandatory = $true)][int]$Season,
        [string]$RepoRoot = (Get-PlayerLeagueScoringRepoRoot)
    )

    $toolPath = Join-Path $RepoRoot "tools/players_league_scoring.py"
    if (-not (Test-Path $toolPath)) {
        throw "League-scoring tool missing at '$toolPath'."
    }

    $python = Get-PlayerLeagueScoringPythonCommand
    $output = & $python $toolPath --repo-root $RepoRoot week-bounds --season $Season 2>&1
    $exitCode = $LASTEXITCODE
    $outputText = (@($output) | ForEach-Object { [string]$_ }) -join [Environment]::NewLine
    if ($exitCode -ne 0) {
        throw "Canonical league week bounds failed with exit code $exitCode. $outputText"
    }

    try {
        $bounds = $outputText | ConvertFrom-Json
    }
    catch {
        throw "Canonical league week bounds returned invalid JSON. $outputText"
    }
    foreach ($name in @('LastLeagueWeek', 'PlayoffStartWeek', 'FinalScoredWeek')) {
        if ($null -eq $bounds.$name -or [int]$bounds.$name -lt 0) {
            throw "Canonical league week bounds lack '$name'."
        }
    }
    return $bounds
}

# A game counts as played with offensive snaps; kickers play with at least one kick attempt.
function Get-PlayerLeagueScoringPlayedRows {
    param(
        [AllowNull()]$SeasonRows,
        [Parameter(Mandatory = $true)][string]$Position,
        [Parameter(Mandatory = $true)][int]$LastWeek
    )

    $rows = @()
    if (-not $SeasonRows) { return $rows }

    foreach ($week in @($SeasonRows.Keys | ForEach-Object { [int]$_ } | Sort-Object)) {
        if ($week -gt $LastWeek) { continue }
        $row = $SeasonRows[[string]$week]
        $played = if ($Position -eq "K") { [double]$row.KickAttempts -gt 0 } else { [double]$row.Snaps -gt 0 }
        if ($played) { $rows += , $row }
    }
    return $rows
}

function Get-PlayerLeagueScoringSeasonStats {
    param(
        [AllowNull()]$SeasonRows,
        [Parameter(Mandatory = $true)][string]$Position,
        [Parameter(Mandatory = $true)][int]$LastWeek
    )

    $result = [ordered]@{
        Total            = 0.0
        AvgGame          = 0.0
        AvgPotentialGame = 0.0
        GamesPlayed      = 0
        PotentialGames   = $LastWeek - 1
    }

    $games = @(Get-PlayerLeagueScoringPlayedRows -SeasonRows $SeasonRows -Position $Position -LastWeek $LastWeek)
    $result.GamesPlayed = $games.Count
    if ($games.Count -gt 0) {
        $sum = 0.0
        foreach ($game in $games) { $sum += [double]$game.Points }
        $result.Total = [math]::Round($sum, 2)
        $result.AvgGame = [math]::Round($result.Total / $result.GamesPlayed, 2)
    }
    if ($result.PotentialGames -gt 0) {
        $result.AvgPotentialGame = [math]::Round($result.Total / $result.PotentialGames, 2)
    }

    return $result
}

# Current-season aggregates in the field shape RequestPlayers.ps1 publishes.
function Get-PlayerLeagueScoringCurrentStats {
    param(
        [AllowNull()]$SeasonRows,
        [Parameter(Mandatory = $true)][string]$Position,
        [Parameter(Mandatory = $true)][int]$LastWeek,
        [Parameter(Mandatory = $true)][int]$GamesPotential
    )

    $games = @(Get-PlayerLeagueScoringPlayedRows -SeasonRows $SeasonRows -Position $Position -LastWeek $LastWeek)
    $points = 0.0
    $snaps = 0.0
    $attempts = 0.0
    $tdPass = 0
    $tdRec = 0
    $tdRush = 0
    foreach ($game in $games) {
        $points += [double]$game.Points
        $snaps += if ($Position -eq "K") { [double]$game.KickAttempts } else { [double]$game.Snaps }
        $attempts += [double]$game.Attempts
        $tdPass += [int]$game.TdPass
        $tdRec += [int]$game.TdRec
        $tdRush += [int]$game.TdRush
    }

    $snapsTotal = [int]$snaps
    $attemptsTotal = [int]$attempts
    return [ordered]@{
        GamesPlayed                   = $games.Count
        SnapsTotal                    = $snapsTotal
        AttemptsTotal                 = $attemptsTotal
        FantasyPointsTotal            = [math]::Round($points, 2)
        FantasyPointsAvgGame          = if ($games.Count -gt 0) { [math]::Round($points / $games.Count, 2) } else { 0 }
        FantasyPointsAvgPotentialGame = if ($GamesPotential -gt 0) { [math]::Round($points / $GamesPotential, 2) } else { 0 }
        FantasyPointsAvgSnap          = if ($snapsTotal -gt 0) { [math]::Round($points / $snapsTotal, 5) } else { 0 }
        FantasyPointsAvgAttempt       = if ($attemptsTotal -gt 0) { [math]::Round($points / $attemptsTotal, 5) } else { 0 }
        TouchdownsTotal               = $tdPass + $tdRec + $tdRush
        TouchdownsPassing             = $tdPass
        TouchdownsReceiving           = $tdRec
        TouchdownsRushing             = $tdRush
    }
}

# GameHistory entries of the export (tools/players_game_history.py) in the published Players.json shape,
# newest game first. WeekPlayoff and WeekScored keep their League-week formulas here. Optional blocks
# (Passing, Rushing, Receiving, Kicking) are only present when the export has them; LongRush,
# LongReceptions and QBRating stay null when the canonical source has no value yet (unknown, not zero).
function ConvertTo-PlayerGameHistory {
    param(
        [AllowNull()][AllowEmptyCollection()]$Entries,
        [Parameter(Mandatory = $true)][int]$PlayoffStartWeek,
        [Parameter(Mandatory = $true)][int]$LastLeagueWeek
    )

    $history = @()
    foreach ($entry in @($Entries)) {
        if ($null -eq $entry) { continue }
        $week = [int]$entry.Week
        $game = [ordered]@{}
        $game.GameID = [string]$entry.GameID
        $game.GameDetails = [ordered]@{
            Week        = $week
            WeekFinal   = [bool]$entry.WeekFinal
            WeekPlayoff = ($week -ge $PlayoffStartWeek -and $PlayoffStartWeek -gt 0)
            WeekScored  = ($week -le $LastLeagueWeek)
            Date        = [string]$entry.Date
            Home        = [string]$entry.Home
            HomeID      = [string]$entry.Home
            Away        = [string]$entry.Away
            AwayID      = [string]$entry.Away
            HomePoints  = if ($null -ne $entry.HomePoints) { [int]$entry.HomePoints } else { 0 }
            AwayPoints  = if ($null -ne $entry.AwayPoints) { [int]$entry.AwayPoints } else { 0 }
        }
        $game.TeamID = [string]$entry.TeamID
        $game.TeamAbv = [string]$entry.TeamAbv
        $game.FantasyPoints = [math]::Round([double]$entry.FantasyPoints, 2)
        $game.Touchdowns = [int]$entry.Touchdowns
        $game.SnapCount = [int]$entry.SnapCount
        $game.SnapPercentage = [double]$entry.SnapPercentage
        $game.Attempts = [int]$entry.Attempts

        if ($entry.ContainsKey('Passing')) {
            $pass = $entry.Passing
            $game.Passing = [PSCustomObject]@{
                QBRating        = if ($null -ne $pass.QBRating) { [double]$pass.QBRating } else { $null }
                Rating          = [double]$pass.Rating
                PassAttempts    = [int]$pass.PassAttempts
                PassAvg         = [double]$pass.PassAvg
                PassTDs         = [int]$pass.PassTDs
                PassYards       = [int]$pass.PassYards
                Interceptions   = [int]$pass.Interceptions
                PassCompletions = [int]$pass.PassCompletions
            }
        }
        if ($entry.ContainsKey('Receiving')) {
            $rec = $entry.Receiving
            $game.Receiving = [PSCustomObject]@{
                Receptions     = [int]$rec.Receptions
                ReceptionTDs   = [int]$rec.ReceptionTDs
                LongReceptions = if ($null -ne $rec.LongReceptions) { [int]$rec.LongReceptions } else { $null }
                Targets        = [int]$rec.Targets
                ReceptionYards = [int]$rec.ReceptionYards
                ReceptionAvg   = [double]$rec.ReceptionAvg
            }
        }
        if ($entry.ContainsKey('Rushing')) {
            $rush = $entry.Rushing
            $game.Rushing = [PSCustomObject]@{
                RushAvg  = [double]$rush.RushAvg
                RushYards = [int]$rush.RushYards
                Carries  = [int]$rush.Carries
                LongRush = if ($null -ne $rush.LongRush) { [int]$rush.LongRush } else { $null }
                RushTDs  = [int]$rush.RushTDs
            }
        }
        if ($entry.ContainsKey('Kicking')) {
            $kick = $entry.Kicking
            $game.Kicking = [PSCustomObject]@{
                KickingPts = [double]$kick.KickingPts
                FgLong     = [int]$kick.FgLong
                FgMade     = [int]$kick.FgMade
                FgAttempts = [int]$kick.FgAttempts
                FgMissed   = [int]$kick.FgMissed
                FgPct      = [double]$kick.FgPct
                XpMade     = [int]$kick.XpMade
                XpAttempts = [int]$kick.XpAttempts
                XpMissed   = [int]$kick.XpMissed
            }
        }
        $history += , $game
    }
    return $history
}

# Identity hold: the player has no unique canonical identity for the current season, so no league
# scoring exists. The last published values are kept (zeros for a player that was never published).
function Get-PlayerLeagueScoringHeldStats {
    param([AllowNull()]$OldPlayer)

    $current = [ordered]@{
        GamesPlayed                   = 0
        SnapsTotal                    = 0
        AttemptsTotal                 = 0
        FantasyPointsTotal            = 0
        FantasyPointsAvgGame          = 0
        FantasyPointsAvgPotentialGame = 0
        FantasyPointsAvgSnap          = 0
        FantasyPointsAvgAttempt       = 0
        TouchdownsTotal               = 0
        TouchdownsPassing             = 0
        TouchdownsReceiving           = 0
        TouchdownsRushing             = 0
    }
    $pointHistory = [ordered]@{}
    foreach ($key in @("SeasonMinus1", "SeasonMinus2", "SeasonMinus3")) {
        $pointHistory[$key] = [ordered]@{
            Total            = 0.0
            AvgGame          = 0.0
            AvgPotentialGame = 0.0
            GamesPlayed      = 0
            PotentialGames   = 0
        }
    }

    if ($OldPlayer) {
        foreach ($name in @($current.Keys)) {
            if ($null -ne $OldPlayer.$name) { $current[$name] = $OldPlayer.$name }
        }
        foreach ($key in @($pointHistory.Keys)) {
            if ($OldPlayer.PointHistory -and $OldPlayer.PointHistory.$key) { $pointHistory[$key] = $OldPlayer.PointHistory.$key }
        }
    }

    return [ordered]@{ Current = $current; PointHistory = $pointHistory }
}

Export-ModuleMember -Function `
    Get-PlayerLeagueScoringHeldStats, `
    Invoke-PlayerLeagueScoringExport, `
    Get-PlayerLeagueWeekBounds, `
    Get-PlayerLeagueScoringPlayedRows, `
    Get-PlayerLeagueScoringSeasonStats, `
    Get-PlayerLeagueScoringCurrentStats, `
    ConvertTo-PlayerGameHistory
