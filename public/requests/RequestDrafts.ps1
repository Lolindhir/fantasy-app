# ===========================================================================
# Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\utils\league\DraftTransactionPipelineUtils.psm1" -ErrorAction Stop -Force
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

$pipelineResult = Invoke-DraftTransactionRebuild
Invoke-PastSeasonsIndexRefresh

if ($pipelineResult.Drafts) {
    Write-Host "Current drafts updated." -ForegroundColor Green
} else {
    Write-Host "No current drafts generated." -ForegroundColor Yellow
}

if ($pipelineResult.HistoricalDrafts) {
    Write-Host "Historical drafts updated." -ForegroundColor Green
} else {
    Write-Host "No historical drafts generated." -ForegroundColor Yellow
}
