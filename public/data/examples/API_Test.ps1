# ==========================
# Combined API Test Script (Sleeper → Tank01 → DraftKings)
# ==========================

# --- Konfiguration laden ---
. "$PSScriptRoot\config.ps1"
if (-not $Global:LeagueID) {
    Write-Error "LeagueID not found in config.ps1"
    exit 1
}

$LeagueID = $Global:LeagueID
Write-Host "Using LeagueID from config: $LeagueID" -ForegroundColor Yellow

# --- Sleeper: Liga abrufen ---
try {
    Write-Host "Fetching Sleeper League $LeagueID..." -ForegroundColor Yellow
    $leagueUrl = "https://api.sleeper.app/v1/league/$LeagueID"
    $league    = Invoke-RestMethod -Uri $leagueUrl -ErrorAction Stop
} catch {
    Write-Error "Error retrieving league: $_"
    exit 1
}

# --- Sleeper Mitglieder + Rosters abrufen ---
try {
    $membersUrl = "https://api.sleeper.app/v1/league/$LeagueID/users"
    $members    = Invoke-RestMethod -Uri $membersUrl -ErrorAction Stop

    $rostersUrl = "https://api.sleeper.app/v1/league/$LeagueID/rosters"
    $rosters    = Invoke-RestMethod -Uri $rostersUrl -ErrorAction Stop
} catch {
    Write-Error "Error retrieving members/rosters: $_"
    exit 1
}

# --- Sleeper: Alle Spieler laden ---
Write-Host "Fetching Sleeper players..." -ForegroundColor Yellow
try {
    $sleeperPlayersUrl = "https://api.sleeper.app/v1/players/nfl"
    $sleeperPlayersRaw = Invoke-RestMethod -Uri $sleeperPlayersUrl
    $sleeperPlayers = $sleeperPlayersRaw.PSObject.Properties.Value
} catch {
    Write-Error "Error fetching Sleeper players: $_"
    exit 1
}

if (-not $sleeperPlayers -or $sleeperPlayers.Count -eq 0) {
    Write-Error "No Sleeper players returned."
    exit 1
}


# --- Einen Sleeper-Spieler aus deiner Liga nehmen ---
$sleeperPlayerID = $rosters[0].starters[0]
$sleeperPlayer = $sleeperPlayers | Where-Object { $_.player_id -eq $sleeperPlayerID } | Select-Object -First 1
if (-not $sleeperPlayer) {
    Write-Error "No Sleeper player found for roster starter."
    exit 1
}

# ==========================================================
# --- Tank01 Setup ---
# ==========================================================
if (-not $Global:RapidAPIKeyAlt1) {
    Write-Error "Tank01 API key missing in config.ps1"
    exit 1
}

$apiKey  = $Global:RapidAPIKeyAlt1
$apiHost = "tank01-nfl-live-in-game-real-time-statistics-nfl.p.rapidapi.com"

function Invoke-Tank01 {
    param ([string]$Url)
    $headers = @{
        "X-RapidAPI-Key"  = $apiKey
        "X-RapidAPI-Host" = $apiHost
    }
    return Invoke-RestMethod -Uri $Url -Headers $headers -ErrorAction Stop
}

Write-Host "Fetching Tank01 players..." -ForegroundColor Yellow


# --- Tank01: Alle Spieler abrufen ---
$playerListUrl = "https://$apiHost/getNFLPlayerList"
try {
    $playerListResponse = Invoke-Tank01 -Url $playerListUrl
    $allPlayers = $playerListResponse.body
} catch {
    Write-Error "Error fetching Tank01 players: $_"
    exit 1
}

if (-not $allPlayers) {
    Write-Error "No Tank01 players found."
    exit 1
}

# --- Versuche, Sleeper-Spieler in Tank01 zu finden ---
$tankMatch = $allPlayers | Where-Object {
    $_.longName -match [regex]::Escape($sleeperPlayer.full_name)
} | Select-Object -First 1

if (-not $tankMatch) {
    $tankMatch = $allPlayers | Select-Object -First 1
}

# ==========================================================
# --- Tank01: Matching Spieler pro Position (QB, RB, WR, TE, K)
# ==========================================================

$positions = @("QB", "RB", "WR", "TE", "K")
$tankMatches = @{}

