
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