$ErrorActionPreference = "Stop"

Import-Module "$PSScriptRoot\utils\league\DraftUtils.psm1" -Force
Import-Module "$PSScriptRoot\utils\league\DraftHistoryUtils.psm1" -Force
Import-Module "$PSScriptRoot\utils\league\DraftOrderAwareUtils.psm1" -Force
Import-Module "$PSScriptRoot\utils\league\TransactionDraftPickEnrichmentUtils.psm1" -Force
Import-Module "$PSScriptRoot\utils\league\HistoricalTransactionDraftPickIdentityUtils.psm1" -Force

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

function Assert-Before {
    param(
        [Parameter(Mandatory = $true)][string]$Text,
        [Parameter(Mandatory = $true)][string]$First,
        [Parameter(Mandatory = $true)][string]$Second,
        [Parameter(Mandatory = $true)][string]$Message
    )

    $firstIndex = $Text.IndexOf($First)
    $secondIndex = $Text.IndexOf($Second)
    if ($firstIndex -lt 0 -or $secondIndex -lt 0 -or $firstIndex -ge $secondIndex) {
        throw $Message
    }
}

# The transactions request must perform a true full rebuild and then rebuild
# dependent drafts before any final draft-result enrichment can read local drafts.
$requestTransactions = Get-Content "$PSScriptRoot\RequestTransactions.ps1" -Raw
Assert-True -Condition $requestTransactions.Contains("Update-TransactionsAllSeasons -ForceCurrent -ForceHistory") -Message "RequestTransactions no longer rebuilds current and historical transaction base data."
Assert-True -Condition $requestTransactions.Contains("Invoke-DraftTransactionRebuild -ForceHistory") -Message "RequestTransactions does not force the coupled historical draft rebuild."
Assert-True -Condition (-not $requestTransactions.Contains("Update-AllTransactionDraftPickDetailsFromLocalDrafts")) -Message "RequestTransactions still enriches directly from potentially stale local drafts."

# Both standalone requests must share one orchestration path so ordering cannot drift.
$requestDrafts = Get-Content "$PSScriptRoot\RequestDrafts.ps1" -Raw
Assert-True -Condition $requestDrafts.Contains("Invoke-DraftTransactionRebuild") -Message "RequestDrafts does not use the shared draft/transaction rebuild pipeline."
Assert-True -Condition (-not $requestDrafts.Contains("Update-DraftsHistoricalSeasonsSafeOrderAware")) -Message "RequestDrafts duplicates historical draft orchestration outside the shared pipeline."

$pipeline = Get-Content "$PSScriptRoot\utils\league\DraftTransactionPipelineUtils.psm1" -Raw
Assert-Before -Text $pipeline -First "Update-AllTransactionDraftPickTypesFromSleeper" -Second "Update-HistoricalTransactionDraftPickTypesFromCompletedDrafts" -Message "Historical identity correction must run after the general transaction identity pass."
Assert-Before -Text $pipeline -First "Update-HistoricalTransactionDraftPickTypesFromCompletedDrafts" -Second "Update-DraftsOrderAware" -Message "Historical transaction identity must match completed draft definitions before draft generation."
Assert-Before -Text $pipeline -First "Update-DraftsOrderAware" -Second "Update-DraftsHistoricalSeasonsSafeOrderAware" -Message "Current draft generation must complete before historical draft generation."
Assert-Before -Text $pipeline -First "Update-DraftsHistoricalSeasonsSafeOrderAware" -Second "Update-AllTransactionDraftPickDetailsFromLocalDrafts" -Message "Historical drafts must be rebuilt before transaction pick-detail enrichment."
Assert-True -Condition $pipeline.Contains("-ForceHistory:`$ForceHistory") -Message "ForceHistory is not forwarded to the historical draft rebuild."

# Canonical historical identity must be regenerated from the current contract,
# never by preserving or translating old D<n> generated keys.
Assert-Equal -Actual (New-DraftKey -season "2024" -draftType "Free_Agent" -draftInstance 1) -Expected "2024_Free_Agent" -Message "Historical Free Agent DraftKey is not canonical."
Assert-Equal -Actual (New-DraftKey -season "2025" -draftType "Rookie" -draftInstance 1) -Expected "2025_Rookie" -Message "Historical Rookie DraftKey is not canonical."
Assert-Equal -Actual (New-DraftCode -draftType "Free_Agent" -draftInstance 1) -Expected "Free_Agent" -Message "Historical DraftCode for instance 1 is not canonical."

