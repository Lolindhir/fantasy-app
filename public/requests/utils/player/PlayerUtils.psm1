# ===========================================================================
# 1. Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\..\ConfigUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\general\ProviderJoinUtils.psm1" -ErrorAction Stop -Force
}
catch {
    Write-Error "Fehler beim Laden der Module: $_"
    throw $_
}

# ===========================================================================
# 2. Funktionen
# ===========================================================================

function Get-AppFantasyPosition {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        $SleeperPlayer
    )

    $allowedPositions = @("TE", "QB", "RB", "WR", "K")
    $primaryPosition = ([string]$SleeperPlayer.position).Trim().ToUpperInvariant()

    if ($primaryPosition -in $allowedPositions) {
        return $primaryPosition
    }

    foreach ($fantasyPosition in @($SleeperPlayer.fantasy_positions)) {
        $candidate = ([string]$fantasyPosition).Trim().ToUpperInvariant()
        if ($candidate -in $allowedPositions) {
            return $candidate
        }
    }

    return $null
}

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

    if ($playersWithoutId.Count -gt 0 -or $duplicateGroups.Count -gt 0) {
        $errorLines = @(
            "Player data validation failed. Players.json will not be overwritten; the last known good file is preserved."
        )

        if ($playersWithoutId.Count -gt 0) {
            $errorLines += "Missing canonical Players.ID on $($playersWithoutId.Count) record(s):"

            foreach ($player in $playersWithoutId) {
                $name = if ($null -ne $player.Name -and -not [string]::IsNullOrWhiteSpace([string]$player.Name)) { [string]$player.Name } else { "<missing>" }
                $teamId = if ($null -ne $player.TeamID -and -not [string]::IsNullOrWhiteSpace([string]$player.TeamID)) { [string]$player.TeamID } else { "<missing>" }
                $position = if ($null -ne $player.Position -and -not [string]::IsNullOrWhiteSpace([string]$player.Position)) { [string]$player.Position } else { "<missing>" }

                $errorLines += "- ID=<missing>; Name='$name'; TeamID=$teamId; Position=$position"
            }
        }

        if ($duplicateGroups.Count -gt 0) {
            $errorLines += "Duplicate canonical Players.ID values detected: $($duplicateGroups.Count)"

            foreach ($group in $duplicateGroups) {
                $recordSummaries = @(
                    @($group.Value) | ForEach-Object {
                        $name = if ($null -ne $_.Name -and -not [string]::IsNullOrWhiteSpace([string]$_.Name)) { [string]$_.Name } else { "<missing>" }
                        $teamId = if ($null -ne $_.TeamID -and -not [string]::IsNullOrWhiteSpace([string]$_.TeamID)) { [string]$_.TeamID } else { "<missing>" }
                        $position = if ($null -ne $_.Position -and -not [string]::IsNullOrWhiteSpace([string]$_.Position)) { [string]$_.Position } else { "<missing>" }

                        "Name='$name'; TeamID=$teamId; Position=$position"
                    }
                )

                $errorLines += "- ID=$($group.Name): $($recordSummaries -join ' | ')"
            }
        }

        throw ($errorLines -join [Environment]::NewLine)
    }

    # Players.json no longer carries a provider ID (TankID removed with #347 H1b); the canonical Sleeper ID is the key.
    return $true
}

