# PlayerValuation consumer adapter (Issue #919 step 5, ADR-055).
# Salary, SalaryProjected, Ranking, rank Grading and the Salary Cap are computed by the central models
# (tools/derived_data.py, product player-valuation under data-derived). This module runs the materializer and
# adapts the snapshot to the unchanged Players.json / League.json contracts. It does no valuation arithmetic.

Import-Module "$PSScriptRoot\..\ConfigUtils.psm1" -ErrorAction Stop

function Get-PlayerValuationRepoRoot {
    return [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\..\..\.."))
}

function Get-PlayerValuationPythonCommand {
    foreach ($name in @("python3", "python")) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($command) { return $command.Source }
    }

    throw "Python is required for the PlayerValuation materializer."
}

# Materializes every season and week of the league (semantic no-op when nothing changed).
# HoldSeedPlayersFile is the last published Players.json; it only seeds identity-hold rows that no snapshot knows.
function Invoke-PlayerValuationMaterialize {
    param(
        [string]$HoldSeedPlayersFile,
        [string]$RepoRoot = (Get-PlayerValuationRepoRoot)
    )

    $toolPath = Join-Path $RepoRoot "tools/derived_data.py"
    if (-not (Test-Path $toolPath)) {
        throw "PlayerValuation materializer missing at '$toolPath'."
    }

    $arguments = @("--repo-root", $RepoRoot, "materialize", "--product", "player-valuation")
    if ($HoldSeedPlayersFile -and (Test-Path $HoldSeedPlayersFile)) {
        $arguments += @("--hold-seed-players-file", $HoldSeedPlayersFile)
    }

    $python = Get-PlayerValuationPythonCommand
    $output = & $python $toolPath @arguments 2>&1
    $exitCode = $LASTEXITCODE
    $outputText = (@($output) | ForEach-Object { [string]$_ }) -join [Environment]::NewLine
    if ($exitCode -ne 0) {
        throw "PlayerValuation materialization failed with exit code $exitCode. $outputText"
    }
    Write-Host "PlayerValuation snapshots materialized." -ForegroundColor Yellow
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

# Snapshot of the given final scored week, rows indexed by Sleeper player ID.
function Get-PlayerValuationSnapshotForWeek {
    param(
        [Parameter(Mandatory = $true)][string]$CanonicalLeagueID,
        [Parameter(Mandatory = $true)][int]$Season,
        [Parameter(Mandatory = $true)][int]$Week,
        [string]$RepoRoot = (Get-PlayerValuationRepoRoot)
    )

    $path = Get-PlayerValuationSnapshotPath -CanonicalLeagueID $CanonicalLeagueID -Season $Season -Week $Week -RepoRoot $RepoRoot
    $snapshot = Read-PlayerValuationSnapshot -Path $path -CanonicalLeagueID $CanonicalLeagueID -Season $Season -Week $Week
    $rows = @{}
    foreach ($row in $snapshot.Players) {
        $id = [string]$row.PlayerID
        if ($rows.ContainsKey($id)) {
            throw "PlayerValuation snapshot '$path' lists Sleeper player $id twice."
        }
        $rows[$id] = $row
    }
    return [PSCustomObject]@{ Snapshot = $snapshot; Rows = $rows }
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

# Salary (double like the published contract), Ranking[] and the Rank grading row of one Players.json player.
function Get-PlayerValuationPlayerValues {
    param(
        [Parameter(Mandatory = $true)]$Row
    )

    if ($null -eq $Row.Salary -or $null -eq $Row.SalaryProjected) {
        throw "PlayerValuation row for Sleeper player $($Row.PlayerID) has no valuation (identity hold without held values)."
    }

    $ranking = @($Row.Ranking | ForEach-Object { [PSCustomObject]@{ Type = [string]$_.Type; Value = $_.Value } })
    $rank = @($Row.Grading | Where-Object { $_.Type -eq 'Rank' })
    if ($rank.Count -ne 1) {
        throw "PlayerValuation row for Sleeper player $($Row.PlayerID) has $($rank.Count) Rank grading rows."
    }

    return [PSCustomObject]@{
        Salary          = [double]$Row.Salary
        SalaryProjected = [double]$Row.SalaryProjected
        Ranking         = $ranking
        RankGrading     = [PSCustomObject]@{
            Type  = "Rank"
            Value = $rank[0].Value
            Rank  = $rank[0].Rank
            Grade = $rank[0].Grade
        }
    }
}

Export-ModuleMember -Function Invoke-PlayerValuationMaterialize, Get-PlayerValuationSnapshotForWeek, Get-PlayerValuationLatestSnapshot, Get-PlayerValuationPlayerValues
