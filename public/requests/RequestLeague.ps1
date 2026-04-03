
# ===========================================================================
# 1. Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\utils\ConfigUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\general\ArrayUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\StandingUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\TeamUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\LeagueUtils.psm1" -ErrorAction Stop -Force
}
catch {
    Write-Error "Fehler beim Laden der Module: $_"
    exit 1
}


# ===========================================================================
# 2. Globale Variablen und Konfiguration
# ===========================================================================

# Konfiguration holen
try {
    $config = Get-Config
}
catch {
    Write-Error "Error loading configuration: $_"
    exit 1
}

# Benötigte Konfigurationen
$LeagueID = $config.LeagueID
$SalaryRelevantTeamSize = $config.SalaryRelevantTeamSize

# Verzeichnis des Skripts
$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$DataDir     = Join-Path $ScriptDir "..\data"
$BackupDir   = Join-Path $DataDir "backup"

# Ziel-Dateinamen
$TargetFile    = Join-Path $DataDir "League.json"
$ScheduleFile = Join-Path $DataDir "Schedule.json"
$TimestampFile = Join-Path $DataDir "Timestamps.json"


# ===========================================================================
# 3. Funktionen
# ===========================================================================

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

    # Teams vergleichen
    if (Compare-Teams $oldLeague.Teams $newLeague.Teams) {
        return $true
    }

    #--- Standings vergleichen ---
    # Prüfe Playoffs
    if (Compare-PlayoffStandings -oldPlayoffs $oldLeague.Standings.Playoffs -newPlayoffs $newLeague.Standings.Playoffs) {
        return $true
    }
    # Prüfe Regular Season
    if (Compare-RegularSeasonStandings -oldRegularSeason $oldLeague.Standings.RegularSeason -newRegularSeason $newLeague.Standings.RegularSeason) {
        return $true
    }

    # Keine Änderungen gefunden
    return $false
}


# ===========================================================================
# 4. Logik
# ===========================================================================

# Hauptlogik in Try-Catch, damit bei Fehlern nicht die alte Datei überschrieben wird
try {

    # Zuerst die Konfiguration prüfen
    if (-not $LeagueID) {
        Write-Error "LeagueID not set in config.ps1!"
        exit 1
    }
    if (-not $SalaryRelevantTeamSize -or $SalaryRelevantTeamSize -le 0) {
        Write-Error "SalaryRelevantTeamSize not set or invalid in config.ps1!"
        exit 1
    }

    # Backup-Verzeichnis sicherstellen, wenn es nicht existiert
    if (!(Test-Path $BackupDir)) { New-Item -ItemType Directory -Path $BackupDir | Out-Null }

    # --- Liga, Teams, Standings holen ---
    $league = Get-LeagueRaw
    $teamData = Get-Teams
    $playoffs = Get-Playoffs
    $standings = Get-Standings -playoffs $playoffs -teamData $teamData


    # --- Spieler-Daten holen aus Players.json ---
    $playersFile = Join-Path $DataDir "Players.json"
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
    $topCount = $Global:SalaryRelevantTeamSize * $teamData.Count  # z.B. 20 relevante Spieler pro Team * Anzahl Teams

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
    if (Test-Path $ScheduleFile) {
        try {
            $scheduleRaw = Get-Content $ScheduleFile -Raw
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
        Standings               = $standings
        Teams                   = $teamData
        Playoffs                = $playoffs
        RosterSize              = $league.roster_positions
        ScoringType             = $league.scoring_settings
        Settings                = $league.settings
        LeagueIDPrevious        = $league.previous_league_id
    }

    # Änderungen prüfen
    # alte JSON laden
    $oldLeague = $null
    if (Test-Path $TargetFile) {
        $oldJsonRaw = Get-Content $TargetFile -Raw
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
    if (Test-Path $TargetFile) {
        $timestamp  = $TimeSnapshot.ToUniversalTime().ToString("yyyyMMdd_HHmmss")
        $backupFile = Join-Path $BackupDir "League_$timestamp.json"
        Copy-Item -Path $TargetFile -Destination $backupFile -Force
        Write-Host "Old League.json backed up as $backupFile" -ForegroundColor Cyan
    }

    # --- JSON schreiben ---
    try {
        $leagueAsJson | ConvertTo-Json -Depth 5 | Out-File $TargetFile -Encoding UTF8
        Write-Host "League.json saved!" -ForegroundColor Green
    } catch {
        Write-Error "Error writing League.json: $_"
        exit 1
    }

    # --- Timestamp aktualisieren ---
    if (Test-Path $TimestampFile) {
        $Timestamps = Get-Content $TimestampFile | ConvertFrom-Json
    } else {
        $Timestamps = @{}
    }
    $Timestamps.League = $Now
    $Timestamps | ConvertTo-Json -Depth 3 | Set-Content $TimestampFile
    Write-Host "League-Timestamp updated: $Now" -ForegroundColor Green

    # --- Fertig ---
    exit 0

}
catch {
    Write-Error "An error occurred: $_"
    exit 1
}



