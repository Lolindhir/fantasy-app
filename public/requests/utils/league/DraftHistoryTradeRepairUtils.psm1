# ===========================================================================
# Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\..\ConfigUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\general\FileUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\league\DraftUtils.psm1" -ErrorAction Stop -Force
}
catch {
    Write-Error "Fehler beim Laden der Module: $_"
    throw $_
}

# ===========================================================================
# Historical Draft Trade Repair
# ===========================================================================

function Get-HistoricalDraftTradeJsonContent {
    param(
        [Parameter(Mandatory = $true)]
        [string]$filePath,

        [Parameter(Mandatory = $true)]
        [string]$description
    )

    if (-not (Test-Path $filePath)) {
        Write-Warning "$description file not found at $filePath. Returning empty array."
        return @()
    }

    try {
        $raw = Get-Content $filePath -Raw
        if ([string]::IsNullOrWhiteSpace($raw)) { return @() }
        return $raw | ConvertFrom-Json
    }
    catch {
        Write-Warning "Could not read $description file at $filePath. $_"
        return @()
    }
}

function Get-HistoricalDraftTradeTransactions {
    $config = Get-Config
    $transactions = @()

    $transactions += ConvertTo-DraftSafeArray -value (
        Get-HistoricalDraftTradeJsonContent -filePath $config.TransactionsFile -description "Transactions"
    )

    $folder = $config.TransactionsArchiveDir
    $filePrefix = Split-Path $config.TransactionsFileHistoricalPrefix -Leaf
    $filter = "$filePrefix*$($config.TransactionsFileHistoricalSuffix)"

    if (Test-Path $folder) {
        Get-ChildItem $folder -Filter $filter | ForEach-Object {
            $transactions += ConvertTo-DraftSafeArray -value (
                Get-HistoricalDraftTradeJsonContent -filePath $_.FullName -description "Historical transactions"
            )
        }
    }

    return @($transactions | Sort-Object CreatedAt, TransactionID)
}

function Test-HistoricalDraftTradeMovementMatchesDraft {
    param(
        [Parameter(Mandatory = $true)]
        [object]$draftPick,

        [Parameter(Mandatory = $true)]
        [object]$draft
    )

    $draftKey = [string]$draft.DraftKey
    $draftSeason = [string]$draft.Season
    $draftType = [string]$draft.DraftType
    $movementDraftKey = [string]$draftPick.DraftKey
    $movementSeason = [string]$draftPick.Season
    $movementDraftType = [string]$draftPick.DraftType
    $movementDraftSource = [string]$draftPick.DraftSource

    if ($movementDraftKey -eq $draftKey) { return $true }
    if ($movementDraftKey -eq "$($draftSeason)_$($draftType)") { return $true }
    if ($movementSeason -eq $draftSeason -and $movementDraftType -eq $draftType) { return $true }

    # Sleeper exposes startup / free-agent draft pick movements as generic Rookie
    # draft picks. For the first historical startup/free-agent draft, match by
    # season, round and original owner instead of the generated draft type key.
    if ($draftType -eq "Free_Agent" -and $movementDraftSource -eq "Sleeper" -and $movementSeason -eq $draftSeason) {
        return $true
    }

    return $false
}

function Get-HistoricalDraftTradeMovementsForDraft {
    param(
        [Parameter(Mandatory = $true)]
        [object]$draft,

        [Parameter(Mandatory = $true)]
        [array]$transactions
    )

    $movements = @()

    foreach ($transaction in $transactions) {
        if ([string]$transaction.Status -ne "complete") { continue }

        foreach ($draftPick in (ConvertTo-DraftSafeArray -value $transaction.DraftPicks)) {
            if (-not (Test-HistoricalDraftTradeMovementMatchesDraft -draftPick $draftPick -draft $draft)) { continue }

            $movements += [PSCustomObject][ordered]@{
                TransactionID         = [string]$transaction.TransactionID
                Source                = [string]$transaction.Source
                CreatedAt             = [Int64]$transaction.CreatedAt
                CreatedDate           = [string]$transaction.CreatedDate
                DraftSource           = [string]$draftPick.DraftSource
                DraftKey              = [string]$draftPick.DraftKey
                Season                = [string]$draftPick.Season
                Round                 = [int]$draftPick.Round
                OriginalOwnerRosterID = [int]$draftPick.OriginalOwnerRosterID
                PreviousOwnerRosterID = [int]$draftPick.PreviousOwnerRosterID
                NewOwnerRosterID      = [int]$draftPick.NewOwnerRosterID
            }
        }
    }

    return @($movements | Sort-Object CreatedAt, TransactionID)
}

