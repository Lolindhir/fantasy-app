
# ===========================================================================
# Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\..\ConfigUtils.psm1" -ErrorAction Stop -Force
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
# Standings Product Utils
# ===========================================================================


# Consumer read of the league-standings product (Issue #987, ADR-072): the App-shaped standings are rendered from the
# persisted data-derived product by tools/league_standings_app_publish.py render, never read back from Standings.json.
# Fails closed (missing tool, product or output).
function Get-LeagueStandingsProduct {
    param(
        [Parameter(Mandatory = $true)][string]$CanonicalLeagueID,
        [Parameter(Mandatory = $true)][string]$RepoRoot
    )

    $toolPath = Join-Path $RepoRoot "tools/league_standings_app_publish.py"
    if (-not (Test-Path $toolPath)) {
        throw "League standings render tool missing at '$toolPath'."
    }

    $python = $null
    foreach ($name in @("python3", "python")) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($command) { $python = $command.Source; break }
    }
    if (-not $python) { throw "Python is required to render the league-standings product." }

    $output = & $python $toolPath --repo-root $RepoRoot render --league $CanonicalLeagueID 2>&1
    $exitCode = $LASTEXITCODE
    $outputText = (@($output) | ForEach-Object { [string]$_ }) -join [Environment]::NewLine
    if ($exitCode -ne 0) {
        throw "League standings render failed with exit code $exitCode. $outputText"
    }

    try {
        $standings = $outputText | ConvertFrom-Json
    }
    catch {
        throw "League standings render returned invalid JSON. $outputText"
    }
    $standings = @($standings)
    if ($standings.Count -eq 0) {
        throw "League standings product for '$CanonicalLeagueID' rendered no seasons."
    }
    return $standings
}
