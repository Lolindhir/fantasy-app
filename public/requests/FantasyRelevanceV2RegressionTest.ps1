$ErrorActionPreference = 'Stop'

Import-Module "$PSScriptRoot\utils\league\DecisionWindowUtils.psm1" -Force
Import-Module "$PSScriptRoot\utils\league\FantasyGameContextUtils.psm1" -Force
Import-Module "$PSScriptRoot\utils\league\FantasyRelevanceV2Utils.psm1" -Force

function Assert-FrvEqual {
    param($Expected, $Actual, [string]$Message)
    if ([string]$Expected -ne [string]$Actual) {
        throw "ASSERTION FAILED: $Message. Expected '$Expected', got '$Actual'."
    }
}

function Assert-FrvTrue {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw "ASSERTION FAILED: $Message" }
}

function New-FrvGame {
    param(
        [string]$GameID,
        [string]$StartsAtUtc,
        [string]$AwayTeamID,
        [string]$HomeTeamID,
        [string]$Status = 'Scheduled'
    )
    return [PSCustomObject]@{
        gameID = $GameID
        season = '2026'
        gameWeek = 'Week 1'
        gameTime_epoch = [string]([DateTimeOffset]::Parse($StartsAtUtc).ToUnixTimeSeconds())
        teamIDAway = $AwayTeamID
        teamIDHome = $HomeTeamID
        away = "A$AwayTeamID"
        home = "H$HomeTeamID"
        gameStatus = $Status
    }
}

function New-FrvRankingPlayer {
    param(
        [string]$PlayerID,
        [string]$GameID,
        [string]$StartsAtUtc
    )
    return [PSCustomObject]@{
        PlayerID = $PlayerID
        Placement = 'starter'
        GameState = 'unlocked'
        GameID = $GameID
        DecisionWindowID = $StartsAtUtc
        StartsAtUtc = $StartsAtUtc
        IsBenchCandidate = $false
        LineupSlotID = $null
        EligibleUnlockedSlotIDs = @()
    }
}

$league = [PSCustomObject]@{
    league_id = 'league'
    season = '2026'
    settings = [PSCustomObject]@{ leg = 1 }
    roster_positions = @('QB','TE','FLEX','BN','BN','BN')
}
$teams = @(
    [PSCustomObject]@{
        TeamID = 1
        Roster = @('q1','t1','rb1','wr1','ir1','taxi1')
        Starter = @('q1','t1','0')
        Reserve = @('ir1')
        Taxi = @('taxi1')
    },
    [PSCustomObject]@{
        TeamID = 2
        Roster = @('q2','t2','r2')
        Starter = @('q2','t2','r2')
        Reserve = @()
        Taxi = @()
    }
)
$players = @(
    [PSCustomObject]@{ ID='q1'; Position='QB'; TeamID='1' },
    [PSCustomObject]@{ ID='t1'; Position='TE'; TeamID='3' },
    [PSCustomObject]@{ ID='rb1'; Position='RB'; TeamID='5' },
    [PSCustomObject]@{ ID='wr1'; Position='WR'; TeamID='7' },
    [PSCustomObject]@{ ID='ir1'; Position='TE'; TeamID='9' },
    [PSCustomObject]@{ ID='taxi1'; Position='WR'; TeamID='11' },
    [PSCustomObject]@{ ID='q2'; Position='QB'; TeamID='13' },
    [PSCustomObject]@{ ID='t2'; Position='TE'; TeamID='15' },
    [PSCustomObject]@{ ID='r2'; Position='RB'; TeamID='17' }
)
$schedule = @(
    New-FrvGame -GameID 'g-q1' -StartsAtUtc '2026-09-13T17:00:00Z' -AwayTeamID '1' -HomeTeamID '2' -Status 'Final'
    New-FrvGame -GameID 'g-t1' -StartsAtUtc '2026-09-13T20:00:00Z' -AwayTeamID '3' -HomeTeamID '4'
    New-FrvGame -GameID 'g-rb1' -StartsAtUtc '2026-09-13T20:25:00Z' -AwayTeamID '5' -HomeTeamID '6'
    New-FrvGame -GameID 'g-wr1' -StartsAtUtc '2026-09-13T17:00:00Z' -AwayTeamID '7' -HomeTeamID '8'
    New-FrvGame -GameID 'g-ir1' -StartsAtUtc '2026-09-14T00:20:00Z' -AwayTeamID '9' -HomeTeamID '10'
    New-FrvGame -GameID 'g-taxi1' -StartsAtUtc '2026-09-14T00:20:00Z' -AwayTeamID '11' -HomeTeamID '12'
    New-FrvGame -GameID 'g-q2' -StartsAtUtc '2026-09-13T17:00:00Z' -AwayTeamID '13' -HomeTeamID '14' -Status 'Final'
    New-FrvGame -GameID 'g-t2' -StartsAtUtc '2026-09-13T17:00:00Z' -AwayTeamID '15' -HomeTeamID '16' -Status 'Final'
    New-FrvGame -GameID 'g-r2' -StartsAtUtc '2026-09-13T17:00:00Z' -AwayTeamID '17' -HomeTeamID '18' -Status 'Final'
)

