$ErrorActionPreference = 'Stop'
Import-Module "$PSScriptRoot\utils\league\WeeklyRecapUtils.psm1" -Force

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw "ASSERTION FAILED: $Message" }
}
function Assert-Equal {
    param($Expected, $Actual, [string]$Message)
    if ($Expected -ne $Actual) { throw "ASSERTION FAILED: $Message. Expected '$Expected', got '$Actual'." }
}

function New-TestPlayer {
    param([string]$PlayerID, [string]$CanonicalPlayerID, [double]$Points, [bool]$Starter = $true)
    return [PSCustomObject]@{ PlayerID=$PlayerID; CanonicalPlayerID=$CanonicalPlayerID; IsStarter=$Starter; HasPoints=$true; Points=$Points }
}

$matchupsWeek = [PSCustomObject]@{
    Week = 4
    CompletionState = 'final'
    Matchups = @(
        [PSCustomObject]@{ FantasyMatchupID='fgm-a'; Participants=@([PSCustomObject]@{TeamID=1;Points=999;ScoreKind='adjusted'},[PSCustomObject]@{TeamID=2;Points=1;ScoreKind='standard'}) },
        [PSCustomObject]@{ FantasyMatchupID='fgm-b'; Participants=@([PSCustomObject]@{TeamID=3;Points=1;ScoreKind='standard'},[PSCustomObject]@{TeamID=4;Points=1;ScoreKind='standard'}) },
        [PSCustomObject]@{ FantasyMatchupID='fgm-c'; Participants=@([PSCustomObject]@{TeamID=5;Points=1;ScoreKind='standard'},[PSCustomObject]@{TeamID=6;Points=1;ScoreKind='standard'}) }
    )
}
$facts = @(
    [PSCustomObject]@{ FantasyMatchupID='fgm-a'; Teams=@(
        [PSCustomObject]@{ FantasyTeamID='1'; Players=@((New-TestPlayer 'p1' 'c1' 20),(New-TestPlayer 'bench' 'cb' 99 $false)) },
        [PSCustomObject]@{ FantasyTeamID='2'; Players=@((New-TestPlayer 'p2' 'c2' 20)) }
    )},
    [PSCustomObject]@{ FantasyMatchupID='fgm-b'; Teams=@(
        [PSCustomObject]@{ FantasyTeamID='3'; Players=@((New-TestPlayer 'p3' 'c3' 18),(New-TestPlayer 'p4' 'c4' 12)) },
        [PSCustomObject]@{ FantasyTeamID='4'; Players=@((New-TestPlayer 'p5' 'c5' 10)) }
    )},
    [PSCustomObject]@{ FantasyMatchupID='fgm-c'; Teams=@(
        [PSCustomObject]@{ FantasyTeamID='5'; Players=@((New-TestPlayer 'p6' 'c6' 20)) },
        [PSCustomObject]@{ FantasyTeamID='6'; Players=@((New-TestPlayer 'p7' 'c7' 5)) }
    )}
)
$identitySchedule = @(
    [PSCustomObject]@{ gameID='game-a'; gameWeek='Week 4'; gameTime_epoch='1000'; away='AAA'; home='BBB'; teamIDAway='11'; teamIDHome='12' },
    [PSCustomObject]@{ gameID='game-b'; gameWeek='Week 4'; gameTime_epoch='1100'; away='WSH'; home='DDD'; teamIDAway='13'; teamIDHome='14' },
    [PSCustomObject]@{ gameID='game-c'; gameWeek='Week 4'; gameTime_epoch='1200'; away='FFF'; home='LAR'; teamIDAway='15'; teamIDHome='16' }
)
$canonicalSchedule = @(
    [PSCustomObject]@{ Week=4; AwayTeam='AAA'; HomeTeam='BBB'; AwayScore=21; HomeScore=17 },
    [PSCustomObject]@{ Week=4; AwayTeam='WAS'; HomeTeam='DDD'; AwayScore=24; HomeScore=20 },
    [PSCustomObject]@{ Week=4; AwayTeam='FFF'; HomeTeam='LA'; AwayScore=10; HomeScore=7 }
)
$rosters = @(
    [PSCustomObject]@{ CanonicalPlayerID='c1'; SourceIDs=[PSCustomObject]@{Sleeper='p1'}; Team='AAA'; Position='QB' },
    [PSCustomObject]@{ CanonicalPlayerID='cb'; SourceIDs=[PSCustomObject]@{Sleeper='bench'}; Team='AAA'; Position='WR' },
    [PSCustomObject]@{ CanonicalPlayerID='c2'; SourceIDs=[PSCustomObject]@{Sleeper='p2'}; Team='BBB'; Position='WR' },
    [PSCustomObject]@{ CanonicalPlayerID='c3'; SourceIDs=[PSCustomObject]@{Sleeper='p3'}; Team='AAA'; Position='RB' },
    [PSCustomObject]@{ CanonicalPlayerID='c4'; SourceIDs=[PSCustomObject]@{Sleeper='p4'}; Team='WAS'; Position='WR' },
    [PSCustomObject]@{ CanonicalPlayerID='c5'; SourceIDs=[PSCustomObject]@{Sleeper='p5'}; Team='DDD'; Position='TE' },
    [PSCustomObject]@{ CanonicalPlayerID='c6'; SourceIDs=[PSCustomObject]@{Sleeper='p6'}; Team='LA'; Position='WR' },
    [PSCustomObject]@{ CanonicalPlayerID='c7'; SourceIDs=[PSCustomObject]@{Sleeper='p7'}; Team='FFF'; Position='RB' }
)
$teamOrder = @{ '1'=1; '2'=4; '3'=3; '4'=5; '5'=2; '6'=6 }
$identityMap = New-WrRosterIdentityMap -Rows $rosters
$recap = New-WeeklyRecapWeekReadModel -Week 4 -MatchupsWeek $matchupsWeek -FantasyMatchups $facts -IdentitySchedule $identitySchedule -CanonicalSchedule $canonicalSchedule -RosterIdentityMap $identityMap -TeamOrder $teamOrder

