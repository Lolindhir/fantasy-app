$ErrorActionPreference = "Stop"

Import-Module "$PSScriptRoot\utils\league\DecisionWindowUtils.psm1" -ErrorAction Stop -Force
Import-Module "$PSScriptRoot\utils\general\FileUtils.psm1" -ErrorAction Stop -Force

function Assert-Equal {
    param(
        [Parameter(Mandatory = $true)][object]$Actual,
        [Parameter(Mandatory = $true)][object]$Expected,
        [Parameter(Mandatory = $true)][string]$Message
    )

    if ([string]$Actual -ne [string]$Expected) {
        throw "$Message Expected '$Expected', got '$Actual'."
    }
}

function Assert-True {
    param(
        [Parameter(Mandatory = $true)][bool]$Condition,
        [Parameter(Mandatory = $true)][string]$Message
    )

    if (-not $Condition) { throw $Message }
}

function New-TestGame {
    param(
        [string]$GameID,
        [int]$Week,
        [string]$StartsAtUtc,
        [string]$AwayTeamID,
        [string]$HomeTeamID,
        [string]$AwayTeamAbbr = "AWY",
        [string]$HomeTeamAbbr = "HME"
    )

    return [PSCustomObject]@{
        GameID       = $GameID
        Week         = $Week
        StartsAtUtc  = $StartsAtUtc
        AwayTeamID   = $AwayTeamID
        HomeTeamID   = $HomeTeamID
        AwayTeamAbbr = $AwayTeamAbbr
        HomeTeamAbbr = $HomeTeamAbbr
    }
}

$schedule = @(
    New-TestGame -GameID "g1" -Week 1 -StartsAtUtc "2026-09-10T00:20:00Z" -AwayTeamID "1" -HomeTeamID "2" -AwayTeamAbbr "AAA" -HomeTeamAbbr "BBB"
    New-TestGame -GameID "g2" -Week 1 -StartsAtUtc "2026-09-13T17:00:00Z" -AwayTeamID "3" -HomeTeamID "4" -AwayTeamAbbr "CCC" -HomeTeamAbbr "DDD"
    New-TestGame -GameID "g3" -Week 1 -StartsAtUtc "2026-09-13T17:00:00Z" -AwayTeamID "5" -HomeTeamID "6" -AwayTeamAbbr "EEE" -HomeTeamAbbr "FFF"
    New-TestGame -GameID "g4" -Week 1 -StartsAtUtc "2026-09-13T20:05:00Z" -AwayTeamID "7" -HomeTeamID "8"
    New-TestGame -GameID "g5" -Week 1 -StartsAtUtc "2026-09-13T20:25:00Z" -AwayTeamID "9" -HomeTeamID "10"
    New-TestGame -GameID "g6" -Week 1 -StartsAtUtc "2026-09-19T17:00:00Z" -AwayTeamID "11" -HomeTeamID "12"
    New-TestGame -GameID "g7" -Week 2 -StartsAtUtc "2026-09-17T00:20:00Z" -AwayTeamID "1" -HomeTeamID "3"
    New-TestGame -GameID "g8" -Week 2 -StartsAtUtc "2026-09-20T17:00:00Z" -AwayTeamID "2" -HomeTeamID "4"
    New-TestGame -GameID "g9" -Week 3 -StartsAtUtc "2026-09-27T17:00:00Z" -AwayTeamID "5" -HomeTeamID "7"
)

$rosters = @(
    [PSCustomObject]@{ FantasyTeamID = 101; PlayerIDs = @("p1", "p2", "p3", "p4", "p5"); StarterIDs = @("p1", "p2", "p3") },
    [PSCustomObject]@{ FantasyTeamID = 202; PlayerIDs = @("p6"); StarterIDs = @("p6") }
)
$assignments = @(
    [PSCustomObject]@{ PlayerID = "p1"; NFLTeamID = "1" },
    [PSCustomObject]@{ PlayerID = "p2"; NFLTeamID = "3" },
    [PSCustomObject]@{ PlayerID = "p3"; NFLTeamID = "13" },
    [PSCustomObject]@{ PlayerID = "p4"; NFLTeamID = $null },
    [PSCustomObject]@{ PlayerID = "p6"; NFLTeamID = "5" }
)

