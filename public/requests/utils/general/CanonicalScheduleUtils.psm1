Import-Module "$PSScriptRoot\NflTeamRegistryUtils.psm1" -ErrorAction Stop -Force

# Builds the App Schedule.json read model from canonical NFL facts (#347 G2):
#   source-data/nfl/schedules/<season>.json   (nflverse.schedules)
#   source-data/nfl/game-finality/<season>.json (nflverse.game-finality)
# No provider call is involved. Timing rule: the canonical GameTime is Eastern local time (America/New_York)
# without a zone marker (nflverse convention); it is converted with the IANA zone, never with a fixed offset.

$script:EasternTimeZone = $null
$script:CsuTeamRegistry = $null

function Get-CsuTeamRegistry {
    if ($null -eq $script:CsuTeamRegistry) {
        $repoRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)))
        $script:CsuTeamRegistry = Get-NflTeamRegistry -RepoRoot $repoRoot
    }
    return $script:CsuTeamRegistry
}

function Get-NflEasternTimeZone {
    if ($null -eq $script:EasternTimeZone) {
        foreach ($id in @('America/New_York', 'Eastern Standard Time')) {
            try {
                $script:EasternTimeZone = [TimeZoneInfo]::FindSystemTimeZoneById($id)
                break
            }
            catch { continue }
        }
        if ($null -eq $script:EasternTimeZone) {
            throw "Eastern time zone (America/New_York) is not available on this system."
        }
    }
    return $script:EasternTimeZone
}

# Converts a canonical GameDay (yyyy-MM-dd) and GameTime (HH:mm, Eastern local time) into UTC epoch seconds as the
# string form the App contract uses ("1788999600.0"). An empty GameTime means the kickoff is unknown and returns
# $null (never 0). A non-existent or ambiguous local time (daylight-saving transition) fails closed.
function ConvertTo-NflKickoffEpoch {
    param(
        [Parameter(Mandatory = $true)][string]$GameDay,
        [AllowNull()][string]$GameTime
    )

    if ([string]::IsNullOrWhiteSpace($GameTime)) { return $null }

    $local = [datetime]::MinValue
    $text = "$($GameDay.Trim()) $($GameTime.Trim())"
    if (-not [datetime]::TryParseExact(
            $text, 'yyyy-MM-dd HH:mm',
            [System.Globalization.CultureInfo]::InvariantCulture,
            [System.Globalization.DateTimeStyles]::None, [ref]$local)) {
        throw "Canonical kickoff '$text' is not a valid yyyy-MM-dd HH:mm value."
    }

    $local = [datetime]::SpecifyKind($local, [DateTimeKind]::Unspecified)
    $zone = Get-NflEasternTimeZone
    if ($zone.IsInvalidTime($local)) { throw "Canonical kickoff '$text' does not exist in Eastern time (daylight-saving gap)." }
    if ($zone.IsAmbiguousTime($local)) { throw "Canonical kickoff '$text' is ambiguous in Eastern time (daylight-saving overlap)." }

    $utc = [TimeZoneInfo]::ConvertTimeToUtc($local, $zone)
    $seconds = [DateTimeOffset]::new($utc, [TimeSpan]::Zero).ToUnixTimeSeconds()
    return ([string]$seconds + '.0')
}

# Tank01-compatible kickoff text such as "8:20p" or "1:00p"; empty/unknown time -> "TBD".
function Format-NflGameTimeText {
    param([AllowNull()][string]$GameTime)

    if ([string]::IsNullOrWhiteSpace($GameTime)) { return 'TBD' }
    $match = [regex]::Match($GameTime.Trim(), '^(\d{1,2}):(\d{2})$')
    if (-not $match.Success) { throw "Canonical GameTime '$GameTime' is not HH:mm." }

    $hour = [int]$match.Groups[1].Value
    $minute = $match.Groups[2].Value
    if ($hour -gt 23 -or [int]$minute -gt 59) { throw "Canonical GameTime '$GameTime' is out of range." }

    $suffix = if ($hour -ge 12) { 'p' } else { 'a' }
    $hour12 = $hour % 12
    if ($hour12 -eq 0) { $hour12 = 12 }
    return "${hour12}:${minute}${suffix}"
}

