$ErrorActionPreference = "Stop"

Import-Module "$PSScriptRoot\utils\league\CanonicalLeagueCoreUtils.psm1" -Force
Import-Module "$PSScriptRoot\utils\league\CanonicalPlayoffUtils.psm1" -Force
Import-Module "$PSScriptRoot\utils\league\StandingUtils.psm1" -Force
Import-Module "$PSScriptRoot\utils\general\AvatarUtils.psm1" -Force
Import-Module "$PSScriptRoot\utils\player\PlayerValuationUtils.psm1" -ErrorAction Stop

function Assert-True {
    param(
        [Parameter(Mandatory = $true)][bool]$Condition,
        [Parameter(Mandatory = $true)][string]$Message
    )

    if (-not $Condition) { throw $Message }
}

function Assert-Equal {
    param(
        [AllowNull()]$Actual,
        [AllowNull()]$Expected,
        [Parameter(Mandatory = $true)][string]$Message
    )

    if ($Actual -ne $Expected) {
        throw "$Message Expected '$Expected', got '$Actual'."
    }
}

function Get-OccurrenceCount {
    param(
        [Parameter(Mandatory = $true)][string]$Text,
        [Parameter(Mandatory = $true)][string]$Needle
    )

    return ([regex]::Matches($Text, [regex]::Escape($Needle))).Count
}

