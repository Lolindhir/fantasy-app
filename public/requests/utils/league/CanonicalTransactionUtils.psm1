# ===========================================================================
# Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\..\ConfigUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\general\ArrayUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\DraftUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\LeagueUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\TransactionUtils.psm1" -ErrorAction Stop -Force
}
catch {
    Write-Error "Fehler beim Laden der Module: $_"
    throw $_
}

# ===========================================================================
# Canonical current-season consumer
# ===========================================================================

function Get-TransactionCanonicalRepoRoot {
    return (Resolve-Path (Join-Path $PSScriptRoot "../../../..")).Path
}

function Get-TransactionPythonCommand {
    foreach ($name in @("python3", "python")) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($command) { return $command.Source }
    }

    throw "Python is required for the canonical transaction consumer."
}

function Invoke-TransactionCanonicalConsumer {
    param(
        [Parameter(Mandatory = $true)][string]$CanonicalLeagueID,
        [Parameter(Mandatory = $true)][string]$Season
    )

    $repoRoot = Get-TransactionCanonicalRepoRoot
    $toolPath = Join-Path $repoRoot "tools/transaction_canonical_consumer.py"
    if (-not (Test-Path $toolPath)) {
        throw "Canonical transaction consumer tool missing at '$toolPath'."
    }

    $python = Get-TransactionPythonCommand
    $output = & $python $toolPath `
        --repo-root $repoRoot `
        --canonical-league-id $CanonicalLeagueID `
        --season $Season 2>&1
    $exitCode = $LASTEXITCODE
    $outputText = (@($output) | ForEach-Object { [string]$_ }) -join [Environment]::NewLine

    if ($exitCode -ne 0) {
        throw "Canonical transaction consumer failed with exit code $exitCode. $outputText"
    }

    try {
        $transactions = $outputText | ConvertFrom-Json
    }
    catch {
        throw "Canonical transaction consumer returned invalid JSON. $_"
    }

    $transactions = @(ConvertTo-SafeArray -value $transactions)
    Test-TransactionIdentityInvariants `
        -Transactions $transactions `
        -SourceLabel "canonical-adapted transactions for $CanonicalLeagueID/$Season" | Out-Null
    return $transactions
}

function Merge-CanonicalTransactionsWithManual {
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [array]$canonicalTransactions,

        [Parameter(Mandatory = $true)]
        [AllowNull()]
        [AllowEmptyCollection()]
        [array]$manualTransactions,

        [Parameter(Mandatory = $true)]
        [string]$season
    )

    $canonicalTransactions = @(ConvertTo-SafeArray -value $canonicalTransactions)
    $manualTransactions = @(
        ConvertTo-SafeArray -value $manualTransactions |
            Where-Object { [string]$_.Season -eq [string]$season }
    )

    $manualBySleeperTransactionID = New-ManualTransactionBindingLookup `
        -ManualTransactions $manualTransactions `
        -SourceLabel "manual canonical transaction bindings for season $season"

    $canonicalIDs = New-Object 'System.Collections.Generic.HashSet[string]'
    foreach ($transaction in $canonicalTransactions) {
        [void]$canonicalIDs.Add([string]$transaction.TransactionID)
    }

    foreach ($manualTransaction in $manualTransactions) {
        $boundID = [string]$manualTransaction.SleeperTransactionID
        if ([string]::IsNullOrWhiteSpace($boundID)) { continue }
        if (-not $canonicalIDs.Contains($boundID)) {
            throw "Manual transaction binding '$boundID' for season $season has no canonical transaction."
        }
    }

    $result = @()
    foreach ($transaction in $canonicalTransactions) {
        $transactionID = [string]$transaction.TransactionID
        if ($manualBySleeperTransactionID.ContainsKey($transactionID)) {
            $manualTransaction = $manualBySleeperTransactionID[$transactionID]
            $transaction.Source = "Sleeper_Manual"

            $draftPicks = @(ConvertTo-SafeArray -value $transaction.DraftPicks)
            foreach ($manualPick in @(ConvertTo-SafeArray -value $manualTransaction.Picks)) {
                $draftPicks += Get-DraftPickOutputFromManual -manualPick $manualPick
            }
            $transaction.DraftPicks = @(
                $draftPicks |
                    Sort-Object Season, Round, OriginalOwnerRosterID, PreviousOwnerRosterID, NewOwnerRosterID
            )

            $rosterIDs = @()
            $rosterIDs += Get-RosterIDsFromPlayerMap -map $transaction.Adds
            $rosterIDs += Get-RosterIDsFromPlayerMap -map $transaction.Drops
            $rosterIDs += ($transaction.DraftPicks | ForEach-Object { $_.PreviousOwnerRosterID })
            $rosterIDs += ($transaction.DraftPicks | ForEach-Object { $_.NewOwnerRosterID })
            $transaction.RosterIDs = @(
                $rosterIDs |
                    Where-Object { $null -ne $_ -and "$_" -ne "" } |
                    ForEach-Object { [int]$_ } |
                    Sort-Object -Unique
            )
        }

        $result += $transaction
    }

    foreach ($manualTransaction in $manualTransactions) {
        $boundID = [string]$manualTransaction.SleeperTransactionID
        if (-not [string]::IsNullOrWhiteSpace($boundID)) { continue }
        $result += Get-TransactionOutput -manualTransaction $manualTransaction -season $season
    }

    $result = @(Get-SortedTransactions -transactions $result)
    Test-TransactionIdentityInvariants `
        -Transactions $result `
        -SourceLabel "canonical plus manual transactions for season $season" | Out-Null
    return $result
}

function Get-CanonicalTransactionsCurrentSeasonInMemory {
    param(
        [string]$CanonicalLeagueID = "nfl-reise"
    )

    $config = Get-Config
    $season = [string]$config.LeagueYear
    Write-Host "Build current season transactions from canonical League source-data..." -ForegroundColor Yellow

    $canonicalTransactions = @(Invoke-TransactionCanonicalConsumer `
        -CanonicalLeagueID $CanonicalLeagueID `
        -Season $season)
    $manualTransactions = @(ConvertTo-SafeArray -value (Get-ManualTransactions -season $season))
    $transactions = @(Merge-CanonicalTransactionsWithManual `
        -canonicalTransactions $canonicalTransactions `
        -manualTransactions $manualTransactions `
        -season $season)

    Write-Host "Canonical current season transaction candidate built in memory." -ForegroundColor DarkCyan
    return $transactions
}

