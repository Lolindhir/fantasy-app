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
    Import-Module "$PSScriptRoot\utils\league\TransactionDraftPickEnrichmentUtils.psm1" -ErrorAction Stop -Force
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
$CapDeadline = $config.CapDeadline
$LeagueTimeZone = $config.LeagueTimeZone
$CapDeadlineBufferDays = 3
$LeagueStatusSeasonStartBufferDays = $config.LeagueStatusSeasonStartBufferDays

try {
    $metadataPath = Join-Path $config.DataDir "Metadata.json"
    if (Test-Path $metadataPath) {
        $metadataContent = Get-Content $metadataPath -Raw | ConvertFrom-Json
        if ($metadataContent.PSObject.Properties.Name -contains "CapDeadlineBufferDays") {
            $CapDeadlineBufferDays = [int]$metadataContent.CapDeadlineBufferDays
        }
    }
}
catch {
    Write-Warning "Could not read CapDeadlineBufferDays from Metadata.json. Falling back to 3 days. $_"
}

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
            'LeagueID','Name','Avatar','Season','SeasonType','Status','Phase',
            'FinalScoredWeek','CurrentWeek','LastLeagueWeek','PlayoffStartWeek', 'TradeDeadlineWeek', 'TradeReviewDays', 'TotalTeams',
            'SalaryCap','SalaryCapProjected','SalaryCapFantasy','SalaryCapProjectedFantasy', 'CapDeadline', 'LeagueTimeZone', 'SalaryRelevantTeamSize',
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
    $transactionsCurrentSeason = Update-CurrentTransactionDraftPickTypesFromSleeper `
        -transactions $transactionsCurrentSeason `
        -leagueID $LeagueID

    if ($transactionsCurrentSeason) {
        Write-Host "Transactions for current season updated." -ForegroundColor Green
    } else {
        Write-Host "No transactions for current season generated." -ForegroundColor Yellow
    }

    # --- Upcoming Drafts aktualisieren ---
    $drafts = Update-DraftsOrderAware
    if (-not $drafts -or @($drafts).Count -eq 0) {
        Write-Warning "Update-DraftsOrderAware returned no drafts. Falling back to local Drafts.json."
        $drafts = Get-LeagueDraftsLocal
    }

    Update-CurrentTransactionDraftPickDetails -drafts $drafts | Out-Null

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
    
    # --- Alle Spieler holen (für Salary Cap Berechnung) ---
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

    if ($finalWeek -ge 0) {
        Write-Host "Final active week detected: Week $finalWeek" -ForegroundColor Yellow
    } else {
        Write-Host "Could not determine current week." -ForegroundColor DarkYellow
    }

    # Offenheit von Trades, Cuts, Waivers prüfen
    $cutsAllowed = $true
    $cutsMetaText = ""
    $waiversOpen = [int]$league.settings.disable_adds -eq 0
    Write-Host "Daily Waivers active per settings: $waiversOpen" -ForegroundColor Yellow
    $waiversMetaText = ""
    $tradeReviewDays = if ($null -ne $league.settings.trade_review_days) { [int]$league.settings.trade_review_days } else { 0 }
    $tradesOpen = [int]$league.settings.disable_trades -eq 0
    $tradesMetaTextParts = @()

    if (-not $tradesOpen) {
        $tradesMetaTextParts += "Disabled in Sleeper"
    }

    if ($tradeReviewDays -gt 0) {
        $tradesOpen = $false
        $tradesMetaTextParts += "Trades will be declined by Commissioner Review"
    }

    $tradeDeadlineWeek = [int]$league.settings.trade_deadline
    $leagueWeekForTradeDeadline = $currentWeek
    if ($leagueWeekForTradeDeadline -le 0) {
        $leagueWeekForTradeDeadline = $finalWeek
    }
    if ($tradeDeadlineWeek -gt 0 -and $leagueWeekForTradeDeadline -ge $tradeDeadlineWeek) {
        $tradesOpen = $false
        $tradesMetaTextParts += "Trade Deadline reached"
    }

    $tradesMetaText = $tradesMetaTextParts -join " | "
    Write-Host "Trade review days: $tradeReviewDays" -ForegroundColor Yellow
    Write-Host "Trades open: $tradesOpen | Trades meta: $tradesMetaText" -ForegroundColor Yellow

    # Status und optionale Status-Phase setzen
    $statusState = Resolve-LeagueStatusState `
        -League $league `
        -Drafts $drafts `
        -Schedule $schedule `
        -LeagueYear ([int]$config.LeagueYear) `
        -CapDeadline $CapDeadline `
        -CapDeadlineBufferDays $CapDeadlineBufferDays `
        -TradesOpen $tradesOpen `
        -FinalScoredWeek $finalWeek `
        -PlayoffStartWeek $playoffStart `
        -SeasonStartBufferDays $LeagueStatusSeasonStartBufferDays

    $status = [string]$statusState.Status
    $phase = [string]$statusState.Phase

    if ($status -eq "Completed") {
        $cutsAllowed = $false
        $waiversOpen = $false
        $tradesOpen = $false
    }

    Write-Host "League is in status '$status' with phase '$phase'." -ForegroundColor Yellow
    Write-Host "Waivers open: $waiversOpen | Trades open: $tradesOpen | Cuts allowed: $cutsAllowed" -ForegroundColor Yellow
    

    # Ermitteln, wann die Waivers sind

    # Waiver Wire Reihenfolge ermitteln

    # Draft Reihenfolge ermitteln


    # --- League JSON vorbereiten ---
    $leagueAsJson = @()
    $leagueAsJson += [PSCustomObject]@{
        LeagueID                = $league.league_id
        Name                    = $league.name
        Avatar                  = Get-SleeperAvatar($league.avatar)
        Season                  = $league.season
        SeasonType              = $league.season_type
        Status                  = $status
        Phase                   = $phase
        CurrentWeek             = $currentWeek
        FinalScoredWeek         = $finalWeek
        LastLeagueWeek          = $lastWeek
        PlayoffStartWeek        = $playoffStart
        TradeDeadlineWeek       = $league.settings.trade_deadline
        TradeReviewDays         = $tradeReviewDays
        CutsAllowed             = $cutsAllowed
        CutsMetaText            = $cutsMetaText
        WaiversOpen             = $waiversOpen
        WaiversMetaText         = $waiversMetaText
        TradesOpen              = $tradesOpen
        TradesMetaText          = $tradesMetaText
        TotalTeams              = $league.total_rosters
        SalaryCap               = $salaryCapTotal
        SalaryCapProjected      = $salaryCapProjected
        CapDeadline             = $CapDeadline
        LeagueTimeZone          = $LeagueTimeZone
        SalaryRelevantTeamSize  = $SalaryRelevantTeamSize
        Teams                   = $teamData
        Standings               = $standings
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
