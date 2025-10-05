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