function Add-PreviousSeasonCombinedRanking {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]
        [AllowEmptyCollection()]
        [array]$Players
    )

    $config = Get-Config
    $weightTotal = [double]$config.WeightTotal
    $weightGame = [double]$config.WeightGame

    foreach ($player in @($Players)) {
        $player.Ranking = @($player.Ranking | Where-Object { $_.Type -ne 'Combined_Previous' })
    }

    $playersWithHistory = @(
        $Players | Where-Object {
            $null -ne $_.PointHistory -and
            $null -ne $_.PointHistory.SeasonMinus1 -and
            [double]$_.PointHistory.SeasonMinus1.AvgPotentialGame -gt 0 -and
            [double]$_.PointHistory.SeasonMinus1.AvgGame -gt 0
        }
    )

    if ($playersWithHistory.Count -eq 0) {
        return $Players
    }

    function Get-HistoricalRankMap {
        param(
            [Parameter(Mandatory=$true)][array]$Items,
            [Parameter(Mandatory=$true)][scriptblock]$ValueSelector
        )

        $rankMap = @{}
        $sorted = @(
            $Items | Sort-Object -Property @{ Expression = { & $ValueSelector $_ }; Descending = $true }
        )
        $previousValue = $null
        $rank = 0
        $index = 0

        foreach ($item in $sorted) {
            $index++
            $value = [double](& $ValueSelector $item)
            if ($null -eq $previousValue -or $value -ne $previousValue) {
                $rank = $index
            }
            $previousValue = $value
            $rankMap[[string]$item.ID] = $rank
        }

        return $rankMap
    }

    $totalSelector = { param($player) [double]$player.PointHistory.SeasonMinus1.AvgPotentialGame }
    $gameSelector = { param($player) [double]$player.PointHistory.SeasonMinus1.AvgGame }
    $totalRanks = Get-HistoricalRankMap -Items $playersWithHistory -ValueSelector $totalSelector
    $gameRanks = Get-HistoricalRankMap -Items $playersWithHistory -ValueSelector $gameSelector

    $combinedRows = @(
        foreach ($player in $playersWithHistory) {
            $playerId = [string]$player.ID
            [PSCustomObject]@{
                Player = $player
                CombinedValue = ([double]$totalRanks[$playerId] * $weightTotal) + ([double]$gameRanks[$playerId] * $weightGame)
                TotalValue = [double]$player.PointHistory.SeasonMinus1.AvgPotentialGame
                GameValue = [double]$player.PointHistory.SeasonMinus1.AvgGame
            }
        }
    ) | Sort-Object -Property @{ Expression = 'CombinedValue'; Ascending = $true },
                               @{ Expression = 'TotalValue'; Descending = $true },
                               @{ Expression = 'GameValue'; Descending = $true }

    $previousCombinedValue = $null
    $combinedRank = 0
    $combinedIndex = 0

    foreach ($row in $combinedRows) {
        $combinedIndex++
        if ($null -eq $previousCombinedValue -or $row.CombinedValue -ne $previousCombinedValue) {
            $combinedRank = $combinedIndex
        }
        $previousCombinedValue = $row.CombinedValue
        $row.Player.Ranking += [PSCustomObject]@{
            Type = 'Combined_Previous'
            Value = $combinedRank
        }
    }

    return $Players
}

# Serialization depth used when RequestPlayers writes Players.json. The change comparison must use
# the same depth: freshly built objects are deeper than the published file (for example
# Grading[].Value[].GameDetails is cut to its type name at this depth), so comparing at a larger
# depth reports a change on every run although the written file stays identical.
$script:PlayersPublishedJsonDepth = 5

function Get-PlayersPublishedJsonDepth {
    return $script:PlayersPublishedJsonDepth
}

function ConvertTo-PublishedPlayersComparable {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]
        [AllowEmptyCollection()]
        [object]$Players
    )

    # Serialize like the published file, then re-parse so freshly built and file-loaded objects
    # share the same types before the sorted, compressed comparison string is produced.
    $depth = Get-PlayersPublishedJsonDepth
    $published = @($Players | Sort-Object -Property ID) | ConvertTo-Json -Depth $depth -Compress -WarningAction SilentlyContinue
    return ($published | ConvertFrom-Json) | ConvertTo-Json -Depth $depth -Compress -WarningAction SilentlyContinue
}

function Compare-Players {
    param(
        [object]$OldPlayers,
        [object]$NewPlayers
    )

    Add-PreviousSeasonCombinedRanking -Players @($NewPlayers) | Out-Null
    Test-UniquePlayerIds -Players @($NewPlayers) | Out-Null

    if (-not $OldPlayers) {
        return $true
    }

    Test-UniquePlayerIds -Players @($OldPlayers) | Out-Null

    if ($OldPlayers.Count -ne $NewPlayers.Count) {
        Write-Host "Player count changed: $($OldPlayers.Count) -> $($NewPlayers.Count)"
        return $true
    }

    $oldPlayersJson = ConvertTo-PublishedPlayersComparable -Players $OldPlayers
    $newPlayersJson = ConvertTo-PublishedPlayersComparable -Players $NewPlayers

    if ($oldPlayersJson -ne $newPlayersJson) {
        Write-Host "Player data changed."
        return $true
    }

    return $false
}