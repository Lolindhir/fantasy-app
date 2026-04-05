
# ===========================================================================
# 1. Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\..\ConfigUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\invoke\SleeperUtils.psm1" -ErrorAction Stop -Force
}
catch {
    Write-Error "Fehler beim Laden der Module: $_"
    throw $_
}

# ===========================================================================
# 2. Funktionen
# ===========================================================================

function Get-LeagueRaw {
    param (
        [string]$leagueID = (Get-Config).LeagueID
    )

    try {
        $leagueData = Get-SleeperLeague -leagueID $leagueID
        Write-Host "Raw Sleeper League data fetched." -ForegroundColor Yellow

        return $leagueData
    }
    catch {
         throw $_
    }    
}

