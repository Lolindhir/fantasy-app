$ErrorActionPreference = 'Stop'

Import-Module "$PSScriptRoot\utils\league\PlayerScoringAvailabilityUtils.psm1" -Force
Import-Module "$PSScriptRoot\utils\league\DecisionWindowUtils.psm1" -Force

function Assert-PsaEqual {
    param($Expected, $Actual, [string]$Message)
    if ([string]$Expected -ne [string]$Actual) {
        throw "ASSERTION FAILED: $Message. Expected '$Expected', got '$Actual'."
    }
}

function Assert-PsaTrue {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw "ASSERTION FAILED: $Message" }
}

function New-PsaModel {
    $slot = [PSCustomObject]@{
        SlotID = 'QB-1'; SlotType = 'QB'; SlotOrdinal = 1; SlotIndex = 0
        CurrentStarterID = 'p1'; State = 'locked-active'; GameID = 'g1'
        DecisionWindowID = '2026-09-13T17:00:00Z'; StartsAtUtc = '2026-09-13T17:00:00Z'
        Repairability = $null
    }
    $player = [PSCustomObject]@{
        PlayerID = 'p1'; Placement = 'starter'; Position = 'QB'; GameState = 'locked-active'
        GameID = 'g1'; DecisionWindowID = '2026-09-13T17:00:00Z'; StartsAtUtc = '2026-09-13T17:00:00Z'
        LineupSlotID = 'QB-1'; LineupSlotType = 'QB'; EligibleUnlockedSlotIDs = @()
        IsBenchCandidate = $false; HasDirectScoringPath = $true; HasAlternativePath = $false
    }
    return [PSCustomObject]@{
        SchemaVersion = 2
        FantasyRelevance = [PSCustomObject]@{
            Version = 3
            Teams = @([PSCustomObject]@{
                FantasyTeamID = 1
                UnlockedStarterCount = 0
                LockedActiveStarterCount = 1
                HasRemainingScoringPath = $true
                Slots = @($slot)
                Players = @($player)
            })
        }
    }
}

$out = [PSCustomObject]@{
    PlayerID = 'p1'
    ESPNPlayerID = '4689114'
    State = 'out'
    ProviderStatus = 'OUT'
    Source = 'ESPN'
    ObservedAtUtc = '2026-09-13T20:30:00Z'
}
$model = Add-PlayerScoringAvailabilityDecisionFacts -BaseReadModel (New-PsaModel) -Observations @($out)
$team = $model.FantasyRelevance.Teams[0]
Assert-PsaEqual 'out' $team.Players[0].ScoringAvailability.State 'OUT state must be attached to player'
Assert-PsaEqual 'OUT' $team.Slots[0].ScoringAvailability.ProviderStatus 'Provider status must be preserved on slot'
Assert-PsaEqual '2026-09-13T20:30:00Z' $team.Slots[0].ScoringAvailability.FirstObservedAtUtc 'Legacy observation time must remain available as first-observed evidence'
Assert-PsaTrue (-not [bool]$team.Players[0].HasDirectScoringPath) 'OUT starter must lose direct scoring path'
Assert-PsaEqual 0 $team.LockedActiveStarterCount 'OUT starter must not count as locked-active scoring path'
Assert-PsaTrue (-not [bool]$team.HasRemainingScoringPath) 'OUT-only team must have no remaining direct scoring path'
Assert-PsaEqual 4 $model.FantasyRelevance.Version 'Availability enrichment must bump relevance version'
Assert-PsaEqual 1 @($model.ScoringAvailabilityObservations).Count 'Raw normalized observation must remain auditable'

$model = Add-PlayerScoringAvailabilityDecisionFacts -BaseReadModel (New-PsaModel) -Observations @()
$team = $model.FantasyRelevance.Teams[0]
Assert-PsaEqual 'unknown' $team.Players[0].ScoringAvailability.State 'Missing ESPN observation must remain unknown'
Assert-PsaTrue ([bool]$team.Players[0].HasDirectScoringPath) 'Missing ESPN observation must not remove scoring path'
Assert-PsaEqual 1 $team.LockedActiveStarterCount 'Missing ESPN observation must preserve existing live state'