$baseDecision = DecisionWindowUtils\New-CurrentLeagueDecisionWindowsReadModel `
    -League $league -Teams $teams -Players $players -Schedule $schedule -LastLineupWeek 1
$decision = Add-FantasyRelevanceDecisionFacts `
    -BaseReadModel $baseDecision -League $league -Teams $teams -Players $players -Schedule $schedule `
    -AsOfUtc ([DateTimeOffset]::Parse('2026-09-13T19:30:00Z'))

Assert-FrvEqual 2 $decision.SchemaVersion 'DecisionWindows v2 must bump schema version'
$teamOne = @($decision.FantasyRelevance.Teams | Where-Object FantasyTeamID -eq '1')[0]
Assert-FrvEqual 4 $teamOne.ActiveRosterPlayerCount 'Active Roster must mean Starter + Bench only'
Assert-FrvEqual 2 $teamOne.StarterCount 'current starter count'
Assert-FrvEqual 2 $teamOne.BenchCount 'Bench must exclude IR and Taxi'
Assert-FrvEqual 1 $teamOne.IRCount 'IR count'
Assert-FrvEqual 1 $teamOne.TaxiCount 'Taxi count'
Assert-FrvEqual 'q1' (@($teamOne.Slots | Where-Object SlotID -eq 'QB-1')[0].CurrentStarterID) 'starter order must map onto ordered lineup slots'
Assert-FrvEqual 'completed' (@($teamOne.Slots | Where-Object SlotID -eq 'QB-1')[0].State) 'final starter slot must be completed'
Assert-FrvEqual 'unlocked' (@($teamOne.Slots | Where-Object SlotID -eq 'TE-1')[0].State) 'future starter slot must remain mutable'
Assert-FrvEqual 'TE-1' (@($teamOne.Players | Where-Object PlayerID -eq 't1')[0].LineupSlotID) 'starter must retain explicit slot identity'
$rbBench = @($teamOne.Players | Where-Object PlayerID -eq 'rb1')[0]
Assert-FrvEqual 'bench' $rbBench.Placement 'non-starter active player must be Bench'
Assert-FrvTrue $rbBench.IsBenchCandidate 'future RB must be a candidate for an unlocked FLEX slot'
Assert-FrvTrue (@($rbBench.EligibleUnlockedSlotIDs) -contains 'FLEX-1') 'FLEX eligibility must be generator-owned'
Assert-FrvTrue (-not (@($teamOne.Players | Where-Object PlayerID -eq 'wr1')[0].IsBenchCandidate)) 'already locked Bench player must not remain a lineup option'
Assert-FrvEqual 'ir' (@($teamOne.Players | Where-Object PlayerID -eq 'ir1')[0].Placement) 'IR must remain outside Active Roster candidates'
Assert-FrvEqual 'taxi' (@($teamOne.Players | Where-Object PlayerID -eq 'taxi1')[0].Placement) 'Taxi must remain outside Active Roster candidates'

$rawMatchups = @(
    [PSCustomObject]@{ matchup_id=1; roster_id=1; players=@('q1','t1','rb1','wr1','ir1','taxi1'); starters=@('q1','t1'); players_points=[PSCustomObject]@{ q1=10; t1=0; rb1=0; wr1=0; ir1=0; taxi1=0 }; points=10; custom_points=$null },
    [PSCustomObject]@{ matchup_id=1; roster_id=2; players=@('q2','t2','r2'); starters=@('q2','t2','r2'); players_points=[PSCustomObject]@{ q2=10; t2=5; r2=5 }; points=20; custom_points=$null }
)
$matchupFacts = @(ConvertTo-FgcCurrentMatchupFacts -Season '2026' -Week 1 -MatchupRows $rawMatchups)
$context = New-FantasyGameContextReadModel `
    -LeagueID 'league' -Season '2026' -Week 1 -DecisionFacts $decision `
    -FantasyMatchups $matchupFacts -Schedule $schedule -WeekIsFinal $false
$remaining = $context.FantasyMatchups[0].RemainingRelevance
Assert-FrvEqual 'left-only' $remaining.State 'only Team 1 should still have a scoring path'
Assert-FrvEqual '2026-09-13T20:00:00Z' $remaining.NextScoringWindowID 'next scoring window should use the current unlocked starter first'
Assert-FrvEqual '2026-09-13T20:25:00Z' $remaining.FinalScoringWindowID 'eligible later Bench option may extend the provisional final window'
Assert-FrvTrue (-not $remaining.IsFinalScoringWindowCommitted) 'a Bench-only provisional final window must not be called committed'
Assert-FrvEqual 'g-t1' $context.MustWatchGames[0].GameID 'current starter exposure must outrank Bench-only alternatives before lock'
Assert-FrvEqual 1 (@($context.Games | Where-Object GameID -eq 'g-t1')[0].RemainingRelevance.DirectStarterFantasyTeamCount) 'direct starter fantasy-team breadth must be materialized'
Assert-FrvTrue (@(@($context.Games | Where-Object GameID -eq 'g-t1')[0].RemainingRelevance.DirectStarterFantasyTeamIDs) -contains '1') 'direct starter fantasy-team identities must be materialized'

# After the TE kickoff, its starter is committed while the later RB remained on Bench and is now locked out.
$lateDecision = Add-FantasyRelevanceDecisionFacts `
    -BaseReadModel (DecisionWindowUtils\New-CurrentLeagueDecisionWindowsReadModel -League $league -Teams $teams -Players $players -Schedule $schedule -LastLineupWeek 1) `
    -League $league -Teams $teams -Players $players -Schedule $schedule `
    -AsOfUtc ([DateTimeOffset]::Parse('2026-09-13T21:00:00Z'))
