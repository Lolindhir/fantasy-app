# ===========================================================================
# Draft Pick Result Utils
# ===========================================================================
#
# Applies Sleeper draft pick result data to generated draft pick objects.
# This is shared by current/live drafts and completed draft history.

try {
    Import-Module "$PSScriptRoot\DraftUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\invoke\SleeperUtils.psm1" -ErrorAction Stop -Force
}
catch {
    Write-Error "Fehler beim Laden der Module: $_"
    throw $_
}

function Get-DraftSleeperPicksSafe {
    param([Parameter(Mandatory = $true)][object]$sleeperDraft)

    $draftID = Get-DraftObjectProperty -object $sleeperDraft -propertyName "draft_id" -defaultValue $null
    if ([string]::IsNullOrWhiteSpace($draftID)) { return @() }

    try { return ConvertTo-DraftSafeArray -value (Get-SleeperDraftPicks -draftID $draftID) }
    catch {
        Write-Warning "Could not load Sleeper draft picks for draft '$draftID'. Keeping generated picks without result enrichment. $_"
        return @()
    }
}

function Get-DraftPlayerNameFromSleeperPick {
    param([AllowNull()]$sleeperPick)

    if ($null -eq $sleeperPick) { return $null }

    $metadata = Get-DraftObjectProperty -object $sleeperPick -propertyName "metadata" -defaultValue $null
    if ($null -eq $metadata) { return $null }

    $firstName = [string](Get-DraftObjectProperty -object $metadata -propertyName "first_name" -defaultValue "")
    $lastName = [string](Get-DraftObjectProperty -object $metadata -propertyName "last_name" -defaultValue "")
    $fullName = [string](Get-DraftObjectProperty -object $metadata -propertyName "full_name" -defaultValue "")
    $name = (($firstName, $lastName | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }) -join " ").Trim()

    if (-not [string]::IsNullOrWhiteSpace($name)) { return $name }
    if (-not [string]::IsNullOrWhiteSpace($fullName)) { return $fullName.Trim() }
    return $null
}

function Get-AppliedDraftPickResults {
    param(
        [Parameter(Mandatory = $true)][array]$picks,
        [Parameter(Mandatory = $true)][object]$sleeperDraft,
        [AllowNull()]$sleeperPicks = $null
    )

    $draftID = Get-DraftObjectProperty -object $sleeperDraft -propertyName "draft_id" -defaultValue $null
    if ([string]::IsNullOrWhiteSpace($draftID)) { return $picks }

    if ($null -eq $sleeperPicks) { $sleeperPicks = Get-DraftSleeperPicksSafe -sleeperDraft $sleeperDraft }
    else { $sleeperPicks = ConvertTo-DraftSafeArray -value $sleeperPicks }

    if ($sleeperPicks.Count -eq 0) { return $picks }

    $pickByOverall = @{}
    foreach ($pick in $picks) {
        if ($null -ne $pick.OverallPick -and -not [string]::IsNullOrWhiteSpace([string]$pick.OverallPick)) {
            $pickByOverall[[int]$pick.OverallPick] = $pick
        }
    }

    foreach ($sleeperPick in $sleeperPicks) {
        $pickNo = Get-DraftObjectProperty -object $sleeperPick -propertyName "pick_no" -defaultValue $null
        $playerID = Get-DraftObjectProperty -object $sleeperPick -propertyName "player_id" -defaultValue $null
        $pickOwnerRosterID = Get-DraftObjectProperty -object $sleeperPick -propertyName "roster_id" -defaultValue $null
        if ($null -eq $pickNo -or [string]::IsNullOrWhiteSpace([string]$pickNo)) { continue }

        $overallPick = [int]$pickNo
        if (-not $pickByOverall.ContainsKey($overallPick)) {
            Write-Warning "Could not map Sleeper pick_no '$overallPick' from draft '$draftID' to generated draft picks."
            continue
        }

        $targetPick = $pickByOverall[$overallPick]
        $targetPick.SleeperPickNo = $overallPick
        $targetPick.SleeperPickedBy = [string](Get-DraftObjectProperty -object $sleeperPick -propertyName "picked_by" -defaultValue $null)

        if ($null -ne $pickOwnerRosterID -and -not [string]::IsNullOrWhiteSpace([string]$pickOwnerRosterID)) {
            $ownerRosterID = [int]$pickOwnerRosterID
            $targetPick.CurrentOwnerRosterID = $ownerRosterID
            $isTraded = ([int]$targetPick.OriginalOwnerRosterID -ne [int]$targetPick.CurrentOwnerRosterID)
            $targetPick.WasTraded = $isTraded
            $targetPick.IsCurrentlyTraded = $isTraded

            if ($isTraded -and [string]::IsNullOrWhiteSpace([string]$targetPick.TradeSource)) {
                $targetPick.TradeSource = "SleeperDraftPick"
            }
        }

        if ($null -ne $playerID -and -not [string]::IsNullOrWhiteSpace([string]$playerID)) {
            $targetPick.PlayerID = [string]$playerID
            $targetPick.PlayerName = Get-DraftPlayerNameFromSleeperPick -sleeperPick $sleeperPick
            $targetPick.Status = "Picked"
        }
    }

    return $picks
}
