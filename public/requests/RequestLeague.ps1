
function Compare-Arrays($oldArray, $newArray, $fieldName, $compareName) {
    # Falls beide leer oder null sind
    if ((-not $oldArray -or $oldArray.Count -eq 0) -and (-not $newArray -or $newArray.Count -eq 0)) {
        return $true
    }

    # Normalisiere Arrays (null -> leer, sortiere für stabilen Vergleich)
    $oldArr = @()
    if ($oldArray) { $oldArr = $oldArray | Sort-Object }
    $newArr = @()
    if ($newArray) { $newArr = $newArray | Sort-Object }

    # Vergleiche Inhalte
    $diff = Compare-Object -ReferenceObject $oldArr -DifferenceObject $newArr

    if ($diff) {
        Write-Host "Difference at field '$fieldName' for '$compareName':" -ForegroundColor Yellow
        foreach ($d in $diff) {
            if ($d.SideIndicator -eq '<=') {
                Write-Host "  Removed: $($d.InputObject)" -ForegroundColor Red
            }
            elseif ($d.SideIndicator -eq '=>') {
                Write-Host "  Added: $($d.InputObject)" -ForegroundColor Green
            }
        }
        return $false
    }

    return $true
}

function LeagueHasChanged($oldLeague, $newLeague) {
    if (-not $oldLeague) { return $true }  # keine alte Daten -> Änderung

    # Prüfe Top-Level Eigenschaften der Liga
    $propsToCheck = @('LeagueID','Name','Avatar','Season','SeasonType','Status','TotalTeams', 'SalaryCap', 'SalaryCapProjected')
    foreach ($prop in $propsToCheck) {
        if ($oldLeague.$prop -ne $newLeague.$prop) {
            Write-Host "League property '$prop' changed: '$($oldLeague.$prop)' -> '$($newLeague.$prop)'"
            return $true
        }
    }

    # Vergleiche Array-Eigenschaften der Liga
    $arrayPropsToCheck = @('RosterSize')
    foreach ($prop in $arrayPropsToCheck) {
        if (-not (Compare-Arrays $oldLeague.$prop $newLeague.$prop $prop "League")) {
            return $true
        }
    }
    foreach ($field in $arraysToCompare) {
        if (-not (Compare-Arrays $oldTeam.$field $newTeam.$field $field $oldTeam.Team)) {
            return $true
        }
    }

    # Prüfe Anzahl der Teams
    if ($oldLeague.Teams.Count -ne $newLeague.Teams.Count) {
        Write-Host "Team count changed: $($oldLeague.Teams.Count) -> $($newLeague.Teams.Count)"
        return $true
    }

    # Prüfe jedes Team
    for ($i = 0; $i -lt $oldLeague.Teams.Count; $i++) {
        $oldTeam = $oldLeague.Teams[$i]
        $newTeam = $newLeague.Teams[$i]

        # Prüfe Top-Level Eigenschaften des Teams
        $propsToCheck = @('TeamID','Name','Avatar','OwnerID','Owner','OwnerAvatar','Points','IsCommissioner','Wins','Losses','Ties','Record','Streak','MatchupID','WaiverPosition','WaiverAdjusted')
        foreach ($prop in $propsToCheck) {
            if ($oldTeam.$prop -ne $newTeam.$prop) {
                Write-Host "Team '$($oldTeam.Owner)' property '$prop' changed: '$($oldTeam.$prop)' -> '$($newTeam.$prop)'"
                return $true
            }
        }

        # Vergleiche Roster, Reserve, Taxi
        $arraysToCompare = @('Roster','Reserve','Taxi')
        foreach ($field in $arraysToCompare) {
            if (-not (Compare-Arrays $oldTeam.$field $newTeam.$field $field $oldTeam.Owner)) {
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
$LeagueID = $Global:LeagueID
$TeamCount = $Global:TeamCount
$SalaryRelevantTeamSize = $Global:SalaryRelevantTeamSize
if (-not $LeagueID) {
    Write-Error "LeagueID not set in config.ps1!"
    exit 1
}
if (-not $TeamCount -or $TeamCount -le 0) {
    Write-Error "TeamCount not set or invalid in config.ps1!"
    exit 1
}
if (-not $SalaryRelevantTeamSize -or $SalaryRelevantTeamSize -le 0) {
    Write-Error "SalaryRelevantTeamSize not set or invalid in config.ps1!"
    exit 1
}


# Verzeichnis des Skripts
$scriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$dataDir     = Join-Path $scriptDir "..\data"
$backupDir   = Join-Path $dataDir "backup"
if (!(Test-Path $backupDir)) { New-Item -ItemType Directory -Path $backupDir | Out-Null }

$targetFile    = Join-Path $dataDir "League.json"
$timestampFile = Join-Path $dataDir "Timestamps.json"

# --- Sleeper: Liga ---
try {
    Write-Host "Get Sleeper League..." -ForegroundColor Yellow
    $leagueUrl = "https://api.sleeper.app/v1/league/$LeagueID"
    $league    = Invoke-RestMethod -Uri $leagueUrl -ErrorAction Stop
    Write-Host "Sleeper League found." -ForegroundColor Yellow
} catch {
    Write-Error "Error retrieving league: $_"
    exit 1
}

# --- Sleeper: Mitglieder + Rosters ---
try {
    Write-Host "Get Sleeper Teams..." -ForegroundColor Yellow
    $membersUrl = "https://api.sleeper.app/v1/league/$LeagueID/users"
    $members    = Invoke-RestMethod -Uri $membersUrl -ErrorAction Stop
    $rostersUrl = "https://api.sleeper.app/v1/league/$LeagueID/rosters"
    $rosters    = Invoke-RestMethod -Uri $rostersUrl -ErrorAction Stop
    Write-Host "Sleeper Teams found: $($rosters.Count)" -ForegroundColor Yellow
} catch {
    Write-Error "Error retrieving teams/rosters: $_"
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

# --- Spieler-Daten holen aus Players.json ---
$playersFile = Join-Path $dataDir "Players.json"
if (!(Test-Path $playersFile)) {
    Write-Error "Players.json not found at '$playersFile'!"
    exit 1
}
$playersJson = Get-Content $playersFile -Raw
if (-not $playersJson) {
    Write-Error "Players.json is empty!"
    exit 1
}
$playersData = $playersJson | ConvertFrom-Json
if (-not $playersData -or $playersData.Count -eq 0) {
    Write-Error "No valid players found in Players.json!"
    exit 1
}

# --- Top-N Spieler bestimmen ---
$topCount = $Global:SalaryRelevantTeamSize * $TeamCount

# Sortiere Spieler nach SalaryDollars und SalaryDollarsProjected (absteigend)
$topPlayers = $playersData | Sort-Object -Property SalaryDollars -Descending | Select-Object -First $topCount
$topPlayersProjected = $playersData | Sort-Object -Property SalaryDollarsProjected -Descending | Select-Object -First $topCount

if ($topPlayers.Count -eq 0 -or $topPlayersProjected.Count -eq 0) {
    Write-Error "No players found for Salary Cap calculation!"
    exit 1
}

# --- Salary Cap berechnen ---
$avgSalary = ($topPlayers | Measure-Object -Property SalaryDollars -Average).Average
$avgSalaryProjected = ($topPlayersProjected | Measure-Object -Property SalaryDollarsProjected -Average).Average

$salaryCapTotal = [math]::Round($avgSalary * $SalaryRelevantTeamSize)
$salaryCapProjected = [math]::Round($avgSalaryProjected * $SalaryRelevantTeamSize)

Write-Host "Top $topCount players considered for Salary Cap calculation." -ForegroundColor Yellow
Write-Host "Salary Cap (current): $($salaryCapTotal.ToString("N0"))" -ForegroundColor Yellow
Write-Host "Salary Cap (projected): $($salaryCapProjected.ToString("N0"))" -ForegroundColor Yellow

# --- League JSON vorbereiten ---
$leagueAsJson = @()
$leagueAsJson += [PSCustomObject]@{
    LeagueID                = $league.league_id
    Name                    = $league.name
    Avatar                  = $league.avatar
    Season                  = $league.season
    SeasonType              = $league.season_type
    Status                  = $league.status
    TotalTeams              = $league.total_rosters
    SalaryCap               = $salaryCapTotal
    SalaryCapProjected      = $salaryCapProjected
    SalaryRelevantTeamSize  = $SalaryRelevantTeamSize
    Teams                   = $teamData
    RosterSize              = $league.roster_positions
    ScoringType             = $league.scoring_settings
    Settings                = $league.settings
    LeagueIDPrevious        = $league.previous_league_id
}

# Änderungen prüfen
# alte JSON laden
$oldLeague = $null
if (Test-Path $targetFile) {
    $oldJsonRaw = Get-Content $targetFile -Raw
    if ($oldJsonRaw) { $oldLeague = ($oldJsonRaw | ConvertFrom-Json) }
}

# neue JSON erzeugen
$newLeague = $leagueAsJson[0]  # Array mit 1 Objekt

# Änderungen prüfen
if (LeagueHasChanged $oldLeague $newLeague) {
    Write-Host "Changes detected - updating file." -ForegroundColor Green
# Backup + Schreiben + Timestamp + Exit 0
}
else {
    Write-Host "No changes - update skipped." -ForegroundColor Cyan
    exit 0
}

# --- Zeitstempel ---
$TimeSnapshot = (Get-Date)
$Now          = $TimeSnapshot.ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

# --- Backup alte Datei ---
if (Test-Path $targetFile) {
    $timestamp  = $TimeSnapshot.ToUniversalTime().ToString("yyyyMMdd_HHmmss")
    $backupFile = Join-Path $backupDir "League_$timestamp.json"
    Copy-Item -Path $targetFile -Destination $backupFile -Force
    Write-Host "Old League.json backed up as $backupFile" -ForegroundColor Cyan
}

# --- JSON schreiben ---
try {
    $leagueAsJson | ConvertTo-Json -Depth 5 | Out-File $targetFile -Encoding UTF8
    Write-Host "League.json saved!" -ForegroundColor Green
} catch {
    Write-Error "Error writing League.json: $_"
    exit 1
}

# --- Timestamp aktualisieren ---
if (Test-Path $timestampFile) {
    $Timestamps = Get-Content $timestampFile | ConvertFrom-Json
} else {
    $Timestamps = @{}
}
$Timestamps.League = $Now
$Timestamps | ConvertTo-Json -Depth 3 | Set-Content $timestampFile
Write-Host "League-Timestamp updated: $Now" -ForegroundColor Green

# --- Fertig ---
exit 0