# Since Issue 999 step 5b RequestLeague no longer builds Transactions or Drafts itself: the league history
# consumer generator writes them before RequestLeague runs in League Live; RequestLeague only reads Drafts.json.
$requestLeague = Get-Content "$PSScriptRoot\RequestLeague.ps1" -Raw
Assert-True -Condition $requestLeague.Contains('$drafts = Get-LeagueDraftsLocal') -Message "RequestLeague does not read the Drafts.json written by the league history consumer generator."
Assert-True -Condition $requestLeague.Contains("Get-LeagueLifecycle") -Message "RequestLeague does not take the lifecycle from the shared lifecycle model (ADR-073)."
foreach ($legacy in @("Resolve-LeagueStatusState", "Resolve-LeagueNextWaiverRunUtc", "Resolve-LeagueTradeDeadlineWeek", "Get-LeagueSeasonKickoffUtc", "Get-LeaguePlayoffStartUtc", "LeagueStatusSeasonStartBufferDays")) {
    Assert-Equal -Actual (Get-OccurrenceCount -Text $requestLeague -Needle $legacy) -Expected 0 -Message "RequestLeague still derives lifecycle state itself ($legacy); it belongs to lifecycle-v1."
}
foreach ($removed in @("LeagueUtils.psm1", "WaiverUtils.psm1", "LeagueOverviewUtils.psm1")) {
    Assert-True -Condition (-not (Test-Path "$PSScriptRoot\utils\league\$removed")) -Message "$removed was retired with the lifecycle cutover (Issue 1199 step 4)."
}
Assert-True -Condition $requestLeague.Contains("Get-LeagueDecisionWindows") -Message "RequestLeague does not take the Decision Windows from the shared Decision Windows function (ADR-074)."
Assert-Equal -Actual (Get-OccurrenceCount -Text $requestLeague -Needle "Resolve-PlayerScoringAvailabilityObservationTimes") -Expected 0 -Message "RequestLeague still carries scoring-availability observation times over from the previous DecisionWindows.json."
Assert-True -Condition $requestLeague.Contains("SeasonKickoff           = `$seasonKickoff") -Message "RequestLeague does not publish SeasonKickoff."
Assert-Equal -Actual (Get-OccurrenceCount -Text $requestLeague -Needle "Matchups                = `$matchupSnapshot") -Expected 0 -Message "RequestLeague still publishes the legacy League.Matchups snapshot."
Assert-Equal -Actual (Get-OccurrenceCount -Text $requestLeague -Needle "ConvertTo-LeagueMatchupSnapshot") -Expected 0 -Message "RequestLeague still builds the legacy League.Matchups snapshot."
Assert-Equal -Actual (Get-OccurrenceCount -Text $requestLeague -Needle "Update-MatchupHistoryReadModels") -Expected 0 -Message "RequestLeague regenerates the Matchups history; the weekly RequestHistoricalAppReadModels owns it (Issue 1189)."
Assert-Equal -Actual (Get-OccurrenceCount -Text $requestLeague -Needle "FantasyGameContextHistory") -Expected 0 -Message "RequestLeague still carries the FantasyGameContext history writer (Issue 1189)."
Assert-True -Condition $requestLeague.Contains("CanonicalLeagueCoreUtils.psm1") -Message "RequestLeague does not import the canonical League Core consumer."
Assert-True -Condition $requestLeague.Contains("CanonicalPlayoffUtils.psm1") -Message "RequestLeague does not import the canonical Playoff consumer."
Assert-True -Condition (-not $requestLeague.Contains("CanonicalMatchupUtils.psm1")) -Message "RequestLeague still imports the canonical current Matchup consumer; Matchups and FantasyGameContext come from tools/matchup_context_app_publish.py (ADR-075)."
Assert-True -Condition (-not $requestLeague.Contains("\utils\league\PlayoffUtils.psm1")) -Message "RequestLeague still imports the legacy live Playoff adapter."
Assert-True -Condition $requestLeague.Contains("Get-CanonicalCurrentLeagueRaw -CanonicalLeagueID `$CanonicalLeagueID") -Message "RequestLeague does not use canonical current League metadata/settings."
Assert-True -Condition $requestLeague.Contains("Get-CanonicalCurrentTeamsForLeague -CanonicalLeagueID `$CanonicalLeagueID") -Message "RequestLeague does not use canonical current Members/Rosters team data."
Assert-Equal -Actual (Get-OccurrenceCount -Text $requestLeague -Needle "Get-LeagueRaw") -Expected 0 -Message "RequestLeague still performs a direct current League provider read."
Assert-Equal -Actual (Get-OccurrenceCount -Text $requestLeague -Needle "Get-TeamsForLeague") -Expected 0 -Message "RequestLeague still performs the legacy current Teams provider read."
Assert-Equal -Actual (Get-OccurrenceCount -Text $requestLeague -Needle "Get-Playoffs") -Expected 0 -Message "RequestLeague still performs the legacy live Playoffs read."
Assert-Equal -Actual (Get-OccurrenceCount -Text $requestLeague -Needle "Get-CanonicalCurrentPlayoffs") -Expected 1 -Message "RequestLeague must use exactly one canonical current Playoffs read."
Assert-Equal -Actual (Get-OccurrenceCount -Text $requestLeague -Needle "Get-FgcCurrentMatchupLoad") -Expected 0 -Message "RequestLeague still performs the legacy live current-matchup provider read after the 6O cutover."
Assert-Equal -Actual (Get-OccurrenceCount -Text $requestLeague -Needle "Get-CanonicalCurrentMatchupLoad") -Expected 0 -Message "RequestLeague still reads the current matchups; the matchup context function owns them (ADR-075)."
Assert-Equal -Actual (Get-OccurrenceCount -Text $requestLeague -Needle "New-MatchupSeasonReadModel") -Expected 0 -Message "RequestLeague still builds the Matchups read model (ADR-075)."
$leagueLiveWorkflow = Get-Content (Join-Path (Join-Path $PSScriptRoot "..\..") ".github/workflows/league-live.yml") -Raw
Assert-True -Condition $leagueLiveWorkflow.Contains("materialization_scope: current") -Message "League Live does not run the combined current League source scope."
Assert-True -Condition $leagueLiveWorkflow.Contains("RequestLeaguePublication.ps1") -Message "League Live does not publish the App League read model."
Assert-True -Condition $leagueLiveWorkflow.Contains("league_history_app_publish.py write") -Message "League Live does not write Transactions.json and Drafts.json from the league history product."
Assert-True -Condition ($leagueLiveWorkflow.IndexOf("league_history_app_publish.py write") -lt $leagueLiveWorkflow.IndexOf("RequestLeaguePublication.ps1")) -Message "League Live must write the league history files before RequestLeague reads Drafts.json."
Assert-True -Condition $leagueLiveWorkflow.Contains("league_standings_app_publish.py write") -Message "League Live does not rebuild Standings."
# Standings must be published before League is built: League.json embeds the published Standings placement context.
Assert-True -Condition ($leagueLiveWorkflow.IndexOf("league_standings_app_publish.py write") -lt $leagueLiveWorkflow.IndexOf("RequestLeaguePublication.ps1")) -Message "League Live must rebuild Standings before League so team placement context is current."
$updateStandingsWorkflow = Get-Content (Join-Path (Join-Path $PSScriptRoot "..\..") ".github/workflows/update-standings.yml") -Raw
Assert-True -Condition (-not $updateStandingsWorkflow.Contains("  push:")) -Message "APP Standings workflow must not have push triggers; League Live owns input-driven rebuilds."
# The Standings writer runs on every League Live tick (Issue #987 step 4): the week basis depends on NFL game finality,
# which nfl-live commits outside this chain, so a change gate on League inputs would miss LeagueScoredWeek moves.
Assert-True -Condition $leagueLiveWorkflow.Contains("--path data-derived/league-standings") -Message "League Live does not publish the league-standings product."
Assert-True -Condition (-not $leagueLiveWorkflow.Contains("Detect changed Standings inputs")) -Message "League Live must not gate the Standings writer on League inputs."