# Exact-kickoff windows: simultaneous games group, nearby unequal times do not.
$facts = Get-DecisionWindowFacts -Season "2026" -Week 1 -ScheduleGames $schedule -FantasyRosters $rosters -PlayerTeamAssignments $assignments -ExpectedStarterCount 3
Assert-Equal -Actual @($facts.DecisionWindows).Count -Expected 5 -Message "Week 1 should produce five exact-kickoff Decision Windows."
$simultaneous = $facts.DecisionWindows | Where-Object { $_.StartsAtUtc -eq "2026-09-13T17:00:00Z" }
Assert-Equal -Actual @($simultaneous.Games).Count -Expected 2 -Message "Exact simultaneous kickoffs must share one Decision Window."
Assert-Equal -Actual @($facts.DecisionWindows | Where-Object { $_.StartsAtUtc -eq "2026-09-13T20:05:00Z" }).Count -Expected 1 -Message "16:05-equivalent kickoff must remain separate."
Assert-Equal -Actual @($facts.DecisionWindows | Where-Object { $_.StartsAtUtc -eq "2026-09-13T20:25:00Z" }).Count -Expected 1 -Message "16:25-equivalent kickoff must remain separate."
Assert-Equal -Actual @($facts.DecisionWindows | Where-Object { $_.StartsAtUtc -eq "2026-09-19T17:00:00Z" }).Count -Expected 1 -Message "Saturday/unusual scheduling must require no weekday rule."

# Player/team association uses stable team IDs and preserves rostered/starter semantics.
$p1 = $facts.PlayerLockFacts | Where-Object PlayerID -eq "p1"
Assert-Equal -Actual $p1.Kind -Expected "scheduled" -Message "Scheduled player should resolve by stable NFL team ID."
Assert-Equal -Actual $p1.GameID -Expected "g1" -Message "Scheduled player should expose the stable GameID."
Assert-Equal -Actual $p1.DecisionWindowID -Expected "2026-09-10T00:20:00Z" -Message "DecisionWindowID should represent kickoff instant."
Assert-Equal -Actual $p1.StartsAtUtc -Expected "2026-09-10T00:20:00Z" -Message "Scheduled lock fact should expose StartsAtUtc."
Assert-True -Condition $p1.IsStarter -Message "Starter association must survive derivation."

$p4 = $facts.PlayerLockFacts | Where-Object PlayerID -eq "p4"
Assert-Equal -Actual $p4.Kind -Expected "no-team" -Message "Blank team assignment should produce no-team."
$p5 = $facts.PlayerLockFacts | Where-Object PlayerID -eq "p5"
Assert-Equal -Actual $p5.Kind -Expected "unknown" -Message "Missing player-team evidence should produce unknown."
$p3 = $facts.PlayerLockFacts | Where-Object PlayerID -eq "p3"
Assert-Equal -Actual $p3.Kind -Expected "unknown" -Message "Unknown NFL team identity should not be guessed."

$affected = $facts.DecisionWindows | Where-Object DecisionWindowID -eq "2026-09-13T17:00:00Z" | Select-Object -ExpandProperty AffectedFantasyTeams
$team101 = $affected | Where-Object FantasyTeamID -eq 101
Assert-Equal -Actual $team101.AffectedRosteredPlayerCount -Expected 1 -Message "Affected rostered count should be window-specific."
Assert-Equal -Actual $team101.AffectedStarterCount -Expected 1 -Message "Affected starter count should preserve starter role."
Assert-True -Condition (-not (($facts | ConvertTo-Json -Depth 10 -Compress) -match "FantasyMatchupID")) -Message "#343 must not depend on FantasyMatchupID."

# Affected players alone are context, not warnings.
$cleanFacts = Get-DecisionWindowFacts `
    -Season "2026" -Week 1 -ScheduleGames $schedule `
    -FantasyRosters @([PSCustomObject]@{ FantasyTeamID = 303; PlayerIDs = @("clean1"); StarterIDs = @("clean1") }) `
    -PlayerTeamAssignments @([PSCustomObject]@{ PlayerID = "clean1"; NFLTeamID = "2" }) `
    -ExpectedStarterCount 1
