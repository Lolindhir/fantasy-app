function Get-GfuPropertyValue {
    param(
        [AllowNull()][object]$Object,
        [Parameter(Mandatory = $true)][string[]]$Names
    )

    if ($null -eq $Object) { return $null }
    foreach ($name in $Names) {
        if ($Object.PSObject.Properties.Name -contains $name) {
            return $Object.$name
        }
    }
    return $null
}

function Get-CanonicalGameFinalityByEspnID {
    param(
        [Parameter(Mandatory = $true)][int]$Season,
        [Parameter(Mandatory = $true)][string]$RepoRoot
    )

    $canonicalSchedulePath = Join-Path $RepoRoot "source-data/nfl/schedules/$Season.json"
    $canonicalFinalityPath = Join-Path $RepoRoot "source-data/nfl/game-finality/$Season.json"

    if (-not (Test-Path $canonicalSchedulePath)) {
        throw "Canonical NFL schedule is required for game finality resolution: $canonicalSchedulePath"
    }
    if (-not (Test-Path $canonicalFinalityPath)) {
        throw "Canonical NFL game finality is required for game finality resolution: $canonicalFinalityPath"
    }

    $canonicalSchedule = Get-Content $canonicalSchedulePath -Raw | ConvertFrom-Json
    $canonicalFinality = Get-Content $canonicalFinalityPath -Raw | ConvertFrom-Json

    if ([int]$canonicalSchedule.Season -ne $Season) {
        throw "Canonical NFL schedule season mismatch: expected $Season, got $($canonicalSchedule.Season)."
    }
    if ([int]$canonicalFinality.Season -ne $Season) {
        throw "Canonical NFL game finality season mismatch: expected $Season, got $($canonicalFinality.Season)."
    }
    if ([string]$canonicalSchedule.SourceDataset -ne 'nflverse.schedules') {
        throw "Unexpected canonical NFL schedule source '$($canonicalSchedule.SourceDataset)'."
    }
    if ([string]$canonicalFinality.SourceDataset -ne 'nflverse.game-finality') {
        throw "Unexpected canonical NFL finality source '$($canonicalFinality.SourceDataset)'."
    }

    $finalityByGameID = @{}
    foreach ($game in @($canonicalFinality.Games)) {
        $gameID = [string](Get-GfuPropertyValue -Object $game -Names @('GameID'))
        if ([string]::IsNullOrWhiteSpace($gameID)) {
            throw "Canonical NFL game-finality row is missing GameID."
        }
        if ($finalityByGameID.ContainsKey($gameID)) {
            throw "Duplicate canonical NFL game-finality GameID '$gameID'."
        }
        $finalityByGameID[$gameID] = [bool](Get-GfuPropertyValue -Object $game -Names @('Final'))
    }

    $byEspnID = @{}
    foreach ($game in @($canonicalSchedule.Games)) {
        $gameID = [string](Get-GfuPropertyValue -Object $game -Names @('GameID'))
        if ([string]::IsNullOrWhiteSpace($gameID)) {
            throw "Canonical NFL schedule row is missing GameID."
        }
        if (-not $finalityByGameID.ContainsKey($gameID)) {
            throw "Canonical NFL finality is missing schedule GameID '$gameID'."
        }

        $providerIDs = Get-GfuPropertyValue -Object $game -Names @('ProviderGameIDs')
        $espnID = [string](Get-GfuPropertyValue -Object $providerIDs -Names @('ESPN'))
        if ([string]::IsNullOrWhiteSpace($espnID)) {
            continue
        }
        $espnID = $espnID.Trim()
        if ($byEspnID.ContainsKey($espnID)) {
            throw "Duplicate canonical ESPN game mapping '$espnID'."
        }

        $byEspnID[$espnID] = [PSCustomObject][ordered]@{
            GameID = $gameID
            Final  = [bool]$finalityByGameID[$gameID]
        }
    }

    if ($byEspnID.Count -eq 0) {
        throw "Canonical NFL schedule contains no ESPN game mappings for season $Season."
    }

    return $byEspnID
}

function Resolve-CanonicalGameFinalitySchedule {
    param(
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$Schedule,
        [Parameter(Mandatory = $true)][int]$Season,
        [Parameter(Mandatory = $true)][string]$RepoRoot
    )

    $canonicalByEspnID = Get-CanonicalGameFinalityByEspnID -Season $Season -RepoRoot $RepoRoot
    $promotedCount = 0

    foreach ($game in @($Schedule)) {
        $legacyGameID = [string](Get-GfuPropertyValue -Object $game -Names @('gameID','GameID'))
        $espnID = [string](Get-GfuPropertyValue -Object $game -Names @('espnID','EspnID','ESPN'))
        if ([string]::IsNullOrWhiteSpace($espnID)) {
            throw "Legacy NFL schedule game '$legacyGameID' is missing the ESPN provider ID required for canonical finality."
        }
        $espnID = $espnID.Trim()
        if (-not $canonicalByEspnID.ContainsKey($espnID)) {
            throw "Legacy NFL schedule game '$legacyGameID' ESPN '$espnID' has no canonical schedule mapping for season $Season."
        }

        $canonical = $canonicalByEspnID[$espnID]
        $legacyStatus = [string](Get-GfuPropertyValue -Object $game -Names @('gameStatus','Status'))
        $legacyClaimsFinal = -not [string]::IsNullOrWhiteSpace($legacyStatus) -and $legacyStatus -match '^Final'

        if ([bool]$canonical.Final) {
            if (-not $legacyClaimsFinal) {
                if ($game.PSObject.Properties.Name -contains 'gameStatus') {
                    $game.gameStatus = 'Final'
                }
                else {
                    $game | Add-Member -NotePropertyName gameStatus -NotePropertyValue 'Final'
                }

                if ($game.PSObject.Properties.Name -contains 'gameStatusCode') {
                    $game.gameStatusCode = '2'
                }
                else {
                    $game | Add-Member -NotePropertyName gameStatusCode -NotePropertyValue '2'
                }
                $promotedCount++
            }
            continue
        }

        if ($legacyClaimsFinal) {
            throw "Legacy NFL schedule claims Final for '$legacyGameID' (ESPN '$espnID') while canonical game '$($canonical.GameID)' is not Final."
        }
    }

    if ($promotedCount -gt 0) {
        Write-Host "Canonical NFL finality promoted $promotedCount schedule game(s) to Final." -ForegroundColor Green
    }
    else {
        Write-Host "Canonical NFL finality produced no schedule status changes." -ForegroundColor DarkGray
    }

    return @($Schedule)
}

Export-ModuleMember -Function Get-CanonicalGameFinalityByEspnID, Resolve-CanonicalGameFinalitySchedule
