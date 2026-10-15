# --- Funktionen ---

function PlayersHaveChanged($oldPlayers, $newPlayers) {
    Compare-Players -OldPlayers $oldPlayers -NewPlayers $newPlayers
}

function Convert-StringToDate($dateStr) {
    [datetime]::ParseExact($dateStr, 'yyyyMMdd', $null)
}

function MapSalaryToDollarsLinear {
    param (
        [double]$salary,
        [double]$salarySourceMin,
        [double]$salarySourceMax,
        [double]$salaryTargetMin,
        [double]$salaryTargetMax
    )
    # Linear skalieren, auch über $salarySourceMax hinaus
    $factor = ($salary - $salarySourceMin) / ($salarySourceMax - $salarySourceMin)
    return $salaryTargetMin + $factor * ($salaryTargetMax - $salaryTargetMin)
}

function MapSalaryToDollarsNonLinear {
    param (
        [double]$salary,
        [double]$salarySourceMin,
        [double]$salarySourceMax,
        [double]$salaryTargetMin,
        [double]$salaryTargetMax
    )
    $k = 2  # Quadratische Skalierung

    # Normalisieren relativ zum SourceMax, nicht clampen
    $normalized = ($salary - $salarySourceMin) / ($salarySourceMax - $salarySourceMin)
    $scaled = [math]::Pow([math]::Max($normalized, 0), $k)  # negatives clampen auf 0

    # Über SourceMax hinaus extrapolieren
    if ($normalized -gt 1) {
        $scaled = 1 + (($normalized - 1) * $k)   # Extrapolation
    }

    return $salaryTargetMin + $scaled * ($salaryTargetMax - $salaryTargetMin)
}

function MapSalaryToDollars {
    param (
        [double]$salary
    )

    # === Parameter-Bereich ===
    $salarySourceMin = 0    
    $salarySourceMax = 8000
    $salaryTargetMin = 250000
    $salaryTargetMax = 50000000
    $salaryMappingNonLinear = $true   # oder $false für lineare Skalierung

    # Salary holen (linear oder non-linear)
    if ($salaryMappingNonLinear) {
        $salaryFlat = MapSalaryToDollarsNonLinear -salary $salary -salarySourceMin $salarySourceMin -salarySourceMax $salarySourceMax -salaryTargetMin $salaryTargetMin -salaryTargetMax $salaryTargetMax
    } else {
        $salaryFlat = MapSalaryToDollarsLinear -salary $salary -salarySourceMin $salarySourceMin -salarySourceMax $salarySourceMax -salaryTargetMin $salaryTargetMin -salaryTargetMax $salaryTargetMax
    }

    # Runden auf ganze Dollar
    return [math]::Round($salaryFlat)
}

function Get-FantasySalaryWithFloor {
    param(
        [double]$pts1,
        [double]$pts2,
        [double]$pts3,
        [double]$weight1 = 0.5,   # Gewicht, wenn pts1 das Maximum ist
        [double]$weight2 = 0.33,  # Gewicht, wenn pts2 das Maximum ist
        [double]$weight3 = 0.17   # Gewicht, wenn pts3 das Maximum ist
    )

    # --- Spezialfall: Wenn die zwei neuesten Werte 0 sind, Salary = 0 ---
    if ($pts1 -eq 0 -and $pts2 -eq 0) {
        return 0
    }

    # --- Bestimmen, welches Jahr (Punktwert) das Maximum hat ---
    if ($pts1 -ge $pts2 -and $pts1 -ge $pts3) {
        $floorRatio = $weight1
        $maxVal = $pts1
    }
    elseif ($pts2 -ge $pts1 -and $pts2 -ge $pts3) {
        $floorRatio = $weight2
        $maxVal = $pts2
    }
    else {
        $floorRatio = $weight3
        $maxVal = $pts3
    }

    # --- Floor berechnen: gewichteter Anteil des Maximums ---
    $floor = [double]($maxVal * $floorRatio)

    # --- Floor anwenden (kein Wert darf unterhalb des Floors liegen) ---
    $pts1 = [Math]::Max($pts1, $floor)
    $pts2 = [Math]::Max($pts2, $floor)
    $pts3 = [Math]::Max($pts3, $floor)

    # --- Salary berechnen (Durchschnitt der drei gefloorten Werte) ---
    return MapSalaryFantasy -salary (($pts1 + $pts2 + $pts3) / 3)
}


