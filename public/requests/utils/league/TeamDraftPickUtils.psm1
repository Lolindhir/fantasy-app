# ===========================================================================
# Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\..\ConfigUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\general\ArrayUtils.psm1" -ErrorAction Stop -Force
}
catch {
    Write-Error "Fehler beim Laden der Module: $_"
    throw $_
}

# ===========================================================================
# Helpers
# ===========================================================================

function Get-LeagueDraftsLocal {
    $config = Get-Config

    if (-not (Test-Path $config.DraftsFile)) {
        Write-Warning "Drafts file not found at $($config.DraftsFile). Returning empty draft list."
        return @()
    }

    try {
        $raw = Get-Content $config.DraftsFile -Raw

        if ([string]::IsNullOrWhiteSpace($raw)) {
            return @()
        }

        return ConvertTo-SafeArray -value ($raw | ConvertFrom-Json)
    }
    catch {
        Write-Warning "Could not read Drafts.json at $($config.DraftsFile). $_"
        return @()
    }
}

function Add-DraftPickKeysToTeams {
    param(
        [Parameter(Mandatory = $true)]
        [array]$teams,

        [Parameter(Mandatory = $true)]
        [array]$drafts
    )

    $pickRefsByTeamID = @{}

    foreach ($team in $teams) {
        if ($null -eq $team.TeamID) { continue }

        $teamID = [int]$team.TeamID
        $pickRefsByTeamID[$teamID] = @()
    }

    foreach ($draft in (ConvertTo-SafeArray -value $drafts)) {
        $draftNo = if ($null -ne $draft.DraftNo) { [int]$draft.DraftNo } else { 999 }
        $seasonSort = if ([string]$draft.Season -match '^\d+$') { [int]$draft.Season } else { 9999 }

        foreach ($pick in (ConvertTo-SafeArray -value $draft.Picks)) {
            if ([string]::IsNullOrWhiteSpace([string]$pick.PickKey)) { continue }
            if ($null -eq $pick.CurrentOwnerRosterID) { continue }

            $currentOwnerRosterID = [int]$pick.CurrentOwnerRosterID

            if (-not $pickRefsByTeamID.ContainsKey($currentOwnerRosterID)) {
                continue
            }

            $overallPickSort = 999999
            if ($null -ne $pick.OverallPick -and -not [string]::IsNullOrWhiteSpace([string]$pick.OverallPick)) {
                $overallPickSort = [int]$pick.OverallPick
            }

            $positionSort = 999999
            if ($null -ne $pick.PositionInRound -and -not [string]::IsNullOrWhiteSpace([string]$pick.PositionInRound)) {
                $positionSort = [int]$pick.PositionInRound
            }

            $pickRefsByTeamID[$currentOwnerRosterID] += [PSCustomObject]@{
                PickKey               = [string]$pick.PickKey
                SeasonSort            = $seasonSort
                DraftNo               = $draftNo
                Round                 = [int]$pick.Round
                OverallPickSort       = $overallPickSort
                PositionSort          = $positionSort
                OriginalOwnerRosterID = [int]$pick.OriginalOwnerRosterID
            }
        }
    }

    foreach ($team in $teams) {
        if ($null -eq $team.TeamID) {
            $team | Add-Member -NotePropertyName DraftPicks -NotePropertyValue @() -Force
            continue
        }

        $teamID = [int]$team.TeamID

        $pickKeys = @(
            $pickRefsByTeamID[$teamID] |
                Sort-Object `
                    SeasonSort,
                    DraftNo,
                    Round,
                    OverallPickSort,
                    PositionSort,
                    OriginalOwnerRosterID |
                ForEach-Object { $_.PickKey }
        )

        $team | Add-Member -NotePropertyName DraftPicks -NotePropertyValue @($pickKeys) -Force
    }

    return $teams
}