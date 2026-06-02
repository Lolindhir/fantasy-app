# ===========================================================================
# Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\..\ConfigUtils.psm1" -ErrorAction Stop -Force
}
catch {
    Write-Error "Fehler beim Laden der Module: $_"
    throw $_
}

# ===========================================================================
# Draft Pick Build Utils
# ===========================================================================

function Get-DraftPickOutput {
    param(
        [Parameter(Mandatory = $true)]
        [object]$pick,

        [Parameter(Mandatory = $true)]
        [ValidateSet("Rookie", "FreeAgent")]
        [string]$draftType,

        [Parameter(Mandatory = $true)]
        [ValidateSet("Sleeper", "Manual")]
        [string]$draftSource,

        [string]$transactionID = $null
    )

    $season = [string]$pick.season
    $round = [int]$pick.round

    $output = [PSCustomObject][ordered]@{
        DraftType             = $draftType
        DraftSource           = $draftSource
        DraftKey              = "$($season)_$($draftType)"

        Season                = $season
        Round                 = $round

        OriginalRosterID      = [int]$pick.roster_id
        PreviousOwnerRosterID = [int]$pick.previous_owner_id
        OwnerRosterID         = [int]$pick.owner_id

        TransactionID         = $transactionID
    }

    return $output
}

function Get-DraftPickOutputsFromSleeperTransaction {
    param(
        [Parameter(Mandatory = $true)]
        [object]$sleeperTransaction
    )

    $draftPicks = @()

    if (-not $sleeperTransaction.draft_picks) {
        return @()
    }

    foreach ($pick in (ConvertTo-DraftSafeArray -value $sleeperTransaction.draft_picks)) {
        $draftPicks += Get-DraftPickOutput `
            -pick $pick `
            -draftType "Rookie" `
            -draftSource "Sleeper" `
            -transactionID $sleeperTransaction.transaction_id
    }

    return $draftPicks
}

function ConvertTo-DraftSafeArray {
    param(
        [AllowNull()]
        $value
    )

    if ($null -eq $value) {
        return @()
    }

    if ($value -is [array]) {
        return $value
    }

    return @($value)
}