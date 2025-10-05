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
            'Number',
            'Picture',
            'SalaryCurrentRaw',
            'SalarySeasonStartRaw',
            'SalaryCurrent',
            'SalarySeasonStart',
            'SalaryDollars',
            'SalaryDollarsCurrent',
            'SalaryDollarsSeasonStart',
            'SalaryDollarsProjected'
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
    $Global:RapidAPIKeyAlt1
    # , $Global:RapidAPIKeyAlt2
)
$Date = (Get-Date -Format "yyyyMMdd")
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$targetFile = Join-Path $scriptDir "..\data\Players.json"
$backupDir = Join-Path $scriptDir "..\data\backup"
if (!(Test-Path $backupDir)) { New-Item -ItemType Directory -Path $backupDir -Force | Out-Null }

# --- Season Start Datum aus config.ps1 ---
if (-not $Global:LeagueStart) {
    Write-Error "LeagueStart not set in config.ps1!"
    exit 1
}
$seasonStartDate = $Global:LeagueStart


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

    # --- PlayerID ---
    $playerID = $sleeperEntry.player_id
    # --- Year berechnen ---
    $year = $sleeperEntry.years_exp + 1
    # --- Age ---
    $age = $sleeperEntry.age
    # --- Position ---
    $position = $sleeperEntry.position

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

    # --- Player Objekt bauen ---
    $playerData += [PSCustomObject]@{
        ID                           = $playerID
        TankID                       = $tankEntry.playerID
        Name                         = $sleeperEntry.full_name
        NameFirst                    = $sleeperEntry.first_name
        NameLast                     = $sleeperEntry.last_name
        NameShort                    = $tankEntry.cbsShortName
        Status                       = $sleeperEntry.status
        Position                     = $position
        Age                          = $age
        Year                         = $year
        SalaryCurrentRaw             = $salaryCurrentRaw
        SalarySeasonStartRaw         = $salarySeasonStartRaw
        SalaryCurrent                = $salaryCurrent
        SalarySeasonStart            = $salarySeasonStart
        SalaryDollars                = $salaryDollars
        SalaryDollarsCurrent         = $salaryDollarsCurrent
        SalaryDollarsSeasonStart     = $salaryDollarsSeasonStart
        SalaryDollarsProjected       = $salaryDollarsProjected
        TeamID                       = $tankEntry.teamID
        Number                       = $tankEntry.jerseyNum
        Picture                      = $tankEntry.espnHeadshot
    }
}

# Spieler nach ID aufsteigend sortieren
$playerData = $playerData | Sort-Object -Property ID

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
