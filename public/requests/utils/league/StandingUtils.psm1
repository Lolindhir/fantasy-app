
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
        if ($match.p -and $match.w -and $match.l) {
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

    # Prüfe Winner Placements auf null oder leer
    if (-not $winnerPlacements -or $winnerPlacements.Count -eq 0) {
        Write-Warning "No winners placements available."
        return @()  # leeres Array zurückgeben
    }
    # Prüfe Loser Placements auf null oder leer -> ist erlaubt, also kein Fehler, aber dann nur Gewinner-Bracket-Standings berechnen
    if (-not $loserPlacements -or $loserPlacements.Count -eq 0) {
        Write-Host "No losers placements available." -ForegroundColor Yellow
    }

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
    return @('Place','TeamID','Owner','TeamName','PlaceType','PlaceOrdinal', 'PlaceCumulative', 'PlaceAverage', 'Championships', 'RunnerUps', 'Thirds')
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

function Format-WinPct {
    param($value)

    if ($value -eq 1) {
        return "1.000"
    }

    return ([math]::Round($value, 3).ToString("0.000", [System.Globalization.CultureInfo]::InvariantCulture)).Substring(1)
}

function Get-RegularSeasonStandings {
    param (
        [Parameter(Mandatory = $true)]
        [array]$teamData,
        [Parameter(Mandatory = $true)]
        [int]$regularSeasonGames
    )

    # Liga-übergreifende Statistiken ermitteln
    $leagueAvgPointsPerGame = if ($teamData.Count -gt 0) {
        ($teamData | Measure-Object -Property Points -Sum).Sum / ($teamData.Count * $regularSeasonGames)
    } else {
        0
    }
    $leagueAvgPointsAgainstPerGame = if ($teamData.Count -gt 0) {
        ($teamData | Measure-Object -Property PointsAgainst -Sum).Sum / ($teamData.Count * $regularSeasonGames)
    } else {
        0
    }
    $leagueAvgWinPct = if ($teamData.Count -gt 0) {
        ($teamData | ForEach-Object { Get-WinPct $_ } | Measure-Object -Average).Average
    } else {
        0
    }

    # Sortierung nach Sleeper-Logik
    $sortedTeams = Get-RankedRegularSeasonStandings -teams $teamData

    $result = for ($i = 0; $i -lt $sortedTeams.Count; $i++) {
        $team = $sortedTeams[$i]

        # Streaks berechnen
        $winStreaks = [regex]::Matches($team.Record, 'W+')
        $longestWinStreak = if ($winStreaks.Count -gt 0) {
            ($winStreaks | ForEach-Object { $_.Value.Length } | Measure-Object -Maximum).Maximum
        } else {
            0
        }
        $lossStreaks = [regex]::Matches($team.Record, 'L+')
        $longestLossStreak = if ($lossStreaks.Count -gt 0) {
            ($lossStreaks | ForEach-Object { $_.Value.Length } | Measure-Object -Maximum).Maximum
        } else {
            0
        }

        # Win Percentage berechnen
        $winPct = Get-WinPct $team

        # Points per Game und Points Against per Game berechnen
        $pointsPerGame = $team.Points / $regularSeasonGames
        $pointsAgainstPerGame = $team.PointsAgainst / $regularSeasonGames

        # Efficiency Score berechnen    
        $pointsPerGameDiff = $pointsPerGame - $leagueAvgPointsPerGame
        $pointsAgainstPerGameDiff = $pointsAgainstPerGame - $leagueAvgPointsAgainstPerGame
        $efficiencyScore = $pointsPerGameDiff + $pointsAgainstPerGameDiff + $team.Wins

        # Iron Will Score berechnen
        if($leagueAvgPointsAgainstPerGame -gt 0){
            $ironWillScore = ($pointsAgainstPerGame / $leagueAvgPointsAgainstPerGame) + [math]::Sqrt($winPct * 0.25)
        } else {
            $ironWillScore = -999
        }

        # Win% Historie berechnen
        if ([string]::IsNullOrEmpty($team.Record)) {
            $record = @()
        } else {
            $record = $team.Record.ToCharArray()
        }
        $winPctHistory = @()
        $wins = 0
        for ($j = 0; $j -lt $record.Length; $j++) {
            if ($record[$j] -eq 'W') { $wins++ }
            $gamesPlayed = $j + 1
            $winPctHistory += [math]::Round($wins / $gamesPlayed, 4)
        }
        # $winPctHistory jetzt = WinPercentage nach jedem Spieltag
        # Differenzen zwischen aufeinanderfolgenden Spieltagen
        $diffs = @()
        for ($k = 1; $k -lt $winPctHistory.Count; $k++) {
            $diffs += $winPctHistory[$k] - $winPctHistory[$k - 1]
        }

        [PSCustomObject]@{
            Place         = $team.PlaceRegular
            PlaceOrdinal  = Get-Ordinal ($team.PlaceRegular)
            TeamID        = $team.TeamID
            Owner         = $team.Owner
            TeamName      = $team.Team
            NumberOfGames = $regularSeasonGames
            Wins          = $team.Wins
            Losses        = $team.Losses
            Ties          = $team.Ties
            Points        = $team.Points
            PointsAgainst = $team.PointsAgainst
            Record        = $team.Record
            Streak        = $team.Streak
            # Berechnung von Scores für Standings und Awards
            WinPercentage                       = [math]::Round($winPct, 4)
            WinPercentageDisplay                = Format-WinPct $winPct
            WinPercentageDiffLeagueAvg          = [math]::Round($winPct - $leagueAvgWinPct, 2)
            WinPercentageHistory                = $winPctHistory
            PointDifference                     = [math]::Round($team.Points - $team.PointsAgainst, 2)
            PointsPerGame                       = [math]::Round($pointsPerGame, 2)
            PointsPerGameDiffLeagueAvg          = [math]::Round($pointsPerGameDiff, 2)
            PointsAgainstPerGame                = [math]::Round($pointsAgainstPerGame, 2)
            PointsAgainstPerGameDiffLeagueAvg   = [math]::Round($pointsAgainstPerGameDiff, 2)
            LongestWinStreak                    = $longestWinStreak;
            WinStreakScore                      = [math]::Round($longestWinStreak + ($team.Wins * 0.001) + ($team.Points * 0.00001), 4)
            LongestLossStreak                   = $longestLossStreak;
            LossStreakScore                     = [math]::Round($longestLossStreak + ($team.Losses * 0.001) + ($team.PointsAgainst * 0.00001), 4)
            EfficiencyScore                     = [math]::Round($efficiencyScore, 4)
            IronWillScore                       = [math]::Round($ironWillScore, 4)
        }
    }

    return $result
}

function Get-RegularSeasonProperties{
    return @('Place','TeamID','Owner','TeamName','PlaceOrdinal','NumberOfGames','Wins','Losses','Ties','RegularSeasonWins','WinPercentage', 'WinPercentageDiffLeagueAvg','Points','PointsAgainst','Record','Streak','PointDifference', 'PointsPerGame', 'PointsPerGameDiffLeagueAvg', 'PointsAgainstPerGame', 'PointsAgainstPerGameDiffLeagueAvg', 'LongestWinStreak', 'WinStreakScore', 'LongestLossStreak', 'LossStreakScore', 'EfficiencyScore', 'IronWillScore')
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
# Award Utils
# ===========================================================================

function Get-Awards {
    param (
        [Parameter(Mandatory = $true)]
        [AllowNull()]
        [array]$regularSeasonStandings,
        [Parameter(Mandatory = $true)]
        [AllowNull()]
        [array]$playoffsStandings,
        [Parameter(Mandatory = $true)]
        [AllowNull()]
        $previousSeasonStandings
    )

    # Award Arten aufbauen
    $awardTypes = @{
        Special = [PSCustomObject]@{
            Name = "Special"
            DisplayText = "Special"
            Order = 1
        }
        RegularSeason = [PSCustomObject]@{
            Name = "RegularSeason"
            DisplayText = "Regular Season"
            Order = 2
        }
    }

    # Awards aufbauen
    $awards = @()
    if(-not $regularSeasonStandings){
        return $awards
    }

    #===================================#
    # Unabhängige Regular Season Awards #
    #===================================#

    # Regular Season King
    $king = $regularSeasonStandings | Sort-Object Place | Select-Object -First 1
    $awards += [PSCustomObject]@{
        Name            = "Regular Season King"
        Type            = $awardTypes['Special']
        IconUnicode     = "1F451" #👑
        StatDisplay     = "Record: ($($king.Wins)-$($king.Losses)-$($king.Ties)) | Points: $($king.Points)"
        TeamID          = $king.TeamID
        Owner           = $king.Owner
        TeamName        = $king.TeamName
    }

    # Best Performer
    $bestPerformer = $regularSeasonStandings | Sort-Object Points -Descending | Select-Object -First 1
    $awards += [PSCustomObject]@{
        Name            = "Best Performer"
        Type            = $awardTypes['RegularSeason']
        IconUnicode     = "1F525" #🔥
        StatDisplay     = "Points: $($bestPerformer.Points) | Points per Game: $($bestPerformer.PointsPerGame)"
        TeamID          = $bestPerformer.TeamID
        Owner           = $bestPerformer.Owner
        TeamName        = $bestPerformer.TeamName
    }

    # Streaker
    $streaker = $regularSeasonStandings | Sort-Object WinStreakScore -Descending | Select-Object -First 1
    $awards += [PSCustomObject]@{
        Name            = "Streaker"
        Type            = $awardTypes['RegularSeason']
        IconUnicode     = "26A1" #⚡
        StatDisplay     = "Longest Streak: $($streaker.LongestWinStreak) Wins | Record: $($streaker.Record)"
        TeamID          = $streaker.TeamID
        Owner           = $streaker.Owner
        TeamName        = $streaker.TeamName
    }

    # Overperformer
    $overperformer = $regularSeasonStandings | Sort-Object EfficiencyScore -Descending | Select-Object -First 1
    $awards += [PSCustomObject]@{
        Name            = "Overperformer"
        Type            = $awardTypes['RegularSeason']
        IconUnicode     = "1F680" #🚀
        StatDisplay     = "Point Difference: $($overperformer.PointDifference) | Wins: $($overperformer.Wins)"
        TeamID          = $overperformer.TeamID
        Owner           = $overperformer.Owner
        TeamName        = $overperformer.TeamName
    }

    # Brick Wall
    $ironWill = $regularSeasonStandings | Sort-Object IronWillScore -Descending | Select-Object -First 1
    $awards += [PSCustomObject]@{
        Name            = "Brick Wall"
        Type            = $awardTypes['RegularSeason']
        IconUnicode     = "1F9F1" #🧱
        StatDisplay     = "Points Against per Game: $($ironWill.PointsAgainstPerGame) | League Difference: $($ironWill.PointsAgainstPerGameDiffLeagueAvg) | Wins: $($ironWill.Wins))"
        TeamID          = $ironWill.TeamID
        Owner           = $ironWill.Owner
        TeamName        = $ironWill.TeamName
    }

    #=========================================#
    # Playoff-abhängige Regular Season Awards #
    #=========================================#
    if($playoffsStandings){

        # Mapping: Teams zwischen Playoffs und Regular Season matchen (über TeamID)
        $playoffsByTeamId = @{}
        if ($playoffsStandings) {
            foreach ($team in $playoffsStandings) {
                $playoffsByTeamId[$team.TeamID] = $team
            }
        }

        # Clutch Peaker
        ###############
        #Score Berechnung
        foreach ($team in $regularSeasonStandings) {
            $playoffTeam = $playoffsByTeamId[$team.TeamID]

            if ($playoffTeam) {
                # Verbesserung = wie viele Plätze gutgemacht
                $placeDiff = $team.Place - $playoffTeam.Place

                # Score (mit kleinem Tiebreaker)
                $score = $placeDiff - ($playoffTeam.Place * 0.01)
            } else {
                # Nicht in den Playoffs → hart bestrafen
                $score = -999
            }
            $team | Add-Member -NotePropertyName ClutchPeakerScore -NotePropertyValue $score -Force
        }
        # Award-Vergabe
        $clutchPeaker = $regularSeasonStandings | Sort-Object ClutchPeakerScore -Descending | Select-Object -First 1
        $playoffTeam = $playoffsByTeamId[$clutchPeaker.TeamID]
        $awards += [PSCustomObject]@{
            Name            = "Clutch Peaker"
            Type            = $awardTypes['Special']
            IconUnicode     = "1F3AF" #🎯
            StatDisplay     = "Regular Season: $($clutchPeaker.PlaceOrdinal) | Playoffs: $($playoffTeam.PlaceOrdinal)"
            TeamID          = $clutchPeaker.TeamID
            Owner           = $clutchPeaker.Owner
            TeamName        = $clutchPeaker.TeamName
        }
    }    

    #===========================================#
    # Vorsaison-abhängige Regular Season Awards #
    #===========================================#
    if($previousSeasonStandings){

        # Mapping: Teams zwischen Seasons matchen (über TeamID)
        $previousByTeamId = @{}
        if ($previousSeasonStandings -and $previousSeasonStandings.RegularSeason) {
            foreach ($team in $previousSeasonStandings.RegularSeason) {
                $previousByTeamId[$team.TeamID] = $team
            }
        }

        # Most Improved
        ###############
        # Score Berechnung
        foreach ($team in $regularSeasonStandings) {
            $prev = $previousByTeamId[$team.TeamID]

            if ($prev) {
                $team | Add-Member -NotePropertyName ImprovementScore -NotePropertyValue (
                    [Math]::Round(($team.WinPercentage - $prev.WinPercentage) + (($team.PointsPerGame - $prev.PointsPerGame) * 0.01), 4)
                )
            } else {
                # neues Team → leicht bestrafen oder neutral
                $team | Add-Member -NotePropertyName ImprovementScore -NotePropertyValue 0
            }
        }
        # Award-Vergabe        
        $mostImproved = $regularSeasonStandings | Where-Object { $null -ne $_.ImprovementScore } | Sort-Object ImprovementScore -Descending | Select-Object -First 1
        $prev = $previousByTeamId[$mostImproved.TeamID]
        if (-not $prev) {
            $prevWins = "N/A"
            $prevPoints = "N/A"
        } else {
            $prevWins = $prev.Wins
            $prevPoints = $prev.Points
        }
        $awards += [PSCustomObject]@{
            Name            = "Most Improved"
            Type            = $awardTypes['RegularSeason']
            IconUnicode     = "1F4AA" #💪
            StatDisplay     = "Wins: $($prevWins) to $($mostImproved.Wins) | Points: $($prevPoints) to $($mostImproved.Points)"
            TeamID          = $mostImproved.TeamID
            Owner           = $mostImproved.Owner
            TeamName        = $mostImproved.TeamName
        }

    }
    

    return $awards
}

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
        [array]$standingsRegularSeason,
        [array]$awards
    )

    $output = [PSCustomObject][ordered]@{
        Season = $season
        Playoffs = $standingsPlayoffs
        RegularSeason = $standingsRegularSeason
        Awards = $awards
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