Assert-Equal 2 @($recap.KeyGames).Count 'exactly two Key Games'
Assert-Equal 3 @($recap.KeyPlayers).Count 'exactly three Key Players'
Assert-Equal 'game-a' $recap.KeyGames[0].GameID 'starter points rank first; bench points do not count'
Assert-Equal 58.0 $recap.KeyGames[0].StarterPoints 'game-a actual starter production only'
Assert-True (-not (@($recap.KeyPlayers | Select-Object -ExpandProperty PlayerID) -contains 'bench')) 'bench-only performance must be excluded'
Assert-Equal 'p1' $recap.KeyPlayers[0].PlayerID 'equal points use neutral team order before PlayerID'
Assert-Equal 'p6' $recap.KeyPlayers[1].PlayerID 'neutral team order determines second tied 20-point starter'
Assert-Equal 'p2' $recap.KeyPlayers[2].PlayerID 'third tied 20-point starter follows neutral team order'
Assert-Equal 1 $recap.KeyPlayers[0].FantasyTeamID 'FantasyTeamID preserves Matchups representation'
Assert-Equal '11' $recap.KeyPlayers[0].NFLTeamID 'week-specific NFL identity resolves through schedule team ID'
Assert-Equal '16' $recap.KeyPlayers[1].NFLTeamID 'canonical LA maps to historical app LAR team ID'
Assert-Equal 'QB' $recap.KeyPlayers[0].Position 'natural position is persisted'
Assert-Equal 21.0 $recap.KeyGames[0].AwayScore 'canonical final away score is persisted'
Assert-True (@($recap.KeyGames[0].FantasyMatchupIDs) -contains 'fgm-a') 'affected FantasyMatchupIDs are persisted'
Assert-True (@($recap.KeyGames[0].FantasyMatchupIDs) -contains 'fgm-b') 'multiple affected fantasy matchups participate in ranking'

# Commissioner-adjusted matchup score must not alter player/game production.
Assert-Equal 58.0 $recap.KeyGames[0].StarterPoints 'commissioner adjustment is not attributed to an NFL game'

# Stat correction rematerializes the deterministic ranking from actual StarterPoints.
$correctedFacts = $facts | ConvertTo-Json -Depth 20 | ConvertFrom-Json
$correctedFacts[2].Teams[0].Players[0].Points = 70
$corrected = New-WeeklyRecapWeekReadModel -Week 4 -MatchupsWeek $matchupsWeek -FantasyMatchups $correctedFacts -IdentitySchedule $identitySchedule -CanonicalSchedule $canonicalSchedule -RosterIdentityMap $identityMap -TeamOrder $teamOrder
Assert-Equal 'p6' $corrected.KeyPlayers[0].PlayerID 'stat correction changes Key Player ranking'
Assert-Equal 'game-c' $corrected.KeyGames[0].GameID 'stat correction changes Key Game ranking'