$previousLegacy = [PSCustomObject]@{
    PlayerID = 'p1'
    ESPNPlayerID = '4689114'
    State = 'uncertain'
    ProviderStatus = 'QUESTIONABLE'
    Source = 'ESPN'
    ObservedAtUtc = '2026-09-13T20:00:00Z'
}
$currentSame = [PSCustomObject]@{
    PlayerID = 'p1'
    ESPNPlayerID = '4689114'
    State = 'uncertain'
    ProviderStatus = 'QUESTIONABLE'
    Source = 'ESPN'
    ObservedAtUtc = '2026-09-13T20:10:00Z'
}
$resolved = @(Resolve-PlayerScoringAvailabilityObservationTimes -CurrentObservations @($currentSame) -PreviousObservations @($previousLegacy))
Assert-PsaEqual '2026-09-13T20:00:00Z' $resolved[0].FirstObservedAtUtc 'Unchanged provider status must preserve first-observed time'
Assert-PsaEqual '2026-09-13T20:00:00Z' $resolved[0].ObservedAtUtc 'Compatibility observation time must stay stable across no-op polls'

$currentDoubtful = [PSCustomObject]@{
    PlayerID = 'p1'
    ESPNPlayerID = '4689114'
    State = 'uncertain'
    ProviderStatus = 'DOUBTFUL'
    Source = 'ESPN'
    ObservedAtUtc = '2026-09-13T20:15:00Z'
}
$resolved = @(Resolve-PlayerScoringAvailabilityObservationTimes -CurrentObservations @($currentDoubtful) -PreviousObservations @($previousLegacy))
Assert-PsaEqual '2026-09-13T20:15:00Z' $resolved[0].FirstObservedAtUtc 'Provider-status change must reset first-observed time even when normalized state stays uncertain'

$previousStable = [PSCustomObject]@{
    PlayerID = 'p1'
    ESPNPlayerID = '4689114'
    State = 'uncertain'
    ProviderStatus = 'DOUBTFUL'
    Source = 'ESPN'
    FirstObservedAtUtc = '2026-09-13T20:15:00Z'
    ObservedAtUtc = '2026-09-13T20:15:00Z'
}
$currentOut = [PSCustomObject]@{
    PlayerID = 'p1'
    ESPNPlayerID = '4689114'
    State = 'out'
    ProviderStatus = 'OUT'
    Source = 'ESPN'
    ObservedAtUtc = '2026-09-13T20:30:00Z'
}
$resolved = @(Resolve-PlayerScoringAvailabilityObservationTimes -CurrentObservations @($currentOut) -PreviousObservations @($previousStable))
Assert-PsaEqual '2026-09-13T20:30:00Z' $resolved[0].FirstObservedAtUtc 'OUT transition must start a new first-observed time'
Assert-PsaEqual '2026-09-13T20:30:00Z' $resolved[0].ObservedAtUtc 'Compatibility timestamp must match the new transition time'

$firstPublished = @(Resolve-PlayerScoringAvailabilityObservationTimes -CurrentObservations @($currentSame) -PreviousObservations @($previousLegacy))
$firstPublishedModel = Add-PlayerScoringAvailabilityDecisionFacts -BaseReadModel (New-PsaModel) -Observations $firstPublished
$laterSame = [PSCustomObject]@{
    PlayerID = 'p1'
    ESPNPlayerID = '4689114'
    State = 'uncertain'
    ProviderStatus = 'QUESTIONABLE'
    Source = 'ESPN'
    ObservedAtUtc = '2026-09-13T20:20:00Z'
}
$secondPublished = @(Resolve-PlayerScoringAvailabilityObservationTimes -CurrentObservations @($laterSame) -PreviousObservations @($firstPublishedModel.ScoringAvailabilityObservations))
$secondPublishedModel = Add-PlayerScoringAvailabilityDecisionFacts -BaseReadModel (New-PsaModel) -Observations $secondPublished
Assert-PsaTrue (-not (Test-DecisionWindowReadModelChanged -OldData $firstPublishedModel -NewData $secondPublishedModel)) 'Unchanged provider status must remain a semantic DecisionWindows no-op even when a later poll occurred'

Write-Host 'Player scoring availability regression tests passed.' -ForegroundColor Green
