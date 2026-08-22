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
