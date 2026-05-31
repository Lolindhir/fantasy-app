
# ===========================================================================
# Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\..\ConfigUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\general\FileUtils.psm1" -ErrorAction Stop -Force
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
# Save Utils
# ===========================================================================

function Save-TransactionsCurrentSeason {
    param (
        [array]$transactions
    )

    # --- JSON schreiben ---
    Write-Host "Saving transactions data to JSON..." -ForegroundColor Yellow
    $compare = & Compare-Transactions
    Save-JsonFile -Type "Transactions" -Data $transactions -CompareScript $compare -CreateBackup -UpdateTimestamp

    Write-Host "Saved current season transactions." -ForegroundColor Green
}

function Save-TransactionsHistoricalSeason {
    param (
        [int]$season,
        [array]$transactions
    )

    $cfg = Get-Config

    $filePath = "$($cfg.TransactionsFileHistorical)$season$($cfg.TransactionsFileHistoricalSuffix)"

    # --- JSON schreiben ---
    Write-Host "Saving historical transactions for $season data to JSON..." -ForegroundColor Yellow
    $compare = & Compare-Transactions
    Save-JsonFile -TargetFile $filePath -Data $transactions -CompareScript $compare

    Write-Host "Saved historical transactions for $season" -ForegroundColor DarkCyan
}

# ===========================================================================
# Getter Utils
# ===========================================================================

function Get-Transactions {
    param(
        [ValidateSet("Local","Remote")]
        [string]$Source = "Local",

        [switch]$IncludeHistory
    )

    if ($Source -eq "Remote") {
        return Get-TransactionsRemote -IncludeHistory:$IncludeHistory
    }

    return Get-TransactionsLocal -IncludeHistory:$IncludeHistory
}

function Get-TransactionsLocal {
    param(
        [switch]$IncludeHistory
    )

    $transactions = @()

    # Current Season
    $transactions += Get-TransactionsLocalForSeason -Season (Get-Config).LeagueYear

    if ($IncludeHistory) {

        $folder = Join-Path (Get-Config).DataDir "past_seasons\Transactions"

        Get-ChildItem $folder -Filter "*.json" | ForEach-Object {
            $transactions += Get-Content $_.FullName -Raw | ConvertFrom-Json
        }
    }

    return $transactions
}

function Get-TransactionsRemote {
    param(
        [switch]$IncludeHistory
    )

    $transactions = @()

    if ($IncludeHistory) {

        $allSeasons = Get-TransactionsRecursive

        foreach ($season in $allSeasons.AllSeasons) {
            $transactions += $season.Transactions
        }
    }
    else {

        $transactions += Get-TransactionsRemoteForSeason
    }

    return $transactions
}

function Get-AllTransactions {
    param (
        [switch]$IncludeHistory = $false
    )

    $all = @()

    # 1. Current Season (immer)
    $current = Get-TransactionsLocalForCurrentSeason
    $all += $current

    # 2. Optional History
    if ($IncludeHistory) {

        $cfg = Get-Config

        # naive approach: alle files im folder
        $files = Get-ChildItem "$($cfg.DataDir)\past_seasons\Transactions" -Filter "*.json"

        foreach ($file in $files) {
            Write-Host "Loading history: $($file.Name)" -ForegroundColor DarkGray

            $data = Get-Content $file.FullName -Raw | ConvertFrom-Json
            $all += $data
        }
    }

    # Sortierung = Timeline Engine
    return $all | Sort-Object CreatedAt
}

function Get-TransactionsForSeason {
    param (
        [int]$season
    )

    if ($season -eq (Get-Config).LeagueYear) {
        return Get-TransactionsLocalForCurrentSeason
    }

    return Get-TransactionsHistoricalSeason -season $season
}

function Get-TransactionsRecursive {
    param(
        [string]$leagueID = (Get-Config).LeagueID,
        [switch]$OnlyCompletedSeasons,
        $accumulatedData = $null
    )

    # Initialisierung nur beim ersten Aufruf
    if (-not $accumulatedData) {
        $accumulatedData = @{}
    }

    $league = Get-LeagueRaw -leagueID $leagueID

    # Rekursiv weitere Seasons holen, falls vorhanden (Abbruch, wenn keine PreviousLeagueID mehr vorhanden ist)
    if ($league.previous_league_id -and $league.previous_league_id -ne "") {
        $accumulatedData = Get-TransactionsRemoteRecursive -leagueID $league.previous_league_id -OnlyCompletedSeasons:$OnlyCompletedSeasons -accumulatedData $accumulatedData
    }

    #berechne Transactions
    $transactionsForSeason = Get-TransactionsRemoteForSeason -leagueID $leagueID -startWeek 1 -endWeek (Get-Config).MaxTransactionWeek
    
    $output = [PSCustomObject]@{
        LeagueID = $leagueID
        Season = $league.season
        SeasonStatus = $league.status
        Transactions = $transactionsForSeason
    }

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


function Get-TransactionsRemoteForSeason {
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
        $data = Get-Content $filePath -Raw | ConvertFrom-Json
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

function Get-TransactionsHistoricalSeason {
    param (
        [int]$season
    )

    $cfg = Get-Config

    $filePath = "$($cfg.TransactionsFileHistorical)$season$($cfg.TransactionsFileHistoricalSuffix)"

    if (-not (Test-Path $filePath)) {
        Write-Warning "No historical file for season $season"
        return @()
    }

    try {
        $data = Get-Content $filePath -Raw | ConvertFrom-Json
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