Assert-Equal -Actual $cleanFacts.TeamLineupEvaluations[0].State -Expected "ready" -Message "Scheduled affected players alone must not create a warning."
Assert-Equal -Actual @($cleanFacts.TeamLineupEvaluations[0].Issues).Count -Expected 0 -Message "Ready lineup should have no objective issues."

# Objective lineup integrity: short/empty list, bye, no-team, unresolved, duplicates and overflow.
$openFacts = Get-DecisionWindowFacts `
    -Season "2026" -Week 1 -ScheduleGames $schedule `
    -FantasyRosters @([PSCustomObject]@{ FantasyTeamID = 404; PlayerIDs = @("a"); StarterIDs = @("a", "", "0") }) `
    -PlayerTeamAssignments @([PSCustomObject]@{ PlayerID = "a"; NFLTeamID = "1" }) `
    -ExpectedStarterCount 3
Assert-Equal -Actual $openFacts.TeamLineupEvaluations[0].State -Expected "action-required" -Message "Open starter slots should require action."
Assert-Equal -Actual ($openFacts.TeamLineupEvaluations[0].Issues | Where-Object Code -eq "OPEN_STARTER_SLOT" | Select-Object -First 1).Count -Expected 2 -Message "OPEN_STARTER_SLOT should report the number of missing starters."

$byeSchedule = @(
    New-TestGame -GameID "w1" -Week 1 -StartsAtUtc "2026-09-13T17:00:00Z" -AwayTeamID "1" -HomeTeamID "2"
    New-TestGame -GameID "w2" -Week 2 -StartsAtUtc "2026-09-20T17:00:00Z" -AwayTeamID "3" -HomeTeamID "4"
)
$byeFacts = Get-DecisionWindowFacts `
    -Season "2026" -Week 1 -ScheduleGames $byeSchedule `
    -FantasyRosters @([PSCustomObject]@{ FantasyTeamID = 505; PlayerIDs = @("bye"); StarterIDs = @("bye") }) `
    -PlayerTeamAssignments @([PSCustomObject]@{ PlayerID = "bye"; NFLTeamID = "3" }) `
    -ExpectedStarterCount 1
Assert-Equal -Actual $byeFacts.PlayerLockFacts[0].Kind -Expected "bye" -Message "Known team without a current-week game should produce bye."
Assert-Equal -Actual $byeFacts.TeamLineupEvaluations[0].State -Expected "action-required" -Message "Starter on bye should require action."
Assert-Equal -Actual ($byeFacts.TeamLineupEvaluations[0].Issues | Where-Object Code -eq "STARTER_ON_BYE").Count -Expected 1 -Message "Starter on bye should expose stable issue code."

$noTeamFacts = Get-DecisionWindowFacts `
    -Season "2026" -Week 1 -ScheduleGames $schedule `
    -FantasyRosters @([PSCustomObject]@{ FantasyTeamID = 606; PlayerIDs = @("nt"); StarterIDs = @("nt") }) `
    -PlayerTeamAssignments @([PSCustomObject]@{ PlayerID = "nt"; NFLTeamID = $null }) `
    -ExpectedStarterCount 1
Assert-Equal -Actual $noTeamFacts.TeamLineupEvaluations[0].State -Expected "review" -Message "Starter without usable NFL team should deterministically require review."

