$ErrorActionPreference = 'Stop'

Import-Module "$PSScriptRoot\utils\league\FantasyWeeklyWatchUtils.psm1" -Force

function Assert-FwwEqual {
    param($Expected, $Actual, [string]$Message)
    if ([string]$Expected -ne [string]$Actual) {
        throw "ASSERTION FAILED: $Message. Expected '$Expected', got '$Actual'."
    }
}

function Assert-FwwTrue {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw "ASSERTION FAILED: $Message" }
}

function New-FwwFantasyTeam {
    param([string]$TeamID, [string]$MatchupID, [int]$StarterCount)
    return [PSCustomObject]@{
        FantasyTeamID = $TeamID
        FantasyMatchupID = $MatchupID
        StarterCount = $StarterCount
    }
}

function New-FwwGame {
    param(
        [string]$GameID,
        [string]$StartsAtUtc,
        [string]$Status,
        [array]$FantasyTeams,
        [int]$LockedActiveStarterCount = 0,
        [bool]$HasRemainingRelevance = $true
    )

    $starterCount = @($FantasyTeams | Measure-Object -Property StarterCount -Sum).Sum
    return [PSCustomObject]@{
        GameID = $GameID
        DecisionWindowID = $StartsAtUtc
        StartsAtUtc = $StartsAtUtc
        Status = $Status
        Relevance = [PSCustomObject]@{ StarterCount = [int]$starterCount }
        FantasyTeams = $FantasyTeams
        RemainingRelevance = [PSCustomObject]@{
            HasRemainingRelevance = $HasRemainingRelevance
            CommittedFinalWindowMatchupCount = 0
            LockedActiveStarterCount = $LockedActiveStarterCount
            DirectStarterFantasyTeamCount = 0
            DirectStarterFantasyTeamIDs = @()
            UnlockedStarterCount = 0
            TwoSidedFantasyMatchupCount = 0
            FantasyMatchupCount = 0
            FinalWindowFantasyMatchupCount = 0
            EligibleBenchCandidateCount = 0
        }
    }
}

$finalBroad = New-FwwGame `
    -GameID 'g-final-broad' `
    -StartsAtUtc '2026-09-10T00:20:00Z' `
    -Status 'Final' `
    -HasRemainingRelevance $false `
    -FantasyTeams @(
        (New-FwwFantasyTeam -TeamID '1' -MatchupID 'm1' -StarterCount 1),
        (New-FwwFantasyTeam -TeamID '2' -MatchupID 'm1' -StarterCount 1),
        (New-FwwFantasyTeam -TeamID '3' -MatchupID 'm2' -StarterCount 1),
        (New-FwwFantasyTeam -TeamID '4' -MatchupID 'm2' -StarterCount 1)
    )
$liveConcentrated = New-FwwGame `
    -GameID 'g-live-concentrated' `
    -StartsAtUtc '2026-09-11T00:35:00Z' `
    -Status 'Scheduled' `
    -LockedActiveStarterCount 6 `
    -FantasyTeams @(
        (New-FwwFantasyTeam -TeamID '1' -MatchupID 'm1' -StarterCount 3),
        (New-FwwFantasyTeam -TeamID '2' -MatchupID 'm1' -StarterCount 3)
    )
$upcomingWide = New-FwwGame `
    -GameID 'g-upcoming-wide' `
    -StartsAtUtc '2026-09-13T17:00:00Z' `
    -Status 'Scheduled' `
    -FantasyTeams @(
        (New-FwwFantasyTeam -TeamID '1' -MatchupID 'm1' -StarterCount 1),
        (New-FwwFantasyTeam -TeamID '3' -MatchupID 'm2' -StarterCount 1),
        (New-FwwFantasyTeam -TeamID '5' -MatchupID 'm3' -StarterCount 1)
    )
$noStarters = New-FwwGame `
    -GameID 'g-options-only' `
    -StartsAtUtc '2026-09-14T00:20:00Z' `
    -Status 'Scheduled' `
    -FantasyTeams @(
        (New-FwwFantasyTeam -TeamID '6' -MatchupID 'm3' -StarterCount 0)
    )

$context = [PSCustomObject]@{
    SchemaVersion = 3
    Games = @($liveConcentrated, $upcomingWide, $finalBroad, $noStarters)
    MustWatchGames = @()
}

$result = Add-FantasyWeeklyWatchContext -BaseContext $context

Assert-FwwEqual 4 $result.SchemaVersion 'weekly Must-watch semantics must bump FantasyGameContext schema to v4'
Assert-FwwEqual 3 @($result.MustWatchGames).Count 'only games with actual Starter exposure belong to weekly Must-watch'
Assert-FwwEqual 'g-final-broad' $result.MustWatchGames[0].GameID 'broad Starter-team exposure must outrank live-state urgency'
Assert-FwwEqual 'g-upcoming-wide' $result.MustWatchGames[1].GameID 'three Starter teams must outrank concentrated six-starter exposure from two teams'
Assert-FwwEqual 'g-live-concentrated' $result.MustWatchGames[2].GameID 'live status must not promote a game above broader weekly Starter impact'
Assert-FwwEqual 4 $result.MustWatchGames[0].DirectStarterFantasyTeamCount 'stable weekly row must preserve Starter-team breadth for Final games'
Assert-FwwEqual 2 $result.MustWatchGames[0].FantasyMatchupCount 'stable weekly row must preserve matchup breadth for Final games'
Assert-FwwTrue (@($result.MustWatchGames[0].DirectStarterFantasyTeamIDs) -contains '4') 'Final weekly row must retain Starter-team identities'
Assert-FwwEqual 1 $finalBroad.RemainingRelevance.MustWatchRank 'Final game must retain its weekly Must-watch rank after remaining relevance reaches none'
Assert-FwwEqual '' $noStarters.RemainingRelevance.MustWatchRank 'option-only games must not receive a weekly Must-watch rank'

# Changing only game state / remaining relevance must not change weekly ordering.
$liveConcentrated.Status = 'Final'
$liveConcentrated.RemainingRelevance.HasRemainingRelevance = $false
$liveConcentrated.RemainingRelevance.LockedActiveStarterCount = 0
$finalBroad.Status = 'Scheduled'
$finalBroad.RemainingRelevance.HasRemainingRelevance = $true
$finalBroad.RemainingRelevance.LockedActiveStarterCount = 4
$resultAfterStateChange = Add-FantasyWeeklyWatchContext -BaseContext $context
Assert-FwwEqual 'g-final-broad' $resultAfterStateChange.MustWatchGames[0].GameID 'Upcoming/Live/Final transitions alone must not reorder weekly Must-watch'
Assert-FwwEqual 'g-upcoming-wide' $resultAfterStateChange.MustWatchGames[1].GameID 'weekly ordering must stay Starter-exposure driven'
Assert-FwwEqual 'g-live-concentrated' $resultAfterStateChange.MustWatchGames[2].GameID 'state-only changes must not alter membership or rank'

Write-Host 'Fantasy weekly Must-watch regression tests passed.' -ForegroundColor Green