function MapSalaryFantasy {
    param (
        [double]$salary
    )

    # === Parameter-Bereich ===
    $salarySourceMin = 0    
    $salarySourceMax = 20
    $salaryTargetMin = 0
    $salaryTargetMax = 50000000
    $salaryMappingNonLinear = $true   # oder $false für lineare Skalierung

    # Salary holen (linear oder non-linear)
    if ($salaryMappingNonLinear) {
        $salaryFlat = MapSalaryToDollarsNonLinear -salary $salary -salarySourceMin $salarySourceMin -salarySourceMax $salarySourceMax -salaryTargetMin $salaryTargetMin -salaryTargetMax $salaryTargetMax
    } else {
        $salaryFlat = MapSalaryToDollarsLinear -salary $salary -salarySourceMin $salarySourceMin -salarySourceMax $salarySourceMax -salaryTargetMin $salaryTargetMin -salaryTargetMax $salaryTargetMax
    }

    # Runden auf ganze Dollar
    return [math]::Round($salaryFlat)
}

function GetDeterministicRandom {
    param(
        [Parameter(Mandatory=$true)]
        [string]$playerID,
        [int]$min = 1,
        [int]$max = 100
    )

    # Hash aus der Spieler-ID erzeugen (alle Bytes nutzen!)
    $hashBytes = [System.Security.Cryptography.MD5]::Create().ComputeHash(
        [System.Text.Encoding]::UTF8.GetBytes($playerID)
    )

    $hashInt = 0
    foreach ($b in $hashBytes) {
        $hashInt = ($hashInt * 31 + $b) -band 0x7FFFFFFF
    }

    $rand = New-Object System.Random $hashInt
    return $rand.Next($min, $max + 1)
}

function GetFallbackSalary {
    param (
        [double]$salary,
        [string]$position,
        [int]$playerID
    )

    # Wenn Salary gültig ist, gib direkt zurück
    if ($salary -gt 0) {
        return [math]::Round($salary)
    }

    # Fallback bei Salary = 0
    switch ($position.ToUpper()) {
        "QB" { $salary = GetDeterministicRandom -playerID $playerID -min 600 -max 750}
        "RB" { $salary = GetDeterministicRandom -playerID $playerID -min 300 -max 600 }
        "WR" { $salary = GetDeterministicRandom -playerID $playerID -min 300 -max 600 }
        "TE" { $salary = GetDeterministicRandom -playerID $playerID -min 100 -max 300 }
        "K"  { $salary = GetDeterministicRandom -playerID $playerID -min 250 -max 750 }
        default { $salary = 0 }
    }

    return [math]::Round($salary)
}

function AdjustSalaryWithMeta {
    param (
        [double]$salaryCurrent,
        [double]$salarySeasonStart,
        [int]$year,
        [int]$age,
        [string]$position,
        [int]$playerID
    )

    # Standardwerte
    $adjustedCurrent = GetFallbackSalary -salary $salaryCurrent -position $position -playerID $playerID
    $adjustedSeason  = GetFallbackSalary -salary $salarySeasonStart -position $position -playerID $playerID

    # === Spezialfälle vorab ===

    # Fall 1: Beide Werte identisch und in bestimmten Stufen
    if ($salaryCurrent -eq $salarySeasonStart) {
        switch ($salaryCurrent) {
            2500 {
                $adjustedCurrent = 1500
                $adjustedSeason  = 1500
            }
            3000 {
                $adjustedCurrent = 2000
                $adjustedSeason  = 2000
            }
            4000 {
                $adjustedCurrent = 2500
                $adjustedSeason  = 2500
            }
        }
    }

    # === Allgemeine Anpassungen ===

    # Salary unter 0 initial anpassen
    if ($adjustedCurrent -le 0) {
        $adjustedCurrent = GetDeterministicRandom -playerID $playerID -min 1 -max 100
    }
    if ($adjustedSeason -le 0) {
        $adjustedSeason = GetDeterministicRandom -playerID $playerID -min 1 -max 100
    }

    # Erfahrungsbonus: pro Jahr in der Liga +50 Punkte
    $adjustedCurrent += ($year - 1) * 50
    $adjustedSeason  += ($year - 1) * 50

    # Altersmalus: pro Jahr über 29 -100 Punkte
    if ($age -gt 29) {
        $adjustedCurrent -= ($age - 29) * 0
        $adjustedSeason  -= ($age - 29) * 100
    }

    # Kicker-Bonus: pro Jahr in der Liga +125 Punkte
    if ($position -eq "K") {
        $adjustedCurrent += $year * 125
        $adjustedSeason  += $year * 125
    }

    # Wert unter 0 verhindern
    if ($adjustedCurrent -le 0) {
        $adjustedCurrent = GetDeterministicRandom -playerID $playerID -min 1 -max 100
    }
    if ($adjustedSeason -le 0) {
        $adjustedSeason = GetDeterministicRandom -playerID $playerID -min 1 -max 100
    }

    # Gerundet zurückgeben
    return @(
        [math]::Round($adjustedCurrent),
        [math]::Round($adjustedSeason)
    )
}

