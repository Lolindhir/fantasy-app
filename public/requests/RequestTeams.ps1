
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

function TeamsHaveChanged($oldTeams, $newTeams) {
    if (-not $oldTeams) { return $true }  # keine alte Daten -> Änderung

    # Prüfe Anzahl der Teams
    if ($oldTeams.Count -ne $newTeams.Count) {
        Write-Host "Team count changed: $($oldTeams.Count) -> $($newTeams.Count)"
        return $true
    }

    # Prüfe jedes Team
    for ($i = 0; $i -lt $oldTeams.Count; $i++) {
        $oldTeam = $oldTeams[$i]
        $newTeam = $newTeams[$i]

        # Prüfe Top-Level Eigenschaften des Teams
        $propsToCheck = @('ID','Name','Abv','City','Logo','Conference','ConferenceAbv','Division')
        foreach ($prop in $propsToCheck) {
            if ($oldTeam.$prop -ne $newTeam.$prop) {
                Write-Host "Team '$($oldTeam.Name)' property '$prop' changed: '$($oldTeam.$prop)' -> '$($newTeam.$prop)'"
                return $true
            }
        }
    }

    # Keine Änderungen gefunden
    return $false
}


# Zuerst die Konfiguration einbinden
. "$PSScriptRoot\config.ps1"
# --- Konfiguration ---
# Keys als Liste definieren
$apiKeys = @(
    $Global:RapidAPIKey,
    $Global:RapidAPIKeyAlt1
    # , $Global:RapidAPIKeyAlt2  # falls Weiteren vorhanden sind
)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$targetFile = Join-Path $scriptDir "..\data\Teams.json"
$backupDir = Join-Path $scriptDir "..\data\backup"
if (!(Test-Path $backupDir)) { New-Item -ItemType Directory -Path $backupDir -Force | Out-Null }

# --- Tank01: Teams abrufen ---
Write-Host "Fetch teams..." -ForegroundColor Yellow
$tankTeamsUrl = "https://tank01-nfl-live-in-game-real-time-statistics-nfl.p.rapidapi.com/getNFLTeams"
try {
    $tankTeamsResponse = Invoke-Tank01-With-Fallback -Url $tankTeamsUrl -Keys $apiKeys
    $tankTeams = $tankTeamsResponse.body
} catch {
    Write-Error "Error fetching teams: $_"
    exit 1
}

Write-Host "Teams found: $($tankTeams.Count)" -ForegroundColor Yellow

# --- Team JSON vorbereiten ---
Write-Host "Creating Teams.json..." -ForegroundColor Yellow
$teamData = @()
foreach ($tankEntry in $tankTeams) {
    $teamData += [PSCustomObject]@{
        ID      = $tankEntry.teamID
        Name    = $tankEntry.teamName
        Abv     = $tankEntry.teamAbv
        City    = $tankEntry.teamCity
        Logo    = $tankEntry.nflComLogo1
        Conference = $tankEntry.conference
        ConferenceAbv = $tankEntry.conferenceAbv
        Division = $tankEntry.division
    }
}

# Änderungen prüfen
# alte JSON laden
$oldTeams = $null
if (Test-Path $targetFile) {
    $oldJsonRaw = Get-Content $targetFile -Raw
    if ($oldJsonRaw) { $oldTeams = ($oldJsonRaw | ConvertFrom-Json) }
}

# neue JSON erzeugen
$newTeams = $teamData

# Änderungen prüfen
if (TeamsHaveChanged $oldTeams $newTeams) {
    Write-Host "Changes detected - updating file." -ForegroundColor Green
# Backup + Schreiben + Timestamp + Exit 0
}
else {
    Write-Host "No changes - update skipped." -ForegroundColor Cyan
    exit 2
}


# --- Zeitstempel ---
$TimeSnapshot = (Get-Date)

# --- Backup alte Datei ---
if (Test-Path $targetFile) {
    $timestamp = $TimeSnapshot.ToUniversalTime().ToString("yyyyMMdd_HHmmss")
    Copy-Item $targetFile -Destination (Join-Path $backupDir "Teams_$timestamp.json") -Force
    Write-Host "Backup of old Teams.json created." -ForegroundColor Green
}

# --- JSON schreiben ---
try {
    $teamData | ConvertTo-Json -Depth 5 | Out-File $targetFile -Encoding UTF8
    Write-Host "Teams.json saved!" -ForegroundColor Green
} catch {
    Write-Error "Error writing Teams.json: $_"
    exit 1
}

# --- Timestamp aktualisieren ---
$TimestampFile = Join-Path $scriptDir "..\data\Timestamps.json"
$Now = $TimeSnapshot.ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
if (Test-Path $TimestampFile) {
    $Timestamps = Get-Content $TimestampFile | ConvertFrom-Json
} else {
    $Timestamps = @{}
}
$Timestamps.Teams = $Now
$Timestamps | ConvertTo-Json -Depth 3 | Set-Content $TimestampFile
Write-Host "Teams-Timestamp updated: $Now" -ForegroundColor Green
