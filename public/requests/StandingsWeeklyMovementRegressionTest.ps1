$ErrorActionPreference = 'Stop'

Import-Module "$PSScriptRoot\utils\league\StandingUtils.psm1" -ErrorAction Stop -Force

function Assert-Equal {
    param(
        [Parameter(Mandatory = $true)][AllowNull()]$Expected,
        [Parameter(Mandatory = $true)][AllowNull()]$Actual,
        [Parameter(Mandatory = $true)][string]$Message
    )

    if ($Expected -ne $Actual -or ($null -eq $Expected) -ne ($null -eq $Actual)) {
        throw "$Message Expected '$Expected', got '$Actual'."
    }
}

function New-TestTeam {
    param([int]$TeamID, [string]$Record, [int]$Wins, [int]$Losses, [int]$Ties, [double]$Points, [double]$PointsAgainst)

    [PSCustomObject]@{
        TeamID = $TeamID; Team = "Team $TeamID"; Owner = "Owner $TeamID"; PlaceRegular = 0
        Wins = $Wins; Losses = $Losses; Ties = $Ties
        Points = $Points; PointsAgainst = $PointsAgainst
        Record = $Record; Streak = ''
    }
}

function New-TestWeek {
    param([int]$Week, [array]$Matchups)

    # Matchups: @( @(teamA, pointsA, teamB, pointsB), ... )
    $entries = @()
    $matchupID = 1
    foreach ($m in $Matchups) {
        $entries += [PSCustomObject]@{ TeamID = $m[0]; MatchupID = $matchupID; Points = $m[1] }
        $entries += [PSCustomObject]@{ TeamID = $m[2]; MatchupID = $matchupID; Points = $m[3] }
        $matchupID++
    }
    [PSCustomObject]@{ Week = $Week; Entries = $entries }
}

# ---------------------------------------------------------------------------
# Scenario 1: up / down / unchanged, 4 teams, 3 completed weeks
# After week 2: C(2-0) 1st, A(1-1, 190) 2nd, B(1-1, 150) 3rd, D(0-2) 4th
# After week 3: A(270) 1st, B(250) 2nd, C(225) 3rd, D 4th (all three at 2-1)
# ---------------------------------------------------------------------------
$weeks = @(
    (New-TestWeek 1 @(@(1, 100, 2, 90), @(3, 80, 4, 70))),
    (New-TestWeek 2 @(@(1, 90, 3, 95), @(2, 60, 4, 50))),
    (New-TestWeek 3 @(@(1, 80, 4, 70), @(2, 100, 3, 50)))
)
$teams = @(
    (New-TestTeam 1 'WLW' 2 1 0 270 255),
    (New-TestTeam 2 'LWW' 2 1 0 250 200),
    (New-TestTeam 3 'WWL' 2 1 0 225 260),
    (New-TestTeam 4 'LLL' 0 3 0 190 220)
)

$places = Get-PreviousWeekRegularSeasonPlaces -teamData $teams -weeklyMatchups $weeks
Assert-Equal 2 $places[1] 'Team 1 previous place.'
Assert-Equal 3 $places[2] 'Team 2 previous place.'
Assert-Equal 1 $places[3] 'Team 3 previous place.'
Assert-Equal 4 $places[4] 'Team 4 previous place.'

$standings = @(Get-RegularSeasonStandings -teamData $teams -regularSeasonGames 14 -previousWeekPlaces $places -includeWeeklyMovement)
$byTeam = @{}
foreach ($row in $standings) { $byTeam[[int]$row.TeamID] = $row }
Assert-Equal 1 $byTeam[1].Place 'Team 1 current place.'
Assert-Equal 1 $byTeam[1].PlaceDelta 'Promoted team must have a positive delta.'
Assert-Equal 1 $byTeam[2].PlaceDelta 'Team 2 promoted by one.'
Assert-Equal -2 $byTeam[3].PlaceDelta 'Dropped team must have a negative delta.'
Assert-Equal 0 $byTeam[4].PlaceDelta 'Unchanged team must have delta 0.'
Assert-Equal 2 $byTeam[1].PreviousWeekPlace 'Team 1 PreviousWeekPlace in output.'

# Without the movement switch (completed seasons) the fields must not exist.
$plain = @(Get-RegularSeasonStandings -teamData $teams -regularSeasonGames 14)
Assert-Equal $false ($plain[0].PSObject.Properties.Name -contains 'PlaceDelta') 'Movement fields must be omitted when not requested.'
Assert-Equal $false ($plain[0].PSObject.Properties.Name -contains 'PreviousWeekPlace') 'Movement fields must be omitted when not requested.'