function Update-TransactionsCurrentSeasonFromCanonical {
    param(
        [string]$CanonicalLeagueID = "nfl-reise"
    )

    $transactions = @(Get-CanonicalTransactionsCurrentSeasonInMemory `
        -CanonicalLeagueID $CanonicalLeagueID)
    Save-TransactionsCurrentSeason -transactions $transactions
    return $transactions
}

# ===========================================================================
# Transitional historical compatibility path
# ===========================================================================

function Update-TransactionsHistoricalSeasonsLegacy {
    param(
        [string]$leagueID = (Get-Config).LeagueID,
        [switch]$ForceHistory
    )

    Write-Host "Update historical transactions from the legacy Sleeper compatibility path..." -ForegroundColor Yellow
    $leagues = Get-LeaguesRecursive -leagueID $leagueID

    foreach ($league in $leagues) {
        $isCurrentLeague = ([string]$league.league_id -eq [string](Get-Config).LeagueID)
        if ($isCurrentLeague) { continue }

        $historicalFile = Get-TransactionsHistoricalFilePath -season $league.season
        if ((Test-Path $historicalFile) -and -not $ForceHistory) {
            Write-Host "Historical transactions for season $($league.season) already exist. Skipping." -ForegroundColor DarkGray
            continue
        }

        Write-Host "Fetching historical transactions for season $($league.season)..." -ForegroundColor Yellow
        if ($ForceHistory) {
            $transactions = Get-TransactionsRemoteForSeason `
                -leagueID $league.league_id `
                -league $league `
                -Force
            Save-TransactionsHistoricalSeason `
                -season $league.season `
                -transactions $transactions `
                -Force
        }
        else {
            $transactions = Get-TransactionsRemoteForSeason `
                -leagueID $league.league_id `
                -league $league
            Save-TransactionsHistoricalSeason `
                -season $league.season `
                -transactions $transactions
        }
    }

    Write-Host "Historical transaction compatibility rebuild finished." -ForegroundColor DarkCyan
}

function Update-TransactionsAllSeasonsCanonicalCurrent {
    param(
        [string]$leagueID = (Get-Config).LeagueID,
        [string]$CanonicalLeagueID = "nfl-reise",
        [switch]$ForceHistory
    )

    Write-Host "Update transactions with canonical current-season ownership..." -ForegroundColor Yellow
    Update-TransactionsCurrentSeasonFromCanonical -CanonicalLeagueID $CanonicalLeagueID | Out-Null
    Update-TransactionsHistoricalSeasonsLegacy -leagueID $leagueID -ForceHistory:$ForceHistory
    Write-Host "Canonical-current transaction rebuild finished." -ForegroundColor DarkCyan
}

Export-ModuleMember -Function @(
    "Get-CanonicalTransactionsCurrentSeasonInMemory",
    "Merge-CanonicalTransactionsWithManual",
    "Update-TransactionsCurrentSeasonFromCanonical",
    "Update-TransactionsHistoricalSeasonsLegacy",
    "Update-TransactionsAllSeasonsCanonicalCurrent"
)
