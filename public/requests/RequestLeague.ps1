
# ===========================================================================
# 1. Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\utils\ConfigUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\general\FileUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\general\ArrayUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\StandingUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\TeamUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\LeagueUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\player\PlayerUtils.psm1" -ErrorAction Stop -Force
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

# Dateinamen
$ScheduleFile = $config.ScheduleFile


# ===========================================================================
# 3. Funktionen
# ===========================================================================

function Get-Compare {
    
    return {
        param($oldLeague, $newLeague)

        if (-not $oldLeague) { return $true }

        # Top-Level
        $propsToCheck = @(
            'LeagueID','Name','Avatar','Season','SeasonType','Status',
            'FinalWeek','LastWeek','PlayoffStartWeek','TotalTeams',
            'SalaryCap','SalaryCapProjected','SalaryCapFantasy','SalaryCapProjectedFantasy'
        )

        foreach ($prop in $propsToCheck) {
            if ($oldLeague.$prop -ne $newLeague.$prop) {
                Write-Host "League property '$prop' changed: '$($oldLeague.$prop)' -> '$($newLeague.$prop)'"
                return $true
            }
        }

        # Arrays
        $arrayPropsToCheck = @('RosterSize')

        foreach ($prop in $arrayPropsToCheck) {
            if (-not (Compare-Arrays $oldLeague.$prop $newLeague.$prop $prop "League")) {
                return $true
            }
        }

        # Teams
        if (Compare-Teams $oldLeague.Teams $newLeague.Teams) {
            return $true
        }

        # Playoffs
        if (Compare-PlayoffStandings `
            -oldPlayoffs $oldLeague.Standings.Playoffs `
            -newPlayoffs $newLeague.Standings.Playoffs) {
            return $true
        }

        # Regular Season
        if (Compare-RegularSeasonStandings `
            -oldRegularSeason $oldLeague.Standings.RegularSeason `
            -newRegularSeason $newLeague.Standings.RegularSeason) {
            return $true
        }

        return $false
    }
    
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


    # --- Liga, Teams, Standings holen ---
    $league = Get-LeagueRaw
    $teamData = Get-Teams
    $playoffs = Get-Playoffs
    $standings = Get-Standings -playoffs $playoffs -teamData $teamData

    
    # --- Alle Spieler holen (für Salary Cap Berechnung) ---
    $playersData = Get-PlayersFromFile    

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

    # --- JSON schreiben ---
    $compare = & Get-Compare
    Save-JsonFile -Type "League" -Data $leagueAsJson -CompareScript $compare -CreateBackup -UpdateTimestamp

    # --- Fertig ---
    exit 0

}
catch {
    Write-Error "An error occurred: $_"
    exit 1
}



