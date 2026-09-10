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

Write-Host 'FantasyGameContext score projection regression test passed.' -ForegroundColor Green