# Production regression: the 2024 startup-style draft has far more rounds than
# the configured rookie/FA drafts and is classified by the historical generator
# as Free_Agent. Historical transaction identity must consume that same concrete
# definition before TradeHistory is generated.
$draftTypeConfigs = @(
    [PSCustomObject][ordered]@{
        DraftType     = "Rookie"
        DraftInstance = 1
        DraftNo       = 1
        Rounds        = 5
    },
    [PSCustomObject][ordered]@{
        DraftType     = "Free_Agent"
        DraftInstance = 1
        DraftNo       = 2
        Rounds        = 5
    }
)
$startupDraft = [PSCustomObject][ordered]@{
    draft_id = "startup-2024"
    season   = "2024"
    type     = "snake"
    status   = "complete"
    settings = [PSCustomObject]@{ rounds = 27 }
    metadata = [PSCustomObject]@{}
}
Assert-Equal `
    -Actual (Resolve-DraftHistoryTypeFromSleeperDraft -sleeperDraft $startupDraft -draftTypeConfigs $draftTypeConfigs) `
    -Expected "Free_Agent" `
    -Message "Startup-style historical draft classification no longer matches the production 2024 Free Agent draft."

$startupDefinition = [PSCustomObject][ordered]@{
    Season        = "2024"
    DraftType     = "Free_Agent"
    DraftInstance = 1
    DraftCode     = "Free_Agent"
    DraftKey      = "2024_Free_Agent"
    SleeperDraft  = $startupDraft
}
$startupTradedPick = [PSCustomObject][ordered]@{
    season            = "2024"
    round             = 1
    roster_id         = 6
    previous_owner_id = 6
    owner_id          = 1
}
$startupContext = New-HistoricalTransactionDraftPickSleeperContext `
    -definition $startupDefinition `
    -tradedPicks @($startupTradedPick)

$rawTransactionPick = Get-DraftPickOutputFromSleeper -sleeperPick $startupTradedPick
$historicalTransaction = [PSCustomObject][ordered]@{
    Source        = "Sleeper"
    TransactionID = "1134212109669441536"
    Type          = "trade"
    Status        = "complete"
    Season        = "2024"
    Week          = 1
    CreatedAt     = [Int64]1724779748888
    CreatedDate   = "2024-08-27"
    RosterIDs     = @(1, 6)
    Adds          = @{}
    Drops         = @{}
    DraftPicks    = @($rawTransactionPick)
    Notes         = $null
}
$identityResult = Resolve-TransactionDraftPickTypesFromContexts `
    -transactions @($historicalTransaction) `
    -contexts @($startupContext)
$resolvedPick = $identityResult.Transactions[0].DraftPicks[0]
Assert-Equal -Actual $resolvedPick.DraftType -Expected "Free_Agent" -Message "Historical transaction pick did not inherit the completed draft type."
Assert-Equal -Actual $resolvedPick.DraftInstance -Expected 1 -Message "Historical transaction pick did not inherit DraftInstance 1."
Assert-Equal -Actual $resolvedPick.DraftCode -Expected "Free_Agent" -Message "Historical transaction pick did not inherit the canonical DraftCode."
Assert-Equal -Actual $resolvedPick.DraftKey -Expected "2024_Free_Agent" -Message "Historical transaction pick did not inherit the canonical DraftKey."
Assert-Equal -Actual $resolvedPick.SleeperDraftID -Expected "startup-2024" -Message "Historical transaction pick did not inherit SleeperDraftID."

$historicalPick = [PSCustomObject][ordered]@{
    PickKey               = "2024_Free_Agent_R1_OO6"
    DraftKey              = "2024_Free_Agent"
    Season                = "2024"
    DraftType             = "Free_Agent"
    DraftInstance         = 1
    DraftCode             = "Free_Agent"
    Round                 = 1
    OriginalOwnerRosterID = 6
    CurrentOwnerRosterID  = 6
    WasTraded             = $false
    IsCurrentlyTraded     = $false
    TradeSource           = $null
    TradeHistory          = @()
}
$appliedPicks = Get-AppliedDraftPickTrades `
    -picks @($historicalPick) `
    -transactions @($identityResult.Transactions) `
    -draftKey "2024_Free_Agent"
