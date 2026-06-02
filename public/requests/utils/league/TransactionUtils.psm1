# ===========================================================================
# Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\..\ConfigUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\general\FileUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\general\ArrayUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\general\ObjectUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\league\LeagueUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\league\DraftUtils.psm1" -ErrorAction Stop -Force
}
catch {
    Write-Error "Fehler beim Laden der Module: $_"
    throw $_
}

# ===========================================================================
# Compare Utils
# ===========================================================================

function Compare-TransactionSeasonData {
    param(
        [Parameter(Mandatory = $true)]
        [AllowNull()]
        $oldData,

        [Parameter(Mandatory = $true)]
        [AllowNull()]
        $newData
    )

    if (-not $oldData -and -not $newData) {
        return $false
    }

    if (($oldData -and -not $newData) -or (-not $oldData -and $newData)) {
        Write-Host "Transaction season data presence changed."
        return $true
    }

    $oldTransactions = Get-TransactionsFromSeasonData -seasonData $oldData
    $newTransactions = Get-TransactionsFromSeasonData -seasonData $newData

    if ($oldData.LeagueID -ne $newData.LeagueID) {
        Write-Host "Transaction LeagueID changed: '$($oldData.LeagueID)' -> '$($newData.LeagueID)'"
        return $true
    }

    if ($oldData.Season -ne $newData.Season) {
        Write-Host "Transaction Season changed: '$($oldData.Season)' -> '$($newData.Season)'"
        return $true
    }

    if ($oldData.SeasonStatus -ne $newData.SeasonStatus) {
        Write-Host "Transaction SeasonStatus changed: '$($oldData.SeasonStatus)' -> '$($newData.SeasonStatus)'"
        return $true
    }

    return Compare-Transactions `
        -oldTransactions $oldTransactions `
        -newTransactions $newTransactions
}

function Compare-Transactions {
    param(
        [Parameter(Mandatory = $true)]
        [AllowNull()]
        [AllowEmptyCollection()]
        [array]$oldTransactions,

        [Parameter(Mandatory = $true)]
        [AllowNull()]
        [AllowEmptyCollection()]
        [array]$newTransactions,

        [array]$propertiesToCheck = (Get-TransactionProperties)
    )

    if (-not $oldTransactions -and -not $newTransactions) {
        return $false
    }

    if (($oldTransactions -and -not $newTransactions) -or (-not $oldTransactions -and $newTransactions)) {
        if ($oldTransactions) {
            $oldStatus = "Present"
        }
        else {
            $oldStatus = "Not Present"
        }

        if ($newTransactions) {
            $newStatus = "Present"
        }
        else {
            $newStatus = "Not Present"
        }

        Write-Host "Transactions presence changed: $oldStatus -> $newStatus"
        return $true
    }

    if ($oldTransactions.Count -ne $newTransactions.Count) {
        Write-Host "Transactions count changed: $($oldTransactions.Count) -> $($newTransactions.Count)"
        return $true
    }

    $oldSorted = $oldTransactions | Sort-Object TransactionID
    $newSorted = $newTransactions | Sort-Object TransactionID

    for ($i = 0; $i -lt $oldSorted.Count; $i++) {
        $oldTransaction = $oldSorted[$i]
        $newTransaction = $newSorted[$i]

        foreach ($prop in $propertiesToCheck) {
            if ($oldTransaction.$prop -ne $newTransaction.$prop) {
                Write-Host "Transaction '$($oldTransaction.TransactionID)' property '$prop' changed: '$($oldTransaction.$prop)' -> '$($newTransaction.$prop)'"
                return $true
            }
        }
    }

    return $false
}

function Get-TransactionProperties {
    return @(
        'TransactionID',
        'Source',
        'Type',
        'Status',
        'LeagueID',
        'Season',
        'Week',
        'Creator',
        'CreatedAt',
        'UpdatedAt'
    )
}