function Get-SeasonPointStats {

    param (
        $playerSeason,
        [int]$lastScoredWeek
    )

    $result = [ordered]@{
        Total               = 0.0
        AvgGame             = 0.0
        AvgPotentialGame    = 0.0
        GamesPlayed         = 0
        PotentialGames      = 0
    }

    if (-not $playerSeason -or -not $playerSeason.Games) {
        return $result
    }

    # --- alle Spiele der Saison, die gescored werden (dafür die lastScoredWeek nutzen)
    # --- und nur Spiele mit SnapCount > 0
    $games = $playerSeason.Games | Where-Object { $_.SnapCount -gt 0 -and $_.GameDetails.Week -le $lastScoredWeek }

    # --- PotentialGames: alle Spiele der Season
    $result.PotentialGames = $lastScoredWeek - 1

    $result.GamesPlayed = $games.Count

    if ($games.Count -gt 0) {

        $result.Total = [math]::Round(
            ($games | Measure-Object FantasyPoints -Sum).Sum,
            2
        )

        $result.AvgGame = [math]::Round(
            $result.Total / $result.GamesPlayed,
            2
        )
    }

    if ($result.PotentialGames -gt 0) {
        $result.AvgPotentialGame = [math]::Round(
            $result.Total / $result.PotentialGames,
            2
        )
    }

    return $result
}


# --- Konfiguration ---
Import-Module "$PSScriptRoot\utils\ConfigUtils.psm1" -ErrorAction Stop -Force
Import-Module "$PSScriptRoot\utils\player\PlayerUtils.psm1" -ErrorAction Stop -Force
Import-Module "$PSScriptRoot\utils\general\NflScheduleUtils.psm1" -ErrorAction Stop -Force
Import-Module "$PSScriptRoot\utils\player\PlayerLeagueScoringUtils.psm1" -ErrorAction Stop -Force
Import-Module "$PSScriptRoot\utils\player\SleeperPlatformUtils.psm1" -ErrorAction Stop -Force
Import-Module "$PSScriptRoot\utils\player\PlayerPopulationUtils.psm1" -ErrorAction Stop -Force
Import-Module "$PSScriptRoot\utils\player\PlayerValuationUtils.psm1" -ErrorAction Stop -Force
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$targetFile = Join-Path $scriptDir "..\data\Players.json"
$backupDir = Join-Path $scriptDir "..\data\backup"
if (!(Test-Path $backupDir)) { New-Item -ItemType Directory -Path $backupDir -Force | Out-Null }
$errorsFile = Join-Path $scriptDir "..\data\Errors.json"

# --- Season (League source manifest) und Gewichtungen (ConfigUtils.psm1) ---
try {
    $config = Get-Config
}
catch {
    Write-Error "Error loading configuration: $_"
    exit 1
}
if (-not $config.LeagueYear) {
    Write-Error "LeagueYear not resolved from the league source manifest!"
    exit 1
}
$seasonYear = $config.LeagueYear

if (-not $config.WeightTotal -or -not $config.WeightGame) {
    Write-Error "Weights not set in ConfigUtils.psm1!"
    exit 1
}
$weightTotal = $config.WeightTotal
$weightGame = $config.WeightGame

try {
    $weekBounds = Get-PlayerLeagueWeekBounds -Season ([int]$seasonYear)
} catch {
    Write-Error "Error resolving canonical league week bounds: $_"
    exit 1
}
$lastWeek = [int]$weekBounds.LastLeagueWeek
$playoffStartWeek = [int]$weekBounds.PlayoffStartWeek
$finalWeek = [int]$weekBounds.FinalScoredWeek
Write-Host "Loaded last week (Week $($lastWeek)) from canonical WeekStructure..." -ForegroundColor Yellow
Write-Host "Loaded playoff start week (Week $($playoffStartWeek)) from canonical WeekStructure..." -ForegroundColor Yellow
Write-Host "Loaded final week (Week $($finalWeek)) from canonical game finality..." -ForegroundColor Yellow

