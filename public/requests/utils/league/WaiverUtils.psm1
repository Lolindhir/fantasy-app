# ===========================================================================
# 1. Funktionen
# ===========================================================================

function ConvertFrom-SleeperDailyWaiverDays {
    param(
        [Parameter(Mandatory = $true)][int]$EncodedDays
    )

    if ($EncodedDays -lt 0) { return $null }

    # Sleeper stores the seven daily modes as base-4 digits, Monday through Sunday.
    # The current league contract intentionally supports only the empirically
    # validated Waivers (1) and Locked (2) modes. Mixed FA modes remain fail-closed
    # until their provider encoding is independently validated.
    $remaining = $EncodedDays
    $modes = [int[]]::new(7)

    for ($index = 6; $index -ge 0; $index--) {
        $modes[$index] = $remaining % 4
        $remaining = [math]::Floor($remaining / 4)
    }

    if ($remaining -ne 0) { return $null }

    return $modes
}

function Get-SleeperWaiverTimeZone {
    foreach ($timeZoneId in @("America/Los_Angeles", "Pacific Standard Time")) {
        try {
            return [TimeZoneInfo]::FindSystemTimeZoneById($timeZoneId)
        }
        catch {
            continue
        }
    }

    return $null
}

function Resolve-LeagueNextWaiverRunUtc {
    param(
        [Parameter(Mandatory = $true)][object]$League,
        [datetime]$NowUtc = [datetime]::UtcNow
    )

    if ($null -eq $League.settings) { return $null }

    $settings = $League.settings
    if ([int]$settings.disable_adds -ne 0) { return $null }
    if ([int]$settings.daily_waivers -ne 1) { return $null }
    if ($null -eq $settings.daily_waivers_days -or $null -eq $settings.daily_waivers_hour) { return $null }

    $waiverHour = [int]$settings.daily_waivers_hour
    if ($waiverHour -lt 0 -or $waiverHour -gt 23) { return $null }

    $dayModes = @(ConvertFrom-SleeperDailyWaiverDays -EncodedDays ([int]$settings.daily_waivers_days))
    if ($dayModes.Count -ne 7) { return $null }

    $unsupportedModes = @($dayModes | Where-Object { $_ -notin @(1, 2) })
    if ($unsupportedModes.Count -gt 0) {
        Write-Warning "Cannot derive next waiver run: daily waiver schedule contains unvalidated Sleeper mode(s): $($unsupportedModes -join ', ')."
        return $null
    }

    if (-not ($dayModes -contains 1)) { return $null }

    $waiverTimeZone = Get-SleeperWaiverTimeZone
    if ($null -eq $waiverTimeZone) {
        Write-Warning "Cannot derive next waiver run: Sleeper Pacific timezone is unavailable on this host."
        return $null
    }

    $normalizedNowUtc = if ($NowUtc.Kind -eq [DateTimeKind]::Unspecified) {
        [DateTime]::SpecifyKind($NowUtc, [DateTimeKind]::Utc)
    } else {
        $NowUtc.ToUniversalTime()
    }

    $nowPacific = [TimeZoneInfo]::ConvertTimeFromUtc($normalizedNowUtc, $waiverTimeZone)

    for ($offset = 0; $offset -le 7; $offset++) {
        $candidateDate = $nowPacific.Date.AddDays($offset)
        $mondayBasedDayIndex = (([int]$candidateDate.DayOfWeek + 6) % 7)

        if ($dayModes[$mondayBasedDayIndex] -ne 1) { continue }

        $candidateLocal = [DateTime]::SpecifyKind(
            $candidateDate.AddHours($waiverHour),
            [DateTimeKind]::Unspecified
        )

        if ($waiverTimeZone.IsInvalidTime($candidateLocal) -or $waiverTimeZone.IsAmbiguousTime($candidateLocal)) {
            Write-Warning "Cannot derive next waiver run safely across a DST transition at $candidateLocal."
            return $null
        }

        $candidateUtc = [TimeZoneInfo]::ConvertTimeToUtc($candidateLocal, $waiverTimeZone)
        if ($candidateUtc -gt $normalizedNowUtc) {
            return $candidateUtc
        }
    }

    return $null
}

Export-ModuleMember -Function Resolve-LeagueNextWaiverRunUtc
