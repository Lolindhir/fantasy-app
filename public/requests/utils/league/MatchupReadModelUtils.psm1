. "$PSScriptRoot\FantasyGameContextCore.ps1"
Import-Module "$PSScriptRoot\StandingUtils.psm1" -ErrorAction Stop -Force
Import-Module "$PSScriptRoot\FantasyTeamOrderUtils.psm1" -ErrorAction Stop -Force

function Get-MrmValue {
    param(
        [AllowNull()][object]$Object,
        [Parameter(Mandatory = $true)][string[]]$Names
    )

    if ($null -eq $Object) { return $null }
    foreach ($name in $Names) {
        if ($Object.PSObject.Properties.Name -contains $name) { return $Object.$name }
    }
    return $null
}

function Get-MrmCollection {
    param([AllowNull()][object]$Value)

    if ($null -eq $Value) { return @() }
    if ($Value -is [string] -or $Value -isnot [System.Collections.IEnumerable]) { return @($Value) }
    return @($Value)
}

function Get-MrmRepositoryRoot {
    return [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\..\..\.."))
}

function Get-MrmSleeperMapping {
    param([AllowNull()][object]$Row)

    return @(
        Get-MrmCollection (Get-MrmValue -Object $Row -Names @('ProviderMappings')) |
            Where-Object { [string](Get-MrmValue -Object $_ -Names @('Provider')) -eq 'Sleeper' }
    ) | Select-Object -First 1
}

function ConvertTo-MrmTeamID {
    param([AllowNull()][object]$Row)

    $mapping = Get-MrmSleeperMapping -Row $Row
    $value = if ($null -ne $mapping) {
        Get-MrmValue -Object $mapping -Names @('ProviderRosterID')
    }
    else {
        Get-MrmValue -Object $Row -Names @('roster_id','RosterID','TeamID','FantasyTeamID')
    }

    if ($null -eq $value -or [string]::IsNullOrWhiteSpace([string]$value)) { return $null }
    $parsed = 0
    if ([int]::TryParse([string]$value, [ref]$parsed)) { return $parsed }
    return [string]$value
}

function Get-MrmProviderMatchupID {
    param([AllowNull()][object]$Row)

    $mapping = Get-MrmSleeperMapping -Row $Row
    if ($null -ne $mapping) {
        $value = Get-MrmValue -Object $mapping -Names @('ProviderMatchupID')
        if ($null -ne $value) { return [string]$value }
    }
    $value = Get-MrmValue -Object $Row -Names @('matchup_id','MatchupID')
    if ($null -eq $value) { return $null }
    return [string]$value
}

function Get-MrmEffectiveScore {
    param([AllowNull()][object]$Row)

    $custom = Get-MrmValue -Object $Row -Names @('custom_points','CustomPoints')
    if ($null -ne $custom -and -not [string]::IsNullOrWhiteSpace([string]$custom)) {
        return [PSCustomObject][ordered]@{ Points = [double]$custom; ScoreKind = 'adjusted' }
    }

    $points = Get-MrmValue -Object $Row -Names @('points','Points')
    if ($null -eq $points -or [string]::IsNullOrWhiteSpace([string]$points)) {
        return [PSCustomObject][ordered]@{ Points = $null; ScoreKind = 'standard' }
    }
    return [PSCustomObject][ordered]@{ Points = [double]$points; ScoreKind = 'standard' }
}

function Get-MrmLiveRowMap {
    param([AllowEmptyCollection()][array]$Rows)

    $map = @{}
    $conflicts = @{}
    foreach ($row in @($Rows)) {
        $teamID = ConvertTo-MrmTeamID -Row $row
        if ($null -eq $teamID) { continue }
        $key = [string]$teamID
        if ($map.ContainsKey($key)) {
            $conflicts[$key] = $true
            continue
        }
        $map[$key] = $row
    }
    return [PSCustomObject]@{ Rows = $map; Conflicts = $conflicts }
}

function Get-MatchupParticipantOrderMap {
    param(
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$Standings,
        [Parameter(Mandatory = $true)][int]$Season,
        [switch]$HistoricalCutoff
    )

    $overall = $null
    if (-not $HistoricalCutoff) {
        $overall = @($Standings | Where-Object { [string]$_.Season -eq 'AllTime' }) | Select-Object -First 1
    }
    else {
        $seasonRows = @(
            $Standings | Where-Object {
                [string]$_.Season -match '^\d{4}$' -and [int]$_.Season -le $Season
            }
        )
        if ($seasonRows.Count -gt 0) {
            $overall = Get-OutputStandingsForAllTime -allSeasonStandings $seasonRows
        }
    }

    if ($null -eq $overall -or @($overall.Playoffs).Count -eq 0) {
        throw "Matchups $Season cannot resolve the All-Time Overall Standings order."
    }

    return Get-FantasyTeamNeutralOrderIndex -AllTimeOverallStandings @($overall.Playoffs)
}

function ConvertTo-MrmCanonicalPairings {
    param(
        [Parameter(Mandatory = $true)][int]$Season,
        [Parameter(Mandatory = $true)][int]$Week,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$Rows,
        [Parameter(Mandatory = $true)][hashtable]$ParticipantOrder,
        [AllowEmptyCollection()][array]$LiveRows = @(),
        [AllowNull()][ref]$MalformedEvidenceFound
    )

    if ($null -ne $MalformedEvidenceFound) { $MalformedEvidenceFound.Value = $false }
    $live = Get-MrmLiveRowMap -Rows $LiveRows
    $groups = @{}
    foreach ($row in @($Rows)) {
        $canonicalID = [string](Get-MrmValue -Object $row -Names @('CanonicalLeagueMatchupID'))
        $providerID = Get-MrmProviderMatchupID -Row $row
        $groupKey = if (-not [string]::IsNullOrWhiteSpace($canonicalID)) { "canonical:$canonicalID" } elseif (-not [string]::IsNullOrWhiteSpace($providerID)) { "provider:$providerID" } else { $null }
        if ($null -eq $groupKey) {
            if ($null -ne $MalformedEvidenceFound) { $MalformedEvidenceFound.Value = $true }
            continue
        }
        if (-not $groups.ContainsKey($groupKey)) { $groups[$groupKey] = @() }
        $groups[$groupKey] += $row
    }

    $result = @()
    foreach ($groupKey in @($groups.Keys | Sort-Object)) {
        $groupRows = @($groups[$groupKey])

        $internalParticipants = @()
        $scoreEvidenceUnknown = $false
        $seenTeams = @{}
        foreach ($row in $groupRows) {
            $teamID = ConvertTo-MrmTeamID -Row $row
            if ($null -eq $teamID) { $scoreEvidenceUnknown = $true; continue }
            $teamKey = [string]$teamID
            if ($seenTeams.ContainsKey($teamKey)) { $scoreEvidenceUnknown = $true; continue }
            $seenTeams[$teamKey] = $true
            if (-not $ParticipantOrder.ContainsKey($teamKey)) {
                throw "Matchups $Season Week $Week cannot order TeamID $teamKey from All-Time Overall Standings."
            }

            $scoreRow = $row
            if ($live.Conflicts.ContainsKey($teamKey)) {
                $scoreEvidenceUnknown = $true
            }
            elseif ($live.Rows.ContainsKey($teamKey)) {
                $liveRow = $live.Rows[$teamKey]
                $canonicalProviderID = Get-MrmProviderMatchupID -Row $row
                $liveProviderID = Get-MrmProviderMatchupID -Row $liveRow
                if (-not [string]::IsNullOrWhiteSpace($canonicalProviderID) -and -not [string]::IsNullOrWhiteSpace($liveProviderID) -and $canonicalProviderID -ne $liveProviderID) {
                    $scoreEvidenceUnknown = $true
                }
                else {
                    $scoreRow = $liveRow
                }
            }

            $score = Get-MrmEffectiveScore -Row $scoreRow
            $internalParticipants += [PSCustomObject][ordered]@{
                TeamID = $teamID
                Points = $score.Points
                ScoreKind = [string]$score.ScoreKind
                Order = [int]$ParticipantOrder[$teamKey]
                SourceRow = $row
            }
        }

        if ($internalParticipants.Count -ne 2) {
            if ($null -ne $MalformedEvidenceFound) { $MalformedEvidenceFound.Value = $true }
            continue
        }
        $internalParticipants = @($internalParticipants | Sort-Object Order)
        $teamIDs = @($internalParticipants | ForEach-Object { [string]$_.TeamID })
        $result += [PSCustomObject][ordered]@{
            FantasyMatchupID = New-FantasyGameContextMatchupID -Season ([string]$Season) -Week $Week -FantasyTeamIDs $teamIDs
            Participants = $internalParticipants
            ScoreEvidenceUnknown = $scoreEvidenceUnknown
        }
    }

    return @($result | Sort-Object FantasyMatchupID)
}

function Get-MrmEasternTimeZone {
    foreach ($id in @('America/New_York','Eastern Standard Time')) {
        try { return [System.TimeZoneInfo]::FindSystemTimeZoneById($id) } catch {}
    }
    throw 'Could not resolve the America/New_York time zone for canonical NFL schedule kickoffs.'
}

function ConvertTo-MrmKickoffUtc {
    param([AllowNull()][object]$Game)

    $day = [string](Get-MrmValue -Object $Game -Names @('GameDay'))
    $time = [string](Get-MrmValue -Object $Game -Names @('GameTime'))
    if ([string]::IsNullOrWhiteSpace($day) -or [string]::IsNullOrWhiteSpace($time)) { return $null }

    $parsed = [datetime]::MinValue
    $formats = @('yyyy-MM-dd HH:mm','yyyy-MM-dd H:mm')
    if (-not [datetime]::TryParseExact("$day $time", $formats, [System.Globalization.CultureInfo]::InvariantCulture, [System.Globalization.DateTimeStyles]::None, [ref]$parsed)) {
        return $null
    }
    $unspecified = [datetime]::SpecifyKind($parsed, [DateTimeKind]::Unspecified)
    $utc = [System.TimeZoneInfo]::ConvertTimeToUtc($unspecified, (Get-MrmEasternTimeZone))
    return ([DateTimeOffset]$utc).ToString("yyyy-MM-ddTHH:mm:ss'Z'")
}

function Get-MrmCanonicalScheduleGames {
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [Parameter(Mandatory = $true)][int]$Season
    )

    $path = Join-Path $RepoRoot "source-data/nfl/schedules/$Season.json"
    if (-not (Test-Path $path)) { throw "Canonical NFL schedule not found for Matchups $Season at $path." }
    $document = Get-Content $path -Raw | ConvertFrom-Json
    return @(Get-MrmCollection (Get-MrmValue -Object $document -Names @('Games')) | Where-Object {
        $gameType = [string](Get-MrmValue -Object $_ -Names @('GameType'))
        [string]::IsNullOrWhiteSpace($gameType) -or $gameType -eq 'REG'
    })
}