Assert-Equal -Actual $appliedPicks[0].CurrentOwnerRosterID -Expected 1 -Message "Canonical historical trade did not update current owner."
Assert-True -Condition ([bool]$appliedPicks[0].WasTraded) -Message "Canonical historical trade did not mark the pick as traded."
Assert-Equal -Actual $appliedPicks[0].TradeHistory.Count -Expected 1 -Message "Canonical historical trade history was not reconstructed."
Assert-Equal -Actual $appliedPicks[0].TradeHistory[0].TransactionID -Expected "1134212109669441536" -Message "Historical TradeHistory lost the source transaction ID."
Assert-Equal -Actual $appliedPicks[0].TradeHistory[0].PreviousOwnerRosterID -Expected 6 -Message "Historical TradeHistory lost previous owner."
Assert-Equal -Actual $appliedPicks[0].TradeHistory[0].NewOwnerRosterID -Expected 1 -Message "Historical TradeHistory lost new owner."

# Cross-season regression: a transaction stored in the 2024 archive can move a
# 2025 pick. Global completed-draft contexts must resolve from the pick season,
# not from the transaction file's season.
$rookieDefinition = [PSCustomObject][ordered]@{
    Season        = "2025"
    DraftType     = "Rookie"
    DraftInstance = 1
    DraftCode     = "Rookie"
    DraftKey      = "2025_Rookie"
    SleeperDraft  = [PSCustomObject]@{ draft_id = "rookie-2025" }
}
$futureTradedPick = [PSCustomObject][ordered]@{
    season            = "2025"
    round             = 2
    roster_id         = 1
    previous_owner_id = 1
    owner_id          = 2
}
$rookieContext = New-HistoricalTransactionDraftPickSleeperContext `
    -definition $rookieDefinition `
    -tradedPicks @($futureTradedPick)
$futureTransaction = [PSCustomObject][ordered]@{
    Source        = "Sleeper"
    TransactionID = "cross-season"
    Type          = "trade"
    Status        = "complete"
    Season        = "2024"
    Week          = 1
    CreatedAt     = [Int64]1
    CreatedDate   = "2024-01-01"
    RosterIDs     = @(1, 2)
    Adds          = @{}
    Drops         = @{}
    DraftPicks    = @((Get-DraftPickOutputFromSleeper -sleeperPick $futureTradedPick))
    Notes         = $null
}
$crossSeasonResult = Resolve-TransactionDraftPickTypesFromContexts `
    -transactions @($futureTransaction) `
    -contexts @($startupContext, $rookieContext)
Assert-Equal -Actual $crossSeasonResult.Transactions[0].Season -Expected "2024" -Message "Cross-season transaction provenance changed unexpectedly."
Assert-Equal -Actual $crossSeasonResult.Transactions[0].DraftPicks[0].DraftKey -Expected "2025_Rookie" -Message "Cross-season historical pick did not resolve against the completed 2025 draft context."
Assert-Equal -Actual $crossSeasonResult.Transactions[0].DraftPicks[0].DraftInstance -Expected 1 -Message "Cross-season historical pick lost concrete DraftInstance."

# Weekly ownership: Transactions is the scheduled coupled rebuild. Drafts remains
# independently dispatchable for manual repair/refresh but is no longer a second
# scheduled writer that can run on stale historical transactions first.
$transactionsWorkflow = Get-Content "$PSScriptRoot\..\..\.github\workflows\update-transactions.yml" -Raw
$draftsWorkflow = Get-Content "$PSScriptRoot\..\..\.github\workflows\update-drafts.yml" -Raw
Assert-True -Condition $transactionsWorkflow.Contains("schedule:") -Message "Transactions workflow lost its weekly schedule."
Assert-True -Condition $transactionsWorkflow.Contains("RequestTransactions.ps1") -Message "Transactions workflow no longer runs RequestTransactions.ps1."
Assert-True -Condition $draftsWorkflow.Contains("workflow_dispatch:") -Message "Drafts workflow is no longer manually dispatchable."
Assert-True -Condition (-not $draftsWorkflow.Contains("schedule:")) -Message "Drafts workflow must be manual-only after the coupled history rebuild change."

Write-Host "Historical transaction rebuild regression tests passed." -ForegroundColor Green
