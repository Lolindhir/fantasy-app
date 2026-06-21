# ===========================================================================
# Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\..\league\DraftUtils.psm1" -ErrorAction Stop -Force
}
catch {
    Write-Error "Fehler beim Laden der Module: $_"
    throw $_
}

# ===========================================================================
# Draft History: Sleeper Pick Owner Enrichment
# ===========================================================================

function Get-DraftHistoryRosterIDFromSleeperPick {
    param([AllowNull()]$sleeperPick)

    if ($null -eq $sleeperPick) { return $null }

    $rosterID = Get-DraftObjectProperty -object $sleeperPick -propertyName "roster_id" -defaultValue $null
    if ($null -eq $rosterID -or [string]::IsNullOrWhiteSpace([string]$rosterID)) { return $null }

    return [int]$rosterID
}

function Set-DraftHistoryPickOwnerFromSleeperPick {
    param(
        [Parameter(Mandatory = $true)]$targetPick,
        [Parameter(Mandatory = $true)]$sleeperPick
    )

    $currentOwnerRosterID = Get-DraftHistoryRosterIDFromSleeperPick -sleeperPick $sleeperPick
    if ($null -eq $currentOwnerRosterID) { return }

    $targetPick.CurrentOwnerRosterID = [int]$currentOwnerRosterID
    $targetPick.IsCurrentlyTraded = ([int]$targetPick.CurrentOwnerRosterID -ne [int]$targetPick.OriginalOwnerRosterID)

    if ($targetPick.IsCurrentlyTraded) {
        $targetPick.WasTraded = $true
        if ([string]::IsNullOrWhiteSpace([string]$targetPick.TradeSource)) {
            $targetPick.TradeSource = "SleeperDraftPick"
        }
    }
    elseif ((ConvertTo-DraftSafeArray -value $targetPick.TradeHistory).Count -eq 0) {
        $targetPick.WasTraded = $false
        $targetPick.TradeSource = $null
    }
}

function Get-AppliedDraftPickResults {
    param(
        [Parameter(Mandatory = $true)][array]$picks,
        [Parameter(Mandatory = $true)][object]$sleeperDraft,
        [AllowNull()]$sleeperPicks = $null
    )

    $draftID = Get-DraftObjectProperty -object $sleeperDraft -propertyName "draft_id" -defaultValue $null
    if ([string]::IsNullOrWhiteSpace($draftID)) { return $picks }

    if ($null -eq $sleeperPicks) { $sleeperPicks = Get-DraftHistorySleeperPicks -sleeperDraft $sleeperDraft }
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
        if ($null -eq $pickNo -or [string]::IsNullOrWhiteSpace([string]$pickNo)) { continue }

        $overallPick = [int]$pickNo
        if (-not $pickByOverall.ContainsKey($overallPick)) {
            Write-Warning "Could not map Sleeper pick_no '$overallPick' from draft '$draftID' to generated draft picks."
            continue
        }

        $targetPick = $pickByOverall[$overallPick]
        $targetPick.SleeperPickNo = $overallPick
        $targetPick.SleeperPickedBy = [string](Get-DraftObjectProperty -object $sleeperPick -propertyName "picked_by" -defaultValue $null)

        Set-DraftHistoryPickOwnerFromSleeperPick -targetPick $targetPick -sleeperPick $sleeperPick

        if ($null -ne $playerID -and -not [string]::IsNullOrWhiteSpace([string]$playerID)) {
            $targetPick.PlayerID = [string]$playerID
            $targetPick.PlayerName = Get-DraftHistoryPlayerNameFromSleeperPick -sleeperPick $sleeperPick
            $targetPick.Status = "Picked"
        }
    }

    return $picks
}
