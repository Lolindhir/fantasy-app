
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
# Compare Utils
# ===========================================================================

function Compare-Transactions{
    param(
        [Parameter(Mandatory=$true)]
        [AllowNull()]
        [AllowEmptyCollection()]
        [array]$oldTransactions,
        [Parameter(Mandatory=$true)]
        [AllowNull()]
        [AllowEmptyCollection()]
        [array]$newTransactions,
        [array]$propertiesToCheck = (Get-TransactionProperties)
    )

    # Wenn nur eine Seite Daten hat, dann Änderung
    if (($oldTransactions -and -not $newTransactions) -or (-not $oldTransactions -and $newTransactions)) {
        if ($oldTransactions) {
            $oldStatus = "Present"
        } else {
            $oldStatus = "Not Present"
        }
        if ($newTransactions) {
            $newStatus = "Present"
        } else {
            $newStatus = "Not Present"
        }
        Write-Host "Transactions presence changed: " $oldStatus " -> " $newStatus
        return $true
    }
    # Wenn beide Seiten Transactions haben, dann vergleichen
    if ($oldTransactions -and $newTransactions) {

        # Vergleiche Anzahl der Transaction-Platzierungen
        if ($oldTransactions.Count -ne $newTransactions.Count) {
            Write-Host "Transactions placements count changed: $($oldTransactions.Count) -> $($newTransactions.Count)"
            return $true
        }

        # Vergleiche jede Transaction
        for ($i = 0; $i -lt $oldTransactions.Count; $i++) {
            $oldTransaction = $oldTransactions[$i]
            $newTransaction = $newTransactions[$i]

            # Prüfe Top-Level Eigenschaften der Transaction
            $propsToCheck = $propertiesToCheck
            foreach ($prop in $propsToCheck) {
                if ($oldTransaction.$prop -ne $newTransaction.$prop) {
                    Write-Host "$($oldTransaction.$outputProperty)'s property '$prop' changed: '$($oldTransaction.$prop)' -> '$($newTransaction.$prop)'"
                    return $true
                }
            }
        }
    }

    return $false
}

function Get-TransactionProperties{
    return @('Type','TransactionID','Status','Creator','CreatedAt','UpdatedAt')
}


# ===========================================================================
# Build Utils
# ===========================================================================

function Get-TransactionOutput {
    param(
        [object]$sleeperTransaction,
        [object]$customTransaction
    )

    if($sleeperTransaction) {
        return $sleeperTransaction
    }
    else {
        $output = [PSCustomObject]@{
            TransactionID = $sleeperTransaction.transaction_id
            Type = $sleeperTransaction.type
            Status = $sleeperTransaction.status
            CreatedAt = [DateTime]::Parse($sleeperTransaction.created_at)
            UpdatedAt = [DateTime]::Parse($sleeperTransaction.updated_at)
            SleeperData = $sleeperTransaction
            CustomData = $customTransaction
        }
    }

    return $output
}

# ===========================================================================
# Getter Utils
# ===========================================================================

function Get-TransactionsRecursive {
    param(
        [string]$leagueID = (Get-Config).LeagueID,
        $accumulatedData = $null
    )

    # Initialisierung nur beim ersten Aufruf
    if (-not $accumulatedData) {
        $accumulatedData = [PSCustomObject]@{
            AllSeasonsCompleted = @()
            AllSeasons          = @()
            PreviousSeason      = $null
        }
    }

    $league = Get-LeagueRaw -leagueID $leagueID

    # Rekursiv weitere Seasons holen, falls vorhanden (Abbruch, wenn keine PreviousLeagueID mehr vorhanden ist)
    if ($league.previous_league_id -and $league.previous_league_id -ne "") {
        $accumulatedData = Get-TransactionsRemoteRecursive -leagueID $league.previous_league_id -accumulatedData $accumulatedData
    }

    #berechne Transactions
    $output = Get-TransactionsRemote -leagueID $leagueID -startWeek 1 -endWeek (Get-Config).MaxTransactionWeek
    
    #baue accumulatedData
    if($league.status -eq "complete"){
        $accumulatedData.AllSeasonsCompleted += $output
    }
    $accumulatedData.AllSeasons += $output
    $accumulatedData.PreviousSeason = $output

    return $accumulatedData
}

# ===========================================================================
# Remote Utils
# ===========================================================================


function Get-TransactionsRemote {
    param (
        [string]$leagueID = (Get-Config).LeagueID,
        [number]$startWeek = 1,
        [number]$endWeek = (Get-Config).MaxTransactionWeek
    )

    try {

        $transactions = @()

        Get-Host "Get Transactions for League $leagueID from Sleeper API..." -ForegroundColor Yellow

        # Hole Transaktionen für alle Wochen bis zur aktuellen Woche
        for ($week = $startWeek; $week -le $endWeek; $week++) {

            Write-Host "Get Transactions for Week $week" -ForegroundColor Yellow
            $weekTransactions = Get-SleeperTransactions -leagueID $leagueID -week $week
            $transactions += Get-TransactionOutput -sleeperTransaction $weekTransactions
        }
        Write-Host "Transactions retrieved." -ForegroundColor Yellow

        return $transactions
    }
    catch {
         throw $_
    }    
}


# ===========================================================================
# File Utils
# ===========================================================================


function Get-TransactionsLocalForCurrentSeason {

    $filePath = (Get-Config).TransactionsFile

     # Prüfe ob Datei existiert
     if (-not (Test-Path $filePath)) {
        Write-Warning "Transactions file not found at $filePath. Returning empty array."
        return @()
    }

    try {
        $data = Get-Content $FilePath -Raw | ConvertFrom-Json
        if ($data -is [array]) {
            return $data
        } else {
            return @($data)
        }
    }
    catch {
        Write-Warning "Could not read existing Transactions.json: $_"
        return @()
    }
}

