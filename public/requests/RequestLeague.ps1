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
    Import-Module "$PSScriptRoot\utils\league\CanonicalLeagueCoreUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\CanonicalPlayoffUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\TeamDraftPickUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\LeagueWeekUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\DecisionWindowUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\PastSeasonsIndexUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\player\PlayerUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\player\PlayerValuationUtils.psm1" -ErrorAction Stop -Force
}
catch {
    Write-Error "Fehler beim Laden der Module: $_"
    exit 1
}

# ===========================================================================
# 2. Globale Variablen und Konfiguration
# ===========================================================================

try {
    $config = Get-Config
}
catch {
    Write-Error "Error loading configuration: $_"
    exit 1
}

$LeagueID = $config.LeagueID
$CanonicalLeagueID = $config.CanonicalLeagueID
$CapDeadline = $config.CapDeadline
$LeagueTimeZone = $config.LeagueTimeZone
$CapDeadlineBufferDays = $config.CapDeadlineBufferDays

$ScheduleFile = $config.ScheduleFile

# ===========================================================================
# 3. Funktionen
# ===========================================================================

function Get-Compare {
    return {
        param($oldLeague, $newLeague)

        if (-not $oldLeague) { return $true }

        $propsToCheck = @(
            'LeagueID','Name','Avatar','Season','SeasonType','Status','Phase',
            'FinalScoredWeek','CurrentWeek','LastLeagueWeek','PlayoffStartWeek','PlayoffStart', 'TradeDeadlineWeek', 'TradeReviewDays', 'TotalTeams',
            'SalaryCap','SalaryCapProjected','SalaryCapFantasy','SalaryCapProjectedFantasy', 'CapDeadline', 'SeasonKickoff', 'LeagueTimeZone', 'SalaryRelevantTeamSize',
            'WaiversOpen', 'WaiversMetaText', 'NextWaiverRun', 'TradesOpen', 'TradesMetaText', 'CutsAllowed', 'CutsMetaText', 'LeagueIDPrevious'
        )

        foreach ($prop in $propsToCheck) {
            if ($oldLeague.$prop -ne $newLeague.$prop) {
                Write-Host "League property '$prop' changed: '$($oldLeague.$prop)' -> '$($newLeague.$prop)'"
                return $true
            }
        }

        foreach ($prop in @('RosterSize')) {
            if (-not (Compare-Arrays $oldLeague.$prop $newLeague.$prop $prop "League")) {
                return $true
            }
        }

        foreach ($prop in @('Settings','ScoringType','Playoffs')) {
            $oldValue = $oldLeague.$prop | ConvertTo-Json -Depth 10 -Compress
            $newValue = $newLeague.$prop | ConvertTo-Json -Depth 10 -Compress
            if ($oldValue -ne $newValue) {
                Write-Host "League property '$prop' changed."
                return $true
            }
        }

        if (Compare-Teams $oldLeague.Teams $newLeague.Teams) { return $true }
        if (Compare-PlayoffStandings -oldPlayoffs $oldLeague.Standings.Playoffs -newPlayoffs $newLeague.Standings.Playoffs) { return $true }
        if (Compare-RegularSeasonStandings -oldRegularSeason $oldLeague.Standings.RegularSeason -newRegularSeason $newLeague.Standings.RegularSeason) { return $true }
        if (Compare-Awards -oldAwards $oldLeague.Standings.Awards -newAwards $newLeague.Standings.Awards) { return $true }

        return $false
    }
}

# ===========================================================================
# 4. Logik
# ===========================================================================

