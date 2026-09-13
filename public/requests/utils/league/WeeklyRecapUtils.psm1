try {
    Import-Module "$PSScriptRoot\FantasyGameContextUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\MatchupReadModelUtils.psm1" -ErrorAction Stop -Force
}
catch {
    Write-Error "Failed to load WeeklyRecap dependencies: $_"
    throw
}

function Get-WrValue {
    param([AllowNull()][object]$Object, [Parameter(Mandatory = $true)][string[]]$Names)
    if ($null -eq $Object) { return $null }
    foreach ($name in $Names) {
        if ($Object -is [System.Collections.IDictionary] -and $Object.Contains($name)) { return $Object[$name] }
        if ($Object.PSObject.Properties.Name -contains $name) { return $Object.$name }
    }
    return $null
}

function Get-WrCollection {
    param([AllowNull()][object]$Value)
    if ($null -eq $Value) { return @() }
    if ($Value -is [string]) { return @($Value) }
    if ($Value -is [System.Collections.IEnumerable]) { return @($Value) }
    return @($Value)
}

function Get-WrRepositoryRoot {
    return [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\..\..\.."))
}

function Get-WrScheduleWeekNumber {
    param([AllowNull()][object]$Game)
    $weekValue = Get-WrValue -Object $Game -Names @('Week','gameWeek')
    if ($null -eq $weekValue) { return 0 }
    $text = ([string]$weekValue).Trim()
    if ($text -match '^(?:Week\s+)?(\d+)$') { return [int]$Matches[1] }
    return 0
}

function ConvertTo-WrCanonicalTeamAbbr {
    param([AllowNull()][object]$TeamAbbr)
    $value = ([string]$TeamAbbr).Trim().ToUpperInvariant()
    switch ($value) {
        'LAR' { return 'LA' }
        'WSH' { return 'WAS' }
        default { return $value }
    }
}

function Get-WrAwayAbbr {
    param([AllowNull()][object]$Game)
    return ConvertTo-WrCanonicalTeamAbbr -TeamAbbr (Get-WrValue -Object $Game -Names @('away','teamAbvAway','AwayTeamAbbr','AwayTeam'))
}

function Get-WrHomeAbbr {
    param([AllowNull()][object]$Game)
    return ConvertTo-WrCanonicalTeamAbbr -TeamAbbr (Get-WrValue -Object $Game -Names @('home','teamAbvHome','HomeTeamAbbr','HomeTeam'))
}

function Get-WrKickoffUtc {
    param([Parameter(Mandatory = $true)][object]$Game)
    $epoch = Get-WrValue -Object $Game -Names @('gameTime_epoch','GameTimeEpoch')
    if ($null -ne $epoch -and -not [string]::IsNullOrWhiteSpace([string]$epoch)) {
        try { return [DateTimeOffset]::FromUnixTimeSeconds([int64][double]$epoch).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss'Z'") } catch {}
    }
    $utc = Get-WrValue -Object $Game -Names @('KickoffUtc','StartsAtUtc','GameTimeUtc')
    if ($null -ne $utc -and -not [string]::IsNullOrWhiteSpace([string]$utc)) {
        try { return ([DateTimeOffset]::Parse([string]$utc)).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss'Z'") } catch {}
    }
    throw "WeeklyRecaps cannot resolve kickoff for game '$([string](Get-WrValue -Object $Game -Names @('gameID','GameID')))'."
}

function Get-WrCanonicalScheduleGames {
    param([Parameter(Mandatory = $true)][string]$RepoRoot, [Parameter(Mandatory = $true)][int]$Season)
    $path = Join-Path $RepoRoot "source-data/nfl/schedules/$Season.json"
    if (-not (Test-Path $path)) { throw "WeeklyRecaps canonical NFL schedule is missing for season $Season at $path." }
    $document = Get-Content $path -Raw | ConvertFrom-Json
    return @(Get-WrCollection (Get-WrValue -Object $document -Names @('Games')))
}

function Get-WrWeeklyRosterRows {
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [Parameter(Mandatory = $true)][int]$Season,
        [Parameter(Mandatory = $true)][int]$Week
    )
    $path = Join-Path $RepoRoot ("source-data/nfl/weekly-rosters/{0}/{1:D2}.json" -f $Season, $Week)
    if (-not (Test-Path $path)) { throw "WeeklyRecaps canonical weekly-roster evidence is missing for season $Season Week $Week at $path." }
    $document = Get-Content $path -Raw | ConvertFrom-Json
    return @(Get-WrCollection (Get-WrValue -Object $document -Names @('Records','Rows','Players','Data')))
}

function New-WrRosterIdentityMap {
    param([Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$Rows)
    $byCanonical = @{}
    $byPlayer = @{}
    foreach ($row in @($Rows)) {
        $canonicalID = ([string](Get-WrValue -Object $row -Names @('CanonicalPlayerID'))).Trim()
        $teamRef = Get-WrValue -Object $row -Names @('Team')
        $teamAbbr = ([string](Get-WrValue -Object $row -Names @('TeamAbbr','TeamAbv'))).Trim().ToUpperInvariant()
        if ([string]::IsNullOrWhiteSpace($teamAbbr) -and $teamRef -is [string]) { $teamAbbr = $teamRef.Trim().ToUpperInvariant() }
        $position = ([string](Get-WrValue -Object $row -Names @('Position'))).Trim().ToUpperInvariant()
        $sourceIDs = Get-WrValue -Object $row -Names @('SourceIDs')
        $playerID = ([string](Get-WrValue -Object $sourceIDs -Names @('Sleeper'))).Trim()
        $identity = [PSCustomObject][ordered]@{
            CanonicalPlayerID = $canonicalID
            PlayerID = $playerID
            TeamAbbr = $teamAbbr
            Position = $position
        }
        if (-not [string]::IsNullOrWhiteSpace($canonicalID)) { $byCanonical[$canonicalID] = $identity }
        if (-not [string]::IsNullOrWhiteSpace($playerID)) { $byPlayer[$playerID] = $identity }
    }
    return [PSCustomObject]@{ ByCanonical = $byCanonical; ByPlayer = $byPlayer }
}

function Get-WrNFLTeamID {
    param(
        [Parameter(Mandatory = $true)][string]$TeamAbbr,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$IdentitySchedule
    )
    $teamKey = ConvertTo-WrCanonicalTeamAbbr -TeamAbbr $TeamAbbr
    $ids = @()
    foreach ($game in @($IdentitySchedule)) {
        $away = Get-WrAwayAbbr -Game $game
        $home = Get-WrHomeAbbr -Game $game
        if ($away -eq $teamKey) { $ids += [string](Get-WrValue -Object $game -Names @('teamIDAway','AwayTeamID')) }
        if ($home -eq $teamKey) { $ids += [string](Get-WrValue -Object $game -Names @('teamIDHome','HomeTeamID')) }
    }
    $ids = @($ids | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Sort-Object -Unique)
    if ($ids.Count -ne 1) { throw "WeeklyRecaps cannot resolve one stable NFLTeamID for '$TeamAbbr'." }
    return [string]$ids[0]
}

function Get-WrWeekGameForTeam {
    param(
        [Parameter(Mandatory = $true)][string]$TeamAbbr,
        [Parameter(Mandatory = $true)][int]$Week,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$IdentitySchedule
    )
    $teamKey = ConvertTo-WrCanonicalTeamAbbr -TeamAbbr $TeamAbbr
    $games = @($IdentitySchedule | Where-Object {
        (Get-WrScheduleWeekNumber -Game $_) -eq $Week -and
        ((Get-WrAwayAbbr -Game $_) -eq $teamKey -or (Get-WrHomeAbbr -Game $_) -eq $teamKey)
    })
    if ($games.Count -gt 1) { throw "WeeklyRecaps found multiple NFL games for '$TeamAbbr' in Week $Week." }
    return $(if ($games.Count -eq 1) { $games[0] } else { $null })
}

function Get-WrCanonicalGame {
    param(
        [Parameter(Mandatory = $true)][object]$IdentityGame,
        [Parameter(Mandatory = $true)][int]$Week,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$CanonicalSchedule
    )
    $away = Get-WrAwayAbbr -Game $IdentityGame
    $home = Get-WrHomeAbbr -Game $IdentityGame
    $games = @($CanonicalSchedule | Where-Object {
        [int](Get-WrValue -Object $_ -Names @('Week')) -eq $Week -and
        (Get-WrAwayAbbr -Game $_) -eq $away -and
        (Get-WrHomeAbbr -Game $_) -eq $home
    })
    if ($games.Count -ne 1) { throw "WeeklyRecaps cannot match app game '$away@$home' Week $Week to exactly one canonical NFL schedule row." }
    return $games[0]
}

function Get-WrTeamOutputValueMap {
    param([Parameter(Mandatory = $true)][object]$MatchupsWeek)
    $map = @{}
    foreach ($matchup in @(Get-WrCollection (Get-WrValue -Object $MatchupsWeek -Names @('Matchups')))) {
        foreach ($participant in @(Get-WrCollection (Get-WrValue -Object $matchup -Names @('Participants')))) {
            $value = Get-WrValue -Object $participant -Names @('TeamID')
            if ($null -ne $value) { $map[[string]$value] = $value }
        }
    }
    return $map
}

function New-WeeklyRecapWeekReadModel {
    param(
        [Parameter(Mandatory = $true)][int]$Week,
        [Parameter(Mandatory = $true)][object]$MatchupsWeek,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$FantasyMatchups,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$IdentitySchedule,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$CanonicalSchedule,
        [Parameter(Mandatory = $true)][object]$RosterIdentityMap,
        [Parameter(Mandatory = $true)][hashtable]$TeamOrder
    )

    if ([string](Get-WrValue -Object $MatchupsWeek -Names @('CompletionState')) -ne 'final') {
        throw "WeeklyRecaps Week $Week was passed to recap derivation without Matchups CompletionState=final."
    }

    $matchupIDs = @{}
    foreach ($matchup in @(Get-WrCollection (Get-WrValue -Object $MatchupsWeek -Names @('Matchups')))) {
        $matchupIDs[[string](Get-WrValue -Object $matchup -Names @('FantasyMatchupID'))] = $true
    }
    $teamOutputValues = Get-WrTeamOutputValueMap -MatchupsWeek $MatchupsWeek
    $starters = @()

    foreach ($matchup in @($FantasyMatchups)) {
        $fantasyMatchupID = [string](Get-WrValue -Object $matchup -Names @('FantasyMatchupID'))
        if (-not $matchupIDs.ContainsKey($fantasyMatchupID)) {
            throw "WeeklyRecaps canonical matchup '$fantasyMatchupID' is not present in final Matchups Week $Week."
        }
        foreach ($team in @(Get-WrCollection (Get-WrValue -Object $matchup -Names @('Teams')))) {
            $teamKey = [string](Get-WrValue -Object $team -Names @('FantasyTeamID'))
            if (-not $teamOutputValues.ContainsKey($teamKey)) { throw "WeeklyRecaps cannot map FantasyTeamID '$teamKey' to Matchups Week $Week." }
            if (-not $TeamOrder.ContainsKey($teamKey)) { throw "WeeklyRecaps neutral team order is missing FantasyTeamID '$teamKey'." }
            foreach ($player in @(Get-WrCollection (Get-WrValue -Object $team -Names @('Players')))) {
                if (-not [bool](Get-WrValue -Object $player -Names @('IsStarter'))) { continue }
                if (-not [bool](Get-WrValue -Object $player -Names @('HasPoints'))) {
                    throw "WeeklyRecaps final Week $Week has an actual starter without realized point evidence."
                }

                $playerID = ([string](Get-WrValue -Object $player -Names @('PlayerID'))).Trim()
                $canonicalID = ([string](Get-WrValue -Object $player -Names @('CanonicalPlayerID'))).Trim()
                $identity = $null
                if (-not [string]::IsNullOrWhiteSpace($canonicalID) -and $RosterIdentityMap.ByCanonical.ContainsKey($canonicalID)) {
                    $identity = $RosterIdentityMap.ByCanonical[$canonicalID]
                }
                elseif (-not [string]::IsNullOrWhiteSpace($playerID) -and $RosterIdentityMap.ByPlayer.ContainsKey($playerID)) {
                    $identity = $RosterIdentityMap.ByPlayer[$playerID]
                }

                $teamAbbr = $null
                $position = $null
                if ($null -ne $identity) {
                    $teamAbbr = [string]$identity.TeamAbbr
                    $position = [string]$identity.Position
                }
                elseif ($playerID.ToUpperInvariant() -match '^[A-Z]{2,3}$') {
                    $teamAbbr = $playerID.ToUpperInvariant()
                    $position = 'DEF'
                }
                else {
                    throw "WeeklyRecaps cannot resolve week-specific NFL identity for PlayerID '$playerID' in Week $Week."
                }
                if ([string]::IsNullOrWhiteSpace($teamAbbr) -or [string]::IsNullOrWhiteSpace($position)) {
                    throw "WeeklyRecaps incomplete weekly-roster identity for PlayerID '$playerID' in Week $Week."
                }

                $nflTeamID = Get-WrNFLTeamID -TeamAbbr $teamAbbr -IdentitySchedule $IdentitySchedule
                $game = Get-WrWeekGameForTeam -TeamAbbr $teamAbbr -Week $Week -IdentitySchedule $IdentitySchedule
                $starters += [PSCustomObject][ordered]@{
                    PlayerID = $playerID
                    FantasyTeamID = $teamOutputValues[$teamKey]
                    FantasyTeamKey = $teamKey
                    FantasyMatchupID = $fantasyMatchupID
                    NFLTeamID = $nflTeamID
                    NFLTeamAbbr = $teamAbbr
                    Position = $position
                    Points = [double](Get-WrValue -Object $player -Names @('Points'))
                    TeamOrder = [int]$TeamOrder[$teamKey]
                    Game = $game
                }
            }
        }
    }

    if ($starters.Count -lt 3) { throw "WeeklyRecaps final Week $Week has fewer than three actual starters with complete scoring identity." }

    $keyPlayers = @(
        $starters |
            Sort-Object `
                @{ Expression = { [double]$_.Points }; Descending = $true }, `
                @{ Expression = { [int]$_.TeamOrder }; Ascending = $true }, `
                @{ Expression = { [string]$_.PlayerID }; Ascending = $true } |
            Select-Object -First 3 |
            ForEach-Object {
                [PSCustomObject][ordered]@{
                    PlayerID = [string]$_.PlayerID
                    FantasyTeamID = $_.FantasyTeamID
                    NFLTeamID = [string]$_.NFLTeamID
                    Position = [string]$_.Position
                    Points = [math]::Round([double]$_.Points, 4)
                }
            }
    )

    $gameGroups = @{}
    foreach ($starter in $starters) {
        if ($null -eq $starter.Game) { continue }
        $gameID = [string](Get-WrValue -Object $starter.Game -Names @('gameID','GameID'))
        if ([string]::IsNullOrWhiteSpace($gameID)) { throw "WeeklyRecaps encountered a scheduled starter without GameID in Week $Week." }
        if (-not $gameGroups.ContainsKey($gameID)) {
            $gameGroups[$gameID] = [PSCustomObject]@{
                Game = $starter.Game
                StarterPoints = 0.0
                StarterCount = 0
                TeamValues = @{}
                MatchupIDs = @{}
            }
        }
        $group = $gameGroups[$gameID]
        $group.StarterPoints = [double]$group.StarterPoints + [double]$starter.Points
        $group.StarterCount = [int]$group.StarterCount + 1
        $group.TeamValues[[string]$starter.FantasyTeamID] = $starter.FantasyTeamID
        $group.MatchupIDs[[string]$starter.FantasyMatchupID] = $true
    }
    if ($gameGroups.Count -lt 2) { throw "WeeklyRecaps final Week $Week has fewer than two NFL games with actual starter production." }

    $gameCandidates = @()
    foreach ($gameID in @($gameGroups.Keys)) {
        $group = $gameGroups[$gameID]
        $identityGame = $group.Game
        $canonicalGame = Get-WrCanonicalGame -IdentityGame $identityGame -Week $Week -CanonicalSchedule $CanonicalSchedule
        $awayScore = Get-WrValue -Object $canonicalGame -Names @('AwayScore')
        $homeScore = Get-WrValue -Object $canonicalGame -Names @('HomeScore')
        if ($null -eq $awayScore -or $null -eq $homeScore) { throw "WeeklyRecaps final Week $Week game '$gameID' is missing canonical final score evidence." }

        $teamValues = @($group.TeamValues.Values)
        $teamValues = @($teamValues | Sort-Object {
            $key = [string]$_
            if ($TeamOrder.ContainsKey($key)) { [int]$TeamOrder[$key] } else { [int]::MaxValue }
        }, { [string]$_ })
        $matchupValues = @($group.MatchupIDs.Keys | Sort-Object)

        $gameCandidates += [PSCustomObject][ordered]@{
            GameID = $gameID
            KickoffUtc = Get-WrKickoffUtc -Game $identityGame
            AwayNFLTeamID = [string](Get-WrValue -Object $identityGame -Names @('teamIDAway','AwayTeamID'))
            HomeNFLTeamID = [string](Get-WrValue -Object $identityGame -Names @('teamIDHome','HomeTeamID'))
            AwayScore = [double]$awayScore
            HomeScore = [double]$homeScore
            StarterPoints = [math]::Round([double]$group.StarterPoints, 4)
            StarterCount = [int]$group.StarterCount
            FantasyTeamIDs = $teamValues
            FantasyMatchupIDs = $matchupValues
            FantasyMatchupCount = $matchupValues.Count
            FantasyTeamCount = $teamValues.Count
        }
    }

    $keyGames = @(
        $gameCandidates |
            Sort-Object `
                @{ Expression = { [double]$_.StarterPoints }; Descending = $true }, `
                @{ Expression = { [int]$_.FantasyMatchupCount }; Descending = $true }, `
                @{ Expression = { [int]$_.FantasyTeamCount }; Descending = $true }, `
                @{ Expression = { [int]$_.StarterCount }; Descending = $true }, `
                @{ Expression = { [string]$_.KickoffUtc }; Ascending = $true }, `
                @{ Expression = { [string]$_.GameID }; Ascending = $true } |
            Select-Object -First 2 |
            ForEach-Object {
                [PSCustomObject][ordered]@{
                    GameID = [string]$_.GameID
                    KickoffUtc = [string]$_.KickoffUtc
                    AwayNFLTeamID = [string]$_.AwayNFLTeamID
                    HomeNFLTeamID = [string]$_.HomeNFLTeamID
                    AwayScore = [double]$_.AwayScore
                    HomeScore = [double]$_.HomeScore
                    StarterPoints = [double]$_.StarterPoints
                    StarterCount = [int]$_.StarterCount
                    FantasyTeamIDs = @($_.FantasyTeamIDs)
                    FantasyMatchupIDs = @($_.FantasyMatchupIDs)
                }
            }
    )

    return [PSCustomObject][ordered]@{
        Week = $Week
        KeyGames = $keyGames
        KeyPlayers = $keyPlayers
    }
}

function New-WeeklyRecapSeasonReadModel {
    param(
        [Parameter(Mandatory = $true)][string]$CanonicalLeagueID,
        [Parameter(Mandatory = $true)][int]$Season,
        [Parameter(Mandatory = $true)][object]$MatchupsReadModel,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$Standings,
        [Parameter(Mandatory = $true)][string]$IdentityScheduleFile,
        [string]$RepoRoot = (Get-WrRepositoryRoot),
        [switch]$HistoricalCutoff
    )

    if ([string](Get-WrValue -Object $MatchupsReadModel -Names @('Season')) -ne [string]$Season) {
        throw "WeeklyRecaps Matchups season does not match requested season $Season."
    }
    $finalWeeks = @(Get-WrCollection (Get-WrValue -Object $MatchupsReadModel -Names @('Weeks')) | Where-Object { [string]$_.CompletionState -eq 'final' } | Sort-Object Week)
    if ($finalWeeks.Count -eq 0) {
        return [PSCustomObject][ordered]@{ SchemaVersion = 1; Season = [string]$Season; Weeks = @() }
    }
    if (-not (Test-Path $IdentityScheduleFile)) { throw "WeeklyRecaps identity schedule is missing for season $Season at $IdentityScheduleFile." }

    $identitySchedule = @(Get-Content $IdentityScheduleFile -Raw | ConvertFrom-Json)
    $canonicalSchedule = @(Get-WrCanonicalScheduleGames -RepoRoot $RepoRoot -Season $Season)
    $teamOrder = Get-MatchupParticipantOrderMap -Standings $Standings -Season $Season -HistoricalCutoff:$HistoricalCutoff
    $seasonDir = Join-Path $RepoRoot "source-data/leagues/$CanonicalLeagueID/seasons/$Season/matchups"
    $weeks = @()

    foreach ($matchupsWeek in $finalWeeks) {
        $week = [int]$matchupsWeek.Week
        $matchupFile = Join-Path $seasonDir "week-$week.json"
        if (-not (Test-Path $matchupFile)) { throw "WeeklyRecaps canonical league matchup partition is missing for season $Season Week $week." }
        $rows = @(Get-Content $matchupFile -Raw | ConvertFrom-Json)
        $facts = @(ConvertTo-FgcCanonicalMatchupFacts -Season ([string]$Season) -Week $week -MatchupRows $rows)
        $rosterRows = @(Get-WrWeeklyRosterRows -RepoRoot $RepoRoot -Season $Season -Week $week)
        $identityMap = New-WrRosterIdentityMap -Rows $rosterRows
        $weeks += New-WeeklyRecapWeekReadModel `
            -Week $week `
            -MatchupsWeek $matchupsWeek `
            -FantasyMatchups $facts `
            -IdentitySchedule $identitySchedule `
            -CanonicalSchedule $canonicalSchedule `
            -RosterIdentityMap $identityMap `
            -TeamOrder $teamOrder
    }

    return [PSCustomObject][ordered]@{
        SchemaVersion = 1
        Season = [string]$Season
        Weeks = @($weeks)
    }
}

function Test-WeeklyRecapsReadModelChanged {
    param([AllowNull()][object]$OldData, [AllowNull()][object]$NewData)
    if ($null -eq $OldData) { return $true }
    return (($OldData | ConvertTo-Json -Depth 30 -Compress) -ne ($NewData | ConvertTo-Json -Depth 30 -Compress))
}

function Update-WeeklyRecapHistoryReadModels {
    param(
        [Parameter(Mandatory = $true)][string]$CanonicalLeagueID,
        [Parameter(Mandatory = $true)][int]$CurrentSeason,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$Standings,
        [Parameter(Mandatory = $true)][hashtable]$Config,
        [string]$RepoRoot = (Get-WrRepositoryRoot)
    )

    $matchupsHistoryDir = [string]$Config.MatchupsArchiveDir
    $historyDir = [string]$Config.WeeklyRecapsArchiveDir
    if (-not (Test-Path $historyDir)) { New-Item -ItemType Directory -Path $historyDir -Force | Out-Null }
    if (-not (Test-Path $matchupsHistoryDir)) { return $false }

    $changed = $false
    foreach ($matchupsFile in @(Get-ChildItem -Path $matchupsHistoryDir -Filter 'Matchups_*.json' -File | Sort-Object Name)) {
        if ($matchupsFile.BaseName -notmatch '^Matchups_(\d+)$') { continue }
        $season = [int]$Matches[1]
        if ($season -ge $CurrentSeason) { continue }
        $matchups = Get-Content $matchupsFile.FullName -Raw | ConvertFrom-Json
        $identityScheduleFile = "$($Config.PastSeasonScheduleFileHistoricalPrefix)$season$($Config.PastSeasonScheduleFileHistoricalSuffix)"
        $model = New-WeeklyRecapSeasonReadModel `
            -CanonicalLeagueID $CanonicalLeagueID `
            -Season $season `
            -MatchupsReadModel $matchups `
            -Standings $Standings `
            -IdentityScheduleFile $identityScheduleFile `
            -RepoRoot $RepoRoot `
            -HistoricalCutoff
        $targetFile = Join-Path $historyDir "WeeklyRecaps_$season.json"
        $old = $null
        if (Test-Path $targetFile) {
            $raw = Get-Content $targetFile -Raw
            if (-not [string]::IsNullOrWhiteSpace($raw)) { $old = $raw | ConvertFrom-Json }
        }
        if (Test-WeeklyRecapsReadModelChanged -OldData $old -NewData $model) {
            $model | ConvertTo-Json -Depth 30 | Out-File $targetFile -Encoding UTF8
            Write-Host "Historical WeeklyRecaps $season materialized/rematerialized." -ForegroundColor Green
            $changed = $true
        }
    }
    return $changed
}

Export-ModuleMember -Function New-WrRosterIdentityMap, New-WeeklyRecapWeekReadModel, New-WeeklyRecapSeasonReadModel, Test-WeeklyRecapsReadModelChanged, Update-WeeklyRecapHistoryReadModels