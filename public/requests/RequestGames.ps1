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


# --- Helper: Compare two objects by canonical JSON (order-insensitive-ish for arrays/dicts) ---
function ObjectsAreEqualByJson {
    param($a, $b)
    # If both null/empty -> equal
    if (-not $a -and -not $b) { return $true }

    try {
        $jsonA = $a | ConvertTo-Json -Depth 20
        $jsonB = $b | ConvertTo-Json -Depth 20
        return ($jsonA -eq $jsonB)
    } catch {
        # Fallback: compare string conversion
        return ("$a" -eq "$b")
    }
}


# ===================================================================
# Fetch Schedule + BoxScores (uses Invoke-Tank01-With-Fallback from your example)
# Saves: Schedule.json, Games.json, Timestamps.json
# ===================================================================

# --- Config / reuse existing variables ---
. "$PSScriptRoot\config.ps1"

# apiKeys must be available in config.ps1 as in your other script
$apiKeys = @(
    $Global:RapidAPIKey,
    $Global:RapidAPIKeyAlt1,
    $Global:RapidAPIKeyAlt2
)

$apiHost = "tank01-nfl-live-in-game-real-time-statistics-nfl.p.rapidapi.com"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$dataDir = Join-Path $scriptDir "..\data"
if (-not (Test-Path $dataDir)) { New-Item -ItemType Directory -Path $dataDir -Force | Out-Null }


# current time
$currentTime = (Get-Date).ToUniversalTime()


$scheduleFile = Join-Path $dataDir "Schedule.json"
$gamesFile    = Join-Path $dataDir "Games.json"
$backupDir    = Join-Path $dataDir "backup"
if (-not (Test-Path $backupDir)) { New-Item -ItemType Directory -Path $backupDir -Force | Out-Null }

$timestampFile = Join-Path $dataDir "Timestamps.json"
$boxScoreWaitSeconds = 1  # Wartezeit zwischen BoxScore-Requests (anpassbar)

# --- Fetch schedule from Tank01 ---
Write-Host "Fetching full schedule (week=all, seasonType=reg)..." -ForegroundColor Yellow
$scheduleUrl = "https://$apiHost/getNFLGamesForWeek?week=all&seasonType=reg"
try {
    $scheduleResp = Invoke-Tank01-With-Fallback -Url $scheduleUrl -Keys $apiKeys
    $schedule = $scheduleResp.body
} catch {
    Write-Error "Error fetching schedule: $_"
    exit 1
}
if (-not $schedule) {
    Write-Error "No schedule returned."
    exit 1
}

Write-Host "Schedule retrieved, total games: $($schedule.Count)" -ForegroundColor Green

# --- Load old schedule if present ---
$oldSchedule = $null
if (Test-Path $scheduleFile) {
    try {
        $oldScheduleRaw = Get-Content $scheduleFile -Raw
        if ($oldScheduleRaw) { $oldSchedule = $oldScheduleRaw | ConvertFrom-Json }
    } catch {
        Write-Warning "Could not read existing Schedule.json: $_"
        $oldSchedule = $null
    }
}

# --- Compare and save Schedule.json only if changed ---
if (ObjectsAreEqualByJson $oldSchedule $schedule) {
    Write-Host "Schedule unchanged. Skipping Schedule.json update." -ForegroundColor Cyan
} else {
    # Backup old schedule
    if (Test-Path $scheduleFile) {
        $ts = $currentTime.ToString("yyyyMMdd_HHmmss")
        Copy-Item $scheduleFile -Destination (Join-Path $backupDir "Schedule_$ts.json") -Force
        Write-Host "Old Schedule.json backed up." -ForegroundColor DarkGray
    }

    # Save new schedule (keep full fields)
    try {
        $schedule | ConvertTo-Json -Depth 20 | Out-File -FilePath $scheduleFile -Encoding UTF8
        Write-Host "Schedule.json saved." -ForegroundColor Green
        # update timestamp
        if (Test-Path $timestampFile) { $timestamps = Get-Content $timestampFile | ConvertFrom-Json } else { $timestamps = @{} }
        $timestamps.Schedule = $currentTime.ToString("yyyy-MM-ddTHH:mm:ssZ")
        $timestamps | ConvertTo-Json -Depth 5 | Set-Content $timestampFile
        Write-Host "Schedule timestamp updated." -ForegroundColor Green
    } catch {
        Write-Error "Error writing Schedule.json: $_"
        exit 1
    }
}

