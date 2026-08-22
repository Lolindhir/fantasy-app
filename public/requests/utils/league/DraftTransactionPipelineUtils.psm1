# ===========================================================================
# Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\..\ConfigUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\DraftUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\DraftDisplayStatusUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\DraftHistoryUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\DraftHistoryEmptyDefinitionsFix.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\DraftOrderAwareUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\TransactionDraftPickEnrichmentUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\HistoricalTransactionDraftPickIdentityUtils.psm1" -ErrorAction Stop -Force
}
catch {
    Write-Error "Fehler beim Laden der Module: $_"
    throw $_
}

# ===========================================================================
# Coupled draft / transaction rebuild
# ===========================================================================

function Invoke-DraftTransactionRebuild {
    param(
        [string]$leagueID = (Get-Config).LeagueID,
        [switch]$ForceHistory
    )

    Write-Host "Resolve transaction draft identities..." -ForegroundColor Yellow
    Update-AllTransactionDraftPickTypesFromSleeper -leagueID $leagueID

    # Historical transaction picks must use the exact same completed-draft
    # definitions that the following historical draft generation step uses.
    # This corrects classification drift before Draft ownership/TradeHistory is built.
    Update-HistoricalTransactionDraftPickTypesFromCompletedDrafts -leagueID $leagueID

    Write-Host "Rebuild current and open drafts from refreshed transactions..." -ForegroundColor Yellow
    $drafts = Update-DraftsOrderAware -leagueID $leagueID
    if ($drafts) {
        $drafts = Set-DraftDisplayStatuses -drafts $drafts
        Save-Drafts -drafts $drafts
    }

    Write-Host "Rebuild completed draft history from refreshed transactions..." -ForegroundColor Yellow
    $historicalDrafts = Update-DraftsHistoricalSeasonsSafeOrderAware `
        -leagueID $leagueID `
        -ForceHistory:$ForceHistory

    Write-Host "Enrich transactions from freshly rebuilt draft outputs..." -ForegroundColor Yellow
    Update-AllTransactionDraftPickDetailsFromLocalDrafts

    return [PSCustomObject][ordered]@{
        Drafts           = $drafts
        HistoricalDrafts = $historicalDrafts
    }
}