$lateContext = New-FantasyGameContextReadModel `
    -LeagueID 'league' -Season '2026' -Week 1 -DecisionFacts $lateDecision `
    -FantasyMatchups $matchupFacts -Schedule $schedule -WeekIsFinal $false
$lateRemaining = $lateContext.FantasyMatchups[0].RemainingRelevance
Assert-FrvEqual '2026-09-13T20:00:00Z' $lateRemaining.FinalScoringWindowID 'locked starter should become the true final remaining window'
Assert-FrvTrue $lateRemaining.IsFinalScoringWindowCommitted 'final window is committed once only locked starters can still score'
$lateGame = @($lateContext.Games | Where-Object GameID -eq 'g-t1')[0]
Assert-FrvEqual 1 $lateGame.RemainingRelevance.CommittedFinalWindowMatchupCount 'committed final-window evidence must be explicit for ranking'
Assert-FrvEqual 1 $lateGame.RemainingRelevance.LockedActiveStarterCount 'live locked starter must drive late-week relevance'
Assert-FrvEqual 'g-t1' $lateContext.MustWatchGames[0].GameID 'committed final-window game must rank first'

# Ordinary upcoming games rank by how many distinct fantasy teams have direct starter exposure,
# before concentrated starter volume or broad matchup-count noise.
$wideTime = '2026-09-20T17:00:00Z'
$concentratedTime = '2026-09-20T20:00:00Z'
$rankingDecisionFacts = [PSCustomObject]@{
    FantasyRelevance = [PSCustomObject]@{
        Teams = @(
            [PSCustomObject]@{ FantasyTeamID='1'; Players=@(
                (New-FrvRankingPlayer -PlayerID 'w1' -GameID 'g-wide' -StartsAtUtc $wideTime),
                (New-FrvRankingPlayer -PlayerID 'c1' -GameID 'g-concentrated' -StartsAtUtc $concentratedTime),
                (New-FrvRankingPlayer -PlayerID 'c2' -GameID 'g-concentrated' -StartsAtUtc $concentratedTime),
                (New-FrvRankingPlayer -PlayerID 'c3' -GameID 'g-concentrated' -StartsAtUtc $concentratedTime)
            ) },
            [PSCustomObject]@{ FantasyTeamID='2'; Players=@(
                (New-FrvRankingPlayer -PlayerID 'w2' -GameID 'g-wide' -StartsAtUtc $wideTime),
                (New-FrvRankingPlayer -PlayerID 'c4' -GameID 'g-concentrated' -StartsAtUtc $concentratedTime),
                (New-FrvRankingPlayer -PlayerID 'c5' -GameID 'g-concentrated' -StartsAtUtc $concentratedTime),
                (New-FrvRankingPlayer -PlayerID 'c6' -GameID 'g-concentrated' -StartsAtUtc $concentratedTime)
            ) },
            [PSCustomObject]@{ FantasyTeamID='3'; Players=@(
                (New-FrvRankingPlayer -PlayerID 'w3' -GameID 'g-wide' -StartsAtUtc $wideTime)
            ) }
        )
    }
}
$rankingBaseContext = [PSCustomObject]@{
    SchemaVersion = 2
    FantasyMatchups = @(
        [PSCustomObject]@{ FantasyMatchupID='m1'; TeamIDs=@('1','2') },
        [PSCustomObject]@{ FantasyMatchupID='m2'; TeamIDs=@('3','4') }
    )
    Games = @(
        [PSCustomObject]@{ GameID='g-wide'; DecisionWindowID=$wideTime; StartsAtUtc=$wideTime },
        [PSCustomObject]@{ GameID='g-concentrated'; DecisionWindowID=$concentratedTime; StartsAtUtc=$concentratedTime }
    )
}
$rankingContext = Add-FantasyRelevanceContext -BaseContext $rankingBaseContext -DecisionFacts $rankingDecisionFacts
$wideGame = @($rankingContext.Games | Where-Object GameID -eq 'g-wide')[0]
$concentratedGame = @($rankingContext.Games | Where-Object GameID -eq 'g-concentrated')[0]
Assert-FrvEqual 3 $wideGame.RemainingRelevance.DirectStarterFantasyTeamCount 'wide game must expose three distinct starter-affected fantasy teams'
Assert-FrvEqual 2 $concentratedGame.RemainingRelevance.DirectStarterFantasyTeamCount 'concentrated game must expose two distinct starter-affected fantasy teams'
Assert-FrvEqual 6 $concentratedGame.RemainingRelevance.UnlockedStarterCount 'ranking fixture must prove concentrated game has more starters'
Assert-FrvEqual 'g-wide' $rankingContext.MustWatchGames[0].GameID 'distinct starter-affected fantasy-team breadth must outrank ordinary starter volume'
Assert-FrvEqual 3 $rankingContext.MustWatchGames[0].DirectStarterFantasyTeamCount 'must-watch rows must retain starter-team breadth'
Assert-FrvTrue (@($rankingContext.MustWatchGames[0].DirectStarterFantasyTeamIDs) -contains '3') 'must-watch rows must retain affected fantasy-team identities'

Write-Host 'Fantasy Relevance v2 regression tests passed.' -ForegroundColor Green
