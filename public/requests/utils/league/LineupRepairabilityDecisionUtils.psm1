Import-Module "$PSScriptRoot\LineupRepairabilityUtils.psm1" -ErrorAction Stop -Force
Import-Module "$PSScriptRoot\LineupRepairabilityEvidenceUtils.psm1" -ErrorAction Stop -Force

function Get-LrdValue {
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

function Get-LrdCollection {
    param([AllowNull()][object]$Value)

    if ($null -eq $Value) { return @() }
    if ($Value -is [string] -or $Value -isnot [System.Collections.IEnumerable]) { return @($Value) }
    return @($Value)
}

function ConvertTo-LrdPlayerID {
    param([AllowNull()][object]$Value)

    if ($null -eq $Value) { return $null }
    $text = ([string]$Value).Trim()
    if ([string]::IsNullOrWhiteSpace($text) -or $text -eq '0') { return $null }
    return $text
}

function New-LrdRepairability {
    param(
        [Parameter(Mandatory = $true)][string]$ProblemCode,
        [Parameter(Mandatory = $true)][object]$Resolved
    )

    return [PSCustomObject][ordered]@{
        ProblemCode            = $ProblemCode
        State                  = [string]$Resolved.State
        Path                   = $Resolved.Path
        ReasonCode             = [string]$Resolved.ReasonCode
        InternalCandidateCount = [int]$Resolved.InternalCandidateCount
        ExternalCandidateCount = [int]$Resolved.ExternalCandidateCount
    }
}

function Add-LineupRepairabilityDecisionFacts {
    param(
        [Parameter(Mandatory = $true)][object]$BaseReadModel,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$Teams,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$Players,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$Schedule,
        [AllowNull()][object]$AcquisitionCapability,
        [DateTimeOffset]$AsOfUtc = [DateTimeOffset]::UtcNow
    )

    $relevance = Get-LrdValue -Object $BaseReadModel -Names @('FantasyRelevance')
    if ($null -eq $relevance) { return $BaseReadModel }

    $lineupWeekRaw = Get-LrdValue -Object $BaseReadModel -Names @('LineupWeek')
    if ($null -eq $lineupWeekRaw) { return $BaseReadModel }
    $lineupWeek = [int]$lineupWeekRaw

    $locks = @{}
    foreach ($lock in @(Get-LrdCollection -Value (Get-LrdValue -Object $BaseReadModel -Names @('PlayerLockFacts')))) {
        if ($null -eq $lock) { continue }

        $teamID = ([string](Get-LrdValue -Object $lock -Names @('FantasyTeamID'))).Trim()
        $playerID = ConvertTo-LrdPlayerID -Value (Get-LrdValue -Object $lock -Names @('PlayerID'))
        if ([string]::IsNullOrWhiteSpace($teamID) -or $null -eq $playerID) { continue }
        $locks["$teamID|$playerID"] = $lock
    }

    $evaluations = @{}
    foreach ($evaluation in @(Get-LrdCollection -Value (Get-LrdValue -Object $BaseReadModel -Names @('TeamLineupEvaluations')))) {
        if ($null -eq $evaluation) { continue }
        $teamID = ([string](Get-LrdValue -Object $evaluation -Names @('FantasyTeamID'))).Trim()
        if (-not [string]::IsNullOrWhiteSpace($teamID)) { $evaluations[$teamID] = $evaluation }
    }

    foreach ($teamState in @(Get-LrdCollection -Value (Get-LrdValue -Object $relevance -Names @('Teams')))) {
        if ($null -eq $teamState) { continue }

        $teamID = ([string](Get-LrdValue -Object $teamState -Names @('FantasyTeamID'))).Trim()
        if ([string]::IsNullOrWhiteSpace($teamID)) { continue }

        $slots = @(Get-LrdCollection -Value (Get-LrdValue -Object $teamState -Names @('Slots')))
        foreach ($slot in $slots) {
            if ($null -ne $slot) {
                $slot | Add-Member -NotePropertyName Repairability -NotePropertyValue $null -Force
            }
        }

        $problems = @{}
        foreach ($slot in $slots) {
            if ($null -eq $slot) { continue }

            $slotID = [string](Get-LrdValue -Object $slot -Names @('SlotID'))
            if ([string]::IsNullOrWhiteSpace($slotID)) { continue }

            $starterID = ConvertTo-LrdPlayerID -Value (Get-LrdValue -Object $slot -Names @('CurrentStarterID'))
            if ($null -eq $starterID) {
                $problems[$slotID] = 'OPEN_STARTER_SLOT'
                continue
            }

            $key = "$teamID|$starterID"
            $kind = if ($locks.ContainsKey($key)) {
                [string](Get-LrdValue -Object $locks[$key] -Names @('Kind'))
            }
            else {
                'unknown'
            }
            if ($kind -eq 'bye') { $problems[$slotID] = 'STARTER_ON_BYE' }
        }
        if ($problems.Count -eq 0) { continue }

        $evaluationState = if ($evaluations.ContainsKey($teamID)) {
            [string](Get-LrdValue -Object $evaluations[$teamID] -Names @('State'))
        }
        else {
            'unknown'
        }

        if (@('unknown','review') -contains $evaluationState) {
            $unknown = [PSCustomObject]@{
                State                  = 'unknown'
                Path                   = $null
                ReasonCode             = 'LINEUP_EVIDENCE_UNKNOWN'
                InternalCandidateCount = 0
                ExternalCandidateCount = 0
            }
            foreach ($slot in $slots) {
                $slotID = [string](Get-LrdValue -Object $slot -Names @('SlotID'))
                if ($problems.ContainsKey($slotID)) {
                    $slot.Repairability = New-LrdRepairability -ProblemCode $problems[$slotID] -Resolved $unknown
                }
            }
            continue
        }

        $mutableSlots = @()
        $mutableSlotIDs = @{}
        foreach ($slot in $slots) {
            if ($null -eq $slot) { continue }

            $slotID = [string](Get-LrdValue -Object $slot -Names @('SlotID'))
            $starterID = ConvertTo-LrdPlayerID -Value (Get-LrdValue -Object $slot -Names @('CurrentStarterID'))
            $state = [string](Get-LrdValue -Object $slot -Names @('State'))
            $mutable = $null -eq $starterID

            if (-not $mutable) {
                $key = "$teamID|$starterID"
                $kind = if ($locks.ContainsKey($key)) {
                    [string](Get-LrdValue -Object $locks[$key] -Names @('Kind'))
                }
                else {
                    'unknown'
                }
                $mutable = $kind -eq 'bye' -or $state -eq 'unlocked'
            }

            if ($mutable) {
                $mutableSlots += $slot
                $mutableSlotIDs[$slotID] = $true
            }
        }

        $internal = @()
        $internalUnknown = $false
        foreach ($player in @(Get-LrdCollection -Value (Get-LrdValue -Object $teamState -Names @('Players')))) {
            if ($null -eq $player) { continue }

            $placement = [string](Get-LrdValue -Object $player -Names @('Placement'))
            if (@('starter','bench') -notcontains $placement) { continue }

            $playerID = ConvertTo-LrdPlayerID -Value (Get-LrdValue -Object $player -Names @('PlayerID'))
            if ($null -eq $playerID) { continue }

            if ($placement -eq 'starter') {
                $lineupSlotID = [string](Get-LrdValue -Object $player -Names @('LineupSlotID'))
                if (
                    [string]::IsNullOrWhiteSpace($lineupSlotID) -or
                    -not $mutableSlotIDs.ContainsKey($lineupSlotID)
                ) {
                    continue
                }
            }

            $position = ([string](Get-LrdValue -Object $player -Names @('Position'))).Trim().ToUpperInvariant()
            $gameState = [string](Get-LrdValue -Object $player -Names @('GameState'))
            $key = "$teamID|$playerID"
            $kind = if ($locks.ContainsKey($key)) {
                [string](Get-LrdValue -Object $locks[$key] -Names @('Kind'))
            }
            else {
                'unknown'
            }
            $relevant = -not [string]::IsNullOrWhiteSpace($position) -and @(
                $mutableSlots | Where-Object {
                    Test-LineupRepairabilitySlotEligibility -Position $position -SlotType ([string]$_.SlotType)
                }
            ).Count -gt 0

            if ($kind -eq 'scheduled' -and $gameState -eq 'unlocked') {
                if ([string]::IsNullOrWhiteSpace($position)) {
                    $internalUnknown = $true
                }
                elseif ($relevant) {
                    $internal += [PSCustomObject][ordered]@{
                        PlayerID = $playerID
                        Position = $position
                    }
                }
            }
            elseif ($kind -eq 'unknown' -and ([string]::IsNullOrWhiteSpace($position) -or $relevant)) {
                $internalUnknown = $true
            }
        }

        $external = Get-LineupExternalRepairEvidence `
            -Players $Players `
            -Teams $Teams `
            -Schedule $Schedule `
            -MutableSlots $mutableSlots `
            -AcquisitionCapability $AcquisitionCapability `
            -LineupWeek $lineupWeek `
            -AsOfUtc $AsOfUtc

        $resolved = Resolve-LineupRepairabilityState `
            -MutableSlots $mutableSlots `
            -InternalCandidates $internal `
            -ExternalCandidates @($external.Candidates) `
            -InternalEvidenceUnknown $internalUnknown `
            -ExternalEvidenceState ([string]$external.State) `
            -ExternalPlayerEvidenceUnknown ([bool]$external.PlayerEvidenceUnknown)

        foreach ($slot in $slots) {
            $slotID = [string](Get-LrdValue -Object $slot -Names @('SlotID'))
            if ($problems.ContainsKey($slotID)) {
                $slot.Repairability = New-LrdRepairability -ProblemCode $problems[$slotID] -Resolved $resolved
            }
        }
    }

    if ($relevance.PSObject.Properties.Name -contains 'Version') {
        $relevance.Version = [Math]::Max(2, [int]$relevance.Version)
    }
    return $BaseReadModel
}

Export-ModuleMember -Function Add-LineupRepairabilityDecisionFacts
