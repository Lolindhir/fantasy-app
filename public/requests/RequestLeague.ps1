# --- Konfiguration ---
$LeagueID = "1257421353431080960"

# --- Sleeper: Liga ---
Write-Host "Hole Sleeper Liga..." -ForegroundColor Yellow
$leagueUrl = "https://api.sleeper.app/v1/league/$LeagueID"
$league = Invoke-RestMethod -Uri $leagueUrl
Write-Host "Sleeper Liga gefunden." -ForegroundColor Yellow

# --- Sleeper: Mitglieder + Rosters ---
Write-Host "Hole Sleeper Teams..." -ForegroundColor Yellow
$membersUrl = "https://api.sleeper.app/v1/league/$LeagueID/users"
$members = Invoke-RestMethod -Uri $membersUrl
$rostersUrl = "https://api.sleeper.app/v1/league/$LeagueID/rosters"
$rosters = Invoke-RestMethod -Uri $rostersUrl
Write-Host "Sleeper Teams gefunden: $($rosters.Count)" -ForegroundColor Yellow

# --- Teams bauen ---
$teamData = @()
foreach ($roster in $rosters) {
    
    # Team Informationen
    $member = $members | Where-Object { $_.user_id -eq $roster.owner_id }

    # Owner Avatar with call to https://sleeper.com/v1/user/{user_id}/avatar, if id not null
    $ownerAvatar = $null
    if ($member.avatar) {
        $avatarID = $member.avatar
        $ownerAvatar = "https://sleepercdn.com/avatars/$avatarID"
    }

    $teamData += [PSCustomObject]@{
        Owner   = $member.display_name
        OwnerID = $member.user_id
        OwnerAvatar = $ownerAvatar
        Team    = $member.metadata.team_name
        TeamID  = $roster.roster_id
        TeamAvatar  = $member.metadata.avatar
        Points  = $roster.settings.fpts
        PointsAgainst = $roster.settings.fpts_against
        Wins    = $roster.settings.wins
        Losses  = $roster.settings.losses
        Ties    = $roster.settings.ties
        Record = $roster.metadata.record
        Streak = $roster.metadata.streak
        MatchupID = $roster.settings.matchup_id
        WaiverPosition = $roster.settings.waiver_position
        WaiverAdjusted = $roster.settings.waiver_adjusted
        IsCommissioner = $member.is_owner
        Roster  = $roster.players
        Reserve = $roster.reserve
        Taxi = $roster.taxi
        Starter = $roster.starters
    }
}

# --- League JSON vorbereiten ---
Write-Host "Erstelle League.json..." -ForegroundColor Yellow
$leagueAsJson = @()
$leagueAsJson += [PSCustomObject]@{
    LeagueID            = $league.league_id
    Name                = $league.name
    Avatar              = $league.avatar
    Season              = $league.season
    SeasonType          = $league.season_type
    Status              = $league.status
    TotalTeams          = $league.total_rosters
    Teams               = $teamData
    RosterSize          = $league.roster_positions
    ScoringType         = $league.scoring_settings
    Settings            = $league.settings
    LeagueIDPrevious    = $league.previous_league_id
}

# Verzeichnis des Skripts
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Ziel-Datei im data-Ordner parallel zum Requests-Ordner
$targetFile = Join-Path $scriptDir "..\data\League.json"

# JSON schreiben
$leagueAsJson | ConvertTo-Json -Depth 5 | Out-File $targetFile -Encoding UTF8
Write-Host "League.json gespeichert!" -ForegroundColor Green