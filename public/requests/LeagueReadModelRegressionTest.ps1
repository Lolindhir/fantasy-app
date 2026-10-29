$ErrorActionPreference = "Stop"

Import-Module "$PSScriptRoot\utils\league\LeagueOverviewUtils.psm1" -Force
Import-Module "$PSScriptRoot\utils\league\CanonicalLeagueCoreUtils.psm1" -Force
Import-Module "$PSScriptRoot\utils\league\CanonicalPlayoffUtils.psm1" -Force
Import-Module "$PSScriptRoot\utils\league\CanonicalMatchupUtils.psm1" -Force
Import-Module "$PSScriptRoot\utils\league\FantasyGameContextUtils.psm1" -Force
Import-Module "$PSScriptRoot\utils\league\StandingUtils.psm1" -Force
Import-Module "$PSScriptRoot\utils\general\AvatarUtils.psm1" -Force

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
Assert-True -Condition $requestLeague.Contains("Resolve-LeagueTradeDeadlineWeek") -Message "RequestLeague does not normalize the trade deadline before publishing League.json."
Assert-True -Condition $requestLeague.Contains("SeasonKickoff           = `$seasonKickoff") -Message "RequestLeague does not publish SeasonKickoff."
Assert-Equal -Actual (Get-OccurrenceCount -Text $requestLeague -Needle "Matchups                = `$matchupSnapshot") -Expected 0 -Message "RequestLeague still publishes the legacy League.Matchups snapshot."
Assert-Equal -Actual (Get-OccurrenceCount -Text $requestLeague -Needle "ConvertTo-LeagueMatchupSnapshot") -Expected 0 -Message "RequestLeague still builds the legacy League.Matchups snapshot."
Assert-Equal -Actual (Get-OccurrenceCount -Text $requestLeague -Needle "Update-MatchupHistoryReadModels") -Expected 0 -Message "RequestLeague regenerates the Matchups history; the weekly RequestHistoricalAppReadModels owns it (Issue 1189)."
Assert-Equal -Actual (Get-OccurrenceCount -Text $requestLeague -Needle "FantasyGameContextHistory") -Expected 0 -Message "RequestLeague still carries the FantasyGameContext history writer (Issue 1189)."
Assert-True -Condition $requestLeague.Contains("CanonicalLeagueCoreUtils.psm1") -Message "RequestLeague does not import the canonical League Core consumer."
Assert-True -Condition $requestLeague.Contains("CanonicalPlayoffUtils.psm1") -Message "RequestLeague does not import the canonical Playoff consumer."
Assert-True -Condition $requestLeague.Contains("CanonicalMatchupUtils.psm1") -Message "RequestLeague does not import the canonical current Matchup consumer."
Assert-True -Condition (-not $requestLeague.Contains("\utils\league\PlayoffUtils.psm1")) -Message "RequestLeague still imports the legacy live Playoff adapter."
Assert-True -Condition $requestLeague.Contains("Get-CanonicalCurrentLeagueRaw -CanonicalLeagueID `$CanonicalLeagueID") -Message "RequestLeague does not use canonical current League metadata/settings."
Assert-True -Condition $requestLeague.Contains("Get-CanonicalCurrentTeamsForLeague -CanonicalLeagueID `$CanonicalLeagueID") -Message "RequestLeague does not use canonical current Members/Rosters team data."
Assert-Equal -Actual (Get-OccurrenceCount -Text $requestLeague -Needle "Get-LeagueRaw") -Expected 0 -Message "RequestLeague still performs a direct current League provider read."
Assert-Equal -Actual (Get-OccurrenceCount -Text $requestLeague -Needle "Get-TeamsForLeague") -Expected 0 -Message "RequestLeague still performs the legacy current Teams provider read."
Assert-Equal -Actual (Get-OccurrenceCount -Text $requestLeague -Needle "Get-Playoffs") -Expected 0 -Message "RequestLeague still performs the legacy live Playoffs read."
Assert-Equal -Actual (Get-OccurrenceCount -Text $requestLeague -Needle "Get-CanonicalCurrentPlayoffs") -Expected 1 -Message "RequestLeague must use exactly one canonical current Playoffs read."
Assert-Equal -Actual (Get-OccurrenceCount -Text $requestLeague -Needle "Get-FgcCurrentMatchupLoad") -Expected 0 -Message "RequestLeague still performs the legacy live current-matchup provider read after the 6O cutover."
Assert-Equal -Actual (Get-OccurrenceCount -Text $requestLeague -Needle "Get-CanonicalCurrentMatchupLoad") -Expected 1 -Message "RequestLeague must use exactly one canonical current Matchup read."
Assert-True -Condition $requestLeague.Contains("Get-CanonicalCurrentMatchupLoad -CanonicalLeagueID `$CanonicalLeagueID -Season ([int]`$league.season) -Week `$matchupWeek") -Message "RequestLeague canonical current Matchup read does not bind canonical league, season and active week explicitly."
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

