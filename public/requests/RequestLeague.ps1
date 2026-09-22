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
    Import-Module "$PSScriptRoot\utils\league\CanonicalMatchupUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\DraftUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\DraftOrderAwareUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\TeamDraftPickUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\LeagueUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\LeagueWeekUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\WaiverUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\AcquisitionCapabilityUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\LeagueOverviewUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\DecisionWindowUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\FantasyGameContextUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\MatchupReadModelUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\PastSeasonsIndexUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\TransactionUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\TransactionDraftPickEnrichmentUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\LeagueTransactionPipelineUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\player\PlayerUtils.psm1" -ErrorAction Stop -Force
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
$CanonicalLeagueID = "nfl-reise"
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

$ScheduleFile = $config.ScheduleFile
$FantasyGameContextFile = Join-Path $config.DataDir "FantasyGameContext.json"

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

function Ensure-PreviousFantasyGameContextHistory {
    param(
        [Parameter(Mandatory = $true)][int]$CurrentSeason
    )

    $historicalSeason = $CurrentSeason - 1
    if ($historicalSeason -lt 2022) { return }

    $historyDir = Join-Path $config.PastSeasonsDir "FantasyGameContext"
    $targetFile = Join-Path $historyDir "FantasyGameContext_$historicalSeason.json"
    if (Test-Path $targetFile) { return }

    $repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))
    $canonicalLeagueID = "nfl-reise"
    $seasonSourceDir = Join-Path $repoRoot "source-data\leagues\$canonicalLeagueID\seasons\$historicalSeason"
    $leagueSourceFile = Join-Path $seasonSourceDir "league.json"
    $matchupDirectory = Join-Path $seasonSourceDir "matchups"
    $scheduleFile = Join-Path $config.PastSeasonsDir "Schedule_$historicalSeason.json"
    $playersFile = Join-Path $config.PastSeasonsDir "Players_$historicalSeason.json"
    $weeklyRosterDirectory = Join-Path $repoRoot "source-data\nfl\weekly-rosters\$historicalSeason"

    if (-not (Test-Path $leagueSourceFile) -or -not (Test-Path $matchupDirectory) -or -not (Test-Path $scheduleFile) -or -not (Test-Path $playersFile)) {
        Write-Warning "Historical FantasyGameContext $historicalSeason is not materialized because required source evidence is incomplete."
        return
    }

    Write-Host "Materializing historical FantasyGameContext for $historicalSeason..." -ForegroundColor Yellow
    $historicalContext = New-HistoricalFantasyGameContextSeason `
        -LeagueID $canonicalLeagueID `
        -Season $historicalSeason `
        -LeagueSourceFile $leagueSourceFile `
        -MatchupDirectory $matchupDirectory `
        -ScheduleFile $scheduleFile `
        -HistoricalPlayersFile $playersFile `
        -WeeklyRosterDirectory $weeklyRosterDirectory

    if (-not (Test-Path $historyDir)) {
        New-Item -ItemType Directory -Path $historyDir -Force | Out-Null
    }
    $historicalContext | ConvertTo-Json -Depth 20 | Out-File $targetFile -Encoding UTF8
    Update-PastSeasonsIndex -Config $config | Out-Null
    Write-Host "Historical FantasyGameContext $historicalSeason materialized." -ForegroundColor Green
}

# ===========================================================================
# 4. Logik
# ===========================================================================

try {
    if (-not $LeagueID) {
        Write-Error "LeagueID not set in config.ps1!"
        exit 1
    }
    if (-not $SalaryRelevantTeamSize -or $SalaryRelevantTeamSize -le 0) {
        Write-Error "SalaryRelevantTeamSize not set or invalid in config.ps1!"
        exit 1
    }

    $transactionsCurrentSeason = Get-LeagueTransactionsCurrentSeasonInMemory -leagueID $LeagueID
    $transactionsCurrentSeason = Resolve-LeagueTransactionDraftPickTypesInMemory `
        -transactions $transactionsCurrentSeason

    if ($transactionsCurrentSeason) {
        Write-Host "Transactions for current season prepared in memory." -ForegroundColor Green
    } else {
        Write-Host "No transactions for current season generated." -ForegroundColor Yellow
    }

    $drafts = Update-LeagueDraftsOrderAwareFromTransactions `
        -transactions $transactionsCurrentSeason `
        -leagueID $LeagueID
    if (-not $drafts -or @($drafts).Count -eq 0) {
        Write-Warning "Update-LeagueDraftsOrderAwareFromTransactions returned no drafts. Falling back to local Drafts.json."
        $drafts = Get-LeagueDraftsLocal
    }
    $transactionsCurrentSeason = Add-LeagueTransactionDraftPickDetailsInMemory `
        -transactions $transactionsCurrentSeason `
        -drafts $drafts
    Save-TransactionsCurrentSeason -transactions $transactionsCurrentSeason

    $league = Get-CanonicalCurrentLeagueRaw -CanonicalLeagueID $CanonicalLeagueID
    $teamData = Get-CanonicalCurrentTeamsForLeague -CanonicalLeagueID $CanonicalLeagueID
    $playoffs = Get-CanonicalCurrentPlayoffs -CanonicalLeagueID $CanonicalLeagueID
    $standings = Get-StandingsLocal

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
        $awardsByTeamId = @{}
        if($standingSeason.Awards){
            foreach ($award in $standingSeason.Awards) {
                if (-not $awardsByTeamId.ContainsKey($award.TeamID)) { $awardsByTeamId[$award.TeamID] = @() }
                $awardsByTeamId[$award.TeamID] += $award
            }
        }

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

            if ($awardsByTeamId.ContainsKey($team.TeamID)) {
                $team.Placements[$key]["Awards"] = $awardsByTeamId[$team.TeamID] | Select-Object * -ExcludeProperty TeamID, Owner, TeamName
            } else {
                $team.Placements[$key]["Awards"] = @()
            }
        }
    }

    Write-Host "Enriching team data with draft pick keys..." -ForegroundColor Yellow
    $teamData = Add-DraftPickKeysToTeams -teams $teamData -drafts $drafts

    $playersData = Get-PlayersFromFile
    $topCount = [int]$SalaryRelevantTeamSize * [int]$teamData.Count
    if ($topCount -le 0) {
        Write-Error "Invalid topCount for Salary Cap calculation. SalaryRelevantTeamSize=$SalaryRelevantTeamSize, TeamCount=$($teamData.Count)"
        exit 1
    }

    $topPlayers = $playersData | Sort-Object -Property Salary -Descending | Select-Object -First $topCount
    $topPlayersProjected = $playersData | Sort-Object -Property SalaryProjected -Descending | Select-Object -First $topCount
    if ($topPlayers.Count -eq 0 -or $topPlayersProjected.Count -eq 0) {
        Write-Error "No players found for Salary Cap calculation!"
        exit 1
    }
    Write-Host "Top $topCount players considered for Salary Cap calculation." -ForegroundColor Yellow

    $avgSalary = ($topPlayers | Measure-Object -Property Salary -Average).Average
    $avgSalaryProjected = ($topPlayersProjected | Measure-Object -Property SalaryProjected -Average).Average
    $salaryCapTotal = [math]::Round($avgSalary * $SalaryRelevantTeamSize * 0.9)
    $salaryCapProjected = [math]::Round($avgSalaryProjected * $SalaryRelevantTeamSize * 0.9)
    Write-Host "Salary Cap (current): $($salaryCapTotal.ToString("N0"))" -ForegroundColor Yellow
    Write-Host "Salary Cap (projected): $($salaryCapProjected.ToString("N0"))" -ForegroundColor Yellow

    $playoffStart = $league.settings.playoff_week_start
    Write-Host "Playoff start week: Week $playoffStart" -ForegroundColor Yellow

    $repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))
    $currentLeagueSourceFile = Join-Path $repoRoot "source-data\leagues\$CanonicalLeagueID\seasons\$currentSeason\league.json"
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

    $waiversOpen = [int]$league.settings.disable_adds -eq 0
    $nextWaiverRun = $null
    $nextWaiverRunUtc = Resolve-LeagueNextWaiverRunUtc -League $league
    if ($null -ne $nextWaiverRunUtc) { $nextWaiverRun = $nextWaiverRunUtc.ToString("yyyy-MM-ddTHH:mm:ssZ") }
    $acquisitionCapability = Resolve-TemporaryWaiverOnlyAcquisitionCapability `
        -WaiversOpen $waiversOpen `
        -NextWaiverRun $nextWaiverRun

    $decisionWindowsAsJson = New-CurrentLeagueDecisionWindowsReadModel `
        -League $league `
        -Teams $teamData `
        -Players $playersData `
        -Schedule $schedule `
        -LastLineupWeek ([int]$lastWeek) `
        -AcquisitionCapability $acquisitionCapability

    if ($schedule) {
        $sortedGames = $schedule | Sort-Object { $_.gameID }
        foreach ($game in $sortedGames) {
            if ($game.gameStatus -notmatch '^Final') {
                if ($game.gameWeek -match 'Week (\d+)') {
                    $currentWeek = [int]$matches[1]
                    Write-Host "-> Found first non-final game: $($game.gameID) (Week $currentWeek)" -ForegroundColor Yellow
                } else {
                    Write-Warning "Could not parse gameWeek for $($game.gameID): $($game.gameWeek)"
                }
                break
            }
        }

        if (-not $currentWeek -and $sortedGames.Count -gt 0) {
            if ($sortedGames[-1].gameWeek -match 'Week (\d+)') {
                $finalWeek = [int]$matches[1]
                Write-Host "All games final. Defaulting to last known week" -ForegroundColor DarkGray
            }
        } else {
            $finalWeek = $currentWeek - 1
        }

        if ($finalWeek -gt $lastWeek) {
            $finalWeek = $lastWeek
            Write-Host "Adjusting final week to last league week: Week $finalWeek" -ForegroundColor DarkGray
        }
    }

    if ($finalWeek -ge 0) {
        Write-Host "Final active week detected: Week $finalWeek" -ForegroundColor Yellow
    } else {
        Write-Host "Could not determine current week." -ForegroundColor DarkYellow
    }

    $seasonKickoffUtc = Get-LeagueSeasonKickoffUtc -Schedule $schedule
    $seasonKickoff = if ($null -ne $seasonKickoffUtc) { $seasonKickoffUtc.ToString("yyyy-MM-ddTHH:mm:ssZ") } else { $null }
    $playoffStartUtc = Get-LeaguePlayoffStartUtc -Schedule $schedule -PlayoffStartWeek ([int]$playoffStart)
    $playoffStartAt = if ($null -ne $playoffStartUtc) { $playoffStartUtc.ToString("yyyy-MM-ddTHH:mm:ssZ") } else { $null }

    $matchupWeek = Resolve-FantasyMatchupLoadWeek `
        -DecisionWindows $decisionWindowsAsJson `
        -LastLeagueWeek ([int]$lastWeek) `
        -LeagueComplete ([string]$league.status -eq "complete")

    $fantasyGameContextAsJson = $null
    $matchupRows = @()
    $activeMatchupScoreEvidenceAvailable = $matchupWeek -le 0
    if ($matchupWeek -gt 0) {
        $matchupLoad = Get-CanonicalCurrentMatchupLoad -CanonicalLeagueID $CanonicalLeagueID -Season ([int]$league.season) -Week $matchupWeek
        if ($matchupLoad.Success) {
            $activeMatchupScoreEvidenceAvailable = $true
            $matchupRows = @($matchupLoad.Rows)

            if ([int]$decisionWindowsAsJson.LineupWeek -eq $matchupWeek) {
                $fantasyMatchupFacts = @(ConvertTo-FgcCurrentMatchupFacts -Season ([string]$league.season) -Week $matchupWeek -MatchupRows $matchupRows)
                $weekIsFinal = $lastScoredLeg -ge $matchupWeek
                $fantasyGameContextAsJson = New-FantasyGameContextReadModel `
                    -LeagueID $LeagueID `
                    -Season ([string]$league.season) `
                    -Week $matchupWeek `
                    -DecisionFacts $decisionWindowsAsJson `
                    -FantasyMatchups $fantasyMatchupFacts `
                    -Schedule @($schedule) `
                    -WeekIsFinal $weekIsFinal
            }
            else {
                Write-Warning "FantasyGameContext not overwritten because matchup Week $matchupWeek differs from DecisionWindows lineup Week $($decisionWindowsAsJson.LineupWeek)."
            }
        }
        else {
            Write-Warning "Canonical current matchup load for Week $matchupWeek failed. Matchups finality will fail closed for active score evidence and FantasyGameContext keeps its previous generated file."
        }
    }

    $matchupsAsJson = New-MatchupSeasonReadModel `
        -CanonicalLeagueID $CanonicalLeagueID `
        -Season ([int]$league.season) `
        -Standings @($standings) `
        -DecisionFacts $decisionWindowsAsJson `
        -LiveMatchupRows @($matchupRows) `
        -LiveMatchupWeek $matchupWeek `
        -ActiveScoreEvidenceAvailable $activeMatchupScoreEvidenceAvailable

    $cutsAllowed = $true
    $cutsMetaText = ""
    Write-Host "Daily Waivers active per settings: $waiversOpen" -ForegroundColor Yellow
    $waiversMetaText = ""
    $tradeReviewDays = if ($null -ne $league.settings.trade_review_days) { [int]$league.settings.trade_review_days } else { 0 }
    $tradesOpen = [int]$league.settings.disable_trades -eq 0
    $tradesMetaTextParts = @()

    if (-not $tradesOpen) { $tradesMetaTextParts += "Disabled in Sleeper" }
    if ($tradeReviewDays -gt 0) {
        $tradesOpen = $false
        $tradesMetaTextParts += "Trades will be declined by Commissioner Review"
    }

    $tradeDeadlineWeek = Resolve-LeagueTradeDeadlineWeek -TradeDeadline $league.settings.trade_deadline
    $leagueWeekForTradeDeadline = $currentWeek
    if ($leagueWeekForTradeDeadline -le 0) { $leagueWeekForTradeDeadline = $finalWeek }
    if ($null -ne $tradeDeadlineWeek -and $leagueWeekForTradeDeadline -ge $tradeDeadlineWeek) {
        $tradesOpen = $false
        $tradesMetaTextParts += "Trade Deadline reached"
    }

    $tradesMetaText = $tradesMetaTextParts -join " | "
    Write-Host "Trade review days: $tradeReviewDays" -ForegroundColor Yellow
    Write-Host "Trades open: $tradesOpen | Trades meta: $tradesMetaText" -ForegroundColor Yellow

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
        $nextWaiverRun = $null
        $tradesOpen = $false
    }

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

    $matchupsCompare = {
        param($oldMatchups, $newMatchups)
        Test-MatchupSeasonReadModelChanged -OldData $oldMatchups -NewData $newMatchups
    }
    Save-JsonFile `
        -TargetFile $config.MatchupsFile `
        -Type "Matchups" `
        -Data $matchupsAsJson `
        -CompareScript $matchupsCompare `
        -UpdateTimestamp

    if ($null -ne $fantasyGameContextAsJson) {
        $fantasyGameContextCompare = {
            param($oldContext, $newContext)
            Test-FantasyGameContextReadModelChanged -OldData $oldContext -NewData $newContext
        }
        Save-JsonFile `
            -TargetFile $FantasyGameContextFile `
            -Type "FantasyGameContext" `
            -Data $fantasyGameContextAsJson `
            -CompareScript $fantasyGameContextCompare `
            -UpdateTimestamp
    }

    $compare = & Get-Compare
    Save-JsonFile -Type "League" -Data $leagueAsJson -CompareScript $compare -CreateBackup -UpdateTimestamp

    Update-MatchupHistoryReadModels `
        -CanonicalLeagueID $CanonicalLeagueID `
        -CurrentSeason ([int]$league.season) `
        -Standings @($standings) `
        -Config $config | Out-Null
    Update-PastSeasonsIndex -Config $config | Out-Null

    try {
        Ensure-PreviousFantasyGameContextHistory -CurrentSeason ([int]$league.season)
    }
    catch {
        Write-Warning "Historical FantasyGameContext materialization failed without blocking the current League refresh. $_"
    }

    exit 0
}
catch {
    Write-Error "An error occurred: $_"
    exit 1
}
