Import-Module "$PSScriptRoot\FantasyRelevanceV2Utils.psm1" -ErrorAction Stop

function Test-LineupRepairabilitySlotEligibility {
    param(
        [AllowNull()][string]$Position,
        [Parameter(Mandatory = $true)][string]$SlotType
    )

    return FantasyRelevanceV2Utils\Test-FrvSlotEligibility -Position $Position -SlotType $SlotType
}

function Test-LruCompleteAssignment {
    param(
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$Slots,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$Candidates
    )

    if (@($Slots).Count -eq 0) { return $true }

    $candidatesByID = @{}
    foreach ($candidate in @($Candidates)) {
        $id = ([string]$candidate.PlayerID).Trim()
        if ([string]::IsNullOrWhiteSpace($id)) { continue }
        if ($candidatesByID.ContainsKey($id)) {
            throw "Duplicate repairability candidate '$id'."
        }
        $candidatesByID[$id] = $candidate
    }
    if ($candidatesByID.Count -lt @($Slots).Count) { return $false }

    $eligible = @{}
    foreach ($slot in @($Slots)) {
        $slotID = [string]$slot.SlotID
        $slotType = [string]$slot.SlotType
        if ([string]::IsNullOrWhiteSpace($slotID) -or [string]::IsNullOrWhiteSpace($slotType)) {
            throw 'Repairability requires SlotID and SlotType.'
        }

        $eligible[$slotID] = @(
            $candidatesByID.Keys |
                Where-Object {
                    Test-LineupRepairabilitySlotEligibility `
                        -Position ([string]$candidatesByID[$_].Position) `
                        -SlotType $slotType
                } |
                Sort-Object
        )
        if (@($eligible[$slotID]).Count -eq 0) { return $false }
    }

    $matches = @{}
    function Test-LruAugment {
        param(
            [Parameter(Mandatory = $true)][string]$SlotID,
            [Parameter(Mandatory = $true)][hashtable]$Visited
        )

        foreach ($playerID in @($eligible[$SlotID])) {
            if ($Visited.ContainsKey($playerID)) { continue }
            $Visited[$playerID] = $true

            if (-not $matches.ContainsKey($playerID)) {
                $matches[$playerID] = $SlotID
                return $true
            }

            $previous = [string]$matches[$playerID]
            if (Test-LruAugment -SlotID $previous -Visited $Visited) {
                $matches[$playerID] = $SlotID
                return $true
            }
        }
        return $false
    }

    $ordered = @(
        $Slots | Sort-Object `
            @{ Expression = { @($eligible[[string]$_.SlotID]).Count }; Ascending = $true }, `
            @{ Expression = { [string]$_.SlotID }; Ascending = $true }
    )
    foreach ($slot in $ordered) {
        if (-not (Test-LruAugment -SlotID ([string]$slot.SlotID) -Visited @{})) { return $false }
    }
    return $true
}

function Resolve-LineupRepairabilityState {
    param(
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$MutableSlots,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$InternalCandidates,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$ExternalCandidates,
        [Parameter(Mandatory = $true)][bool]$InternalEvidenceUnknown,
        [Parameter(Mandatory = $true)][ValidateSet('available','unavailable','unknown')][string]$ExternalEvidenceState,
        [Parameter(Mandatory = $true)][bool]$ExternalPlayerEvidenceUnknown
    )

    $internalCount = @($InternalCandidates).Count
    $externalCount = @($ExternalCandidates).Count

    if (@($MutableSlots).Count -eq 0) {
        $state = 'unknown'
        $path = $null
        $reason = 'LINEUP_EVIDENCE_UNKNOWN'
    }
    elseif (Test-LruCompleteAssignment -Slots $MutableSlots -Candidates $InternalCandidates) {
        $state = 'repairable'
        $path = 'internal-roster'
        $reason = 'INTERNAL_ASSIGNMENT_AVAILABLE'
    }
    elseif (
        $ExternalEvidenceState -eq 'available' -and
        (Test-LruCompleteAssignment -Slots $MutableSlots -Candidates (@($InternalCandidates) + @($ExternalCandidates)))
    ) {
        $state = 'repairable'
        $path = 'external-acquisition'
        $reason = 'EXTERNAL_ACQUISITION_ASSIGNMENT_AVAILABLE'
    }
    elseif ($InternalEvidenceUnknown) {
        $state = 'unknown'
        $path = $null
        $reason = 'LINEUP_EVIDENCE_UNKNOWN'
    }
    elseif ($ExternalEvidenceState -eq 'unknown') {
        $state = 'unknown'
        $path = $null
        $reason = 'ACQUISITION_EVIDENCE_UNKNOWN'
    }
    elseif ($ExternalEvidenceState -eq 'available' -and $ExternalPlayerEvidenceUnknown) {
        $state = 'unknown'
        $path = $null
        $reason = 'EXTERNAL_PLAYER_EVIDENCE_UNKNOWN'
    }
    else {
        $state = 'irreparable'
        $path = $null
        $reason = 'NO_LEGAL_REPAIR_PATH'
    }

    return [PSCustomObject][ordered]@{
        State                  = $state
        Path                   = $path
        ReasonCode             = $reason
        InternalCandidateCount = $internalCount
        ExternalCandidateCount = $externalCount
    }
}

Export-ModuleMember -Function Resolve-LineupRepairabilityState, Test-LineupRepairabilitySlotEligibility
