
# Zuerst die Konfiguration einbinden
. "$PSScriptRoot\config.ps1"

# --- Konfiguration ---
$LeagueID = $Global:LeagueID

# Verzeichnis des Skripts
$scriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$dataDir     = Join-Path $scriptDir "..\data"
$backupDir   = Join-Path $dataDir "backup"
if (!(Test-Path $backupDir)) { New-Item -ItemType Directory -Path $backupDir | Out-Null }

$targetFile    = Join-Path $dataDir "League.json"
$timestampFile = Join-Path $dataDir "Timestamps.json"

# --- Sleeper: Liga ---
try {
    Write-Host "Hole Sleeper Liga..." -ForegroundColor Yellow
    $leagueUrl = "https://api.sleeper.app/v1/league/$LeagueID"
    $league    = Invoke-RestMethod -Uri $leagueUrl -ErrorAction Stop
    Write-Host "Sleeper Liga gefunden." -ForegroundColor Yellow
} catch {
    Write-Error "Fehler beim Abrufen der Liga: $_"
    exit 1
}

# --- Sleeper: Mitglieder + Rosters ---
try {
    Write-Host "Hole Sleeper Teams..." -ForegroundColor Yellow
    $membersUrl = "https://api.sleeper.app/v1/league/$LeagueID/users"
    $members    = Invoke-RestMethod -Uri $membersUrl -ErrorAction Stop
    $rostersUrl = "https://api.sleeper.app/v1/league/$LeagueID/rosters"
    $rosters    = Invoke-RestMethod -Uri $rostersUrl -ErrorAction Stop
    Write-Host "Sleeper Teams gefunden: $($rosters.Count)" -ForegroundColor Yellow
} catch {
    Write-Error "Fehler beim Abrufen der Teams/Rosters: $_"
    exit 1
}

# --- Teams bauen ---
$teamData = @()
foreach ($roster in $rosters) {
    $member = $members | Where-Object { $_.user_id -eq $roster.owner_id }
    $ownerAvatar = $null
    if ($member.avatar) {
        $avatarID    = $member.avatar
        $ownerAvatar = "https://sleepercdn.com/avatars/$avatarID"
    }

    $teamData += [PSCustomObject]@{
        Owner          = $member.display_name
        OwnerID        = $member.user_id
        OwnerAvatar    = $ownerAvatar
        Team           = $member.metadata.team_name
        TeamID         = $roster.roster_id
        TeamAvatar     = $member.metadata.avatar
        Points         = $roster.settings.fpts
        PointsAgainst  = $roster.settings.fpts_against
        Wins           = $roster.settings.wins
        Losses         = $roster.settings.losses
        Ties           = $roster.settings.ties
        Record         = $roster.metadata.record
        Streak         = $roster.metadata.streak
        MatchupID      = $roster.settings.matchup_id
        WaiverPosition = $roster.settings.waiver_position
        WaiverAdjusted = $roster.settings.waiver_adjusted
        IsCommissioner = $member.is_owner
        Roster         = $roster.players
        Reserve        = $roster.reserve
        Taxi           = $roster.taxi
        Starter        = $roster.starters
    }
}

# --- League JSON vorbereiten ---
$leagueAsJson = @()
$leagueAsJson += [PSCustomObject]@{
    LeagueID          = $league.league_id
    Name              = $league.name
    Avatar            = $league.avatar
    Season            = $league.season
    SeasonType        = $league.season_type
    Status            = $league.status
    TotalTeams        = $league.total_rosters
    Teams             = $teamData
    RosterSize        = $league.roster_positions
    ScoringType       = $league.scoring_settings
    Settings          = $league.settings
    LeagueIDPrevious  = $league.previous_league_id
}

$TimeSnapshot = (Get-Date)
$Now          = $TimeSnapshot.ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

# --- JSONs vergleichen ---
$oldJsonObj = Get-Content $targetFile -Raw | ConvertFrom-Json
$newJsonObj = $leagueAsJson
if (TeamsAreEqual $oldJsonObj.Teams $newJsonObj.Teams) {
    Write-Host "Keine Änderungen bei Teams erkannt – Update wird übersprungen." -ForegroundColor Cyan
    exit 2
}

# --- Backup alte Datei ---
if (Test-Path $targetFile) {
    $timestamp  = $TimeSnapshot.ToUniversalTime().ToString("yyyyMMdd_HHmmss")
    $backupFile = Join-Path $backupDir "League_$timestamp.json"
    Copy-Item -Path $targetFile -Destination $backupFile -Force
    Write-Host "Alte League.json gesichert als $backupFile" -ForegroundColor Cyan
}

# --- JSON schreiben ---
$newJson | Out-File $targetFile -Encoding UTF8
Write-Host "League.json gespeichert!" -ForegroundColor Green

# --- Timestamp aktualisieren ---
if (Test-Path $timestampFile) {
    $Timestamps = Get-Content $timestampFile | ConvertFrom-Json
} else {
    $Timestamps = @{}
}
$Timestamps.League = $Now
$Timestamps | ConvertTo-Json -Depth 3 | Set-Content $timestampFile
Write-Host "League-Timestamp aktualisiert: $Now" -ForegroundColor Green

# --- Fertig ---
exit 0




function TeamsAreEqual($oldTeams, $newTeams) {
    if ($oldTeams.Count -ne $newTeams.Count) { return $false }

    # Teams nach TeamID sortieren
    $oldSorted = $oldTeams | Sort-Object TeamID
    $newSorted = $newTeams | Sort-Object TeamID

    for ($i = 0; $i -lt $oldSorted.Count; $i++) {
        $oldTeam = $oldSorted[$i]
        $newTeam = $newSorted[$i]

        # Wichtige Properties vergleichen
        $props = 'TeamID','OwnerID','Points','PointsAgainst','Wins','Losses','Ties','Record','Streak','MatchupID','WaiverPosition','WaiverAdjusted','IsCommissioner'
        foreach ($prop in $props) {
            if ($oldTeam.$prop -ne $newTeam.$prop) { return $false }
        }

        # Spielerlisten vergleichen (nach Spieler-ID sortiert)
        $arrays = 'Roster','Starter','Reserve','Taxi'
        foreach ($arr in $arrays) {
            $oldArr = @($oldTeam.$arr) | Sort-Object
            $newArr = @($newTeam.$arr) | Sort-Object
            if (-not ($oldArr -eq $newArr)) { return $false }
        }
    }

    return $true
}