$ErrorActionPreference = "Stop"

Import-Module "$PSScriptRoot\utils\league\DraftUtils.psm1" -Force

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
Assert-Before -Text $pipeline -First "Update-AllTransactionDraftPickTypesFromSleeper" -Second "Update-DraftsOrderAware" -Message "Draft identity must resolve before current draft generation."
Assert-Before -Text $pipeline -First "Update-DraftsOrderAware" -Second "Update-DraftsHistoricalSeasonsSafeOrderAware" -Message "Current draft generation must complete before historical draft generation."
Assert-Before -Text $pipeline -First "Update-DraftsHistoricalSeasonsSafeOrderAware" -Second "Update-AllTransactionDraftPickDetailsFromLocalDrafts" -Message "Historical drafts must be rebuilt before transaction pick-detail enrichment."
Assert-True -Condition $pipeline.Contains("-ForceHistory:`$ForceHistory") -Message "ForceHistory is not forwarded to the historical draft rebuild."

# Canonical historical identity must be regenerated from the current contract,
# never by preserving or translating old D<n> generated keys.
Assert-Equal -Actual (New-DraftKey -season "2024" -draftType "Free_Agent" -draftInstance 1) -Expected "2024_Free_Agent" -Message "Historical Free Agent DraftKey is not canonical."
Assert-Equal -Actual (New-DraftKey -season "2025" -draftType "Rookie" -draftInstance 1) -Expected "2025_Rookie" -Message "Historical Rookie DraftKey is not canonical."
Assert-Equal -Actual (New-DraftCode -draftType "Free_Agent" -draftInstance 1) -Expected "Free_Agent" -Message "Historical DraftCode for instance 1 is not canonical."

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
