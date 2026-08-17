# ===========================================================================
# 1. Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\..\ConfigUtils.psm1" -ErrorAction Stop -Force
}
catch {
    Write-Error "Fehler beim Laden der Module: $_"
    throw $_
}

# ===========================================================================
# 2. Funktionen
# ===========================================================================

function Get-PlayersFromFile {
    param(
        [string]$PlayersFile = (Get-Config).PlayersFile
    )

    try {
        # --- Spieler-Daten holen---
        if (!(Test-Path $PlayersFile)) {
            throw "Players.json not found at '$PlayersFile'!"
        }
        $playersJson = Get-Content $PlayersFile -Raw
        if (-not $playersJson) {
            throw "Players.json is empty!"
        }
        $playersData = $playersJson | ConvertFrom-Json
        if (-not $playersData -or $playersData.Count -eq 0) {
            throw "No valid players found in Players.json!"
        }

        return $playersData
    }
    catch {
        Write-Error "Failed to read or parse Players file: $_"
        throw $_
    }
}

function Test-UniquePlayerIds {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]
        [AllowEmptyCollection()]
        [array]$Players
    )

    $playersById = @{}
    $playersWithoutId = @()

    foreach ($player in @($Players)) {
        $playerId = [string]$player.ID

        if ([string]::IsNullOrWhiteSpace($playerId)) {
            $playersWithoutId += $player
            continue
        }

        if (-not $playersById.ContainsKey($playerId)) {
            $playersById[$playerId] = @()
        }

        $playersById[$playerId] = @($playersById[$playerId]) + @($player)
    }

    $duplicateGroups = @(
        $playersById.GetEnumerator() |
            Where-Object { @($_.Value).Count -gt 1 } |
            Sort-Object -Property Name
    )

    if ($playersWithoutId.Count -eq 0 -and $duplicateGroups.Count -eq 0) {
        return $true
    }

    $errorLines = @(
        "Player data validation failed. Players.json will not be overwritten; the last known good file is preserved."
    )

    if ($playersWithoutId.Count -gt 0) {
        $errorLines += "Missing canonical Players.ID on $($playersWithoutId.Count) record(s):"

        foreach ($player in $playersWithoutId) {
            $tankId = if ($null -ne $player.TankID -and -not [string]::IsNullOrWhiteSpace([string]$player.TankID)) { [string]$player.TankID } else { "<missing>" }
            $name = if ($null -ne $player.Name -and -not [string]::IsNullOrWhiteSpace([string]$player.Name)) { [string]$player.Name } else { "<missing>" }
            $teamId = if ($null -ne $player.TeamID -and -not [string]::IsNullOrWhiteSpace([string]$player.TeamID)) { [string]$player.TeamID } else { "<missing>" }
            $position = if ($null -ne $player.Position -and -not [string]::IsNullOrWhiteSpace([string]$player.Position)) { [string]$player.Position } else { "<missing>" }

            $errorLines += "- ID=<missing>; TankID=$tankId; Name='$name'; TeamID=$teamId; Position=$position"
        }
    }

    if ($duplicateGroups.Count -gt 0) {
        $errorLines += "Duplicate canonical Players.ID values detected: $($duplicateGroups.Count)"

        foreach ($group in $duplicateGroups) {
            $recordSummaries = @(
                @($group.Value) | ForEach-Object {
                    $tankId = if ($null -ne $_.TankID -and -not [string]::IsNullOrWhiteSpace([string]$_.TankID)) { [string]$_.TankID } else { "<missing>" }
                    $name = if ($null -ne $_.Name -and -not [string]::IsNullOrWhiteSpace([string]$_.Name)) { [string]$_.Name } else { "<missing>" }
                    $teamId = if ($null -ne $_.TeamID -and -not [string]::IsNullOrWhiteSpace([string]$_.TeamID)) { [string]$_.TeamID } else { "<missing>" }
                    $position = if ($null -ne $_.Position -and -not [string]::IsNullOrWhiteSpace([string]$_.Position)) { [string]$_.Position } else { "<missing>" }

                    "TankID=$tankId; Name='$name'; TeamID=$teamId; Position=$position"
                }
            )

            $errorLines += "- ID=$($group.Name): $($recordSummaries -join ' | ')"
        }
    }

    throw ($errorLines -join [Environment]::NewLine)
}

function Compare-Players {
    param(
        [object]$OldPlayers,
        [object]$NewPlayers
    )

    Test-UniquePlayerIds -Players @($NewPlayers) | Out-Null

    if (-not $OldPlayers) {
        return $true
    }

    if ($OldPlayers.Count -ne $NewPlayers.Count) {
        Write-Host "Player count changed: $($OldPlayers.Count) -> $($NewPlayers.Count)"
        return $true
    }

    $oldPlayersJson = @($OldPlayers | Sort-Object -Property ID) | ConvertTo-Json -Depth 20 -Compress
    $newPlayersJson = @($NewPlayers | Sort-Object -Property ID) | ConvertTo-Json -Depth 20 -Compress

    if ($oldPlayersJson -ne $newPlayersJson) {
        Write-Host "Player data changed."
        return $true
    }

    return $false
}

function Get-NumberOrZero {
    param(
        [object]$Value
    )

    if ($null -eq $Value) {
        return 0.0
    }

    try {
        return [double]$Value
    }
    catch {
        return 0.0
    }
}

