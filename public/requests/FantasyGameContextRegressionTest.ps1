$ErrorActionPreference = 'Stop'

Import-Module "$PSScriptRoot\utils\league\FantasyGameContextUtils.psm1" -Force

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw "ASSERTION FAILED: $Message" }
}

function Assert-Equal {
    param($Expected, $Actual, [string]$Message)
    if ($Expected -ne $Actual) { throw "ASSERTION FAILED: $Message. Expected '$Expected', got '$Actual'." }
}

function New-TestDecisionFacts {
    return [PSCustomObject]@{
        DecisionWindows = @(
            [PSCustomObject]@{
                DecisionWindowID = 'dw-a'
                StartsAtUtc = '2026-09-10T00:00:00Z'
                Games = @(
                    [PSCustomObject]@{ GameID='g-a'; AwayTeamID='A'; AwayTeamAbbr='AAA'; HomeTeamID='H'; HomeTeamAbbr='HHH' }
                )
            }
        )
        PlayerLockFacts = @(
            [PSCustomObject]@{ FantasyTeamID='1'; PlayerID='p1'; NFLTeamID='A'; Kind='scheduled'; GameID='g-a'; DecisionWindowID='dw-a'; StartsAtUtc='2026-09-10T00:00:00Z'; IsStarter=$true },
            [PSCustomObject]@{ FantasyTeamID='1'; PlayerID='p2'; NFLTeamID='A'; Kind='scheduled'; GameID='g-a'; DecisionWindowID='dw-a'; StartsAtUtc='2026-09-10T00:00:00Z'; IsStarter=$false },
            [PSCustomObject]@{ FantasyTeamID='2'; PlayerID='p3'; NFLTeamID='H'; Kind='scheduled'; GameID='g-a'; DecisionWindowID='dw-a'; StartsAtUtc='2026-09-10T00:00:00Z'; IsStarter=$true },
            [PSCustomObject]@{ FantasyTeamID='2'; PlayerID='p4'; NFLTeamID=$null; Kind='unknown'; GameID=$null; DecisionWindowID=$null; StartsAtUtc=$null; IsStarter=$false }
        )
    }
}

$raw = @(
    [PSCustomObject]@{ matchup_id=9; roster_id=1; players=@('p1','p2'); starters=@('p1'); players_points=[PSCustomObject]@{ p1=18.0; p2=7.0 }; points=30.0; custom_points=$null },
    [PSCustomObject]@{ matchup_id=9; roster_id=2; players=@('p3','p4'); starters=@('p3'); players_points=[PSCustomObject]@{ p3=5.0; p4=2.0 }; points=20.0; custom_points=$null }
)
$facts = @(ConvertTo-FgcCurrentMatchupFacts -Season '2026' -Week 1 -MatchupRows $raw)
Assert-Equal 1 $facts.Count 'pairing count'
Assert-True ($facts[0].FantasyMatchupID -match '^fgm-[0-9a-f]{24}$') 'FantasyMatchupID must be opaque and app-owned'
Assert-Equal $facts[0].FantasyMatchupID (New-FantasyGameContextMatchupID -Season '2026' -Week 1 -FantasyTeamIDs @('2','1')) 'FantasyMatchupID must be deterministic and pairing based'

$schedule = @([PSCustomObject]@{ gameID='g-a'; gameStatus='Final'; gameWeek='Week 1' })
$context = New-FantasyGameContextReadModel -LeagueID 'league' -Season '2026' -Week 1 -DecisionFacts (New-TestDecisionFacts) -FantasyMatchups $facts -Schedule $schedule -WeekIsFinal $true
$game = $context.Games[0]
Assert-Equal 3 $game.Relevance.RosteredPlayerCount 'scheduled rostered players are counted'
Assert-Equal 2 $game.Relevance.StarterCount 'bench player must not increase starter count'
Assert-Equal 2 $game.Relevance.FantasyTeamCount 'fantasy team relevance count'
Assert-Equal 1 $game.Relevance.FantasyMatchupCount 'fantasy matchup relevance count'
Assert-Equal 30.0 $game.Impact.RosteredPoints 'impact must use supplied league matchup PlayerPoints'
Assert-Equal 23.0 $game.Impact.StarterPoints 'starter impact must use supplied league matchup starter points'
Assert-Equal 'final' $game.Impact.State 'final scoring state'
Assert-Equal 1 $game.Impact.OutcomeSwingMatchupCount 'removing selected NFL-game starter points changes the final outcome'
Assert-True ($context.NonGameAssociations | Where-Object { $_.PlayerID -eq 'p4' -and $_.Kind -eq 'unknown' }) 'unknown association must remain explicit'

