$ErrorActionPreference = "Stop"

Import-Module "$PSScriptRoot\utils\league\WaiverUtils.psm1" -ErrorAction Stop -Force

function Assert-Equal {
    param(
        [Parameter(Mandatory = $true)]$Actual,
        [Parameter(Mandatory = $true)]$Expected,
        [Parameter(Mandatory = $true)][string]$Message
    )

    if ($Actual -ne $Expected) {
        throw "$Message Expected '$Expected' but got '$Actual'."
    }
}

function Assert-Null {
    param(
        $Actual,
        [Parameter(Mandatory = $true)][string]$Message
    )

    if ($null -ne $Actual) {
        throw "$Message Expected null but got '$Actual'."
    }
}

function New-TestLeague {
    param(
        [int]$DailyWaiversDays = 10665,
        [int]$DailyWaiversHour = 3,
        [int]$DailyWaivers = 1,
        [int]$DisableAdds = 0
    )

    return [PSCustomObject]@{
        settings = [PSCustomObject]@{
            daily_waivers      = $DailyWaivers
            daily_waivers_days = $DailyWaiversDays
            daily_waivers_hour = $DailyWaiversHour
            disable_adds       = $DisableAdds
        }
    }
}

$league = New-TestLeague

$summerNowUtc = [DateTimeOffset]::Parse("2026-09-04T10:00:00Z").UtcDateTime
$summerRun = Resolve-LeagueNextWaiverRunUtc -League $league -NowUtc $summerNowUtc
Assert-Equal `
    -Actual $summerRun.ToString("yyyy-MM-ddTHH:mm:ssZ") `
    -Expected "2026-09-06T10:00:00Z" `
    -Message "Summer schedule should resolve Sunday 03:00 Pacific without a fixed UTC offset."

$afterSundayUtc = [DateTimeOffset]::Parse("2026-09-06T10:01:00Z").UtcDateTime
$nextWednesdayRun = Resolve-LeagueNextWaiverRunUtc -League $league -NowUtc $afterSundayUtc
Assert-Equal `
    -Actual $nextWednesdayRun.ToString("yyyy-MM-ddTHH:mm:ssZ") `
    -Expected "2026-09-09T10:00:00Z" `
    -Message "After the Sunday run the next configured run should be Wednesday."

$winterNowUtc = [DateTimeOffset]::Parse("2026-01-02T10:00:00Z").UtcDateTime
$winterRun = Resolve-LeagueNextWaiverRunUtc -League $league -NowUtc $winterNowUtc
Assert-Equal `
    -Actual $winterRun.ToString("yyyy-MM-ddTHH:mm:ssZ") `
    -Expected "2026-01-04T11:00:00Z" `
    -Message "Winter schedule should follow Pacific DST rules instead of reusing the summer offset."

$unsupportedModesLeague = New-TestLeague -DailyWaiversDays 0
$unsupportedRun = Resolve-LeagueNextWaiverRunUtc -League $unsupportedModesLeague -NowUtc $summerNowUtc
Assert-Null `
    -Actual $unsupportedRun `
    -Message "Unvalidated daily waiver modes must fail closed."

$disabledAddsLeague = New-TestLeague -DisableAdds 1
$disabledRun = Resolve-LeagueNextWaiverRunUtc -League $disabledAddsLeague -NowUtc $summerNowUtc
Assert-Null `
    -Actual $disabledRun `
    -Message "Globally disabled adds must not publish a future waiver run."

Write-Host "Waiver schedule regression tests passed." -ForegroundColor Green
