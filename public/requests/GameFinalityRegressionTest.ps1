$ErrorActionPreference = 'Stop'

Import-Module "$PSScriptRoot\utils\general\GameFinalityUtils.psm1" -Force

function Assert-GfrEqual {
    param($Expected, $Actual, [string]$Message)
    if ([string]$Expected -ne [string]$Actual) {
        throw "ASSERTION FAILED: $Message. Expected '$Expected', got '$Actual'."
    }
}

function Assert-GfrTrue {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw "ASSERTION FAILED: $Message" }
}

$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("fantasy-game-finality-" + [guid]::NewGuid().ToString('N'))
try {
    $canonicalScheduleDir = Join-Path $tempRoot 'data-source/nfl/schedules'
    $canonicalFinalityDir = Join-Path $tempRoot 'data-source/nfl/game-finality'
    New-Item -ItemType Directory -Path $canonicalScheduleDir -Force | Out-Null
    New-Item -ItemType Directory -Path $canonicalFinalityDir -Force | Out-Null

    $canonicalSchedule = [PSCustomObject][ordered]@{
        SchemaVersion = 2
        Season = 2026
        SourceDataset = 'nflverse.schedules'
        Finalized = $false
        Games = @(
            [PSCustomObject][ordered]@{
                GameID = '2026_01_NE_SEA'
                GameType = 'REG'
                Week = 1
                ProviderGameIDs = [PSCustomObject]@{ ESPN = '401872656' }
            }
        )
    }
    $canonicalFinality = [PSCustomObject][ordered]@{
        SchemaVersion = 2
        Season = 2026
        SourceDataset = 'nflverse.game-finality'
        ScheduleDataset = 'nflverse.schedules'
        Finalized = $false
        Games = @(
            [PSCustomObject][ordered]@{
                GameID = '2026_01_NE_SEA'
                GameType = 'REG'
                Week = 1
                Final = $true
            }
        )
        Weeks = @()
    }
    $canonicalSchedule | ConvertTo-Json -Depth 10 | Set-Content (Join-Path $canonicalScheduleDir '2026.json') -Encoding UTF8
    $canonicalFinality | ConvertTo-Json -Depth 10 | Set-Content (Join-Path $canonicalFinalityDir '2026.json') -Encoding UTF8

    $kickoff = '2026-09-10T00:20:00Z'
    $legacySchedule = @(
        [PSCustomObject][ordered]@{
            gameID = '20260909_NE@SEA'
            season = '2026'
            gameWeek = 'Week 1'
            gameTime_epoch = [string]([DateTimeOffset]::Parse($kickoff).ToUnixTimeSeconds())
            teamIDAway = '1'
            teamIDHome = '2'
            away = 'NE'
            home = 'SEA'
            espnID = '401872656'
            gameStatus = 'Scheduled'
            gameStatusCode = '0'
        }
    )

    $resolvedSchedule = @(Resolve-CanonicalGameFinalitySchedule -Schedule $legacySchedule -Season 2026 -RepoRoot $tempRoot)
    Assert-GfrEqual 'Final' $resolvedSchedule[0].gameStatus 'canonical Final must override stale Tank01 Scheduled status'
    Assert-GfrEqual '2' $resolvedSchedule[0].gameStatusCode 'legacy compatibility status code must be promoted with Final'


    $canonicalFinality.Games[0].Final = $false
    $canonicalFinality | ConvertTo-Json -Depth 10 | Set-Content (Join-Path $canonicalFinalityDir '2026.json') -Encoding UTF8
    $legacyFinal = @(
        [PSCustomObject][ordered]@{
            gameID = '20260909_NE@SEA'
            season = '2026'
            espnID = '401872656'
            gameStatus = 'Final'
            gameStatusCode = '2'
        }
    )
    $conflictFailedClosed = $false
    try {
        Resolve-CanonicalGameFinalitySchedule -Schedule $legacyFinal -Season 2026 -RepoRoot $tempRoot | Out-Null
    }
    catch {
        $conflictFailedClosed = $true
    }
    Assert-GfrTrue $conflictFailedClosed 'legacy Final must not override canonical Final=false'
}
finally {
    if (Test-Path $tempRoot) {
        Remove-Item -Path $tempRoot -Recurse -Force
    }
}

Write-Host 'Canonical NFL game-finality regression tests passed.' -ForegroundColor Green
