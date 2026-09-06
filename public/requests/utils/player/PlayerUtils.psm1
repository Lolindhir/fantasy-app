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

function New-PlayerProviderLookups {
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [array]$SleeperPlayers,

        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [array]$TankPlayers
    )

    $sleeperByID = New-UniqueObjectLookup `
        -Items $SleeperPlayers `
        -KeyProperty "player_id" `
        -SourceLabel "Sleeper NFL players" `
        -KeyLabel "player_id" `
        -DescriptionProperties @("player_id", "full_name", "position", "team") `
        -AllowMissingKey

    $tankByID = New-UniqueObjectLookup `
        -Items $TankPlayers `
        -KeyProperty "playerID" `
        -SourceLabel "Tank01 NFL players" `
        -KeyLabel "playerID" `
        -DescriptionProperties @("playerID", "longName", "team", "pos")

    $tankBySleeperID = New-UniqueObjectLookup `
        -Items $TankPlayers `
        -KeyProperty "sleeperBotID" `
        -SourceLabel "Tank01 to Sleeper player mappings" `
        -KeyLabel "sleeperBotID" `
        -DescriptionProperties @("playerID", "longName", "sleeperBotID", "team", "pos") `
        -AllowMissingKey

    return [PSCustomObject][ordered]@{
        SleeperByID     = $sleeperByID
        TankByID        = $tankByID
        TankBySleeperID = $tankBySleeperID
    }
}

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

function New-HistoricalPlayerTankLookup {
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [array]$Players,

        [Parameter(Mandatory = $true)]
        [string]$Season
    )

    return New-UniqueObjectLookup `
        -Items $Players `
        -KeyProperty "TankID" `
        -SourceLabel "historical Players_$Season" `
        -KeyLabel "TankID" `
        -DescriptionProperties @("TankID", "ID", "Name", "TeamID", "Position")
}

function Test-RequiredHistoricalPlayerTankIds {
    $config = Get-Config
    $leagueYear = [int]$config.LeagueYear

    foreach ($offset in 1..3) {
        $season = $leagueYear - $offset
        $filePath = "$($config.PastSeasonPlayersFileHistoricalPrefix)$season$($config.PastSeasonPlayersFileHistoricalSuffix)"
        if (-not (Test-Path $filePath)) {
            continue
        }

        try {
            $players = Get-Content $filePath -Raw | ConvertFrom-Json
        }
        catch {
            throw "Could not parse historical Players_$season at '$filePath'. $_"
        }

        New-HistoricalPlayerTankLookup -Players @($players) -Season ([string]$season) | Out-Null
    }

    return $true
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

    New-UniqueObjectLookup `
        -Items @($Players) `
        -KeyProperty "TankID" `
        -SourceLabel "generated Players.json provider identities" `
        -KeyLabel "TankID" `
        -DescriptionProperties @("TankID", "ID", "Name", "TeamID", "Position") | Out-Null

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

function Compare-Players {
    param(
        [object]$OldPlayers,
        [object]$NewPlayers
    )

    Add-PreviousSeasonCombinedRanking -Players @($NewPlayers) | Out-Null
    Test-RequiredHistoricalPlayerTankIds | Out-Null
    Test-UniquePlayerIds -Players @($NewPlayers) | Out-Null

    if (-not $OldPlayers) {
        return $true
    }

    Test-UniquePlayerIds -Players @($OldPlayers) | Out-Null

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