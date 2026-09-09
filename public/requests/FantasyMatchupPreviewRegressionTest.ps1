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
$starterWindow = '2026-09-13T17:00:00Z'

$matchup = [PSCustomObject]@{
    FantasyMatchupID = 'm1'
    TeamIDs = @('1', '2')
    Games = @(
        [PSCustomObject]@{ GameID='g-option'; DecisionWindowID=$optionWindow; StartsAtUtc=$optionWindow; LeftStarterCount=0; RightStarterCount=0 },
        [PSCustomObject]@{ GameID='g-a'; DecisionWindowID=$starterWindow; StartsAtUtc=$starterWindow; LeftStarterCount=1; RightStarterCount=1 },
        [PSCustomObject]@{ GameID='g-b'; DecisionWindowID=$starterWindow; StartsAtUtc=$starterWindow; LeftStarterCount=1; RightStarterCount=0 }
    )
    RemainingRelevance = [PSCustomObject]@{
        NextScoringWindowID = $optionWindow
        NextScoringGameIDs = @('g-option')
    }
}

$base = [PSCustomObject]@{ FantasyMatchups = @($matchup) }
$decision = [PSCustomObject]@{
    FantasyRelevance = [PSCustomObject]@{
        Teams = @(
            [PSCustomObject]@{ FantasyTeamID='1'; Players=@(
                (New-FmpPlayer -PlayerID 'opt-1' -GameID 'g-option' -WindowID $optionWindow -Placement 'bench' -IsBenchCandidate $true),
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
Assert-FmpEqual $starterWindow $remaining.NextScoringWindowID 'direct starter window must outrank earlier option-only window'
Assert-FmpEqual 'g-a' $remaining.NextScoringPrimaryGameID 'primary preview game must favor the game with more direct starters'
Assert-FmpEqual 2 $remaining.NextScoringWindowGameCount 'all relevant games in the selected starter window must remain represented'
Assert-FmpEqual 0 $remaining.NextScoringLockedActiveStarterCount 'fixture has no locked-active starter in the preview game'
Assert-FmpEqual 2 $remaining.NextScoringUnlockedStarterCount 'preview starter count must be matchup/game-specific'
Assert-FmpEqual 1 $remaining.NextScoringOptionCount 'preview option count must be matchup/game-specific'
Assert-FmpTrue (@($remaining.NextScoringGameIDs) -contains 'g-b') 'selected window must retain secondary relevant games'

$optionOnlyMatchup = [PSCustomObject]@{
    FantasyMatchupID = 'm2'
    TeamIDs = @('3', '4')
    Games = @([PSCustomObject]@{ GameID='g-only'; DecisionWindowID=$optionWindow; StartsAtUtc=$optionWindow; LeftStarterCount=0; RightStarterCount=0 })
    RemainingRelevance = [PSCustomObject]@{}
}
$optionOnlyBase = [PSCustomObject]@{ FantasyMatchups = @($optionOnlyMatchup) }
$optionOnlyDecision = [PSCustomObject]@{
    FantasyRelevance = [PSCustomObject]@{
        Teams = @(
            [PSCustomObject]@{ FantasyTeamID='3'; Players=@((New-FmpPlayer -PlayerID 'only-opt' -GameID 'g-only' -WindowID $optionWindow -Placement 'bench' -IsBenchCandidate $true)) },
            [PSCustomObject]@{ FantasyTeamID='4'; Players=@() }
        )
    }
}
$optionOnlyResult = Add-FantasyMatchupPreviewContext -BaseContext $optionOnlyBase -DecisionFacts $optionOnlyDecision
$optionOnlyRemaining = $optionOnlyResult.FantasyMatchups[0].RemainingRelevance
Assert-FmpEqual 'g-only' $optionOnlyRemaining.NextScoringPrimaryGameID 'option-only relevance must remain a deterministic fallback when no direct starter path exists'
Assert-FmpEqual 0 $optionOnlyRemaining.NextScoringUnlockedStarterCount 'option-only fallback must not invent starters'
Assert-FmpEqual 1 $optionOnlyRemaining.NextScoringOptionCount 'option-only fallback must preserve its option count'

Write-Host 'Fantasy matchup preview regression tests passed.' -ForegroundColor Green
