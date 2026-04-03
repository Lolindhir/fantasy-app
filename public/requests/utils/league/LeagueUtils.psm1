
# ===========================================================================
# 1. Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\..\ConfigUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\invoke\SleeperUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\StandingUtils.psm1" -ErrorAction Stop -Force
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
        Write-Host "Sleeper League found." -ForegroundColor Yellow

        return $leagueData
    }
    catch {
         throw $_
    }    
}

function Get-Playoffs {
    param (
        [string]$leagueID = (Get-Config).LeagueID
    )

    try {
        $winnersBracket = Get-SleeperWinnersBracket -leagueID $leagueID
        $losersBracket  = Get-SleeperLosersBracket -leagueID $leagueID

        # Winners und Losers sicher extrahieren
        if (-not $winnersBracket) { 
            $winnersBracket = @() 
            Write-Warning "Winners bracket is empty."
        }
        if (-not $losersBracket)  { 
            $losersBracket  = @() 
            Write-Warning "Losers bracket is empty."
        }

        # --- Playoff-Daten in finale Struktur packen ---
        $playoffs = if ($winnersBracket -or $losersBracket) {
            
            Write-Host "Playoffs found" -ForegroundColor Yellow

            [PSCustomObject]@{
                WinnersBracket = $winnersBracket
                LosersBracket  = $losersBracket
            }
        } else {
            Write-Host "No playoffs found." -ForegroundColor Yellow
            $null
        }

        return $playoffs
    }
    catch {
         throw $_
    }    
}

function Get-Standings {
    param (
        [string]$leagueID = (Get-Config).LeagueID,
        [array]$playoffs = (Get-Playoffs -leagueID $leagueID),
        [array]$teamData = (Get-Teams -leagueID $leagueID)
    )

    try {
        $winnersBracket = $playoffs.WinnersBracket
        $losersBracket  = $playoffs.LosersBracket

        Write-Host "Calculate standings..." -ForegroundColor Yellow

        # Playoff-Standings berechnen
        $playoffStandings = Get-PlayoffStandings -winnersBracket $winnersBracket -losersBracket $losersBracket -teamData $teamData

        # Regular Season Standings berechnen
        $regularStandings = Get-RegularSeasonStandings -teamData $teamData

        # --- Platzierungen in finale Struktur packen ---
        $standings = if ($winnersBracket -or $losersBracket) {
            [PSCustomObject]@{
                Playoffs = $playoffStandings
                RegularSeason = $regularStandings
            }
        } else {
            $null
        }

        Write-Host "Standings calculated." -ForegroundColor Yellow

        return $standings
    }
    catch {
         throw $_
    }    
}