$unknownFacts = Get-DecisionWindowFacts `
    -Season "2026" -Week 1 -ScheduleGames $schedule `
    -FantasyRosters @([PSCustomObject]@{ FantasyTeamID = 707; PlayerIDs = @("missing"); StarterIDs = @("missing") }) `
    -PlayerTeamAssignments @() -ExpectedStarterCount 1
Assert-Equal -Actual $unknownFacts.TeamLineupEvaluations[0].State -Expected "unknown" -Message "Unresolved non-empty starter ID must remain uncertainty."

$duplicateFacts = Get-DecisionWindowFacts `
    -Season "2026" -Week 1 -ScheduleGames $schedule `
    -FantasyRosters @([PSCustomObject]@{ FantasyTeamID = 808; PlayerIDs = @("dup"); StarterIDs = @("dup", "dup") }) `
    -PlayerTeamAssignments @([PSCustomObject]@{ PlayerID = "dup"; NFLTeamID = "1" }) `
    -ExpectedStarterCount 1
Assert-Equal -Actual $duplicateFacts.TeamLineupEvaluations[0].State -Expected "unknown" -Message "Duplicate starter evidence must never produce ready."

$overflowFacts = Get-DecisionWindowFacts `
    -Season "2026" -Week 1 -ScheduleGames $schedule `
    -FantasyRosters @([PSCustomObject]@{ FantasyTeamID = 909; PlayerIDs = @("o1", "o2"); StarterIDs = @("o1", "o2") }) `
    -PlayerTeamAssignments @([PSCustomObject]@{ PlayerID = "o1"; NFLTeamID = "1" }, [PSCustomObject]@{ PlayerID = "o2"; NFLTeamID = "2" }) `
    -ExpectedStarterCount 1
Assert-Equal -Actual $overflowFacts.TeamLineupEvaluations[0].State -Expected "unknown" -Message "Unexpected starter overflow must never produce ready."

# Duplicate player-team evidence is ambiguous even if one record looks usable.
$ambiguousFacts = Get-DecisionWindowFacts `
    -Season "2026" -Week 1 -ScheduleGames $schedule `
    -FantasyRosters @([PSCustomObject]@{ FantasyTeamID = 1001; PlayerIDs = @("amb"); StarterIDs = @("amb") }) `
    -PlayerTeamAssignments @([PSCustomObject]@{ PlayerID = "amb"; NFLTeamID = "1" }, [PSCustomObject]@{ PlayerID = "amb"; NFLTeamID = "2" }) `
    -ExpectedStarterCount 1
Assert-Equal -Actual $ambiguousFacts.PlayerLockFacts[0].Kind -Expected "unknown" -Message "Duplicate assignment evidence must not use first/last-wins semantics."
Assert-Equal -Actual $ambiguousFacts.TeamLineupEvaluations[0].State -Expected "unknown" -Message "Ambiguous assignment must propagate to lineup uncertainty."

# Clock-stable contract: next window is derived from StartsAtUtc; game Final state is not an input.
$nowAtKickoff = [DateTimeOffset]::Parse("2026-09-13T17:00:00Z")
$futureWindows = @($facts.DecisionWindows | Where-Object { [DateTimeOffset]::Parse($_.StartsAtUtc) -gt $nowAtKickoff } | Sort-Object StartsAtUtc)
Assert-Equal -Actual $futureWindows[0].StartsAtUtc -Expected "2026-09-13T20:05:00Z" -Message "Next-window selection must advance exactly at kickoff without waiting for Final."
Assert-True -Condition (-not (($facts | ConvertTo-Json -Depth 10 -Compress) -match '"(upcoming|locked|NextDecisionWindow)"')) -Message "Generated facts must not persist wall-clock-only labels or a stale NextDecisionWindow."

# Rescheduling: stable GameID moves to a new exact-kickoff window when source kickoff changes.
$rescheduleBase = @(New-TestGame -GameID "rescheduled" -Week 4 -StartsAtUtc "2026-10-04T17:00:00Z" -AwayTeamID "1" -HomeTeamID "2")
$rescheduleNew = @(New-TestGame -GameID "rescheduled" -Week 4 -StartsAtUtc "2026-10-04T20:25:00Z" -AwayTeamID "1" -HomeTeamID "2")
$oldRescheduleFacts = Get-DecisionWindowFacts -Season "2026" -Week 4 -ScheduleGames $rescheduleBase -FantasyRosters @() -PlayerTeamAssignments @() -ExpectedStarterCount 0
$newRescheduleFacts = Get-DecisionWindowFacts -Season "2026" -Week 4 -ScheduleGames $rescheduleNew -FantasyRosters @() -PlayerTeamAssignments @() -ExpectedStarterCount 0
Assert-Equal -Actual $oldRescheduleFacts.DecisionWindows[0].Games[0].GameID -Expected "rescheduled" -Message "Stable GameID should be preserved before reschedule."
Assert-Equal -Actual $newRescheduleFacts.DecisionWindows[0].Games[0].GameID -Expected "rescheduled" -Message "Stable GameID should be preserved after reschedule."
Assert-Equal -Actual $newRescheduleFacts.DecisionWindows[0].DecisionWindowID -Expected "2026-10-04T20:25:00Z" -Message "Rescheduled game must move to the new kickoff window."

# Small current read model: all current windows + only first next-week window; lookahead is pending.
$readModel = New-DecisionWindowsReadModel `
    -LeagueID "league" -Season "2026" -LineupWeek 1 -LastLineupWeek 3 `
    -ScheduleGames $schedule `
    -FantasyRosters @([PSCustomObject]@{ FantasyTeamID = 303; PlayerIDs = @("clean1"); StarterIDs = @("clean1") }) `
    -PlayerTeamAssignments @([PSCustomObject]@{ PlayerID = "clean1"; NFLTeamID = "2" }) `
    -ExpectedStarterCount 1