function Get-MrmFinalityMap {
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [Parameter(Mandatory = $true)][int]$Season
    )

    $path = Join-Path $RepoRoot "source-data/nfl/game-finality/$Season.json"
    if (-not (Test-Path $path)) { return $null }
    $document = Get-Content $path -Raw | ConvertFrom-Json
    $map = @{}
    foreach ($game in @(Get-MrmCollection (Get-MrmValue -Object $document -Names @('Games')))) {
        $gameID = [string](Get-MrmValue -Object $game -Names @('GameID'))
        if ([string]::IsNullOrWhiteSpace($gameID)) { continue }
        if ($map.ContainsKey($gameID)) { throw "Duplicate canonical NFL finality GameID '$gameID' for season $Season." }
        $map[$gameID] = Get-MrmValue -Object $game -Names @('Final')
    }
    return $map
}

function Get-MrmWeeklyAssignmentMap {
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [Parameter(Mandatory = $true)][int]$Season,
        [Parameter(Mandatory = $true)][int]$Week
    )

    $path = Join-Path $RepoRoot ("source-data/nfl/weekly-rosters/{0}/{1:D2}.json" -f $Season, $Week)
    if (-not (Test-Path $path)) { return $null }
    $document = Get-Content $path -Raw | ConvertFrom-Json
    $map = @{}
    foreach ($assignment in @(Get-FgcWeeklyRosterAssignments -Document $document)) {
        $canonicalID = [string]$assignment.CanonicalPlayerID
        if ([string]::IsNullOrWhiteSpace($canonicalID)) { continue }
        if (-not $map.ContainsKey($canonicalID)) { $map[$canonicalID] = @() }
        $teamAbbr = ([string]$assignment.TeamAbbr).Trim().ToUpperInvariant()
        if (-not [string]::IsNullOrWhiteSpace($teamAbbr)) { $map[$canonicalID] += $teamAbbr }
    }
    foreach ($key in @($map.Keys)) { $map[$key] = @($map[$key] | Sort-Object -Unique) }
    return $map
}

