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
            'SalaryCurrentRaw',
            'SalarySeasonStartRaw',
            'SalaryCurrent',
            'SalarySeasonStart',
            'SalaryDollars',
            'SalaryDollarsFantasy',
            'SalaryDollarsCurrent',
            'SalaryDollarsSeasonStart',
            'SalaryDollarsProjected',
            'SalaryDollarsProjectedFantasy',
            'College',
            'HighSchool',
            'ESPN',
            'FantasyPros',
            'Injured',
            #'Injury',   #object
            #'Ranking',   #object
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

function Get-DraftKings($dateStr, $apiKeys) {
    Write-Host "Fetch Tank01 DraftKings salaries $dateStr..." -ForegroundColor Yellow
    $dfsUrl = "https://tank01-nfl-live-in-game-real-time-statistics-nfl.p.rapidapi.com/getNFLDFS?date=$dateStr"
    try {
        $dfsResponse = Invoke-Tank01-With-Fallback -Url $dfsUrl -Keys $apiKeys
    } catch {
        Write-Warning "Error fetching DraftKings data: $_"
        return $null
    }

    $draftKings = $dfsResponse.body.draftkings
    if (-not $draftKings -or $draftKings.Count -eq 0) {
        Write-Host "No DraftKings players found, reducing date by 1 day..." -ForegroundColor Blue
        $prevDate = (Convert-StringToDate $dateStr).AddDays(-1).ToString("yyyyMMdd")
        return Get-DraftKings $prevDate $apiKeys
    }
    return $draftKings
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

# function AdjustSalaryWithMeta {
#     param (
#         [double]$salary,
#         [int]$year,
#         [int]$age,
#         [string]$position,
#         [int]$playerID
#     )

#     $adjusted = $salary

#     # Salary unter 0 initial anpassen
#     if ($adjusted -le 0) {
#         $adjusted = GetDeterministicRandom -playerID $playerID -min 1 -max 100
#     }

#     # Erfahrungsbonus: pro Jahr in der Liga +50 Punkte
#     $adjusted += ($year - 1) * 50

#     # Altersmalus: pro Jahr über 29 -100 Punkte
#     if ($age -gt 29) {
#         $adjusted -= ($age - 29) * 100
#     }

#     # Kicker-Bonus: pro Jahr in der Liga +200 Punkte
#     if ($position -eq "K") {
#         $adjusted += $year * 200
#     }

#     # Wert unter 0 verhindern
#     if ($adjusted -le 0) {
#         $adjusted = GetDeterministicRandom -playerID $playerID -min 1 -max 100
#     }

#     return [math]::Round($adjusted)
# }

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
if (Test-Path $leagueFile) {
    try {
        $leagueRaw = Get-Content $leagueFile -Raw
        $league = $leagueRaw | ConvertFrom-Json
        if($league){
            $finalWeek = $league.FinalWeek
        }
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

# --- DraftKings Salaries ---
Write-Host "Fetch Tank01 DraftKings Salaries..." -ForegroundColor Yellow
$draftKings = Get-DraftKings $Date $apiKeys
if (-not $draftKings) {
    Write-Error "Error fetching DraftKings data: $_"
    exit 1
}
Write-Host "DraftKings players found: $($draftKings.Count)" -ForegroundColor Yellow


# --- Spieler JSON vorbereiten ---
Write-Host "Creating Players.json..." -ForegroundColor Yellow
$sleeperLookup = @{}
foreach ($sleeper in $sleeperPlayers) { $sleeperLookup[$sleeper.player_id] = $sleeper }

$draftKingsLookup = @{}
foreach ($dk in $draftKings) { $draftKingsLookup[$dk.playerID] = $dk }

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

                # --- Details bauen
                $gameStats.GameDetails = [ordered]@{}
                if ($game.gameWeek -match 'Week (\d+)') {
                    $gameStats.GameDetails.Week = [int]$matches[1]
                } else {
                    Write-Warning "Could not parse gameWeek: $($game.gameWeek)"
                }
                $gameStats.GameDetails.WeekFinal = $game.weekFinal
                $gameStats.GameDetails.Date = $game.gameDate
                $gameStats.GameDetails.Home = $game.home
                $gameStats.GameDetails.Away = $game.away
                $gameStats.GameDetails.HomePoints = $game.homePts
                $gameStats.GameDetails.AwayPoints = $game.awayPts

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

                if($p.Passing) {$gameStats.Passing = $p.Passing}
                if($p.Receiving) {$gameStats.Receiving = $p.Receiving}
                if($p.Rushing) {$gameStats.Rushing = $p.Rushing}
                if($p.Kicking) {$gameStats.Kicking = $p.Kicking}

                # Game zur Historie hinzufügen (vorne)
                $playerHistory[$playerID].GameHistory += @($gameStats)

                # Summenwerte berechnen, wenn Snap-Count vorhanden ist (dann sollten alle Daten vorhanden sein) und die Woche final ist
                if($gameStats.SnapCount -gt 0 -and $gameStats.GameDetails.WeekFinal) { 

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


# Cache für SeasonStart DraftKings
$draftKingsStartLookup = $null

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

    # --- Salary (heutige DraftKings) ---
    $dfsEntry = $draftKingsLookup[$tankEntry.playerID]
    $salaryCurrentRaw = if ($dfsEntry) { $dfsEntry.salary } else { 0 }
    # --- Prüfung für alten Salary ---
    if ($salaryCurrentRaw -eq 0 -and $oldPlayers) {
        $oldPlayer = $oldPlayers | Where-Object { $_.ID -eq $sleeperEntry.player_id }
        if ($oldPlayer -and $oldPlayer.SalaryCurrentRaw -gt 0) {
            $salaryCurrentRaw = $oldPlayer.SalaryCurrentRaw
            Write-Host "  Using old salary for $($sleeperEntry.full_name): $($salaryCurrentRaw)" -ForegroundColor DarkGray
        }
        # historischen Wert nach Umstellung auf neue Players.json Struktur abfragen als Fallback
        elseif ($oldPlayer -and $oldPlayer.Salary -gt 0) {
            $salaryCurrentRaw = $oldPlayer.Salary
            Write-Host "  Using fallback salary for $($sleeperEntry.full_name): $($salaryCurrentRaw)" -ForegroundColor DarkGray
        }
    }
    # --- auf Array prüfen und zu Number konvertieren ---
    if ($salaryCurrentRaw -is [System.Array]) { $salaryCurrentRaw = $salaryCurrentRaw[0] }
    $salaryCurrentRaw = [double]$salaryCurrentRaw

    # --- SalarySeasonStart bestimmen ---
    $salarySeasonStartRaw = $null
    if ($oldPlayer -and $oldPlayer.SalarySeasonStartRaw) {
        $salarySeasonStartRaw = $oldPlayer.SalarySeasonStartRaw
    }
    if (-not $salarySeasonStartRaw) {
        # DraftKingsStart nur bei Bedarf laden
        if (-not $draftKingsStartLookup) {
            Write-Host "Fetching DraftKings salaries for season start $seasonStartDate..." -ForegroundColor Yellow
            $draftKingsStart = Get-DraftKings $seasonStartDate $apiKeys

            if (-not $draftKingsStart -or $draftKingsStart.Count -eq 0) {
                Write-Warning "No DraftKings entries found for season start $seasonStartDate"
                $draftKingsStartLookup = @{}
            } else {
                # Ein Lookup erstellen für O(1)-Zugriff
                $draftKingsStartLookup = @{}
                foreach ($dk in $draftKingsStart) {
                    if ($dk.playerID) {
                        $draftKingsStartLookup[$dk.playerID] = $dk
                    }
                }
            }
        }

        $dfsStartEntry = $draftKingsStartLookup[$tankEntry.playerID]
        $salarySeasonStartRaw = if ($dfsStartEntry) { $dfsStartEntry.salary } else { 0 }
    }
    # --- auf Array prüfen und zu Number konvertieren ---
    if ($salarySeasonStartRaw -is [System.Array]) { $salarySeasonStartRaw = $salarySeasonStartRaw[0] }
    $salarySeasonStartRaw = [double]$salarySeasonStartRaw

    # --- Salary anpassen (Meta-Daten) ---
    # $salaryCurrent = AdjustSalaryWithMeta -salary $salaryCurrentRaw -year $year -age $age -position $position -playerID $playerID
    # $salarySeasonStart = AdjustSalaryWithMeta -salary $salarySeasonStartRaw -year $year -age $age -position $position -playerID $playerID
    $adjusted = AdjustSalaryWithMeta -salaryCurrent $salaryCurrentRaw -salarySeasonStart $salarySeasonStartRaw -year $year -age $age -position $position -playerID $playerID
    $salaryCurrent = $adjusted[0]
    $salarySeasonStart = $adjusted[1]

    # --- Salary in Dollar umrechnen ---
    $salaryDollarsCurrent = MapSalaryToDollars -salary $salaryCurrent
    $salaryDollarsSeasonStart = MapSalaryToDollars -salary $salarySeasonStart

    # --- Salary holen oder setzen ---
    $salaryDollars = $null
    if ($year -eq 1) {
        # Rookies haben bewusst kein SalaryLastSeason
        $salaryDollars = 0
    } else {
        if ($oldPlayer -and $oldPlayer.SalaryDollars) {
            $salaryDollars = $oldPlayer.SalaryDollars
        }
        if (-not $salaryDollars) {
            # wenn nicht vorhanden, nimm SalarySeasonStart
            $salaryDollars = $salaryDollarsSeasonStart

            # wenn es sich um einen Spieler in seinem zweiten Jahr handelt, dann halbiere den SalaryDollars, da er das vorige Jahr ein Rookie war
            if ($year -eq 2) {
                $salaryDollars = [math]::Round($salaryDollars / 2)
            }
        }
    }
    # --- auf Array prüfen ---
    if ($salaryDollars -is [System.Array]) { $salaryDollars = $salaryDollars[0] }

    # --- SalaryProjected bestimmen ---
    # Durchschnitt aus SalaryDollarsCurrent und SalaryDollarsSeasonStart
    # und dann Mittelwert mit SalaryDollars
    $salaryDollarsProjected = [math]::Round((($salaryDollarsCurrent + $salaryDollarsSeasonStart) / 2 + $salaryDollars) / 2)    

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
    $pointHistory = [ordered]@{}
    $pointHistory.SeasonMinus1 = [ordered]@{}
        $pointHistory.SeasonMinus1.Total = 0
        $pointHistory.SeasonMinus1.AvgGame = 0
        $pointHistory.SeasonMinus1.AgvPotentialGame = 0
        $pointHistory.SeasonMinus1.GamesPlayed = 0
        $pointHistory.SeasonMinus1.PotentialGames = 0
    $pointHistory.SeasonMinus2 = [ordered]@{}
        $pointHistory.SeasonMinus2.Total = 0
        $pointHistory.SeasonMinus2.AvgGame = 0
        $pointHistory.SeasonMinus2.AgvPotentialGame = 0
        $pointHistory.SeasonMinus2.GamesPlayed = 0
        $pointHistory.SeasonMinus2.PotentialGames = 0
    $pointHistory.SeasonMinus3 = [ordered]@{}
        $pointHistory.SeasonMinus3.Total = 0
        $pointHistory.SeasonMinus3.AvgGame = 0
        $pointHistory.SeasonMinus3.AgvPotentialGame = 0
        $pointHistory.SeasonMinus3.GamesPlayed = 0
        $pointHistory.SeasonMinus3.PotentialGames = 0
    if($playerLastSeason){
        $pointHistory.SeasonMinus1.Total = $playerLastSeason.TotalFantasyPoints
        $pointHistory.SeasonMinus1.AvgGame = $playerLastSeason.FantasyPointsAvg
        $pointHistory.SeasonMinus1.AgvPotentialGame = $playerLastSeason.FantasyPointsAvgPotential
        $pointHistory.SeasonMinus1.GamesPlayed = $playerLastSeason.TotalGames
        $pointHistory.SeasonMinus1.PotentialGames = $playerLastSeason.PotentialGames
    }
    if($playerBeforeLastSeason){
        $pointHistory.SeasonMinus2.Total = $playerBeforeLastSeason.TotalFantasyPoints
        $pointHistory.SeasonMinus2.AvgGame = $playerBeforeLastSeason.FantasyPointsAvg
        $pointHistory.SeasonMinus2.AgvPotentialGame = $playerBeforeLastSeason.FantasyPointsAvgPotential
        $pointHistory.SeasonMinus2.GamesPlayed = $playerBeforeLastSeason.TotalGames
        $pointHistory.SeasonMinus2.PotentialGames = $playerBeforeLastSeason.PotentialGames
    }
    if($playerBeforeBeforeLastSeason){
        $pointHistory.SeasonMinus3.Total = $playerBeforeBeforeLastSeason.TotalFantasyPoints
        $pointHistory.SeasonMinus3.AvgGame = $playerBeforeBeforeLastSeason.FantasyPointsAvg
        $pointHistory.SeasonMinus3.AgvPotentialGame = $playerBeforeBeforeLastSeason.FantasyPointsAvgPotential
        $pointHistory.SeasonMinus3.GamesPlayed = $playerBeforeBeforeLastSeason.TotalGames
        $pointHistory.SeasonMinus3.PotentialGames = $playerBeforeBeforeLastSeason.PotentialGames
    }

    # --------------------------------------
    # --- Salaries aus Fantasy berechnen ---
    # --------------------------------------
    # Jahrespunkte berechnen
    $ptsCurrent = $fantasyPointsAvgPotentialPPR * $weightTotal + $fantasyPointsAvgPPR * $weightGame
    $ptsSeasonMinus1 = $pointHistory.SeasonMinus1.AgvPotentialGame  * $weightTotal + $pointHistory.SeasonMinus1.AvgGame * $weightGame
    $ptsSeasonMinus2 = $pointHistory.SeasonMinus2.AgvPotentialGame  * $weightTotal + $pointHistory.SeasonMinus2.AvgGame * $weightGame
    $ptsSeasonMinus3 = $pointHistory.SeasonMinus3.AgvPotentialGame  * $weightTotal + $pointHistory.SeasonMinus3.AvgGame * $weightGame
    # Ceiling Vergangenheit berechnen
    $maxPast = [Math]::Max([Math]::Max($ptsSeasonMinus1, $ptsSeasonMinus2), $ptsSeasonMinus3)
    $ceilingPast = [Math]::Ceiling($maxPast / 2)
    # Ceiling Projected berechnen
    $maxProjected = [Math]::Max($maxPast, $ptsCurrent)
    $ceilingProjected = [Math]::Ceiling($maxProjected / 2)
    # Ceiling anwenden (keiner der Werte darf unterhalb des Floors liegen)
    $ptsSeasonMinus1 = [Math]::Max($ptsSeasonMinus1, $ceilingPast)
    $ptsSeasonMinus2 = [Math]::Max($ptsSeasonMinus2, $ceilingPast)
    $ptsSeasonMinus3 = [Math]::Max($ptsSeasonMinus3, $ceilingPast)
    # Aktuelle Salary berechnen -> Durchschnitt aus letzter Saison, vorletzter Saison und vorvorletzter Saison
    $salaryDollarsFantasy = MapSalaryFantasy -salary (($ptsSeasonMinus1 + $ptsSeasonMinus2 + $ptsSeasonMinus3)/3)
    # Projected Salary berechnen -> Durchschnitt aus aktueller Saison, letzter Saison und vorletzter Saison
    $ptsCurrent      = [Math]::Max($ptsCurrent, $ceilingProjected)
    $ptsSeasonMinus1 = [Math]::Max($ptsSeasonMinus1, $ceilingProjected)
    $ptsSeasonMinus2 = [Math]::Max($ptsSeasonMinus2, $ceilingProjected)
    $salaryDollarsProjectedFantasy = MapSalaryFantasy -salary (($ptsCurrent + $ptsSeasonMinus1 + $ptsSeasonMinus2)/3)

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
        SalaryCurrentRaw             = $salaryCurrentRaw
        SalarySeasonStartRaw         = $salarySeasonStartRaw
        SalaryCurrent                = $salaryCurrent
        SalarySeasonStart            = $salarySeasonStart
        SalaryDollars                = $salaryDollars
        SalaryDollarsFantasy         = $salaryDollarsFantasy
        SalaryDollarsCurrent         = $salaryDollarsCurrent
        SalaryDollarsSeasonStart     = $salaryDollarsSeasonStart
        SalaryDollarsProjected       = $salaryDollarsProjected
        SalaryDollarsProjectedFantasy       = $salaryDollarsProjectedFantasy
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
