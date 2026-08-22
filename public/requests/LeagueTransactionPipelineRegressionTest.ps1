$ErrorActionPreference = "Stop"

Import-Module "$PSScriptRoot\utils\league\TransactionUtils.psm1" -Force
Import-Module "$PSScriptRoot\utils\league\LeagueTransactionPipelineUtils.psm1" -Force

function Assert-True {
    param(
        [Parameter(Mandatory = $true)][bool]$Condition,
        [Parameter(Mandatory = $true)][string]$Message
    )

    if (-not $Condition) { throw $Message }
}

function Assert-Equal {
    param(
        [AllowNull()]$Actual,
        [AllowNull()]$Expected,
        [Parameter(Mandatory = $true)][string]$Message
    )

    if ($Actual -ne $Expected) {
        throw "$Message Expected '$Expected', got '$Actual'."
    }
}

function Get-OccurrenceCount {
    param(
        [Parameter(Mandatory = $true)][string]$Text,
        [Parameter(Mandatory = $true)][string]$Needle
    )

    return ([regex]::Matches($Text, [regex]::Escape($Needle))).Count
}

# RequestLeague must use the in-memory orchestration and persist current
# Transactions.json exactly once after both enrichment phases.
$requestLeague = Get-Content "$PSScriptRoot\RequestLeague.ps1" -Raw
Assert-Equal -Actual (Get-OccurrenceCount -Text $requestLeague -Needle "Save-TransactionsCurrentSeason -transactions `$transactionsCurrentSeason") -Expected 1 -Message "RequestLeague must have exactly one final Transactions persistence point."
Assert-Equal -Actual (Get-OccurrenceCount -Text $requestLeague -Needle "Update-TransactionsCurrentSeason") -Expected 0 -Message "RequestLeague still uses the persisting current-season transaction updater."
Assert-Equal -Actual (Get-OccurrenceCount -Text $requestLeague -Needle "Update-CurrentTransactionDraftPickTypesFromSleeper") -Expected 0 -Message "RequestLeague still uses the persisting draft-identity enrichment wrapper."
Assert-Equal -Actual (Get-OccurrenceCount -Text $requestLeague -Needle "Update-CurrentTransactionDraftPickDetails") -Expected 0 -Message "RequestLeague still uses the persisting pick-detail enrichment wrapper."
Assert-Equal -Actual (Get-OccurrenceCount -Text $requestLeague -Needle "Update-DraftsOrderAware") -Expected 0 -Message "RequestLeague still lets Drafts reload Transactions.json instead of using the same snapshot."
Assert-True -Condition $requestLeague.Contains("Get-LeagueTransactionsCurrentSeasonInMemory") -Message "RequestLeague does not build transactions in memory."
Assert-True -Condition $requestLeague.Contains("Resolve-LeagueTransactionDraftPickTypesInMemory") -Message "RequestLeague does not resolve draft identity in memory."
Assert-True -Condition $requestLeague.Contains("Update-LeagueDraftsOrderAwareFromTransactions") -Message "RequestLeague does not pass the in-memory transaction snapshot to draft generation."
Assert-True -Condition $requestLeague.Contains("Add-LeagueTransactionDraftPickDetailsInMemory") -Message "RequestLeague does not enrich transaction pick details in memory."

# The dedicated helper must never publish Transactions.json itself. Drafts may
# still be persisted by the draft step; only Transactions are delayed.
$pipeline = Get-Content "$PSScriptRoot\utils\league\LeagueTransactionPipelineUtils.psm1" -Raw
Assert-Equal -Actual (Get-OccurrenceCount -Text $pipeline -Needle "Save-TransactionsCurrentSeason") -Expected 0 -Message "League in-memory helper unexpectedly persists Transactions.json."
Assert-Equal -Actual (Get-OccurrenceCount -Text $pipeline -Needle "Save-TransactionDraftPickTransactions") -Expected 0 -Message "League in-memory helper unexpectedly persists enriched Transactions.json."

