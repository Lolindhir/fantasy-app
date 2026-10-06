$ErrorActionPreference = 'Stop'

Import-Module "$PSScriptRoot\utils\general\CanonicalScheduleUtils.psm1" -Force

# Regression for #347 G2: Schedule.json is built from canonical NFL facts. All fixtures are synthetic
# (season 2030) so no assertion depends on today's real schedule, players or results.

function Assert-CsrEqual {
    param($Expected, $Actual, [string]$Message)
    if ([string]$Expected -ne [string]$Actual) {
        throw "ASSERTION FAILED: $Message. Expected '$Expected', got '$Actual'."
    }
}

function Assert-CsrTrue {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw "ASSERTION FAILED: $Message" }
}

function Assert-CsrThrows {
    param([scriptblock]$Action, [string]$Pattern, [string]$Message)
    $thrown = $null
    try { & $Action | Out-Null } catch { $thrown = $_.Exception.Message }
    if ($null -eq $thrown) { throw "ASSERTION FAILED: $Message (no exception)." }
    if ($thrown -notmatch $Pattern) { throw "ASSERTION FAILED: $Message (got '$thrown')." }
}

# --- 1. Kickoff conversion (Eastern local time -> UTC epoch), independently computed literals ---
Assert-CsrEqual '1915488900.0' (ConvertTo-NflKickoffEpoch -GameDay '2030-09-12' -GameTime '20:15') 'Thursday 20:15 EDT.'
$early = ConvertTo-NflKickoffEpoch -GameDay '2030-10-06' -GameTime '16:05'
$late = ConvertTo-NflKickoffEpoch -GameDay '2030-10-06' -GameTime '16:25'
Assert-CsrEqual '1917547500.0' $early 'Sunday 16:05 EDT.'
Assert-CsrEqual '1917548700.0' $late 'Sunday 16:25 EDT.'
Assert-CsrTrue (([double]$late - [double]$early) -eq 1200) '16:05 and 16:25 kickoffs must stay 20 minutes apart (separate windows).'
Assert-CsrEqual '1918128600.0' (ConvertTo-NflKickoffEpoch -GameDay '2030-10-13' -GameTime '09:30') 'London 9:30 EDT kickoff.'
Assert-CsrEqual '1919895300.0' (ConvertTo-NflKickoffEpoch -GameDay '2030-11-02' -GameTime '20:15') 'Saturday before the DST end still EDT.'
Assert-CsrEqual '1919959200.0' (ConvertTo-NflKickoffEpoch -GameDay '2030-11-03' -GameTime '13:00') 'Sunday after the DST end uses EST.'
Assert-CsrEqual '1923588000.0' (ConvertTo-NflKickoffEpoch -GameDay '2030-12-15' -GameTime '13:00') 'December 13:00 EST.'
Assert-CsrEqual '1899392400.0' (ConvertTo-NflKickoffEpoch -GameDay '2030-03-10' -GameTime '13:00') 'DST start Sunday 13:00 is already EDT.'
Assert-CsrTrue ($null -eq (ConvertTo-NflKickoffEpoch -GameDay '2030-12-15' -GameTime '')) 'Empty GameTime must give an unknown (null) kickoff, never 0.'
Assert-CsrTrue ($null -eq (ConvertTo-NflKickoffEpoch -GameDay '2030-12-15' -GameTime $null)) 'Null GameTime must give an unknown (null) kickoff.'
Assert-CsrThrows { ConvertTo-NflKickoffEpoch -GameDay '2030-03-10' -GameTime '02:30' } 'does not exist' 'Non-existent DST-gap time must fail closed.'
Assert-CsrThrows { ConvertTo-NflKickoffEpoch -GameDay '2030-11-03' -GameTime '01:30' } 'ambiguous' 'Ambiguous DST-overlap time must fail closed.'
Assert-CsrThrows { ConvertTo-NflKickoffEpoch -GameDay '2030-13-45' -GameTime '13:00' } 'not a valid' 'Invalid GameDay must fail closed.'

