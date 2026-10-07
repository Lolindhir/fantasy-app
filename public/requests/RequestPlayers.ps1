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
. "$PSScriptRoot\config.ps1"
Import-Module "$PSScriptRoot\utils\player\PlayerUtils.psm1" -ErrorAction Stop -Force
Import-Module "$PSScriptRoot\utils\general\NflScheduleUtils.psm1" -ErrorAction Stop -Force
Import-Module "$PSScriptRoot\utils\player\PlayerLeagueScoringUtils.psm1" -ErrorAction Stop -Force
Import-Module "$PSScriptRoot\utils\player\SleeperPlatformUtils.psm1" -ErrorAction Stop -Force
Import-Module "$PSScriptRoot\utils\player\PlayerPopulationUtils.psm1" -ErrorAction Stop -Force
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$targetFile = Join-Path $scriptDir "..\data\Players.json"
$backupDir = Join-Path $scriptDir "..\data\backup"
if (!(Test-Path $backupDir)) { New-Item -ItemType Directory -Path $backupDir -Force | Out-Null }
$errorsFile = Join-Path $scriptDir "..\data\Errors.json"

# --- Season aus config.ps1 ---
if (-not $Global:LeagueYear) {
    Write-Error "LeagueYear not set in config.ps1!"
    exit 1
}
$seasonYear = $Global:LeagueYear

# --- Gewichtungen aus config.ps1 ---
if (-not $Global:WeightTotal -or -not $Global:WeightGame) {
    Write-Error "Weights not set in config.ps1!"
    exit 1
}
$weightTotal = $Global:WeightTotal
$weightGame = $Global:WeightGame

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

    # --------------------------------------
    # --- Salaries aus Fantasy berechnen ---
    # --------------------------------------
    # Jahrespunkte berechnen
    $ptsCurrent = $fantasyPointsAvgPotentialGame * $weightTotal + $fantasyPointsAvgGame * $weightGame
    $ptsSeasonMinus1 = $pointHistory.SeasonMinus1.AvgPotentialGame  * $weightTotal + $pointHistory.SeasonMinus1.AvgGame * $weightGame
    $ptsSeasonMinus2 = $pointHistory.SeasonMinus2.AvgPotentialGame  * $weightTotal + $pointHistory.SeasonMinus2.AvgGame * $weightGame
    $ptsSeasonMinus3 = $pointHistory.SeasonMinus3.AvgPotentialGame  * $weightTotal + $pointHistory.SeasonMinus3.AvgGame * $weightGame
    # Vergangenheitswerte
    $salaryDollarsFantasy = Get-FantasySalaryWithFloor $ptsSeasonMinus1 $ptsSeasonMinus2 $ptsSeasonMinus3 #-weight1 0.5 -weight2 0.35 -weight3 0.25
    # Projektionswerte
    # Wenn aktuelle Saison vor Spieltag 1 liegt, dann ist ptsCurrent der Wert der letzten Saison, ansonsten die aktuelle Saison
    if($finalWeek -eq 0){
        $ptsCurrent = $ptsSeasonMinus1
    }
    if($finalWeek -eq 1){
        $ptsCurrent = $ptsCurrent * 0.25 + $ptsSeasonMinus1 * 0.75
    }
    if($finalWeek -eq 2){
        $ptsCurrent = $ptsCurrent * 0.35 + $ptsSeasonMinus1 * 0.65
    }
    if($finalWeek -eq 3){
        $ptsCurrent = $ptsCurrent * 0.5 + $ptsSeasonMinus1 * 0.5
    }
    if($finalWeek -eq 4){
        $ptsCurrent = $ptsCurrent * 0.75 + $ptsSeasonMinus1 * 0.25
    }
    $salaryDollarsProjectedFantasy = Get-FantasySalaryWithFloor $ptsCurrent $ptsSeasonMinus1 $ptsSeasonMinus2 #-weight1 0.5 -weight2 0.35 -weight3 0.25


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
        Salary                       = [math]::Round($salaryDollarsFantasy)
        SalaryProjected              = [math]::Round($salaryDollarsProjectedFantasy)
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
        Ranking                      = @()
        Grading                      = $grading
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



