# ===========================================================================
# League-scoring Players inputs (#347 D4)
#
# Consumes the export of tools/players_league_scoring.py: canonical NFL stats scored
# with the league ScoringSettings, per Sleeper player ID and season. It replaces
# Tank01 PPR points and the Tank01 past_seasons/Players_<year>.json archives as the
# points source of RequestPlayers.ps1. Salary, ranking and grading formulas stay in
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

# Rescores the per-game points of the current season in place. Only final regular-season weeks
# are replaced (a week without a stat row scores 0); playoff and not yet final games keep the
# provider value. Returns the number of rescored games.
function Update-PlayerGameHistoryLeaguePoints {
    param(
        [AllowNull()][AllowEmptyCollection()]$GameHistory,
        [AllowNull()]$SeasonRows,
        [Parameter(Mandatory = $true)][int[]]$FinalWeeks
    )

    $rescored = 0
    foreach ($game in @($GameHistory)) {
        if ($null -eq $game) { continue }
        $week = [int]$game.GameDetails.Week
        if ($game.GameDetails.WeekPlayoff -or ($FinalWeeks -notcontains $week)) { continue }

        $row = if ($SeasonRows) { $SeasonRows[[string]$week] } else { $null }
        $game.FantasyPoints = if ($row) { [math]::Round([double]$row.Points, 2) } else { 0.0 }
        $rescored++
    }
    return $rescored
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
    Get-PlayerLeagueScoringPlayedRows, `
    Get-PlayerLeagueScoringSeasonStats, `
    Get-PlayerLeagueScoringCurrentStats, `
    Update-PlayerGameHistoryLeaguePoints
