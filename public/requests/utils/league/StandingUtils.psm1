
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

function Get-WinPct($team) {
    $games = $team.Wins + $team.Losses + $team.Ties
    if ($games -eq 0) { return -1 } # Keine Spiele, Win% undefiniert
    return ($team.Wins + (0.5 * $team.Ties)) / $games
}

# ===========================================================================
# Playoff-Standings Utils
# ===========================================================================

function Get-PlayoffProperties{
    return @('Place','TeamID','Owner','OwnerAvatar','TeamName','TeamAvatar','PlaceType','PlaceOrdinal', 'PlaceCumulative', 'PlaceAverage', 'Championships', 'RunnerUps', 'Thirds')
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
        [switch]$allTime
    )

    Write-Host "$($teams.Count) regular season teams to rank." -ForegroundColor Yellow

    # Sortierung abhängig von Season oder AllTime
    if($allTime){
        $sorted = $teams | Sort-Object -Property @{
            Expression = "RegularSeasonWins"; Descending = $true
        }, @{
            Expression = { Get-WinPct $_ }; Descending = $true
        }, @{
            Expression = "Points"; Descending = $true
        }, @{
            Expression = "PointsAgainst"; Ascending = $true
        }
    } else {
        $sorted = $teams | Sort-Object -Property @{
            Expression = { Get-WinPct $_ }; Descending = $true
        }, @{
            Expression = "Points"; Descending = $true
        }, @{
            Expression = "PointsAgainst"; Ascending = $true
        }
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
        if($allTime) {
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

function Get-RegularSeasonProperties{
    return @('Place','TeamID','Owner','TeamName','PlaceOrdinal','NumberOfGames','Wins','Losses','Ties','RegularSeasonWins','WinPercentage', 'WinPercentageDiffLeagueAvg','Points','PointsAgainst','Record','Streak','PointDifference', 'PointsPerGame', 'PointsPerGameDiffLeagueAvg', 'PointsAgainstPerGame', 'PointsAgainstPerGameDiffLeagueAvg', 'LongestWinStreak', 'WinStreakScore', 'LongestLossStreak', 'LossStreakScore', 'EfficiencyScore', 'IronWillScore', 'PreviousWeekPlace', 'PlaceDelta')
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

    # A previously published weekly movement may change even when current
    # wins, points and current PlaceDelta are identical. Compare nested values
    # explicitly; Compare-Standings' scalar -ne is not an array comparator.
    for ($i = 0; $i -lt @($newRegularSeason).Count; $i++) {
        # Rows without the field (AllTime, completed seasons) must compare equal:
        # assign arrays directly (an if expression unrolls @($null) to $null) and
        # drop the $null that @() makes from a missing property.
        $oldHistory = @()
        if ($i -lt @($oldRegularSeason).Count) {
            $oldHistory = @($oldRegularSeason[$i].WeeklyMovements | Where-Object { $null -ne $_ })
        }
        $newHistory = @($newRegularSeason[$i].WeeklyMovements | Where-Object { $null -ne $_ })
        if ((ConvertTo-Json -InputObject $oldHistory -Depth 6 -Compress) -cne (ConvertTo-Json -InputObject $newHistory -Depth 6 -Compress)) {
            Write-Host "Regular season weekly movements changed for team '$($newRegularSeason[$i].TeamID)'."
            return $true
        }
    }

    return $false
}

# ===========================================================================
# Award Utils
# ===========================================================================

function Get-AwardProperties{
    return @('Name','IconUnicode','StatDisplay','TeamID','Owner','TeamName')
}

function Compare-Awards{
    
    param(
        [Parameter(Mandatory=$true)]
        [AllowNull()]
        [AllowEmptyCollection()]
        [array]$oldAwards,
        [Parameter(Mandatory=$true)]
        [AllowNull()]
        [AllowEmptyCollection()]
        [array]$newAwards
    )

    if (-not $oldAwards -and -not $newAwards) {
        return $false
    }

    if (-not $oldAwards -or -not $newAwards) {
        Write-Host "Awards presence changed."
        return $true
    }

    if ($oldAwards.Count -ne $newAwards.Count) {
        Write-Host "Awards count changed."
        return $true
    }

    for ($i = 0; $i -lt $oldAwards.Count; $i++) {
        $oldAward = $oldAwards[$i]
        $newAward = $newAwards[$i]

        if ($oldAward.Name -ne $newAward.Name) {
            Write-Host "Award name changed at index $($i): '$($oldAward.Name)' -> '$($newAward.Name)'"
            return $true
        }

        if(Compare-Standings -oldStandings $oldAwards -newStandings $newAwards -propertiesToCheck (Get-AwardProperties) -outputProperty "Name") {
            Write-Host "Awards changed."
            return $true
        }
    }

    return $false
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
                    RegularSeasonWins = 0
                }
            }
            if($team.Place -eq 1) {
                $standingsRegularSeason[$team.TeamID].RegularSeasonWins += 1
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
                    RunnerUps = 0
                    Thirds = 0
                    PlaceCumulative = 0
                    PlaceAverage = -1
                    Placements = @() # Array aller Platzierungen über die Seasons hinweg, z.B. [1, 3, 2, ...]
                }
            }
            if($team.Place -eq 1) {
                $standingsPlayoffs[$team.TeamID].Championships += 1
            }
            if($team.Place -eq 2) {
                $standingsPlayoffs[$team.TeamID].RunnerUps += 1
            }
            if($team.Place -eq 3) {
                $standingsPlayoffs[$team.TeamID].Thirds += 1
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
    $standingsRegularSeasonSorted = Get-RankedRegularSeasonStandings -teams ($standingsRegularSeason.Values) -allTime

    # Playoffs: Sortierung nach Championships mit Tie Breaker: RunnerUps, Thirds, Regular Season Wins, PlaceAverage, Regular Season Place
    $standingsPlayoffsSorted = $standingsPlayoffs.Values | Sort-Object -Property @{
        Expression = "Championships"; Descending = $true
    }, @{
        Expression = "RunnerUps"; Descending = $true
    }, @{
        Expression = "Thirds"; Descending = $true        
    }, @{
        Expression = { 
            $teamID = $_.TeamID
            if ($standingsRegularSeason -and $standingsRegularSeason.ContainsKey($teamID)) {
                return $standingsRegularSeason[$teamID].RegularSeasonWins
            } else {
                return [int]::MaxValue # Wenn kein Regular Season Platz, dann ans Ende sortieren
            }
        }; Descending = $true
    }, @{
        Expression = "PlaceAverage"; Ascending = $true
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