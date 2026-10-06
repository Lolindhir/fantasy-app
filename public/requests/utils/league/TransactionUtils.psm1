# ===========================================================================
# Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\..\ConfigUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\general\FileUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\general\ArrayUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\general\ObjectUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\general\DateTimeUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\general\ProviderJoinUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\league\LeagueUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\league\TeamUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\league\DraftUtils.psm1" -ErrorAction Stop -Force
}
catch {
    Write-Error "Fehler beim Laden der Module: $_"
    throw $_
}

# ===========================================================================
# Identity invariants
# ===========================================================================

function Test-TransactionIdentityInvariants {
    param(
        [Parameter(Mandatory = $true)]
        [AllowNull()]
        [AllowEmptyCollection()]
        [array]$Transactions,

        [string]$SourceLabel = "generated transactions"
    )

    New-UniqueObjectLookup `
        -Items @(ConvertTo-SafeArray -value $Transactions) `
        -KeyProperty "TransactionID" `
        -SourceLabel $SourceLabel `
        -KeyLabel "TransactionID" `
        -DescriptionProperties @("TransactionID", "Source", "Season", "Week", "CreatedDate") | Out-Null

    return $true
}

function New-ManualTransactionBindingLookup {
    param(
        [Parameter(Mandatory = $true)]
        [AllowNull()]
        [AllowEmptyCollection()]
        [array]$ManualTransactions,

        [string]$SourceLabel = "manual transaction Sleeper bindings"
    )

    return New-UniqueObjectLookup `
        -Items @(ConvertTo-SafeArray -value $ManualTransactions) `
        -KeyProperty "SleeperTransactionID" `
        -SourceLabel $SourceLabel `
        -KeyLabel "SleeperTransactionID" `
        -DescriptionProperties @("SleeperTransactionID", "Season", "Week", "Date") `
        -AllowMissingKey
}

function New-SleeperTransactionWeekLookup {
    param(
        [Parameter(Mandatory = $true)]
        [AllowNull()]
        [AllowEmptyCollection()]
        [array]$Transactions,

        [Parameter(Mandatory = $true)]
        [string]$SourceLabel
    )

    return New-UniqueObjectLookup `
        -Items @(ConvertTo-SafeArray -value $Transactions) `
        -KeyProperty "transaction_id" `
        -SourceLabel $SourceLabel `
        -KeyLabel "transaction_id" `
        -DescriptionProperties @("transaction_id", "type", "status", "leg", "created")
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

function ConvertTo-ComparableJson {
    param(
        [AllowNull()]
        $value
    )

    if ($null -eq $value) {
        return $null
    }

    return ($value | ConvertTo-Json -Depth 20 -Compress)
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

    $oldTransactions = @(ConvertTo-SafeArray -value $oldTransactions)
    $newTransactions = @(ConvertTo-SafeArray -value $newTransactions)

    if ($oldTransactions.Count -eq 0 -and $newTransactions.Count -eq 0) {
        return $false
    }

    $oldByID = New-UniqueObjectLookup `
        -Items $oldTransactions `
        -KeyProperty "TransactionID" `
        -SourceLabel "existing transaction read model" `
        -KeyLabel "TransactionID" `
        -DescriptionProperties @("TransactionID", "Source", "Season", "Week", "CreatedDate")

    $newByID = New-UniqueObjectLookup `
        -Items $newTransactions `
        -KeyProperty "TransactionID" `
        -SourceLabel "new transaction read model" `
        -KeyLabel "TransactionID" `
        -DescriptionProperties @("TransactionID", "Source", "Season", "Week", "CreatedDate")

    if ($oldTransactions.Count -ne $newTransactions.Count) {
        Write-Host "Transactions count changed: $($oldTransactions.Count) -> $($newTransactions.Count)"
        return $true
    }

    foreach ($oldID in $oldByID.Keys) {
        if (-not $newByID.ContainsKey($oldID)) {
            Write-Host "Transaction removed: '$oldID'"
            return $true
        }
    }

    foreach ($newID in $newByID.Keys) {
        if (-not $oldByID.ContainsKey($newID)) {
            Write-Host "Transaction added: '$newID'"
            return $true
        }
    }

    foreach ($id in $oldByID.Keys) {
        $oldTransaction = $oldByID[$id]
        $newTransaction = $newByID[$id]

        foreach ($prop in $propertiesToCheck) {
            $oldValue = ConvertTo-ComparableJson -value $oldTransaction.$prop
            $newValue = ConvertTo-ComparableJson -value $newTransaction.$prop

            if ($oldValue -ne $newValue) {
                Write-Host "Transaction '$id' property '$prop' changed."
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
        'Season',
        'Week',
        #'Creator',
        'CreatedAt',
        'CreatedDate',
        #'UpdatedAt',
        'RosterIDs',
        'Adds',
        'Drops',
        'DraftPicks',
        'Notes'
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
        [object]$sleeperTransaction = $null,

        [object]$manualTransaction = $null,

        [Parameter(Mandatory = $true)]
        [string]$season
    )

    $week = 0
    if ($sleeperTransaction.leg){
        $week = [int]$sleeperTransaction.leg
    } elseif ($manualTransaction.Week) {
        $week = [int]$manualTransaction.Week
    }

    $source = "None"
    if ($sleeperTransaction -and $manualTransaction) {
        $source = "Sleeper_Manual"
    } elseif ($sleeperTransaction) {
        $source = "Sleeper"
    } elseif ($manualTransaction) {
        $source = "Manual"
    }

    $transactionID = $null
    if ($sleeperTransaction.transaction_id) {
        $transactionID = [string]$sleeperTransaction.transaction_id
    } elseif ($manualTransaction) {
        $transactionID = Get-ManualTransactionID -manualTransaction $manualTransaction
    }

    $type = "unknown"
    if ($sleeperTransaction.type) {
        $type = [string]$sleeperTransaction.type
    } elseif ($manualTransaction) {
        $type = "trade"
    }

    $status = "unknown"
    if ($sleeperTransaction.status) {
        $status = [string]$sleeperTransaction.status
    } elseif ($manualTransaction) {
        $status = "complete"
    }

    $createdAt = 0
    if ($sleeperTransaction.created) {
        $createdAt = [Int64]$sleeperTransaction.created
    } elseif ($manualTransaction.Date) {
        $createdAt = ConvertTo-UnixMillisecondsFromDateString -date $manualTransaction.Date
    }

    $notes = $null
    if ($sleeperTransaction.metadata -and $sleeperTransaction.metadata.notes) {
        $notes = $sleeperTransaction.metadata.notes
    }

    $adds = @{}
    if ($sleeperTransaction.adds) {
        $adds = ConvertTo-SafeObject -value $sleeperTransaction.adds
    }

    $drops = @{}
    if ($sleeperTransaction.drops) {
        $drops = ConvertTo-SafeObject -value $sleeperTransaction.drops
    }

    $draftPicks = @()
    if ($sleeperTransaction.draft_picks) {
        foreach ($pick in $sleeperTransaction.draft_picks) {
            $draftPicks += Get-DraftPickOutputFromSleeper -sleeperPick $pick
        }
    }
    if ($manualTransaction.Picks) {
        foreach ($pick in $manualTransaction.Picks) {
            $draftPicks += Get-DraftPickOutputFromManual -manualPick $pick
        }
    }
    $draftPicks = @(
        $draftPicks |
            Sort-Object Season, Round, OriginalOwnerRosterID, PreviousOwnerRosterID, NewOwnerRosterID
    )

    $rosterIDs = @()
    $rosterIDs += Get-RosterIDsFromPlayerMap -map $adds
    $rosterIDs += Get-RosterIDsFromPlayerMap -map $drops
    $rosterIDs += ($draftPicks | ForEach-Object { $_.PreviousOwnerRosterID })
    $rosterIDs += ($draftPicks | ForEach-Object { $_.NewOwnerRosterID })
    $rosterIDs = @(
        $rosterIDs |
            Where-Object { $null -ne $_ -and $_ -ne "" } |
            ForEach-Object { [int]$_ } |
            Sort-Object -Unique
    )

    return [PSCustomObject][ordered]@{
        Source        = $source
        TransactionID = $transactionID
        Type          = $type
        Status        = $status
        Season        = $season
        Week          = $week
        CreatedAt     = $createdAt
        CreatedDate   = ConvertFrom-UnixMillisecondsToDateString -timestamp $createdAt
        RosterIDs     = @($rosterIDs)
        Adds          = $adds
        Drops         = $drops
        DraftPicks    = $draftPicks
        Notes         = $notes
    }
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

    return [PSCustomObject][ordered]@{
        LeagueID     = $leagueID
        Season       = $season
        SeasonStatus = $seasonStatus
        UpdatedAt    = (Get-Date).ToString("o")
        Transactions = $transactions
    }
}

function Get-RosterIDsFromPlayerMap {
    param(
        [object]$map
    )

    if ($null -eq $map) {
        return @()
    }

    if ($map -is [System.Collections.IDictionary]) {
        return @($map.Values)
    }

    return @(
        $map.PSObject.Properties |
            Where-Object { $_.MemberType -eq "NoteProperty" } |
            ForEach-Object { $_.Value }
    )
}

# ===========================================================================
# Manual Transaction Utility Functions
# ===========================================================================

function Get-ManualTransactionID {
    param(
        [Parameter(Mandatory = $true)]
        [object]$manualTransaction
    )

    $pickKey = @(
        ConvertTo-SafeArray -value $manualTransaction.Picks | ForEach-Object {
            "$($_.Season)-R$($_.Round)-O$(Get-OwnerIDByName -ownerName $_.Original)-F$(Get-OwnerIDByName -ownerName $_.From)-T$(Get-OwnerIDByName -ownerName $_.To)"
        }
    ) -join "|"

    $raw = "$($manualTransaction.Season)|$($manualTransaction.Date)|$pickKey"

    $bytes = [System.Text.Encoding]::UTF8.GetBytes($raw)
    $sha1 = [System.Security.Cryptography.SHA1]::Create()

    try {
        $hash = ([BitConverter]::ToString($sha1.ComputeHash($bytes))).Replace("-", "").Substring(0, 12)
    }
    finally {
        $sha1.Dispose()
    }

    return "Manual_$($manualTransaction.Season)_$hash"
}

# ===========================================================================
# Manual Transaction Integration Functions
# ===========================================================================

function Get-ManualTransactions {
    param(
        [AllowNull()]
        [string]$season = $null
    )

    $filePath = (Get-Config).ManualTransactionsFile

    if (-not (Test-Path $filePath)) {
        Write-Host "Manual transactions file not found at $filePath." -ForegroundColor Red
        return @()
    }

    try {
        $data = Get-Content $filePath -Raw | ConvertFrom-Json
        $transactions = ConvertTo-SafeArray -value $data

        if (-not [string]::IsNullOrWhiteSpace($season)) {
            $transactions = @(
                $transactions | Where-Object {
                    [string]$_.Season -eq [string]$season
                }
            )
        }

        return $transactions
    }
    catch {
        throw "Could not read or validate manual transactions file at $filePath. $_"
    }
}

# ===========================================================================
# Update Utils
# ===========================================================================

# ===========================================================================
# Save Utils
# ===========================================================================

function Save-TransactionsCurrentSeason {
    param (
        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [array]$transactions
    )

    Write-Host "Saving current season transactions data to JSON..." -ForegroundColor Yellow
    Test-TransactionIdentityInvariants -Transactions $transactions -SourceLabel "current generated transactions" | Out-Null

    $compare = ${function:Compare-Transactions}
    Save-JsonFile -Type "Transactions" -Data $transactions -CompareScript $compare -CreateBackup -UpdateTimestamp

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
    Test-TransactionIdentityInvariants -Transactions $transactions -SourceLabel "historical generated transactions for season $season" | Out-Null

    if ($Force) {
        Save-JsonFile -TargetFile $filePath -Data $transactions
    }
    else {
        $compare = ${function:Compare-Transactions}
        Save-JsonFile -TargetFile $filePath -Data $transactions -CompareScript $compare
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

    return Get-SortedTransactions -transactions $transactions
}

function Get-TransactionsLocalForCurrentSeason {
    $filePath = (Get-Config).TransactionsFile

    if (-not (Test-Path $filePath)) {
        Write-Warning "Transactions file not found at $filePath. Returning empty array."
        return @()
    }

    try {
        $data = Get-Content $filePath -Raw | ConvertFrom-Json
        $transactions = ConvertTo-SafeArray -value $data
        Test-TransactionIdentityInvariants -Transactions $transactions -SourceLabel "existing current Transactions.json" | Out-Null
        return $transactions
    }
    catch {
        throw "Could not read or validate existing Transactions.json at '$filePath'. $_"
    }
}

function Get-TransactionsLocalHistoricalSeasons {
    $cfg = Get-Config
    $folder = Get-TransactionsHistoricalFolder
    $filePrefix = Split-Path $cfg.TransactionsFileHistoricalPrefix -Leaf
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
            $fileTransactions = ConvertTo-SafeArray -value $data
            Test-TransactionIdentityInvariants -Transactions $fileTransactions -SourceLabel "historical transaction file '$($_.Name)'" | Out-Null
            $transactions += $fileTransactions
        }
        catch {
            throw "Could not read or validate historical transactions file '$($_.FullName)'. $_"
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
    return "$($cfg.TransactionsFileHistoricalPrefix)$season$($cfg.TransactionsFileHistoricalSuffix)"
}

function Get-TransactionsHistoricalFolder {
    $cfg = Get-Config
    return $cfg.TransactionsArchiveDir
}

# ===========================================================================
# Remote Utils
# ===========================================================================

# ===========================================================================
# Helper für Wochenlogik
# ===========================================================================

# ===========================================================================
# Allgemeine Helper
# ===========================================================================

function Get-SortedTransactions {
    param(
        [AllowNull()]
        [array]$transactions
    )

    return @(
        ConvertTo-SafeArray -value $transactions |
            Sort-Object Season, Week, CreatedAt, TransactionID -Descending
    )
}