function Get-MrmStarterGameResolution {
    param(
        [Parameter(Mandatory = $true)][object]$Starter,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$WeekGames,
        [AllowNull()][hashtable]$WeeklyAssignments,
        [AllowNull()][hashtable]$FinalityMap
    )

    if ($null -eq $FinalityMap -or $null -eq $WeeklyAssignments) { return 'unknown' }
    $player = Get-MrmValue -Object $Starter -Names @('Player')
    $canonicalID = [string](Get-MrmValue -Object $player -Names @('CanonicalPlayerID'))
    $teamAbbrs = @()
    if (-not [string]::IsNullOrWhiteSpace($canonicalID) -and $WeeklyAssignments.ContainsKey($canonicalID)) {
        $teamAbbrs += @($WeeklyAssignments[$canonicalID])
    }

    foreach ($mapping in @(Get-MrmCollection (Get-MrmValue -Object $player -Names @('ProviderMappings')))) {
        if ([string](Get-MrmValue -Object $mapping -Names @('Provider')) -ne 'Sleeper') { continue }
        $providerPlayerID = ([string](Get-MrmValue -Object $mapping -Names @('ProviderPlayerID'))).Trim().ToUpperInvariant()
        if ($providerPlayerID -match '^[A-Z]{2,3}$') { $teamAbbrs += $providerPlayerID }
    }
    $teamAbbrs = @($teamAbbrs | Sort-Object -Unique)
    if ($teamAbbrs.Count -eq 0) { return 'unknown' }

    $candidateGames = @(
        $WeekGames | Where-Object {
            $away = ([string](Get-MrmValue -Object $_ -Names @('AwayTeam'))).Trim().ToUpperInvariant()
            $home = ([string](Get-MrmValue -Object $_ -Names @('HomeTeam'))).Trim().ToUpperInvariant()
            $teamAbbrs -contains $away -or $teamAbbrs -contains $home
        } | Sort-Object { [string](Get-MrmValue -Object $_ -Names @('GameID')) } -Unique
    )
    if ($candidateGames.Count -ne 1) { return 'unknown' }

    $gameID = [string](Get-MrmValue -Object $candidateGames[0] -Names @('GameID'))
    if ([string]::IsNullOrWhiteSpace($gameID) -or -not $FinalityMap.ContainsKey($gameID) -or $null -eq $FinalityMap[$gameID]) { return 'unknown' }
    return $(if ([bool]$FinalityMap[$gameID]) { 'final' } else { 'open' })
}