function Get-TransactionsFromSeasonData {
    param(
        [AllowNull()]
        $seasonData
    )

    if (-not $seasonData) {
        return @()
    }

    if ($seasonData.PSObject.Properties.Name -contains "Transactions") {
        return ConvertTo-SafeArray -value $seasonData.Transactions
    }

    return ConvertTo-SafeArray -value $seasonData
}

# ===========================================================================
# Build Utils
# ===========================================================================

function Get-TransactionOutput {
    param(
        [Parameter(Mandatory = $true)]
        [object]$sleeperTransaction,

        [Parameter(Mandatory = $true)]
        [string]$leagueID,

        [Parameter(Mandatory = $true)]
        [string]$season,

        [Parameter(Mandatory = $true)]
        [int]$week,

        [object]$customTransaction = $null
    )

    $createdAt = 0
    if ($sleeperTransaction.created) {
        $createdAt = [Int64]$sleeperTransaction.created
    }

    $updatedAt = $createdAt
    if ($sleeperTransaction.status_updated) {
        $updatedAt = [Int64]$sleeperTransaction.status_updated
    }

    $transactionWeek = $week
    if ($sleeperTransaction.leg) {
        $transactionWeek = [int]$sleeperTransaction.leg
    }

    $notes = $null
    if ($sleeperTransaction.metadata -and $sleeperTransaction.metadata.notes) {
        $notes = $sleeperTransaction.metadata.notes
    }

    $output = [PSCustomObject][ordered]@{
        TransactionID = $sleeperTransaction.transaction_id
        Source        = "Sleeper"

        Type          = $sleeperTransaction.type
        Status        = $sleeperTransaction.status

        LeagueID      = $leagueID
        Season        = $season
        Week          = $transactionWeek

        Creator       = $sleeperTransaction.creator
        CreatedAt     = $createdAt
        UpdatedAt     = $updatedAt

        RosterIDs     = @(ConvertTo-SafeArray -value $sleeperTransaction.roster_ids)
        #ConsenterIDs  = ConvertTo-SafeArray -value $sleeperTransaction.consenter_ids

        Adds          = ConvertTo-SafeObject -value $sleeperTransaction.adds
        Drops         = ConvertTo-SafeObject -value $sleeperTransaction.drops
        DraftPicks    = @(Get-DraftPickOutputsFromSleeperTransaction -sleeperTransaction $sleeperTransaction)
        #WaiverBudget  = ConvertTo-SafeArray -value $sleeperTransaction.waiver_budget

        #Settings      = $sleeperTransaction.settings
        #Metadata      = $sleeperTransaction.metadata
        Notes         = $notes

        #SleeperData   = $sleeperTransaction
        #CustomData    = $customTransaction
    }

    return $output
}

function Get-TransactionsSeasonOutput {
    param(
        [Parameter(Mandatory = $true)]
        [string]$leagueID,

        [Parameter(Mandatory = $true)]
        [string]$season,

        [Parameter(Mandatory = $true)]
        [AllowNull()]
        [string]$seasonStatus,

        [Parameter(Mandatory = $true)]
        [array]$transactions
    )

    $output = [PSCustomObject][ordered]@{
        LeagueID     = $leagueID
        Season       = $season
        SeasonStatus = $seasonStatus
        UpdatedAt    = (Get-Date).ToString("o")
        Transactions = $transactions
    }

    return $output
}


# ===========================================================================
# Update Utils
# ===========================================================================