try {
    if (-not $LeagueID) {
        Write-Error "LeagueID not set in the league metadata (data-meta)!"
        exit 1
    }

    # Current Transactions.json and Drafts.json are written from the league history product by the consumer
    # generator (tools/league_history_app_publish.py write, ADR-057, Issue #999 step 5b) before this script runs
    # in League Live. League status/phase and team draft picks read the freshly written Drafts.json.
    $drafts = Get-LeagueDraftsLocal
    if (-not $drafts -or @($drafts).Count -eq 0) {
        throw "Drafts.json is missing or empty. The league history consumer generator must run before RequestLeague."
    }
    Write-Host "Current drafts loaded from Drafts.json ($(@($drafts).Count))." -ForegroundColor Green

    $league = Get-CanonicalCurrentLeagueRaw -CanonicalLeagueID $CanonicalLeagueID
    $teamData = Get-CanonicalCurrentTeamsForLeague -CanonicalLeagueID $CanonicalLeagueID
    $playoffs = Get-CanonicalCurrentPlayoffs -CanonicalLeagueID $CanonicalLeagueID
    $standingsRepoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))
    $standings = Get-LeagueStandingsProduct -CanonicalLeagueID $CanonicalLeagueID -RepoRoot $standingsRepoRoot

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
        foreach ($team in $teamData) {
            if (-not ($team.Placements -is [hashtable])) { $team.Placements = @{} }
            if (-not ($team.Placements[$key] -is [hashtable])) { $team.Placements[$key] = @{} }

            $playoffStanding = $standingSeason.Playoffs | Where-Object { $_.TeamID -eq $team.TeamID } | Select-Object -First 1
            if ($playoffStanding) {
                $team.Placements[$key]["Playoffs"] = $playoffStanding | Select-Object * -ExcludeProperty TeamID, Owner, TeamName
            }

            $regularStanding = $standingSeason.RegularSeason | Where-Object { $_.TeamID -eq $team.TeamID } | Select-Object -First 1
            if ($regularStanding) {
                $team.Placements[$key]["Regular"] = $regularStanding | Select-Object * -ExcludeProperty TeamID, Owner, TeamName
            }
        }
    }

    Write-Host "Enriching team data with draft pick keys..." -ForegroundColor Yellow
    $teamData = Add-DraftPickKeysToTeams -teams $teamData -drafts $drafts

    $playersData = Get-PlayersFromFile
    # --- Salary Cap aus dem PlayerValuation-Snapshot (#919 step 5): der neueste Snapshot der Saison ist der
    # Stand, den der letzte Players-Lauf zusammen mit Players.json veroeffentlicht hat. Keine Berechnung hier.
    $valuationSnapshot = Get-PlayerValuationLatestSnapshot -CanonicalLeagueID $CanonicalLeagueID -Season ([int]$league.season)
    if ([int]$valuationSnapshot.League.TeamCount -ne [int]$teamData.Count) {
        Write-Error "PlayerValuation snapshot TeamCount $($valuationSnapshot.League.TeamCount) differs from the league's $($teamData.Count) teams."
        exit 1
    }
    $SalaryRelevantTeamSize = [int]$valuationSnapshot.League.SalaryRelevantTeamSize
    if ($SalaryRelevantTeamSize -le 0) {
        Write-Error "PlayerValuation snapshot SalaryRelevantTeamSize $SalaryRelevantTeamSize is invalid."
        exit 1
    }
    $salaryCapTotal = [double]$valuationSnapshot.League.SalaryCap
    $salaryCapProjected = [double]$valuationSnapshot.League.SalaryCapProjected
    Write-Host "Salary Cap (current): $($salaryCapTotal.ToString("N0")) from $($valuationSnapshot.Models.SalaryCap) snapshot week $($valuationSnapshot.AsOfFinalScoredWeek)" -ForegroundColor Yellow
    Write-Host "Salary Cap (projected): $($salaryCapProjected.ToString("N0"))" -ForegroundColor Yellow

    $playoffStart = $league.settings.playoff_week_start
    Write-Host "Playoff start week: Week $playoffStart" -ForegroundColor Yellow

    $repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))
    $currentLeagueSourceFile = Join-Path (Get-DataSourceRoot -RepoRoot $repoRoot) "leagues\$CanonicalLeagueID\seasons\$currentSeason\league.json"
    $leagueWeekState = Resolve-LeagueWeekState `
        -League $league `
        -CanonicalLeagueSourceFile $currentLeagueSourceFile
    $lastScoredLeg = [int]$leagueWeekState.LastScoredLeg
    $lastWeek = [int]$leagueWeekState.LastLeagueWeek
    Write-Host "Last scored leg in league: Week $lastScoredLeg" -ForegroundColor Yellow
    Write-Host "Last structural league week: Week $lastWeek ($($leagueWeekState.BoundarySource))" -ForegroundColor Yellow

    $currentWeek = 0
    $finalWeek = 0
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

    if (-not $schedule) {
        throw "Decision Windows require Schedule.json in the League refresh."
    }

    # Status, Phase, weeks, trade and waiver state and the season boundaries come from the shared lifecycle model
    # (lifecycle-v1, ADR-073, Issue 1199); only the display texts are built here.
    $lifecycle = Get-LeagueLifecycle -CanonicalLeagueID $CanonicalLeagueID -Season ([int]$currentSeason) -RepoRoot $repoRoot
    $waiversOpen = [bool]$lifecycle.WaiversOpen
    $nextWaiverRun = $lifecycle.NextWaiverRun

    # Windows, locks, Fantasy Relevance, scoring availability, repairability and the scoring path come from the shared
    # Decision Windows function (ADR-074, Issue 1199 section 2); the delivery contract is unchanged.
    $decisionWindowsAsJson = Get-LeagueDecisionWindows -CanonicalLeagueID $CanonicalLeagueID -Season ([int]$currentSeason) -RepoRoot $repoRoot
    $outAvailabilityCount = @(@($decisionWindowsAsJson.ScoringAvailabilityObservations) | Where-Object State -eq 'out').Count
    Write-Host "ESPN scoring availability: $(@($decisionWindowsAsJson.ScoringAvailabilityObservations).Count) starter observations, $outAvailabilityCount OUT." -ForegroundColor DarkGray

    # FinalScoredWeek is the shared LeagueScoredWeek milestone (ADR-071, #897); CurrentWeek is a separate concept
    # (first non-final game of the canonical schedule); both come from the lifecycle.
    $currentWeek = [int]$lifecycle.CurrentWeek
    $finalWeek = [int]$lifecycle.FinalScoredWeek

    if ($finalWeek -ge 0) {
        Write-Host "Final active week detected: Week $finalWeek" -ForegroundColor Yellow
    } else {
        Write-Host "Could not determine current week." -ForegroundColor DarkYellow
    }

    $seasonKickoff = $lifecycle.SeasonKickoff
    $playoffStartAt = $lifecycle.PlayoffStart

    # Matchups.json and FantasyGameContext.json are no longer built here: the computed matchup context (ADR-075) is
    # delivered by tools/matchup_context_app_publish.py before this script runs.

    $cutsAllowed = [bool]$lifecycle.CutsAllowed
    $cutsMetaText = ""
    Write-Host "Daily Waivers active per settings: $waiversOpen" -ForegroundColor Yellow
    $waiversMetaText = ""
    $tradeReviewDays = [int]$lifecycle.TradeReviewDays
    $tradesOpen = [bool]$lifecycle.TradesOpen
    $tradeDeadlineWeek = $lifecycle.TradeDeadlineWeek

    $tradesMetaTextParts = @()
    $tradesClosedBy = @($lifecycle.TradesClosedBy)
    if ($tradesClosedBy -contains "DisabledInProvider") { $tradesMetaTextParts += "Disabled in Sleeper" }
    if ($tradesClosedBy -contains "CommissionerReview") { $tradesMetaTextParts += "Trades will be declined by Commissioner Review" }
    if ($tradesClosedBy -contains "TradeDeadlineReached") { $tradesMetaTextParts += "Trade Deadline reached" }

    $tradesMetaText = $tradesMetaTextParts -join " | "
    Write-Host "Trade review days: $tradeReviewDays" -ForegroundColor Yellow
    Write-Host "Trades open: $tradesOpen | Trades meta: $tradesMetaText" -ForegroundColor Yellow

    $status = [string]$lifecycle.Status
    $phase = [string]$lifecycle.Phase

    Write-Host "League is in status '$status' with phase '$phase'." -ForegroundColor Yellow
    Write-Host "Waivers open: $waiversOpen | Next waiver run: $nextWaiverRun | Trades open: $tradesOpen | Cuts allowed: $cutsAllowed" -ForegroundColor Yellow

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
        PlayoffStart            = $playoffStartAt
        TradeDeadlineWeek       = $tradeDeadlineWeek
        TradeReviewDays         = $tradeReviewDays
        CutsAllowed             = $cutsAllowed
        CutsMetaText            = $cutsMetaText
        WaiversOpen             = $waiversOpen
        WaiversMetaText         = $waiversMetaText
        NextWaiverRun           = $nextWaiverRun
        TradesOpen              = $tradesOpen
        TradesMetaText          = $tradesMetaText
        TotalTeams              = $league.total_rosters
        SalaryCap               = $salaryCapTotal
        SalaryCapProjected      = $salaryCapProjected
        CapDeadline             = $CapDeadline
        SeasonKickoff           = $seasonKickoff
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

    $decisionCompare = {
        param($oldDecisionWindows, $newDecisionWindows)
        Test-DecisionWindowReadModelChanged -OldData $oldDecisionWindows -NewData $newDecisionWindows
    }
    Save-JsonFile -Type "DecisionWindows" -Data $decisionWindowsAsJson -CompareScript $decisionCompare -UpdateTimestamp

    $compare = & Get-Compare
    Save-JsonFile -Type "League" -Data $leagueAsJson -CompareScript $compare -CreateBackup -UpdateTimestamp

    # Historical Matchups and FantasyGameContext files are regenerated by the weekly update-transactions run
    # (tools/matchup_context_app_publish.py write --history), not by the ten-minute League refresh.
    Update-PastSeasonsIndex -Config $config | Out-Null

    exit 0
}
catch {
    Write-Error "An error occurred: $_"
    exit 1
}