# League overview read-model helpers normalize optional deadline settings and
# deterministic kickoff facts without frontend derivation.
Assert-Equal -Actual (Resolve-LeagueTradeDeadlineWeek -TradeDeadline $null) -Expected $null -Message "Null trade deadline must stay null."
Assert-Equal -Actual (Resolve-LeagueTradeDeadlineWeek -TradeDeadline 0) -Expected $null -Message "Trade deadline week 0 must normalize to null."
Assert-Equal -Actual (Resolve-LeagueTradeDeadlineWeek -TradeDeadline -1) -Expected $null -Message "Negative trade deadline must normalize to null."
Assert-Equal -Actual (Resolve-LeagueTradeDeadlineWeek -TradeDeadline "off") -Expected $null -Message "Non-numeric trade deadline must normalize to null."
Assert-Equal -Actual (Resolve-LeagueTradeDeadlineWeek -TradeDeadline 99) -Expected $null -Message "Sleeper trade deadline sentinel 99 must normalize to null."
Assert-Equal -Actual (Resolve-LeagueTradeDeadlineWeek -TradeDeadline 11) -Expected 11 -Message "Positive trade deadline week changed unexpectedly."

$scheduleFixture = @(
    [PSCustomObject]@{ seasonType = "Preseason"; gameTime_epoch = "1788000000" },
    [PSCustomObject]@{ seasonType = "Regular Season"; gameTime_epoch = "1789318800" },
    [PSCustomObject]@{ seasonType = "Regular Season"; gameTime_epoch = "1788999600" }
)
$kickoff = Get-LeagueSeasonKickoffUtc -Schedule $scheduleFixture
$expectedKickoff = [DateTimeOffset]::FromUnixTimeSeconds(1788999600).UtcDateTime
Assert-Equal -Actual $kickoff.ToString("o") -Expected $expectedKickoff.ToString("o") -Message "Season kickoff did not use the earliest regular-season game."

$leagueOverviewUtils = Get-Content "$PSScriptRoot\utils\league\LeagueOverviewUtils.psm1" -Raw
Assert-Equal -Actual (Get-OccurrenceCount -Text $leagueOverviewUtils -Needle "ConvertTo-LeagueMatchupSnapshot") -Expected 0 -Message "LeagueOverviewUtils still contains the legacy matchup snapshot converter."
Assert-Equal -Actual (Get-OccurrenceCount -Text $leagueOverviewUtils -Needle "Get-LeagueMatchupSnapshot") -Expected 0 -Message "LeagueOverviewUtils still contains the legacy matchup snapshot loader."

$matchupReadModelUtils = Get-Content "$PSScriptRoot\utils\league\MatchupReadModelUtils.psm1" -Raw
Assert-Equal -Actual (Get-OccurrenceCount -Text $matchupReadModelUtils -Needle "Set-Alias -Name Ensure-MatchupHistoryReadModels") -Expected 0 -Message "MatchupReadModelUtils still exposes the transitional history alias."
Assert-True -Condition $matchupReadModelUtils.Contains("Update-MatchupHistoryReadModels") -Message "MatchupReadModelUtils no longer exposes the approved public history API."


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
$canonicalLeagueCoreShadow = Get-CanonicalCurrentLeagueCoreShadow -CanonicalLeagueID "nfl-reise"

$canonicalPlayoffUtils = Get-Content "$PSScriptRoot\utils\league\CanonicalPlayoffUtils.psm1" -Raw
Assert-True -Condition (-not $canonicalPlayoffUtils.Contains("Get-SleeperWinnersBracket")) -Message "Canonical Playoff shadow performs a live Sleeper winners-bracket read."
Assert-True -Condition (-not $canonicalPlayoffUtils.Contains("Get-SleeperLosersBracket")) -Message "Canonical Playoff shadow performs a live Sleeper losers-bracket read."
Assert-True -Condition (-not $canonicalPlayoffUtils.Contains("Get-Playoffs")) -Message "Canonical Playoff shadow delegates to the legacy live Playoff adapter."
Assert-True -Condition (-not $canonicalPlayoffUtils.Contains("Invoke-RestMethod")) -Message "Canonical Playoff shadow performs a direct HTTP read."

$canonicalPlayoffs = Get-CanonicalCurrentPlayoffs -CanonicalLeagueID "nfl-reise"
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

