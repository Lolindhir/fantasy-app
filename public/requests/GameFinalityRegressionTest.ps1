$ErrorActionPreference = 'Stop'

Import-Module "$PSScriptRoot\utils\general\GameFinalityUtils.psm1" -Force
Import-Module "$PSScriptRoot\utils\league\DecisionWindowUtils.psm1" -Force
Import-Module "$PSScriptRoot\utils\league\FantasyGameContextUtils.psm1" -Force
Import-Module "$PSScriptRoot\utils\league\FantasyRelevanceV2Utils.psm1" -Force

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
    $canonicalScheduleDir = Join-Path $tempRoot 'source-data/nfl/schedules'
    $canonicalFinalityDir = Join-Path $tempRoot 'source-data/nfl/game-finality'
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

    $league = [PSCustomObject]@{
        league_id = 'league'
        season = '2026'
        settings = [PSCustomObject]@{ leg = 1 }
        roster_positions = @('QB','BN')
    }
    $teams = @(
        [PSCustomObject]@{ TeamID = 1; Roster = @('q1'); Starter = @('q1'); Reserve = @(); Taxi = @() },
        [PSCustomObject]@{ TeamID = 2; Roster = @('q2'); Starter = @('q2'); Reserve = @(); Taxi = @() }
    )
    $players = @(
        [PSCustomObject]@{ ID = 'q1'; Position = 'QB'; TeamID = '1' },
        [PSCustomObject]@{ ID = 'q2'; Position = 'QB'; TeamID = '2' }
    )

    $baseDecision = DecisionWindowUtils\New-CurrentLeagueDecisionWindowsReadModel `
        -League $league -Teams $teams -Players $players -Schedule $resolvedSchedule -LastLineupWeek 1
    $decision = Add-FantasyRelevanceDecisionFacts `
        -BaseReadModel $baseDecision -League $league -Teams $teams -Players $players -Schedule $resolvedSchedule `
        -AsOfUtc ([DateTimeOffset]::Parse('2026-09-10T05:00:00Z'))

    $teamOne = @($decision.FantasyRelevance.Teams | Where-Object FantasyTeamID -eq '1')[0]
    $teamTwo = @($decision.FantasyRelevance.Teams | Where-Object FantasyTeamID -eq '2')[0]
    Assert-GfrEqual 'completed' $teamOne.Players[0].GameState 'completed canonical NFL game must complete starter one'
    Assert-GfrEqual 'completed' $teamTwo.Players[0].GameState 'completed canonical NFL game must complete starter two'
    Assert-GfrTrue (-not [bool]$teamOne.Players[0].HasDirectScoringPath) 'completed starter must not retain a direct scoring path'
    Assert-GfrTrue (-not [bool]$teamTwo.Players[0].HasDirectScoringPath) 'completed starter must not retain a direct scoring path'

    $rawMatchups = @(
        [PSCustomObject]@{
            matchup_id = 1
            roster_id = 1
            players = @('q1')
            starters = @('q1')
            players_points = [PSCustomObject]@{ q1 = 14.5 }
            points = 14.5
            custom_points = $null
        },
        [PSCustomObject]@{
            matchup_id = 1
            roster_id = 2
            players = @('q2')
            starters = @('q2')
            players_points = [PSCustomObject]@{ q2 = 10.0 }
            points = 10.0
            custom_points = $null
        }
    )
    $matchupFacts = @(ConvertTo-FgcCurrentMatchupFacts -Season '2026' -Week 1 -MatchupRows $rawMatchups)
    $context = New-FantasyGameContextReadModel `
        -LeagueID 'league' -Season '2026' -Week 1 -DecisionFacts $decision `
        -FantasyMatchups $matchupFacts -Schedule $resolvedSchedule -WeekIsFinal $false

    Assert-GfrEqual 0 @($context.MustWatchGames).Count 'completed game must disappear from Must-watch'
    Assert-GfrTrue (-not [bool]$context.Games[0].RemainingRelevance.HasRemainingRelevance) 'completed game must have no remaining relevance'
    Assert-GfrEqual 'none' $context.FantasyMatchups[0].RemainingRelevance.State 'completed matchup must have no remaining scoring paths'
    Assert-GfrTrue (-not [bool]$context.FantasyMatchups[0].RemainingRelevance.HasRemainingScoringPaths) 'completed matchup must expose no remaining scoring paths'
    Assert-GfrEqual 'final' $context.Games[0].Impact.State 'existing fantasy points must become completed/final impact'
    Assert-GfrEqual '24.5' $context.Games[0].Impact.StarterPoints 'existing fantasy points must remain visible after finality changes'

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