foreach ($pos in $positions) {
    # Finde Sleeper-Spieler dieser Position aus erstem Roster (alle Spieler, nicht nur Starter)
    $sleeperPlayerPos = $null
    foreach ($playerId in $rosters[0].starters) {
        $candidate = $sleeperPlayers | Where-Object { $_.player_id -eq $playerId -and $_.position -eq $pos } | Select-Object -First 1
        if ($candidate) {
            $sleeperPlayerPos = $candidate
            break
        }
    }

    if (-not $sleeperPlayerPos) {
        Write-Warning "No Sleeper player found for position $pos."
        continue
    }

    # Finde passenden Tank01-Spieler nach Namen
    $tankTempMatch = $allPlayers | Where-Object {
        $_.longName -match [regex]::Escape($sleeperPlayerPos.full_name)
    } | Select-Object -First 1

    if (-not $tankTempMatch) {
        Write-Warning "No Tank01 player matched for $pos ($($sleeperPlayerPos.full_name)). Using fallback."
        $tankTempMatch = $allPlayers | Where-Object { $_.position -eq $pos } | Select-Object -First 1
    }

    # Variable für Zugriff + Sammlung für spätere Nutzung
    Set-Variable -Name "tank$pos" -Value $tankTempMatch -Scope Script
    $tankMatches[$pos] = $tankTempMatch

    Write-Host "Matched $($pos): $($sleeperPlayerPos.full_name) -> $($tankTempMatch.longName)" -ForegroundColor Cyan
}


# ==========================================================
# --- DraftKings / DFS Daten abrufen ---
# ==========================================================
function Convert-StringToDate($dateStr) {
    [datetime]::ParseExact($dateStr, 'yyyyMMdd', $null)
}

function Get-DraftKings($dateStr, $apiKeys) {
    $dfsUrl = "https://tank01-nfl-live-in-game-real-time-statistics-nfl.p.rapidapi.com/getNFLDFS?date=$dateStr"
    try {
        $dfsResponse = Invoke-Tank01 -Url $dfsUrl
    } catch {
        Write-Warning "Error fetching DraftKings data: $_"
        return $null
    }

    $draftKings = $dfsResponse.body.draftkings
    if (-not $draftKings -or $draftKings.Count -eq 0) {
        $prevDate = (Convert-StringToDate $dateStr).AddDays(-1).ToString("yyyyMMdd")
        return Get-DraftKings $prevDate $apiKeys
    }
    return $draftKings
}

Write-Host "Fetching Draft King Salaries..." -ForegroundColor Yellow

$dfsDate = (Get-Date).ToString("yyyyMMdd")
$dkPlayers = Get-DraftKings $dfsDate $apiKey

if (-not $dkPlayers) {
    Write-Error "No DraftKings data returned."
    exit 1
}

# --- Versuche, denselben Spieler im DraftKings-Dataset zu finden ---
$dkMatch = $dkPlayers | Where-Object {
    $_.playerID -match [regex]::Escape($tankMatch.playerID)
} | Select-Object -First 1

if (-not $dkMatch) {
    $dkMatch = $dkPlayers | Where-Object { $_.salary -gt 5000 } | Select-Object -First 1
}

# ==========================================================
# --- Spiele des Tank01-Spielers abrufen ---
# ==========================================================
if ($tankMatch.playerID) {
    $gamesUrl = "https://$apiHost/getNFLGamesForPlayer?playerID=$($tankMatch.playerID)&fantasyPoints=true&itemFormat=list"
    try {
        $gamesResponse = Invoke-Tank01 -Url $gamesUrl
        $playerGames = $gamesResponse.body
    } catch {
        $playerGames = @()
    }
} else {
    $playerGames = @()
}

# ==========================================================
# --- Box Score des Tank01-Spielers abrufen (letztes Spiel) ---
# ==========================================================
$gameID = $playerGames[0].gameID

Write-Host "Fetching Game Score for '$($gameID)'..." -ForegroundColor Yellow

$gameIDEncoded = [uri]::EscapeDataString($gameID)
$boxScoresUrl = "https://$apiHost/getNFLBoxScore?gameID=$($gameIDEncoded)&playByPlay=false&fantasyPoints=true"
try {
    $bscoreResponse = Invoke-Tank01 -Url $boxScoresUrl
    $boxScore = $bscoreResponse.body
} catch {
    $boxScore = @()
}

if (-not $boxScore) {
    Write-Error "No Game Score found."
    exit 1
}


# ==========================================================
# --- League-Schedule abrufen ---
# ==========================================================
Write-Host "Fetching League Schedule..." -ForegroundColor Yellow

# week all or week number
# seasonType can be: reg, post, pre, or all
# season (2025, 2024, ...), if empty current season assumed
$scheduleUrl = "https://$apiHost/getNFLGamesForWeek?week=all&seasonType=reg"
try {
    $scheduleResponse = Invoke-Tank01 -Url $scheduleUrl
    $schedule = $scheduleResponse.body
} catch {
    $schedule = @()
}

