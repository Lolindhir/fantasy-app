$ErrorActionPreference = "Stop"

Import-Module "$PSScriptRoot\utils\league\WaiverUtils.psm1" -ErrorAction Stop -Force
Import-Module "$PSScriptRoot\utils\league\AcquisitionCapabilityUtils.psm1" -ErrorAction Stop -Force

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

$knownCapability = Resolve-TemporaryWaiverOnlyAcquisitionCapability `
    -WaiversOpen $true `
    -NextWaiverRun "2026-09-06T10:00:00Z"
Assert-Equal -Actual $knownCapability.State -Expected "known" -Message "Supported waiver evidence should be known."
Assert-Equal -Actual $knownCapability.ExternalAcquisitionMode -Expected "waiver-only" -Message "The temporary bridge must be explicitly waiver-only."
Assert-Equal -Actual $knownCapability.ExternalAddsAllowed -Expected $true -Message "Open waivers should permit external waiver acquisition."
Assert-Equal -Actual $knownCapability.WaiverAddsAllowed -Expected $true -Message "Waiver availability should follow the already-derived availability fact."
Assert-Equal -Actual $knownCapability.ImmediateFreeAgentAddsAllowed -Expected $false -Message "Immediate Free Agent adds must remain unavailable in the temporary bridge."
Assert-Equal -Actual $knownCapability.TradeRepairAllowed -Expected $false -Message "Trades must not become a repair path through the temporary bridge."
Assert-Equal -Actual $knownCapability.NextWaiverRun -Expected "2026-09-06T10:00:00Z" -Message "Known waiver timing should be exposed in normalized UTC form."

$missingTimingCapability = Resolve-TemporaryWaiverOnlyAcquisitionCapability `
    -WaiversOpen $true `
    -NextWaiverRun $null
Assert-Equal -Actual $missingTimingCapability.State -Expected "unknown" -Message "Open waivers without timing evidence must remain unknown."
Assert-Equal -Actual $missingTimingCapability.ExternalAddsAllowed -Expected $true -Message "Known add availability remains a fact even when timing is unknown."
Assert-Null -Actual $missingTimingCapability.NextWaiverRun -Message "Unknown timing must not publish a guessed waiver run."
Assert-Equal -Actual $missingTimingCapability.ImmediateFreeAgentAddsAllowed -Expected $false -Message "Unknown waiver timing must not enable immediate Free Agent adds."
Assert-Equal -Actual $missingTimingCapability.TradeRepairAllowed -Expected $false -Message "Unknown waiver timing must not enable trade repair."

$invalidTimingCapability = Resolve-TemporaryWaiverOnlyAcquisitionCapability `
    -WaiversOpen $true `
    -NextWaiverRun "not-a-timestamp"
Assert-Equal -Actual $invalidTimingCapability.State -Expected "unknown" -Message "Malformed waiver timing must fail conservative."
Assert-Null -Actual $invalidTimingCapability.NextWaiverRun -Message "Malformed timing must not leak into the capability."

$contradictoryCapability = Resolve-TemporaryWaiverOnlyAcquisitionCapability `
    -WaiversOpen $false `
    -NextWaiverRun "2026-09-06T10:00:00Z"
Assert-Equal -Actual $contradictoryCapability.State -Expected "unknown" -Message "Closed waivers plus a future waiver run are contradictory evidence."
Assert-Equal -Actual $contradictoryCapability.ExternalAddsAllowed -Expected $false -Message "The explicit closed availability fact should remain visible."
Assert-Null -Actual $contradictoryCapability.NextWaiverRun -Message "Contradictory timing must not be exposed as actionable."

$closedCapability = Resolve-TemporaryWaiverOnlyAcquisitionCapability `
    -WaiversOpen $false `
    -NextWaiverRun $null
Assert-Equal -Actual $closedCapability.State -Expected "known" -Message "Closed waivers without a future run are a known unavailable state."
Assert-Equal -Actual $closedCapability.ExternalAddsAllowed -Expected $false -Message "Closed waivers should not permit external acquisition."
Assert-Equal -Actual $closedCapability.WaiverAddsAllowed -Expected $false -Message "Closed waivers should not permit waiver acquisition."
Assert-Equal -Actual $closedCapability.ImmediateFreeAgentAddsAllowed -Expected $false -Message "Closed waivers must not imply immediate Free Agent acquisition."
Assert-Equal -Actual $closedCapability.TradeRepairAllowed -Expected $false -Message "Trade remains excluded even when waivers are closed."

$missingAvailabilityCapability = Resolve-TemporaryWaiverOnlyAcquisitionCapability `
    -WaiversOpen $null `
    -NextWaiverRun "2026-09-06T10:00:00Z"
Assert-Equal -Actual $missingAvailabilityCapability.State -Expected "unknown" -Message "Missing waiver availability must remain unknown even with timing evidence."
Assert-Null -Actual $missingAvailabilityCapability.ExternalAddsAllowed -Message "Missing availability must not be guessed."
Assert-Null -Actual $missingAvailabilityCapability.WaiverAddsAllowed -Message "Missing waiver availability must not be guessed."
Assert-Null -Actual $missingAvailabilityCapability.NextWaiverRun -Message "Timing without availability must not be exposed as actionable."

Write-Host "Waiver schedule and temporary acquisition capability regression tests passed." -ForegroundColor Green
