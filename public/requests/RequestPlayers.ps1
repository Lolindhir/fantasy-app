# --- Funktionen ---
# Globale Variable für den zuletzt erfolgreichen Key
$Global:CurrentApiKey = $null
function Invoke-Tank01-With-Fallback {
    param(
        [string]$Url,
        [string[]]$Keys
    )

    $delay = 2  # Start-Wartezeit in Sekunden

    # Wenn bereits ein funktionierender Key gespeichert ist, probiere diesen zuerst
    if ($Global:CurrentApiKey -and $Keys -contains $Global:CurrentApiKey) {
        $headers = @{
            "X-RapidAPI-Key" = $Global:CurrentApiKey
            "X-RapidAPI-Host" = "tank01-nfl-live-in-game-real-time-statistics-nfl.p.rapidapi.com"
        }
        try {
            Write-Host "  Using cached key: $($Global:CurrentApiKey)" -ForegroundColor DarkGray
            return Invoke-RestMethod -Uri $Url -Headers $headers -ErrorAction Stop
        } catch {
            $statusCode = $_.Exception.Response.StatusCode.Value__
            if ($statusCode -eq 429) {
                Write-Warning "Cached key $($Global:CurrentApiKey) hit 429 - switching..."
                # Reset Key, nächster Versuch mit allen Keys
                $Global:CurrentApiKey = $null
            } else {
                throw $_
            }
        }
    }

    # Normale Fallback-Logik (alle Keys durchprobieren)
    foreach ($key in $Keys) {
        $headers = @{
            "X-RapidAPI-Key" = $key
            "X-RapidAPI-Host" = "tank01-nfl-live-in-game-real-time-statistics-nfl.p.rapidapi.com"
        }

        try {
            Write-Host "  Try with key: $key" -ForegroundColor DarkGray
            $result = Invoke-RestMethod -Uri $Url -Headers $headers -ErrorAction Stop
            # Wenn erfolgreich: Key merken
            $Global:CurrentApiKey = $key
            return $result
        } catch {
            $statusCode = $_.Exception.Response.StatusCode.Value__
            if ($statusCode -eq 429) {
                Write-Warning "429 Too Many Requests - wait $delay sec before next key..."
                Start-Sleep -Seconds $delay
                $delay = [Math]::Min($delay * 2, 30)
                continue
            } else {
                throw $_
            }
        }
    }

    throw "All API keys have failed (including 429 errors)."
}

function PlayersHaveChanged($oldPlayers, $newPlayers) {
    if (-not $oldPlayers) { return $true }

    if ($oldPlayers.Count -ne $newPlayers.Count) {
        Write-Host "Player count changed: $($oldPlayers.Count) -> $($newPlayers.Count)"
        return $true
    }

    for ($i = 0; $i -lt $oldPlayers.Count; $i++) {
        $old = $oldPlayers[$i]
        $new = $newPlayers[$i]

        $propsToCheck = @('ID','TankID','Name','NameFirst','NameLast','NameShort','Status','Position','Age','Year','Salary','TeamID','Number','Picture')
        foreach ($prop in $propsToCheck) {
            if ($old.$prop -ne $new.$prop) {
                Write-Host "Player property '$prop' changed: '$($old.$prop)' -> '$($new.$prop)'"
                return $true
            }
        }
    }

    return $false
}

function Convert-StringToDate($dateStr) {
    [datetime]::ParseExact($dateStr, 'yyyyMMdd', $null)
}

function Get-DraftKings($dateStr, $apiKeys) {
    Write-Host "Fetch Tank01 DraftKings salaries $dateStr..." -ForegroundColor Yellow
    $dfsUrl = "https://tank01-nfl-live-in-game-real-time-statistics-nfl.p.rapidapi.com/getNFLDFS?date=$dateStr"
    try {
        $dfsResponse = Invoke-Tank01-With-Fallback -Url $dfsUrl -Keys $apiKeys
    } catch {
        Write-Warning "Error fetching DraftKings data: $_"
        return $null
    }

    $draftKings = $dfsResponse.body.draftkings
    if (-not $draftKings -or $draftKings.Count -eq 0) {
        Write-Host "No DraftKings players found, reducing date by 1 day..." -ForegroundColor Blue
        $prevDate = (Convert-StringToDate $dateStr).AddDays(-1).ToString("yyyyMMdd")
        return Get-DraftKings $prevDate $apiKeys
    }
    return $draftKings
}