# Maps the canonical GameType to the App seasonType label. REG is evidenced by the published data; the
# postseason value is a documented decision (G1 decision 3) secured by the regression test.
function ConvertTo-AppSeasonType {
    param([Parameter(Mandatory = $true)][string]$GameType)

    switch ($GameType.Trim().ToUpperInvariant()) {
        'REG' { return 'Regular Season' }
        { $_ -in @('WC', 'DIV', 'CON', 'SB') } { return 'Post Season' }
        default { throw "Unsupported canonical NFL GameType '$GameType'." }
    }
}

# Provider spelling of a canonical team (Registry alias of kind provider-spelling, e.g. LA -> LAR, WAS -> WSH).
# Teams without such an alias keep their canonical abbreviation. Used for the legacy gameID and join stability.
function Get-NflTeamProviderSpelling {
    param([Parameter(Mandatory = $true)][string]$Team)

    $registry = Get-CsuTeamRegistry
    $canonical = Resolve-NflTeamKey -Registry $registry -Value $Team
    foreach ($alias in $registry.Aliases.GetEnumerator()) {
        if ($alias.Value.Team -eq $canonical -and $alias.Value.LastSeason -eq $null -and $alias.Key -ne $canonical) {
            return [string]$alias.Key
        }
    }
    return $canonical
}

# CBS box-score spelling: provider spelling with JAX -> JAC and WSH -> WAS (CBS is not a registry alias).
function Get-NflTeamCbsSpelling {
    param([Parameter(Mandatory = $true)][string]$Team)

    $provider = Get-NflTeamProviderSpelling -Team $Team
    switch ($provider) {
        'JAX' { return 'JAC' }
        'WSH' { return 'WAS' }
        default { return $provider }
    }
}

function Get-CsuValue {
    param([AllowNull()][object]$Object, [Parameter(Mandatory = $true)][string]$Name)
    if ($null -eq $Object) { return $null }
    if ($Object.PSObject.Properties.Name -contains $Name) { return $Object.$Name }
    return $null
}

function ConvertTo-CsuScore {
    param([AllowNull()][object]$Value)
    if ($null -eq $Value -or [string]::IsNullOrWhiteSpace([string]$Value)) { return $null }
    $parsed = 0.0
    if ([double]::TryParse([string]$Value, [System.Globalization.NumberStyles]::Float,
            [System.Globalization.CultureInfo]::InvariantCulture, [ref]$parsed)) {
        return [double]$parsed
    }
    return $null
}

