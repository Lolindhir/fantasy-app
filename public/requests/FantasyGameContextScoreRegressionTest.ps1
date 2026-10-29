$ErrorActionPreference = 'Stop'

Import-Module "$PSScriptRoot\utils\league\FantasyGameContextUtils.psm1" -ErrorAction Stop -Force

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw $Message }
}

$context = [PSCustomObject]@{
    SchemaVersion = 2
    Games = @(
        [PSCustomObject]@{ GameID = 'g-final'; Status = 'Final' },
        [PSCustomObject]@{ GameID = 'g-future'; Status = 'Scheduled' },
        [PSCustomObject]@{ GameID = 'g-missing'; Status = 'Final' }
    )
}

$schedule = @(
    [PSCustomObject]@{ gameID = 'g-final'; gameStatus = 'Final'; awayPts = '24'; homePts = '0' },
    [PSCustomObject]@{ gameID = 'g-future'; gameStatus = 'Scheduled'; awayPts = '17'; homePts = '20' },
    [PSCustomObject]@{ gameID = 'g-missing'; gameStatus = 'Final'; awayPts = '21'; homePts = $null }
)

$result = Add-FantasyGameScoreContext -BaseContext $context -Schedule $schedule
$final = @($result.Games | Where-Object GameID -eq 'g-final')[0]
$future = @($result.Games | Where-Object GameID -eq 'g-future')[0]
$missing = @($result.Games | Where-Object GameID -eq 'g-missing')[0]

Assert-True ([int]$result.SchemaVersion -eq 3) 'FantasyGameContext score projection must bump schema version to 3.'
Assert-True ([double]$final.AwayScore -eq 24 -and [double]$final.HomeScore -eq 0) 'Final NFL score pair must project into FantasyGameContext and preserve zero.'
Assert-True ($null -eq $future.AwayScore -and $null -eq $future.HomeScore) 'Score fields must remain null for non-final games even if schedule score evidence exists.'
Assert-True ($null -eq $missing.AwayScore -and $null -eq $missing.HomeScore) 'Incomplete NFL score evidence must remain unknown rather than defaulting to zero.'

$duplicateFailed = $false
try {
    Add-FantasyGameScoreContext `
        -BaseContext ([PSCustomObject]@{ SchemaVersion = 2; Games = @([PSCustomObject]@{ GameID = 'dup'; Status = 'Final' }) }) `
        -Schedule @(
            [PSCustomObject]@{ gameID = 'dup'; gameStatus = 'Final'; awayPts = 10; homePts = 7 },
            [PSCustomObject]@{ gameID = 'dup'; gameStatus = 'Final'; awayPts = 10; homePts = 7 }
        ) | Out-Null
}
catch {
    $duplicateFailed = $true
}
Assert-True $duplicateFailed 'Duplicate schedule score identity must fail closed.'

