
# ===========================================================================
# 1. Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\utils\general\FileUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\StandingUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\TeamUtils.psm1" -ErrorAction Stop -Force
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

function Get-SeasonDataRecursive {
    param(
        [string]$leagueID = (Get-Config).LeagueID,
        $accumulatedData = $null
    )

    # Initialisierung nur beim ersten Aufruf
    if (-not $accumulatedData) {
        $accumulatedData = [PSCustomObject]@{
            AllSeasons     = @()
            PreviousSeason = $null
        }
    }

    Write-Host "Fetching data for league ID $leagueID..." -ForegroundColor Cyan

    $league = Get-LeagueRaw -leagueID $leagueID
    $teamData = Get-Teams -leagueID $leagueID

    $standingsPreviousLeague = $null
    # Rekursiv weitere Seasons holen, falls vorhanden (Abbruch, wenn keine PreviousLeagueID mehr vorhanden ist)
    if ($league.previous_league_id -and $league.previous_league_id -ne "") {
        $accumulatedData = Get-SeasonDataRecursive -leagueID $league.previous_league_id -accumulatedData $accumulatedData
        $standingsPreviousLeague = $accumulatedData.PreviousSeason
    }

    #berechne Standings
    $standings = Get-StandingsRemote -leagueID $leagueID -teamData $teamData -regularSeasonGames ($league.settings.playoff_week_start - 1) -previousSeasonStandings $standingsPreviousLeague

    #bereite den Output der Standings vor
    $output = Get-OutputStandingsForSeason -season $league.season -standingsPlayoffs $standings.Playoffs -standingsRegular $standings.RegularSeason -awards $standings.Awards
    
    #baue accumulatedData
    $accumulatedData.AllSeasons += $output
    $accumulatedData.PreviousSeason = $output

    Write-Host "Fetched data for season $($league.season)." -ForegroundColor Cyan

    return $accumulatedData
}

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

    # Array mit allen Seasons holen
    $allSeasonData += (Get-SeasonDataRecursive).AllSeasons

    if (-not $allSeasonData -or $allSeasonData.Count -eq 0) {
        Write-Error "No season data available!"
        exit 1
    }

    # All Season Data sortieren (neueste Saison zuerst)
    $allSeasonData = $allSeasonData | Sort-Object -Property Season -Descending

    # AllTime berechnen
    $allSeasonData += Get-OutputStandingsForAllTime -allSeasonStandings $allSeasonData

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