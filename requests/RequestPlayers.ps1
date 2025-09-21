
# Konvertiere yyyyMMdd-String in DateTime
function Convert-StringToDate($dateStr) {
    [datetime]::ParseExact($dateStr, 'yyyyMMdd', $null)
}

# --- Tank01: DraftKings Salaries ---
function Get-DraftKings($dateStr) {
    Write-Host "Hole Tank01 DraftKings Salaries $dateStr..." -ForegroundColor Yellow
    $dfsUrl = "https://tank01-nfl-live-in-game-real-time-statistics-nfl.p.rapidapi.com/getNFLDFS?date=$dateStr"
    $dfsResponse = Invoke-RestMethod -Uri $dfsUrl -Headers $tankHeaders
    $draftKings = $dfsResponse.body.draftkings

    if ($draftKings.Count -eq 0) {
        Write-Host "Keine DraftKings Spieler gefunden, Datum um 1 Tag reduzieren..." -ForegroundColor Blue
        $prevDate = (Convert-StringToDate $dateStr).AddDays(-1).ToString("yyyyMMdd")
        return Get-DraftKings $prevDate  # rekursiver Aufruf
    }

    return $draftKings
}

# --- Konfiguration ---
$RapidAPIKey = "cccff76c4bmsh01946acbc2d3c0bp141721jsn161bd86f4c69"
$Date = (Get-Date -Format "yyyyMMdd")

# --- Sleeper: Spieler ---
Write-Host "Hole Sleeper Spieler..." -ForegroundColor Yellow
$sleeperPlayersUrl = "https://api.sleeper.app/v1/players/nfl"
$sleeperPlayers = Invoke-RestMethod -Uri $sleeperPlayersUrl
# hole das Array aus den sleeperPlayers (Key: Values)
$sleeperPlayers = $sleeperPlayers.PSObject.Properties.Value
Write-Host "Sleeper Spieler gefunden: $($sleeperPlayers.Count)" -ForegroundColor Yellow

# --- Tank01: Spieler ---
Write-Host "Hole Tank01 Spieler..." -ForegroundColor Yellow
$tankPlayersUrl = "https://tank01-nfl-live-in-game-real-time-statistics-nfl.p.rapidapi.com/getNFLPlayerList"
$tankHeaders = @{
    "X-RapidAPI-Key" = $RapidAPIKey
    "X-RapidAPI-Host" = "tank01-nfl-live-in-game-real-time-statistics-nfl.p.rapidapi.com"
}
$tankPlayersResponse = Invoke-RestMethod -Uri $tankPlayersUrl -Headers $tankHeaders
$tankPlayers = $tankPlayersResponse.body
Write-Host "Tank01 Spieler gefunden: $($tankPlayers.Count)" -ForegroundColor Yellow

# --- Tank01: DraftKings Salaries ---
Write-Host "Hole Tank01 DraftKings Salaries..." -ForegroundColor Yellow
$draftKings = Get-DraftKings '20250901' # $Date
Write-Host "DraftKings Spieler gefunden: $($draftKings.Count)" -ForegroundColor Yellow

# --- Spieler JSON vorbereiten (mit Tank01-Daten + Salary) ---
Write-Host "Erstelle Players.json..." -ForegroundColor Yellow

# Hashtable für schnellen Lookup vorbereiten (O(1) Zugriffe)
$sleeperLookup = @{}
foreach ($sleeper in $sleeperPlayers) {
    $sleeperLookup[$sleeper.player_id] = $sleeper
}
$draftKingsLookup = @{}
foreach ($draftKings in $draftKings) {
    $draftKingsLookup[$draftKings.playerID] = $draftKings
}

$playerData = @()
foreach ($tankEntry in $tankPlayers) {

    # Sleeper-Info direkt aus Hashtable ziehen
    if (-not $tankEntry.sleeperBotID) { continue }
    $sleeperEntry = $sleeperLookup[$tankEntry.sleeperBotID]
    if (-not $sleeperEntry) { continue }

    # nur TE, QB, RB, WR, K aufnehmen
    if ($sleeperEntry.position -notin @("TE", "QB", "RB", "WR", "K")) { continue }

    # DFS Info
    $salary = 0
    $dfsEntry = $draftKingsLookup[$tankEntry.playerID]
    $salary = if ($dfsEntry) { $dfsEntry.salary } else { 0 }

    $playerData += [PSCustomObject]@{
        ID      = $sleeperEntry.player_id
        TankID      = $tankEntry.playerID
        Name    = $sleeperEntry.full_name
        NameFirst    = $sleeperEntry.first_name
        NameLast    = $sleeperEntry.last_name
        NameShort    = $tankEntry.cbsShortName
        Status  = $sleeperEntry.status
        Position = $sleeperEntry.position
        Age     = $sleeperEntry.age
        Year = $sleeperEntry.years_exp + 1
        Salary  = $salary
        TeamID  = $tankEntry.teamID
        Number  = $tankEntry.jerseyNum
        Picture = $tankEntry.espnHeadshot
    }
}

# Verzeichnis des Skripts
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Ziel-Datei im data-Ordner parallel zum Requests-Ordner
$targetFile = Join-Path $scriptDir "..\data\Players.json"

# JSON schreiben
$playerData | ConvertTo-Json -Depth 5 | Out-File $targetFile -Encoding UTF8
Write-Host "Players.json gespeichert!" -ForegroundColor Green
