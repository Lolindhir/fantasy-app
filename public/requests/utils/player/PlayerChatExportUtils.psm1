# ===========================================================================
# 1. Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\..\general\FileUtils.psm1" -ErrorAction Stop -Force
}
catch {
    Write-Error "Fehler beim Laden der Module: $_"
    throw $_
}

# ===========================================================================
# 2. Funktionen
# ===========================================================================

function ConvertTo-PlayerChatLookupKey {
    param(
        [object]$Value
    )

    if ($null -eq $Value) {
        return ""
    }

    $text = ([string]$Value).Trim()
    if ([string]::IsNullOrWhiteSpace($text)) {
        return ""
    }

    return $text.ToLowerInvariant()
}

function Add-PlayerChatLookupValue {
    param(
        [Parameter(Mandatory=$true)]
        [hashtable]$Lookup,

        [string]$Key,

        [string]$PlayerId
    )

    if ([string]::IsNullOrWhiteSpace($Key) -or [string]::IsNullOrWhiteSpace($PlayerId)) {
        return
    }

    if (-not $Lookup.ContainsKey($Key)) {
        $Lookup[$Key] = @()
    }

    if ($Lookup[$Key] -notcontains $PlayerId) {
        $Lookup[$Key] += $PlayerId
    }
}

function Compare-PlayerChatJsonData {
    param(
        [object]$OldData,
        [object]$NewData
    )

    if (-not $OldData) {
        return $true
    }

    $oldJson = $OldData | ConvertTo-Json -Depth 20 -Compress
    $newJson = $NewData | ConvertTo-Json -Depth 20 -Compress

    return ($oldJson -ne $newJson)
}

function Export-PlayersForChatChunks {
    param(
        [Parameter(Mandatory=$true)]
        [array]$Players,

        [Parameter(Mandatory=$true)]
        [string]$TargetDirectory,

        [int]$ChunkSize = 10,

        [string]$Source = "Players_Relevant.json"
    )

    if ($ChunkSize -le 0) {
        throw "ChunkSize must be greater than 0."
    }

    if (-not (Test-Path $TargetDirectory)) {
        New-Item -ItemType Directory -Path $TargetDirectory -Force | Out-Null
    }

    $compareJson = {
        param($oldData, $newData)
        Compare-PlayerChatJsonData -OldData $oldData -NewData $newData
    }

    $playersArray = @($Players)
    $playerCount = $playersArray.Count
    $chunkCount = if ($playerCount -gt 0) { [int][math]::Ceiling($playerCount / $ChunkSize) } else { 0 }

    $files = @()
    $playerLookup = [ordered]@{}
    $nameLookup = @{}
    $positionLookup = @{}
    $teamLookup = @{}

    for ($chunkIndex = 0; $chunkIndex -lt $chunkCount; $chunkIndex++) {
        $startIndex = $chunkIndex * $ChunkSize
        $endIndex = [math]::Min($startIndex + $ChunkSize - 1, $playerCount - 1)
        $chunk = @($playersArray[$startIndex..$endIndex])
        $fileName = "players_{0:D4}.json" -f ($chunkIndex + 1)
        $targetFile = Join-Path $TargetDirectory $fileName

        Save-JsonFile -TargetFile $targetFile -Data $chunk -CompareScript $compareJson

        $filePlayerIds = @()
        $fileNames = @()

        for ($indexInChunk = 0; $indexInChunk -lt $chunk.Count; $indexInChunk++) {
            $player = $chunk[$indexInChunk]
            $playerId = [string]$player.ID

            if ([string]::IsNullOrWhiteSpace($playerId)) {
                continue
            }

            $filePlayerIds += $playerId
            $fileNames += $player.Name

            $playerLookup[$playerId] = [PSCustomObject]@{
                File            = $fileName
                ChunkIndex      = $chunkIndex
                IndexInFile     = $indexInChunk
                Name            = $player.Name
                Position        = $player.Position
                TeamID          = $player.TeamID
                TeamAbbr        = $player.TeamAbbr
                IsFreeAgent     = $player.IsFreeAgent
                Year            = $player.Year
                Age             = $player.Age
                Salary          = $player.Salary
                SalaryProjected = $player.SalaryProjected
            }

            $nameKeys = @(
                (ConvertTo-PlayerChatLookupKey $player.Name),
                (ConvertTo-PlayerChatLookupKey $player.NameShort),
                (ConvertTo-PlayerChatLookupKey "$($player.NameFirst) $($player.NameLast)")
            ) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Sort-Object -Unique

            foreach ($nameKey in $nameKeys) {
                Add-PlayerChatLookupValue -Lookup $nameLookup -Key $nameKey -PlayerId $playerId
            }

            Add-PlayerChatLookupValue -Lookup $positionLookup -Key (ConvertTo-PlayerChatLookupKey $player.Position) -PlayerId $playerId
            Add-PlayerChatLookupValue -Lookup $teamLookup -Key (ConvertTo-PlayerChatLookupKey $player.TeamAbbr) -PlayerId $playerId
        }

        $files += [PSCustomObject]@{
            File      = $fileName
            FromIndex = $startIndex
            ToIndex   = $endIndex
            PlayerIDs = $filePlayerIds
            Names     = $fileNames
        }
    }

    $index = [PSCustomObject]@{
        Source         = $Source
        ChunkSize      = $ChunkSize
        PlayerCount    = $playerCount
        ChunkCount     = $chunkCount
        Files          = $files
        PlayerLookup   = $playerLookup
        NameLookup     = $nameLookup
        PositionLookup = $positionLookup
        TeamLookup     = $teamLookup
    }

    Save-JsonFile -TargetFile (Join-Path $TargetDirectory "index.json") -Data $index -CompareScript $compareJson
    Write-Host "Player chat export ready: $playerCount players in $chunkCount chunks ($TargetDirectory)" -ForegroundColor Yellow
}