# --- Population und Plattformfelder aus dem kanonischen Source-Data (#347 H1b) ---
# Fantasy-Management-Regel (NFL-Roster/-Draft der Saison oder Liga-Besitz), Team/Status/Profil aus dem
# kanonischen Sleeper-Snapshot ueber die Team-Registry. Kein Tank01- und kein Live-Sleeper-Aufruf.
Write-Host "Build population from canonical source data..." -ForegroundColor Yellow
try {
    $population = Invoke-PlayerPopulationExport -Season ([int]$seasonYear) -RepoRoot (Split-Path -Parent (Split-Path -Parent $scriptDir))
} catch {
    Write-Error "Error building the Players population: $_"
    exit 1
}
if ($population.RosterBasis.UsedPreviousSeasonRoster) {
    Write-Warning "Season roster $($population.RosterBasis.Season) not yet published; population uses the $($population.RosterBasis.RosterSeason) roster."
}
Write-Host "Population players: $($population.Players.Count)" -ForegroundColor Yellow

# --- Sleeper Depth Charts aus dem kanonischen Plattform-Snapshot (#347 H4) ---
$sleeperDepthCharts = Get-CanonicalSleeperDepthCharts -RepoRoot (Split-Path -Parent (Split-Path -Parent $scriptDir))
Write-Host "Canonical Sleeper depth chart records: $($sleeperDepthCharts.Count)" -ForegroundColor Yellow
$depthChartMissingPlayers = @()

# --- Spieler JSON vorbereiten ---
Write-Host "Creating Players.json..." -ForegroundColor Yellow

# Alte Spieler laden (für Vergleich und evtl. Gehälter)
$oldPlayersLookup = @{}
$oldPlayers = $null
if (Test-Path $targetFile) {
    $oldJsonRaw = Get-Content $targetFile -Raw
    if ($oldJsonRaw) { 
        $oldPlayers = ($oldJsonRaw | ConvertFrom-Json)
        # Lookup für schnellen Zugriff
        foreach ($p in $oldPlayers) {
            $oldPlayersLookup[$p.ID] = $p
        }
    }
}


# Team → ByeWeek mapping aus dem kanonischen NFL-Spielplan (nicht aus bereits gespielten Games)
$teamByeWeek = Get-CanonicalNflTeamByeWeeks -Season ([int]$seasonYear) -RepoRoot (Split-Path -Parent (Split-Path -Parent $scriptDir))
Write-Host "Loaded bye weeks for $($teamByeWeek.Count) teams from canonical NFL schedule..." -ForegroundColor Yellow


# --- League scoring (#347 D4): canonical NFL stats scored with the league ScoringSettings ---
# Replaces Tank01 PPR points and the Tank01 past_seasons archives. The export is keyed by Sleeper player ID.
$leagueScoringSleeperIDs = @($population.Players | ForEach-Object { [string]$_.SleeperID })
$leagueScoringExport = Invoke-PlayerLeagueScoringExport -SleeperIDs $leagueScoringSleeperIDs -Season ([int]$seasonYear)
if ([int]$leagueScoringExport.Season -ne [int]$seasonYear) {
    throw "League scoring export season $($leagueScoringExport.Season) does not match LeagueYear $seasonYear."
}
$identityHoldPlayers = @()

# --- PlayerValuation (#919 step 5): Salary, Ranking, Grading come from the central models ---
# The materializer seeds identity-hold rows from the Players.json published so far; the snapshot of the final
# scored week is then the only source of Salary, SalaryProjected, Ranking and the Rank grading.
try {
    Invoke-PlayerValuationMaterialize -HoldSeedPlayersFile $targetFile
    $valuation = Get-PlayerValuationSnapshotForWeek -CanonicalLeagueID $config.CanonicalLeagueID -Season ([int]$seasonYear) -Week $finalWeek
} catch {
    Write-Error "Error building the PlayerValuation snapshot: $_"
    exit 1
}
Write-Host "PlayerValuation snapshot: $($valuation.Snapshot.Models.Salary), week $finalWeek, $($valuation.Rows.Count) rows." -ForegroundColor Yellow