# --- Determine which weeks are closed (all games final) ---
$weeksClosed = @{}

# Gruppiere nach Week und prüfe, ob alle Spiele mit "Final" beginnen
foreach ($weekGroup in ($schedule | Group-Object -Property gameWeek)) {
    $week = $weekGroup.Name
    $allFinal = $true
    foreach ($g in $weekGroup.Group) {
        if ($g.gameStatus -notmatch '^Final') {
            $allFinal = $false
            break
        }
    }
    $weeksClosed[$week] = $allFinal
    if($allFinal){
        Write-Host "$($week) marked as all final" -ForegroundColor Cyan
    }
}


# --- Load existing Games.json (list of game objects) ---
$games = @()
if (Test-Path $gamesFile) {
    try {
        $gamesRaw = Get-Content $gamesFile -Raw
        if ($gamesRaw) {
            $games = $gamesRaw | ConvertFrom-Json
            if (-not ($games -is [System.Collections.IEnumerable])) {
                $games = @($games)
            }
        }
    } catch {
        Write-Warning "Could not read existing Games.json: $_"
        $games = @()
    }
}

# --- Iterate schedule; for games with gameStatus containing "Final" that are not in $games or do not have snapCounts, fetch boxscore ---
$addedCount = 0
$updatedCount = 0
foreach ($g in $schedule) {
    
    $added = $false
    $updated = $false

    # safeguard: ensure gameID exists
    if (-not $g.gameID) { continue }
    $gameID = $g.gameID

    # Check if status contains "Final" (case-insensitive)
    $status = $g.gameStatus
    if (-not $status) { continue }
    if ($status -imatch "Final") {

        # try get matching game
        $matchingGame = $games | Where-Object { $_.gameID -eq $g.gameID }
        $snapsMissing = $false

        if($matchingGame) {
            if(
                $matchingGame.playerStats.PSObject.Properties.Value |
                Where-Object { -not ($_.PSObject.Properties.Name -contains 'snapCounts') }
            ) {
                $snapsMissing = $true
                Write-Host "No Snap Counts for '$($gameID)'..." -ForegroundColor Yellow
            }
        } else {
            Write-Host "No Game Score for '$($gameID)'..." -ForegroundColor Yellow
        }        

        # If not yet present in games or no snapCounts -> fetch
        if (-not $matchingGame -or $snapsMissing
        )  {
            
            Write-Host "Fetching Game Score for '$($gameID)'..." -ForegroundColor Yellow

            $gameIDEncoded = [uri]::EscapeDataString($gameID)
            $boxScoresUrl = "https://$apiHost/getNFLBoxScore?gameID=$gameIDEncoded&playByPlay=false&fantasyPoints=true"

            try {
                $bscoreResponse = Invoke-Tank01-With-Fallback -Url $boxScoresUrl -Keys $apiKeys
                $boxScore = $bscoreResponse.body

                if ($boxScore) {
                    # Convert to PSCustomObject only at the end
                    $boxObj = $boxScore | ConvertTo-Json -Depth 10 | ConvertFrom-Json

                    # Prüfen, ob nach Fetch noch Spieler ohne snapCounts existieren
                    $missingSnapsFetched = @()
                    foreach ($playerProp in $boxObj.playerStats.PSObject.Properties) {
                        $player = $playerProp.Value
                        if (-not $player.snapCounts) {
                            # Spieler-ID und Name speichern
                            $missingSnapsFetched += $player
                            Write-Host "  -> Player missing snapCounts: $($player.playerID) - $($player.longName)" -ForegroundColor Gray
                        }
                    }

                    # Wenn es Spieler ohne snapCounts gibt und das Spiel vorher schon existierte, nicht überschreiben
                    if ($missingSnapsFetched.Count -gt 0 -and $matchingGame) {
                        Write-Host "  -> Fetched game still has players without snapCounts. Existing game is kept." 
                    } else {
                        # Spiel anhand der ID finden
                        $index = [array]::IndexOf(($games | ForEach-Object { $_.gameID }), $gameID)

                        if ($index -ge 0) {
                            $games[$index] = $boxObj
                            Write-Host "  -> Updated existing Game Score for $gameID" -ForegroundColor Yellow
                            $updated = $true
                        } else {
                            $games += $boxObj
                            Write-Host "  -> Game Score saved for $gameID" -ForegroundColor Green
                            $added = $true
                        }
                    }
                } else {
                    Write-Warning "  -> No boxScore.body returned for $gameID"
                }
            } catch {
                Write-Warning "  -> Error fetching boxscore for $($gameID): $_"
            }

            # short sleep to avoid rapid-fire requests; adjust $boxScoreWaitSeconds as needed
            Start-Sleep -Seconds $boxScoreWaitSeconds
        } else {
            Write-Host "Game $($g.gameID) already present in Games.json - skipping." -ForegroundColor DarkGray
        }

        # --- check & update weekFinal flag ---
        # try get matching game (safeguard, game should exist)
        $matchingGame = $games | Where-Object { $_.gameID -eq $g.gameID }
        if($matchingGame) {
            
            if ($matchingGame.gameWeek -and $weeksClosed.ContainsKey($matchingGame.gameWeek)) {
                $newValue = [bool]$weeksClosed[$matchingGame.gameWeek]
            } else {
                $newValue = $false
            }

            # Prüfen, ob das Property existiert
            if ($matchingGame.PSObject.Properties.Name -contains 'weekFinal') {
                $oldValue = [bool]$matchingGame.weekFinal
                if ($oldValue -ne $newValue) {
                    $matchingGame.weekFinal = $newValue
                    Write-Host "Updated weekFinal for $($matchingGame.gameID): $oldValue -> $newValue" -ForegroundColor Yellow
                    $updated = $true
                }
            } else {
                # Erstmaliges Hinzufügen
                $matchingGame | Add-Member -NotePropertyName "weekFinal" -NotePropertyValue $newValue
                Write-Host "Added weekFinal for $($matchingGame.gameID): $newValue" -ForegroundColor Yellow
                $added = $true
            }
        }  

    } # end if status Final

    if($added) { $addedCount++ }
    if($updated) { $updatedCount++ }

} # end foreach schedule


