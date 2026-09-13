. "$PSScriptRoot\MatchupReadModelCore.ps1"

# Canonical NFL schedule times are stored as local America/New_York wall-clock values.
# Parse one explicit format at a time so PowerShell binds the scalar TryParseExact
# overload deterministically on every supported runner/platform.
function ConvertTo-MrmKickoffUtc {
    param([AllowNull()][object]$Game)

    $day = [string](Get-MrmValue -Object $Game -Names @('GameDay'))
    $time = [string](Get-MrmValue -Object $Game -Names @('GameTime'))
    if ([string]::IsNullOrWhiteSpace($day) -or [string]::IsNullOrWhiteSpace($time)) { return $null }

    $parsed = [datetime]::MinValue
    $parsedSuccessfully = $false
    foreach ($format in @('yyyy-MM-dd HH:mm','yyyy-MM-dd H:mm')) {
        $candidate = [datetime]::MinValue
        if ([datetime]::TryParseExact(
            "$day $time",
            [string]$format,
            [System.Globalization.CultureInfo]::InvariantCulture,
            [System.Globalization.DateTimeStyles]::None,
            [ref]$candidate
        )) {
            $parsed = $candidate
            $parsedSuccessfully = $true
            break
        }
    }
    if (-not $parsedSuccessfully) { return $null }

    $unspecified = [datetime]::SpecifyKind($parsed, [DateTimeKind]::Unspecified)
    $utc = [System.TimeZoneInfo]::ConvertTimeToUtc($unspecified, (Get-MrmEasternTimeZone))
    return ([DateTimeOffset]$utc).ToString("yyyy-MM-ddTHH:mm:ss'Z'")
}
