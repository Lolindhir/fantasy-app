# Temporary compatibility bridge for Issue #493.
#
# This is intentionally not a general Sleeper acquisition-policy implementation.
# It consumes only already-derived provider-neutral league facts and encodes the
# current league's accepted waiver-only assumptions. Issue #492 is the permanent
# replacement and should remove this helper once normalized acquisition policy and
# current-state facts are available.

function Resolve-TemporaryWaiverOnlyAcquisitionCapability {
    param(
        [AllowNull()][Nullable[bool]]$WaiversOpen,
        [AllowNull()][string]$NextWaiverRun
    )

    $normalizedNextWaiverRun = $null
    $waiverTimingState = "missing"

    if (-not [string]::IsNullOrWhiteSpace($NextWaiverRun)) {
        try {
            $parsedNextWaiverRun = [DateTimeOffset]::Parse(
                $NextWaiverRun,
                [System.Globalization.CultureInfo]::InvariantCulture,
                [System.Globalization.DateTimeStyles]::AssumeUniversal
            )
            $normalizedNextWaiverRun = $parsedNextWaiverRun.ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss'Z'")
            $waiverTimingState = "known"
        }
        catch {
            $waiverTimingState = "invalid"
        }
    }

    $state = "known"
    if ($null -eq $WaiversOpen) {
        $state = "unknown"
    }
    elseif ([bool]$WaiversOpen) {
        if ($waiverTimingState -ne "known") {
            $state = "unknown"
        }
    }
    elseif ($waiverTimingState -eq "known") {
        # A future waiver run conflicts with the already-derived signal that adds
        # are unavailable. Do not choose one fact over the other.
        $state = "unknown"
    }

    $externalAddsAllowed = if ($null -eq $WaiversOpen) { $null } else { [bool]$WaiversOpen }
    $nextKnownWaiverRun = if ($state -eq "known" -and $externalAddsAllowed) {
        $normalizedNextWaiverRun
    }
    else {
        $null
    }

    return [PSCustomObject][ordered]@{
        State                         = $state
        ExternalAcquisitionMode       = "waiver-only"
        ExternalAddsAllowed           = $externalAddsAllowed
        ImmediateFreeAgentAddsAllowed = $false
        WaiverAddsAllowed             = $externalAddsAllowed
        NextWaiverRun                 = $nextKnownWaiverRun
        TradeRepairAllowed            = $false
    }
}

Export-ModuleMember -Function Resolve-TemporaryWaiverOnlyAcquisitionCapability
