$ErrorActionPreference = 'Stop'

Import-Module "$PSScriptRoot\utils\league\MatchupReadModelUtils.psm1" -ErrorAction Stop -Force

function Assert-MrmEqual {
    param($Expected, $Actual, [string]$Message)
    if ($Expected -ne $Actual) {
        throw "$Message Expected '$Expected', got '$Actual'."
    }
}

function Assert-MrmTrue {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw $Message }
}

function Write-MrmJson {
    param([Parameter(Mandatory = $true)][string]$Path, [Parameter(Mandatory = $true)][object]$Value)
    $dir = Split-Path $Path -Parent
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    $Value | ConvertTo-Json -Depth 30 | Out-File $Path -Encoding UTF8
}

function New-MrmCanonicalRow {
    param(
        [int]$TeamID,
        [string]$CanonicalPlayerID,
        [double]$Points,
        [AllowNull()]$CustomPoints = $null,
        [int]$ProviderMatchupID = 1
    )

    return [PSCustomObject][ordered]@{
        CanonicalLeagueMatchupID = 'clmup-test'
        CanonicalLeagueRosterID = "clr-$TeamID"
        CustomPoints = $CustomPoints
        Points = $Points
        ProviderMappings = @(
            [PSCustomObject][ordered]@{
                Provider = 'Sleeper'
                ProviderMatchupID = $ProviderMatchupID
                ProviderRosterID = [string]$TeamID
            }
        )
        StarterPoints = @(
            [PSCustomObject][ordered]@{
                Player = [PSCustomObject][ordered]@{
                    CanonicalPlayerID = $CanonicalPlayerID
                    ProviderMappings = @(
                        [PSCustomObject][ordered]@{
                            Provider = 'Sleeper'
                            ProviderPlayerID = "P$TeamID"
                        }
                    )
                }
                Points = $Points
            }
        )
        Week = 1
    }
}

function New-MrmDecisionFacts {
    param(
        [bool]$Team1HasPath = $false,
        [bool]$Team2HasPath = $false,
        [bool]$Team1Repairable = $false,
        [switch]$OmitTeam2Evaluation
    )

    $team1Slots = @()
    if ($Team1Repairable) {
        $team1Slots = @(
            [PSCustomObject][ordered]@{
                SlotID = 'QB-1'
                State = 'unlocked'
                Repairability = [PSCustomObject][ordered]@{ State = 'repairable' }
            }
        )
    }
    $evaluations = @(
        [PSCustomObject][ordered]@{ FantasyTeamID = 1; State = 'valid' }
    )
    if (-not $OmitTeam2Evaluation) {
        $evaluations += [PSCustomObject][ordered]@{ FantasyTeamID = 2; State = 'valid' }
    }

    return [PSCustomObject][ordered]@{
        Season = '2026'
        LineupWeek = 1
        FantasyRelevance = [PSCustomObject][ordered]@{
            Teams = @(
                [PSCustomObject][ordered]@{
                    FantasyTeamID = 1
                    HasRemainingScoringPath = $Team1HasPath
                    Slots = $team1Slots
                },
                [PSCustomObject][ordered]@{
                    FantasyTeamID = 2
                    HasRemainingScoringPath = $Team2HasPath
                    Slots = @()
                }
            )
        }
        TeamLineupEvaluations = $evaluations
    }
}