# Key Game ordering: same points then affected matchup/team/starter density.
$tieFacts = $facts | ConvertTo-Json -Depth 20 | ConvertFrom-Json
$tieFacts[0].Teams[0].Players[0].Points = 10
$tieFacts[0].Teams[1].Players[0].Points = 10
$tieFacts[1].Teams[0].Players[0].Points = 0
$tieFacts[1].Teams[0].Players[1].Points = 10
$tieFacts[1].Teams[1].Players[0].Points = 10
$tieFacts[2].Teams[0].Players[0].Points = 10
$tieFacts[2].Teams[1].Players[0].Points = 0
$tie = New-WeeklyRecapWeekReadModel -Week 4 -MatchupsWeek $matchupsWeek -FantasyMatchups $tieFacts -IdentitySchedule $identitySchedule -CanonicalSchedule $canonicalSchedule -RosterIdentityMap $identityMap -TeamOrder $teamOrder
Assert-Equal 'game-a' $tie.KeyGames[0].GameID 'affected-matchup/team/starter density tiebreaks are deterministic'

$openWeek = $matchupsWeek | ConvertTo-Json -Depth 10 | ConvertFrom-Json
$openWeek.CompletionState = 'open'
$failedOpen = $false
try { New-WeeklyRecapWeekReadModel -Week 4 -MatchupsWeek $openWeek -FantasyMatchups $facts -IdentitySchedule $identitySchedule -CanonicalSchedule $canonicalSchedule -RosterIdentityMap $identityMap -TeamOrder $teamOrder | Out-Null } catch { $failedOpen = $true }
Assert-True $failedOpen 'non-final Matchups week must never materialize a recap'

$again = New-WeeklyRecapWeekReadModel -Week 4 -MatchupsWeek $matchupsWeek -FantasyMatchups $facts -IdentitySchedule $identitySchedule -CanonicalSchedule $canonicalSchedule -RosterIdentityMap $identityMap -TeamOrder $teamOrder
Assert-Equal ($recap | ConvertTo-Json -Depth 30 -Compress) ($again | ConvertTo-Json -Depth 30 -Compress) 'WeeklyRecaps output must be deterministic'