$customRaw = @(
    [PSCustomObject]@{ matchup_id=9; roster_id=1; players=@('p1'); starters=@('p1'); players_points=[PSCustomObject]@{ p1=18.0 }; points=30.0; custom_points=31.0 },
    [PSCustomObject]@{ matchup_id=9; roster_id=2; players=@('p3'); starters=@('p3'); players_points=[PSCustomObject]@{ p3=5.0 }; points=20.0; custom_points=$null }
)
$customFacts = @(ConvertTo-FgcCurrentMatchupFacts -Season '2026' -Week 1 -MatchupRows $customRaw)
$customContext = New-FantasyGameContextReadModel -LeagueID 'league' -Season '2026' -Week 1 -DecisionFacts (New-TestDecisionFacts) -FantasyMatchups $customFacts -Schedule $schedule -WeekIsFinal $true
Assert-Equal 'unavailable-custom-score' $customContext.FantasyMatchups[0].CounterfactualState 'custom score must disable counterfactual claims'
Assert-Equal 0 $customContext.Games[0].Impact.OutcomeSwingMatchupCount 'custom score must not create a counterfactual swing claim'

$malformed = @([PSCustomObject]@{ matchup_id=2; roster_id=1; players=@('x'); starters=@('x'); players_points=[PSCustomObject]@{ x=1 }; points=1 })
Assert-Equal 0 @(ConvertTo-FgcCurrentMatchupFacts -Season '2026' -Week 1 -MatchupRows $malformed).Count 'malformed one-sided pairing must be excluded'

$duplicateOwnership = @(
    [PSCustomObject]@{ matchup_id=2; roster_id=1; players=@('dup'); starters=@('dup'); players_points=[PSCustomObject]@{ dup=1 }; points=1 },
    [PSCustomObject]@{ matchup_id=2; roster_id=2; players=@('dup'); starters=@('dup'); players_points=[PSCustomObject]@{ dup=2 }; points=2 }
)
$duplicateFailed = $false
try { ConvertTo-FgcCurrentMatchupFacts -Season '2026' -Week 1 -MatchupRows $duplicateOwnership | Out-Null } catch { $duplicateFailed = $true }
Assert-True $duplicateFailed 'same player assigned to multiple fantasy teams must fail closed'

# Historical adapter: canonical week-specific membership wins, inactive/unresolved players stay unknown.
$historicalMatchups = @(
    [PSCustomObject]@{
        FantasyMatchupID='fgm-history'; TeamIDs=@('1','2'); Teams=@(
            [PSCustomObject]@{ FantasyTeamID='1'; Players=@([PSCustomObject]@{ PlayerID='hp1'; CanonicalPlayerID='cp1'; IsStarter=$true; HasPoints=$true; Points=10.0 }); FinalScore=15.0; HasCustomPoints=$false },
            [PSCustomObject]@{ FantasyTeamID='2'; Players=@([PSCustomObject]@{ PlayerID='inactive'; CanonicalPlayerID='cp-inactive'; IsStarter=$false; HasPoints=$true; Points=0.0 }); FinalScore=5.0; HasCustomPoints=$false }
        )
    }
)
$historicalSchedule = @([PSCustomObject]@{ gameID='hist-game'; gameWeek='Week 1'; gameTime_epoch=1789000000; teamIDAway='OLD'; teamIDHome='NEW'; teamAbvAway='OLD'; teamAbvHome='NEW' })
$weekly = @([PSCustomObject]@{ CanonicalPlayerID='cp1'; CanonicalTeamID='NEW'; TeamAbbr='NEW' })
$historicalDecision = New-FgcHistoricalDecisionFacts -Week 1 -Schedule $historicalSchedule -FantasyMatchups $historicalMatchups -HistoricalPlayers @() -WeeklyRosterDocument $weekly
Assert-Equal 'hist-game' (@($historicalDecision.PlayerLockFacts | Where-Object PlayerID -eq 'hp1')[0].GameID) 'historical canonical weekly membership must resolve the actual week team/game'
Assert-Equal 'unknown' (@($historicalDecision.PlayerLockFacts | Where-Object PlayerID -eq 'inactive')[0].Kind) 'inactive player without week evidence must remain unknown instead of using current roster membership'

# Real 2025 canonical matchup fixture: pairing identity and league-scored points must be deterministic.
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))
$weekOneFile = Join-Path $repoRoot 'source-data\leagues\nfl-reise\seasons\2025\matchups\week-1.json'
if (Test-Path $weekOneFile) {
    $weekOneRows = @(Get-Content $weekOneFile -Raw | ConvertFrom-Json)
    $historyA = @(ConvertTo-FgcCanonicalMatchupFacts -Season '2025' -Week 1 -MatchupRows $weekOneRows)
    $historyB = @(ConvertTo-FgcCanonicalMatchupFacts -Season '2025' -Week 1 -MatchupRows $weekOneRows)
    Assert-True ($historyA.Count -gt 0) '2025 canonical matchup fixture must materialize'
    Assert-Equal ($historyA | ConvertTo-Json -Depth 20 -Compress) ($historyB | ConvertTo-Json -Depth 20 -Compress) '2025 historical derivation must be deterministic'
    $scoredPlayers = @($historyA.Teams.Players | Where-Object HasPoints)
    Assert-True ($scoredPlayers.Count -gt 0) '2025 history must consume persisted league matchup scoring facts'
}

Write-Host 'FantasyGameContext regression tests passed.' -ForegroundColor Green