function Get-MrmExpectedStarterCount {
    param([AllowNull()][object]$LeagueSource)

    $positions = @(Get-MrmCollection (Get-MrmValue -Object $LeagueSource -Names @('RosterPositions')))
    return @($positions | Where-Object { @('BN','IR','TAXI','RESERVE') -notcontains ([string]$_).ToUpperInvariant() }).Count
}

function Resolve-MrmActiveCompletionState {
    param(
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$TeamIDs,
        [Parameter(Mandatory = $true)][object]$DecisionFacts
    )

    $relevance = Get-MrmValue -Object $DecisionFacts -Names @('FantasyRelevance')
    if ($null -eq $relevance) { return 'unknown' }
    $states = @{}
    foreach ($team in @(Get-MrmCollection (Get-MrmValue -Object $relevance -Names @('Teams')))) {
        $teamID = Get-MrmValue -Object $team -Names @('FantasyTeamID')
        if ($null -ne $teamID) { $states[[string]$teamID] = $team }
    }
    $evaluations = @{}
    foreach ($evaluation in @(Get-MrmCollection (Get-MrmValue -Object $DecisionFacts -Names @('TeamLineupEvaluations')))) {
        $teamID = Get-MrmValue -Object $evaluation -Names @('FantasyTeamID')
        if ($null -ne $teamID) { $evaluations[[string]$teamID] = $evaluation }
    }

    $unknown = $false
    foreach ($teamID in $TeamIDs) {
        $key = [string]$teamID
        if (-not $states.ContainsKey($key)) { $unknown = $true; continue }
        $state = $states[$key]
        $hasPath = Get-MrmValue -Object $state -Names @('HasRemainingScoringPath')
        $repairable = @(
            Get-MrmCollection (Get-MrmValue -Object $state -Names @('Slots')) | Where-Object {
                [string](Get-MrmValue -Object (Get-MrmValue -Object $_ -Names @('Repairability')) -Names @('State')) -eq 'repairable'
            }
        ).Count -gt 0
        if ($hasPath -eq $true -or $repairable) { return 'open' }
        if ($null -eq $hasPath) { $unknown = $true }

        if (-not $evaluations.ContainsKey($key)) {
            $unknown = $true
        }
        else {
            $evaluationState = [string](Get-MrmValue -Object $evaluations[$key] -Names @('State'))
            if (@('unknown','review') -contains $evaluationState) { $unknown = $true }
        }

        foreach ($slot in @(Get-MrmCollection (Get-MrmValue -Object $state -Names @('Slots')))) {
            if ([string](Get-MrmValue -Object $slot -Names @('State')) -eq 'unknown') { $unknown = $true }
            $repairability = Get-MrmValue -Object $slot -Names @('Repairability')
            if ($null -ne $repairability -and [string](Get-MrmValue -Object $repairability -Names @('State')) -eq 'unknown') { $unknown = $true }
        }
    }

    return $(if ($unknown) { 'unknown' } else { 'final' })
}