function Update-TransactionsCurrentSeason {
    param(
        [string]$leagueID = (Get-Config).LeagueID,
        [switch]$Force
    )

    Write-Host "Update transactions for current season..." -ForegroundColor Yellow

    $league = Get-SleeperLeague -leagueID $leagueID
    $season = $league.season

    $maxWeekToFetch = Get-CurrentTransactionMaxWeek -league $league

    if ($Force) {
        Write-Host "Force enabled: rebuilding current season transactions from remote only." -ForegroundColor Cyan

        $weeksToFetch = @(1..$maxWeekToFetch)

        $remoteTransactions = @(
            Get-TransactionsRemoteForWeeks `
                -leagueID $leagueID `
                -season $season `
                -weeks $weeksToFetch
        )

        Save-TransactionsCurrentSeason `
            -transactions $remoteTransactions `
            -Force

        Write-Host "Current season transactions rebuilt." -ForegroundColor DarkCyan

        return $remoteTransactions
    }

    # Normaler inkrementeller Modus
    $existingTransactions = Get-TransactionsLocalForCurrentSeason

    $weeksToFetch = Get-WeeksToFetch `
        -existingTransactions $existingTransactions `
        -maxWeek $maxWeekToFetch

    if (-not $weeksToFetch -or $weeksToFetch.Count -eq 0) {
        Write-Host "No transaction weeks need to be updated." -ForegroundColor DarkCyan
        return $existingTransactions
    }

    Write-Host "Weeks to fetch: $($weeksToFetch -join ', ')" -ForegroundColor Yellow

    $remoteTransactions = Get-TransactionsRemoteForWeeks `
        -leagueID $leagueID `
        -season $season `
        -weeks $weeksToFetch

    $mergedTransactions = Merge-TransactionsForWeeks `
        -existingTransactions $existingTransactions `
        -newTransactions $remoteTransactions `
        -weeksToReplace $weeksToFetch

    Save-TransactionsCurrentSeason -transactions $mergedTransactions

    Write-Host "Current season transactions updated." -ForegroundColor DarkCyan

    return $mergedTransactions
}

function Update-TransactionsAllSeasons {
    param(
        [string]$leagueID = (Get-Config).LeagueID,
        [switch]$ForceCurrent,
        [switch]$ForceHistory
    )

    Write-Host "Update transactions for all seasons..." -ForegroundColor Yellow

    $leagues = Get-LeaguesRecursive -leagueID $leagueID

    foreach ($league in $leagues) {

        $isCurrentLeague = ([string]$league.league_id -eq [string](Get-Config).LeagueID)

        if ($isCurrentLeague) {
            
            if ($ForceCurrent) {
                Update-TransactionsCurrentSeason `
                    -leagueID $league.league_id `
                    -Force
            }
            else {
                Update-TransactionsCurrentSeason `
                    -leagueID $league.league_id
            }

            continue
        }

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
        }
        else {
            $transactions = Get-TransactionsRemoteForSeason `
                -leagueID $league.league_id `
                -league $league
        }

        if ($ForceHistory) {
            Save-TransactionsHistoricalSeason `
                -season $league.season `
                -transactions $transactions `
                -Force
        }
        else {
            Save-TransactionsHistoricalSeason `
                -season $league.season `
                -transactions $transactions
        }
    }

    Write-Host "All season transactions updated." -ForegroundColor DarkCyan
}

# ===========================================================================
# Save Utils
# ===========================================================================

function Save-TransactionsCurrentSeason {
    param (
        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [array]$transactions,

        [switch]$Force
    )

    Write-Host "Saving current season transactions data to JSON..." -ForegroundColor Yellow

    if ($Force) {
        Save-JsonFile `
            -Type "Transactions" `
            -Data $transactions `
            -CreateBackup `
            -UpdateTimestamp
    }
    else {
        $compare = ${function:Compare-Transactions}

        Save-JsonFile `
            -Type "Transactions" `
            -Data $transactions `
            -CompareScript $compare `
            -CreateBackup `
            -UpdateTimestamp
    }

    Write-Host "Saved current season transactions." -ForegroundColor DarkCyan
}