Assert-Equal -Actual $readModel.LineupWeek -Expected 1 -Message "Read model should preserve authoritative lineup week input."
Assert-Equal -Actual @($readModel.DecisionWindows).Count -Expected 5 -Message "Read model should contain all current-week Decision Windows."
Assert-Equal -Actual $readModel.LookaheadDecisionWindow.Week -Expected 2 -Message "Lookahead should target only the next fantasy week."
Assert-Equal -Actual $readModel.LookaheadDecisionWindow.DecisionWindowID -Expected "2026-09-17T00:20:00Z" -Message "Lookahead should contain only the first next-week Decision Window."
Assert-Equal -Actual $readModel.LookaheadDecisionWindow.FantasyContextState -Expected "pending" -Message "Next-week lookahead lineup context must be pending before rollover."
Assert-Equal -Actual @($readModel.LookaheadDecisionWindow.AffectedFantasyTeams).Count -Expected 0 -Message "Pending lookahead must not evaluate stale current-week starters."

$lastWeekModel = New-DecisionWindowsReadModel `
    -LeagueID "league" -Season "2026" -LineupWeek 3 -LastLineupWeek 3 `
    -ScheduleGames $schedule -FantasyRosters @() -PlayerTeamAssignments @() -ExpectedStarterCount 0
Assert-True -Condition ($null -eq $lastWeekModel.LookaheadDecisionWindow) -Message "No lookahead may be created beyond the last lineup-relevant week."

$afterLastWeekModel = New-DecisionWindowsReadModel `
    -LeagueID "league" -Season "2026" -LineupWeek 4 -LastLineupWeek 3 `
    -ScheduleGames $schedule `
    -FantasyRosters @([PSCustomObject]@{ FantasyTeamID = 999; PlayerIDs = @("stale"); StarterIDs = @("stale") }) `
    -PlayerTeamAssignments @([PSCustomObject]@{ PlayerID = "stale"; NFLTeamID = "1" }) `
    -ExpectedStarterCount 1
Assert-Equal -Actual @($afterLastWeekModel.DecisionWindows).Count -Expected 0 -Message "No actionable current windows may exist beyond the last lineup week."
Assert-Equal -Actual @($afterLastWeekModel.PlayerLockFacts).Count -Expected 0 -Message "No actionable lock facts may exist beyond the last lineup week."
Assert-Equal -Actual $afterLastWeekModel.TeamLineupEvaluations[0].State -Expected "pending" -Message "Post-lineup-week fantasy context should be pending, not stale action-required."
Assert-True -Condition ($null -eq $afterLastWeekModel.LookaheadDecisionWindow) -Message "No lookahead may exist beyond the last lineup week."

# Transitional current adapter: lineup week comes from platform settings.leg, roster size from configuration, and joins use stable TeamID fields.
$currentKickoff = [DateTimeOffset]::Parse("2026-09-20T17:00:00Z").ToUnixTimeSeconds()
$currentLeague = [PSCustomObject]@{
    league_id = "current-league"
    season = "2026"
    CurrentWeek = 1
    settings = [PSCustomObject]@{ leg = 2 }
    roster_positions = @("QB", "RB", "BN")
}
$currentTeams = @([PSCustomObject]@{ TeamID = 77; Roster = @("cur1", "cur2"); Starter = @("cur1", "cur2") })
$currentPlayers = @(
    [PSCustomObject]@{ ID = "cur1"; TeamID = "31" },
    [PSCustomObject]@{ ID = "cur2"; TeamID = "32" }
)
$currentSchedule = @([PSCustomObject]@{
    gameID = "current-game"
    season = "2026"
    gameWeek = "Week 2"
    gameTime_epoch = [string]$currentKickoff
    teamIDAway = "31"
    teamIDHome = "32"
    away = "ALIAS-A"
    home = "ALIAS-B"
})
$currentModel = New-CurrentLeagueDecisionWindowsReadModel `
    -League $currentLeague -Teams $currentTeams -Players $currentPlayers -Schedule $currentSchedule -LastLineupWeek 17
