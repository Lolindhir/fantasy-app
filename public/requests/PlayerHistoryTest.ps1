# --- Konfiguration ---
. "$PSScriptRoot\config.ps1"
$apiKeys = @(
    $Global:RapidAPIKey,
    $Global:RapidAPIKeyAlt1
)
$PlayerTankID = "4595348"   # <-- Hier die Tank01 PlayerID eintragen
$DatesToCheck = @(
    "20241215"
)   # <-- Liste der Datumswerte, yyyyMMdd

# --- Globale Funktionen ---
$Global:CurrentApiKey = $null

function Invoke-Tank01-With-Fallback {
    param([string]$Url, [string[]]$Keys)
    $delay = 2
    if ($Global:CurrentApiKey -and $Keys -contains $Global:CurrentApiKey) {
        $headers = @{ "X-RapidAPI-Key" = $Global:CurrentApiKey; "X-RapidAPI-Host" = "tank01-nfl-live-in-game-real-time-statistics-nfl.p.rapidapi.com" }
        try { return Invoke-RestMethod -Uri $Url -Headers $headers -ErrorAction Stop } catch { $Global:CurrentApiKey = $null }
    }
    foreach ($key in $Keys) {
        $headers = @{ "X-RapidAPI-Key" = $key; "X-RapidAPI-Host" = "tank01-nfl-live-in-game-real-time-statistics-nfl.p.rapidapi.com" }
        try { $Global:CurrentApiKey = $key; return Invoke-RestMethod -Uri $Url -Headers $headers -ErrorAction Stop } catch { Start-Sleep -Seconds $delay; continue }
    }
    throw "All API keys failed"
}

function Get-DraftKings($dateStr, $apiKeys) {
    $dfsUrl = "https://tank01-nfl-live-in-game-real-time-statistics-nfl.p.rapidapi.com/getNFLDFS?date=$dateStr"
    try { $dfsResponse = Invoke-Tank01-With-Fallback -Url $dfsUrl -Keys $apiKeys } catch { return $null }
    return $dfsResponse.body.draftkings
}

# --- Salary für Liste von Datumswerten abrufen ---
$SalaryHistory = @()

foreach ($dateStr in $DatesToCheck) {
    $salary = 0
    $daysChecked = 0
    $currentDate = [datetime]::ParseExact($dateStr, 'yyyyMMdd', $null)

    while ($salary -eq 0 -and $daysChecked -lt 10) {
        $currentDateStr = $currentDate.ToString("yyyyMMdd")
        $draftKings = Get-DraftKings $currentDateStr $apiKeys

        if ($draftKings) {
            $entry = $draftKings | Where-Object { $_.playerID -eq $PlayerTankID }
            if ($entry -and $entry.salary -gt 0) {
                $salary = $entry.salary
            }
        }

        if ($salary -eq 0) {
            # einen Tag zurück
            $currentDate = $currentDate.AddDays(-1)
            $daysChecked++
        }
    }

    $SalaryHistory += [PSCustomObject]@{
        RequestedDate = $dateStr
        SalaryDate = $currentDate.ToString("yyyyMMdd")
        Salary = $salary
    }
}

# --- Ausgabe ---
$SalaryHistory | Sort-Object RequestedDate | Format-Table -AutoSize
