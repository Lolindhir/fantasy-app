
# ===========================================================================
# 1. Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\..\ConfigUtils.psm1" -ErrorAction Stop -Force
}
catch {
    Write-Error "Fehler beim Laden der Module: $_"
    throw $_
}

# ===========================================================================
# 2. Funktionen
# ===========================================================================

function Get-PlayersFromFile {
    param(
        [string]$PlayersFile = (Get-Config).PlayersFile
    )

    try {
        # --- Spieler-Daten holen---
        if (!(Test-Path $PlayersFile)) {
            throw "Players.json not found at '$PlayersFile'!"
        }
        $playersJson = Get-Content $PlayersFile -Raw
        if (-not $playersJson) {
            throw "Players.json is empty!"
        }
        $playersData = $playersJson | ConvertFrom-Json
        if (-not $playersData -or $playersData.Count -eq 0) {
            throw "No valid players found in Players.json!"
        }

        return $playersData
    }
    catch {
        Write-Error "Failed to read or parse Players file: $_"
        throw $_
    }
}