# ===========================================================================
# Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\utils\league\DraftUtils.psm1" -ErrorAction Stop -Force
}
catch {
    Write-Error "Fehler beim Laden der Module: $_"
    exit 1
}

# ===========================================================================
# Logik
# ===========================================================================

$drafts = Update-Drafts

if ($drafts) {
    Write-Host "Drafts updated." -ForegroundColor Green
} else {
    Write-Host "No drafts generated." -ForegroundColor Yellow
}