function Resolve-MrmNonActiveCompletionState {
    param(
        [Parameter(Mandatory = $true)][object]$Pairing,
        [Parameter(Mandatory = $true)][object]$LeagueSource,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$WeekGames,
        [AllowNull()][hashtable]$WeeklyAssignments,
        [AllowNull()][hashtable]$FinalityMap,
        [AllowNull()][string]$FirstKickoffUtc,
        [DateTimeOffset]$AsOfUtc = [DateTimeOffset]::UtcNow
    )

    if (-not [string]::IsNullOrWhiteSpace($FirstKickoffUtc)) {
        try {
            if ([DateTimeOffset]::Parse($FirstKickoffUtc) -gt $AsOfUtc) {
                $starterEvidence = 0
                foreach ($participant in @($Pairing.Participants)) {
                    $starterEvidence += @(Get-MrmCollection (Get-MrmValue -Object $participant.SourceRow -Names @('StarterPoints'))).Count
                }
                return $(if ($starterEvidence -gt 0) { 'open' } else { 'unknown' })
            }
        } catch { return 'unknown' }
    }

    $expectedStarterCount = Get-MrmExpectedStarterCount -LeagueSource $LeagueSource
    if ($expectedStarterCount -le 0) { return 'unknown' }
    $unknown = $false
    foreach ($participant in @($Pairing.Participants)) {
        $starters = @(Get-MrmCollection (Get-MrmValue -Object $participant.SourceRow -Names @('StarterPoints')))
        if ($starters.Count -lt $expectedStarterCount) { $unknown = $true }
        foreach ($starter in $starters) {
            $resolution = Get-MrmStarterGameResolution -Starter $starter -WeekGames $WeekGames -WeeklyAssignments $WeeklyAssignments -FinalityMap $FinalityMap
            if ($resolution -eq 'open') { return 'open' }
            if ($resolution -eq 'unknown') { $unknown = $true }
        }
    }
    return $(if ($unknown) { 'unknown' } else { 'final' })
}

