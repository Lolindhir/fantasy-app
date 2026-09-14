$ErrorActionPreference = 'Stop'

Import-Module "$PSScriptRoot\utils\league\FantasyMatchupPreviewUtils.psm1" -ErrorAction Stop -Force

function Assert-FmpEqual {
    param([object]$Expected, [object]$Actual, [string]$Message)
    if ($Expected -ne $Actual) {
        throw "$Message. Expected '$Expected' but got '$Actual'."
    }
}

function Assert-FmpTrue {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw $Message }
}

function New-FmpPlayer {
    param(
        [string]$PlayerID,
        [string]$GameID,
        [string]$WindowID,
        [string]$Placement = 'starter',
        [string]$GameState = 'unlocked',
        [bool]$IsBenchCandidate = $false
    )

    return [PSCustomObject]@{
        PlayerID         = $PlayerID
        Placement        = $Placement
        GameState        = $GameState
        GameID           = $GameID
        DecisionWindowID = $WindowID
        StartsAtUtc      = $WindowID
        IsBenchCandidate = $IsBenchCandidate
    }
}

function New-FmpMatchup {
    param([string]$MatchupID, [string[]]$TeamIDs)
    return [PSCustomObject]@{
        FantasyMatchupID = $MatchupID
        TeamIDs = @($TeamIDs)
        Games = @()
        RemainingRelevance = [PSCustomObject]@{}
    }
}

function Invoke-FmpFixture {
    param(
        [Parameter(Mandatory = $true)][object]$Matchup,
        [Parameter(Mandatory = $true)][object[]]$Teams
    )
    $base = [PSCustomObject]@{ SchemaVersion = 4; FantasyMatchups = @($Matchup) }
    $decision = [PSCustomObject]@{
        FantasyRelevance = [PSCustomObject]@{ Teams = @($Teams) }
    }
    return Add-FantasyMatchupPreviewContext -BaseContext $base -DecisionFacts $decision
}

$optionWindow = '2026-09-10T00:20:00Z'
$starterWindow = '2026-09-11T00:35:00Z'

# No-live + next, with an earlier option-only lineup-decision window.
$matchup = New-FmpMatchup -MatchupID 'm1' -TeamIDs @('1', '2')
$decisionTeams = @(
    [PSCustomObject]@{ FantasyTeamID='1'; Players=@(
        (New-FmpPlayer -PlayerID 'kicker-option' -GameID 'g-option' -WindowID $optionWindow -Placement 'bench' -IsBenchCandidate $true),
        (New-FmpPlayer -PlayerID 'a-1' -GameID 'g-a' -WindowID $starterWindow),
        (New-FmpPlayer -PlayerID 'b-1' -GameID 'g-b' -WindowID $starterWindow)
    ) },
    [PSCustomObject]@{ FantasyTeamID='2'; Players=@(
        (New-FmpPlayer -PlayerID 'a-2' -GameID 'g-a' -WindowID $starterWindow),
        (New-FmpPlayer -PlayerID 'a-opt' -GameID 'g-a' -WindowID $starterWindow -Placement 'bench' -IsBenchCandidate $true)
    ) }
)
$result = Invoke-FmpFixture -Matchup $matchup -Teams $decisionTeams
$remaining = $result.FantasyMatchups[0].RemainingRelevance