function Save-TransactionsHistoricalSeason {
    param (
        [Parameter(Mandatory = $true)]
        [string]$season,

        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [array]$transactions,

        [switch]$Force
    )

    $cfg = Get-Config
    $filePath = "$($cfg.TransactionsFileHistoricalPrefix)$season$($cfg.TransactionsFileHistoricalSuffix)"

    Write-Host "Saving historical transactions for $season to JSON..." -ForegroundColor Yellow

    if ($Force) {
        Save-JsonFile `
            -TargetFile $filePath `
            -Data $transactions
    }
    else {
        $compare = ${function:Compare-Transactions}

        Save-JsonFile `
            -TargetFile $filePath `
            -Data $transactions `
            -CompareScript $compare
    }

    Write-Host "Saved historical transactions for $season." -ForegroundColor DarkCyan
}

# ===========================================================================
# Getter Utils
# ===========================================================================

function Get-Transactions {
    param(
        [switch]$IncludeHistory
    )

    Write-Host "Load transactions from local files..." -ForegroundColor Yellow

    $transactions = @()

    $current = Get-TransactionsLocalForCurrentSeason
    $transactions += ConvertTo-SafeArray -value $current

    if ($IncludeHistory) {
        $historical = Get-TransactionsLocalHistoricalSeasons
        $transactions += ConvertTo-SafeArray -value $historical
    }

    return $transactions | Sort-Object Season, Week, CreatedAt, TransactionID
}

function Get-TransactionsLocalForCurrentSeason {
    $filePath = (Get-Config).TransactionsFile

    if (-not (Test-Path $filePath)) {
        Write-Warning "Transactions file not found at $filePath. Returning empty array."
        return @()
    }

    try {
        $data = Get-Content $filePath -Raw | ConvertFrom-Json
        return ConvertTo-SafeArray -value $data
    }
    catch {
        Write-Warning "Could not read existing Transactions.json: $_"
        return @()
    }
}

function Get-TransactionsLocalHistoricalSeasons {

    $cfg = Get-Config

    $folder = Get-TransactionsHistoricalFolder
    $filePrefix = Split-Path $cfg.TransactionsFileHistorical -Leaf
    $filter = "$filePrefix*$($cfg.TransactionsFileHistoricalSuffix)"

    if (-not (Test-Path $folder)) {
        Write-Warning "Transactions historical folder not found at $folder. Returning empty array."
        return @()
    }

    $transactions = @()

    Get-ChildItem $folder -Filter $filter | ForEach-Object {
        try {
            Write-Host "Loading historical transactions: $($_.Name)" -ForegroundColor DarkGray

            $data = Get-Content $_.FullName -Raw | ConvertFrom-Json
            $transactions += ConvertTo-SafeArray -value $data
        }
        catch {
            Write-Warning "Could not read historical transactions file $($_.FullName): $_"
        }
    }

    return $transactions
}

function Get-TransactionsHistoricalFilePath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$season
    )

    $cfg = Get-Config

    return "$($cfg.TransactionsFileHistorical)$season$($cfg.TransactionsFileHistoricalSuffix)"
}

function Get-TransactionsHistoricalFolder {
    $cfg = Get-Config
    return Split-Path $cfg.TransactionsFileHistorical -Parent
}

# ===========================================================================
# Remote Utils
# ===========================================================================

function Get-TransactionsRemoteRecursive {
    param(
        [string]$leagueID = (Get-Config).LeagueID,
        [array]$accumulatedData = @()
    )

    try {
        $league = Get-SleeperLeague -leagueID $leagueID

        if ($league.previous_league_id -and $league.previous_league_id -ne "") {
            $accumulatedData = Get-TransactionsRemoteRecursive `
                -leagueID $league.previous_league_id `
                -accumulatedData $accumulatedData
        }

        $seasonData = Get-TransactionsRemoteForSeason `
            -leagueID $leagueID `
            -league $league

        $accumulatedData += $seasonData

        return $accumulatedData
    }
    catch {
        Write-Error "Failed to recursively retrieve transactions for league $leagueID."
        throw $_
    }
}

function Get-TransactionsRemoteForSeason {
    param (
        [string]$leagueID = (Get-Config).LeagueID,

        [object]$league = $null,

        [int]$startWeek = 1,

        [int]$endWeek = (Get-Config).MaxTransactionWeek,

        [switch]$Force
    )

    try {
        if (-not $league) {
            $league = Get-SleeperLeague -leagueID $leagueID
        }

        $maxWeekToFetch = if ($Force) {
            $endWeek
        }
        else {
            Get-CurrentTransactionMaxWeek -league $league
        }

        $weeks = @($startWeek..$maxWeekToFetch)

        return Get-TransactionsRemoteForWeeks `
            -leagueID $leagueID `
            -season $league.season `
            -weeks $weeks
    }
    catch {
        Write-Error "Failed to retrieve transactions for league $leagueID."
        throw $_
    }
}