# Awards come from finalized Shared Derived snapshots, never recalculated by this module.
# Missing partitions are explicitly unknown; corrupted or mismatched available partitions fail closed.
$scratch = Join-Path ([System.IO.Path]::GetTempPath()) ("weekly-recaps-awards-" + [guid]::NewGuid().ToString('N'))
try {
    New-Item -ItemType Directory -Path $scratch -Force | Out-Null
    $sourceWeek = @(
        1..6 | ForEach-Object {
            [PSCustomObject]@{
                Week = 4
                CanonicalLeagueRosterID = "roster-$_"
                ProviderMappings = @([PSCustomObject]@{ Provider = 'Sleeper'; ProviderRosterID = [string]$_ })
            }
        }
    )
    $missing = Get-WrTeamAwards -CanonicalLeagueID 'test-league' -Season 2026 -Week 4 -MatchupRows $sourceWeek -MatchupsWeek $matchupsWeek -RepoRoot $scratch
    Assert-Equal 'unavailable' $missing.State 'missing derived awards remain explicitly unavailable'
    Assert-Equal 0 @($missing.BestManager).Count 'missing award is not a zero-score winner'

    $directory = Join-Path $scratch 'data-derived/team-week-performance/test-league/2026'
    New-Item -ItemType Directory -Path $directory -Force | Out-Null
    $file = Join-Path $directory '04.json'
    $derivedTest = [PSCustomObject]@{
        ContractVersion = 1
        CanonicalLeagueID = 'test-league'
        Season = 2026
        Week = 4
        FinalityEvidence = 'data-source/nfl/game-finality/2026.json:REG-W4;league:scored-week-confirmed'
        LineupDefinitionHash = 'sha256:lineup'
        ScoringProfile = [PSCustomObject]@{ SettingsHash = 'sha256:scoring' }
        Teams = @(1..6 | ForEach-Object {
            [PSCustomObject]@{
                CanonicalLeagueRosterID = "roster-$_"
                PotentialPoints = (100 + $_)
                ActualStarterPoints = (80 + $_)
                MissedPoints = 20
                EfficiencyPercent = 80
            }
        })
        Awards = [PSCustomObject]@{
            BestManagerRosterIDs = @('roster-2')
            BestCoachRosterIDs = @('roster-4','roster-6')
        }
    }
    $derivedTest | ConvertTo-Json -Depth 20 | Set-Content -Path $file -Encoding UTF8
    $awards = Get-WrTeamAwards -CanonicalLeagueID 'test-league' -Season 2026 -Week 4 -MatchupRows $sourceWeek -MatchupsWeek $matchupsWeek -RepoRoot $scratch
    Assert-Equal 'available' $awards.State 'final derived award is available'
    Assert-Equal 1 @($awards.BestManager).Count 'Best Manager count comes from derived owner'
    Assert-Equal 2 $awards.BestManager[0].FantasyTeamID 'canonical week roster -> historical app team ID'
    Assert-Equal 102 $awards.BestManager[0].PotentialPoints 'Best Manager points copied without recalculation'
    Assert-Equal 2 @($awards.BestCoach).Count 'all exact-tie coaches are kept'
    Assert-Equal 4 $awards.BestCoach[0].FantasyTeamID 'tied coaches sort deterministically'
    Assert-Equal 6 $awards.BestCoach[1].FantasyTeamID 'second coach preserved'
    Assert-True (-not ($awards.BestManager[0].PSObject.Properties.Name -contains 'Owner')) 'no current owner/manager name is backdated'
    $awardsAgain = Get-WrTeamAwards -CanonicalLeagueID 'test-league' -Season 2026 -Week 4 -MatchupRows $sourceWeek -MatchupsWeek $matchupsWeek -RepoRoot $scratch
    Assert-Equal ($awards | ConvertTo-Json -Depth 20 -Compress) ($awardsAgain | ConvertTo-Json -Depth 20 -Compress) 'derived projection is deterministic'

    $original = $derivedTest | ConvertTo-Json -Depth 20 -Compress

    # A scoreless final week can legitimately have NO winners; this is
    # different from an absent Derived partition or missing award fields.
    $derivedTest.Awards.BestManagerRosterIDs = @()
    $derivedTest.Awards.BestCoachRosterIDs = @()
    $derivedTest | ConvertTo-Json -Depth 20 | Set-Content -Path $file -Encoding UTF8
    $emptyWinners = Get-WrTeamAwards -CanonicalLeagueID 'test-league' -Season 2026 -Week 4 -MatchupRows $sourceWeek -MatchupsWeek $matchupsWeek -RepoRoot $scratch
    Assert-Equal 'available' $emptyWinners.State 'available final derived snapshot may have no winning team'
    Assert-Equal 0 @($emptyWinners.BestManager).Count 'legitimately empty manager winners'
    Assert-Equal 0 @($emptyWinners.BestCoach).Count 'legitimately empty coach winners'
    $derivedTest = $original | ConvertFrom-Json
    $derivedTest | ConvertTo-Json -Depth 20 | Set-Content -Path $file -Encoding UTF8

    # Invalid data is NOT swallowed as unavailable, including season/week mismatch,
    # invalid finality, missing winners, duplicate winners or owner join drift.
    $derivedTest.Week = 3
    $derivedTest | ConvertTo-Json -Depth 20 | Set-Content -Path $file -Encoding UTF8
    $failed = $false
    try { Get-WrTeamAwards -CanonicalLeagueID 'test-league' -Season 2026 -Week 4 -MatchupRows $sourceWeek -MatchupsWeek $matchupsWeek -RepoRoot $scratch | Out-Null } catch { $failed = $true }
    Assert-True $failed 'derived week mismatch fails closed'
    $derivedTest = $original | ConvertFrom-Json
    $derivedTest.Awards.BestManagerRosterIDs = @('unknown-roster')
    $derivedTest | ConvertTo-Json -Depth 20 | Set-Content -Path $file -Encoding UTF8
    $failed = $false
    try { Get-WrTeamAwards -CanonicalLeagueID 'test-league' -Season 2026 -Week 4 -MatchupRows $sourceWeek -MatchupsWeek $matchupsWeek -RepoRoot $scratch | Out-Null } catch { $failed = $true }
    Assert-True $failed 'unknown canonical award winner fails closed'
    $derivedTest = $original | ConvertFrom-Json
    $derivedTest | ConvertTo-Json -Depth 20 | Set-Content -Path $file -Encoding UTF8
    $badRosterRows = $sourceWeek | ConvertTo-Json -Depth 20 | ConvertFrom-Json
    $badRosterRows[0].ProviderMappings[0].ProviderRosterID = '99'
    $failed = $false
    try { Get-WrTeamAwards -CanonicalLeagueID 'test-league' -Season 2026 -Week 4 -MatchupRows $badRosterRows -MatchupsWeek $matchupsWeek -RepoRoot $scratch | Out-Null } catch { $failed = $true }
    Assert-True $failed 'provider roster ID missing in exact Matchups participants fails closed'
}
finally {
    if (Test-Path $scratch) { Remove-Item -Path $scratch -Recurse -Force }
}

Write-Host 'WeeklyRecaps regression suite passed.' -ForegroundColor Green