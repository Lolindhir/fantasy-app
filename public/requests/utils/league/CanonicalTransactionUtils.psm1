# ===========================================================================
# Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\..\ConfigUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\general\ArrayUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\DraftUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\TransactionUtils.psm1" -ErrorAction Stop -Force
}
catch {
    Write-Error "Fehler beim Laden der Module: $_"
    throw $_
}

# ===========================================================================
# Canonical transaction consumer
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

function Get-CanonicalTransactionsForSeasonInMemory {
    param(
        [string]$CanonicalLeagueID = "nfl-reise",
        [Parameter(Mandatory = $true)][string]$Season
    )

    Write-Host "Build season $Season transactions from canonical League source-data..." -ForegroundColor Yellow

    $canonicalTransactions = @(Invoke-TransactionCanonicalConsumer `
        -CanonicalLeagueID $CanonicalLeagueID `
        -Season $Season)
    $manualTransactions = @(ConvertTo-SafeArray -value (Get-ManualTransactions -season $Season))
    $transactions = @(Merge-CanonicalTransactionsWithManual `
        -canonicalTransactions $canonicalTransactions `
        -manualTransactions $manualTransactions `
        -season $Season)

    Write-Host "Canonical season $Season transaction candidate built in memory." -ForegroundColor DarkCyan
    return $transactions
}

function Get-CanonicalTransactionsCurrentSeasonInMemory {
    param(
        [string]$CanonicalLeagueID = "nfl-reise"
    )

    $season = [string](Get-Config).LeagueYear
    return @(Get-CanonicalTransactionsForSeasonInMemory `
        -CanonicalLeagueID $CanonicalLeagueID `
        -Season $season)
}

function Get-CanonicalHistoricalTransactionSeasons {
    param(
        [string]$CanonicalLeagueID = "nfl-reise"
    )

    $repoRoot = Get-TransactionCanonicalRepoRoot
    $seasonsRoot = Join-Path $repoRoot "source-data\leagues\$CanonicalLeagueID\seasons"
    if (-not (Test-Path $seasonsRoot)) {
        throw "Canonical League season directory missing at '$seasonsRoot'."
    }

    $currentSeason = [int](Get-Config).LeagueYear
    $seasons = @()

    foreach ($directory in (Get-ChildItem -Path $seasonsRoot -Directory)) {
        $seasonNumber = 0
        if (-not [int]::TryParse([string]$directory.Name, [ref]$seasonNumber)) { continue }
        if ($seasonNumber -ge $currentSeason) { continue }

        $rostersFile = Join-Path $directory.FullName "rosters.json"
        $transactionsDirectory = Join-Path $directory.FullName "transactions"
        if (-not (Test-Path $rostersFile) -or -not (Test-Path $transactionsDirectory)) {
            throw "Canonical historical transaction source is incomplete for $CanonicalLeagueID/$seasonNumber."
        }

        $seasons += [string]$seasonNumber
    }

    return @($seasons | Sort-Object { [int]$_ })
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
# Canonical historical transaction consumer
# ===========================================================================

function Update-TransactionsHistoricalSeasonsFromCanonical {
    param(
        [string]$CanonicalLeagueID = "nfl-reise",
        [switch]$ForceHistory
    )

    Write-Host "Update historical transactions from canonical League source-data..." -ForegroundColor Yellow
    $seasons = @(Get-CanonicalHistoricalTransactionSeasons -CanonicalLeagueID $CanonicalLeagueID)

    if ($seasons.Count -eq 0) {
        Write-Host "No canonical historical transaction seasons found." -ForegroundColor DarkGray
        return
    }

    foreach ($season in $seasons) {
        $historicalFile = Get-TransactionsHistoricalFilePath -season $season
        if ((Test-Path $historicalFile) -and -not $ForceHistory) {
            Write-Host "Historical transactions for season $season already exist. Skipping." -ForegroundColor DarkGray
            continue
        }

        Write-Host "Building historical transactions for season $season from canonical source-data..." -ForegroundColor Yellow
        $transactions = @(Get-CanonicalTransactionsForSeasonInMemory `
            -CanonicalLeagueID $CanonicalLeagueID `
            -Season $season)
        Save-TransactionsHistoricalSeason `
            -season $season `
            -transactions $transactions `
            -Force:$ForceHistory
    }

    Write-Host "Canonical historical transaction rebuild finished." -ForegroundColor DarkCyan
}

function Update-TransactionsAllSeasonsCanonical {
    param(
        [string]$CanonicalLeagueID = "nfl-reise",
        [switch]$ForceHistory
    )

    Write-Host "Update current and historical transactions from canonical League source-data..." -ForegroundColor Yellow
    Update-TransactionsCurrentSeasonFromCanonical -CanonicalLeagueID $CanonicalLeagueID | Out-Null
    Update-TransactionsHistoricalSeasonsFromCanonical `
        -CanonicalLeagueID $CanonicalLeagueID `
        -ForceHistory:$ForceHistory
    Write-Host "Canonical all-season transaction rebuild finished." -ForegroundColor DarkCyan
}

Export-ModuleMember -Function @(
    "Get-CanonicalTransactionsForSeasonInMemory",
    "Get-CanonicalTransactionsCurrentSeasonInMemory",
    "Get-CanonicalHistoricalTransactionSeasons",
    "Merge-CanonicalTransactionsWithManual",
    "Update-TransactionsCurrentSeasonFromCanonical",
    "Update-TransactionsHistoricalSeasonsFromCanonical",
    "Update-TransactionsAllSeasonsCanonical"
)