# #1148: current App Market delivery joins only through Schedule.CanonicalGameID.
$marketContext = [PSCustomObject]@{
    SchemaVersion = 5
    Games = @(
        [PSCustomObject]@{ GameID = 'display-pit-no'; AwayTeamID = 'PIT'; HomeTeamID = 'NO'; Status = 'Scheduled' },
        [PSCustomObject]@{ GameID = 'display-ne-chi'; AwayTeamID = 'NE'; HomeTeamID = 'CHI'; Status = 'Final' },
        [PSCustomObject]@{ GameID = 'display-unmatched'; AwayTeamID = 'CAR'; HomeTeamID = 'TB'; Status = 'Scheduled' }
    )
}
$marketSchedule = @(
    [PSCustomObject]@{ gameID = 'display-pit-no'; CanonicalGameID = '2026_07_PIT_NO' },
    [PSCustomObject]@{ gameID = 'display-ne-chi'; CanonicalGameID = '2026_07_NE_CHI' },
    [PSCustomObject]@{ gameID = 'display-unmatched'; CanonicalGameID = '2026_07_CAR_TB' }
)
$derived = [PSCustomObject]@{
    SchemaVersion = 1
    Season = 2026
    Games = @(
        [PSCustomObject]@{
            GameID = '2026_07_PIT_NO'; Week = 7; AwayTeam = 'PIT'; HomeTeam = 'NO'
            Market = [PSCustomObject]@{ SpreadLine = -3; TotalLine = 44.5; ImpliedAwayPoints = 23.75; ImpliedHomePoints = 20.75 }
        },
        [PSCustomObject]@{
            GameID = '2026_07_NE_CHI'; Week = 7; AwayTeam = 'NE'; HomeTeam = 'CHI'
            Market = [PSCustomObject]@{ SpreadLine = 3; TotalLine = 50.5; ImpliedAwayPoints = 23.75; ImpliedHomePoints = 26.75 }
        }
    )
}
$marketResult = Add-FantasyGameMarketContext -BaseContext $marketContext -Schedule $marketSchedule -Season '2026' -Week 7 -NflGameDerived $derived
$pit = @($marketResult.Games | Where-Object GameID -eq 'display-pit-no')[0]
$ne = @($marketResult.Games | Where-Object GameID -eq 'display-ne-chi')[0]
$unmatched = @($marketResult.Games | Where-Object GameID -eq 'display-unmatched')[0]
Assert-True ([int]$marketResult.SchemaVersion -eq 6) 'Current market delivery must use FantasyGameContext schema v6.'
Assert-True ($pit.Market.ImpliedAwayPoints -eq 23.75 -and $pit.Market.ImpliedHomePoints -eq 20.75) 'Market must project both canonical implied scores unchanged.'
Assert-True ($pit.Market.SpreadLine -eq -3 -and $pit.Market.TotalLine -eq 44.5) 'Market must retain signed away spread and total.'
Assert-True ($ne.Market.ImpliedAwayPoints -eq 23.75) 'Final games retain source evidence; the frontend decides to show real final scores.'
Assert-True ($null -eq $unmatched.Market) 'Missing canonical market identity must remain explicitly unavailable.'

$emptyResult = Add-FantasyGameMarketContext `
    -BaseContext ([PSCustomObject]@{ SchemaVersion = 5; Games = @([PSCustomObject]@{ GameID = 'display-pit-no' }) }) `
    -Schedule $marketSchedule -Season '2026' -Week 7 -NflGameDerived $null
Assert-True ($null -eq $emptyResult.Games[0].Market) 'Missing Derived partition must not fabricate odds or block the current App read model.'

$wrongTeam = [PSCustomObject]@{
    SchemaVersion = 1; Season = 2026
    Games = @([PSCustomObject]@{ GameID = '2026_07_PIT_NO'; Week = 7; AwayTeam = 'NO'; HomeTeam = 'PIT'; Market = $null })
}
$mismatchRejected = $false
try {
    Add-FantasyGameMarketContext `
        -BaseContext ([PSCustomObject]@{ SchemaVersion = 5; Games = @([PSCustomObject]@{ GameID = 'display-pit-no'; AwayTeamID = 'PIT'; HomeTeamID = 'NO' }) }) `
        -Schedule $marketSchedule -Season '2026' -Week 7 -NflGameDerived $wrongTeam | Out-Null
}
catch { $mismatchRejected = $true }
Assert-True $mismatchRejected 'Wrong away/home identity must fail closed rather than show a swapped market.'

$wrongSeasonRejected = $false
try {
    Add-FantasyGameMarketContext `
        -BaseContext ([PSCustomObject]@{ SchemaVersion = 5; Games = @() }) `
        -Schedule @() -Season '2025' -Week 7 -NflGameDerived $derived | Out-Null
}
catch { $wrongSeasonRejected = $true }
Assert-True $wrongSeasonRejected 'Cross-season market evidence must fail closed.'

Write-Host 'FantasyGameContext score projection regression test passed.' -ForegroundColor Green