# Standings consumers read the league-standings product, never the rendered Standings.json (Issue #1197).
foreach ($consumerName in @("RequestLeague.ps1")) {
    $consumerText = Get-Content (Join-Path $PSScriptRoot $consumerName) -Raw
    Assert-True -Condition $consumerText.Contains("Get-LeagueStandingsProduct") -Message "$consumerName does not read the league-standings product."
    Assert-True -Condition (-not $consumerText.Contains("Get-StandingsLocal")) -Message "$consumerName still reads the rendered Standings.json through Get-StandingsLocal."
    Assert-True -Condition (-not $consumerText.Contains("StandingsFile")) -Message "$consumerName still reads the rendered Standings.json."
}

$avatarCompareOld = [PSCustomObject]@{
    Place = 1; TeamID = 3; Owner = "FloDHL99"; OwnerAvatar = "owner.png"; TeamName = "Just Bill"; TeamAvatar = "historical.png";
    PlaceType = "Winner"; PlaceOrdinal = "1st"; PlaceCumulative = $null; PlaceAverage = $null; Championships = $null; RunnerUps = $null; Thirds = $null
}
$avatarCompareNew = $avatarCompareOld.PSObject.Copy()
$avatarCompareNew.TeamAvatar = "changed.png"
Assert-True -Condition (Compare-PlayoffStandings -oldPlayoffs @($avatarCompareOld) -newPlayoffs @($avatarCompareNew)) -Message "Playoff change detection ignores historical TeamAvatar changes."
Assert-True -Condition $requestLeague.Contains("'LeagueIDPrevious'") -Message "RequestLeague change detection does not track LeagueIDPrevious."
Assert-True -Condition $requestLeague.Contains("@('Settings','ScoringType','Playoffs')") -Message "RequestLeague change detection does not track canonical Settings, ScoringType and Playoffs structurally."
Assert-True -Condition $requestLeague.Contains("ConvertTo-Json -Depth 10 -Compress") -Message "RequestLeague canonical structured comparison is not structural."
Assert-True -Condition $requestLeague.Contains('$oldCurrent.Weeks') -Message "League change detection must compare historical weekly snapshots to avoid retaining stale data."
Assert-True -Condition $requestLeague.Contains('$newCurrent.Weeks') -Message "League change detection must notice new validated weekly product rows."
Assert-True -Condition $requestLeague.Contains('$oldWeeksJson -cne $newWeeksJson') -Message "League change detection ignores canonical current-season weekly standings changes."



function ConvertTo-StandingsComparableValue {
    param([AllowNull()]$Value)

    if ($null -eq $Value) { return $null }

    if ($Value -is [string] -or $Value -is [char] -or $Value -is [bool] -or $Value -is [ValueType]) {
        return $Value
    }

    if ($Value -is [System.Collections.IDictionary]) {
        $ordered = [ordered]@{}
        foreach ($key in @($Value.Keys | ForEach-Object { [string]$_ } | Sort-Object)) {
            $ordered[$key] = ConvertTo-StandingsComparableValue -Value $Value[$key]
        }
        return [PSCustomObject]$ordered
    }

    if ($Value -is [pscustomobject]) {
        $ordered = [ordered]@{}
        foreach ($property in @($Value.PSObject.Properties | Sort-Object Name)) {
            $ordered[$property.Name] = ConvertTo-StandingsComparableValue -Value $property.Value
        }
        return [PSCustomObject]$ordered
    }

    if ($Value -is [System.Collections.IEnumerable]) {
        return @($Value | ForEach-Object { ConvertTo-StandingsComparableValue -Value $_ })
    }

    return $Value
}

function Assert-StandingsJsonEqual {
    param(
        [AllowNull()]$Actual,
        [AllowNull()]$Expected,
        [Parameter(Mandatory = $true)][string]$Message
    )

    $actualJson = ConvertTo-StandingsComparableValue -Value $Actual | ConvertTo-Json -Depth 100 -Compress
    $expectedJson = ConvertTo-StandingsComparableValue -Value $Expected | ConvertTo-Json -Depth 100 -Compress
    if ($actualJson -ne $expectedJson) {
        throw "$Message Canonical historical output differs from the published read model."
    }
}