function Get-MrmKnownLastWeek {
    param([Parameter(Mandatory = $true)][object]$LeagueSource)

    $weekStructure = Get-MrmValue -Object $LeagueSource -Names @('WeekStructure')
    $settings = Get-MrmValue -Object $LeagueSource -Names @('Settings')
    $expectedLast = [int](Get-MrmValue -Object $weekStructure -Names @('ExpectedLastLeagueWeek'))
    if ($expectedLast -le 0) { $expectedLast = [int](Get-MrmValue -Object $weekStructure -Names @('FinalLeagueWeek')) }
    if ($expectedLast -le 0) { $expectedLast = [int](Get-MrmValue -Object $settings -Names @('last_scored_leg')) }
    if ($expectedLast -le 0) { throw 'Cannot resolve the last fantasy league week.' }

    if ([string](Get-MrmValue -Object $LeagueSource -Names @('Status')) -eq 'complete') {
        $final = [int](Get-MrmValue -Object $weekStructure -Names @('FinalLeagueWeek'))
        return $(if ($final -gt 0) { [Math]::Min($final, $expectedLast) } else { $expectedLast })
    }

    $playoffStart = [int](Get-MrmValue -Object $weekStructure -Names @('PlayoffStartWeek'))
    if ($playoffStart -le 0) { $playoffStart = [int](Get-MrmValue -Object $settings -Names @('playoff_week_start')) }
    if ($playoffStart -le 0) { return $expectedLast }
    $leg = [int](Get-MrmValue -Object $settings -Names @('leg'))
    if ($leg -lt $playoffStart) { return [Math]::Min($playoffStart - 1, $expectedLast) }

    $roundType = [int](Get-MrmValue -Object $weekStructure -Names @('PlayoffRoundType'))
    if ($roundType -eq 2) {
        $roundStart = $playoffStart + ([Math]::Floor(($leg - $playoffStart) / 2) * 2)
        return [Math]::Min($roundStart + 1, $expectedLast)
    }
    return [Math]::Min($leg, $expectedLast)
}

