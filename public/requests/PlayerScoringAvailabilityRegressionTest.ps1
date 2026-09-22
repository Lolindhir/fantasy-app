$ErrorActionPreference = 'Stop'

Import-Module "$PSScriptRoot\utils\league\PlayerScoringAvailabilityUtils.psm1" -Force

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

Write-Host 'Player scoring availability regression tests passed.' -ForegroundColor Green