$temp = Join-Path ([System.IO.Path]::GetTempPath()) ("matchup-read-model-" + [guid]::NewGuid().ToString('N'))
try {
    $seasonDir = Join-Path $temp 'source-data/leagues/nfl-reise/seasons/2026'
    $matchupDir = Join-Path $seasonDir 'matchups'
    New-Item -ItemType Directory -Path $matchupDir -Force | Out-Null

    $leagueSource = [PSCustomObject][ordered]@{
        Season = 2026
        Status = 'in_season'
        RosterPositions = @('QB','BN')
        Settings = [PSCustomObject][ordered]@{
            leg = 1
            start_week = 1
            playoff_week_start = 2
            playoff_round_type = 0
        }
        WeekStructure = [PSCustomObject][ordered]@{
            StartWeek = 1
            PlayoffStartWeek = 2
            PlayoffRoundType = 0
            ExpectedLastLeagueWeek = 3
            FinalLeagueWeek = $null
        }
    }
    Write-MrmJson -Path (Join-Path $seasonDir 'league.json') -Value $leagueSource

    $team1Row = New-MrmCanonicalRow -TeamID 1 -CanonicalPlayerID 'NFLP-1' -Points 10
    $team2Row = New-MrmCanonicalRow -TeamID 2 -CanonicalPlayerID 'NFLP-2' -Points 7
    Write-MrmJson -Path (Join-Path $matchupDir 'week-1.json') -Value @($team1Row, $team2Row)
    Write-MrmJson -Path (Join-Path $matchupDir 'week-2.json') -Value @(
        (New-MrmCanonicalRow -TeamID 1 -CanonicalPlayerID 'NFLP-1' -Points 0 -ProviderMatchupID 2),
        (New-MrmCanonicalRow -TeamID 2 -CanonicalPlayerID 'NFLP-2' -Points 0 -ProviderMatchupID 2)
    )

    $schedule = [PSCustomObject][ordered]@{
        SchemaVersion = 2
        Season = 2026
        Games = @(
            [PSCustomObject][ordered]@{
                GameID = '2026_01_AAA_BBB'
                GameType = 'REG'
                Week = 1
                GameDay = '2026-09-10'
                GameTime = '20:15'
                AwayTeam = 'AAA'
                HomeTeam = 'BBB'
            },
            [PSCustomObject][ordered]@{
                GameID = '2026_01_CCC_DDD'
                GameType = 'REG'
                Week = 1
                GameDay = '2026-09-14'
                GameTime = '20:15'
                AwayTeam = 'CCC'
                HomeTeam = 'DDD'
            },
            [PSCustomObject][ordered]@{
                GameID = '2026_02_AAA_CCC'
                GameType = 'REG'
                Week = 2
                GameDay = '2026-09-17'
                GameTime = '20:15'
                AwayTeam = 'AAA'
                HomeTeam = 'CCC'
            }
        )
    }
    Write-MrmJson -Path (Join-Path $temp 'source-data/nfl/schedules/2026.json') -Value $schedule
    Write-MrmJson -Path (Join-Path $temp 'source-data/nfl/game-finality/2026.json') -Value ([PSCustomObject][ordered]@{
        SchemaVersion = 2
        Season = 2026
        Games = @(
            [PSCustomObject][ordered]@{ GameID = '2026_01_AAA_BBB'; GameType = 'REG'; Week = 1; Final = $true },
            [PSCustomObject][ordered]@{ GameID = '2026_01_CCC_DDD'; GameType = 'REG'; Week = 1; Final = $false }
        )
    })
    Write-MrmJson -Path (Join-Path $temp 'source-data/nfl/weekly-rosters/2026/01.json') -Value ([PSCustomObject][ordered]@{
        SchemaVersion = 2
        Season = 2026
        Week = 1
        Records = @(
            [PSCustomObject][ordered]@{ CanonicalPlayerID = 'NFLP-1'; Team = 'AAA' },
            [PSCustomObject][ordered]@{ CanonicalPlayerID = 'NFLP-2'; Team = 'AAA' }
        )
    })

    $standings = @(
        [PSCustomObject][ordered]@{
            Season = 'AllTime'
            Playoffs = @(
                [PSCustomObject][ordered]@{ TeamID = 2; Place = 1 },
                [PSCustomObject][ordered]@{ TeamID = 1; Place = 2 }
            )
            RegularSeason = @()
        },
        [PSCustomObject][ordered]@{
            Season = '2024'
            Playoffs = @(
                [PSCustomObject][ordered]@{ TeamID = 1; Owner = 'One'; TeamName = 'One'; Place = 1 },
                [PSCustomObject][ordered]@{ TeamID = 2; Owner = 'Two'; TeamName = 'Two'; Place = 2 }
            )
            RegularSeason = @(
                [PSCustomObject][ordered]@{ TeamID = 1; Owner = 'One'; TeamName = 'One'; Place = 1; Wins = 10; Losses = 2; Ties = 0; Points = 100; PointsAgainst = 80 },
                [PSCustomObject][ordered]@{ TeamID = 2; Owner = 'Two'; TeamName = 'Two'; Place = 2; Wins = 8; Losses = 4; Ties = 0; Points = 90; PointsAgainst = 85 }
            )
        },
        [PSCustomObject][ordered]@{
            Season = '2025'
            Playoffs = @(
                [PSCustomObject][ordered]@{ TeamID = 2; Owner = 'Two'; TeamName = 'Two'; Place = 1 },
                [PSCustomObject][ordered]@{ TeamID = 1; Owner = 'One'; TeamName = 'One'; Place = 2 }
            )
            RegularSeason = @(
                [PSCustomObject][ordered]@{ TeamID = 2; Owner = 'Two'; TeamName = 'Two'; Place = 1; Wins = 11; Losses = 1; Ties = 0; Points = 110; PointsAgainst = 75 },
                [PSCustomObject][ordered]@{ TeamID = 1; Owner = 'One'; TeamName = 'One'; Place = 2; Wins = 7; Losses = 5; Ties = 0; Points = 88; PointsAgainst = 92 }
            )
        }
    )

    $liveRows = @(
        [PSCustomObject][ordered]@{ roster_id = 1; matchup_id = 1; points = 0.0; custom_points = 0.0 },
        [PSCustomObject][ordered]@{ roster_id = 2; matchup_id = 1; points = 7.0; custom_points = $null }
    )

    $finalModel = New-MatchupSeasonReadModel `
        -CanonicalLeagueID 'nfl-reise' `
        -Season 2026 `
        -Standings $standings `
        -DecisionFacts (New-MrmDecisionFacts) `
        -LiveMatchupRows $liveRows `
        -AsOfUtc ([DateTimeOffset]::Parse('2026-09-13T18:00:00Z')) `
        -RepoRoot $temp

    Assert-MrmEqual 1 (@($finalModel.Weeks).Count) 'Future playoff pairings must not be materialized before playoff start.'
    Assert-MrmEqual 'regular-season' $finalModel.Weeks[0].Stage 'Week 1 stage is incorrect.'
    Assert-MrmEqual 'final' $finalModel.Weeks[0].CompletionState 'An irrelevant unfinished NFL game must not block fantasy matchup finality.'
    Assert-MrmEqual 'final' $finalModel.Weeks[0].Matchups[0].CompletionState 'Final matchup state is incorrect.'
    Assert-MrmEqual 2 $finalModel.Weeks[0].Matchups[0].Participants[0].TeamID 'Participant storage order must follow All-Time Overall Standings.'
    Assert-MrmEqual 1 $finalModel.Weeks[0].Matchups[0].Participants[1].TeamID 'Participant storage order must remain neutral and deterministic.'
    Assert-MrmEqual 0.0 $finalModel.Weeks[0].Matchups[0].Participants[1].Points 'Reliable zero adjusted score must be preserved.'
    Assert-MrmEqual 'adjusted' $finalModel.Weeks[0].Matchups[0].Participants[1].ScoreKind 'Custom score must be marked adjusted.'
    Assert-MrmEqual 'win' $finalModel.Weeks[0].Matchups[0].Result.Type 'Final result type is incorrect.'
    Assert-MrmEqual 2 $finalModel.Weeks[0].Matchups[0].Result.WinnerTeamID 'Final winner must use the effective score.'
    Assert-MrmEqual 1 $finalModel.Summary.LastCompletedWeek 'LastCompletedWeek is incorrect.'
    Assert-MrmTrue ($null -eq $finalModel.Summary.ActiveOrNextWeek) 'ActiveOrNextWeek must be null after the last known week is final.'

    $matchupReadModelModule = Get-Module MatchupReadModelUtils
    $historyDiagnostics = & $matchupReadModelModule {
        param($Root, $Starter)
        $assignments = Get-MrmWeeklyAssignmentMap -RepoRoot $Root -Season 2026 -Week 1
        $games = @(Get-MrmCanonicalScheduleGames -RepoRoot $Root -Season 2026 | Where-Object { [int](Get-MrmValue -Object $_ -Names @('Week')) -eq 1 })
        $finality = Get-MrmFinalityMap -RepoRoot $Root -Season 2026
        [PSCustomObject][ordered]@{
            Assignment = if ($null -ne $assignments -and $assignments.ContainsKey('NFLP-1')) { @($assignments['NFLP-1']) -join ',' } else { $null }
            StarterResolution = Get-MrmStarterGameResolution -Starter $Starter -WeekGames $games -WeeklyAssignments $assignments -FinalityMap $finality
        }
    } $temp $team1Row.StarterPoints[0]
    Assert-MrmEqual 'AAA' $historyDiagnostics.Assignment 'Canonical weekly-roster assignment map must expose Team strings.'
    Assert-MrmEqual 'final' $historyDiagnostics.StarterResolution 'Canonical weekly-roster assignment must resolve the starter NFL game finality.'

    $historicalStyleModel = New-MatchupSeasonReadModel `
        -CanonicalLeagueID 'nfl-reise' `
        -Season 2026 `
        -Standings $standings `
        -DecisionFacts $null `
        -AsOfUtc ([DateTimeOffset]::Parse('2026-09-15T18:00:00Z')) `
        -RepoRoot $temp
    Assert-MrmEqual 'final' $historicalStyleModel.Weeks[0].CompletionState 'Canonical weekly-roster Team strings must resolve historical starter finality.'
    Assert-MrmEqual 'final' $historicalStyleModel.Weeks[0].Matchups[0].CompletionState 'An unrelated unfinished NFL game must not block historical fantasy finality.'

    $openModel = New-MatchupSeasonReadModel `
        -CanonicalLeagueID 'nfl-reise' `
        -Season 2026 `
        -Standings $standings `
        -DecisionFacts (New-MrmDecisionFacts -Team1HasPath $true) `
        -LiveMatchupRows $liveRows `
        -AsOfUtc ([DateTimeOffset]::Parse('2026-09-13T18:00:00Z')) `
        -RepoRoot $temp
    Assert-MrmEqual 'open' $openModel.Weeks[0].CompletionState 'Known remaining scoring path must keep the week open.'
    Assert-MrmTrue ($null -eq $openModel.Weeks[0].Matchups[0].Result) 'Open matchup Result must be null.'
    Assert-MrmTrue ($null -eq $openModel.Summary.LastCompletedWeek) 'Open week must not become LastCompletedWeek.'
    Assert-MrmEqual 1 $openModel.Summary.ActiveOrNextWeek 'Open week must be ActiveOrNextWeek.'

    $repairableModel = New-MatchupSeasonReadModel `
        -CanonicalLeagueID 'nfl-reise' `
        -Season 2026 `
        -Standings $standings `
        -DecisionFacts (New-MrmDecisionFacts -Team1Repairable $true) `
        -LiveMatchupRows $liveRows `
        -AsOfUtc ([DateTimeOffset]::Parse('2026-09-13T18:00:00Z')) `
        -RepoRoot $temp
    Assert-MrmEqual 'open' $repairableModel.Weeks[0].Matchups[0].CompletionState 'Repairable lineup path must count as a legal remaining scoring path.'

    $unknownModel = New-MatchupSeasonReadModel `
        -CanonicalLeagueID 'nfl-reise' `
        -Season 2026 `
        -Standings $standings `
        -DecisionFacts (New-MrmDecisionFacts -OmitTeam2Evaluation) `
        -LiveMatchupRows $liveRows `
        -AsOfUtc ([DateTimeOffset]::Parse('2026-09-13T18:00:00Z')) `
        -RepoRoot $temp
    Assert-MrmEqual 'unknown' $unknownModel.Weeks[0].Matchups[0].CompletionState 'Missing lineup evidence must fail closed to unknown.'
    Assert-MrmTrue ($null -eq $unknownModel.Weeks[0].Matchups[0].Result) 'Unknown matchup Result must be null.'

    $orderMap = Get-MatchupParticipantOrderMap -Standings $standings -Season 2026
    $pairA = @(ConvertTo-MrmCanonicalPairings -Season 2026 -Week 1 -Rows @($team1Row, $team2Row) -ParticipantOrder $orderMap)[0]
    $pairB = @(ConvertTo-MrmCanonicalPairings -Season 2026 -Week 1 -Rows @($team2Row, $team1Row) -ParticipantOrder $orderMap)[0]
    Assert-MrmEqual $pairA.FantasyMatchupID $pairB.FantasyMatchupID 'FantasyMatchupID must be independent of provider row order.'

    $malformedRow = New-MrmCanonicalRow -TeamID 1 -CanonicalPlayerID 'NFLP-1' -Points 5 -ProviderMatchupID 9
    $malformedRow.CanonicalLeagueMatchupID = 'clmup-malformed'
    $malformedEvidence = $false
    $resolvedPairings = @(ConvertTo-MrmCanonicalPairings -Season 2026 -Week 1 -Rows @($team1Row, $team2Row, $malformedRow) -ParticipantOrder $orderMap -MalformedEvidenceFound ([ref]$malformedEvidence))
    Assert-MrmEqual 1 $resolvedPairings.Count 'Malformed one-sided pairing evidence must not create a speculative matchup.'
    Assert-MrmTrue $malformedEvidence 'Known malformed pairing evidence must be surfaced to week-level fail-closed aggregation.'

    $historicalOrder = Get-MatchupParticipantOrderMap -Standings $standings -Season 2024 -HistoricalCutoff
    Assert-MrmEqual 0 $historicalOrder['1'] 'Historical participant order must use the historical All-Time cutoff rather than current All-Time order.'
    Assert-MrmEqual 1 $historicalOrder['2'] 'Historical participant order cutoff is incorrect.'

    $adjustedCanonical = New-MrmCanonicalRow -TeamID 1 -CanonicalPlayerID 'NFLP-1' -Points 12 -CustomPoints 3
    $adjustedScore = Get-MrmEffectiveScore -Row $adjustedCanonical
    Assert-MrmEqual 3.0 $adjustedScore.Points 'Canonical custom score must replace standard score.'
    Assert-MrmEqual 'adjusted' $adjustedScore.ScoreKind 'Canonical custom score kind is incorrect.'

    Write-Host 'Matchup read-model regression tests passed.' -ForegroundColor Green
}
finally {
    if (Test-Path $temp) { Remove-Item $temp -Recurse -Force }
}
