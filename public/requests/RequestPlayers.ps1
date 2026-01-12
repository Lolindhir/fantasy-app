# --- Funktionen ---
# Globale Variable für den zuletzt erfolgreichen Key
$Global:CurrentApiKey = $null
function Invoke-Tank01-With-Fallback {
    param(
        [string]$Url,
        [string[]]$Keys
    )

    $delay = 2  # Start-Wartezeit in Sekunden

    # Wenn bereits ein funktionierender Key gespeichert ist, probiere diesen zuerst
    if ($Global:CurrentApiKey -and $Keys -contains $Global:CurrentApiKey) {
        $headers = @{
            "X-RapidAPI-Key" = $Global:CurrentApiKey
            "X-RapidAPI-Host" = "tank01-nfl-live-in-game-real-time-statistics-nfl.p.rapidapi.com"
        }
        try {
            Write-Host "  Using cached key: $($Global:CurrentApiKey)" -ForegroundColor DarkGray
            return Invoke-RestMethod -Uri $Url -Headers $headers -ErrorAction Stop
        } catch {
            $statusCode = $_.Exception.Response.StatusCode.Value__
            if ($statusCode -eq 429) {
                Write-Warning "Cached key $($Global:CurrentApiKey) hit 429 - switching..."
                # Reset Key, nächster Versuch mit allen Keys
                $Global:CurrentApiKey = $null
            } else {
                throw $_
            }
        }
    }

    # Normale Fallback-Logik (alle Keys durchprobieren)
    foreach ($key in $Keys) {
        $headers = @{
            "X-RapidAPI-Key" = $key
            "X-RapidAPI-Host" = "tank01-nfl-live-in-game-real-time-statistics-nfl.p.rapidapi.com"
        }

        try {
            Write-Host "  Try with key: $key" -ForegroundColor DarkGray
            $result = Invoke-RestMethod -Uri $Url -Headers $headers -ErrorAction Stop
            # Wenn erfolgreich: Key merken
            $Global:CurrentApiKey = $key
            return $result
        } catch {
            $statusCode = $_.Exception.Response.StatusCode.Value__
            if ($statusCode -eq 429) {
                Write-Warning "429 Too Many Requests - wait $delay sec before next key..."
                Start-Sleep -Seconds $delay
                $delay = [Math]::Min($delay * 2, 30)
                continue
            } else {
                throw $_
            }
        }
    }

    throw "All API keys have failed (including 429 errors)."
}

