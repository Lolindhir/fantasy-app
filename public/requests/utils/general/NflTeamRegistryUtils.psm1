# Fail-closed resolver for NFL team keys against the canonical team registry (source-data/nfl/teams.json).
# Accepts canonical abbreviations, provider spellings (LAR, WSH), season-bounded historical aliases
# (OAK, SD, STL) and the legacy numeric app team IDs. Mirrors tools/nfl_source_data_lib/teams.py.

function Get-NflTeamRegistry {
    param([Parameter(Mandatory = $true)][string]$RepoRoot)

    $path = Join-Path $RepoRoot 'source-data/nfl/teams.json'
    if (-not (Test-Path $path)) {
        throw "Canonical NFL team registry is required: $path"
    }

    $payload = Get-Content $path -Raw -Encoding UTF8 | ConvertFrom-Json
    if ([string]$payload.SourceDataset -ne 'nflverse.teams') {
        throw "Unexpected canonical NFL team registry source '$($payload.SourceDataset)'."
    }

    $teams = @($payload.Teams)
    if ($teams.Count -ne 32) {
        throw "Canonical NFL team registry must list 32 teams, found $($teams.Count)."
    }

    $byAbbr = @{}
    $aliases = @{}
    $legacy = @{}
    foreach ($team in $teams) {
        $abbr = [string]$team.TeamAbbr
        if ($byAbbr.ContainsKey($abbr)) { throw "Duplicate NFL team '$abbr' in the canonical registry." }
        $byAbbr[$abbr] = $team
        $legacyId = [string]$team.LegacyAppTeamID
        if (-not [string]::IsNullOrWhiteSpace($legacyId)) {
            if ($legacy.ContainsKey($legacyId)) { throw "Duplicate legacy NFL team ID '$legacyId' in the canonical registry." }
            $legacy[$legacyId] = $abbr
        }
    }
    foreach ($team in $teams) {
        foreach ($alias in @($team.Aliases)) {
            $key = ([string]$alias.Alias).ToUpperInvariant()
            if ($aliases.ContainsKey($key) -or $byAbbr.ContainsKey($key)) { throw "Ambiguous NFL team alias '$key'." }
            $lastSeason = $null
            if ($null -ne $alias.PSObject.Properties['LastSeason'] -and $null -ne $alias.LastSeason) {
                $lastSeason = [int]$alias.LastSeason
            }
            $aliases[$key] = [PSCustomObject]@{ Team = [string]$team.TeamAbbr; LastSeason = $lastSeason }
        }
    }

    return [PSCustomObject]@{
        Teams  = $byAbbr
        Aliases = $aliases
        Legacy = $legacy
    }
}

function Resolve-NflTeamKey {
    param(
        [Parameter(Mandatory = $true)][object]$Registry,
        [AllowNull()][string]$Value,
        [Nullable[int]]$Season = $null
    )

    if ([string]::IsNullOrWhiteSpace($Value)) { throw 'Empty NFL team key.' }
    $text = $Value.Trim()
    $key = $text.ToUpperInvariant()

    if ($Registry.Teams.ContainsKey($key)) { return $key }

    if ($Registry.Aliases.ContainsKey($key)) {
        $alias = $Registry.Aliases[$key]
        if ($null -eq $alias.LastSeason) { return $alias.Team }
        if ($null -eq $Season) { throw "Historical NFL team alias '$key' requires a season." }
        if ([int]$Season -gt [int]$alias.LastSeason) { throw "NFL team alias '$key' is not valid after season $($alias.LastSeason)." }
        return $alias.Team
    }

    if ($Registry.Legacy.ContainsKey($text)) { return $Registry.Legacy[$text] }

    throw "Unknown NFL team key '$text'."
}

$script:DefaultNflTeamRegistry = $null

function Get-DefaultNflTeamRegistry {
    if ($null -eq $script:DefaultNflTeamRegistry) {
        $repoRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)))
        $script:DefaultNflTeamRegistry = Get-NflTeamRegistry -RepoRoot $repoRoot
    }
    return $script:DefaultNflTeamRegistry
}

# Join key for matching NFL team references that may still use different key forms (canonical abbreviation,
# provider spelling or legacy numeric app ID). Tolerant on purpose: a value the registry cannot resolve is
# returned trimmed and unchanged, so an unknown team stays an unknown team in the caller's existing fail-closed
# handling instead of aborting the whole generation. Empty input returns $null. Emitted data is never rewritten.
function Get-NflTeamJoinKey {
    param(
        [AllowNull()][object]$Value,
        [Nullable[int]]$Season = $null
    )

    if ($null -eq $Value) { return $null }
    $text = ([string]$Value).Trim()
    if ([string]::IsNullOrWhiteSpace($text)) { return $null }

    $registry = Get-DefaultNflTeamRegistry
    try {
        return Resolve-NflTeamKey -Registry $registry -Value $text -Season $Season
    }
    catch {
        return $text
    }
}

Export-ModuleMember -Function Get-NflTeamRegistry, Resolve-NflTeamKey, Get-NflTeamJoinKey