Assert-Equal -Actual $currentModel.LineupWeek -Expected 2 -Message "Current adapter must use platform settings.leg rather than League.CurrentWeek/finality."
Assert-Equal -Actual $currentModel.TeamLineupEvaluations[0].ExpectedStarterCount -Expected 2 -Message "Expected starter count must derive from league roster_positions, excluding bench slots."
Assert-Equal -Actual $currentModel.TeamLineupEvaluations[0].State -Expected "ready" -Message "Current adapter should preserve a structurally complete lineup."
Assert-Equal -Actual ($currentModel.PlayerLockFacts | Where-Object PlayerID -eq "cur1").GameID -Expected "current-game" -Message "Current player TeamID must join stable schedule team IDs without abbreviation guessing."

# Dynamic fantasy-team count: derivation uses provided rosters, never a six-team assumption.
$dynamicFacts = Get-DecisionWindowFacts `
    -Season "2026" -Week 1 -ScheduleGames $schedule `
    -FantasyRosters @(
        [PSCustomObject]@{ FantasyTeamID = 1; PlayerIDs = @("d1"); StarterIDs = @("d1") },
        [PSCustomObject]@{ FantasyTeamID = 2; PlayerIDs = @("d2"); StarterIDs = @("d2") },
        [PSCustomObject]@{ FantasyTeamID = 3; PlayerIDs = @("d3"); StarterIDs = @("d3") }
    ) `
    -PlayerTeamAssignments @(
        [PSCustomObject]@{ PlayerID = "d1"; NFLTeamID = "1" },
        [PSCustomObject]@{ PlayerID = "d2"; NFLTeamID = "2" },
        [PSCustomObject]@{ PlayerID = "d3"; NFLTeamID = "3" }
    ) `
    -ExpectedStarterCount 1
Assert-Equal -Actual @($dynamicFacts.TeamLineupEvaluations).Count -Expected 3 -Message "Fantasy team count must be fully dynamic."

# Historical fixture uses exactly the same normalized semantics, without live snapshots.
$historicalSchedule = @(
    New-TestGame -GameID "hist1" -Week 7 -StartsAtUtc "2025-10-19T17:00:00Z" -AwayTeamID "20" -HomeTeamID "21"
    New-TestGame -GameID "hist2" -Week 8 -StartsAtUtc "2025-10-26T17:00:00Z" -AwayTeamID "22" -HomeTeamID "23"
)
$historicalFacts = Get-DecisionWindowFacts `
    -Season "2025" -Week 7 -ScheduleGames $historicalSchedule `
    -FantasyRosters @([PSCustomObject]@{ FantasyTeamID = 44; PlayerIDs = @("historical-player"); StarterIDs = @("historical-player") }) `
    -PlayerTeamAssignments @([PSCustomObject]@{ PlayerID = "historical-player"; NFLTeamID = "20" }) `
    -ExpectedStarterCount 1