function PlayersHaveChanged($oldPlayers, $newPlayers) {
    if (-not $oldPlayers) { return $true }

    if ($oldPlayers.Count -ne $newPlayers.Count) {
        Write-Host "Player count changed: $($oldPlayers.Count) -> $($newPlayers.Count)"
        return $true
    }

    # sicherstellen, dass beide Listen nach ID sortiert sind
    $oldPlayers = $oldPlayers | Sort-Object -Property ID
    $newPlayers = $newPlayers | Sort-Object -Property ID

    for ($i = 0; $i -lt $oldPlayers.Count; $i++) {
        $old = $oldPlayers[$i]
        $new = $newPlayers[$i]

        $propsToCheck = @(
            'ID',
            'TankID',
            'Name',
            'NameFirst',
            'NameLast',
            'NameShort',
            'Status',
            'Position',
            'Age',
            'Year',
            'TeamID',
            'TeamAbbr',
            'ByeWeek',
            'Number',
            'Picture',
            'Salary',
            'SalaryProjected',
            'College',
            'HighSchool',
            'ESPN',
            'FantasyPros',
            'Injured',
            #'Injury',   #object
            #'Ranking',   #object
            #'Grading',   #object
            #'PointHistory',   #object
            #'GameHistory'   #object
            'GamesPlayed',
            'GamesPotential',
            'SnapsTotal',
            'AttemptsTotal',
            'FantasyPointsTotal',
            'FantasyPointsAvgGame',
            'FantasyPointsAvgPotentialGame',
            'FantasyPointsAvgSnap',
            'FantasyPointsAvgAttempt',
            'TouchdownsTotal',
            'TouchdownsRushing',
            'TouchdownsReceiving',
            'TouchdownsPassing'
        )
        foreach ($prop in $propsToCheck) {
            if ($old.$prop -ne $new.$prop) {
                Write-Host "Player '$($old.Name)' property '$prop' changed: '$($old.$prop)' -> '$($new.$prop)'"
                return $true
            }
        }
    }

    return $false
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
        [double]$weight2 = 0.35,  # Gewicht, wenn pts2 das Maximum ist
        [double]$weight3 = 0.25   # Gewicht, wenn pts3 das Maximum ist
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


function Get-LetterGrade {
    param([double]$value)
    if ($value -ge 95) { return 'S' }
    elseif ($value -ge 85) { return 'A' }
    elseif ($value -ge 75) { return 'B' }
    elseif ($value -ge 65) { return 'C' }
    elseif ($value -ge 50) { return 'D' }
    elseif ($value -ge 35) { return 'E' }
    else { return 'F' }
}


function Add-PositionalGradings {
    param(
        [Parameter(Mandatory)][Array]$players,
        [double]$weightForm = 0.2,
        [double]$weightConsistency = 0.2,
        [double]$weightEfficiency = 0.2,
        [double]$weightImpact = 0.2,
        [double]$weightPotential = 0.2
    )

    # --- Wunsch-Gradings (Werte von 0-5) ---
    # Ranking (Kombination aus Overall und Positional Rank)
    # Verlässlichkeit (Vergangenheit, Floor, Effizienz)
    # Potential (Impact, Ceiling, Draft Position Rookies, Highest Scores in Vergangenheit)
    # Form (letzte X Spiele inklusive Playoffs, Teamrecord, Entwicklung Einsatzzeit)
    # Position Individuelles


    # --- Hilfsfunktion: Schulnote ---
    function Get-Grade([double]$value) {
        switch ($value) {
            {$_ -ge 95} { return "S" }
            {$_ -ge 90} { return "A" }
            {$_ -ge 80} { return "B" }
            {$_ -ge 70} { return "C" }
            {$_ -ge 60} { return "D" }
            {$_ -ge 50} { return "E" }
            default { return "F" }
        }
    }

    # --- Spieler nach Position gruppieren ---
    $positions = $players | Select-Object -ExpandProperty Position -Unique

    foreach ($pos in $positions) {
        $posPlayers = $players | Where-Object { $_.Position -eq $pos }

        # --- Maximalwerte pro Kriterium ermitteln ---
        $maxForm = ($posPlayers | Measure-Object -Property FantasyPointsAvgGame -Maximum).Maximum
        $maxConsistency = ($posPlayers | Measure-Object -Property FantasyPointsAvgPotentialGame -Maximum).Maximum
        $maxEfficiency = ($posPlayers | Measure-Object -Property FantasyPointsAvgSnap -Maximum).Maximum
        $maxImpact = ($posPlayers | Measure-Object -Property TouchdownsTotal -Maximum).Maximum
        $maxPotential = ($posPlayers | Measure-Object -Property FantasyPointsAvgPotentialGame -Maximum).Maximum

        foreach ($p in $posPlayers) {
            # --- Normierte Werte berechnen ---
            $formValue = if ($maxForm -gt 0) { ($p.FantasyPointsAvgGame / $maxForm) * 100 } else { 0 }
            $consistencyValue = if ($maxConsistency -gt 0) { ($p.FantasyPointsAvgPotentialGame / $maxConsistency) * 100 } else { 0 }
            $efficiencyValue = if ($maxEfficiency -gt 0) { ($p.FantasyPointsAvgSnap / $maxEfficiency) * 100 } else { 0 }
            # Impact: Punkte abziehen für Touchdowns, weniger TDs = höherer Impact
            $impactValue = if ($maxImpact -gt 0) { ((1 - ($p.TouchdownsTotal / $maxImpact)) * 100) } else { 100 }
            $potentialValue = if ($maxPotential -gt 0) { ($p.FantasyPointsAvgPotentialGame / $maxPotential) * 100 } else { 0 }

            # --- Gesamt-GradeValue ---
            $gradeValue = ($formValue * $weightForm) + ($consistencyValue * $weightConsistency) +
                          ($efficiencyValue * $weightEfficiency) + ($impactValue * $weightImpact) +
                          ($potentialValue * $weightPotential)

            $p.Grading += [PSCustomObject]@{ GradeValueForm = [math]::Round($formValue,2) }
            $p.Grading += [PSCustomObject]@{ GradeValueConsistency = [math]::Round($consistencyValue,2) }
            $p.Grading += [PSCustomObject]@{ GradeValueEfficiency = [math]::Round($efficiencyValue,2) }
            $p.Grading += [PSCustomObject]@{ GradeValueImpact = [math]::Round($impactValue,2) }
            $p.Grading += [PSCustomObject]@{ GradeValuePotential = [math]::Round($potentialValue,2) }
            $p.Grading += [PSCustomObject]@{ GradeValue = [math]::Round($gradeValue,2) }
            $p.Grading += [PSCustomObject]@{ Grade = (Get-Grade $gradeValue) }

            # --- Objekt erweitern ---
            # $p.Grading.GradeValueForm = [math]::Round($formValue,2)
            # $p.Grading.GradeValueConsistency = [math]::Round($consistencyValue,2)
            # $p.Grading.GradeValueEfficiency = [math]::Round($efficiencyValue,2)
            # $p.Grading.GradeValueImpact = [math]::Round($impactValue,2)
            # $p.Grading.GradeValuePotential = [math]::Round($potentialValue,2)
            # $p.Grading.GradeValue = [math]::Round($gradeValue,2)
            # $p.Grading.Grade = (Get-Grade $gradeValue)
        }
    }

    return $players
}

# --- Konfiguration ---
. "$PSScriptRoot\config.ps1"
$apiKeys = @(
    $Global:RapidAPIKey,
    $Global:RapidAPIKeyAlt1,
    $Global:RapidAPIKeyAlt2
)
$Date = (Get-Date -Format "yyyyMMdd")
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$targetFile = Join-Path $scriptDir "..\data\Players.json"
$backupDir = Join-Path $scriptDir "..\data\backup"
if (!(Test-Path $backupDir)) { New-Item -ItemType Directory -Path $backupDir -Force | Out-Null }
$gamesFile = Join-Path $scriptDir "..\data\Games.json"
$leagueFile = Join-Path $scriptDir "..\data\League.json"

# --- Season aus config.ps1 ---
if (-not $Global:LeagueYear) {
    Write-Error "LeagueYear not set in config.ps1!"
    exit 1
}
$seasonYear = $Global:LeagueYear

# --- Lookup-Tabelle für Spielerstatistiken des letzten Jahres holen
$seasonLast = $seasonYear - 1
$seasonLastFile = Join-Path $scriptDir "..\data\past_seasons\Players_$seasonLast.json"
$playersLookupLastSeason = @{}
try {
    $seasonLastRaw = Get-Content $seasonLastFile -Raw
    $playersLastSeason = $seasonLastRaw | ConvertFrom-Json
    if(-not $playersLastSeason){
        Write-Host "Couldn't load old player stats for year: $seasonLast" -ForegroundColor Red
        exit 1
    } else {
        foreach ($player in $playersLastSeason) { $playersLookupLastSeason[$player.TankID] = $player }
        Write-Host "Loaded old player stats for year: $seasonLast..." -ForegroundColor Yellow
    }
} catch {
    Write-Error "Error fetching old player stats: $_"
    exit 1
}

# --- Lookup-Tabelle für Spielerstatistiken des vorletzten Jahres holen
$seasonBeforeLast = $seasonYear - 2
$seasonBeforeLastFile = Join-Path $scriptDir "..\data\past_seasons\Players_$seasonBeforeLast.json"
$playersLookupBeforeLastSeason = @{}
try {
    $seasonBeforeLastRaw = Get-Content $seasonBeforeLastFile -Raw
    $playersBeforeLastSeason = $seasonBeforeLastRaw | ConvertFrom-Json
    if(-not $playersBeforeLastSeason){
        Write-Host "Couldn't load old player stats for year: $seasonBeforeLast" -ForegroundColor Red
        exit 1
    } else {
        foreach ($player in $playersBeforeLastSeason) { $playersLookupBeforeLastSeason[$player.TankID] = $player }
        Write-Host "Loaded old player stats for year: $seasonBeforeLast..." -ForegroundColor Yellow
    }
} catch {
    Write-Error "Error fetching old player stats: $_"
    exit 1
}

# --- Lookup-Tabelle für Spielerstatistiken des vorvorletzten Jahres holen
$seasonBeforeBeforeLast = $seasonYear - 3
$seasonBeforeBeforeLastFile = Join-Path $scriptDir "..\data\past_seasons\Players_$seasonBeforeBeforeLast.json"
$playersLookupBeforeBeforeLastSeason = @{}
try {
    $seasonBeforeBeforeLastRaw = Get-Content $seasonBeforeBeforeLastFile -Raw
    $playersBeforeBeforeLastSeason = $seasonBeforeBeforeLastRaw | ConvertFrom-Json
    if(-not $playersBeforeBeforeLastSeason){
        Write-Host "Couldn't load old player stats for year: $seasonBeforeBeforeLast" -ForegroundColor Red
        exit 1
    } else {
        foreach ($player in $playersBeforeBeforeLastSeason) { $playersLookupBeforeBeforeLastSeason[$player.TankID] = $player }
        Write-Host "Loaded old player stats for year: $seasonBeforeBeforeLast..." -ForegroundColor Yellow
    }
} catch {
    Write-Error "Error fetching old player stats: $_"
    exit 1
}

# --- Season Start Datum aus config.ps1 ---
if (-not $Global:LeagueStart) {
    Write-Error "LeagueStart not set in config.ps1!"
    exit 1
}
$seasonStartDate = $Global:LeagueStart

# --- Gewichtungen aus config.ps1 ---
if (-not $Global:WeightTotal -or -not $Global:WeightGame) {
    Write-Error "Weights not set in config.ps1!"
    exit 1
}
$weightTotal = $Global:WeightTotal
$weightGame = $Global:WeightGame

$finalWeek = 0
$lastWeek = 0
$playoffStartWeek = 0
if (Test-Path $leagueFile) {
    try {
        $leagueRaw = Get-Content $leagueFile -Raw
        $league = $leagueRaw | ConvertFrom-Json
        if($league){
            $lastWeek = $league.LastWeek
            $playoffStartWeek = $league.PlayoffStartWeek
            $finalWeek = $league.FinalWeek
        }
        Write-Host "Loaded last week (Week $($lastWeek)) from League.json..." -ForegroundColor Yellow
        Write-Host "Loaded playoff start week (Week $($playoffStartWeek)) from League.json..." -ForegroundColor Yellow
        Write-Host "Loaded final week (Week $($finalWeek)) from League.json..." -ForegroundColor Yellow
    } catch {
        Write-Error "Error fetching league: $_"
        exit 1
    }
}

# --- Sleeper Spieler abrufen ---
Write-Host "Fetch Sleeper players..." -ForegroundColor Yellow
try {
    $sleeperPlayersUrl = "https://api.sleeper.app/v1/players/nfl"
    $sleeperPlayers = Invoke-RestMethod -Uri $sleeperPlayersUrl
    $sleeperPlayers = $sleeperPlayers.PSObject.Properties.Value
} catch {
    Write-Error "Error fetching Sleeper players: $_"
    exit 1
}
Write-Host "Sleeper players found: $($sleeperPlayers.Count)" -ForegroundColor Yellow

# --- Tank01 Spieler ---
Write-Host "Fetch Tank01 players..." -ForegroundColor Yellow
$tankPlayersUrl = "https://tank01-nfl-live-in-game-real-time-statistics-nfl.p.rapidapi.com/getNFLPlayerList"
try {
    $tankPlayersResponse = Invoke-Tank01-With-Fallback -Url $tankPlayersUrl -Keys $apiKeys
    $tankPlayers = $tankPlayersResponse.body
} catch {
    Write-Error "Error fetching Tank01 players: $_"
    exit 1
}
Write-Host "Tank01 players found: $($tankPlayers.Count)" -ForegroundColor Yellow

# --- Spieler JSON vorbereiten ---
Write-Host "Creating Players.json..." -ForegroundColor Yellow
$sleeperLookup = @{}
foreach ($sleeper in $sleeperPlayers) { $sleeperLookup[$sleeper.player_id] = $sleeper }

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


# --- Load Games.json (alle Saisonspiele mit Stats) ---
$playerHistory = @{}

# Team → ByeWeek mapping vorbereiten
$teamByeWeek = @{}

if (Test-Path $gamesFile) {
    try {
        $gamesRaw = Get-Content $gamesFile -Raw
        $games = $gamesRaw | ConvertFrom-Json
        Write-Host "Loaded $($games.Count) games from Games.json..." -ForegroundColor Yellow

        # Sortiere Games nach GameID (neueste oben)
        $games = $games | Sort-Object -Property gameID -Descending

        # Alle Weeks der Saison durchgehen
        for ($week = 1; $week -le 18; $week++) {
            # Alle Teams in dieser Woche
            $teamsPlaying = @()
            foreach ($game in $games | Where-Object { $_.gameWeek -match "Week $week" }) {
                $teamsPlaying += $game.home
                $teamsPlaying += $game.away
            }
            
            # Alle Teams der Liga
            $allTeams = ($games | ForEach-Object { $_.home; $_.away } | Sort-Object -Unique)
            
            # Teams, die nicht gespielt haben -> ByeWeek
            $teamsNotPlaying = $allTeams | Where-Object { $teamsPlaying -notcontains $_ }
            
            foreach ($team in $teamsNotPlaying) {
                # Sollte nur eine Woche pro Team sein
                if (-not $teamByeWeek.ContainsKey($team)) {
                    $teamByeWeek[$team] = $week
                }
            }
        }

        foreach ($game in $games) {
            if (-not $game.playerStats) { continue }

            foreach ($playerKey in $game.playerStats.PSObject.Properties.Name) {
                $p = $game.playerStats.$playerKey
                if (-not $p.playerID) { continue }

                $playerID = $p.playerID
                if (-not $playerHistory.ContainsKey($playerID)) {
                    $playerHistory[$playerID] = [ordered]@{
                        TankID                 = $playerID
                        GamesPlayed            = 0
                        FantasyPointsTotalPPR  = 0.0
                        TouchdownsTotal        = 0
                        TouchdownsPassing      = 0
                        TouchdownsReceiving    = 0
                        TouchdownsRushing      = 0
                        SnapsTotal             = 0
                        AttemptsTotal          = 0
                        GameHistory            = @()
                    }
                }

                # --- GameInfo aufbauen (individuelle Teile aus Stat-Objekt übernehmen) ---
                $gameStats = [ordered]@{}
                # foreach ($prop in $p.PSObject.Properties) {
                #     $gameStats[$prop.Name] = $prop.Value
                # }
                $gameStats.GameID = $p.gameID

                # Game Week ermitteln
                if ($game.gameWeek -match 'Week (\d+)') {
                    $gameWeek = [int]$matches[1]
                } else {
                    Write-Warning "Could not parse gameWeek: $($game.gameWeek)"
                }

                # --- Details bauen
                $gameStats.GameDetails = [ordered]@{}
                $gameStats.GameDetails.Week = $gameWeek
                $gameStats.GameDetails.WeekFinal = $game.weekFinal
                $gameStats.GameDetails.WeekPlayoff = $gameStats.GameDetails.Week -ge $playoffStartWeek -and $playoffStartWeek -gt 0
                $gameStats.GameDetails.WeekScored = $gameStats.GameDetails.Week -le $lastWeek
                $gameStats.GameDetails.Date = $game.gameDate
                $gameStats.GameDetails.Home = $game.home
                $gameStats.GameDetails.HomeID = $game.teamIDHome
                $gameStats.GameDetails.Away = $game.away
                $gameStats.GameDetails.AwayID = $game.teamIDAway
                $gameStats.GameDetails.HomePoints = [int]$game.homePts
                $gameStats.GameDetails.AwayPoints = [int]$game.awayPts

                $gameStats.TeamID = $p.teamID
                $gameStats.TeamAbv = $p.teamAbv
                $gameStats.FantasyPoints = [double]$p.fantasyPointsDefault.PPR

                if($p.snapCounts) {
                    # Kicker erhalten pro Attempt einen Snap, alle anderen nehmen die Offensive Snaps
                    if ($p.Kicking) {
                        $gameStats.SnapCount = [int]$([int]$p.Kicking.fgAttempts + [int]$p.Kicking.xpAttempts)
                        $gameStats.SnapPercentage = 1
                    } else {
                        $gameStats.SnapCount = [int]$p.snapCounts.offSnap
                        $gameStats.SnapPercentage = [double]$p.snapCounts.offSnapPct
                    }                    
                } else {
                    $gameStats.SnapCount = 0
                    $gameStats.SnapPercentage = 0
                }

                $gameStats.Attempts = 0
                if($p.Passing.passAttempts) { $gameStats.Attempts += [int]$p.Passing.passAttempts }
                if($p.Receiving.targets) { $gameStats.Attempts += [int]$p.Receiving.targets }
                if($p.Rushing.carries) { $gameStats.Attempts += [int]$p.Rushing.carries }
                if($p.Kicking.fgAttempts) { $gameStats.Attempts += [int]$p.Kicking.fgAttempts }
                if($p.Kicking.xpAttempts) { $gameStats.Attempts += [int]$p.Kicking.xpAttempts }

                # QBR sauber in Double konvertieren, falls möglich
                $qbrValue = $null
                if ([double]::TryParse($pass.qbr, [ref]$qbrValue)) {
                    $QBRating = $qbrValue
                } else {
                    $QBRating = $null  # oder 0, je nach Wunsch
                }

                if ($p.Passing) {
                    $pass = $p.Passing
                    $gameStats.Passing = [PSCustomObject]@{
                        QBRating        = $QBRating
                        Rating          = [double]$pass.rtg
                        PassAttempts    = [int]$pass.passAttempts
                        PassAvg         = [double]$pass.passAvg
                        PassTDs         = [int]$pass.passTD
                        PassYards       = [int]$pass.passYds
                        Interceptions   = [int]$pass.int
                        PassCompletions = [int]$pass.passCompletions
                    }
                }
                if ($p.Receiving) {
                    $rec = $p.Receiving
                    $gameStats.Receiving = [PSCustomObject]@{
                        Receptions       = [int]$rec.receptions
                        ReceptionTDs     = [int]$rec.recTD
                        LongReceptions   = [int]$rec.longRec
                        Targets          = [int]$rec.targets
                        ReceptionYards   = [int]$rec.recYds
                        ReceptionAvg     = [double]$rec.recAvg
                    }
                }

                if ($p.Rushing) {
                    $rush = $p.Rushing
                    $gameStats.Rushing = [PSCustomObject]@{
                        RushAvg     = [double]$rush.rushAvg
                        RushYards   = [int]$rush.rushYds
                        Carries     = [int]$rush.carries
                        LongRush    = [int]$rush.longRush
                        RushTDs     = [int]$rush.rushTD
                    }
                }
                if ($p.Kicking) {
                    $kick = $p.Kicking
                    $gameStats.Kicking = [PSCustomObject]@{
                        KickingPts  = [double]$kick.kickingPts
                        FgLong      = [int]$kick.fgLong
                        FgMade      = [int]$kick.fgMade
                        FgAttempts  = [int]$kick.fgAttempts
                        FgMissed    = [int]$kick.fgMissed
                        FgPct       = [double]$kick.fgPct
                        XpMade      = [int]$kick.xpMade
                        XpAttempts  = [int]$kick.xpAttempts
                        XpMissed    = [int]$kick.xpMissed
                    }
                }

                # Game zur Historie hinzufügen (vorne)
                $playerHistory[$playerID].GameHistory += @($gameStats)

                # Summenwerte berechnen, wenn Snap-Count vorhanden ist (dann sollten alle Daten vorhanden sein) und die Woche final ist und die Woche gescored wird
                if($gameStats.SnapCount -gt 0 -and $gameStats.GameDetails.WeekFinal -and $gameStats.GameDetails.WeekScored) { 

                    $playerHistory[$playerID].GamesPlayed++ 
                
                    $ppr = 0.0
                    if ($p.fantasyPointsDefault.PPR) { $ppr = [double]$p.fantasyPointsDefault.PPR }
                    $playerHistory[$playerID].FantasyPointsTotalPPR += $ppr

                    $rushTD = 0
                    if ($p.Rushing.rushTD) { $rushTD = [int]$p.Rushing.rushTD }
                    $recTD = 0
                    if ($p.Receiving.recTD) { $recTD = [int]$p.Receiving.recTD }
                    $passTD = 0
                    if ($p.Passing.passTD) { $passTD = [int]$p.Passing.passTD }

                    $playerHistory[$playerID].TouchdownsRushing += $rushTD
                    $playerHistory[$playerID].TouchdownsReceiving += $recTD
                    $playerHistory[$playerID].TouchdownsPassing += $passTD
                    $playerHistory[$playerID].TouchdownsTotal += ($rushTD + $recTD + $passTD)
                    $playerHistory[$playerID].SnapsTotal += $gameStats.SnapCount
                    $playerHistory[$playerID].AttemptsTotal += $gameStats.Attempts            }

                }             
        }

    } catch {
        Write-Error "Error reading Games.json: $_"
        return 1
    }
} else {
    Write-Error "Games.json not found!"
    return 1
}


$playerData = @()
foreach ($tankEntry in $tankPlayers) {
    if (-not $tankEntry.sleeperBotID) { continue }
    $sleeperEntry = $sleeperLookup[$tankEntry.sleeperBotID]
    if (-not $sleeperEntry) { continue }
    if ($sleeperEntry.position -notin @("TE","QB","RB","WR","K")) { continue }

    # Alte Daten laden
    $oldPlayer = $oldPlayersLookup[$sleeperEntry.player_id]

    # --- PlayerID ---
    $playerID = $sleeperEntry.player_id
    # --- Year berechnen ---
    $year = $sleeperEntry.years_exp + 1
    # --- Age ---
    $age = $sleeperEntry.age
    # --- Position ---
    $position = $sleeperEntry.position
    # --- Team ---
    $team = $tankEntry.team

    # --- Bye-Week bestimmen
    $byeWeek = if ($teamByeWeek.ContainsKey($team)) { $teamByeWeek[$team] } else { 0 }

    # --- Injury bestimmen ---
    $injured = $false
    $injury = [PSCustomObject]@{
        ReturnDate  = ""
        Description = ""
        Date        = ""
        Designation = ""
    }

    if ($tankEntry.injury.injReturnDate) {
        $injury.ReturnDate = $tankEntry.injury.injReturnDate
    }
    if ($tankEntry.injury.injDate) {
        $injury.Date = $tankEntry.injury.injDate
    }
    if ($tankEntry.injury.description) {
        $injury.Description = $tankEntry.injury.description
    }    
    if ($tankEntry.injury.designation) {
        $injury.Designation = $tankEntry.injury.designation
        $injured = $true
    }


    # --- Player Stats (aus Games.json) ---
    $stats = $playerHistory[$tankEntry.playerID]
    if ($stats) {
        
        $gamesPlayed = $stats.GamesPlayed

        # --- Potentielle Spiele berechnen (ByeWeek berücksichtigen) ---
        $gamesPotential = $finalWeek
        if($byeWeek -le $finalWeek){
            $gamesPotential--
        }

        $fantasyPointsTotalPPR = [math]::Round($stats.FantasyPointsTotalPPR,2)
        $fantasyPointsAvgPPR = 0
        if($stats.GamesPlayed -gt 0){
            $fantasyPointsAvgPPR = [math]::Round($($stats.FantasyPointsTotalPPR/$stats.GamesPlayed),2)
        }
        $fantasyPointsAvgPotentialPPR = 0
        if($gamesPotential -gt 0){
            $fantasyPointsAvgPotentialPPR = [math]::Round($($stats.FantasyPointsTotalPPR/$gamesPotential),2)
        }
        $fantasyPointsAvgSnapPPR = 0
        if($stats.SnapsTotal -gt 0){
            $fantasyPointsAvgSnapPPR = [math]::Round($($stats.FantasyPointsTotalPPR/$stats.SnapsTotal),5)
        }
        $fantasyPointsAvgAttemptPPR = 0
        if($stats.AttemptsTotal -gt 0){
            $fantasyPointsAvgAttemptPPR = [math]::Round($($stats.FantasyPointsTotalPPR/$stats.AttemptsTotal),5)
        }
        $snaps = $stats.SnapsTotal
        $attempts = $stats.AttemptsTotal
        $tdTotal = $stats.TouchdownsTotal
        $tdRush = $stats.TouchdownsRushing
        $tdRec = $stats.TouchdownsReceiving
        $tdPass = $stats.TouchdownsPassing
        $gameHistory = $stats.GameHistory
    } else {
        $gamesPlayed = 0
        $gamesPotential = 0
        $snaps = 0
        $attempts = 0
        $fantasyPointsTotalPPR = 0
        $fantasyPointsAvgPPR = 0
        $fantasyPointsAvgPotentialPPR = 0
        $fantasyPointsAvgSnapPPR = 0
        $fantasyPointsAvgAttemptPPR = 0
        $tdTotal = 0
        $tdRush = 0
        $tdRec = 0
        $tdPass = 0
        $gameHistory = @()
    }

    # --- Daten der Vorjahre laden und abspeichern
    $playerLastSeason = $playersLookupLastSeason[$tankEntry.playerID]
    $playerBeforeLastSeason = $playersLookupBeforeLastSeason[$tankEntry.playerID]
    $playerBeforeBeforeLastSeason = $playersLookupBeforeBeforeLastSeason[$tankEntry.playerID]
    $pointHistory = [ordered]@{
    SeasonMinus1 = Get-SeasonPointStats $playerLastSeason $lastWeek
    SeasonMinus2 = Get-SeasonPointStats $playerBeforeLastSeason $lastWeek
    SeasonMinus3 = Get-SeasonPointStats $playerBeforeBeforeLastSeason $lastWeek
}

    # --------------------------------------
    # --- Salaries aus Fantasy berechnen ---
    # --------------------------------------
    # Jahrespunkte berechnen
    $ptsCurrent = $fantasyPointsAvgPotentialPPR * $weightTotal + $fantasyPointsAvgPPR * $weightGame
    $ptsSeasonMinus1 = $pointHistory.SeasonMinus1.AvgPotentialGame  * $weightTotal + $pointHistory.SeasonMinus1.AvgGame * $weightGame
    $ptsSeasonMinus2 = $pointHistory.SeasonMinus2.AvgPotentialGame  * $weightTotal + $pointHistory.SeasonMinus2.AvgGame * $weightGame
    $ptsSeasonMinus3 = $pointHistory.SeasonMinus3.AvgPotentialGame  * $weightTotal + $pointHistory.SeasonMinus3.AvgGame * $weightGame
    # Vergangenheitswerte
    $salaryDollarsFantasy = Get-FantasySalaryWithFloor $ptsSeasonMinus1 $ptsSeasonMinus2 $ptsSeasonMinus3 -weight1 0.5 -weight2 0.35 -weight3 0.25
    # Projektionswerte
    $salaryDollarsProjectedFantasy = Get-FantasySalaryWithFloor $ptsCurrent $ptsSeasonMinus1 $ptsSeasonMinus2 -weight1 0.5 -weight2 0.35 -weight3 0.25


    # --- Player Objekt bauen ---
    $playerData += [PSCustomObject]@{
        ID                           = $playerID
        TankID                       = $tankEntry.playerID
        Name                         = $sleeperEntry.full_name
        NameFirst                    = $sleeperEntry.first_name
        NameLast                     = $sleeperEntry.last_name
        NameShort                    = $tankEntry.cbsShortName
        TeamID                       = $tankEntry.teamID
        TeamAbbr                     = $tankEntry.team
        ByeWeek                      = $byeWeek
        Status                       = $sleeperEntry.status
        Position                     = $position
        Age                          = $age
        Year                         = $year
        Number                       = $tankEntry.jerseyNum
        Salary                       = [math]::Round($salaryDollarsFantasy)
        SalaryProjected              = [math]::Round($salaryDollarsProjectedFantasy)
        Picture                      = $tankEntry.espnHeadshot
        FantasyPros                  = $tankEntry.fantasyProsLink
        ESPN                         = $tankEntry.espnLink
        College                      = $sleeperEntry.college
        HighSchool                   = $sleeperEntry.high_school
        Injured                      = $injured
        InjuryDetails                = $injury
        GamesPlayed                  = $gamesPlayed
        GamesPotential               = $gamesPotential
        SnapsTotal                   = $snaps
        AttemptsTotal                = $attempts
        FantasyPointsTotal           = $fantasyPointsTotalPPR
        FantasyPointsAvgGame         = $fantasyPointsAvgPPR
        FantasyPointsAvgPotentialGame = $fantasyPointsAvgPotentialPPR
        FantasyPointsAvgSnap         = $fantasyPointsAvgSnapPPR
        FantasyPointsAvgAttempt      = $fantasyPointsAvgAttemptPPR
        Ranking                      = @()
        Grading                      = @()
        PointHistory                 = $pointHistory
        TouchdownsTotal              = $tdTotal
        TouchdownsPassing            = $tdPass
        TouchdownsReceiving          = $tdRec
        TouchdownsRushing            = $tdRush
        GameHistory                  = $gameHistory
    }
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


# Gradings berechnen
Write-Host "Calculating player gradings..." -ForegroundColor Yellow
$playerData = Add-PositionalGradings -players $playerData `
                                     -weightForm 0.2 `
                                     -weightConsistency 0.2 `
                                     -weightEfficiency 0.2 `
                                     -weightImpact 0.2 `
                                     -weightPotential 0.2
Write-Host "Player gradings calculated and added." -ForegroundColor Yellow


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
    $playerData | ConvertTo-Json -Depth 5 | Out-File $targetFile -Encoding UTF8
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