function Get-TransactionsRemoteForWeeks {
    param (
        [Parameter(Mandatory = $true)]
        [string]$leagueID,

        [Parameter(Mandatory = $true)]
        [string]$season,

        [Parameter(Mandatory = $true)]
        [array]$weeks
    )

    $transactions = @()

    Write-Host "Get Transactions for League $leagueID / Season $season from Sleeper API..." -ForegroundColor Yellow

    foreach ($week in $weeks) {

        Write-Host "Get Transactions for Week $week" -ForegroundColor Yellow

        $weekTransactions = Get-SleeperTransactions -leagueID $leagueID -week $week
        $weekTransactions = ConvertTo-SafeArray -value $weekTransactions

        foreach ($tx in $weekTransactions) {
            $transactions += Get-TransactionOutput `
                -sleeperTransaction $tx `
                -leagueID $leagueID `
                -season $season `
                -week $week
        }
    }

    Write-Host "Transactions retrieved." -ForegroundColor Yellow

    return $transactions
}

# ===========================================================================
# Helper für Wochenlogik
# ===========================================================================

function Get-CurrentTransactionMaxWeek {
    param(
        [Parameter(Mandatory = $true)]
        [object]$league
    )

    $cfg = Get-Config

    if ($league.status -eq "complete") {
        return [int]$cfg.MaxTransactionWeek
    }

    $week = 1

    if ($league.settings -and $league.settings.leg) {
        $week = [int]$league.settings.leg
    }
    elseif ($league.settings -and $league.settings.last_scored_leg) {
        $week = [int]$league.settings.last_scored_leg + 1
    }

    if ($week -lt 1) {
        $week = 1
    }

    if ($week -gt [int]$cfg.MaxTransactionWeek) {
        $week = [int]$cfg.MaxTransactionWeek
    }

    return $week
}

function Get-WeeksToFetch {
    param(
        [AllowNull()]
        [array]$existingTransactions,

        [Parameter(Mandatory = $true)]
        [int]$maxWeek,

        [switch]$Force
    )

    if ($Force) {
        return @((1..$maxWeek))
    }

    $existingTransactions = ConvertTo-SafeArray -value $existingTransactions

    $existingWeeks = @(
        $existingTransactions |
            Where-Object { $_.Week } |
            Select-Object -ExpandProperty Week -Unique
    )

    $weeksToFetch = @()

    for ($week = 1; $week -le $maxWeek; $week++) {

        $weekAlreadyExists = $existingWeeks -contains $week

        if (-not $weekAlreadyExists) {
            $weeksToFetch += $week
            continue
        }

        # Aktuelle Woche immer refreshen, weil dort noch neue Moves entstehen können.
        if ($week -eq $maxWeek) {
            $weeksToFetch += $week
        }
    }

    return $weeksToFetch
}

function Merge-TransactionsForWeeks {
    param(
        [AllowNull()]
        [array]$existingTransactions,

        [AllowNull()]
        [array]$newTransactions,

        [Parameter(Mandatory = $true)]
        [array]$weeksToReplace
    )

    $existingTransactions = ConvertTo-SafeArray -value $existingTransactions
    $newTransactions = ConvertTo-SafeArray -value $newTransactions

    $keptTransactions = $existingTransactions |
        Where-Object { $weeksToReplace -notcontains $_.Week }

    $merged = @()
    $merged += $keptTransactions
    $merged += $newTransactions

    return $merged |
        Sort-Object Season, Week, CreatedAt, TransactionID
}