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
    [PSCustomObject]@{ gameID='game-b'; gameWeek='Week 4'; gameTime_epoch='1100'; away='CCC'; home='DDD'; teamIDAway='13'; teamIDHome='14' },
    [PSCustomObject]@{ gameID='game-c'; gameWeek='Week 4'; gameTime_epoch='1200'; away='EEE'; home='FFF'; teamIDAway='15'; teamIDHome='16' }
)
$canonicalSchedule = @(
    [PSCustomObject]@{ Week=4; AwayTeam='AAA'; HomeTeam='BBB'; AwayScore=21; HomeScore=17 },
    [PSCustomObject]@{ Week=4; AwayTeam='CCC'; HomeTeam='DDD'; AwayScore=24; HomeScore=20 },
    [PSCustomObject]@{ Week=4; AwayTeam='EEE'; HomeTeam='FFF'; AwayScore=10; HomeScore=7 }
)
$rosters = @(
    [PSCustomObject]@{ CanonicalPlayerID='c1'; SourceIDs=[PSCustomObject]@{Sleeper='p1'}; Team='AAA'; Position='QB' },
    [PSCustomObject]@{ CanonicalPlayerID='cb'; SourceIDs=[PSCustomObject]@{Sleeper='bench'}; Team='AAA'; Position='WR' },
    [PSCustomObject]@{ CanonicalPlayerID='c2'; SourceIDs=[PSCustomObject]@{Sleeper='p2'}; Team='BBB'; Position='WR' },
    [PSCustomObject]@{ CanonicalPlayerID='c3'; SourceIDs=[PSCustomObject]@{Sleeper='p3'}; Team='AAA'; Position='RB' },
    [PSCustomObject]@{ CanonicalPlayerID='c4'; SourceIDs=[PSCustomObject]@{Sleeper='p4'}; Team='CCC'; Position='WR' },
    [PSCustomObject]@{ CanonicalPlayerID='c5'; SourceIDs=[PSCustomObject]@{Sleeper='p5'}; Team='DDD'; Position='TE' },
    [PSCustomObject]@{ CanonicalPlayerID='c6'; SourceIDs=[PSCustomObject]@{Sleeper='p6'}; Team='EEE'; Position='WR' },
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

Write-Host 'WeeklyRecaps regression suite passed.' -ForegroundColor Green