# --- 2. Kickoff text ---
Assert-CsrEqual '8:20p' (Format-NflGameTimeText -GameTime '20:20') 'Evening time.'
Assert-CsrEqual '1:00p' (Format-NflGameTimeText -GameTime '13:00') 'Afternoon time.'
Assert-CsrEqual '9:30a' (Format-NflGameTimeText -GameTime '09:30') 'Morning time without leading zero.'
Assert-CsrEqual '12:05p' (Format-NflGameTimeText -GameTime '12:05') 'Noon hour.'
Assert-CsrEqual '12:30a' (Format-NflGameTimeText -GameTime '00:30') 'Midnight hour.'
Assert-CsrEqual 'TBD' (Format-NflGameTimeText -GameTime '') 'Unknown time.'
Assert-CsrThrows { Format-NflGameTimeText -GameTime '25:00' } 'out of range' 'Out-of-range hour must fail.'

# --- 3. Season type and team spellings ---
Assert-CsrEqual 'Regular Season' (ConvertTo-AppSeasonType -GameType 'REG') 'REG season type.'
foreach ($type in @('WC', 'DIV', 'CON', 'SB')) {
    Assert-CsrEqual 'Post Season' (ConvertTo-AppSeasonType -GameType $type) "$type season type."
}
Assert-CsrThrows { ConvertTo-AppSeasonType -GameType 'PRE' } 'Unsupported' 'Unknown GameType must fail closed.'

Assert-CsrEqual 'LAR' (Get-NflTeamProviderSpelling -Team 'LA') 'LA provider spelling.'
Assert-CsrEqual 'WSH' (Get-NflTeamProviderSpelling -Team 'WAS') 'WAS provider spelling.'
Assert-CsrEqual 'NE' (Get-NflTeamProviderSpelling -Team 'NE') 'NE has no alias.'
Assert-CsrEqual 'LAR' (Get-NflTeamCbsSpelling -Team 'LA') 'CBS keeps LAR.'
Assert-CsrEqual 'WAS' (Get-NflTeamCbsSpelling -Team 'WAS') 'CBS uses WAS.'
Assert-CsrEqual 'JAC' (Get-NflTeamCbsSpelling -Team 'JAX') 'CBS uses JAC.'
Assert-CsrEqual 'SEA' (Get-NflTeamCbsSpelling -Team 'SEA') 'CBS keeps other teams.'

