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

$optionWindow = '2026-09-10T00:20:00Z'
$starterWindow = '2026-09-11T00:35:00Z'

$matchup = [PSCustomObject]@{
    FantasyMatchupID = 'm1'
    TeamIDs = @('1', '2')
    Games = @(
        [PSCustomObject]@{ GameID='g-option'; DecisionWindowID=$optionWindow; StartsAtUtc=$optionWindow; LeftStarterCount=0; RightStarterCount=0 },
        [PSCustomObject]@{ GameID='g-a'; DecisionWindowID=$starterWindow; StartsAtUtc=$starterWindow; LeftStarterCount=1; RightStarterCount=1 },
        [PSCustomObject]@{ GameID='g-b'; DecisionWindowID=$starterWindow; StartsAtUtc=$starterWindow; LeftStarterCount=1; RightStarterCount=0 }
    )
    RemainingRelevance = [PSCustomObject]@{}
}

$base = [PSCustomObject]@{ FantasyMatchups = @($matchup) }
$decision = [PSCustomObject]@{
    FantasyRelevance = [PSCustomObject]@{
        Teams = @(
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
    }
}

$result = Add-FantasyMatchupPreviewContext -BaseContext $base -DecisionFacts $decision
$remaining = $result.FantasyMatchups[0].RemainingRelevance

Assert-FmpEqual $optionWindow $remaining.NextLineupDecisionWindowID 'earlier option-only window must remain a lineup decision'
Assert-FmpEqual 'g-option' $remaining.NextLineupDecisionPrimaryGameID 'lineup decision preview must point to the option game'
Assert-FmpEqual 0 $remaining.NextLineupDecisionStarterCount 'option-only decision must not invent a starter'
Assert-FmpEqual 1 $remaining.NextLineupDecisionOptionCount 'option-only decision must keep the option count'

Assert-FmpEqual $starterWindow $remaining.NextScoringWindowID 'next scoring window must be the later direct-starter window'
Assert-FmpEqual 'g-a' $remaining.NextScoringPrimaryGameID 'primary scoring game must favor the game with more direct starters'
Assert-FmpEqual 2 $remaining.NextScoringWindowGameCount 'all direct-starter games in the selected scoring window must remain represented'
Assert-FmpEqual 0 $remaining.NextScoringLockedActiveStarterCount 'fixture has no locked-active starter in the scoring game'
Assert-FmpEqual 2 $remaining.NextScoringUnlockedStarterCount 'scoring starter count must be matchup/game-specific'
Assert-FmpEqual 1 $remaining.NextScoringOptionCount 'same-game option context may remain secondary on the scoring preview'
Assert-FmpTrue (@($remaining.NextScoringGameIDs) -contains 'g-b') 'selected scoring window must retain secondary direct-starter games'

$sharedWindow = '2026-09-13T17:00:00Z'
$sharedMatchup = [PSCustomObject]@{
    FantasyMatchupID = 'm2'
    TeamIDs = @('3', '4')
    Games = @([PSCustomObject]@{ GameID='g-shared'; DecisionWindowID=$sharedWindow; StartsAtUtc=$sharedWindow; LeftStarterCount=1; RightStarterCount=0 })
    RemainingRelevance = [PSCustomObject]@{}
}
$sharedBase = [PSCustomObject]@{ FantasyMatchups = @($sharedMatchup) }
$sharedDecision = [PSCustomObject]@{
    FantasyRelevance = [PSCustomObject]@{
        Teams = @(
            [PSCustomObject]@{ FantasyTeamID='3'; Players=@(
                (New-FmpPlayer -PlayerID 'starter' -GameID 'g-shared' -WindowID $sharedWindow),
                (New-FmpPlayer -PlayerID 'option' -GameID 'g-shared' -WindowID $sharedWindow -Placement 'bench' -IsBenchCandidate $true)
            ) },
            [PSCustomObject]@{ FantasyTeamID='4'; Players=@() }
        )
    }
}
$sharedResult = Add-FantasyMatchupPreviewContext -BaseContext $sharedBase -DecisionFacts $sharedDecision
$sharedRemaining = $sharedResult.FantasyMatchups[0].RemainingRelevance
Assert-FmpEqual $sharedWindow $sharedRemaining.NextLineupDecisionWindowID 'starter lock is also a lineup decision while unlocked'
Assert-FmpEqual $sharedWindow $sharedRemaining.NextScoringWindowID 'same unlocked starter window must also be the scoring window'
Assert-FmpEqual 'g-shared' $sharedRemaining.NextLineupDecisionPrimaryGameID 'shared decision game must be stable'
Assert-FmpEqual 'g-shared' $sharedRemaining.NextScoringPrimaryGameID 'shared scoring game must be stable'
Assert-FmpEqual 1 $sharedRemaining.NextLineupDecisionStarterCount 'shared decision must include current starter count'
Assert-FmpEqual 1 $sharedRemaining.NextLineupDecisionOptionCount 'shared decision must include option count'

$optionOnlyMatchup = [PSCustomObject]@{
    FantasyMatchupID = 'm3'
    TeamIDs = @('5', '6')
    Games = @([PSCustomObject]@{ GameID='g-only'; DecisionWindowID=$optionWindow; StartsAtUtc=$optionWindow; LeftStarterCount=0; RightStarterCount=0 })
    RemainingRelevance = [PSCustomObject]@{}
}
$optionOnlyBase = [PSCustomObject]@{ FantasyMatchups = @($optionOnlyMatchup) }
$optionOnlyDecision = [PSCustomObject]@{
    FantasyRelevance = [PSCustomObject]@{
        Teams = @(
            [PSCustomObject]@{ FantasyTeamID='5'; Players=@((New-FmpPlayer -PlayerID 'only-opt' -GameID 'g-only' -WindowID $optionWindow -Placement 'bench' -IsBenchCandidate $true)) },
            [PSCustomObject]@{ FantasyTeamID='6'; Players=@() }
        )
    }
}
$optionOnlyResult = Add-FantasyMatchupPreviewContext -BaseContext $optionOnlyBase -DecisionFacts $optionOnlyDecision
$optionOnlyRemaining = $optionOnlyResult.FantasyMatchups[0].RemainingRelevance
Assert-FmpEqual 'g-only' $optionOnlyRemaining.NextLineupDecisionPrimaryGameID 'option-only relevance must remain a lineup decision'
Assert-FmpEqual $null $optionOnlyRemaining.NextScoringPrimaryGameID 'option-only relevance must not be mislabeled as a scoring window'
Assert-FmpEqual 1 $optionOnlyRemaining.NextLineupDecisionOptionCount 'option-only decision must preserve its option count'

Write-Host 'Fantasy matchup preview regression tests passed.' -ForegroundColor Green
