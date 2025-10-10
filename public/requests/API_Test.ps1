# ==========================
# Sleeper API Test Script
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
    Write-Host "League retrieved successfully." -ForegroundColor Green
} catch {
    Write-Error "Error retrieving league: $_"
    exit 1
}

Write-Host "`n--- League Fields ---" -ForegroundColor Cyan
$league | Format-List *


# --- Sleeper: Mitglieder + Rosters abrufen ---
try {
    Write-Host "`nFetching Sleeper League Members..." -ForegroundColor Yellow
    $membersUrl = "https://api.sleeper.app/v1/league/$LeagueID/users"
    $members    = Invoke-RestMethod -Uri $membersUrl -ErrorAction Stop
    Write-Host "Members retrieved successfully: $($members.Count)" -ForegroundColor Green

    Write-Host "`nFetching Sleeper League Rosters..." -ForegroundColor Yellow
    $rostersUrl = "https://api.sleeper.app/v1/league/$LeagueID/rosters"
    $rosters    = Invoke-RestMethod -Uri $rostersUrl -ErrorAction Stop
    Write-Host "Rosters retrieved successfully: $($rosters.Count)" -ForegroundColor Green
} catch {
    Write-Error "Error retrieving members/rosters: $_"
    exit 1
}

# --- Alle Felder von Mitgliedern anzeigen ---
Write-Host "`n--- Members Fields ---" -ForegroundColor Cyan
foreach ($member in $members) {
    Write-Host "`nMember ID: $($member.user_id)" -ForegroundColor DarkCyan
    $member | Format-List *
}

# --- Alle Felder von Rostern anzeigen ---
Write-Host "`n--- Rosters Fields ---" -ForegroundColor Cyan
foreach ($roster in $rosters) {
    Write-Host "`nRoster ID: $($roster.roster_id)" -ForegroundColor DarkMagenta
    $roster | Format-List *
}

Write-Host "`nSleeper API Test Completed." -ForegroundColor Green




# ================================
# Tank01 Player & DraftKings Test
# ================================

# --- Konfiguration laden ---
. "$PSScriptRoot\config.ps1"
if (-not $Global:RapidAPIKeyAlt1) {
    Write-Error "Tank01ApiKey not set in config.ps1!"
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

# --- 1. Alle Spieler abrufen ---
Write-Host "Fetching all players from Tank01..." -ForegroundColor Yellow
$playerListUrl = "https://$apiHost/getNFLPlayerList"
try {
    $playerListResponse = Invoke-Tank01 -Url $playerListUrl
} catch {
    Write-Error "Error fetching player list: $_"
    exit 1
}

# Annahme: Spieler sind in .body
$allPlayers = $playerListResponse.body
if (-not $allPlayers) {
    Write-Error "No players returned from Tank01."
    exit 1
}
Write-Host "Number of players retrieved: $($allPlayers.Count)" -ForegroundColor Green

# --- 2. Suche Spieler, der kein Free Agent ist ---
$nonFree = $allPlayers | Where-Object { $_.isFreeAgent -eq $false }
if (-not $nonFree -or $nonFree.Count -eq 0) {
    Write-Warning "Kein Spieler mit isFreeAgent = false gefunden. Fallback auf beliebigen Spieler."
    $samplePlayer = $allPlayers | Select-Object -First 1
} else {
    $samplePlayer = $nonFree | Select-Object -First 1
}


# --- 2. DraftKings / DFS Daten abrufen ---
# Beispiel-Datum – du kannst das dynamisch machen
# $dfsDate = "20251010"  # yyyyMMdd
$dfsDate = (Get-Date).ToString("yyyyMMdd")
Write-Host "`nFetching DraftKings/DFS data for date $dfsDate..." -ForegroundColor Yellow
$dfsUrl = "https://$apiHost/getNFLDFS?date=$dfsDate"
try {
    $dfsResponse = Invoke-Tank01 -Url $dfsUrl
} catch {
    Write-Error "Error fetching DFS data: $_"
    exit 1
}

# Annahme: Daten liegen in .body.draftkings
$dkPlayers = $dfsResponse.body.draftkings
if (-not $dkPlayers) {
    Write-Error "No DraftKings data returned."
    exit 1
}
Write-Host "Number of DFS players retrieved: $($dkPlayers.Count)" -ForegroundColor Green

# --- 4. Spieler mit Salary > 5000 suchen ---
$dkPlayerHighSalary = $dkPlayers | Where-Object { $_.salary -gt 5000 } | Select-Object -First 1
if (-not $dkPlayerHighSalary) {
    Write-Warning "Kein DraftKings-Spieler mit Salary > 5000 gefunden. Fallback auf ersten Spieler."
    $dkPlayerHighSalary = $dkPlayers | Select-Object -First 1
}



# ==========================================================
# --- 3️⃣ Sleeper Spieler aus deiner Liga ---
# ==========================================================

Write-Host "`nFetching Sleeper players..." -ForegroundColor Yellow

try {
    $sleeperPlayersUrl = "https://api.sleeper.app/v1/players/nfl"
    $sleeperPlayers = Invoke-RestMethod -Uri $sleeperPlayersUrl
    $sleeperPlayersArray = $sleeperPlayers.PSObject.Properties.Value
} catch {
    Write-Error "Error fetching Sleeper rosters: $_"
    exit 1
}

if (-not $sleeperPlayers -or $sleeperPlayers.Count -eq 0) {
    Write-Error "No Sleeper rosters returned."
    exit 1
}

#$sleeperPlayersArray = $sleeperPlayers.Values
Write-Host "Number of Sleeper players retrieved: $($sleeperPlayersArray.Count)" -ForegroundColor Green

# Ersten Starter des ersten Rosters
$starterID = $rosters[0].starters[0]

# Player-Objekt suchen
$sleeperPlayer = $sleeperPlayersArray | Where-Object { $_.player_id -eq $starterID } | Select-Object -First 1

if (-not $sleeperPlayer) {
    Write-Warning "No player found in first Sleeper roster."
}


# ==========================================================
# --- Zusammenfassung ---
# ==========================================================
Write-Host "`n=== Summary ===" -ForegroundColor Green
Write-Host "Tank01 Player:"
$samplePlayer | Format-List *
Write-Host "DraftKings Player:"
$dkPlayerHighSalary | Format-List *
Write-Host "Sleeper Player:"
$sleeperPlayer | Format-List *


Write-Host "`nTest complete." -ForegroundColor Green