# Current League Core must reconstruct the source-owned League/Team inputs
# from canonical data without performing direct provider reads.
$canonicalLeagueCoreUtils = Get-Content "$PSScriptRoot\utils\league\CanonicalLeagueCoreUtils.psm1" -Raw
Assert-True -Condition (-not $canonicalLeagueCoreUtils.Contains("Get-LeagueRaw")) -Message "Canonical League Core shadow performs a legacy league read."
Assert-True -Condition (-not $canonicalLeagueCoreUtils.Contains("Get-Teams")) -Message "Canonical League Core shadow performs a legacy team read."
Assert-True -Condition (-not $canonicalLeagueCoreUtils.Contains("Get-SleeperMembers")) -Message "Canonical League Core shadow performs a direct Sleeper member read."
Assert-True -Condition (-not $canonicalLeagueCoreUtils.Contains("Get-SleeperRosters")) -Message "Canonical League Core shadow performs a direct Sleeper roster read."
Assert-True -Condition (-not $canonicalLeagueCoreUtils.Contains("Invoke-RestMethod")) -Message "Canonical League Core shadow performs a direct HTTP read."

$publishedLeague = Get-Content (Get-Config).LeagueFile -Raw | ConvertFrom-Json
$canonicalLeagueId = [string](Get-Config).CanonicalLeagueID
$canonicalLeagueCoreShadow = Get-CanonicalCurrentLeagueCoreShadow -CanonicalLeagueID $canonicalLeagueId
# Implicit metadata default must reproduce every explicit canonical League Core input.
Assert-StandingsJsonEqual -Actual (Get-CanonicalCurrentLeagueCoreShadow) -Expected $canonicalLeagueCoreShadow -Message "Default League Core shadow mismatch."
Assert-StandingsJsonEqual -Actual (Get-CanonicalCurrentLeagueRaw) -Expected $canonicalLeagueCoreShadow.League -Message "Default current League raw mismatch."
Assert-StandingsJsonEqual -Actual (Get-CanonicalCurrentTeamsForLeague) -Expected $canonicalLeagueCoreShadow.Teams -Message "Default current teams mismatch."
Assert-StandingsJsonEqual -Actual (Get-CanonicalLeagueSeasonLeagues) -Expected (Get-CanonicalLeagueSeasonLeagues -CanonicalLeagueID $canonicalLeagueId) -Message "Default historical League seasons mismatch."

$canonicalPlayoffUtils = Get-Content "$PSScriptRoot\utils\league\CanonicalPlayoffUtils.psm1" -Raw
Assert-True -Condition (-not $canonicalPlayoffUtils.Contains("Get-SleeperWinnersBracket")) -Message "Canonical Playoff shadow performs a live Sleeper winners-bracket read."
Assert-True -Condition (-not $canonicalPlayoffUtils.Contains("Get-SleeperLosersBracket")) -Message "Canonical Playoff shadow performs a live Sleeper losers-bracket read."
Assert-True -Condition (-not $canonicalPlayoffUtils.Contains("Get-Playoffs")) -Message "Canonical Playoff shadow delegates to the legacy live Playoff adapter."
Assert-True -Condition (-not $canonicalPlayoffUtils.Contains("Invoke-RestMethod")) -Message "Canonical Playoff shadow performs a direct HTTP read."

$canonicalPlayoffs = Get-CanonicalCurrentPlayoffs -CanonicalLeagueID $canonicalLeagueId
Assert-StandingsJsonEqual -Actual (Get-CanonicalCurrentPlayoffs) -Expected $canonicalPlayoffs -Message "Default current Playoff mismatch."
Assert-StandingsJsonEqual -Actual $canonicalPlayoffs -Expected $publishedLeague.Playoffs -Message "Canonical current Playoff shadow differs from published League.json::Playoffs."

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$providerLeagueID = [string]$canonicalLeagueCoreShadow.League.league_id
$rawWinnersPath = Join-Path $repoRoot "data-source/providers/sleeper/leagues/$providerLeagueID/winners-bracket.json"
$rawLosersPath = Join-Path $repoRoot "data-source/providers/sleeper/leagues/$providerLeagueID/losers-bracket.json"
$rawWinners = @((Get-Content $rawWinnersPath -Raw | ConvertFrom-Json))
$rawLosers = @((Get-Content $rawLosersPath -Raw | ConvertFrom-Json))
$shadowWinners = @($canonicalPlayoffs.WinnersBracket)
$shadowLosers = @($canonicalPlayoffs.LosersBracket)
Assert-StandingsJsonEqual -Actual $shadowWinners -Expected $rawWinners -Message "Canonical current winners bracket does not reconstruct raw Sleeper routing."
Assert-StandingsJsonEqual -Actual $shadowLosers -Expected $rawLosers -Message "Canonical current losers bracket does not reconstruct raw Sleeper routing."

