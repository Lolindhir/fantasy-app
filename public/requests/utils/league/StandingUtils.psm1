
# ===========================================================================
# Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\..\ConfigUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\league\LeagueUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\league\PlayoffUtils.psm1" -ErrorAction Stop -Force
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

function Get-WinPct($team) {
    $games = $team.Wins + $team.Losses + $team.Ties
    if ($games -eq 0) { return -1 } # Keine Spiele, Win% undefiniert
    return ($team.Wins + (0.5 * $team.Ties)) / $games
}

# ===========================================================================
# Playoff-Standings Utils
# ===========================================================================

function Get-BracketStandings{
    param(
        [Parameter(Mandatory=$true)]
        [AllowEmptyCollection()]
        [AllowNull()]
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
        [AllowNull()]
        [array]$winnersBracket,
        [Parameter(Mandatory=$true)]
        [AllowEmptyCollection()]
        [AllowNull()]
        [array]$losersBracket,
        [Parameter(Mandatory=$true)]
        [array]$teamData
    )

    # Prüfe Winner Bracket auf null oder leer
    if (-not $winnersBracket -or $winnersBracket.Count -eq 0) {
        Write-Warning "No winners bracket available."
        return @()  # leeres Array zurückgeben
    }
    # Prüfe Loser Bracket auf null oder leer -> ist erlaubt, also kein Fehler, aber dann nur Gewinner-Bracket-Standings berechnen
    if (-not $losersBracket -or $losersBracket.Count -eq 0) {
        Write-Host "No losers bracket available." -ForegroundColor Yellow
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
            $teamInfo.PlacePlayoffs = $placeNum # Platzierung in TeamData speichern
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
    return @('Place','TeamID','Owner','TeamName','PlaceType','PlaceOrdinal', 'PlaceCumulative', 'PlaceAverage', 'Championships')
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

function Get-RankedRegularSeasonStandings {
    param(
        [array]$teams,
        [switch]$writePlace
    )

    Write-Host "$($teams.Count) regular season teams to rank." -ForegroundColor Yellow

    # Sortierung
    $sorted = $teams | Sort-Object -Property @{
        Expression = { Get-WinPct $_ }; Descending = $true
    }, @{
        Expression = "Points"; Descending = $true
    }, @{
        Expression = "PointsAgainst"; Ascending = $true
    }

    # gib die Teams der Reihenfolge nach aus
    Write-Host "Teams ranked in the following order:" -ForegroundColor Yellow
    foreach ($team in $sorted) {
        $winPct = Get-WinPct $team
        Write-Host "Team: $($team.Team) | Owner: $($team.Owner) | Win%: $([math]::Round($winPct, 4)) | Points: $($team.Points) | Points Against: $($team.PointsAgainst)" -ForegroundColor Cyan
    }

    # Ergebnis bauen
    $lastPlace = $null
    $lastKey = $null

    for ($i = 0; $i -lt $sorted.Count; $i++) {
        $team = $sorted[$i]
        $currentPlace = 0
        # Berechne Win Percentage für das Team        
        $winPct = Get-WinPct $team
        # Vergleichsschlüssel für Gleichstand
        $currentKey = "{0:N6}-{1:N2}-{2:N2}" -f $winPct, $team.Points, $team.PointsAgainst

        if($winPct -ge 0) {            
            if ($i -eq 0) {
                $currentPlace = 1
            }
            elseif (($i -gt 0) -and ($currentKey -eq $lastKey)) {                
                $currentPlace = $lastPlace
            }
            else {
                $currentPlace = $lastPlace + 1
            }            
        }

        # Properties setzen
        if($writePlace) {
            $team.Place = $currentPlace
            $team.PlaceOrdinal = Get-Ordinal $currentPlace
        }
        else {
            $team.PlaceRegular = $currentPlace
        }

        $lastPlace = $currentPlace
        $lastKey = $currentKey
    }

    return $sorted
}

function Get-RegularSeasonStandings {
    param (
        [Parameter(Mandatory = $true)]
        [array]$teamData
    )

    # Sortierung nach Sleeper-Logik
    $sortedTeams = Get-RankedRegularSeasonStandings -teams $teamData

    $result = for ($i = 0; $i -lt $sortedTeams.Count; $i++) {
        $team = $sortedTeams[$i]

        $winPct = Get-WinPct $team

        [PSCustomObject]@{
            Place         = $team.PlaceRegular
            PlaceOrdinal  = Get-Ordinal ($team.PlaceRegular)
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



# ===========================================================================
# Standings Remote Utils
# ===========================================================================

function Get-StandingsRemote {
    param (
        [string]$leagueID = (Get-Config).LeagueID,
        [array]$playoffs = (Get-Playoffs -leagueID $leagueID),
        [Parameter(Mandatory=$true)][array]$teamData
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
            [PSCustomObject][ordered]@{
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


# ===========================================================================
# Standings File Utils
# ===========================================================================


function Get-StandingsLocal {

    $filePath = (Get-Config).StandingsFile

     # Prüfe ob Datei existiert
     if (-not (Test-Path $filePath)) {
        Write-Warning "Standings file not found at $filePath. Returning empty array."
        return @()
    }

    try {
        $data = Get-Content $FilePath -Raw | ConvertFrom-Json
        if ($data -is [array]) {
            return $data
        } else {
            return @($data)
        }
    }
    catch {
        Write-Warning "Could not read existing Standings.json: $_"
        return @()
    }
}


function Get-OutputStandingsForSeason {
    param(
        [string]$season,
        [array]$standingsPlayoffs,
        [array]$standingsRegularSeason
    )

    $output = [PSCustomObject][ordered]@{
        Season = $season
        Playoffs = $standingsPlayoffs
        RegularSeason = $standingsRegularSeason
    }

    return $output
}

function Get-OutputStandingsForAllTime {
    param(
        [array]$allSeasonStandings
    )

    $seasonNumber = $allSeasonStandings.Count

    # gehe durch alle Seasons durch und baue kumulierte Standings für Regular Season und Playoffs je Team auf
    $standingsRegularSeason = @{}
    $standingsPlayoffs = @{}
    foreach ($season in $allSeasonStandings) {
        foreach ($team in $season.RegularSeason) {
            if (-not $standingsRegularSeason.ContainsKey($team.TeamID)) {
                $standingsRegularSeason[$team.TeamID] = [PSCustomObject]@{
                    Place = 0
                    PlaceOrdinal = "none"
                    TeamID = $team.TeamID
                    Owner = $team.Owner
                    TeamName = $team.TeamName
                    Wins = 0
                    Losses = 0
                    Ties = 0
                    WinPercentage = -1
                    Points = 0
                    PointsAgainst = 0
                }
            }
            $standingsRegularSeason[$team.TeamID].Wins += $team.Wins
            $standingsRegularSeason[$team.TeamID].Losses += $team.Losses
            $standingsRegularSeason[$team.TeamID].Ties += $team.Ties
            $standingsRegularSeason[$team.TeamID].Points += $team.Points
            $standingsRegularSeason[$team.TeamID].PointsAgainst += $team.PointsAgainst
        }
        foreach ($team in $season.Playoffs) {
            if (-not $standingsPlayoffs.ContainsKey($team.TeamID)) {
                $standingsPlayoffs[$team.TeamID] = [PSCustomObject]@{
                    Place = 0
                    PlaceOrdinal = "none"
                    TeamID = $team.TeamID
                    Owner = $team.Owner
                    TeamName = $team.TeamName
                    Championships = 0
                    PlaceCumulative = 0
                    PlaceAverage = -1
                    Placements = @() # Array aller Platzierungen über die Seasons hinweg, z.B. [1, 3, 2, ...]
                }
            }
            if($team.Place -eq 1) {
                $standingsPlayoffs[$team.TeamID].Championships += 1
            }
            $standingsPlayoffs[$team.TeamID].PlaceCumulative += $team.Place
            $standingsPlayoffs[$team.TeamID].Placements += $team.Place
        }
    }

    # Win Percentage berechnen und Standings in finale Struktur packen
    foreach ($teamID in $standingsRegularSeason.Keys) {
        $team = $standingsRegularSeason[$teamID]
        $winPct = Get-WinPct $team

        # Update der Standings
        $standingsRegularSeason[$team.TeamID].WinPercentage = [math]::Round($winPct, 4)
        $standingsRegularSeason[$team.TeamID].Points = [math]::Round($standingsRegularSeason[$team.TeamID].Points, 2)
        $standingsRegularSeason[$team.TeamID].PointsAgainst = [math]::Round($standingsRegularSeason[$team.TeamID].PointsAgainst, 2)
    }

    # Place Average berechnen und Standings in finale Struktur packen
    foreach ($teamID in $standingsPlayoffs.Keys) {
        $team = $standingsPlayoffs[$teamID]
        if ($seasonNumber -gt 0) {
            $placeAvg = ($team.PlaceCumulative / $seasonNumber)
        } else {
            $placeAvg = -1 # Keine Spiele, Win% undefiniert
        }

        # Update der Standings
        $standingsPlayoffs[$team.TeamID].PlaceAverage = [math]::Round($placeAvg, 2)
    }

    # Regular Season: Sortierung und Rankings eintragen
    $standingsRegularSeasonSorted = Get-RankedRegularSeasonStandings -teams ($standingsRegularSeason.Values) -writePlace

    # Playoffs: Sortierung nach PlaceAverage, dann Championships, dann Regular Season Place als Tiebreaker
    $standingsPlayoffsSorted = $standingsPlayoffs.Values | Sort-Object -Property @{
        Expression = "PlaceAverage"; Ascending = $true
    }, @{
        Expression = "Championships"; Descending = $true
    }, @{
        Expression = { 
            $teamID = $_.TeamID
            if ($standingsRegularSeason -and $standingsRegularSeason.ContainsKey($teamID)) {
                return $standingsRegularSeason[$teamID].Place
            } else {
                return [int]::MaxValue # Wenn kein Regular Season Platz, dann ans Ende sortieren
            }
        }; Ascending = $true
    }

    # Update der Playoff Place basierend auf Sortierung
    for ($i = 0; $i -lt $standingsPlayoffsSorted.Count; $i++) {
        $standingsPlayoffsSorted[$i].Place = $i + 1
        $standingsPlayoffsSorted[$i].PlaceOrdinal = Get-Ordinal ($i + 1)
    }

    $output = [PSCustomObject]@{
        Season = "AllTime"
        Playoffs = $standingsPlayoffsSorted
        RegularSeason = $standingsRegularSeasonSorted
    }

    return $output
}