$playerData = @()
foreach ($entry in $population.Players) {
    $position = [string]$entry.Position
    if (-not $position) { continue }

    # --- PlayerID ---
    $playerID = [string]$entry.SleeperID
    # --- Year berechnen ---
    $year = $entry.YearsExp + 1
    # --- Team (kanonisches Kuerzel oder $null ohne NFL-Team) ---
    $team = $entry.TeamAbbr

    # --- Age ---
    $age = $null
    if ($entry.BirthDate) {
        try {
            $birthDate = [datetime]::ParseExact(
                $entry.BirthDate,
                "yyyy-MM-dd",
                [System.Globalization.CultureInfo]::InvariantCulture
            )

            $age = [double]([math]::Round(
                ((Get-Date).Date - $birthDate.Date).TotalDays / 365.2425,
                1
            ))
        }
        catch {
            $age = $null
        }
    }

    # Spieler ohne gültiges Alter komplett ignorieren
    if ($null -eq $age) {
        continue
    }

    # --- Bye-Week bestimmen
    $canonicalTeam = ConvertTo-CanonicalNflScheduleTeam -Team $team
    $byeWeek = if ($canonicalTeam -and $teamByeWeek.ContainsKey($canonicalTeam)) { $teamByeWeek[$canonicalTeam] } else { 0 }

    # --- Free Agency Status: NFL-Free-Agency (kein Sleeper-Team), nicht Fantasy-Verfuegbarkeit ---
    $freeAgent = [bool]$entry.IsFreeAgent

    # --- Injury aus dem kanonischen Sleeper-Snapshot (#347 Decision 6), ReturnDate unbekannt ---
    $injuryResult = ConvertTo-PlayerInjuryDetails -Injury $entry.Injury
    $injured = $injuryResult.Injured
    $injury = $injuryResult.Details


    # --- Player Stats: Spiele, Punkte und Spielzahlen aus den kanonischen NFL-Fakten (#347 G3, D4) ---
    $leagueScoring = $leagueScoringExport.Players[[string]$playerID]
    $gameHistory = @()
    if ($leagueScoring -and $leagueScoring.Status -eq 'resolved') {
        $gameHistory = @(ConvertTo-PlayerGameHistory -Entries $leagueScoring.GameHistory -PlayoffStartWeek $playoffStartWeek -LastLeagueWeek $lastWeek)
    } elseif ($oldPlayersLookup.ContainsKey([string]$playerID) -and $oldPlayersLookup[[string]$playerID].GameHistory) {
        # Identity hold: keep the last published games together with the other held values.
        $gameHistory = @($oldPlayersLookup[[string]$playerID].GameHistory)
    }

    # --- Potentielle Spiele berechnen (ByeWeek berücksichtigen) ---
    $gamesPotential = 0
    if ($gameHistory.Count -gt 0) {
        $gamesPotential = $finalWeek
        if($byeWeek -le $finalWeek){
            $gamesPotential--
        }
    }

    if ($leagueScoring -and $leagueScoring.Status -eq 'resolved') {
        $currentRows = $leagueScoring.Seasons[[string]$seasonYear]
        $current = Get-PlayerLeagueScoringCurrentStats -SeasonRows $currentRows -Position $position -LastWeek $lastWeek -GamesPotential $gamesPotential
        $pointHistory = [ordered]@{
            SeasonMinus1 = Get-PlayerLeagueScoringSeasonStats -SeasonRows $leagueScoring.Seasons[[string]($seasonYear - 1)] -Position $position -LastWeek $lastWeek
            SeasonMinus2 = Get-PlayerLeagueScoringSeasonStats -SeasonRows $leagueScoring.Seasons[[string]($seasonYear - 2)] -Position $position -LastWeek $lastWeek
            SeasonMinus3 = Get-PlayerLeagueScoringSeasonStats -SeasonRows $leagueScoring.Seasons[[string]($seasonYear - 3)] -Position $position -LastWeek $lastWeek
        }
    } else {
        # Identity hold (no unique canonical identity for the current season): keep the last published values.
        $identityHoldPlayers += "$($entry.FullName) ($playerID)"
        $held = Get-PlayerLeagueScoringHeldStats -OldPlayer $oldPlayersLookup[[string]$playerID]
        $current = $held.Current
        $pointHistory = $held.PointHistory
    }

    $gamesPlayed = $current.GamesPlayed
    $snaps = $current.SnapsTotal
    $attempts = $current.AttemptsTotal
    $fantasyPointsTotal = $current.FantasyPointsTotal
    $fantasyPointsAvgGame = $current.FantasyPointsAvgGame
    $fantasyPointsAvgPotentialGame = $current.FantasyPointsAvgPotentialGame
    $fantasyPointsAvgSnap = $current.FantasyPointsAvgSnap
    $fantasyPointsAvgAttempt = $current.FantasyPointsAvgAttempt
    $tdTotal = $current.TouchdownsTotal
    $tdRush = $current.TouchdownsRushing
    $tdRec = $current.TouchdownsReceiving
    $tdPass = $current.TouchdownsPassing

    # --- Salary, Ranking und Rank-Grading aus dem PlayerValuation-Snapshot (#919 step 5) ---
    $valuationRow = $valuation.Rows[[string]$playerID]
    if (-not $valuationRow) {
        throw "PlayerValuation snapshot lacks Sleeper player $playerID ($($entry.FullName)); population and snapshot diverge."
    }
    $valuationValues = Get-PlayerValuationPlayerValues -Row $valuationRow


    # ----------------------------------------------
    # --- Grading Werte setzen, die setzbar sind ---
    # ----------------------------------------------
    # Grading Objekt initialisieren
    $grading = @()

    # --- Average letzte vier gescorte Spiele für Form-Grading berechnen ---
    $formValue = @()
    $formValue = $gameHistory | 
        Where-Object { $_.GameDetails.WeekFinal -and $_.GameDetails.WeekScored } |
        Select-Object -First 4
    
    $form = [PSCustomObject]@{
        Type = "Form"
        Value = $formValue
    }

    $grading += $form


    # Depth chart: canonical snapshot; a player not yet in the snapshot stays unknown (null), never guessed.
    $depthChart = $sleeperDepthCharts[[string]$playerID]
    if (-not $depthChart) {
        $depthChart = @{ Position = $null; Order = $null }
        $depthChartMissingPlayers += "$($entry.FullName) ($playerID)"
    }

    # --- Player Objekt bauen ---
    $playerData += [PSCustomObject]@{
        ID                           = $playerID
        Name                         = $entry.FullName
        NameFirst                    = $entry.FirstName
        NameLast                     = $entry.LastName
        NameShort                    = $entry.NameShort
        TeamID                       = $entry.TeamID
        TeamAbbr                     = $entry.TeamAbbr
        ByeWeek                      = $byeWeek
        Status                       = $entry.Status
        IsFreeAgent                  = $freeAgent
        Position                     = $position
        Age                          = $age
        Year                         = $year
        Number                       = if ($null -ne $entry.Number) { [string]$entry.Number } else { "" }
        Salary                       = $valuationValues.Salary
        SalaryProjected              = $valuationValues.SalaryProjected
        Picture                      = $entry.Picture
        PictureLarge                 = $entry.PictureLarge
        FantasyPros                  = $entry.FantasyPros
        ESPN                         = $entry.ESPN
        SleeperDepthChartPosition    = $depthChart.Position
        SleeperDepthChartOrder       = $depthChart.Order
        College                      = $entry.College
        HighSchool                   = $entry.HighSchool
        Injured                      = $injured
        InjuryDetails                = $injury
        GamesPlayed                  = $gamesPlayed
        GamesPotential               = $gamesPotential
        SnapsTotal                   = $snaps
        AttemptsTotal                = $attempts
        FantasyPointsTotal           = $fantasyPointsTotal
        FantasyPointsAvgGame         = $fantasyPointsAvgGame
        FantasyPointsAvgPotentialGame = $fantasyPointsAvgPotentialGame
        FantasyPointsAvgSnap         = $fantasyPointsAvgSnap
        FantasyPointsAvgAttempt      = $fantasyPointsAvgAttempt
        Ranking                      = $valuationValues.Ranking
        Grading                      = $grading + $valuationValues.RankGrading
        PointHistory                 = $pointHistory
        TouchdownsTotal              = $tdTotal
        TouchdownsPassing            = $tdPass
        TouchdownsReceiving          = $tdRec
        TouchdownsRushing            = $tdRush
        GameHistory                  = $gameHistory
    }
}

