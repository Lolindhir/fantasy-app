
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
        [array]$propertiesToCheck
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
                    Write-Host "Standings placement '$($oldPlace.PlaceOrdinal)' property '$prop' changed: '$($oldPlace.$prop)' -> '$($newPlace.$prop)'"
                    return $true
                }
            }
        }
    }

    return $false
}


# ===========================================================================
# Playoff-Standings Utils
# ===========================================================================

function Get-BracketStandings{
    param(
        [Parameter(Mandatory=$true)]
        [AllowEmptyCollection()]
        [array]$matches,
        [Parameter(Mandatory=$true)]
        [int]$startPlace
    )

    # prüfe ob Matches null oder leer sind
    if (-not $matches -or $matches.Count -eq 0) {
        return @{}  # leeres Dictionary zurückgeben
    }

    $placements = @{}

    foreach ($match in $matches) {
        if ($match.p) {
            # Gewinner bekommt Platz p + Offset
            $placements["$($startPlace + $match.p - 1)"] = $match.w
            # Verlierer bekommt Platz p+1 + Offset
            $placements["$($startPlace + $match.p)"]     = $match.l
        }
    }    

    return $placements
}

function Get-PlayoffStandings{
    param(
        [Parameter(Mandatory=$true)]
        [AllowEmptyCollection()]
        [array]$winnersBracket,
        [Parameter(Mandatory=$true)]
        [AllowEmptyCollection()]
        [array]$losersBracket,
        [Parameter(Mandatory=$true)]
        [array]$teamData
    )

    # Prüfe Brackets auf null oder leer
    if (-not $winnersBracket -or $winnersBracket.Count -eq 0) {
        Write-Warning "No winners bracket available."
        return @()  # leeres Array zurückgeben
    }
    if (-not $losersBracket -or $losersBracket.Count -eq 0) {
        Write-Warning "No losers bracket available."
        return @()  # leeres Array zurückgeben
    }

    # Platzierungen berechnen
    $winnerPlacements = Get-BracketStandings $winnersBracket 1
    $loserPlacements  = Get-BracketStandings $losersBracket ($winnerPlacements.Count + 1)

    # Zusammenführen
    $placements = @{}
    foreach ($k in $winnerPlacements.Keys) { $placements[$k] = $winnerPlacements[$k] }
    foreach ($k in $loserPlacements.Keys)  { $placements[$k] = $loserPlacements[$k] }

    # Placements in Objekte umwandeln
    # Struktur aus folgenden Properties: Place (1, 2, 3, ...), TeamID (RosterID des Teams auf diesem Platz), Owner (Name des Besitzers des Teams auf diesem Platz), TeamName (Name des Teams auf diesem Platz), PlaceType (Winner, Loser), PlaceOrdinal (1st, 2nd, 3rd, ...)
    $placements = $placements.GetEnumerator() | Sort-Object Name | ForEach-Object {
        $placeNum = [int]$_.Name
        $teamID = $_.Value
        $teamInfo = $teamData | Where-Object { $_.TeamID -eq $teamID }
        if ($teamInfo) {
            [PSCustomObject]@{
                Place        = $placeNum
                TeamID       = $teamID
                Owner        = $teamInfo.Owner
                TeamName     = $teamInfo.Team
                PlaceType    = if ($placeNum -le $winnerPlacements.Count) { "Winner" } else { "Loser" }
                PlaceOrdinal = switch ($placeNum) {
                    1 { "1st" }
                    2 { "2nd" }
                    3 { "3rd" }
                    default { "${placeNum}th" }
                }
            }
        } else {
            Write-Warning "Could not find team info for TeamID $teamID in placements."
            [PSCustomObject]@{
                Place        = $placeNum
                TeamID       = $teamID
                Owner        = "Unknown Owner"
                TeamName     = "Unknown Team (ID: $teamID)"
                PlaceType    = if ($placeNum -le $winnerPlacements.Count) { "Winner" } else { "Loser" }
                PlaceOrdinal = switch ($placeNum) {
                    1 { "1st" }
                    2 { "2nd" }
                    3 { "3rd" }
                    default { "${placeNum}th" }
                }
            }
        }
    }

    return $placements
}

function Get-PlayoffProperties{
    return @('Place','TeamID','Owner','TeamName','PlaceType','PlaceOrdinal')
}

function Compare-PlayoffStandings{
    
    param(
        [Parameter(Mandatory=$true)]
        [AllowNull()]
        [AllowEmptyCollection()]
        [array]$oldPlayoffs,
        [Parameter(Mandatory=$true)]
        [AllowNull()]
        [AllowEmptyCollection()]
        [array]$newPlayoffs
    )

    if(Compare-Standings -oldStandings $oldPlayoffs -newStandings $newPlayoffs -propertiesToCheck (Get-PlayoffProperties)) {
        Write-Host "Playoff standings changed."
        return $true
    }

    return $false
}



# ===========================================================================
# Regular Season-Standings Utils
# ===========================================================================

function Get-RegularSeasonStandings {
    param (
        [Parameter(Mandatory = $true)]
        [array]$teamData
    )

    # Win Percentage berechnen
    function Get-WinPct($team) {
        $games = $team.Wins + $team.Losses + $team.Ties
        if ($games -eq 0) { return 0 }
        return ($team.Wins + (0.5 * $team.Ties)) / $games
    }

    # Ordinal (1st, 2nd, ...)
    function Get-Ordinal($n) {
        if ($n % 100 -in 11,12,13) { return "$($n)th" }
        switch ($n % 10) {
            1 { return "$($n)st" }
            2 { return "$($n)nd" }
            3 { return "$($n)rd" }
            default { return "$($n)th" }
        }
    }

    # Sortierung nach Sleeper-Logik
    $sortedTeams = $teamData | Sort-Object `
        @{Expression = { Get-WinPct $_ }; Descending = $true },
        @{Expression = { $_.Points }; Descending = $true },
        @{Expression = { $_.PointsAgainst }; Ascending = $true }

    # Ergebnis bauen
    $result = for ($i = 0; $i -lt $sortedTeams.Count; $i++) {
        $team = $sortedTeams[$i]
        $winPct = Get-WinPct $team

        [PSCustomObject]@{
            Place         = $i + 1
            PlaceOrdinal  = Get-Ordinal ($i + 1)
            TeamID        = $team.TeamID
            Owner         = $team.Owner
            TeamName      = $team.Team
            Wins          = $team.Wins
            Losses        = $team.Losses
            Ties          = $team.Ties
            WinPercentage = [math]::Round($winPct, 4)
            Points        = $team.Points
            PointsAgainst = $team.PointsAgainst
            Record        = $team.Record
            Streak        = $team.Streak
        }
    }

    return $result
}

function Get-RegularSeasonProperties{
    return @('Place','TeamID','Owner','TeamName','PlaceOrdinal','Wins','Losses','Ties','WinPercentage','Points','PointsAgainst','Record','Streak')
}

function Compare-RegularSeasonStandings{
    
    param(
        [Parameter(Mandatory=$true)]
        [AllowNull()]
        [AllowEmptyCollection()]
        [array]$oldRegularSeason,
        [Parameter(Mandatory=$true)]
        [AllowNull()]
        [AllowEmptyCollection()]
        [array]$newRegularSeason
    )

    if(Compare-Standings -oldStandings $oldRegularSeason -newStandings $newRegularSeason -propertiesToCheck (Get-RegularSeasonProperties)) {
        Write-Host "Regular season standings changed."
        return $true
    }

    return $false
}