# --- 4. Builder on a synthetic canonical repository ---
$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("canonical-schedule-" + [guid]::NewGuid().ToString('N'))
try {
    $scheduleDir = Join-Path $tempRoot 'source-data/nfl/schedules'
    $finalityDir = Join-Path $tempRoot 'source-data/nfl/game-finality'
    New-Item -ItemType Directory -Path $scheduleDir -Force | Out-Null
    New-Item -ItemType Directory -Path $finalityDir -Force | Out-Null

    function New-CsrGame {
        param([string]$Id, [string]$Type = 'REG', [int]$Week, [string]$Day, [string]$Time, [string]$AwayTeamKey, [string]$HomeTeamKey,
            $AwayScore = $null, $HomeScore = $null, [string]$Overtime = '0', [string]$Location = 'Home', [string]$Espn)
        [PSCustomObject][ordered]@{
            GameID = $Id; GameType = $Type; Week = $Week; GameDay = $Day; GameTime = $Time
            AwayTeam = $AwayTeamKey; HomeTeam = $HomeTeamKey; AwayScore = $AwayScore; HomeScore = $HomeScore
            Overtime = $Overtime; Location = $Location
            ProviderGameIDs = [PSCustomObject]@{ ESPN = $Espn }
        }
    }

    function Write-CsrFixture {
        param([object[]]$Games, [object[]]$Finality, [string]$ScheduleSource = 'nflverse.schedules',
            [string]$FinalitySource = 'nflverse.game-finality', [int]$Season = 2030)
        [PSCustomObject]@{ SchemaVersion = 2; Season = $Season; SourceDataset = $ScheduleSource; Finalized = $false; Games = $Games } |
            ConvertTo-Json -Depth 6 | Set-Content (Join-Path $scheduleDir '2030.json') -Encoding UTF8
        [PSCustomObject]@{ SchemaVersion = 2; Season = $Season; SourceDataset = $FinalitySource; Games = $Finality } |
            ConvertTo-Json -Depth 6 | Set-Content (Join-Path $finalityDir '2030.json') -Encoding UTF8
    }

    $gameRows = @(
        (New-CsrGame -Id '2030_01_LA_WAS' -Week 1 -Day '2030-09-12' -Time '20:15' -AwayTeamKey 'LA' -HomeTeamKey 'WAS' -AwayScore 20 -HomeScore 17 -Overtime '1' -Espn '9001'),
        (New-CsrGame -Id '2030_01_JAX_NE' -Week 1 -Day '2030-10-13' -Time '09:30' -AwayTeamKey 'JAX' -HomeTeamKey 'NE' -AwayScore 3 -HomeScore 0 -Location 'Neutral' -Espn '9002'),
        (New-CsrGame -Id '2030_01_SEA_DAL' -Week 1 -Day '2030-10-06' -Time '16:25' -AwayTeamKey 'SEA' -HomeTeamKey 'DAL' -Espn '9003'),
        (New-CsrGame -Id '2030_01_NE_SEA' -Week 1 -Day '2030-10-06' -Time '16:05' -AwayTeamKey 'NE' -HomeTeamKey 'SEA' -Espn '9004'),
        (New-CsrGame -Id '2030_16_DAL_NE' -Week 16 -Day '2030-12-22' -Time '' -AwayTeamKey 'DAL' -HomeTeamKey 'NE' -Espn '9005'),
        (New-CsrGame -Id '2030_19_NE_DAL' -Type 'WC' -Week 19 -Day '2031-01-12' -Time '16:30' -AwayTeamKey 'NE' -HomeTeamKey 'DAL' -Espn '9006')
    )
    $finality = @(
        [PSCustomObject]@{ GameID = '2030_01_LA_WAS'; Final = $true },
        [PSCustomObject]@{ GameID = '2030_01_JAX_NE'; Final = $true },
        [PSCustomObject]@{ GameID = '2030_01_SEA_DAL'; Final = $false },
        [PSCustomObject]@{ GameID = '2030_01_NE_SEA'; Final = $false },
        [PSCustomObject]@{ GameID = '2030_16_DAL_NE'; Final = $false },
        [PSCustomObject]@{ GameID = '2030_19_NE_DAL'; Final = $false }
    )
    Write-CsrFixture -Games $gameRows -Finality $finality

    $schedule = @(Get-CanonicalAppSchedule -Season 2030 -RepoRoot $tempRoot)
    Assert-CsrEqual 5 $schedule.Count 'Default scope is regular season only.'
    $byEspn = @{}
    foreach ($game in $schedule) { $byEspn[$game.espnID] = $game }

    $ot = $byEspn['9001']
    Assert-CsrEqual '20300912_LAR@WSH' $ot.gameID 'gameID keeps the provider spelling.'
    Assert-CsrEqual '2030_01_LA_WAS' $ot.CanonicalGameID 'CanonicalGameID is additive.'
    Assert-CsrEqual 'LA' $ot.away 'away carries the canonical abbreviation.'
    Assert-CsrEqual 'WAS' $ot.home 'home carries the canonical abbreviation.'
    Assert-CsrEqual 'LA' $ot.teamIDAway 'teamIDAway carries the canonical abbreviation.'
    Assert-CsrEqual 'WAS' $ot.teamIDHome 'teamIDHome carries the canonical abbreviation.'
    Assert-CsrEqual 'Final/OT' $ot.gameStatus 'Overtime Final status.'
    Assert-CsrEqual '2' $ot.gameStatusCode 'Final status code.'
    Assert-CsrEqual 20 $ot.awayPts 'Final away score.'
    Assert-CsrEqual 17 $ot.homePts 'Final home score.'
    Assert-CsrEqual 'Week 1' $ot.gameWeek 'Week label.'
    Assert-CsrEqual '20300912' $ot.gameDate 'Game date.'
    Assert-CsrEqual '8:15p' $ot.gameTime 'Game time text.'
    Assert-CsrEqual '1915488900.0' $ot.gameTime_epoch 'Game epoch.'
    Assert-CsrEqual '2030' $ot.season 'Season label.'
    Assert-CsrEqual 'Regular Season' $ot.seasonType 'Season type.'
    Assert-CsrEqual 'https://www.espn.com/nfl/boxscore/_/gameId/9001' $ot.espnLink 'ESPN link.'
    Assert-CsrEqual 'https://www.cbssports.com/nfl/gametracker/boxscore/NFL_20300912_LAR@WAS' $ot.cbsLink 'CBS link keeps LAR and uses WAS.'

    $neutral = $byEspn['9002']
    Assert-CsrEqual 'True' $neutral.neutralSite 'Neutral location marks neutralSite.'
    Assert-CsrEqual 'Final' $neutral.gameStatus 'Regular Final status.'
    Assert-CsrEqual 0 $neutral.homePts 'A zero score must stay a valid score.'
    Assert-CsrEqual 'https://www.cbssports.com/nfl/gametracker/boxscore/NFL_20301013_JAC@NE' $neutral.cbsLink 'CBS link uses JAC.'
    Assert-CsrEqual '20301013_JAX@NE' $neutral.gameID 'gameID keeps JAX.'

    $pending = $byEspn['9003']
    Assert-CsrEqual 'Scheduled' $pending.gameStatus 'Non-final game is Scheduled.'
    Assert-CsrEqual '0' $pending.gameStatusCode 'Scheduled status code.'
    Assert-CsrEqual 'False' $pending.neutralSite 'Home location is not neutral.'
    Assert-CsrTrue (-not ($pending.PSObject.Properties.Name -contains 'awayPts')) 'Non-final game must not carry scores.'
    Assert-CsrTrue (-not ($pending.PSObject.Properties.Name -contains 'homePts')) 'Non-final game must not carry scores.'

    # 16:05 / 16:25 stay distinct kickoff instants and are ordered by kickoff within the same day.
    $sameDay = @($schedule | Where-Object { $_.gameDate -eq '20301006' })
    Assert-CsrEqual '9004' $sameDay[0].espnID 'Earlier kickoff is listed first.'
    Assert-CsrEqual '9003' $sameDay[1].espnID 'Later kickoff is listed second.'
    Assert-CsrTrue (([double]$sameDay[1].gameTime_epoch - [double]$sameDay[0].gameTime_epoch) -eq 1200) 'Kickoffs stay 20 minutes apart.'

    $tbd = $byEspn['9005']
    Assert-CsrEqual '' $tbd.gameTime_epoch 'Unknown kickoff stays an empty epoch.'
    Assert-CsrEqual 'TBD' $tbd.gameTime 'Unknown kickoff text.'

    $post = @(Get-CanonicalAppSchedule -Season 2030 -RepoRoot $tempRoot -GameTypes @('REG', 'WC'))
    Assert-CsrEqual 6 $post.Count 'Postseason games are included only on request.'
    $wild = $post | Where-Object { $_.espnID -eq '9006' }
    Assert-CsrEqual 'Post Season' $wild.seasonType 'Postseason type label.'

    # Final without a score pair keeps the score unknown instead of inventing zero.
    $noScore = @(
        (New-CsrGame -Id '2030_01_NE_SEA' -Week 1 -Day '2030-10-06' -Time '16:05' -AwayTeamKey 'NE' -HomeTeamKey 'SEA' -Espn '9004')
    )
    Write-CsrFixture -Games $noScore -Finality @([PSCustomObject]@{ GameID = '2030_01_NE_SEA'; Final = $true })
    $unknownScore = @(Get-CanonicalAppSchedule -Season 2030 -RepoRoot $tempRoot)[0]
    Assert-CsrEqual 'Final' $unknownScore.gameStatus 'Finality comes from the finality dataset.'
    Assert-CsrTrue (-not ($unknownScore.PSObject.Properties.Name -contains 'awayPts')) 'Missing canonical score must stay unknown.'

    # --- fail-closed cases ---
    Write-CsrFixture -Games $gameRows -Finality @($finality | Select-Object -First 5)
    Assert-CsrThrows { Get-CanonicalAppSchedule -Season 2030 -RepoRoot $tempRoot } 'finality is missing' 'Schedule game without finality must fail closed.'

    $extraFinality = @($finality) + @([PSCustomObject]@{ GameID = '2030_02_XX_YY'; Final = $false })
    Write-CsrFixture -Games $gameRows -Finality $extraFinality
    Assert-CsrThrows { Get-CanonicalAppSchedule -Season 2030 -RepoRoot $tempRoot } 'not in the schedule' 'Finality game without schedule row must fail closed.'

    $dupEspn = @($gameRows | ForEach-Object { $_ })
    $dupEspn[3] = New-CsrGame -Id '2030_01_NE_SEA' -Week 1 -Day '2030-10-06' -Time '16:05' -AwayTeamKey 'NE' -HomeTeamKey 'SEA' -Espn '9003'
    Write-CsrFixture -Games $dupEspn -Finality $finality
    Assert-CsrThrows { Get-CanonicalAppSchedule -Season 2030 -RepoRoot $tempRoot } 'Duplicate ESPN' 'Duplicate ESPN ID must fail closed.'

    $noEspn = @($gameRows | ForEach-Object { $_ })
    $noEspn[3] = New-CsrGame -Id '2030_01_NE_SEA' -Week 1 -Day '2030-10-06' -Time '16:05' -AwayTeamKey 'NE' -HomeTeamKey 'SEA' -Espn ''
    Write-CsrFixture -Games $noEspn -Finality $finality
    Assert-CsrThrows { Get-CanonicalAppSchedule -Season 2030 -RepoRoot $tempRoot } 'no ESPN' 'Missing ESPN ID must fail closed.'

    $badTeam = @($gameRows | ForEach-Object { $_ })
    $badTeam[3] = New-CsrGame -Id '2030_01_NE_SEA' -Week 1 -Day '2030-10-06' -Time '16:05' -AwayTeamKey 'ZZZ' -HomeTeamKey 'SEA' -Espn '9004'
    Write-CsrFixture -Games $badTeam -Finality $finality
    Assert-CsrThrows { Get-CanonicalAppSchedule -Season 2030 -RepoRoot $tempRoot } 'Unknown NFL team' 'Unknown team must fail closed.'

    Write-CsrFixture -Games @() -Finality @()
    Assert-CsrThrows { Get-CanonicalAppSchedule -Season 2030 -RepoRoot $tempRoot } 'contains no games' 'Empty schedule must fail closed.'

    Write-CsrFixture -Games $gameRows -Finality $finality -ScheduleSource 'other.dataset'
    Assert-CsrThrows { Get-CanonicalAppSchedule -Season 2030 -RepoRoot $tempRoot } 'Unexpected canonical NFL schedule source' 'Unexpected schedule source must fail closed.'

    Write-CsrFixture -Games $gameRows -Finality $finality -FinalitySource 'other.dataset'
    Assert-CsrThrows { Get-CanonicalAppSchedule -Season 2030 -RepoRoot $tempRoot } 'Unexpected canonical NFL finality source' 'Unexpected finality source must fail closed.'

    Write-CsrFixture -Games $gameRows -Finality $finality -Season 2029
    Assert-CsrThrows { Get-CanonicalAppSchedule -Season 2030 -RepoRoot $tempRoot } 'season mismatch' 'Season mismatch must fail closed.'

    Remove-Item (Join-Path $finalityDir '2030.json')
    Assert-CsrThrows { Get-CanonicalAppSchedule -Season 2030 -RepoRoot $tempRoot } 'game finality is required' 'Missing finality file must fail closed.'

    Remove-Item (Join-Path $scheduleDir '2030.json')
    Assert-CsrThrows { Get-CanonicalAppSchedule -Season 2030 -RepoRoot $tempRoot } 'schedule is required' 'Missing schedule file must fail closed.'
}
finally {
    if (Test-Path $tempRoot) { Remove-Item $tempRoot -Recurse -Force }
}

# --- 5. RequestGames no longer calls Tank01 for the schedule or the scores ---
$requestGamesSource = Get-Content (Join-Path $PSScriptRoot 'RequestGames.ps1') -Raw
Assert-CsrTrue ($requestGamesSource.Contains('Get-CanonicalAppSchedule')) 'RequestGames must build the schedule from canonical facts.'
Assert-CsrTrue (-not $requestGamesSource.Contains('getNFLGamesForWeek')) 'RequestGames must not fetch the Tank01 schedule.'
Assert-CsrTrue (-not $requestGamesSource.Contains('getNFLScoresOnly')) 'RequestGames must not fetch Tank01 scores.'

Write-Host 'Canonical schedule regression test passed.' -ForegroundColor Green