# Current matchup adapter must reconstruct the persisted Sleeper provider semantics
# from canonical week-partitioned data-source without live-provider fallback.
$canonicalMatchupUtils = Get-Content "$PSScriptRoot\utils\league\CanonicalMatchupUtils.psm1" -Raw
Assert-True -Condition (-not $canonicalMatchupUtils.Contains("Get-SleeperMatchups")) -Message "Canonical current matchup shadow performs a live Sleeper matchup read."
Assert-True -Condition (-not $canonicalMatchupUtils.Contains("Invoke-RestMethod")) -Message "Canonical current matchup shadow performs a direct HTTP read."
Assert-True -Condition (-not $canonicalMatchupUtils.Contains("Get-FgcCurrentMatchupLoad")) -Message "Canonical current matchup shadow delegates to the legacy live matchup loader."

$currentMatchupSeason = [int]$canonicalLeagueCoreShadow.League.season
$currentMatchupWeek = [int]$canonicalLeagueCoreShadow.League.settings.leg
if ($currentMatchupWeek -le 0) {
    $currentMatchupWeek = [int]$canonicalLeagueCoreShadow.League.settings.last_scored_leg + 1
}
Assert-True -Condition ($currentMatchupWeek -gt 0) -Message "Canonical current matchup parity could not resolve a positive active week."

$rawCurrentMatchupPath = Join-Path $repoRoot "data-source/providers/sleeper/leagues/$providerLeagueID/matchups/week-$currentMatchupWeek.json"
Assert-True -Condition (Test-Path $rawCurrentMatchupPath) -Message "Persisted current Sleeper matchup source is missing for parity."
$rawCurrentMatchupRows = @(
    Get-Content $rawCurrentMatchupPath -Raw |
        ConvertFrom-Json |
        Sort-Object { [int]$_.roster_id }
)
$canonicalCurrentMatchupLoad = Get-CanonicalCurrentMatchupLoad -CanonicalLeagueID "nfl-reise" -Season $currentMatchupSeason -Week $currentMatchupWeek
Assert-True -Condition ([bool]$canonicalCurrentMatchupLoad.Success) -Message "Canonical current matchup shadow failed to load."
$canonicalCurrentMatchupRows = @($canonicalCurrentMatchupLoad.Rows | Sort-Object { [int]$_.roster_id })
Assert-Equal -Actual $canonicalCurrentMatchupRows.Count -Expected $rawCurrentMatchupRows.Count -Message "Canonical current matchup shadow row count differs from persisted Sleeper raw."

function Select-CurrentMatchupProviderComparable {
    param([Parameter(Mandatory = $true)]$Row)

    $playerPoints = @(
        $Row.players_points.PSObject.Properties |
            Sort-Object Name |
            ForEach-Object {
                [PSCustomObject][ordered]@{
                    PlayerID = [string]$_.Name
                    Points   = if ($null -eq $_.Value) { $null } else { [double]$_.Value }
                }
            }
    )

    # Sleeper marks an unfilled starter slot with "0". The canonical layer treats it as "no player"
    # (issue #940), so the provider side drops those slots together with their parallel points.
    $starterIds = @($Row.starters | ForEach-Object { [string]$_ })
    $starterPointValues = @($Row.starters_points)
    $filledStarters = @()
    $filledStarterPoints = @()
    for ($i = 0; $i -lt $starterIds.Count; $i++) {
        if ($starterIds[$i] -eq '0') { continue }
        $filledStarters += $starterIds[$i]
        $filledStarterPoints += $(if ($null -eq $starterPointValues[$i]) { $null } else { [double]$starterPointValues[$i] })
    }

    return [PSCustomObject][ordered]@{
        roster_id       = [int]$Row.roster_id
        matchup_id      = if ($null -eq $Row.matchup_id) { $null } else { [int]$Row.matchup_id }
        players         = @($Row.players | ForEach-Object { [string]$_ })
        starters        = $filledStarters
        players_points  = $playerPoints
        starters_points = $filledStarterPoints
        points          = if ($null -eq $Row.points) { $null } else { [double]$Row.points }
        custom_points   = if ($null -eq $Row.custom_points) { $null } else { [double]$Row.custom_points }
    }
}

$rawCurrentMatchupComparable = @($rawCurrentMatchupRows | ForEach-Object { Select-CurrentMatchupProviderComparable -Row $_ })
$canonicalCurrentMatchupComparable = @($canonicalCurrentMatchupRows | ForEach-Object { Select-CurrentMatchupProviderComparable -Row $_ })
Assert-StandingsJsonEqual -Actual $canonicalCurrentMatchupComparable -Expected $rawCurrentMatchupComparable -Message "Canonical current matchup shadow does not reconstruct persisted Sleeper provider semantics."

