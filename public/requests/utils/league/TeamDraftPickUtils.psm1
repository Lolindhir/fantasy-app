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

# Shared Derived LeagueDrafts is the authoritative pick owner (ADR-057).
# Read only current-season and future product documents, never App Drafts.json.
# This adapter does not compute draft order, trades, owners or draft identities.
function Get-LeagueDraftsProduct {
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [Parameter(Mandatory = $true)][string]$CanonicalLeagueID,
        [Parameter(Mandatory = $true)][int]$LeagueYear
    )

    if ($CanonicalLeagueID -notmatch '^[A-Za-z0-9_-]+$') {
        throw "Invalid canonical league ID for LeagueDrafts: '$CanonicalLeagueID'."
    }

    $productRoot = Join-Path (Get-DataDerivedRoot -RepoRoot $RepoRoot) 'league-drafts'
    $leagueRoot = Join-Path $productRoot $CanonicalLeagueID
    if (-not (Test-Path -LiteralPath $leagueRoot -PathType Container)) {
        throw "LeagueDrafts product directory missing for '$CanonicalLeagueID'."
    }

    $files = @(Get-ChildItem -LiteralPath $leagueRoot -File -Filter '*.json' |
        Where-Object { $_.BaseName -match '^\d{4}$' -and [int]$_.BaseName -ge $LeagueYear } |
        Sort-Object { [int]$_.BaseName })

    if ($files.Count -eq 0 -or [int]$files[0].BaseName -ne $LeagueYear) {
        throw "LeagueDrafts product for current season $LeagueYear is missing."
    }

    $drafts = [System.Collections.Generic.List[object]]::new()
    $draftKeys = [System.Collections.Generic.HashSet[string]]::new()
    $pickKeys = [System.Collections.Generic.HashSet[string]]::new()
    $expectedSeason = $LeagueYear

    foreach ($file in $files) {
        $season = [int]$file.BaseName
        if ($season -ne $expectedSeason) {
            throw "LeagueDrafts has a gap before season $season (expected $expectedSeason)."
        }
        $expectedSeason++

        $product = Get-Content -LiteralPath $file.FullName -Raw -ErrorAction Stop |
            ConvertFrom-Json -ErrorAction Stop
        if ([int]$product.ContractVersion -ne 2 -or
            [string]$product.CanonicalLeagueID -cne $CanonicalLeagueID -or
            [int]$product.Season -ne $season) {
            throw "LeagueDrafts product identity/contract mismatch for season $season."
        }
        if ($null -eq $product.Drafts -or @($product.Drafts).Count -eq 0) {
            throw "LeagueDrafts product contains no drafts for season $season."
        }

        foreach ($draft in @($product.Drafts)) {
            $draftKey = [string]$draft.DraftKey
            if ([string]::IsNullOrWhiteSpace($draftKey) -or
                [int]$draft.Season -ne $season -or
                $null -eq $draft.DraftNo -or
                $null -eq $draft.Picks -or
                -not $draftKeys.Add($draftKey)) {
                throw "Invalid or duplicate LeagueDrafts identity in season $season."
            }
            foreach ($pick in @($draft.Picks)) {
                if ([string]::IsNullOrWhiteSpace([string]$pick.PickKey) -or
                    [string]$pick.DraftKey -cne $draftKey -or
                    $null -eq $pick.Round -or
                    $null -eq $pick.OriginalOwnerRosterID -or
                    $null -eq $pick.CurrentOwnerRosterID -or
                    -not $pickKeys.Add([string]$pick.PickKey)) {
                    throw "Invalid or duplicate LeagueDrafts pick in '$draftKey'."
                }
            }
            $drafts.Add($draft)
        }
    }

    if ($drafts.Count -eq 0) {
        throw "LeagueDrafts yielded no current/future drafts for '$CanonicalLeagueID'."
    }
    return $drafts.ToArray()
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