# --- Duplikate und leere SnapCounts entfernen ---
Write-Host "Cleaning up duplicate games and entries without snapCounts..." -ForegroundColor Yellow

$beforeCount = $games.Count

# --- Duplikate nach gameID entfernen ---
$games = $games | Group-Object -Property gameID | ForEach-Object {
    $group = $_.Group

    # Bevorzuge Spielversionen, bei denen alle Spieler snapCounts haben
    $validGames = $group | Where-Object {
        ($_.playerStats.PSObject.Properties.Value | Where-Object { -not $_.snapCounts }).Count -eq 0
    }

    if ($validGames) {
        $validGames | Select-Object -First 1
    } else {
        # Wenn keine Version vollständig ist, nimm die erste
        $group | Select-Object -First 1
    }
}

$afterCount = $games.Count
$diff = $beforeCount - $afterCount

Write-Host "Cleanup complete:" -ForegroundColor Cyan
Write-Host "  - Original games: $beforeCount"
Write-Host "  - Remaining games: $afterCount"
Write-Host "  - Removed games: $diff" -ForegroundColor Cyan


# --- Sortierung, neuestes Spiel oben auf
$games = $games | Sort-Object gameID -Descending

# --- If any new games were added -> write Games.json + update timestamp (and backup previous) ---
if ($addedCount -gt 0 -or $updatedCount -gt 0 -or $diff -gt 0) {
    # Backup old Games.json
    if (Test-Path $gamesFile) {
        $ts = $currentTime.ToString("yyyyMMdd_HHmmss")
        Copy-Item $gamesFile -Destination (Join-Path $backupDir "Games_$ts.json") -Force
        Write-Host "Old Games.json backed up." -ForegroundColor DarkGray
    }

    # Save new games
    try {
        $games | ConvertTo-Json -Depth 20 | Out-File -FilePath $gamesFile -Encoding UTF8
        Write-Host "Games.json updated with $($addedCount+$updatedCount) new or updated game(s)." -ForegroundColor Green

        # update timestamp
        if (Test-Path $timestampFile) { $timestamps = Get-Content $timestampFile | ConvertFrom-Json } else { $timestamps = @{} }
        $timestamps.Games = $currentTime.ToString("yyyy-MM-ddTHH:mm:ssZ")
        $timestamps | ConvertTo-Json -Depth 5 | Set-Content $timestampFile
        Write-Host "Games timestamp updated." -ForegroundColor Green
    } catch {
        Write-Error "Error writing Games.json: $_"
        exit 1
    }
} else {
    Write-Host "No new final games to add. Games.json unchanged." -ForegroundColor Cyan
}

Write-Host "Done. Added $addedCount new boxscore(s)." -ForegroundColor Green