if (-not $schedule) {
    Write-Error "No schedule found."
    exit 1
}



# ==========================================================
# --- JSON-Dateien speichern ---
# ==========================================================
Write-Host "Saving JSON files..." -ForegroundColor Green

# --- Sleeper Daten ---
$league  | ConvertTo-Json -Depth 10 | Out-File "$PSScriptRoot\SleeperLeague.json"  -Encoding utf8
Write-Host "Saved league: $("$PSScriptRoot\SleeperLeague.json")" -ForegroundColor Green
$members | ConvertTo-Json -Depth 10 | Out-File "$PSScriptRoot\SleeperMembers.json" -Encoding utf8
Write-Host "Saved members: $("$PSScriptRoot\SleeperMembers.json")" -ForegroundColor Green
$rosters | ConvertTo-Json -Depth 10 | Out-File "$PSScriptRoot\SleeperRosters.json" -Encoding utf8
Write-Host "Saved rosters: $("$PSScriptRoot\SleeperRoster.json")" -ForegroundColor Green


# Nur EINEN Sleeper-Spieler
$sleeperPlayer | ConvertTo-Json -Depth 10 | Out-File "$PSScriptRoot\SleeperPlayer.json" -Encoding utf8
Write-Host "Saved Sleeper player: $("$PSScriptRoot\SleeperPlayer.json")" -ForegroundColor Green

# Nur EINEN Tank01-Spieler
$tankMatch | ConvertTo-Json -Depth 10 | Out-File "$PSScriptRoot\Tank01Player.json" -Encoding utf8
Write-Host "Saved Tank01 player: $("$PSScriptRoot\Tank01Player.json")" -ForegroundColor Green

# Nur EINEN DraftKings-/Salary-Spieler
$dkMatch | ConvertTo-Json -Depth 10 | Out-File "$PSScriptRoot\Tank01PlayerSalary.json" -Encoding utf8
Write-Host "Saved salary: $("$PSScriptRoot\Tank01PlayerSalary.json")" -ForegroundColor Green

# Nur Spiele dieses Spielers
$playerGames | ConvertTo-Json -Depth 10 | Out-File "$PSScriptRoot\Tank01PlayerGames.json" -Encoding utf8
Write-Host "Saved games for player: $("$PSScriptRoot\Tank01PlayerGames.json")" -ForegroundColor Green

# Game Score des letzten Spiel des Spielers ausgeben
$boxScore | ConvertTo-Json -Depth 10 | Out-File "$PSScriptRoot\Tank01GameScore.json" -Encoding utf8
Write-Host "Saved game score: $("$PSScriptRoot\Tank01GameScore.json")" -ForegroundColor Green

# Schedule ausgeben
$schedule | ConvertTo-Json -Depth 10 | Out-File "$PSScriptRoot\Tank01Schedule.json" -Encoding utf8
Write-Host "Saved schedule: $("$PSScriptRoot\Tank01Schedule.json")" -ForegroundColor Green

# ==========================================================
# --- Tank01: Spiele für QB, RB, WR, TE, K abrufen
# ==========================================================

$positions = @("QB", "RB", "WR", "TE", "K")

foreach ($pos in $positions) {
    $tankVarName = "tank$pos"
    $tankPlayer = Get-Variable -Name $tankVarName -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Value

    if ($tankPlayer -and $tankPlayer.playerID) {

        $gamesUrl = "https://$apiHost/getNFLGamesForPlayer?playerID=$($tankPlayer.playerID)&fantasyPoints=true"
        try {
            $gamesResponse = Invoke-Tank01 -Url $gamesUrl
            $playerGames = $gamesResponse.body
        } catch {
            Write-Warning "Error fetching games for $($pos): $_"
            $playerGames = @()
        }
    } else {
        Write-Warning "No Tank01 player found for $pos or missing playerID."
        $playerGames = @()
    }

    # Variable + JSON-Datei speichern
    Set-Variable -Name "Tank01PlayerGames$pos" -Value $playerGames -Scope Script

    $jsonPath = Join-Path $PSScriptRoot "Tank01PlayerGames$pos.json"
    $playerGames | ConvertTo-Json -Depth 10 | Out-File -Encoding UTF8 $jsonPath

    Write-Host "Saved games for $($pos): $jsonPath" -ForegroundColor Green
}


Write-Host "All JSON files saved successfully in script directory." -ForegroundColor Cyan