Assert-Equal -Actual ([string]$canonicalLeagueCoreShadow.League.league_id) -Expected ([string]$publishedLeague.LeagueID) -Message "Canonical League Core provider LeagueID parity failed."
Assert-Equal -Actual ([string]$canonicalLeagueCoreShadow.League.name) -Expected ([string]$publishedLeague.Name) -Message "Canonical League Core name parity failed."
Assert-Equal -Actual ([string]$canonicalLeagueCoreShadow.League.season) -Expected ([string]$publishedLeague.Season) -Message "Canonical League Core season parity failed."
Assert-Equal -Actual ([string]$canonicalLeagueCoreShadow.League.season_type) -Expected ([string]$publishedLeague.SeasonType) -Message "Canonical League Core season type parity failed."
Assert-Equal -Actual ([int]$canonicalLeagueCoreShadow.League.total_rosters) -Expected ([int]$publishedLeague.TotalTeams) -Message "Canonical League Core team-count parity failed."
Assert-Equal -Actual ([string]$canonicalLeagueCoreShadow.League.previous_league_id) -Expected ([string]$publishedLeague.LeagueIDPrevious) -Message "Canonical League Core previous-LeagueID parity failed."

$canonicalLeagueAvatar = if ([string]::IsNullOrWhiteSpace([string]$canonicalLeagueCoreShadow.League.avatar)) {
    $null
}
else {
    Get-SleeperAvatar ([string]$canonicalLeagueCoreShadow.League.avatar)
}
Assert-Equal -Actual ([string]$canonicalLeagueAvatar) -Expected ([string]$publishedLeague.Avatar) -Message "Canonical League Core avatar parity failed."

$canonicalComparableSettings = $canonicalLeagueCoreShadow.League.settings | Select-Object * -ExcludeProperty daily_waivers_last_ran
$publishedComparableSettings = $publishedLeague.Settings | Select-Object * -ExcludeProperty daily_waivers_last_ran
Assert-StandingsJsonEqual -Actual $canonicalComparableSettings -Expected $publishedComparableSettings -Message "Canonical League Core stable-settings parity failed."
Assert-StandingsJsonEqual -Actual $canonicalLeagueCoreShadow.League.scoring_settings -Expected $publishedLeague.ScoringType -Message "Canonical League Core scoring settings parity failed."
Assert-StandingsJsonEqual -Actual @($canonicalLeagueCoreShadow.League.roster_positions) -Expected @($publishedLeague.RosterSize) -Message "Canonical League Core roster-position parity failed."

function Select-LeagueCoreTeamComparable {
    param([Parameter(Mandatory = $true)]$Team)

    return [PSCustomObject][ordered]@{
        Owner          = $Team.Owner
        OwnerID        = $Team.OwnerID
        OwnerAvatar    = $Team.OwnerAvatar
        Team           = $Team.Team
        TeamAbbr       = $Team.TeamAbbr
        TeamID         = $Team.TeamID
        TeamAvatar     = $Team.TeamAvatar
        MatchupID      = $Team.MatchupID
        WaiverPosition = $Team.WaiverPosition
        WaiverAdjusted = $Team.WaiverAdjusted
        IsCommissioner = $Team.IsCommissioner
        Roster         = @($Team.Roster)
        Reserve        = @($Team.Reserve)
        Taxi           = @($Team.Taxi)
        Starter        = @($Team.Starter)
    }
}

$canonicalCoreTeams = @(
    $canonicalLeagueCoreShadow.Teams |
        Sort-Object { [int]$_.TeamID } |
        ForEach-Object { Select-LeagueCoreTeamComparable -Team $_ }
)
$publishedCoreTeams = @(
    $publishedLeague.Teams |
        Sort-Object { [int]$_.TeamID } |
        ForEach-Object { Select-LeagueCoreTeamComparable -Team $_ }
)
Assert-Equal -Actual $canonicalCoreTeams.Count -Expected $publishedCoreTeams.Count -Message "Canonical League Core team count differs from published League.json."
Assert-StandingsJsonEqual -Actual $canonicalCoreTeams -Expected $publishedCoreTeams -Message "Canonical League Core team-source parity failed."

