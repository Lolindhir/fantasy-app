# ===========================================================================
# Parameters
# ===========================================================================

param(
    [switch]$ForceHistory
)

# ===========================================================================
# Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\utils\ConfigUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\DraftHistoryUtils.psm1" -ErrorAction Stop -Force
}
catch {
    Write-Error "Fehler beim Laden der Module: $_"
    exit 1
}

# ===========================================================================
# Logic
# ===========================================================================

try {
    $config = Get-Config

    if (-not $config.LeagueID) {
        Write-Error "LeagueID not set in Metadata.json!"
        exit 1
    }

    Update-DraftsHistoricalSeasons `
        -leagueID $config.LeagueID `
        -ForceHistory:$ForceHistory

    Write-Host "Draft history request finished." -ForegroundColor DarkCyan
    exit 0
}
catch {
    Write-Error "An error occurred while updating draft history: $_"
    exit 1
}