# --- Rankings hinzufügen ---
Write-Host "Calculating player rankings..." -ForegroundColor Yellow

function Add-Rankings {
    param (
        [Parameter(Mandatory)] [Array]$players,
        [string]$propTotal = 'FantasyPointsAvgPotentialGame',
        [string]$propAvg = 'FantasyPointsAvgGame',
        [double]$weightTotal = 0.5,   # Gewichtung Total
        [double]$weightAvg = 0.5      # Gewichtung PerGame
    )

    # Nur Spieler berücksichtigen, die überhaupt Werte haben
    $playersActive = $players | Where-Object { $_.$propTotal -gt 0 -and $_.$propAvg -gt 0 }

    # --- Helper: Ranking mit Sprüngen & Gleichständen ---
    function Set-Rankings($list, $type, $property) {
        $sorted = $list | Sort-Object -Property $property -Descending
        $prevValue = $null
        $rank = 0
        $i = 0

        foreach ($player in $sorted) {
            $i++
            $value = $player.$property
            if ($null -eq $value -or $value -eq 0) { continue }

            # Nur neuen Rang vergeben, wenn sich der Wert ändert
            if ($value -ne $prevValue) { $rank = $i }
            $prevValue = $value

            if (-not $player.PSObject.Properties["Ranking"]) {
                $player | Add-Member -NotePropertyName 'Ranking' -NotePropertyValue @()
            }

            $player.Ranking += [PSCustomObject]@{ Type = $type; Value = $rank }
        }
    }

    # --- Basis-Rankings ---
    Set-Rankings $playersActive 'Total' $propTotal
    Set-Rankings $playersActive 'PerGame' $propAvg

    # --- Combined Rank vorbereiten (Gewichtung über Ränge) ---
    foreach ($p in $playersActive) {
        $rankTotal = ($p.Ranking | Where-Object { $_.Type -eq 'Total' }).Value
        $rankAvg   = ($p.Ranking | Where-Object { $_.Type -eq 'PerGame' }).Value
        if ($null -ne $rankTotal -and $null -ne $rankAvg) {
            $combinedValue = ($rankTotal * $weightTotal) + ($rankAvg * $weightAvg)
            $p | Add-Member -NotePropertyName 'CombinedRankValue' -NotePropertyValue $combinedValue -Force
        }
    }

    # --- Combined Ranking mit Tiebreaks ---
    $combinedList = $playersActive | Where-Object { $_.CombinedRankValue -gt 0 } |
        Sort-Object -Property @{Expression = 'CombinedRankValue'; Ascending = $true},
                               @{Expression = $propTotal; Ascending = $false},
                               @{Expression = $propAvg; Ascending = $false}

    $prevValue = $null
    $rank = 0
    $i = 0
    foreach ($p in $combinedList) {
        $i++
        $value = $p.CombinedRankValue

        # Gleichstand -> gleicher Rang, Sprung danach
        if ($value -ne $prevValue) { $rank = $i }
        $prevValue = $value

        if (-not $p.PSObject.Properties["Ranking"]) {
            $p | Add-Member -NotePropertyName 'Ranking' -NotePropertyValue @()
        }
        $p.Ranking += [PSCustomObject]@{ Type = 'Combined'; Value = $rank }
    }

    # --- Positions-Rankings ---
    $positions = $playersActive | Select-Object -ExpandProperty Position -Unique
    foreach ($pos in $positions) {
        $posPlayers = $playersActive | Where-Object { $_.Position -eq $pos }

        # Positionsbasierte Rankings
        Set-Rankings $posPlayers "Total_Pos" $propTotal
        Set-Rankings $posPlayers "PerGame_Pos" $propAvg

        # Kombinierter Positionswert
        foreach ($p in $posPlayers) {
            $rankTotal = ($p.Ranking | Where-Object { $_.Type -eq 'Total_Pos' }).Value
            $rankAvg   = ($p.Ranking | Where-Object { $_.Type -eq 'PerGame_Pos' }).Value
            if ($null -ne $rankTotal -and $null -ne $rankAvg) {
                $combinedValue = ($rankTotal * $weightTotal) + ($rankAvg * $weightAvg)
                $p | Add-Member -NotePropertyName 'CombinedRankValue_Pos' -NotePropertyValue $combinedValue -Force
            }
        }

        # Positionsweise Combined mit Tiebreaks
        $combinedPosList = $posPlayers | Where-Object { $_.CombinedRankValue_Pos -gt 0 } |
            Sort-Object -Property @{Expression = 'CombinedRankValue_Pos'; Ascending = $true},
                                   @{Expression = $propTotal; Ascending = $false},
                                   @{Expression = $propAvg; Ascending = $false}

        $prevValue = $null
        $rank = 0
        $i = 0
        foreach ($p in $combinedPosList) {
            $i++
            $value = $p.CombinedRankValue_Pos
            if ($value -ne $prevValue) { $rank = $i }
            $prevValue = $value
            $p.Ranking += [PSCustomObject]@{ Type = 'Combined_Pos'; Value = $rank }
        }
    }

    # Temporäre Felder entfernen
    foreach ($p in $playersActive) {
        $p.PSObject.Properties.Remove('CombinedRankValue')
        $p.PSObject.Properties.Remove('CombinedRankValue_Pos')
    }

    return $players
}

