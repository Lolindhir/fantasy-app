function ConvertTo-UnixMillisecondsFromDateString {
    param(
        [AllowNull()]
        [string]$date
    )

    if ([string]::IsNullOrWhiteSpace($date)) {
        return 0
    }

    try {
        $parsed = [datetime]::ParseExact(
            $date,
            "yyyy-MM-dd",
            [System.Globalization.CultureInfo]::InvariantCulture
        )

        $dto = [datetimeoffset]::new(
            $parsed.Year,
            $parsed.Month,
            $parsed.Day,
            0,
            0,
            0,
            [TimeSpan]::Zero
        )

        return $dto.ToUnixTimeMilliseconds()
    }
    catch {
        Write-Warning "Could not parse manual transaction date '$date'. Using CreatedAt = 0."
        return 0
    }
}

function ConvertFrom-UnixMillisecondsToDateString {
    param(
        [AllowNull()]
        [Nullable[Int64]]$timestamp
    )

    if ($null -eq $timestamp -or $timestamp -eq 0) {
        return $null
    }

    try {
        return [DateTimeOffset]::FromUnixTimeMilliseconds($timestamp).ToString("yyyy-MM-dd")
    }
    catch {
        Write-Warning "Could not parse unix timestamp '$timestamp'. Using Date = null."
        return $null
    }
}

function ConvertFrom-UnixMillisecondsToIsoString {
    param(
        [AllowNull()]
        [Nullable[Int64]]$timestamp
    )

    if ($null -eq $timestamp -or $timestamp -eq 0) {
        return $null
    }

    try {
        return [DateTimeOffset]::FromUnixTimeMilliseconds($timestamp).ToString("o")
    }
    catch {
        Write-Warning "Could not parse unix timestamp '$timestamp'. Using Date = null."
        return $null
    }
}