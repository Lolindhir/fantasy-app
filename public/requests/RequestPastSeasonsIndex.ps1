# ===========================================================================
# Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\utils\ConfigUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\PastSeasonsIndexUtils.psm1" -ErrorAction Stop -Force
}
catch {
    Write-Error "Fehler beim Laden der Module: $_"
    exit 1
}

# ===========================================================================
# Logik
# ===========================================================================

try {
    $config = Get-Config
    $changed = Update-PastSeasonsIndex -Config $config

    if ($changed) {
        Write-Host "Past seasons index updated." -ForegroundColor Green
    }
    else {
        Write-Host "Past seasons index already up to date." -ForegroundColor Cyan
    }
}
catch {
    Write-Error "Error updating past seasons index: $_"
    exit 1
}