if ($depthChartMissingPlayers.Count -gt 0) {
    Write-Warning "Depth chart unknown (player not yet in the canonical Sleeper snapshot) for $($depthChartMissingPlayers.Count) players: $($depthChartMissingPlayers -join ', ')"
}
if ($identityHoldPlayers.Count -gt 0) {
    Write-Warning "League scoring identity hold: kept the last published scoring values for $($identityHoldPlayers.Count) players: $($identityHoldPlayers -join ', ')"
}

# Spieler nach ID aufsteigend sortieren
$playerData = $playerData | Sort-Object -Property ID



# Ranking und Rank-Grading stammen aus dem PlayerValuation-Snapshot (#919 step 5); keine Berechnung hier.

# Aus Errors.json EmptyPlayers-Error holen
$emptyPlayersError = $null
if (Test-Path $errorsFile) {        
    try {
        $errorsRaw = Get-Content $errorsFile -Raw
        $errors = $errorsRaw | ConvertFrom-Json
        $emptyPlayersError = $errors | Where-Object { $_.Type -eq 'EmptyPlayers' }
    } catch {
        Write-Error "Error reading Errors.json: $_"
        exit 1
    }
}
# Nun prüfen ob mindestens ein Spieler vorhanden ist
# Wenn nicht, dann prüfen ob EmptyPlayers true ist
# Wenn ja, dann Fehler werfen und Exit 1 (weil wiederholte leere Spieler)
# Wenn nein, dann Warnung ausgeben, aber Exit 0 (weil erstmal leere Spieler möglich) und EmptyPlayers auf true setzen
# Wenn Spieler vorhanden sind, dann EmptyPlayers auf false setzen (weil erfolgreich Spieler geladen)
if ($playerData.Count -eq 0) {
    if ($emptyPlayersError -and $emptyPlayersError.Value -eq $true) {
        Write-Error "No players found and EmptyPlayers error already set. Exiting with error."
        exit 1
    } else {
        Write-Warning "No players found. Setting EmptyPlayers error for next run."
        $newError = [PSCustomObject]@{ Type = 'EmptyPlayers'; Value = $true }
        if ($errors) {
            # Fehler aktualisieren oder hinzufügen
            $existingError = $errors | Where-Object { $_.Type -eq 'EmptyPlayers' }
            if ($existingError) {
                $existingError.Value = $true
            } else {
                $errors += $newError
            }
        } else {
            # Neue Fehlerliste erstellen
            $errors = @($newError)
        }
        # Fehlerliste speichern
        $errors | ConvertTo-Json -Depth 3 | Set-Content $errorsFile
        exit 0
    }
} else {
    # Spieler gefunden, EmptyPlayers Fehler zurücksetzen, falls vorhanden
    if ($emptyPlayersError) {
        $emptyPlayersError.Value = $false
        # Fehlerliste aktualisieren
        $errors | ConvertTo-Json -Depth 3 | Set-Content $errorsFile
    }
}

