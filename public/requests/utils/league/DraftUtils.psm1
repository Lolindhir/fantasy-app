# ===========================================================================
# Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\..\ConfigUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\league\TeamUtils.psm1" -ErrorAction Stop -Force
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
        [ValidateSet("Rookie", "Free_Agent")]
        [string]$draftType,

        [Parameter(Mandatory = $true)]
        [ValidateSet("Sleeper", "Manual")]
        [string]$draftSource,

        # Bleibt als optionaler Parameter erhalten, damit bestehende Aufrufe nicht brechen.
        # Wird aber bewusst nicht mehr ins Output-Objekt geschrieben.
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

        OriginalOwnerRosterID = [int]$pick.roster_id
        PreviousOwnerRosterID = [int]$pick.previous_owner_id
        NewOwnerRosterID      = [int]$pick.owner_id
    }

    return $output
}

function Get-DraftPickOutputFromSleeper {
    param(
        [Parameter(Mandatory = $true)]
        [object]$sleeperPick
    )

    return Get-DraftPickOutput `
            -pick $sleeperPick `
            -draftType "Rookie" `
            -draftSource "Sleeper"

}

function Get-DraftPickOutputFromManual {
    param(
        [Parameter(Mandatory = $true)]
        [object]$manualPick
    )

    # Map the manual pick to the internal standard format
    $normalizedPick = [PSCustomObject]@{
        season            = $manualPick.Season
        round             = $manualPick.Round
        roster_id         = Get-OwnerIDByName -ownerName $manualPick.Original
        previous_owner_id = Get-OwnerIDByName -ownerName $manualPick.From
        owner_id          = Get-OwnerIDByName -ownerName $manualPick.To
    }

    return Get-DraftPickOutput `
            -pick $normalizedPick `
            -draftType "Free_Agent" `
            -draftSource "Manual"

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