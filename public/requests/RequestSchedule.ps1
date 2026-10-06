# ===========================================================================
# 1. Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\utils\ConfigUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\general\FileUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\general\CanonicalScheduleUtils.psm1" -ErrorAction Stop -Force
}
catch {
    Write-Error "Fehler beim Laden der Module: $_"
    exit 1
}



# --- Funktionen ---
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
# Build Schedule.json from canonical NFL facts (source-data/nfl/schedules + game-finality).
# No provider call and no API key: the former provider schedule, score and boxscore
# fetches (and Games.json) were retired with #347 G2-G4.
# Saves: Schedule.json, Timestamps.json
# ===================================================================

# --- Config / reuse existing variables ---
. "$PSScriptRoot\config.ps1"

# year aus config holen
$year = $Global:LeagueYear

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$dataDir = Join-Path $scriptDir "..\data"
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $scriptDir "..\.."))
if (-not (Test-Path $dataDir)) { New-Item -ItemType Directory -Path $dataDir -Force | Out-Null }


# current time
$currentTime = (Get-Date).ToUniversalTime()


$scheduleFile = Join-Path $dataDir "Schedule.json"
$backupDir    = Join-Path $dataDir "backup"
if (-not (Test-Path $backupDir)) { New-Item -ItemType Directory -Path $backupDir -Force | Out-Null }

$timestampFile = Join-Path $dataDir "Timestamps.json"

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

# --- Pre-Check: Existing Schedule belongs to current season? ---
if ($oldSchedule -and $oldSchedule.Count -gt 0) {

    $invalidSeasonGame = $oldSchedule | Where-Object {
        $_.season -ne $year
    } | Select-Object -First 1

    if ($invalidSeasonGame) {
        Write-Host "Schedule contains games from a different season -> clearing data." -ForegroundColor Yellow

        # Backup
        $ts = (Get-Date).ToUniversalTime().ToString("yyyyMMdd_HHmmss")

        if (Test-Path $scheduleFile) {
            Copy-Item $scheduleFile -Destination (Join-Path $backupDir "Schedule_$ts.json") -Force
        }

        # Clear files
        @() | ConvertTo-Json -Depth 20 | Out-File -FilePath $scheduleFile -Encoding UTF8

        Write-Host "Schedule.json cleared." -ForegroundColor Green
        $oldSchedule = $null
    }
}


# --- Build schedule from canonical NFL facts (#347 G2) ---
# source-data/nfl/schedules + game-finality own kickoff, teams, week, status and final scores. A missing or
# inconsistent canonical schedule aborts here and leaves the last published Schedule.json untouched.
Write-Host "Building schedule from canonical NFL source data (season $year)..." -ForegroundColor Yellow
try {
    $schedule = @(Get-CanonicalAppSchedule -Season ([int]$year) -RepoRoot $repoRoot)
}
catch {
    Write-Error "Error building schedule from canonical NFL source data: $_"
    exit 1
}

$finalWithoutScore = @($schedule | Where-Object { $_.gameStatus -match '^Final' -and -not ($_.PSObject.Properties.Name -contains 'awayPts' -and $_.PSObject.Properties.Name -contains 'homePts') })
foreach ($noScore in $finalWithoutScore) {
    Write-Warning "Canonical NFL schedule has no score pair for Final game $($noScore.gameID); score stays unknown."
}

Write-Host "Schedule built, total games: $($schedule.Count)" -ForegroundColor Green



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
        # Games.json is retired (#347 G4); drop its now meaningless freshness stamp.
        if ($timestamps -is [pscustomobject]) { $timestamps.PSObject.Properties.Remove('Games') } else { $timestamps.Remove('Games') }
        $timestamps | ConvertTo-Json -Depth 5 | Set-Content $timestampFile
        Write-Host "Schedule timestamp updated." -ForegroundColor Green
    } catch {
        Write-Error "Error writing Schedule.json: $_"
        exit 1
    }
}
