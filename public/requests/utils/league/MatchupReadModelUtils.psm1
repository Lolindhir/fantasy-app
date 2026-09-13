# Keep the implementation core private to this module boundary. The core predates this
# wrapper split and contains its original Export-ModuleMember declaration; shadow the
# cmdlet while loading it so this module can expose one deliberate public API below.
function Export-ModuleMember {
    param(
        [string[]]$Function,
        [string[]]$Cmdlet,
        [string[]]$Variable,
        [string[]]$Alias
    )
}

. "$PSScriptRoot\MatchupReadModelCore.ps1"
Remove-Item Function:\Export-ModuleMember -Force

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

function Update-MatchupHistoryReadModels {
    param(
        [Parameter(Mandatory = $true)][string]$CanonicalLeagueID,
        [Parameter(Mandatory = $true)][int]$CurrentSeason,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$Standings,
        [Parameter(Mandatory = $true)][hashtable]$Config,
        [string]$RepoRoot = (Get-MrmRepositoryRoot)
    )

    Ensure-MatchupHistoryReadModels @PSBoundParameters
}

Microsoft.PowerShell.Core\Export-ModuleMember -Function `
    New-MatchupSeasonReadModel, `
    Test-MatchupSeasonReadModelChanged, `
    Update-MatchupHistoryReadModels, `
    Get-MatchupParticipantOrderMap, `
    ConvertTo-MrmCanonicalPairings, `
    Get-MrmEffectiveScore