# Ranking anwenden
$playerData = Add-Rankings -players $playerData -weightTotal $weightTotal -weightAvg $weightGame
Write-Host "Player rankings calculated and added." -ForegroundColor Yellow



function Get-LetterGrade {
    param(
        [double]$value,
        [string]$position
    )

    $multiplier = 1.5
    if($position -eq 'K') {
        $multiplier = 1
    }
    if($position -eq 'RB' -or $position -eq 'WR') {
        $multiplier = 2
    }

    #if ($value -ge 95) { return 'S' }

    if ($value -le 6 * $multiplier) { return 'A' }
    elseif ($value -le 12 * $multiplier) { return 'B' }
    elseif ($value -le 18 * $multiplier) { return 'C' }
    elseif ($value -le 24 * $multiplier) { return 'D' }
    elseif ($value -le 30 * $multiplier) { return 'E' }
    else { return 'F' }
}


function Add-PositionalGradings {
    param(
        [Parameter(Mandatory)][Array]$players
    )

    # --- Wunsch-Gradings (Werte von 0-5) ---
    # Ranking (Kombination aus diesem und letztem Jahr, wo verfügbar)
    # Verlässlichkeit (TD bereinigt, Vergangenheit, Floor, Effizienz)
    # Potential (Impact, Ceiling, Draft Position Rookies, Highest Scores in Vergangenheit)
    # Form (letzte X Spiele inklusive Playoffs, Teamrecord, Entwicklung Einsatzzeit)
    # Position Individuelles


    # --- jeden Spieler durchgehen und Grading Werte berechnen ---
    foreach ($p in $players) {
        
        # Grading Objekt initialisieren, wenn noch nicht vorhanden
        if (-not $p.PSObject.Properties["Grading"]) {
            $p | Add-Member -NotePropertyName 'Grading' -NotePropertyValue @()
        }

        # --- Positional Ranking extrahieren (Combined_Pos) ---
        $rankValue = ($p.Ranking | Where-Object { $_.Type -eq 'Combined_Pos' }).Value
        
        $posRank = [PSCustomObject]@{
            Type = "Rank"
            Value = $rankValue
            Rank = $rankValue
            Grade = Get-LetterGrade $rankValue $p.Position
        }

        $p.Grading += $posRank
    }



    # # --- Spieler nach Position gruppieren ---
    # $positions = $players | Select-Object -ExpandProperty Position -Unique

    # foreach ($pos in $positions) {
    #     $posPlayers = $players | Where-Object { $_.Position -eq $pos }

    #     # --- Maximalwerte pro Kriterium ermitteln ---
    #     $maxForm = ($posPlayers | Measure-Object -Property FantasyPointsAvgGame -Maximum).Maximum
    #     $maxConsistency = ($posPlayers | Measure-Object -Property FantasyPointsAvgPotentialGame -Maximum).Maximum
    #     $maxEfficiency = ($posPlayers | Measure-Object -Property FantasyPointsAvgSnap -Maximum).Maximum
    #     $maxImpact = ($posPlayers | Measure-Object -Property TouchdownsTotal -Maximum).Maximum
    #     $maxPotential = ($posPlayers | Measure-Object -Property FantasyPointsAvgPotentialGame -Maximum).Maximum

    #     foreach ($p in $posPlayers) {
    #         # --- Normierte Werte berechnen ---
    #         $formValue = if ($maxForm -gt 0) { ($p.FantasyPointsAvgGame / $maxForm) * 100 } else { 0 }
    #         $consistencyValue = if ($maxConsistency -gt 0) { ($p.FantasyPointsAvgPotentialGame / $maxConsistency) * 100 } else { 0 }
    #         $efficiencyValue = if ($maxEfficiency -gt 0) { ($p.FantasyPointsAvgSnap / $maxEfficiency) * 100 } else { 0 }
    #         # Impact: Punkte abziehen für Touchdowns, weniger TDs = höherer Impact
    #         $impactValue = if ($maxImpact -gt 0) { ((1 - ($p.TouchdownsTotal / $maxImpact)) * 100) } else { 100 }
    #         $potentialValue = if ($maxPotential -gt 0) { ($p.FantasyPointsAvgPotentialGame / $maxPotential) * 100 } else { 0 }

    #         # --- Gesamt-GradeValue ---
    #         $gradeValue = ($formValue * $weightForm) + ($consistencyValue * $weightConsistency) +
    #                       ($efficiencyValue * $weightEfficiency) + ($impactValue * $weightImpact) +
    #                       ($potentialValue * $weightPotential)

    #         $p.Grading += [PSCustomObject]@{ GradeValueForm = [math]::Round($formValue,2) }
    #         $p.Grading += [PSCustomObject]@{ GradeValueConsistency = [math]::Round($consistencyValue,2) }
    #         $p.Grading += [PSCustomObject]@{ GradeValueEfficiency = [math]::Round($efficiencyValue,2) }
    #         $p.Grading += [PSCustomObject]@{ GradeValueImpact = [math]::Round($impactValue,2) }
    #         $p.Grading += [PSCustomObject]@{ GradeValuePotential = [math]::Round($potentialValue,2) }
    #         $p.Grading += [PSCustomObject]@{ GradeValue = [math]::Round($gradeValue,2) }
    #         $p.Grading += [PSCustomObject]@{ Grade = (Get-Grade $gradeValue) }

    #         # --- Objekt erweitern ---
    #         # $p.Grading.GradeValueForm = [math]::Round($formValue,2)
    #         # $p.Grading.GradeValueConsistency = [math]::Round($consistencyValue,2)
    #         # $p.Grading.GradeValueEfficiency = [math]::Round($efficiencyValue,2)
    #         # $p.Grading.GradeValueImpact = [math]::Round($impactValue,2)
    #         # $p.Grading.GradeValuePotential = [math]::Round($potentialValue,2)
    #         # $p.Grading.GradeValue = [math]::Round($gradeValue,2)
    #         # $p.Grading.Grade = (Get-Grade $gradeValue)
    #     }
    # }

    return $players
}


# Gradings berechnen
Write-Host "Calculating player gradings..." -ForegroundColor Yellow
$playerData = Add-PositionalGradings -players $playerData
Write-Host "Player gradings calculated and added." -ForegroundColor Yellow


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