function Get-FantasyRosteredPlayerIds {
    param(
        [Parameter(Mandatory=$true)]
        [array]$Teams
    )

    $playerIds = @{}
    $rosterProperties = @("Roster", "Reserve", "Taxi", "Starter")

    foreach ($team in @($Teams)) {
        foreach ($property in $rosterProperties) {
            if ($team.PSObject.Properties.Name -notcontains $property) {
                continue
            }

            foreach ($playerId in @($team.$property)) {
                if ($null -eq $playerId -or [string]::IsNullOrWhiteSpace([string]$playerId)) {
                    continue
                }

                $playerIds[[string]$playerId] = $true
            }
        }
    }

    return $playerIds
}

function Get-PlayerPointHistoryMetrics {
    param(
        [Parameter(Mandatory=$true)]
        [object]$Player
    )

    $history = $Player.PointHistory
    $seasonMinus1 = if ($history -and $history.SeasonMinus1) { $history.SeasonMinus1 } else { $null }
    $seasonMinus2 = if ($history -and $history.SeasonMinus2) { $history.SeasonMinus2 } else { $null }
    $seasonMinus3 = if ($history -and $history.SeasonMinus3) { $history.SeasonMinus3 } else { $null }

    $seasonMinus1Total = Get-NumberOrZero $seasonMinus1.Total
    $seasonMinus2Total = Get-NumberOrZero $seasonMinus2.Total
    $seasonMinus3Total = Get-NumberOrZero $seasonMinus3.Total

    $avgPotentialValues = @(
        (Get-NumberOrZero $seasonMinus1.AvgPotentialGame),
        (Get-NumberOrZero $seasonMinus2.AvgPotentialGame),
        (Get-NumberOrZero $seasonMinus3.AvgPotentialGame)
    )

    $weightedPoints =
        ($seasonMinus1Total * 0.6) +
        ($seasonMinus2Total * 0.3) +
        ($seasonMinus3Total * 0.1)

    return [PSCustomObject]@{
        WeightedPoints      = [math]::Round($weightedPoints, 2)
        MaxAvgPotentialGame = ($avgPotentialValues | Measure-Object -Maximum).Maximum
    }
}

function Test-PlayerHistoricalProduction {
    param(
        [Parameter(Mandatory=$true)]
        [object]$Player
    )

    $metrics = Get-PlayerPointHistoryMetrics -Player $Player
    $weightedPoints = Get-NumberOrZero $metrics.WeightedPoints
    $maxAvgPotentialGame = Get-NumberOrZero $metrics.MaxAvgPotentialGame

    switch ($Player.Position) {
        "QB" {
            return ($weightedPoints -ge 25 -or $maxAvgPotentialGame -ge 2.5)
        }
        "RB" {
            return ($weightedPoints -ge 50 -or $maxAvgPotentialGame -ge 5)
        }
        "WR" {
            return ($weightedPoints -ge 50 -or $maxAvgPotentialGame -ge 5)
        }
        "TE" {
            return ($weightedPoints -ge 30 -or $maxAvgPotentialGame -ge 3)
        }
        "K" {
            return ($weightedPoints -ge 30 -or $maxAvgPotentialGame -ge 4)
        }
        default {
            return $false
        }
    }
}

function Get-PlayerRelevantReasons {
    param(
        [Parameter(Mandatory=$true)]
        [object]$Player,

        [Parameter(Mandatory=$true)]
        [hashtable]$FantasyRosteredPlayerIds
    )

    $reasons = @()
    $playerId = [string]$Player.ID

    if ($FantasyRosteredPlayerIds.ContainsKey($playerId)) {
        $reasons += "FantasyRostered"
    }

    if ($Player.Status -eq "Retired") {
        return $reasons
    }

    $year = Get-NumberOrZero $Player.Year
    if ($year -gt 0 -and $year -le 2) {
        $reasons += "YoungProspect"
    }

    if (Test-PlayerHistoricalProduction -Player $Player) {
        $reasons += "HistoricalProduction"
    }

    $maxSalary = [math]::Max(
        (Get-NumberOrZero $Player.Salary),
        (Get-NumberOrZero $Player.SalaryProjected)
    )

    if ($Player.IsFreeAgent -ne $true -and $maxSalary -ge 2000000) {
        $reasons += "HighSalarySignal"
    }

    return $reasons
}

function Get-RelevantPlayers {
    param(
        [Parameter(Mandatory=$true)]
        [array]$Players,

        [Parameter(Mandatory=$true)]
        [array]$Teams
    )

    $fantasyRosteredPlayerIds = Get-FantasyRosteredPlayerIds -Teams $Teams
    $reasonCounts = @{}
    $relevantPlayers = @()

    foreach ($player in @($Players)) {
        $reasons = @(Get-PlayerRelevantReasons `
            -Player $player `
            -FantasyRosteredPlayerIds $fantasyRosteredPlayerIds)

        if ($reasons.Count -eq 0) {
            continue
        }

        $relevantPlayers += $player

        foreach ($reason in $reasons) {
            if (-not $reasonCounts.ContainsKey($reason)) {
                $reasonCounts[$reason] = 0
            }

            $reasonCounts[$reason]++
        }
    }

    $relevantPlayers = @($relevantPlayers | Sort-Object -Property ID)

    Write-Host "Relevant players selected: $($relevantPlayers.Count) / $($Players.Count)" -ForegroundColor Yellow
    foreach ($reason in @("FantasyRostered", "YoungProspect", "HistoricalProduction", "HighSalarySignal")) {
        $count = if ($reasonCounts.ContainsKey($reason)) { $reasonCounts[$reason] } else { 0 }
        Write-Host "- $reason`: $count" -ForegroundColor DarkGray
    }

    return $relevantPlayers
}
