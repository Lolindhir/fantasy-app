# ===========================================================================
# 1. Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\utils\ConfigUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\general\FileUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\general\ArrayUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\general\AvatarUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\StandingUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\TeamUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\DraftUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\DraftOrderAwareUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\TeamDraftPickUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\LeagueUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\PlayoffUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\TransactionUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\player\PlayerUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\player\PlayerChatExportUtils.psm1" -ErrorAction Stop -Force
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
$CapDeadline = $config.CapDeadline
$LeagueStatusSeasonStartBufferDays = $config.LeagueStatusSeasonStartBufferDays

# Dateinamen
$ScheduleFile = $config.ScheduleFile
$PlayersRelevantFile = $config.PlayersRelevantFile
$PlayersRelevantChatDir = $config.PlayersRelevantChatDir


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
            'FinalScoredWeek','CurrentWeek','LastLeagueWeek','PlayoffStartWeek', 'TradeDeadlineWeek','TotalTeams',
            'SalaryCap','SalaryCapProjected','SalaryCapFantasy','SalaryCapProjectedFantasy', 'CapDeadline', 'SalaryRelevantTeamSize',
            'WaiversOpen', 'WaiversMetaText', 'TradesOpen', 'TradesMetaText', 'CutsAllowed', 'CutsMetaText'
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

        # Awards
        if (Compare-Awards `
            -oldAwards $oldLeague.Standings.Awards `
            -newAwards $newLeague.Standings.Awards) {
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


    # --- Transaktionen für aktuelle Saison aktualisieren ---
    $transactionsCurrentSeason = Update-TransactionsCurrentSeason
    if ($transactionsCurrentSeason) {
        Write-Host "Transactions for current season updated." -ForegroundColor Green
    } else {
        Write-Host "No transactions for current season generated." -ForegroundColor Yellow
    }

    # --- Upcoming Drafts aktualisieren ---
    $drafts = Update-DraftsOrderAware
    if (-not $drafts -or @($drafts).Count -eq 0) {
        Write-Warning "Update-Drafts returned no drafts. Falling back to local Drafts.json."
        $drafts = Get-LeagueDraftsLocal
    }

    # --- Liga, Teams, Standings holen ---
    $league = Get-LeagueRaw
    $teamData = Get-TeamsForLeague
    $playoffs = Get-Playoffs
    $standings = Get-StandingsLocal

    # --- Für jedes Team die Standings ergänzen ---
    # (nur AllTime, aktuelle und letzte Saison)
    $currentSeason = $league.Season
    $previousSeason = $league.Season - 1
    Write-Host "Enriching team data ($($teamData.Count) teams) with standings for seasons: Current ($currentSeason), Previous ($previousSeason), AllTime" -ForegroundColor Yellow
    Write-Host "Total standings to enrich from: $($standings.Count)" -ForegroundColor Yellow
    foreach ($standingSeason in $standings) {

        $key = switch ($standingSeason.Season) {
            "AllTime" { "AllTime" }
            $currentSeason { "Current" }
            $previousSeason { "Previous" }
            default { $null }
        }

        if (-not $key) { continue }

        Write-Host "Enriching standings for season '$($standingSeason.Season)' (key: '$key')" -ForegroundColor Yellow
        
        # --- Mapping für Awards aufbauen, wenn vorhanden ---
        $awardsByTeamId = @{}
        if($standingSeason.Awards){
            foreach ($award in $standingSeason.Awards) {
                if (-not $awardsByTeamId.ContainsKey($award.TeamID)) {
                    $awardsByTeamId[$award.TeamID] = @()
                }

                $awardsByTeamId[$award.TeamID] += $award
            }
        }        
        
        # --- jedes Team durchgehen und zugehörige Placements hinzufügen ---
        foreach ($team in $teamData) {
            #$teamSeasonStanding = $standingSeason.Playoffs | Where-Object { $_.TeamID -eq $team.TeamID }

            # if ($teamSeasonStanding) {
            #     $team.Placements[$key] = $teamSeasonStanding
            # }

            # Ensure Placements exists
            if (-not ($team.Placements -is [hashtable])) {
                $team.Placements = @{}
            }

            # Sub-Objekt initialisieren (wichtig!)
            if (-not ($team.Placements[$key] -is [hashtable])) {
                $team.Placements[$key] = @{}
            }

            # --- Playoffs ---
            $playoffStanding = $standingSeason.Playoffs |
                Where-Object { $_.TeamID -eq $team.TeamID } |
                Select-Object -First 1

            if ($playoffStanding) {

                $team.Placements[$key]["Playoffs"] = $playoffStanding |
                    Select-Object * -ExcludeProperty TeamID, Owner, TeamName
            }

            # --- Regular Season ---
            $regularStanding = $standingSeason.RegularSeason |
                Where-Object { $_.TeamID -eq $team.TeamID } |
                Select-Object -First 1

            if ($regularStanding) {
                $team.Placements[$key]["Regular"] = $regularStanding |
                    Select-Object * -ExcludeProperty TeamID, Owner, TeamName
            }

            # --- Awards ---
            if ($awardsByTeamId.ContainsKey($team.TeamID)) {
                $team.Placements[$key]["Awards"] = $awardsByTeamId[$team.TeamID] |
                    Select-Object * -ExcludeProperty TeamID, Owner, TeamName
            } else {
                $team.Placements[$key]["Awards"] = @()
            }
        }
    }

    # --- Draft Pick Keys je Team ergänzen ---
    Write-Host "Enriching team data with draft pick keys..." -ForegroundColor Yellow
    $teamData = Add-DraftPickKeysToTeams -teams $teamData -drafts $drafts
    
    # --- Alle Spieler holen (für Salary Cap Berechnung und relevante Spielerdatei) ---
    $playersData = Get-PlayersFromFile    

    # --- Top-N Spieler bestimmen ---
    $topCount = [int]$SalaryRelevantTeamSize * [int]$teamData.Count  # z.B. 20 relevante Spieler pro Team * Anzahl Teams
    if ($topCount -le 0) {
        Write-Error "Invalid topCount for Salary Cap calculation. SalaryRelevantTeamSize=$SalaryRelevantTeamSize, TeamCount=$($teamData.Count)"
        exit 1
    }

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

    # --- Playoff Start holen ---
    $playoffStart = $league.settings.playoff_week_start
    Write-Host "Playoff start week: Week $playoffStart" -ForegroundColor Yellow

    # --- Letzte Liga-Woche holen ---
    $lastWeek = $league.settings.last_scored_leg
    if($null -eq $lastWeek){
        Write-Host "Last scored week in league not set in league settings." -ForegroundColor Yellow
        $lastWeek = $playoffStart - 1 + $playoffs.WinnersBracket.length
    }
    Write-Host "Last scored week in league: Week $lastWeek" -ForegroundColor Yellow


    # --- Aktuelle Woche berechnen ---
    $currentWeek = 0
    $finalWeek = 0
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
            if (-not $game.gameDetails.week) { continue }

            $week = [int]$game.gameDetails.week

            if ($game.gameDetails.gameStatus -eq "Completed") {
                if ($week -gt $finalWeek) { $finalWeek = $week }
                if ($week -gt $currentWeek) { $currentWeek = $week + 1 }
            }
        }

        # Fallback: Wenn noch keine Games completed sind, Woche 1
        if ($currentWeek -eq 0) { $currentWeek = 1 }

        # Deckelung auf letzte Liga-Woche
        if ($currentWeek -gt $lastWeek) { $currentWeek = $lastWeek }
    }

    # --- Ligaobjekt bauen ---
    $leagueOutput = [ordered]@{
        LeagueID                  = $league.league_id
        Name                      = $league.name
        Avatar                    = Get-SleeperAvatarUrl $league.avatar
        Season                    = $league.season
        SeasonType                = $league.season_type
        Status                    = Get-LeagueStatus `
                                        -leagueStatus $league.status `
                                        -leagueSeason ([int]$league.season) `
                                        -currentYear ([int]$config.LeagueYear) `
                                        -seasonStartBufferDays ([int]$LeagueStatusSeasonStartBufferDays)
        FinalScoredWeek           = $finalWeek
        CurrentWeek               = $currentWeek
        LastLeagueWeek            = $lastWeek
        PlayoffStartWeek          = $playoffStart
        TradeDeadlineWeek         = $league.settings.trade_deadline
        RosterSize                = $league.roster_positions
        TotalTeams                = $league.total_rosters
        SalaryCap                 = $salaryCapTotal
        SalaryCapProjected        = $salaryCapProjected
        SalaryCapFantasy          = 200
        SalaryCapProjectedFantasy = 200
        CapDeadline               = $CapDeadline
        SalaryRelevantTeamSize    = $SalaryRelevantTeamSize

        WaiversOpen               = Test-LeagueWaiversOpen `
                                        -leagueStatus $league.status `
                                        -finalScoredWeek $finalWeek `
                                        -lastLeagueWeek $lastWeek
        WaiversMetaText           = Get-LeagueWaiversMetaText `
                                        -leagueStatus $league.status `
                                        -finalScoredWeek $finalWeek `
                                        -lastLeagueWeek $lastWeek
        TradesOpen                = Test-LeagueTradesOpen `
                                        -leagueStatus $league.status `
                                        -currentWeek $currentWeek `
                                        -tradeDeadlineWeek $league.settings.trade_deadline
        TradesMetaText            = Get-LeagueTradesMetaText `
                                        -leagueStatus $league.status `
                                        -currentWeek $currentWeek `
                                        -tradeDeadlineWeek $league.settings.trade_deadline
        CutsAllowed               = Test-LeagueCutsAllowed `
                                        -leagueStatus $league.status `
                                        -capDeadline $CapDeadline
        CutsMetaText              = Get-LeagueCutsMetaText `
                                        -leagueStatus $league.status `
                                        -capDeadline $CapDeadline
        Teams                     = $teamData
        Standings                 = $standings
    }

    # --- JSON speichern mit Vergleich ---
    Save-JsonFile -Type "League" -Data $leagueOutput -CompareScript (Get-Compare) -CreateBackup -UpdateTimestamp

    # --- Relevante Spielerdatei und Chat-Export aktualisieren ---
    $relevantPlayers = Get-RelevantPlayers -players $playersData -leagueTeams $teamData
    Save-JsonFile -TargetFile $PlayersRelevantFile -Data $relevantPlayers
    Export-PlayerChatChunks -Players $relevantPlayers -OutputDir $PlayersRelevantChatDir

}
catch {
    Write-Error "Fehler beim Aktualisieren der League-Daten: $_"
    exit 1
}
