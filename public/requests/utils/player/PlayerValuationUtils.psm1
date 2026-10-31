# Read-only PlayerValuation snapshot adapter for League.json Salary Cap (#919, #1238).
# Salary, SalaryProjected and SalaryRelevantTeamSize are derived by the Python
# player-valuation product; RequestLeague consumes its latest season snapshot.
# This module neither materializes a product nor computes valuation arithmetic.

Import-Module "$PSScriptRoot\..\ConfigUtils.psm1" -ErrorAction Stop

function Get-PlayerValuationRepoRoot {
    return [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\..\..\.."))
}

function Get-PlayerValuationSnapshotPath {
    param(
        [Parameter(Mandatory = $true)][string]$CanonicalLeagueID,
        [Parameter(Mandatory = $true)][int]$Season,
        [Parameter(Mandatory = $true)][int]$Week,
        [string]$RepoRoot = (Get-PlayerValuationRepoRoot)
    )

    $seasonDir = Join-Path (Join-Path (Join-Path (Get-DataDerivedRoot -RepoRoot $RepoRoot) "player-valuation") $CanonicalLeagueID) ([string]$Season)
    return Join-Path $seasonDir ("week-{0:00}.json" -f $Week)
}

# Reads one snapshot and fails closed when it is missing or does not match the requested identity.
function Read-PlayerValuationSnapshot {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$CanonicalLeagueID,
        [Parameter(Mandatory = $true)][int]$Season,
        [int]$Week = -1
    )

    if (-not (Test-Path $Path)) {
        throw "PlayerValuation snapshot missing at '$Path'."
    }
    $snapshot = Get-Content $Path -Raw | ConvertFrom-Json
    if ($snapshot.CanonicalLeagueID -ne $CanonicalLeagueID -or [int]$snapshot.Season -ne $Season) {
        throw "PlayerValuation snapshot '$Path' belongs to $($snapshot.CanonicalLeagueID) $($snapshot.Season), expected $CanonicalLeagueID $Season."
    }
    if ($Week -ge 0 -and [int]$snapshot.AsOfFinalScoredWeek -ne $Week) {
        throw "PlayerValuation snapshot '$Path' is as of week $($snapshot.AsOfFinalScoredWeek), expected week $Week."
    }
    return $snapshot
}

# Newest snapshot of the season (the one the last Players run published together with Players.json).
function Get-PlayerValuationLatestSnapshot {
    param(
        [Parameter(Mandatory = $true)][string]$CanonicalLeagueID,
        [Parameter(Mandatory = $true)][int]$Season,
        [string]$RepoRoot = (Get-PlayerValuationRepoRoot)
    )

    $seasonDir = Split-Path -Parent (Get-PlayerValuationSnapshotPath -CanonicalLeagueID $CanonicalLeagueID -Season $Season -Week 0 -RepoRoot $RepoRoot)
    $files = @(Get-ChildItem -Path $seasonDir -Filter "week-*.json" -File -ErrorAction SilentlyContinue | Sort-Object Name)
    if ($files.Count -eq 0) {
        throw "No PlayerValuation snapshot found in '$seasonDir'."
    }
    return Read-PlayerValuationSnapshot -Path $files[-1].FullName -CanonicalLeagueID $CanonicalLeagueID -Season $Season
}

Export-ModuleMember -Function Get-PlayerValuationLatestSnapshot
