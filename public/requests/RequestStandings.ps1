
# ===========================================================================
# 1. Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\utils\general\FileUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\CanonicalStandingUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\StandingUtils.psm1" -ErrorAction Stop -Force
}
catch {
    Write-Error "Fehler beim Laden der Module: $_"
    exit 1
}


# ===========================================================================
# 2. Globale Variablen und Konfiguration
# ===========================================================================


# ===========================================================================
# 3. Funktionen
# ===========================================================================

function Get-Compare {
    
    return {
        param($oldStandings, $newStandings)

        if (-not $oldStandings) { return $true }

        # Vergleiche Anzahl Seasons       
        if ($oldStandings.Count -ne $newStandings.Count) {
            Write-Host "Number of seasons changed: $($oldStandings.Count) -> $($newStandings.Count)"
            return $true
        }

        # Vergleiche jede Season einzeln
        for ($i = 0; $i -lt $oldStandings.Count; $i++) {
            $oldSeason = $oldStandings[$i]
            $newSeason = $newStandings[$i]

            if ($oldSeason.Season -ne $newSeason.Season) {
                Write-Host "Season name changed at index $($i): '$($oldSeason.Season)' -> '$($newSeason.Season)'"
                return $true
            }

            # Vergleiche Playoffs
            if (Compare-PlayoffStandings `
                -oldPlayoffs $oldSeason.Playoffs `
                -newPlayoffs $newSeason.Playoffs) {
                Write-Host "Playoff standings changed for season '$($oldSeason.Season)'."
                return $true
            }

            # Vergleiche Regular Season
            if (Compare-RegularSeasonStandings `
                -oldRegularSeason $oldSeason.RegularSeason `
                -newRegularSeason $newSeason.RegularSeason) {
                Write-Host "Regular season standings changed for season '$($oldSeason.Season)'."
                return $true
            }

            # Vergleiche Awards
            if (Compare-Awards `
                -oldAwards $oldSeason.Awards `
                -newAwards $newSeason.Awards) {
                Write-Host "Awards changed for season '$($oldSeason.Season)'."
                return $true
            }
        }

        return $false
    }
    
}


# ===========================================================================
# 4. Logik
# ===========================================================================

try {

    Write-Host "Starting to fetch and build standings data..." -ForegroundColor Yellow

    # Historical and current standings are rebuilt from Canonical League source-data.
    # Current inputs are refreshed by the bounded League Core producer before app consumers.
    $canonicalLeagueID = "nfl-reise"
    $historicalStandings = Get-CanonicalHistoricalStandings -CanonicalLeagueID $canonicalLeagueID
    $historicalSeasons = @($historicalStandings.Seasons)

    $previousSeasonStandings = $historicalSeasons |
        Sort-Object { [int]$_.Season } -Descending |
        Select-Object -First 1

    $currentSeasonData = Get-CanonicalCurrentSeasonData `
        -CanonicalLeagueID $canonicalLeagueID `
        -PreviousSeasonStandings $previousSeasonStandings

    if (@($historicalSeasons | Where-Object { [string]$_.Season -eq [string]$currentSeasonData.Output.Season }).Count -gt 0) {
        throw "Current standings season '$($currentSeasonData.Output.Season)' is also present in canonical historical standings."
    }

    $allSeasonData = @($historicalSeasons) + @($currentSeasonData.Output)
    $allSeasonCompletedData = @($historicalSeasons)
    if ($currentSeasonData.IsCompleted) {
        $allSeasonCompletedData += $currentSeasonData.Output
    }

    if (-not $allSeasonData -or $allSeasonData.Count -eq 0) {
        Write-Error "No season data available!"
        exit 1
    }

    # All Season Data sortieren (neueste Saison zuerst)
    $allSeasonData = $allSeasonData | Sort-Object -Property Season -Descending
    $allSeasonCompletedData = $allSeasonCompletedData | Sort-Object -Property Season -Descending

    # AllTime berechnen
    $allSeasonData += Get-OutputStandingsForAllTime -allSeasonStandings $allSeasonCompletedData

    # All Season Data sortieren (neueste Saison zuerst und AllTime am Start)
    # Sortierung nach Season als String, mit Descending ist AllTime an vorderster Stelle, danach die Jahre in absteigender Reihenfolge
    $allSeasonData = $allSeasonData | Sort-Object -Property Season -Descending

    # --- JSON schreiben ---
    Write-Host "Saving standings data to JSON..." -ForegroundColor Yellow
    $compare = & Get-Compare
    Save-JsonFile -Type "Standings" -Data $allSeasonData -CompareScript $compare -CreateBackup -UpdateTimestamp

    Write-Host "Standings.json successfully updated." -ForegroundColor Green

    exit 0
}
catch {
    Write-Error "An error occurred: $_"
    exit 1
}