# Standalone/history requests intentionally retain their file-based contract.
$requestTransactions = Get-Content "$PSScriptRoot\RequestTransactions.ps1" -Raw
Assert-True -Condition $requestTransactions.Contains("Update-TransactionsAllSeasons -ForceCurrent -ForceHistory") -Message "Standalone transaction history rebuild contract changed."
Assert-True -Condition $requestTransactions.Contains("Update-AllTransactionDraftPickTypesFromSleeper") -Message "Standalone transaction draft-identity enrichment is missing."
Assert-True -Condition $requestTransactions.Contains("Update-AllTransactionDraftPickDetailsFromLocalDrafts") -Message "Standalone transaction pick-detail enrichment is missing."

$requestDrafts = Get-Content "$PSScriptRoot\RequestDrafts.ps1" -Raw
Assert-True -Condition $requestDrafts.Contains("Update-AllTransactionDraftPickTypesFromSleeper") -Message "Standalone draft request no longer prepares persisted transaction identities."
Assert-True -Condition $requestDrafts.Contains("Update-DraftsOrderAware") -Message "Standalone current draft generation contract changed."
Assert-True -Condition $requestDrafts.Contains("Update-DraftsHistoricalSeasonsSafeOrderAware") -Message "Historical draft generation contract changed."
Assert-True -Condition $requestDrafts.Contains("Update-AllTransactionDraftPickDetailsFromLocalDrafts") -Message "Standalone draft request no longer enriches persisted transaction details."

# Pure in-memory detail enrichment must yield the same canonical transaction
# shape that Compare-Transactions considers stable on the next no-op run.
$transaction = [PSCustomObject][ordered]@{
    Source        = "Sleeper"
    TransactionID = "pipeline-test"
    Type          = "trade"
    Status        = "complete"
    Season        = "2026"
    Week          = 1
    CreatedAt     = [Int64]1
    CreatedDate   = "2026-01-01"
    RosterIDs     = @(1, 2)
    Adds          = @{}
    Drops         = @{}
    DraftPicks    = @(
        [PSCustomObject][ordered]@{
            DraftType             = "Rookie"
            DraftInstance         = 1
            DraftCode             = "Rookie"
            DraftSource           = "Sleeper"
            DraftKey              = "2026_Rookie"
            Season                = "2026"
            Round                 = 1
            OriginalOwnerRosterID = 1
            PreviousOwnerRosterID = 1
            NewOwnerRosterID      = 2
            SleeperDraftID        = "draft-1"
        }
    )
    Notes         = $null
}
$draft = [PSCustomObject][ordered]@{
    DraftKey       = "2026_Rookie"
    Season         = "2026"
    DraftType      = "Rookie"
    DraftInstance  = 1
    DraftCode      = "Rookie"
    SleeperDraftID = "draft-1"
    Picks          = @(
        [PSCustomObject][ordered]@{
            PickKey               = "2026_Rookie_R1_OO1"
            Season                = "2026"
            DraftType             = "Rookie"
            DraftInstance         = 1
            DraftCode             = "Rookie"
            Round                 = 1
            OriginalOwnerRosterID = 1
            CurrentOwnerRosterID  = 2
            PositionInRound       = 3
            OverallPick           = 3
            DisplayPick           = "1.03"
            TradeHistory          = @(
                [PSCustomObject][ordered]@{
                    TransactionID         = "pipeline-test"
                    PreviousOwnerRosterID = 1
                    NewOwnerRosterID      = 2
                }
            )
            PlayerID              = "player-1"
            PlayerName            = "Test Player"
            Status                = "Picked"
            SleeperPickNo         = 3
        }
    )
}

$enriched = Add-LeagueTransactionDraftPickDetailsInMemory -transactions @($transaction) -drafts @($draft)
$pick = $enriched[0].DraftPicks[0]
Assert-Equal -Actual $pick.PickKey -Expected "2026_Rookie_R1_OO1" -Message "In-memory pick enrichment did not propagate PickKey."
Assert-Equal -Actual $pick.DisplayPick -Expected "1.03" -Message "In-memory pick enrichment did not propagate DisplayPick."
Assert-Equal -Actual $pick.PlayerID -Expected "player-1" -Message "In-memory pick enrichment did not propagate selected player."
Assert-Equal -Actual (Compare-Transactions -oldTransactions $enriched -newTransactions $enriched) -Expected $false -Message "A fully enriched no-op transaction snapshot is not semantically stable."

Write-Host "League transaction single-persist regression tests passed." -ForegroundColor Green
