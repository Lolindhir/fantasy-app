# --- Funktionen ---
function Convert-StringToDate($dateStr) {
    [datetime]::ParseExact($dateStr, 'yyyyMMdd', $null)
}

function Get-DraftKings($dateStr) {
    Write-Host "Hole Tank01 DraftKings Salaries $dateStr..." -ForegroundColor Yellow
    $dfsUrl = "https://tank01-nfl-live-in-game-real-time-statistics-nfl.p.rapidapi.com/getNFLDFS?date=$dateStr"
    try {
        $dfsResponse = Invoke-RestMethod -Uri $dfsUrl -Headers $tankHeaders
    } catch {
        Write-Warning "Fehler beim Abrufen der DraftKings Daten: $_"
        return $null
    }

    $draftKings = $dfsResponse.body.draftkings
    if (-not $draftKings -or $draftKings.Count -eq 0) {
        Write-Host "Keine DraftKings Spieler gefunden, Datum um 1 Tag reduzieren..." -ForegroundColor Blue
        $prevDate = (Convert-StringToDate $dateStr).AddDays(-1).ToString("yyyyMMdd")
        return Get-DraftKings $prevDate
    }
    return $draftKings
}

# --- Konfiguration ---
$RapidAPIKey = "cccff76c4bmsh01946acbc2d3c0bp141721jsn161bd86f4c69"
$Date = (Get-Date -Format "yyyyMMdd")
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$targetFile = Join-Path $scriptDir "..\data\Players.json"
$backupDir = Join-Path $scriptDir "..\data\backup"
if (!(Test-Path $backupDir)) { New-Item -ItemType Directory -Path $backupDir -Force | Out-Null }

# --- Sleeper Spieler abrufen ---
Write-Host "Hole Sleeper Spieler..." -ForegroundColor Yellow
try {
    $sleeperPlayersUrl = "https://api.sleeper.app/v1/players/nfl"
    $sleeperPlayers = Invoke-RestMethod -Uri $sleeperPlayersUrl
    $sleeperPlayers = $sleeperPlayers.PSObject.Properties.Value
} catch {
    Write-Error "Fehler beim Abrufen der Sleeper Spieler: $_"
    exit 1
}
Write-Host "Sleeper Spieler gefunden: $($sleeperPlayers.Count)" -ForegroundColor Yellow

# --- Tank01 Spieler abrufen ---
Write-Host "Hole Tank01 Spieler..." -ForegroundColor Yellow
$tankPlayersUrl = "https://tank01-nfl-live-in-game-real-time-statistics-nfl.p.rapidapi.com/getNFLPlayerList"
$tankHeaders = @{
    "X-RapidAPI-Key" = $RapidAPIKey
    "X-RapidAPI-Host" = "tank01-nfl-live-in-game-real-time-statistics-nfl.p.rapidapi.com"
}
try {
    $tankPlayersResponse = Invoke-RestMethod -Uri $tankPlayersUrl -Headers $tankHeaders
    $tankPlayers = $tankPlayersResponse.body
} catch {
    Write-Error "Fehler beim Abrufen der Tank01 Spieler: $_"
    exit 1
}
Write-Host "Tank01 Spieler gefunden: $($tankPlayers.Count)" -ForegroundColor Yellow

# --- Tank01 DraftKings Salaries ---
Write-Host "Hole Tank01 DraftKings Salaries..." -ForegroundColor Yellow
$draftKings = Get-DraftKings $Date
if (-not $draftKings) {
    Write-Error "DraftKings Daten konnten nicht abgerufen werden, Abbruch."
    exit 1
}
Write-Host "DraftKings Spieler gefunden: $($draftKings.Count)" -ForegroundColor Yellow

# --- Spieler JSON vorbereiten ---
Write-Host "Erstelle Players.json..." -ForegroundColor Yellow
$sleeperLookup = @{}
foreach ($sleeper in $sleeperPlayers) { $sleeperLookup[$sleeper.player_id] = $sleeper }

$draftKingsLookup = @{}
foreach ($dk in $draftKings) { $draftKingsLookup[$dk.playerID] = $dk }

$playerData = @()
foreach ($tankEntry in $tankPlayers) {
    if (-not $tankEntry.sleeperBotID) { continue }
    $sleeperEntry = $sleeperLookup[$tankEntry.sleeperBotID]
    if (-not $sleeperEntry) { continue }
    if ($sleeperEntry.position -notin @("TE","QB","RB","WR","K")) { continue }

    $dfsEntry = $draftKingsLookup[$tankEntry.playerID]
    $salary = if ($dfsEntry) { $dfsEntry.salary } else { 0 }

    $playerData += [PSCustomObject]@{
        ID = $sleeperEntry.player_id
        TankID = $tankEntry.playerID
        Name = $sleeperEntry.full_name
        NameFirst = $sleeperEntry.first_name
        NameLast = $sleeperEntry.last_name
        NameShort = $tankEntry.cbsShortName
        Status = $sleeperEntry.status
        Position = $sleeperEntry.position
        Age = $sleeperEntry.age
        Year = $sleeperEntry.years_exp + 1
        Salary = $salary
        TeamID = $tankEntry.teamID
        Number = $tankEntry.jerseyNum
        Picture = $tankEntry.espnHeadshot
    }
}

$TimeSnapshot = (Get-Date)

# --- Backup alte Datei ---
if (Test-Path $targetFile) {
    $timestamp = $TimeSnapshot.ToUniversalTime().ToString("yyyyMMdd_HHmmss")
    Copy-Item $targetFile -Destination (Join-Path $backupDir "Players-$timestamp.json") -Force
    Write-Host "Backup der alten Players.json erstellt." -ForegroundColor Green
}

# --- JSON schreiben ---
try {
    $playerData | ConvertTo-Json -Depth 5 | Out-File $targetFile -Encoding UTF8
    Write-Host "Players.json gespeichert!" -ForegroundColor Green
} catch {
    Write-Error "Fehler beim Schreiben der Players.json: $_"
    exit 1
}

# --- Timestamp aktualisieren ---
$TimestampFile = Join-Path $scriptDir "..\data\Timestamps.json"
$Now = $TimeSnapshot.ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
if (Test-Path $TimestampFile) {
    $Timestamps = Get-Content $TimestampFile | ConvertFrom-Json
} else { $Timestamps = @{} }
$Timestamps.Players = $Now
$Timestamps | ConvertTo-Json -Depth 3 | Set-Content $TimestampFile
Write-Host "Players-Timestamp aktualisiert: $Now" -ForegroundColor Green