Assert-FmpEqual 5 $result.SchemaVersion 'scoring-window separation must bump FantasyGameContext schema to v5'
Assert-FmpEqual $optionWindow $remaining.NextLineupDecisionWindowID 'earlier option-only window must remain a lineup decision'
Assert-FmpEqual 'g-option' $remaining.NextLineupDecisionPrimaryGameID 'lineup decision preview must point to the option game'
Assert-FmpEqual 0 $remaining.NextLineupDecisionStarterCount 'option-only decision must not invent a starter'
Assert-FmpEqual 1 $remaining.NextLineupDecisionOptionCount 'option-only decision must keep the option count'
Assert-FmpEqual $null $remaining.ActiveScoringWindowID 'no-live fixture must not invent an active scoring window'
Assert-FmpEqual 0 @($remaining.ActiveScoringGameIDs).Count 'no-live fixture must not invent active scoring games'
Assert-FmpEqual $starterWindow $remaining.NextScoringWindowID 'next scoring window must be the future direct-starter window'
Assert-FmpEqual 'g-a' $remaining.NextScoringPrimaryGameID 'primary scoring game must favor the game with more direct starters'
Assert-FmpEqual 2 $remaining.NextScoringWindowGameCount 'all direct-starter games in the selected scoring window must remain represented'
Assert-FmpEqual 0 $remaining.NextScoringLockedActiveStarterCount 'future-only next scoring preview cannot contain locked-active starters'
Assert-FmpEqual 2 $remaining.NextScoringUnlockedStarterCount 'scoring starter count must be matchup/game-specific'
Assert-FmpEqual 1 $remaining.NextScoringOptionCount 'same-game option context may remain secondary on the scoring preview'
Assert-FmpTrue (@($remaining.NextScoringGameIDs) -contains 'g-b') 'selected scoring window must retain secondary direct-starter games'

# Live + future-next + even-later must expose Active and future-only Next independently.
$liveWindow = '2026-09-13T17:00:00Z'
$nextWindow = '2026-09-13T20:25:00Z'
$laterWindow = '2026-09-14T00:20:00Z'
$liveMatchup = New-FmpMatchup -MatchupID 'm-live-next-later' -TeamIDs @('3', '4')
$liveTeams = @(
    [PSCustomObject]@{ FantasyTeamID='3'; Players=@(
        (New-FmpPlayer -PlayerID 'completed' -GameID 'g-completed' -WindowID '2026-09-12T00:00:00Z' -GameState 'completed'),
        (New-FmpPlayer -PlayerID 'live-a' -GameID 'g-live-a' -WindowID $liveWindow -GameState 'locked-active'),
        (New-FmpPlayer -PlayerID 'next-a' -GameID 'g-next' -WindowID $nextWindow),
        (New-FmpPlayer -PlayerID 'later-a' -GameID 'g-later' -WindowID $laterWindow)
    ) },
    [PSCustomObject]@{ FantasyTeamID='4'; Players=@(
        (New-FmpPlayer -PlayerID 'live-b' -GameID 'g-live-b' -WindowID $liveWindow -GameState 'locked-active'),
        (New-FmpPlayer -PlayerID 'next-b' -GameID 'g-next' -WindowID $nextWindow),
        (New-FmpPlayer -PlayerID 'option-between' -GameID 'g-option-between' -WindowID '2026-09-13T19:00:00Z' -Placement 'bench' -IsBenchCandidate $true)
    ) }
)
$liveResult = Invoke-FmpFixture -Matchup $liveMatchup -Teams $liveTeams
$liveRemaining = $liveResult.FantasyMatchups[0].RemainingRelevance
Assert-FmpEqual $liveWindow $liveRemaining.ActiveScoringWindowID 'locked-active direct starters must define the active scoring window'
Assert-FmpEqual 2 @($liveRemaining.ActiveScoringGameIDs).Count 'active scoring breadth must retain every direct-starter NFL game in the live window'
Assert-FmpTrue (@($liveRemaining.ActiveScoringGameIDs) -contains 'g-live-a') 'active window must contain first live direct-starter game'
Assert-FmpTrue (@($liveRemaining.ActiveScoringGameIDs) -contains 'g-live-b') 'active window must contain second live direct-starter game'
Assert-FmpEqual $nextWindow $liveRemaining.NextScoringWindowID 'live window must not consume future-only Next'
Assert-FmpEqual 'g-next' $liveRemaining.NextScoringPrimaryGameID 'future-only Next must point to the next direct-starter NFL game'
Assert-FmpTrue (-not (@($liveRemaining.NextScoringGameIDs) -contains 'g-later')) 'even-later starter game must remain outside the next future scoring window'
Assert-FmpEqual '2026-09-13T19:00:00Z' $liveRemaining.NextLineupDecisionWindowID 'earlier option-only decision may coexist without becoming scoring Next'

