function Get-PspValue {
    param(
        [AllowNull()][object]$Object,
        [Parameter(Mandatory = $true)][string[]]$Names
    )

    if ($null -eq $Object) { return $null }
    foreach ($name in $Names) {
        if ($Object.PSObject.Properties.Name -contains $name) { return $Object.$name }
    }
    return $null
}

function Get-PspCollection {
    param([AllowNull()][object]$Value)

    if ($null -eq $Value) { return @() }
    if ($Value -is [string] -or $Value -isnot [System.Collections.IEnumerable]) { return @($Value) }
    return @($Value)
}

function Resolve-ParticipantRemainingScoringPathState {
    param(
        [Parameter(Mandatory = $true)][object]$TeamState,
        [AllowNull()][object]$LineupEvaluation
    )

    $hasPath = Get-PspValue -Object $TeamState -Names @('HasRemainingScoringPath')
    $slots = @(Get-PspCollection (Get-PspValue -Object $TeamState -Names @('Slots')))
    $hasRepairablePath = @(
        $slots | Where-Object {
            [string](Get-PspValue -Object (Get-PspValue -Object $_ -Names @('Repairability')) -Names @('State')) -eq 'repairable'
        }
    ).Count -gt 0

    if ($hasPath -eq $true -or $hasRepairablePath) { return 'open' }
    if ($null -eq $hasPath) { return 'unknown' }

    $evaluationState = [string](Get-PspValue -Object $LineupEvaluation -Names @('State'))
    if ($null -eq $LineupEvaluation -or @('unknown','review') -contains $evaluationState) {
        return 'unknown'
    }

    foreach ($slot in $slots) {
        if ([string](Get-PspValue -Object $slot -Names @('State')) -eq 'unknown') {
            return 'unknown'
        }
        $repairability = Get-PspValue -Object $slot -Names @('Repairability')
        if ($null -ne $repairability -and [string](Get-PspValue -Object $repairability -Names @('State')) -eq 'unknown') {
            return 'unknown'
        }
    }

    return 'none'
}

function Add-ParticipantScoringPathDecisionFacts {
    param([Parameter(Mandatory = $true)][object]$BaseReadModel)

    $relevance = Get-PspValue -Object $BaseReadModel -Names @('FantasyRelevance')
    if ($null -eq $relevance) { return $BaseReadModel }

    $evaluations = @{}
    foreach ($evaluation in @(Get-PspCollection (Get-PspValue -Object $BaseReadModel -Names @('TeamLineupEvaluations')))) {
        if ($null -eq $evaluation) { continue }
        $teamID = ([string](Get-PspValue -Object $evaluation -Names @('FantasyTeamID'))).Trim()
        if (-not [string]::IsNullOrWhiteSpace($teamID)) { $evaluations[$teamID] = $evaluation }
    }

    foreach ($teamState in @(Get-PspCollection (Get-PspValue -Object $relevance -Names @('Teams')))) {
        if ($null -eq $teamState) { continue }
        $teamID = ([string](Get-PspValue -Object $teamState -Names @('FantasyTeamID'))).Trim()
        $evaluation = if (-not [string]::IsNullOrWhiteSpace($teamID) -and $evaluations.ContainsKey($teamID)) {
            $evaluations[$teamID]
        }
        else {
            $null
        }
        $state = Resolve-ParticipantRemainingScoringPathState -TeamState $teamState -LineupEvaluation $evaluation
        $teamState | Add-Member -NotePropertyName RemainingScoringPathState -NotePropertyValue $state -Force
    }

    if ($relevance.PSObject.Properties.Name -contains 'Version') {
        $relevance.Version = [Math]::Max(3, [int]$relevance.Version)
    }
    return $BaseReadModel
}

Export-ModuleMember -Function Add-ParticipantScoringPathDecisionFacts, Resolve-ParticipantRemainingScoringPathState