# Änderungen prüfen
if (-not (PlayersHaveChanged $oldPlayers $playerData)) {
    Write-Host "No changes - update skipped." -ForegroundColor Cyan
    exit 0
}

# --- Zeitstempel ---
$TimeSnapshot = (Get-Date)

# --- Backup alte Datei ---
if (Test-Path $targetFile) {
    $timestamp = $TimeSnapshot.ToUniversalTime().ToString("yyyyMMdd_HHmmss")
    Copy-Item $targetFile -Destination (Join-Path $backupDir "Players_$timestamp.json") -Force
    Write-Host "Old Players.json backup created." -ForegroundColor Green
}

# --- JSON schreiben ---
try {
    $playerData | ConvertTo-Json -Depth (Get-PlayersPublishedJsonDepth) | Out-File $targetFile -Encoding UTF8
    Write-Host "Players.json saved!" -ForegroundColor Green
} catch {
    Write-Error "Error writing Players.json: $_"
    exit 1
}

# --- Timestamp aktualisieren ---
$TimestampFile = Join-Path $scriptDir "..\data\Timestamps.json"
$Now = $TimeSnapshot.ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
if (Test-Path $TimestampFile) {
    $Timestamps = Get-Content $TimestampFile | ConvertFrom-Json
} else { $Timestamps = @{} }
$Timestamps.Players = $Now
$Timestamps | ConvertTo-Json -Depth 3 | Set-Content $TimestampFile
Write-Host "Players-Timestamp updated: $Now" -ForegroundColor Green