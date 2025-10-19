param (
    [Parameter(Mandatory = $true)]
    [string]$year
)

# --- Validierung des Jahres ---
if ($year -notmatch '^\d{4}$') {
    Write-Error "Please enter a valid year (e.g. 2024)."
    exit 1
}


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
    $Global:RapidAPIKeyAlt1
    #, $Global:RapidAPIKeyAlt2
)

$apiHost = "tank01-nfl-live-in-game-real-time-statistics-nfl.p.rapidapi.com"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$dataDir = Join-Path $scriptDir "..\data\past_seasons"
if (-not (Test-Path $dataDir)) { New-Item -ItemType Directory -Path $dataDir -Force | Out-Null }

$scheduleFile = Join-Path $dataDir "Schedule_$year.json"
$gamesFile    = Join-Path $dataDir "Games_$year.json"

$boxScoreWaitSeconds = 0.2  # Wartezeit zwischen BoxScore-Requests (anpassbar)

# --- Fetch schedule from Tank01 ---
Write-Host "Fetching full schedule (week=all, seasonType=reg)..." -ForegroundColor Yellow
$scheduleUrl = "https://$apiHost/getNFLGamesForWeek?week=all&seasonType=reg&season=$year"
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

# Save schedule
try {
    $schedule | ConvertTo-Json -Depth 20 | Out-File -FilePath $scheduleFile -Encoding UTF8
    Write-Host "Schedule.json saved." -ForegroundColor Green
} catch {
    Write-Error "Error writing Schedule.json: $_"
    exit 1
}

# --- Iterate schedule ---
$games = @()
$addedCount = 0
foreach ($g in $schedule) {

    # safeguard: ensure gameID exists
    if (-not $g.gameID) { continue }
    $gameID = $g.gameID

    Write-Host "Fetching Game Score for '$($gameID)'..." -ForegroundColor Yellow

    $gameIDEncoded = [uri]::EscapeDataString($gameID)
    $boxScoresUrl = "https://$apiHost/getNFLBoxScore?gameID=$gameIDEncoded&playByPlay=false&fantasyPoints=true"

    try {
        $bscoreResponse = Invoke-Tank01-With-Fallback -Url $boxScoresUrl -Keys $apiKeys
        $boxScore = $bscoreResponse.body

        if ($boxScore) {
            # Convert to PSCustomObject only at the end
            $boxObj = $boxScore | ConvertTo-Json -Depth 10 | ConvertFrom-Json

            $games += $boxObj
            Write-Host "  -> Game Score saved for $gameID" -ForegroundColor Green
            $addedCount++

        } else {
            Write-Warning "  -> No boxScore.body returned for $gameID"
        }
    } catch {
        Write-Warning "  -> Error fetching boxscore for $($gameID): $_"
    }

    # short sleep to avoid rapid-fire requests; adjust $boxScoreWaitSeconds as needed
    Start-Sleep -Seconds $boxScoreWaitSeconds

} # end foreach schedule


# --- Duplikate und leere SnapCounts entfernen ---
Write-Host "Cleaning up duplicate games and entries without snapCounts..." -ForegroundColor Yellow

$beforeCount = $games.Count

# --- Schritt 1: Duplikate nach gameID entfernen ---
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

# --- If any new games were added -> write Games.json ---
if ($addedCount -gt 0 -or $diff -gt 0) {
    # Save new games
    try {
        $games | ConvertTo-Json -Depth 20 | Out-File -FilePath $gamesFile -Encoding UTF8
        Write-Host "Games_$year.json created with $($addedCount) game(s)." -ForegroundColor Green
    } catch {
        Write-Error "Error writing Games.json: $_"
        exit 1
    }
} else {
    Write-Host "No games to add. Games_$year.json not created." -ForegroundColor Cyan
}

