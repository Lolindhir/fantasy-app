
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
    $propsToCheck = @('LeagueID','Name','Avatar','Season','SeasonType','Status','FinalWeek','LastWeek','PlayoffStartWeek','TotalTeams', 'SalaryCap', 'SalaryCapProjected', 'SalaryCapFantasy', 'SalaryCapProjectedFantasy')
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

    #--- Standings vergleichen ---
    # Prüfe Playoffs
    $oldPlayoffs = $oldLeague.Standings.Playoffs
    $newPlayoffs = $newLeague.Standings.Playoffs
    # Wenn nur eine Seite Daten hat, dann Änderung
    if (($oldPlayoffs -and -not $newPlayoffs) -or (-not $oldPlayoffs -and $newPlayoffs)) {
        if ($oldPlayoffs) {
            $oldStatus = "Present"
        } else {
            $oldStatus = "Not Present"
        }
        if ($newPlayoffs) {
            $newStatus = "Present"
        } else {
            $newStatus = "Not Present"
        }
        Write-Host "Playoffs presence changed: " + $oldStatus + " -> " + $newStatus
        return $true
    }
    # Wenn beide Seiten Playoffs haben, dann vergleichen
    if ($oldPlayoffs -and $newPlayoffs) {

        # Vergleiche Anzahl der Playoff-Platzierungen
        if ($oldPlayoffs.Count -ne $newPlayoffs.Count) {
            Write-Host "Playoff placements count changed: $($oldPlayoffs.Count) -> $($newPlayoffs.Count)"
            return $true
        }

        # Vergleiche jede Platzierung
        for ($i = 0; $i -lt $oldPlayoffs.Count; $i++) {
            $oldPlace = $oldPlayoffs[$i]
            $newPlace = $newPlayoffs[$i]

            # Prüfe Top-Level Eigenschaften der Platzierung
            $propsToCheck = @('Place','TeamID','Owner','TeamName','PlaceType','PlaceOrdinal')
            foreach ($prop in $propsToCheck) {
                if ($oldPlace.$prop -ne $newPlace.$prop) {
                    Write-Host "Playoff placement '$($oldPlace.PlaceOrdinal)' property '$prop' changed: '$($oldPlace.$prop)' -> '$($newPlace.$prop)'"
                    return $true
                }
            }
        }
    }


    # Keine Änderungen gefunden
    return $false
}



