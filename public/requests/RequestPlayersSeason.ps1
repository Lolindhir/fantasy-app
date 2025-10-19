param (
    [Parameter(Mandatory = $true)]
    [string]$year
)

# --- Validierung des Jahres ---
if ($year -notmatch '^\d{4}$') {
    Write-Error "Please enter a valid year (e.g. 2024)."
    exit 1
}

# --- Verzeichnisstruktur ---
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$dataDir = Join-Path $scriptDir "..\data\past_seasons"

if (-not (Test-Path $dataDir)) {
    New-Item -ItemType Directory -Path $dataDir -Force | Out-Null
}

$InputFile   = Join-Path $dataDir "Games_$year.json"
$OutputFile = Join-Path $dataDir "Players_$year.json"

# --- Existenzprüfung der Spiele-Datei ---
if (-not (Test-Path $InputFile)) {
    Write-Error "File '$InputFile' does not exist."
    exit 1
}

Write-Host "Use data for year $year" -ForegroundColor Cyan
Write-Host "   Input file: $InputFile"
Write-Host "   Output file: $OutputFile"


# --- Load all games ---
$games = Get-Content $InputFile -Raw | ConvertFrom-Json

# --- Determine total weeks in dataset ---
$weeks = @()
foreach ($g in $games) {
    if ($g.gameWeek -match '\d+') {
        $weeks += [int]($matches[0])
    }
}
$weeks = $weeks | Sort-Object -Unique
$potentialGames = ($weeks | Measure-Object).Count - 1
Write-Host "Found $($weeks.Count) weeks -> PotentialGames = $potentialGames" -ForegroundColor Cyan

# --- Dictionary for player aggregation ---
$playersDict = @{}

foreach ($game in $games) {
    if (-not $game.playerStats) { continue }

    foreach ($playerID in $game.playerStats.PSObject.Properties.Name) {
        $p = $game.playerStats.$playerID

        # --- Fantasy Points ---
        $fantasy = $p.fantasyPointsDefault
        $fp      = [double]$fantasy.PPR

        # --- Snap data ---
        $snapCount = 0
        $snapPct   = 0
        if ($p.snapCounts) {
            if ($p.Kicking) {
                $fgAtt = [int]($p.Kicking.fgAttempts)
                $xpAtt = [int]($p.Kicking.xpAttempts)
                $snapCount = $fgAtt + $xpAtt
                $snapPct   = 1
            } else {
                $snapCount = [int]$p.snapCounts.offSnap
                $snapPct   = [double]$p.snapCounts.offSnapPct
            }
        }

        # --- Initialize player ---
        if (-not $playersDict.ContainsKey($playerID)) {
            $playersDict[$playerID] = [PSCustomObject]@{
                playerID             = $p.playerID
                longName             = $p.longName
                teamAbv              = $p.teamAbv
                teamIDs              = @($p.teamID)
                totalFantasyPoints   = 0.0
                totalGames           = 0
                totalSnaps           = 0
                totalSnapPct         = 0.0
            }
        }

        $player = $playersDict[$playerID]

        # --- Accumulate values ---
        $player.totalFantasyPoints        += $fp
        $player.totalGames                += 1
        $player.totalSnaps                += $snapCount
        $player.totalSnapPct              += $snapPct

        # --- Track team switches ---
        if (-not ($player.teamIDs -contains $p.teamID)) {
            $player.teamIDs += $p.teamID
        }

        $player.teamAbv = $p.teamAbv
    }
}

# --- Build final player list ---
$players = @()
foreach ($p in $playersDict.Values) {
    $avgSnapPct = 0
    if ($p.totalGames -gt 0) {
        $avgSnapPct = [math]::Round($p.totalSnapPct / $p.totalGames, 3)
    }

    $totalGames = $p.totalGames
    $avgPoints = 0
    if ($totalGames -gt 0) {
        $avgPoints = [math]::Round($p.totalFantasyPoints / $totalGames, 2)
    }

    $avgPotentialPoints = 0
    if ($potentialGames -gt 0) {
        $avgPotentialPoints        = [math]::Round($p.totalFantasyPoints / $potentialGames, 2)
    }

    $players += [PSCustomObject]@{
        TankID          = $p.playerID
        Name            = $p.longName
        TeamIDs         = $p.teamIDs
        TotalGames      = $totalGames
        PotentialGames  = $potentialGames
        TotalSnaps      = $p.totalSnaps
        AvgSnapPct      = $avgSnapPct
        TotalFantasyPoints              = [math]::Round($p.totalFantasyPoints, 2)
        FantasyPointsAvg                = $avgPoints
        FantasyPointsAvgPotential       = $avgPotentialPoints
    }
}

# --- Export to JSON ---
$players | ConvertTo-Json -Depth 5 | Out-File $OutputFile -Encoding UTF8

Write-Host "Player summary saved to $OutputFile"
