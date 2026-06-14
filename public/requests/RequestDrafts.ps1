# ===========================================================================
# Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\utils\league\DraftUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\DraftHistoryUtils.psm1" -ErrorAction Stop -Force
}
catch {
    Write-Error "Fehler beim Laden der Module: $_"
    exit 1
}

# ===========================================================================
# Logik
# ===========================================================================

$drafts = Update-Drafts
$historicalDrafts = Update-DraftsHistoricalSeasons

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
