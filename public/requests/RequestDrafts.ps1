# ===========================================================================
# Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\utils\league\DraftUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\DraftDisplayStatusUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\DraftHistoryUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\DraftHistoryEmptyDefinitionsFix.psm1" -ErrorAction Stop -Force
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

    if ($LASTEXITCODE -ne 0) {
        throw "RequestPastSeasonsIndex.ps1 failed with exit code $LASTEXITCODE."
    }
}

# ===========================================================================
# Logik
# ===========================================================================

$drafts = Update-Drafts
if ($drafts) {
    $drafts = Set-DraftDisplayStatuses -drafts $drafts
    Save-Drafts -drafts $drafts
}

$historicalDrafts = Update-DraftsHistoricalSeasonsSafe
Invoke-PastSeasonsIndexRefresh

if ($drafts) {
    Write-Host "Current drafts updated." -ForegroundColor Green
} else {
    Write-Host "No current drafts generated." -ForegroundColor Yellow
}

if ($historicalDrafts) {
    Write-Host "Historical drafts updated." -ForegroundColor Green
} else {
    Write-Host "No historical drafts generated." -ForegroundColor Yellow
}
