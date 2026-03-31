
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
        [array]$losersBracket,
        [Parameter(Mandatory=$true)]
        [array]$teamData
    )

    # Prüfe Brackets auf null oder leer
    if (-not $winnersBracket -or $winnersBracket.Count -eq 0) {
        Write-Warning "No winners bracket available."
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
        [AllowEmptyCollection()]
        [array]$oldPlayoffs,
        [Parameter(Mandatory=$true)]
        [AllowEmptyCollection()]
        [array]$newPlayoffs
    )

    # Wenn nur eine Seite Daten hat, dann Änderung
    if (($oldPlayoffs -and -not $newPlayoffs) -or (-not $oldPlayoffs -and $newPlayoffs)) {
        if ($oldPlayoffs) {
            $oldStatus = "Present"
        } else {
            $oldStatus = "Not Present"
        }
        if ($newPlayoffs) {
            $newStatus = "Present"
        } else {
            $newStatus = "Not Present"
        }
        Write-Host "Playoffs presence changed: " + $oldStatus + " -> " + $newStatus
        return $true
    }
    # Wenn beide Seiten Playoffs haben, dann vergleichen
    if ($oldPlayoffs -and $newPlayoffs) {

        # Vergleiche Anzahl der Playoff-Platzierungen
        if ($oldPlayoffs.Count -ne $newPlayoffs.Count) {
            Write-Host "Playoff placements count changed: $($oldPlayoffs.Count) -> $($newPlayoffs.Count)"
            return $true
        }

        # Vergleiche jede Platzierung
        for ($i = 0; $i -lt $oldPlayoffs.Count; $i++) {
            $oldPlace = $oldPlayoffs[$i]
            $newPlace = $newPlayoffs[$i]

            # Prüfe Top-Level Eigenschaften der Platzierung
            $propsToCheck = Get-PlayoffProperties
            foreach ($prop in $propsToCheck) {
                if ($oldPlace.$prop -ne $newPlace.$prop) {
                    Write-Host "Playoff placement '$($oldPlace.PlaceOrdinal)' property '$prop' changed: '$($oldPlace.$prop)' -> '$($newPlace.$prop)'"
                    return $true
                }
            }
        }
    }

    return $false
}



# ===========================================================================
# Regular Season-Standings Utils
# ===========================================================================