# --- Konfiguration ---
. "$PSScriptRoot\config.ps1"
$apiKeys = @(
    $Global:RapidAPIKey,
    $Global:RapidAPIKeyAlt1
    # , $Global:RapidAPIKeyAlt2
)
$Date = (Get-Date -Format "yyyyMMdd")
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$targetFile = Join-Path $scriptDir "..\data\Players.json"
$backupDir = Join-Path $scriptDir "..\data\backup"
if (!(Test-Path $backupDir)) { New-Item -ItemType Directory -Path $backupDir -Force | Out-Null }

# --- Sleeper Spieler abrufen ---
Write-Host "Fetch Sleeper players..." -ForegroundColor Yellow
try {
    $sleeperPlayersUrl = "https://api.sleeper.app/v1/players/nfl"
    $sleeperPlayers = Invoke-RestMethod -Uri $sleeperPlayersUrl
    $sleeperPlayers = $sleeperPlayers.PSObject.Properties.Value
} catch {
    Write-Error "Error fetching Sleeper players: $_"
    exit 1
}
Write-Host "Sleeper players found: $($sleeperPlayers.Count)" -ForegroundColor Yellow

# --- Tank01 Spieler ---
Write-Host "Fetch Tank01 players..." -ForegroundColor Yellow
$tankPlayersUrl = "https://tank01-nfl-live-in-game-real-time-statistics-nfl.p.rapidapi.com/getNFLPlayerList"
try {
    $tankPlayersResponse = Invoke-Tank01-With-Fallback -Url $tankPlayersUrl -Keys $apiKeys
    $tankPlayers = $tankPlayersResponse.body
} catch {
    Write-Error "Error fetching Tank01 players: $_"
    exit 1
}
Write-Host "Tank01 players found: $($tankPlayers.Count)" -ForegroundColor Yellow

# --- DraftKings Salaries ---
Write-Host "Fetch Tank01 DraftKings Salaries..." -ForegroundColor Yellow
$draftKings = Get-DraftKings $Date $apiKeys
if (-not $draftKings) {
    Write-Error "Error fetching DraftKings data: $_"
    exit 1
}
Write-Host "DraftKings players found: $($draftKings.Count)" -ForegroundColor Yellow


# --- Spieler JSON vorbereiten ---
Write-Host "Creating Players.json..." -ForegroundColor Yellow
$sleeperLookup = @{}
foreach ($sleeper in $sleeperPlayers) { $sleeperLookup[$sleeper.player_id] = $sleeper }

$draftKingsLookup = @{}
foreach ($dk in $draftKings) { $draftKingsLookup[$dk.playerID] = $dk }


# Alte Spieler laden (für Vergleich und evtl. Gehälter)
$oldPlayers = $null
if (Test-Path $targetFile) {
    $oldJsonRaw = Get-Content $targetFile -Raw
    if ($oldJsonRaw) { $oldPlayers = ($oldJsonRaw | ConvertFrom-Json) }
}

$playerData = @()
foreach ($tankEntry in $tankPlayers) {
    if (-not $tankEntry.sleeperBotID) { continue }
    $sleeperEntry = $sleeperLookup[$tankEntry.sleeperBotID]
    if (-not $sleeperEntry) { continue }
    if ($sleeperEntry.position -notin @("TE","QB","RB","WR","K")) { continue }

    $dfsEntry = $draftKingsLookup[$tankEntry.playerID]
    $salary = if ($dfsEntry) { $dfsEntry.salary } else { 0 }

    # --- Neue Prüfung für alten Salary ---
    if ($salary -eq 0 -and $oldPlayers) {
        $oldPlayer = $oldPlayers | Where-Object { $_.ID -eq $sleeperEntry.player_id }
        if ($oldPlayer -and $oldPlayer.Salary -gt 0) {
            $salary = $oldPlayer.Salary
            Write-Host "  Using old salary for $($sleeperEntry.full_name): $($salary)" -ForegroundColor DarkGray
        }
    }

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

# Änderungen prüfen
if (-not (PlayersHaveChanged $oldPlayers $playerData)) {
    Write-Host "No changes - update skipped." -ForegroundColor Cyan
    exit 2
}

# --- Zeitstempel ---
$TimeSnapshot = (Get-Date)

# --- Backup alte Datei ---
if (Test-Path $targetFile) {
    $timestamp = $TimeSnapshot.ToUniversalTime().ToString("yyyyMMdd_HHmmss")
    Copy-Item $targetFile -Destination (Join-Path $backupDir "Players_$timestamp.json") -Force
    Write-Host "Old Players.json backup created." -ForegroundColor Green
}

# --- JSON schreiben ---
try {
    $playerData | ConvertTo-Json -Depth 5 | Out-File $targetFile -Encoding UTF8
    Write-Host "Players.json saved!" -ForegroundColor Green
} catch {
    Write-Error "Error writing Players.json: $_"
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
Write-Host "Players-Timestamp updated: $Now" -ForegroundColor Green