# One App Schedule record from one canonical schedule row plus its finality. Field set and value shapes follow
# the published Tank01-compatible contract; teamIDHome/teamIDAway and home/away carry the canonical abbreviation
# (F3d). gameID keeps the provider spelling (LAR/WSH) for join stability; CanonicalGameID is additive.
function New-AppScheduleGame {
    param(
        [Parameter(Mandatory = $true)][object]$CanonicalGame,
        [Parameter(Mandatory = $true)][bool]$Final,
        [Parameter(Mandatory = $true)][int]$Season
    )

    $espnID = [string](Get-CsuValue -Object (Get-CsuValue -Object $CanonicalGame -Name 'ProviderGameIDs') -Name 'ESPN')
    if ([string]::IsNullOrWhiteSpace($espnID)) {
        throw "Canonical NFL game '$($CanonicalGame.GameID)' has no ESPN provider ID."
    }
    $espnID = $espnID.Trim()

    $awayTeam = ConvertTo-CanonicalNflTeamStrict -Team ([string]$CanonicalGame.AwayTeam) -Season $Season
    $homeTeam = ConvertTo-CanonicalNflTeamStrict -Team ([string]$CanonicalGame.HomeTeam) -Season $Season

    $gameDay = [string]$CanonicalGame.GameDay
    $dateKey = $gameDay.Replace('-', '')
    if ($dateKey -notmatch '^\d{8}$') { throw "Canonical NFL game '$($CanonicalGame.GameID)' has an invalid GameDay '$gameDay'." }

    $gameID = "${dateKey}_$(Get-NflTeamProviderSpelling -Team $awayTeam)@$(Get-NflTeamProviderSpelling -Team $homeTeam)"
    $cbsID = "${dateKey}_$(Get-NflTeamCbsSpelling -Team $awayTeam)@$(Get-NflTeamCbsSpelling -Team $homeTeam)"

    $epoch = ConvertTo-NflKickoffEpoch -GameDay $gameDay -GameTime ([string](Get-CsuValue -Object $CanonicalGame -Name 'GameTime'))
    $overtime = [string](Get-CsuValue -Object $CanonicalGame -Name 'Overtime')
    $hasOvertime = -not [string]::IsNullOrWhiteSpace($overtime) -and $overtime -ne '0'

    $record = [ordered]@{
        gameID          = $gameID
        CanonicalGameID = [string]$CanonicalGame.GameID
        espnID          = $espnID
        season          = [string]$Season
        seasonType      = ConvertTo-AppSeasonType -GameType ([string]$CanonicalGame.GameType)
        gameWeek        = "Week $([int]$CanonicalGame.Week)"
        gameDate        = $dateKey
        gameTime        = Format-NflGameTimeText -GameTime ([string](Get-CsuValue -Object $CanonicalGame -Name 'GameTime'))
        gameTime_epoch  = if ($null -eq $epoch) { '' } else { $epoch }
        away            = $awayTeam
        home            = $homeTeam
        teamIDAway      = $awayTeam
        teamIDHome      = $homeTeam
        neutralSite     = if ([string](Get-CsuValue -Object $CanonicalGame -Name 'Location') -eq 'Neutral') { 'True' } else { 'False' }
        gameStatus      = if ($Final) { if ($hasOvertime) { 'Final/OT' } else { 'Final' } } else { 'Scheduled' }
        gameStatusCode  = if ($Final) { '2' } else { '0' }
        espnLink        = "https://www.espn.com/nfl/boxscore/_/gameId/$espnID"
        cbsLink         = "https://www.cbssports.com/nfl/gametracker/boxscore/NFL_$cbsID"
    }

    if ($Final) {
        $awayScore = ConvertTo-CsuScore (Get-CsuValue -Object $CanonicalGame -Name 'AwayScore')
        $homeScore = ConvertTo-CsuScore (Get-CsuValue -Object $CanonicalGame -Name 'HomeScore')
        if ($null -ne $awayScore -and $null -ne $homeScore) {
            $record['awayPts'] = $awayScore
            $record['homePts'] = $homeScore
        }
    }

    return [PSCustomObject]$record
}

function ConvertTo-CanonicalNflTeamStrict {
    param([AllowNull()][string]$Team, [Nullable[int]]$Season = $null)

    if ([string]::IsNullOrWhiteSpace($Team)) { throw 'Canonical NFL schedule row has an empty team.' }
    return (Resolve-NflTeamKey -Registry (Get-CsuTeamRegistry) -Value $Team -Season $Season)
}

