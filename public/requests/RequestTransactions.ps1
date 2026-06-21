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
# Funktionen
# ===========================================================================

function Invoke-PastSeasonsIndexRefresh {
    Write-Host "Refreshing PastSeasonsIndex.json..." -ForegroundColor Yellow
    & "$PSScriptRoot\RequestPastSeasonsIndex.ps1"

    if (-not $?) {
        throw "RequestPastSeasonsIndex.ps1 failed."
    }
}

# ===========================================================================
# Logik
# ===========================================================================

#--- Transaktionen für alle Saisons aktualisieren ---
$updatedTransactions = Update-TransactionsAllSeasons -ForceCurrent -ForceHistory
Invoke-PastSeasonsIndexRefresh

if ($updatedTransactions) {
    Write-Host "Transactions updated." -ForegroundColor Green
} else {
    Write-Host "No transactions updated." -ForegroundColor Yellow
}