Assert-Equal -Actual $historicalFacts.DecisionWindows[0].AffectedFantasyTeams[0].Players[0].PlayerID -Expected "historical-player" -Message "Historical persisted facts should rebuild the same association shape."
Assert-True -Condition $historicalFacts.DecisionWindows[0].AffectedFantasyTeams[0].Players[0].IsStarter -Message "Historical starters must preserve starter semantics."

# RequestLeague must invoke the transitional adapter with facts already loaded in the same refresh; no feature-local provider fetch is allowed.
$requestLeagueText = Get-Content "$PSScriptRoot\RequestLeague.ps1" -Raw
Assert-True -Condition ($requestLeagueText -match 'New-CurrentLeagueDecisionWindowsReadModel') -Message "RequestLeague must invoke the current Decision Window adapter."
Assert-True -Condition ($requestLeagueText -match '-League\s+\$league') -Message "RequestLeague must reuse already-fetched league state for DecisionWindows."
Assert-True -Condition ($requestLeagueText -match '-Teams\s+\$teamData') -Message "RequestLeague must reuse current in-memory fantasy teams for DecisionWindows."
Assert-True -Condition ($requestLeagueText -match '-Players\s+\$playersData') -Message "RequestLeague must reuse current generated player data for DecisionWindows."
Assert-True -Condition ($requestLeagueText -match '-Schedule\s+\$schedule') -Message "RequestLeague must reuse current Schedule data for DecisionWindows."
Assert-True -Condition ($requestLeagueText -match 'Save-JsonFile -Type "DecisionWindows"') -Message "RequestLeague must publish DecisionWindows through the central JSON writer."

# Central writer semantics: identical semantic output skips rewrite/timestamp; changed output updates both.
$tempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("decision-window-regression-" + [Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
$tempDataFile = Join-Path $tempDir "DecisionWindows.json"
$tempTimestampFile = Join-Path $tempDir "Timestamps.json"
$global:TimestampFile = $tempTimestampFile
$compare = { param($oldData, $newData) Test-DecisionWindowReadModelChanged -OldData $oldData -NewData $newData }
try {
    Save-JsonFile -TargetFile $tempDataFile -Type "DecisionWindows" -Data $readModel -CompareScript $compare -UpdateTimestamp
    Set-Content -Path $tempTimestampFile -Value '{"DecisionWindows":"2000-01-01T00:00:00Z"}'
    $beforeData = Get-Content $tempDataFile -Raw

    Save-JsonFile -TargetFile $tempDataFile -Type "DecisionWindows" -Data $readModel -CompareScript $compare -UpdateTimestamp
    $unchangedTimestamp = (Get-Content $tempTimestampFile -Raw | ConvertFrom-Json).DecisionWindows
    Assert-Equal -Actual $unchangedTimestamp -Expected "2000-01-01T00:00:00Z" -Message "No semantic change should preserve DecisionWindows timestamp."
    Assert-Equal -Actual (Get-Content $tempDataFile -Raw) -Expected $beforeData -Message "No semantic change should skip DecisionWindows rewrite."

    $changedModel = $readModel | ConvertTo-Json -Depth 10 | ConvertFrom-Json
    $changedModel.SchemaVersion = 2
    Save-JsonFile -TargetFile $tempDataFile -Type "DecisionWindows" -Data $changedModel -CompareScript $compare -UpdateTimestamp
    $changedTimestamp = (Get-Content $tempTimestampFile -Raw | ConvertFrom-Json).DecisionWindows
    Assert-True -Condition ($changedTimestamp -ne "2000-01-01T00:00:00Z") -Message "Semantic change should update Timestamps.json.DecisionWindows."
    Assert-Equal -Actual (Get-Content $tempDataFile -Raw | ConvertFrom-Json).SchemaVersion -Expected 2 -Message "Semantic change should update DecisionWindows output."
}
finally {
    Remove-Variable -Name TimestampFile -Scope Global -ErrorAction SilentlyContinue
    Remove-Item -Path $tempDir -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host "Decision Window regression tests passed." -ForegroundColor Green