function Repair-HistoricalDraftTradeOwnershipForDraft {
    param(
        [Parameter(Mandatory = $true)]
        [object]$draft,

        [Parameter(Mandatory = $true)]
        [array]$transactions
    )

    $picks = ConvertTo-DraftSafeArray -value $draft.Picks
    if ($picks.Count -eq 0) { return $draft }

    foreach ($pick in $picks) {
        $pick.CurrentOwnerRosterID = [int]$pick.OriginalOwnerRosterID
        $pick.WasTraded = $false
        $pick.IsCurrentlyTraded = $false
        $pick.TradeSource = $null
        $pick.TradeHistory = @()
    }

    $pickByKey = @{}
    foreach ($pick in $picks) {
        $pickKey = New-DraftPickKey `
            -draftKey ([string]$draft.DraftKey) `
            -round ([int]$pick.Round) `
            -originalOwnerRosterID ([int]$pick.OriginalOwnerRosterID)
        $pickByKey[$pickKey] = $pick
    }

    $movements = Get-HistoricalDraftTradeMovementsForDraft -draft $draft -transactions $transactions

    foreach ($movement in $movements) {
        $targetPickKey = New-DraftPickKey `
            -draftKey ([string]$draft.DraftKey) `
            -round ([int]$movement.Round) `
            -originalOwnerRosterID ([int]$movement.OriginalOwnerRosterID)

        if (-not $pickByKey.ContainsKey($targetPickKey)) { continue }

        $targetPick = $pickByKey[$targetPickKey]
        $targetPick.CurrentOwnerRosterID = [int]$movement.NewOwnerRosterID
        $targetPick.WasTraded = $true
        $targetPick.IsCurrentlyTraded = ([int]$targetPick.CurrentOwnerRosterID -ne [int]$targetPick.OriginalOwnerRosterID)
        $targetPick.TradeSource = [string]$movement.Source
        $targetPick.TradeHistory = @($targetPick.TradeHistory) + [PSCustomObject][ordered]@{
            TransactionID         = $movement.TransactionID
            Source                = $movement.Source
            CreatedAt             = $movement.CreatedAt
            CreatedDate           = $movement.CreatedDate
            DraftSource           = $movement.DraftSource
            PreviousOwnerRosterID = $movement.PreviousOwnerRosterID
            NewOwnerRosterID      = $movement.NewOwnerRosterID
        }
    }

    foreach ($pick in $picks) {
        $pick.IsCurrentlyTraded = ([int]$pick.CurrentOwnerRosterID -ne [int]$pick.OriginalOwnerRosterID)
    }

    $draft.Picks = @($picks)
    return $draft
}

function Repair-DraftsHistoricalTradeOwnership {
    $config = Get-Config
    $folder = $config.DraftsArchiveDir

    if (-not (Test-Path $folder)) {
        Write-Warning "Drafts historical folder not found at $folder. Skipping historical draft trade repair."
        return
    }

    $transactions = Get-HistoricalDraftTradeTransactions
    $filePrefix = Split-Path $config.DraftsFileHistoricalPrefix -Leaf
    $filter = "$filePrefix*$($config.DraftsFileHistoricalSuffix)"

    Get-ChildItem $folder -Filter $filter | ForEach-Object {
        $filePath = $_.FullName
        $draftData = Get-HistoricalDraftTradeJsonContent -filePath $filePath -description "Historical drafts"
        $drafts = ConvertTo-DraftSafeArray -value $draftData

        if ($drafts.Count -eq 0) { return }

        $repairedDrafts = @()
        foreach ($draft in $drafts) {
            $repairedDrafts += Repair-HistoricalDraftTradeOwnershipForDraft -draft $draft -transactions $transactions
        }

        $compare = ${function:Compare-Drafts}
        Save-JsonFile -TargetFile $filePath -Data $repairedDrafts -CompareScript $compare
    }
}