# A live final direct-Starter window has Active facts and no future Next, even if an option-only decision remains.
$finalLiveMatchup = New-FmpMatchup -MatchupID 'm-live-final' -TeamIDs @('5', '6')
$finalLiveTeams = @(
    [PSCustomObject]@{ FantasyTeamID='5'; Players=@(
        (New-FmpPlayer -PlayerID 'live-final' -GameID 'g-live-final' -WindowID $liveWindow -GameState 'locked-active'),
        (New-FmpPlayer -PlayerID 'late-option' -GameID 'g-late-option' -WindowID $laterWindow -Placement 'bench' -IsBenchCandidate $true)
    ) },
    [PSCustomObject]@{ FantasyTeamID='6'; Players=@() }
)
$finalLiveResult = Invoke-FmpFixture -Matchup $finalLiveMatchup -Teams $finalLiveTeams
$finalLiveRemaining = $finalLiveResult.FantasyMatchups[0].RemainingRelevance
Assert-FmpEqual $liveWindow $finalLiveRemaining.ActiveScoringWindowID 'live-final fixture must preserve active scoring evidence'
Assert-FmpEqual $null $finalLiveRemaining.NextScoringWindowID 'live-final fixture must not fabricate a future direct-starter scoring window'
Assert-FmpEqual 0 @($finalLiveRemaining.NextScoringGameIDs).Count 'live-final fixture must have no future scoring games'
Assert-FmpEqual $laterWindow $finalLiveRemaining.NextLineupDecisionWindowID 'later option-only decision remains a decision fact'

# Option-only relevance must never become either active or next scoring.
$optionOnlyMatchup = New-FmpMatchup -MatchupID 'm-option-only' -TeamIDs @('7', '8')
$optionOnlyTeams = @(
    [PSCustomObject]@{ FantasyTeamID='7'; Players=@((New-FmpPlayer -PlayerID 'only-opt' -GameID 'g-only' -WindowID $optionWindow -Placement 'bench' -IsBenchCandidate $true)) },
    [PSCustomObject]@{ FantasyTeamID='8'; Players=@() }
)
$optionOnlyResult = Invoke-FmpFixture -Matchup $optionOnlyMatchup -Teams $optionOnlyTeams
$optionOnlyRemaining = $optionOnlyResult.FantasyMatchups[0].RemainingRelevance
Assert-FmpEqual 'g-only' $optionOnlyRemaining.NextLineupDecisionPrimaryGameID 'option-only relevance must remain a lineup decision'
Assert-FmpEqual $null $optionOnlyRemaining.ActiveScoringWindowID 'option-only relevance must not invent live scoring'
Assert-FmpEqual $null $optionOnlyRemaining.NextScoringPrimaryGameID 'option-only relevance must not be mislabeled as future scoring'
Assert-FmpEqual 1 $optionOnlyRemaining.NextLineupDecisionOptionCount 'option-only decision must preserve its option count'

# Re-running the same generator enrichment must be semantically stable.
$stableOnce = ($liveResult | ConvertTo-Json -Depth 20 -Compress)
$stableTwiceResult = Add-FantasyMatchupPreviewContext -BaseContext $liveResult -DecisionFacts ([PSCustomObject]@{
    FantasyRelevance = [PSCustomObject]@{ Teams = @($liveTeams) }
})
$stableTwice = ($stableTwiceResult | ConvertTo-Json -Depth 20 -Compress)
Assert-FmpEqual $stableOnce $stableTwice 'second identical matchup-preview generation must be semantically stable'

Write-Host 'Fantasy matchup preview regression tests passed.' -ForegroundColor Green