$weeklyWorkflow = Get-Content "$PSScriptRoot\..\..\.github\workflows\update-transactions.yml" -Raw
Assert-True -Condition ($weeklyWorkflow.Contains('tools/matchup_context_app_publish.py write --scope history')) -Message "The weekly update-transactions run does not regenerate the historical App read models (Issue 1189, ADR-075)."
Assert-True -Condition ($weeklyWorkflow.Contains('tools/weekly_recaps_app_publish.py write --scope history')) -Message "The weekly update-transactions run does not regenerate the historical WeeklyRecaps (Issue 1199 section 4)."
Assert-True -Condition $leagueLiveWorkflow.Contains('tools/weekly_recaps_app_publish.py write') -Message "League Live does not publish WeeklyRecaps from the computed recap function (Issue 1199 section 4)."
$requestLeaguePublicationText = Get-Content (Join-Path $PSScriptRoot "RequestLeaguePublication.ps1") -Raw
Assert-True -Condition (-not $requestLeaguePublicationText.Contains("RequestWeeklyRecaps.ps1")) -Message "RequestLeaguePublication still calls the PowerShell WeeklyRecaps generator (Issue 1199 section 4)."

# PlayerValuation cap input remains the newest week snapshot for the requested
# league/season; an empty or cross-league result must fail closed (Issue #1238).
$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("league-pv-snapshot-" + [Guid]::NewGuid().ToString("N"))
$seasonPath = Join-Path $tempRoot "data-derived/player-valuation/fixture-league/2030"
New-Item -ItemType Directory -Path $seasonPath -Force | Out-Null
try {
    foreach ($week in @(2, 9)) {
        [PSCustomObject]@{
            CanonicalLeagueID = "fixture-league"
            Season = 2030
            AsOfFinalScoredWeek = $week
            League = [PSCustomObject]@{
                TeamCount = 4
                SalaryRelevantTeamSize = 17
                SalaryCap = (1800 + $week)
                SalaryCapProjected = (1900 + $week)
            }
        } | ConvertTo-Json -Depth 6 | Set-Content -Path (Join-Path $seasonPath ("week-{0:00}.json" -f $week))
    }
    $latest = Get-PlayerValuationLatestSnapshot -CanonicalLeagueID "fixture-league" -Season 2030 -RepoRoot $tempRoot
    Assert-Equal -Actual ([int]$latest.AsOfFinalScoredWeek) -Expected 9 -Message "Latest PV snapshot must select the newest week."
    Assert-Equal -Actual ([int]$latest.League.TeamCount) -Expected 4 -Message "PV cap input must preserve its team count."
    Assert-Equal -Actual ([int]$latest.League.SalaryRelevantTeamSize) -Expected 17 -Message "PV cap input must preserve the relevant roster size."
    Assert-Equal -Actual ([int]$latest.League.SalaryCap) -Expected 1809 -Message "PV cap input must preserve current cap."
    Assert-Equal -Actual ([int]$latest.League.SalaryCapProjected) -Expected 1909 -Message "PV cap input must preserve projected cap."

    $noSnapshotRejected = $false
    try {
        Get-PlayerValuationLatestSnapshot -CanonicalLeagueID "fixture-league" -Season 2031 -RepoRoot $tempRoot | Out-Null
    }
    catch { $noSnapshotRejected = [string]$_.Exception.Message -like "*No PlayerValuation snapshot found*" }
    Assert-True -Condition $noSnapshotRejected -Message "Missing PlayerValuation snapshot must fail closed."

    $badPath = Join-Path $seasonPath "week-09.json"
    $bad = Get-Content -Path $badPath -Raw | ConvertFrom-Json
    $bad.CanonicalLeagueID = "other-league"
    $bad | ConvertTo-Json -Depth 6 | Set-Content -Path $badPath
    $crossLeagueRejected = $false
    try {
        Get-PlayerValuationLatestSnapshot -CanonicalLeagueID "fixture-league" -Season 2030 -RepoRoot $tempRoot | Out-Null
    }
    catch { $crossLeagueRejected = [string]$_.Exception.Message -like "*belongs to other-league*" }
    Assert-True -Condition $crossLeagueRejected -Message "Cross-league valuation snapshot must fail closed."
}
finally {
    Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host "League transaction, overview and PV snapshot regression tests passed." -ForegroundColor Green
