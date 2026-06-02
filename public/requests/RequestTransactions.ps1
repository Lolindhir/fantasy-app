# ===========================================================================
# Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\utils\league\TransactionUtils.psm1" -ErrorAction Stop -Force
}
catch {
    Write-Error "Fehler beim Laden der Module: $_"
    exit 1
}

# ===========================================================================
# Logik
# ===========================================================================

# --- Transaktionen für alle Saisons aktualisieren ---
$updatedTransactions = Update-TransactionsAllSeasons -ForceCurrent -ForceHistory

if ($updatedTransactions) {
    Write-Host "Transactions updated." -ForegroundColor Green
} else {
    Write-Host "No transaction updates required." -ForegroundColor Yellow
}