# Reads and validates the canonical schedule plus finality for one season and returns the App Schedule array.
# Fails closed on a missing file, unexpected source/season, duplicate or missing ESPN/game IDs, and any
# schedule game without a finality row (and vice versa). GameTypes limits the scope (default: regular season,
# matching the former Tank01 seasonType=reg call).
function Get-CanonicalAppSchedule {
    param(
        [Parameter(Mandatory = $true)][int]$Season,
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [string[]]$GameTypes = @('REG')
    )

    $schedulePath = Join-Path $RepoRoot "source-data/nfl/schedules/$Season.json"
    $finalityPath = Join-Path $RepoRoot "source-data/nfl/game-finality/$Season.json"
    if (-not (Test-Path $schedulePath)) { throw "Canonical NFL schedule is required: $schedulePath" }
    if (-not (Test-Path $finalityPath)) { throw "Canonical NFL game finality is required: $finalityPath" }

    $schedule = Get-Content $schedulePath -Raw | ConvertFrom-Json
    $finality = Get-Content $finalityPath -Raw | ConvertFrom-Json
    if ([int]$schedule.Season -ne $Season) { throw "Canonical NFL schedule season mismatch: expected $Season, got $($schedule.Season)." }
    if ([int]$finality.Season -ne $Season) { throw "Canonical NFL game finality season mismatch: expected $Season, got $($finality.Season)." }
    if ([string]$schedule.SourceDataset -ne 'nflverse.schedules') { throw "Unexpected canonical NFL schedule source '$($schedule.SourceDataset)'." }
    if ([string]$finality.SourceDataset -ne 'nflverse.game-finality') { throw "Unexpected canonical NFL finality source '$($finality.SourceDataset)'." }

    $finalityByGame = @{}
    foreach ($row in @($finality.Games)) {
        $id = [string](Get-CsuValue -Object $row -Name 'GameID')
        if ([string]::IsNullOrWhiteSpace($id)) { throw 'Canonical NFL game-finality row is missing GameID.' }
        if ($finalityByGame.ContainsKey($id)) { throw "Duplicate canonical NFL game-finality GameID '$id'." }
        $finalityByGame[$id] = $row
    }

    $allGames = @($schedule.Games)
    if ($allGames.Count -eq 0) { throw "Canonical NFL schedule $Season contains no games." }
    $scheduleIDs = @{}
    foreach ($game in $allGames) {
        $id = [string](Get-CsuValue -Object $game -Name 'GameID')
        if ([string]::IsNullOrWhiteSpace($id)) { throw 'Canonical NFL schedule row is missing GameID.' }
        if ($scheduleIDs.ContainsKey($id)) { throw "Duplicate canonical NFL schedule GameID '$id'." }
        $scheduleIDs[$id] = $true
        if (-not $finalityByGame.ContainsKey($id)) { throw "Canonical NFL finality is missing schedule GameID '$id'." }
    }
    foreach ($id in $finalityByGame.Keys) {
        if (-not $scheduleIDs.ContainsKey($id)) { throw "Canonical NFL finality lists GameID '$id' that is not in the schedule." }
    }

    $games = @()
    $seenEspn = @{}
    $seenGameIDs = @{}
    foreach ($canonical in $allGames) {
        if ([string]$canonical.GameType -notin $GameTypes) { continue }
        $final = [bool](Get-CsuValue -Object $finalityByGame[[string]$canonical.GameID] -Name 'Final')
        $record = New-AppScheduleGame -CanonicalGame $canonical -Final $final -Season $Season
        if ($seenEspn.ContainsKey($record.espnID)) { throw "Duplicate ESPN game ID '$($record.espnID)' in canonical NFL schedule." }
        if ($seenGameIDs.ContainsKey($record.gameID)) { throw "Duplicate App gameID '$($record.gameID)' in canonical NFL schedule." }
        $seenEspn[$record.espnID] = $true
        $seenGameIDs[$record.gameID] = $true
        $games += $record
    }
    if ($games.Count -eq 0) { throw "Canonical NFL schedule $Season has no games for types $($GameTypes -join ', ')." }

    return @($games | Sort-Object { [string]$_.gameDate }, { if ([string]::IsNullOrEmpty([string]$_.gameTime_epoch)) { [double]::MaxValue } else { [double]$_.gameTime_epoch } }, { [string]$_.gameID })
}

Export-ModuleMember -Function ConvertTo-NflKickoffEpoch, Format-NflGameTimeText, ConvertTo-AppSeasonType, `
    Get-NflTeamProviderSpelling, Get-NflTeamCbsSpelling, New-AppScheduleGame, Get-CanonicalAppSchedule
