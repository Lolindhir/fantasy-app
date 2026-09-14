$ErrorActionPreference = 'Stop'

Import-Module "$PSScriptRoot\utils\league\ParticipantScoringPathDecisionUtils.psm1" -Force

function Assert-PspEqual {
    param($Expected, $Actual, [string]$Message)
    if ([string]$Expected -ne [string]$Actual) {
        throw "ASSERTION FAILED: $Message. Expected '$Expected', got '$Actual'."
    }
}

function New-PspSlot {
    param(
        [string]$State = 'completed',
        [AllowNull()][string]$RepairabilityState = $null
    )

    $repairability = if ($null -eq $RepairabilityState) {
        $null
    }
    else {
        [PSCustomObject]@{ State = $RepairabilityState }
    }

    return [PSCustomObject]@{
        SlotID = 'QB-1'
        State = $State
        Repairability = $repairability
    }
}

function New-PspModel {
    param(
        [AllowNull()][object]$HasRemainingScoringPath = $false,
        [string]$EvaluationState = 'ready',
        [array]$Slots = @((New-PspSlot))
    )

    $team = [PSCustomObject]@{
        FantasyTeamID = 1
        HasRemainingScoringPath = $HasRemainingScoringPath
        Slots = $Slots
    }

    return [PSCustomObject]@{
        TeamLineupEvaluations = @([PSCustomObject]@{
            FantasyTeamID = 1
            State = $EvaluationState
        })
        FantasyRelevance = [PSCustomObject]@{
            Version = 2
            Teams = @($team)
        }
    }
}

$model = New-PspModel -HasRemainingScoringPath $true
$result = Add-ParticipantScoringPathDecisionFacts -BaseReadModel $model
Assert-PspEqual 'open' $result.FantasyRelevance.Teams[0].RemainingScoringPathState 'Known remaining direct/alternative path must stay open'

$model = New-PspModel -HasRemainingScoringPath $false -Slots @((New-PspSlot -State 'unlocked' -RepairabilityState 'repairable'))
$result = Add-ParticipantScoringPathDecisionFacts -BaseReadModel $model
Assert-PspEqual 'open' $result.FantasyRelevance.Teams[0].RemainingScoringPathState 'Known repairability path must stay open'

$model = New-PspModel -HasRemainingScoringPath $false
$result = Add-ParticipantScoringPathDecisionFacts -BaseReadModel $model
Assert-PspEqual 'none' $result.FantasyRelevance.Teams[0].RemainingScoringPathState 'Complete known evidence with no path must be terminal'
Assert-PspEqual 3 $result.FantasyRelevance.Version 'Participant scoring-path state must bump FantasyRelevance version'

foreach ($evaluationState in @('unknown','review')) {
    $model = New-PspModel -HasRemainingScoringPath $false -EvaluationState $evaluationState
    $result = Add-ParticipantScoringPathDecisionFacts -BaseReadModel $model
    Assert-PspEqual 'unknown' $result.FantasyRelevance.Teams[0].RemainingScoringPathState "Evaluation '$evaluationState' must fail closed"
}

$model = New-PspModel -HasRemainingScoringPath $false -Slots @((New-PspSlot -State 'unknown'))
$result = Add-ParticipantScoringPathDecisionFacts -BaseReadModel $model
Assert-PspEqual 'unknown' $result.FantasyRelevance.Teams[0].RemainingScoringPathState 'Unknown starter lifecycle must fail closed'

$model = New-PspModel -HasRemainingScoringPath $false -Slots @((New-PspSlot -State 'completed' -RepairabilityState 'unknown'))
$result = Add-ParticipantScoringPathDecisionFacts -BaseReadModel $model
Assert-PspEqual 'unknown' $result.FantasyRelevance.Teams[0].RemainingScoringPathState 'Unknown repairability must fail closed'

$model = New-PspModel -HasRemainingScoringPath $null
$result = Add-ParticipantScoringPathDecisionFacts -BaseReadModel $model
Assert-PspEqual 'unknown' $result.FantasyRelevance.Teams[0].RemainingScoringPathState 'Missing path evidence must fail closed'

$model = New-PspModel -HasRemainingScoringPath $false
$first = Add-ParticipantScoringPathDecisionFacts -BaseReadModel $model
$firstJson = $first | ConvertTo-Json -Depth 20 -Compress
$second = Add-ParticipantScoringPathDecisionFacts -BaseReadModel $first
$secondJson = $second | ConvertTo-Json -Depth 20 -Compress
Assert-PspEqual $firstJson $secondJson 'Participant scoring-path enrichment must be idempotent'

Write-Host 'Participant scoring-path regression tests passed.' -ForegroundColor Green