function New-MatchupSeasonReadModel {
    param(
        [Parameter(Mandatory = $true)][string]$CanonicalLeagueID,
        [Parameter(Mandatory = $true)][int]$Season,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$Standings,
        [AllowNull()][object]$DecisionFacts,
        [AllowEmptyCollection()][array]$LiveMatchupRows = @(),
        [bool]$ActiveScoreEvidenceAvailable = $true,
        [DateTimeOffset]$AsOfUtc = [DateTimeOffset]::UtcNow,
        [string]$RepoRoot = (Get-MrmRepositoryRoot),
        [switch]$HistoricalCutoff
    )

    $seasonDir = Join-Path $RepoRoot "source-data/leagues/$CanonicalLeagueID/seasons/$Season"
    $leagueFile = Join-Path $seasonDir 'league.json'
    $matchupDir = Join-Path $seasonDir 'matchups'
    if (-not (Test-Path $leagueFile) -or -not (Test-Path $matchupDir)) {
        throw "Canonical league matchup source is incomplete for $CanonicalLeagueID season $Season."
    }
    $leagueSource = Get-Content $leagueFile -Raw | ConvertFrom-Json
    $participantOrder = Get-MatchupParticipantOrderMap -Standings $Standings -Season $Season -HistoricalCutoff:$HistoricalCutoff
    $scheduleGames = @(Get-MrmCanonicalScheduleGames -RepoRoot $RepoRoot -Season $Season)
    $finalityMap = Get-MrmFinalityMap -RepoRoot $RepoRoot -Season $Season
    $lastKnownWeek = Get-MrmKnownLastWeek -LeagueSource $leagueSource
    $weekStructure = Get-MrmValue -Object $leagueSource -Names @('WeekStructure')
    $settings = Get-MrmValue -Object $leagueSource -Names @('Settings')
    $startWeek = [int](Get-MrmValue -Object $weekStructure -Names @('StartWeek'))
    if ($startWeek -le 0) { $startWeek = [int](Get-MrmValue -Object $settings -Names @('start_week')) }
    if ($startWeek -le 0) { $startWeek = 1 }
    $playoffStart = [int](Get-MrmValue -Object $weekStructure -Names @('PlayoffStartWeek'))
    if ($playoffStart -le 0) { $playoffStart = [int](Get-MrmValue -Object $settings -Names @('playoff_week_start')) }

    $decisionSeason = [string](Get-MrmValue -Object $DecisionFacts -Names @('Season'))
    $activeWeek = if ($null -ne $DecisionFacts -and $decisionSeason -eq [string]$Season) { [int](Get-MrmValue -Object $DecisionFacts -Names @('LineupWeek')) } else { 0 }
    $weeks = @()

    for ($week = $startWeek; $week -le $lastKnownWeek; $week++) {
        $weekGames = @($scheduleGames | Where-Object { [int](Get-MrmValue -Object $_ -Names @('Week')) -eq $week })
        $kickoffs = @($weekGames | ForEach-Object { ConvertTo-MrmKickoffUtc -Game $_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Sort-Object)
        $firstKickoff = if ($kickoffs.Count -gt 0) { [string]$kickoffs[0] } else { $null }
        $matchupFile = Join-Path $matchupDir "week-$week.json"
        $rows = if (Test-Path $matchupFile) { @(Get-Content $matchupFile -Raw | ConvertFrom-Json) } else { @() }
        $weekLiveRows = if ($week -eq $activeWeek) { @($LiveMatchupRows) } else { @() }
        $malformedEvidenceFound = $false
        $pairings = @(ConvertTo-MrmCanonicalPairings -Season $Season -Week $week -Rows $rows -ParticipantOrder $participantOrder -LiveRows $weekLiveRows -MalformedEvidenceFound ([ref]$malformedEvidenceFound))
        if ($week -eq $activeWeek -and -not $ActiveScoreEvidenceAvailable) {
            foreach ($pairing in $pairings) { $pairing.ScoreEvidenceUnknown = $true }
        }
        $weeklyAssignments = $null
        if ($week -ne $activeWeek -and -not [string]::IsNullOrWhiteSpace($firstKickoff)) {
            try {
                if ([DateTimeOffset]::Parse($firstKickoff) -le $AsOfUtc) {
                    $weeklyAssignments = Get-MrmWeeklyAssignmentMap -RepoRoot $RepoRoot -Season $Season -Week $week
                }
            } catch {}
        }

        $matchupViews = @()
        foreach ($pairing in $pairings) {
            $teamIDs = @($pairing.Participants | ForEach-Object { $_.TeamID })
            $completion = if ($week -eq $activeWeek -and $null -ne $DecisionFacts) {
                Resolve-MrmActiveCompletionState -TeamIDs $teamIDs -DecisionFacts $DecisionFacts
            }
            else {
                Resolve-MrmNonActiveCompletionState -Pairing $pairing -LeagueSource $leagueSource -WeekGames $weekGames -WeeklyAssignments $weeklyAssignments -FinalityMap $finalityMap -FirstKickoffUtc $firstKickoff -AsOfUtc $AsOfUtc
            }
            if ($pairing.ScoreEvidenceUnknown -and $completion -eq 'final') { $completion = 'unknown' }
            if ($completion -eq 'final' -and @($pairing.Participants | Where-Object { $null -eq $_.Points }).Count -gt 0) { $completion = 'unknown' }

            $participants = @($pairing.Participants | ForEach-Object {
                [PSCustomObject][ordered]@{
                    TeamID = $_.TeamID
                    Points = $_.Points
                    ScoreKind = [string]$_.ScoreKind
                }
            })
            $view = [ordered]@{
                FantasyMatchupID = [string]$pairing.FantasyMatchupID
                Participants = $participants
                CompletionState = $completion
                Result = $null
            }
            if ($completion -eq 'final') {
                $left = $participants[0]
                $right = $participants[1]
                if ([double]$left.Points -eq [double]$right.Points) {
                    $view.Result = [PSCustomObject][ordered]@{ Type = 'tie'; WinnerTeamID = $null }
                }
                else {
                    $winner = if ([double]$left.Points -gt [double]$right.Points) { $left.TeamID } else { $right.TeamID }
                    $view.Result = [PSCustomObject][ordered]@{ Type = 'win'; WinnerTeamID = $winner }
                }
            }
            $matchupViews += [PSCustomObject]$view
        }

        $weekCompletion = if ($matchupViews.Count -eq 0) {
            'unknown'
        }
        elseif (@($matchupViews | Where-Object { $_.CompletionState -eq 'open' }).Count -gt 0) {
            'open'
        }
        elseif ($malformedEvidenceFound -or @($matchupViews | Where-Object { $_.CompletionState -eq 'unknown' }).Count -gt 0) {
            'unknown'
        }
        else {
            'final'
        }
        $weeks += [PSCustomObject][ordered]@{
            Week = $week
            Stage = $(if ($playoffStart -gt 0 -and $week -ge $playoffStart) { 'playoffs' } else { 'regular-season' })
            FirstKickoffUtc = $firstKickoff
            CompletionState = $weekCompletion
            Matchups = @($matchupViews | Sort-Object FantasyMatchupID)
        }
    }

    $lastCompletedWeek = @($weeks | Where-Object { $_.CompletionState -eq 'final' } | Select-Object -ExpandProperty Week | Sort-Object -Descending | Select-Object -First 1)
    $lastCompleted = if ($lastCompletedWeek.Count -eq 1) { [int]$lastCompletedWeek[0] } else { $null }
    $activeOrNext = @($weeks | Where-Object {
        ($null -eq $lastCompleted -or $_.Week -gt $lastCompleted) -and $_.CompletionState -ne 'final' -and @($_.Matchups).Count -gt 0
    } | Sort-Object Week | Select-Object -First 1)

    return [PSCustomObject][ordered]@{
        SchemaVersion = 1
        Season = [string]$Season
        Weeks = $weeks
        Summary = [PSCustomObject][ordered]@{
            LastCompletedWeek = $lastCompleted
            ActiveOrNextWeek = if ($activeOrNext.Count -eq 1) { [int]$activeOrNext[0].Week } else { $null }
        }
    }
}

function Test-MatchupSeasonReadModelChanged {
    param([AllowNull()][object]$OldData, [AllowNull()][object]$NewData)
    if ($null -eq $OldData) { return $true }
    return (($OldData | ConvertTo-Json -Depth 30 -Compress) -ne ($NewData | ConvertTo-Json -Depth 30 -Compress))
}

function Ensure-MatchupHistoryReadModels {
    param(
        [Parameter(Mandatory = $true)][string]$CanonicalLeagueID,
        [Parameter(Mandatory = $true)][int]$CurrentSeason,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$Standings,
        [Parameter(Mandatory = $true)][hashtable]$Config,
        [string]$RepoRoot = (Get-MrmRepositoryRoot)
    )

    $seasonRoot = Join-Path $RepoRoot "source-data/leagues/$CanonicalLeagueID/seasons"
    if (-not (Test-Path $seasonRoot)) { throw "Canonical league season root not found at $seasonRoot." }
    $historyDir = Join-Path ([string]$Config.PastSeasonsDir) 'Matchups'
    if (-not (Test-Path $historyDir)) { New-Item -ItemType Directory -Path $historyDir -Force | Out-Null }

    $created = $false
    foreach ($dir in @(Get-ChildItem -Path $seasonRoot -Directory | Sort-Object Name)) {
        $historicalSeason = 0
        if (-not [int]::TryParse($dir.Name, [ref]$historicalSeason) -or $historicalSeason -ge $CurrentSeason) { continue }
        $leagueFile = Join-Path $dir.FullName 'league.json'
        if (-not (Test-Path $leagueFile)) { continue }
        $leagueSource = Get-Content $leagueFile -Raw | ConvertFrom-Json
        if ([string](Get-MrmValue -Object $leagueSource -Names @('Status')) -ne 'complete') { continue }

        $targetFile = Join-Path $historyDir "Matchups_$historicalSeason.json"
        if (Test-Path $targetFile) { continue }
        $model = New-MatchupSeasonReadModel -CanonicalLeagueID $CanonicalLeagueID -Season $historicalSeason -Standings $Standings -RepoRoot $RepoRoot -HistoricalCutoff
        $model | ConvertTo-Json -Depth 30 | Out-File $targetFile -Encoding UTF8
        Write-Host "Historical Matchups $historicalSeason materialized." -ForegroundColor Green
        $created = $true
    }
    return $created
}

Export-ModuleMember -Function New-MatchupSeasonReadModel, Test-MatchupSeasonReadModelChanged, Ensure-MatchupHistoryReadModels, Get-MatchupParticipantOrderMap, ConvertTo-MrmCanonicalPairings, Get-MrmEffectiveScore
