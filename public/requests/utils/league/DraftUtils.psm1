
# ===========================================================================
# Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\..\ConfigUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\league\LeagueUtils.psm1" -ErrorAction Stop -Force
}
catch {
    Write-Error "Fehler beim Laden der Module: $_"
    throw $_
}


# ===========================================================================
# Helper Utils
# ===========================================================================

function Compare-Standings{
    
    param(
        [Parameter(Mandatory=$true)]
        [AllowNull()]
        [AllowEmptyCollection()]
        [array]$oldStandings,
        [Parameter(Mandatory=$true)]
        [AllowNull()]
        [AllowEmptyCollection()]
        [array]$newStandings,
        [Parameter(Mandatory=$true)]
        [array]$propertiesToCheck,
        [string]$outputProperty = "Owner"
    )

    # Wenn nur eine Seite Daten hat, dann Änderung
    if (($oldStandings -and -not $newStandings) -or (-not $oldStandings -and $newStandings)) {
        if ($oldStandings) {
            $oldStatus = "Present"
        } else {
            $oldStatus = "Not Present"
        }
        if ($newStandings) {
            $newStatus = "Present"
        } else {
            $newStatus = "Not Present"
        }
        Write-Host "Standings presence changed: " $oldStatus " -> " $newStatus
        return $true
    }
    # Wenn beide Seiten Standings haben, dann vergleichen
    if ($oldStandings -and $newStandings) {

        # Vergleiche Anzahl der Standing-Platzierungen
        if ($oldStandings.Count -ne $newStandings.Count) {
            Write-Host "Standings placements count changed: $($oldStandings.Count) -> $($newStandings.Count)"
            return $true
        }

        # Vergleiche jede Platzierung
        for ($i = 0; $i -lt $oldStandings.Count; $i++) {
            $oldPlace = $oldStandings[$i]
            $newPlace = $newStandings[$i]

            # Prüfe Top-Level Eigenschaften der Platzierung
            $propsToCheck = $propertiesToCheck
            foreach ($prop in $propsToCheck) {
                if ($oldPlace.$prop -ne $newPlace.$prop) {
                    Write-Host "$($oldPlace.$outputProperty)'s property '$prop' changed: '$($oldPlace.$prop)' -> '$($newPlace.$prop)'"
                    return $true
                }
            }
        }
    }

    return $false
}

function Get-Ordinal {
    param([int]$number)

    switch ($number) {
        0 { "none" }
        1 { "1st" }
        2 { "2nd" }
        3 { "3rd" }
        default { "$number" + "th" }
    }
}



# ===========================================================================
# Playoff-Standings Utils
# ===========================================================================



# ===========================================================================
# Standings Remote Utils
# ===========================================================================

function Get-StandingsRemote {
    param (
        [string]$leagueID = (Get-Config).LeagueID,
        [array]$playoffs = (Get-Playoffs -leagueID $leagueID),
        [Parameter(Mandatory=$true)][array]$teamData,
        [Parameter(Mandatory=$true)][int]$regularSeasonGames,
        [Parameter(Mandatory=$true)][AllowNull()]$previousSeasonStandings
    )

    try {
        $winnersBracket = $playoffs.WinnersBracket
        $losersBracket  = $playoffs.LosersBracket

        Write-Host "Calculate standings..." -ForegroundColor Yellow

        # Playoff-Standings berechnen
        $playoffStandings = Get-PlayoffStandings -winnersBracket $winnersBracket -losersBracket $losersBracket -teamData $teamData

        if($playoffStandings.Count -eq 0){
            Write-Host "No playoff information available yet." -ForegroundColor Cyan
        }

        # Regular Season Standings berechnen
        $regularStandings = Get-RegularSeasonStandings -teamData $teamData -regularSeasonGames $regularSeasonGames

        if($regularStandings.Count -eq 0){
            Write-Host "No regular season information available yet." -ForegroundColor Cyan
        }

        # Awards berechnen
        $awards = Get-Awards -regularSeasonStandings $regularStandings -playoffsStandings $playoffStandings -previousSeasonStandings $previousSeasonStandings

        # --- Platzierungen in finale Struktur packen ---
        $standings = [PSCustomObject][ordered]@{
            Playoffs = $playoffStandings
            RegularSeason = $regularStandings
            Awards = $awards
        }

        Write-Host "Standings calculated." -ForegroundColor Yellow

        return $standings
    }
    catch {
         throw $_
    }    
}