$rawCurrentMatchupFacts = @(ConvertTo-FgcCurrentMatchupFacts -Season ([string]$currentMatchupSeason) -Week $currentMatchupWeek -MatchupRows $rawCurrentMatchupRows)
$canonicalCurrentMatchupFacts = @(ConvertTo-FgcCurrentMatchupFacts -Season ([string]$currentMatchupSeason) -Week $currentMatchupWeek -MatchupRows $canonicalCurrentMatchupRows)
Assert-StandingsJsonEqual -Actual $canonicalCurrentMatchupFacts -Expected $rawCurrentMatchupFacts -Message "Canonical current matchup shadow changes downstream FantasyGameContext matchup facts."

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

# --- Issue 1189: historical Matchups and FantasyGameContext are regenerated, never skipped or read from archives ---
$matchupCore = Get-Content "$PSScriptRoot\utils\league\MatchupReadModelCore.ps1" -Raw
$contextCore = Get-Content "$PSScriptRoot\utils\league\FantasyGameContextCore.ps1" -Raw
Assert-True -Condition ($matchupCore -notmatch 'Test-Path \$targetFile\)\s*\{\s*continue') -Message "Matchups history skips existing files again (Issue 1189)."
Assert-True -Condition ($contextCore -notmatch 'Test-Path \$targetFile\)\s*\{\s*return') -Message "FantasyGameContext history skips existing files again (Issue 1189)."
Assert-True -Condition (-not $contextCore.Contains('Schedule_$')) -Message "FantasyGameContext history reads the Schedule archive again (Issue 1189)."
Assert-True -Condition ($contextCore.Contains('Get-CanonicalAppSchedule')) -Message "FantasyGameContext history no longer takes the canonical NFL schedule (Issue 1189)."

$historyTestDir = Join-Path ([System.IO.Path]::GetTempPath()) ("history-regeneration-" + [guid]::NewGuid().ToString('N'))
try {
    $historyFile = Join-Path $historyTestDir 'nested/Model_2030.json'
    $historyChanged = { param($oldData, $newData) (($oldData | ConvertTo-Json -Depth 10 -Compress) -ne ($newData | ConvertTo-Json -Depth 10 -Compress)) }
    $modelV1 = [PSCustomObject][ordered]@{ SchemaVersion = 1; Weeks = @([PSCustomObject][ordered]@{ Week = 1; CompletionState = 'unknown' }) }
    $modelV2 = [PSCustomObject][ordered]@{ SchemaVersion = 1; Weeks = @([PSCustomObject][ordered]@{ Week = 1; CompletionState = 'final' }) }

    Assert-Equal -Actual (Save-HistoricalReadModelIfChanged -TargetFile $historyFile -Model $modelV1 -ChangedScript $historyChanged) -Expected 'created' -Message "A missing historical file is not created."
    $hashAfterCreate = (Get-FileHash $historyFile).Hash
    Start-Sleep -Milliseconds 50
    Assert-Equal -Actual (Save-HistoricalReadModelIfChanged -TargetFile $historyFile -Model $modelV1 -ChangedScript $historyChanged) -Expected 'unchanged' -Message "An identical second run is not a no-op."
    Assert-Equal -Actual (Get-FileHash $historyFile).Hash -Expected $hashAfterCreate -Message "A no-op run rewrote the historical file."
    Assert-Equal -Actual (Save-HistoricalReadModelIfChanged -TargetFile $historyFile -Model $modelV2 -ChangedScript $historyChanged) -Expected 'updated' -Message "A corrected derivation is not adopted into the existing historical file."
    Assert-Equal -Actual (Get-Content $historyFile -Raw | ConvertFrom-Json).Weeks[0].CompletionState -Expected 'final' -Message "The corrected value was not written."
    Assert-Equal -Actual (Save-HistoricalReadModelIfChanged -TargetFile $historyFile -Model $modelV2 -ChangedScript $historyChanged) -Expected 'unchanged' -Message "The run after the correction is not a no-op."
}
finally {
    if (Test-Path $historyTestDir) { Remove-Item $historyTestDir -Recurse -Force }
}

$weeklyWorkflow = Get-Content "$PSScriptRoot\..\..\.github\workflows\update-transactions.yml" -Raw
Assert-True -Condition ($weeklyWorkflow.Contains('RequestHistoricalAppReadModels.ps1')) -Message "The weekly update-transactions run does not regenerate the historical App read models (Issue 1189)."

Write-Host "League transaction and overview regression tests passed." -ForegroundColor Green