function Get-BracketPlacementsByP {
    param(
        [Parameter(Mandatory=$true)]
        [AllowEmptyCollection()]
        [array]$matches,
        [Parameter(Mandatory=$true)]
        [int]$startPlace
    )

    # prüfe ob Matches null oder leer sind
    if (-not $matches -or $matches.Count -eq 0) {
        return @{}  # leeres Dictionary zurückgeben
    }

    $placements = @{}

    foreach ($match in $matches) {
        if ($match.p) {
            # Gewinner bekommt Platz p + Offset
            $placements["$($startPlace + $match.p - 1)"] = $match.w
            # Verlierer bekommt Platz p+1 + Offset
            $placements["$($startPlace + $match.p)"]     = $match.l
        }
    }    

    return $placements
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
$scheduleFile = Join-Path $dataDir "Schedule.json"
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

     # Punkte berechnen als Double
    $points = [double]($roster.settings.fpts + ($roster.settings.fpts_decimal / 100))
    $pointsAgainst = [double]($roster.settings.fpts_against + ($roster.settings.fpts_against_decimal / 100))

    $teamData += [PSCustomObject]@{
        Owner          = $member.display_name
        OwnerID        = $member.user_id
        OwnerAvatar    = $ownerAvatar
        Team           = $member.metadata.team_name
        TeamID         = $roster.roster_id
        TeamAvatar     = $member.metadata.avatar
        Points         = $points
        PointsAgainst  = $pointsAgainst
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

# Sortiere Spieler nach Salarys und SalaryProjected (absteigend)
$topPlayers = $playersData | Sort-Object -Property Salary -Descending | Select-Object -First $topCount
$topPlayersProjected = $playersData | Sort-Object -Property SalaryProjected -Descending | Select-Object -First $topCount

if ($topPlayers.Count -eq 0 -or $topPlayersProjected.Count -eq 0) {
    Write-Error "No players found for Salary Cap calculation!"
    exit 1
}

Write-Host "Top $topCount players considered for Salary Cap calculation." -ForegroundColor Yellow

# --- Salary Cap berechnen ---
$avgSalary = ($topPlayers | Measure-Object -Property Salary -Average).Average
$avgSalaryProjected = ($topPlayersProjected | Measure-Object -Property SalaryProjected -Average).Average

$salaryCapTotal = [math]::Round($avgSalary * $SalaryRelevantTeamSize * 0.9)  # 10% Veränderung ist gewünscht, selbst bei fairer Verteilung
$salaryCapProjected = [math]::Round($avgSalaryProjected * $SalaryRelevantTeamSize * 0.9)  # 10% Veränderung ist gewünscht, selbst bei fairer Verteilung

Write-Host "Salary Cap (current): $($salaryCapTotal.ToString("N0"))" -ForegroundColor Yellow
Write-Host "Salary Cap (projected): $($salaryCapProjected.ToString("N0"))" -ForegroundColor Yellow

# --- Letzte Liga-Woche holen ---
$lastWeek = $league.settings.last_scored_leg
Write-Host "Last scored week in league: Week $lastWeek" -ForegroundColor Yellow

# --- Aktuelle Woche berechnen ---
$currentWeek = $null
$finalWeek = $null
# --- Load old schedule if present ---
$schedule = $null
if (Test-Path $scheduleFile) {
    try {
        $scheduleRaw = Get-Content $scheduleFile -Raw
        if ($scheduleRaw) { $schedule = $scheduleRaw | ConvertFrom-Json }
    } catch {
        Write-Warning "Could not read existing Schedule.json: $_"
        $schedule = $null
    }
}
if ($schedule) {
    # Sortiere Spiele chronologisch nach Datum (gameID beginnt mit YYYYMMDD)
    $sortedGames = $schedule | Sort-Object { $_.gameID }

    foreach ($game in $sortedGames) {
        # Nur Spiele zählen, die NICHT mit "Final" beginnen (also z.B. "Scheduled", "In Progress", etc.)
        if ($game.gameStatus -notmatch '^Final') {
            # Woche extrahieren
            if ($game.gameWeek -match 'Week (\d+)') {
                $currentWeek = [int]$matches[1]
                Write-Host "-> Found first non-final game: $($game.gameID) (Week $currentWeek)" -ForegroundColor Yellow
            } else {
                Write-Warning "Could not parse gameWeek for $($game.gameID): $($game.gameWeek)"
            }
            break
        }
    }

    # Wenn alle Spiele "Final" sind (oder "Final/OT"), letzte bekannte Woche nehmen
    if (-not $currentWeek -and $sortedGames.Count -gt 0) {
        if ($sortedGames[-1].gameWeek -match 'Week (\d+)') {
            $finalWeek = [int]$matches[1]
            Write-Host "All games final. Defaulting to last known week" -ForegroundColor DarkGray
        }
    } else {
        $finalWeek = $currentWeek - 1
    }

    # Wenn die finale Woche größer als die letzte gewertete Woche ist, setzen wir sie auf diese
    if ($finalWeek -gt $lastWeek) {
        $finalWeek = $lastWeek
        Write-Host "Adjusting final week to last scored week: Week $finalWeek" -ForegroundColor DarkGray
    }
}

if ($finalWeek) {
    Write-Host "Final active week detected: Week $finalWeek" -ForegroundColor Yellow
} else {
    Write-Host "Could not determine current week." -ForegroundColor DarkYellow
}



# --- Sleeper: Playoff Brackets laden ---
$winnersBracket = $null
$losersBracket  = $null

try {
    Write-Host "Get Sleeper Winners Bracket..." -ForegroundColor Yellow
    $winnersUrl = "https://api.sleeper.app/v1/league/$LeagueID/winners_bracket"
    $winnersBracket = Invoke-RestMethod -Uri $winnersUrl -ErrorAction Stop
} catch {
    Write-Warning "No winners bracket available."
}

try {
    Write-Host "Get Sleeper Losers Bracket..." -ForegroundColor Yellow
    $losersUrl = "https://api.sleeper.app/v1/league/$LeagueID/losers_bracket"
    $losersBracket = Invoke-RestMethod -Uri $losersUrl -ErrorAction Stop
} catch {
    Write-Warning "No losers bracket available."
}

# --- Playoff-Platzierungen berechnen ---
#$placements = Get-PlayoffPlacements $winnersBracket $losersBracket

# Winners und Losers sicher extrahieren
if (-not $winnersBracket) { $winnersBracket = @() }
if (-not $losersBracket)  { $losersBracket  = @() }

# --- Playoff-Daten in finale Struktur packen ---
$Playoffs = if ($winnersBracket -or $losersBracket) {
    [PSCustomObject]@{
        WinnersBracket = $winnersBracket
        LosersBracket  = $losersBracket
    }
} else {
    $null
}

# Platzierungen berechnen
$winnerPlacements = Get-BracketPlacementsByP $winnersBracket 1
$loserPlacements  = Get-BracketPlacementsByP $losersBracket ($winnerPlacements.Count + 1)

# Zusammenführen
$placements = @{}
foreach ($k in $winnerPlacements.Keys) { $placements[$k] = $winnerPlacements[$k] }
foreach ($k in $loserPlacements.Keys)  { $placements[$k] = $loserPlacements[$k] }

# Placements in Objekte umwandeln
# Struktur aus folgenden Properties: Place (1, 2, 3, ...), TeamID (RosterID des Teams auf diesem Platz), Owner (Name des Besitzers des Teams auf diesem Platz), TeamName (Name des Teams auf diesem Platz), PlaceType (Winner, Loser), PlaceOrdinal (1st, 2nd, 3rd, ...)
$placements = $placements.GetEnumerator() | Sort-Object Name | ForEach-Object {
    $placeNum = [int]$_.Name
    $teamID = $_.Value
    $teamInfo = $teamData | Where-Object { $_.TeamID -eq $teamID }
    if ($teamInfo) {
        [PSCustomObject]@{
            Place        = $placeNum
            TeamID       = $teamID
            Owner        = $teamInfo.Owner
            TeamName     = $teamInfo.Team
            PlaceType    = if ($placeNum -le $winnerPlacements.Count) { "Winner" } else { "Loser" }
            PlaceOrdinal = switch ($placeNum) {
                1 { "1st" }
                2 { "2nd" }
                3 { "3rd" }
                default { "${placeNum}th" }
            }
        }
    } else {
        Write-Warning "Could not find team info for TeamID $teamID in placements."
        [PSCustomObject]@{
            Place        = $placeNum
            TeamID       = $teamID
            Owner        = "Unknown Owner"
            TeamName     = "Unknown Team (ID: $teamID)"
            PlaceType    = if ($placeNum -le $winnerPlacements.Count) { "Winner" } else { "Loser" }
            PlaceOrdinal = switch ($placeNum) {
                1 { "1st" }
                2 { "2nd" }
                3 { "3rd" }
                default { "${placeNum}th" }
            }
        }
    }
}

# --- Playoff-Daten in finale Struktur packen ---
$Standings = if ($winnersBracket -or $losersBracket) {
    [PSCustomObject]@{
        Playoffs = $placements
    }
} else {
    $null
}




# --- League JSON vorbereiten ---
$leagueAsJson = @()
$leagueAsJson += [PSCustomObject]@{
    LeagueID                = $league.league_id
    Name                    = $league.name
    Avatar                  = $league.avatar
    Season                  = $league.season
    SeasonType              = $league.season_type
    Status                  = $league.status
    LastWeek                = $lastWeek
    PlayoffStartWeek        = $league.settings.playoff_week_start
    FinalWeek               = $finalWeek
    TotalTeams              = $league.total_rosters
    SalaryCap               = $salaryCapTotal
    SalaryCapProjected      = $salaryCapProjected
    SalaryRelevantTeamSize  = $SalaryRelevantTeamSize
    Standings               = $Standings
    Teams                   = $teamData
    Playoffs                = $Playoffs
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