# ---------------------------------------------------------------------------
# Scenario 2: tiebreak and shared places in the previous table
# After week 1: A and C are tied (1-0, 100 PF, 80 PA) and share place 1; B and D share place 2.
# After week 2: A beats C, B beats D.
# ---------------------------------------------------------------------------
$tieWeeks = @(
    (New-TestWeek 1 @(@(1, 100, 2, 80), @(3, 100, 4, 80))),
    (New-TestWeek 2 @(@(1, 90, 3, 70), @(2, 90, 4, 70)))
)
$tieTeams = @(
    (New-TestTeam 1 'WW' 2 0 0 190 150),
    (New-TestTeam 2 'LW' 1 1 0 170 190),
    (New-TestTeam 3 'WL' 1 1 0 170 190),
    (New-TestTeam 4 'LL' 0 2 0 150 190)
)
$tiePlaces = Get-PreviousWeekRegularSeasonPlaces -teamData $tieTeams -weeklyMatchups $tieWeeks
Assert-Equal 1 $tiePlaces[1] 'Tied teams must share the previous place.'
Assert-Equal 1 $tiePlaces[3] 'Tied teams must share the previous place.'
Assert-Equal $tiePlaces[2] $tiePlaces[4] 'Tied teams must share the previous place.'

# Points break a win-percentage tie: week 1 both teams win, team 3 scores more.
$pointsTieWeeks = @(
    (New-TestWeek 1 @(@(1, 100, 2, 80), @(3, 120, 4, 80))),
    (New-TestWeek 2 @(@(1, 70, 3, 60), @(2, 90, 4, 70)))
)
$pointsTieTeams = @(
    (New-TestTeam 1 'WW' 2 0 0 170 140),
    (New-TestTeam 2 'LW' 1 1 0 170 170),
    (New-TestTeam 3 'WL' 1 1 0 180 170),
    (New-TestTeam 4 'LL' 0 2 0 150 190)
)
$pointsTiePlaces = Get-PreviousWeekRegularSeasonPlaces -teamData $pointsTieTeams -weeklyMatchups $pointsTieWeeks
Assert-Equal 2 $pointsTiePlaces[1] 'Lower scoring winner ranks behind the higher scoring winner.'
Assert-Equal 1 $pointsTiePlaces[3] 'Higher scoring winner must lead the previous table.'

# ---------------------------------------------------------------------------
# Scenario 3: no comparable prior week / unreliable inputs
# ---------------------------------------------------------------------------
$weekOneTeams = @(
    (New-TestTeam 1 'W' 1 0 0 100 90),
    (New-TestTeam 2 'L' 0 1 0 90 100)
)
$weekOneMatchups = @((New-TestWeek 1 @(@(1, 100, 2, 90))))
Assert-Equal $null (Get-PreviousWeekRegularSeasonPlaces -teamData $weekOneTeams -weeklyMatchups $weekOneMatchups) 'After week 1 there is no prior completed week.'

$noGamesTeams = @((New-TestTeam 1 '' 0 0 0 0 0), (New-TestTeam 2 '' 0 0 0 0 0))
Assert-Equal $null (Get-PreviousWeekRegularSeasonPlaces -teamData $noGamesTeams -weeklyMatchups @()) 'Before the first completed week there is no comparison.'

Assert-Equal $null (Get-PreviousWeekRegularSeasonPlaces -teamData $teams -weeklyMatchups @($weeks[1], $weeks[2])) 'Missing weekly facts must disable the comparison.'

$wrongRecordTeams = @(
    (New-TestTeam 1 'LLW' 2 1 0 270 255),
    (New-TestTeam 2 'LWW' 2 1 0 250 200),
    (New-TestTeam 3 'WWL' 2 1 0 225 260),
    (New-TestTeam 4 'LLL' 0 3 0 190 220)
)
Assert-Equal $null (Get-PreviousWeekRegularSeasonPlaces -teamData $wrongRecordTeams -weeklyMatchups $weeks) 'Weekly facts contradicting Record must disable the comparison.'

$partialWeeks = @($weeks[0], (New-TestWeek 2 @(@(1, 90, 3, 95))), $weeks[2])
Assert-Equal $null (Get-PreviousWeekRegularSeasonPlaces -teamData $teams -weeklyMatchups $partialWeeks) 'A week that does not cover all teams must disable the comparison.'

# Rows without a comparison keep explicit null values when movement was requested.
$nullStandings = @(Get-RegularSeasonStandings -teamData $teams -regularSeasonGames 14 -previousWeekPlaces $null -includeWeeklyMovement)
Assert-Equal $true ($nullStandings[0].PSObject.Properties.Name -contains 'PlaceDelta') 'Unavailable movement must stay an explicit null field.'
Assert-Equal $null $nullStandings[0].PlaceDelta 'Unavailable movement must be null.'
Assert-Equal $null $nullStandings[0].PreviousWeekPlace 'Unavailable previous place must be null.'

# Change detection must see movement changes.
Assert-Equal $true ((Get-RegularSeasonProperties) -contains 'PlaceDelta') 'Movement fields must participate in change detection.'

Write-Host 'StandingsWeeklyMovementRegressionTest passed.' -ForegroundColor Green
