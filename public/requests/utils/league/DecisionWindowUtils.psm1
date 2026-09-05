function ConvertTo-DecisionWindowUtcString {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Value
    )

    try {
        $parsed = [DateTimeOffset]::Parse(
            [string]$Value,
            [System.Globalization.CultureInfo]::InvariantCulture,
            [System.Globalization.DateTimeStyles]::AssumeUniversal
        )
    }
    catch {
        throw "Decision Window schedule contains invalid StartsAtUtc '$Value'."
    }

    return $parsed.ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss'Z'")
}

function Get-DecisionWindowCollectionInfo {
    param(
        [AllowNull()]
        [object]$Value
    )

    if ($null -eq $Value) {
        return [PSCustomObject]@{ IsValid = $true; Items = @() }
    }

    if ($Value -is [string] -or $Value -isnot [System.Collections.IEnumerable]) {
        return [PSCustomObject]@{ IsValid = $false; Items = @() }
    }

    return [PSCustomObject]@{ IsValid = $true; Items = @($Value) }
}

function ConvertTo-DecisionWindowPlayerId {
    param(
        [AllowNull()]
        [object]$Value,
        [switch]$TreatZeroAsEmpty
    )

    if ($null -eq $Value) {
        return [PSCustomObject]@{ State = "empty"; Value = $null }
    }

    if ($Value -is [System.Collections.IEnumerable] -and $Value -isnot [string]) {
        return [PSCustomObject]@{ State = "malformed"; Value = $null }
    }

    if ($Value -isnot [string] -and $Value -isnot [ValueType]) {
        return [PSCustomObject]@{ State = "malformed"; Value = $null }
    }

    $text = ([string]$Value).Trim()
    if ([string]::IsNullOrWhiteSpace($text)) {
        return [PSCustomObject]@{ State = "empty"; Value = $null }
    }

    if ($TreatZeroAsEmpty -and $text -eq "0") {
        return [PSCustomObject]@{ State = "empty"; Value = $null }
    }

    return [PSCustomObject]@{ State = "valid"; Value = $text }
}

function New-DecisionWindowIssue {
    param(
        [Parameter(Mandatory = $true)][string]$Code,
        [Parameter(Mandatory = $true)][ValidateSet("review", "action-required", "unknown")][string]$State,
        [AllowNull()][string]$PlayerID,
        [AllowNull()][Nullable[int]]$Count
    )

    return [PSCustomObject][ordered]@{
        Code     = $Code
        State    = $State
        PlayerID = $PlayerID
        Count    = $Count
    }
}

function Get-DecisionWindowEvaluationState {
    param(
        [AllowEmptyCollection()]
        [array]$Issues
    )

    if (@($Issues | Where-Object { $_.State -eq "unknown" }).Count -gt 0) {
        return "unknown"
    }
    if (@($Issues | Where-Object { $_.State -eq "action-required" }).Count -gt 0) {
        return "action-required"
    }
    if (@($Issues | Where-Object { $_.State -eq "review" }).Count -gt 0) {
        return "review"
    }

    return "ready"
}

function Get-DecisionWindowFacts {
    param(
        [Parameter(Mandatory = $true)][string]$Season,
        [Parameter(Mandatory = $true)][int]$Week,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$ScheduleGames,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$FantasyRosters,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$PlayerTeamAssignments,
        [Parameter(Mandatory = $true)][ValidateRange(0, 100)][int]$ExpectedStarterCount
    )

    if ([string]::IsNullOrWhiteSpace($Season)) {
        throw "Decision Window derivation requires Season."
    }
    if ($Week -lt 0) {
        throw "Decision Window derivation requires a non-negative Week."
    }

    $normalizedGames = @()
    $gameIds = @{}
    $knownTeamIds = @{}

    foreach ($game in @($ScheduleGames)) {
        if ($null -eq $game) {
            throw "Decision Window schedule contains a null game."
        }

        $gameId = ([string]$game.GameID).Trim()
        $homeTeamId = ([string]$game.HomeTeamID).Trim()
        $awayTeamId = ([string]$game.AwayTeamID).Trim()
        if ([string]::IsNullOrWhiteSpace($gameId)) {
            throw "Decision Window schedule contains a game without GameID."
        }
        if ([string]::IsNullOrWhiteSpace($homeTeamId) -or [string]::IsNullOrWhiteSpace($awayTeamId)) {
            throw "Decision Window game '$gameId' is missing a stable home/away team identity."
        }
        if ($gameIds.ContainsKey($gameId)) {
            throw "Decision Window schedule contains duplicate GameID '$gameId'."
        }

        if (-not ($game.PSObject.Properties.Name -contains "Week") -or $null -eq $game.Week) {
            throw "Decision Window game '$gameId' is missing Week."
        }
        $gameWeek = 0
        try { $gameWeek = [int]$game.Week } catch { throw "Decision Window game '$gameId' has invalid Week '$($game.Week)'." }
        $startsAtUtc = ConvertTo-DecisionWindowUtcString -Value $game.StartsAtUtc

        $normalizedGames += [PSCustomObject][ordered]@{
            GameID       = $gameId
            Week         = $gameWeek
            StartsAtUtc  = $startsAtUtc
            AwayTeamID   = $awayTeamId
            AwayTeamAbbr = if ([string]::IsNullOrWhiteSpace([string]$game.AwayTeamAbbr)) { $null } else { ([string]$game.AwayTeamAbbr).Trim() }
            HomeTeamID   = $homeTeamId
            HomeTeamAbbr = if ([string]::IsNullOrWhiteSpace([string]$game.HomeTeamAbbr)) { $null } else { ([string]$game.HomeTeamAbbr).Trim() }
        }

        $gameIds[$gameId] = $true
        $knownTeamIds[$homeTeamId] = $true
        $knownTeamIds[$awayTeamId] = $true
    }

    $weekGames = @($normalizedGames | Where-Object { $_.Week -eq $Week } | Sort-Object StartsAtUtc, GameID)
    $weekGamesByTeam = @{}
    foreach ($game in $weekGames) {
        foreach ($teamId in @($game.HomeTeamID, $game.AwayTeamID)) {
            if (-not $weekGamesByTeam.ContainsKey($teamId)) {
                $weekGamesByTeam[$teamId] = @()
            }
            $weekGamesByTeam[$teamId] += $game
        }
    }

    $decisionWindows = @()
    $windowById = @{}
    foreach ($group in @($weekGames | Group-Object StartsAtUtc | Sort-Object Name)) {
        $games = @($group.Group | Sort-Object GameID | ForEach-Object {
            [PSCustomObject][ordered]@{
                GameID       = $_.GameID
                Week         = $_.Week
                AwayTeamID   = $_.AwayTeamID
                AwayTeamAbbr = $_.AwayTeamAbbr
                HomeTeamID   = $_.HomeTeamID
                HomeTeamAbbr = $_.HomeTeamAbbr
            }
        })
        $participatingTeamIds = @(
            $group.Group |
                ForEach-Object { @($_.AwayTeamID, $_.HomeTeamID) } |
                Sort-Object -Unique
        )

        $window = [PSCustomObject][ordered]@{
            DecisionWindowID        = [string]$group.Name
            Week                    = $Week
            StartsAtUtc             = [string]$group.Name
            Games                   = $games
            ParticipatingNFLTeamIDs = $participatingTeamIds
            FantasyContextState     = "available"
            AffectedFantasyTeams    = @()
        }
        $decisionWindows += $window
        $windowById[$window.DecisionWindowID] = $window
    }

    $assignmentByPlayer = @{}
    $ambiguousAssignments = @{}
    foreach ($assignment in @($PlayerTeamAssignments)) {
        if ($null -eq $assignment) {
            throw "Decision Window player-team assignments contain a null record."
        }

        $playerInfo = ConvertTo-DecisionWindowPlayerId -Value $assignment.PlayerID
        if ($playerInfo.State -ne "valid") {
            throw "Decision Window player-team assignment is missing a valid PlayerID."
        }

        $playerId = $playerInfo.Value
        if (-not ($assignment.PSObject.Properties.Name -contains "NFLTeamID")) {
            throw "Decision Window player-team assignment for '$playerId' is missing NFLTeamID."
        }
        $nflTeamId = if ([string]::IsNullOrWhiteSpace([string]$assignment.NFLTeamID)) { $null } else { ([string]$assignment.NFLTeamID).Trim() }
        if ($assignmentByPlayer.ContainsKey($playerId) -or $ambiguousAssignments.ContainsKey($playerId)) {
            $assignmentByPlayer.Remove($playerId)
            $ambiguousAssignments[$playerId] = $true
            continue
        }

        $assignmentByPlayer[$playerId] = $nflTeamId
    }

    $teamIds = @{}
    $rosterOwnerByPlayer = @{}
    $playerLockFacts = @()
    $teamLineupEvaluations = @()
    $affectedByWindowAndTeam = @{}

    foreach ($roster in @($FantasyRosters)) {
        if ($null -eq $roster) {
            throw "Decision Window fantasy rosters contain a null record."
        }

        $fantasyTeamKey = ([string]$roster.FantasyTeamID).Trim()
        if ([string]::IsNullOrWhiteSpace($fantasyTeamKey)) {
            throw "Decision Window fantasy roster is missing FantasyTeamID."
        }
        if ($teamIds.ContainsKey($fantasyTeamKey)) {
            throw "Decision Window fantasy rosters contain duplicate FantasyTeamID '$fantasyTeamKey'."
        }
        $teamIds[$fantasyTeamKey] = $true

        $issues = @()
        $rosterProperties = @($roster.PSObject.Properties.Name)
        $rosterInfo = if ($rosterProperties -contains "PlayerIDs") {
            Get-DecisionWindowCollectionInfo -Value $roster.PlayerIDs
        } else {
            [PSCustomObject]@{ IsValid = $false; Items = @() }
        }
        $starterInfo = if ($rosterProperties -contains "StarterIDs") {
            Get-DecisionWindowCollectionInfo -Value $roster.StarterIDs
        } else {
            [PSCustomObject]@{ IsValid = $false; Items = @() }
        }
        if (-not $rosterInfo.IsValid) {
            $issues += New-DecisionWindowIssue -Code "MALFORMED_ROSTER_STRUCTURE" -State "unknown"
        }
        if (-not $starterInfo.IsValid) {
            $issues += New-DecisionWindowIssue -Code "MALFORMED_STARTER_STRUCTURE" -State "unknown"
        }

        $validRosterIds = @()
        $rosterSeen = @{}
        foreach ($rawPlayerId in @($rosterInfo.Items)) {
            $playerInfo = ConvertTo-DecisionWindowPlayerId -Value $rawPlayerId
            if ($playerInfo.State -ne "valid") {
                $issues += New-DecisionWindowIssue -Code "MALFORMED_ROSTER_PLAYER" -State "unknown"
                continue
            }

            $playerId = $playerInfo.Value
            if ($rosterSeen.ContainsKey($playerId)) {
                $issues += New-DecisionWindowIssue -Code "DUPLICATE_ROSTER_PLAYER" -State "unknown" -PlayerID $playerId
                continue
            }
            $rosterSeen[$playerId] = $true
            $validRosterIds += $playerId

            if ($rosterOwnerByPlayer.ContainsKey($playerId) -and $rosterOwnerByPlayer[$playerId] -ne $fantasyTeamKey) {
                throw "Decision Window roster evidence assigns PlayerID '$playerId' to multiple fantasy teams."
            }
            $rosterOwnerByPlayer[$playerId] = $fantasyTeamKey
        }

        $validStarterIds = @()
        $starterSeen = @{}
        foreach ($rawStarterId in @($starterInfo.Items)) {
            $playerInfo = ConvertTo-DecisionWindowPlayerId -Value $rawStarterId -TreatZeroAsEmpty
            if ($playerInfo.State -eq "empty") {
                continue
            }
            if ($playerInfo.State -ne "valid") {
                $issues += New-DecisionWindowIssue -Code "MALFORMED_STARTER_PLAYER" -State "unknown"
                continue
            }

            $playerId = $playerInfo.Value
            if ($starterSeen.ContainsKey($playerId)) {
                $issues += New-DecisionWindowIssue -Code "DUPLICATE_STARTER" -State "unknown" -PlayerID $playerId
                continue
            }
            $starterSeen[$playerId] = $true
            $validStarterIds += $playerId

            if (-not $rosterSeen.ContainsKey($playerId)) {
                $issues += New-DecisionWindowIssue -Code "STARTER_NOT_IN_ROSTER" -State "unknown" -PlayerID $playerId
            }
        }

        $starterCount = @($validStarterIds).Count
        if ($starterCount -lt $ExpectedStarterCount) {
            $openSlots = $ExpectedStarterCount - $starterCount
            $issues += New-DecisionWindowIssue -Code "OPEN_STARTER_SLOT" -State "action-required" -Count $openSlots
        }
        elseif ($starterCount -gt $ExpectedStarterCount) {
            $issues += New-DecisionWindowIssue -Code "STARTER_COUNT_OVERFLOW" -State "unknown" -Count ($starterCount - $ExpectedStarterCount)
        }

        foreach ($playerId in @($validRosterIds)) {
            $isStarter = $starterSeen.ContainsKey($playerId)
            $nflTeamId = $null
            $kind = "unknown"
            $gameId = $null
            $decisionWindowId = $null
            $startsAtUtc = $null

            if ($ambiguousAssignments.ContainsKey($playerId)) {
                $kind = "unknown"
            }
            elseif (-not $assignmentByPlayer.ContainsKey($playerId)) {
                $kind = "unknown"
            }
            else {
                $nflTeamId = $assignmentByPlayer[$playerId]
                if ([string]::IsNullOrWhiteSpace([string]$nflTeamId)) {
                    $kind = "no-team"
                }
                elseif (-not $knownTeamIds.ContainsKey([string]$nflTeamId)) {
                    $kind = "unknown"
                }
                elseif (-not $weekGamesByTeam.ContainsKey([string]$nflTeamId)) {
                    $kind = "bye"
                }
                else {
                    $candidateGames = @($weekGamesByTeam[[string]$nflTeamId])
                    if ($candidateGames.Count -ne 1) {
                        $kind = "unknown"
                    }
                    else {
                        $kind = "scheduled"
                        $gameId = [string]$candidateGames[0].GameID
                        $startsAtUtc = [string]$candidateGames[0].StartsAtUtc
                        $decisionWindowId = $startsAtUtc
                    }
                }
            }

            $playerLockFacts += [PSCustomObject][ordered]@{
                FantasyTeamID    = $roster.FantasyTeamID
                PlayerID         = $playerId
                NFLTeamID        = $nflTeamId
                Kind             = $kind
                GameID           = $gameId
                DecisionWindowID = $decisionWindowId
                StartsAtUtc      = $startsAtUtc
                IsStarter        = $isStarter
            }

            if ($kind -eq "unknown") {
                $issues += New-DecisionWindowIssue -Code $(if ($isStarter) { "STARTER_LOCK_UNKNOWN" } else { "UNRESOLVED_ROSTER_PLAYER" }) -State "unknown" -PlayerID $playerId
            }
            elseif ($isStarter -and $kind -eq "bye") {
                $issues += New-DecisionWindowIssue -Code "STARTER_ON_BYE" -State "action-required" -PlayerID $playerId
            }
            elseif ($isStarter -and $kind -eq "no-team") {
                $issues += New-DecisionWindowIssue -Code "STARTER_WITHOUT_NFL_TEAM" -State "review" -PlayerID $playerId
            }

            if ($kind -eq "scheduled") {
                $affectedKey = "$decisionWindowId|$fantasyTeamKey"
                if (-not $affectedByWindowAndTeam.ContainsKey($affectedKey)) {
                    $affectedByWindowAndTeam[$affectedKey] = [PSCustomObject]@{
                        WindowID      = $decisionWindowId
                        FantasyTeamID = $roster.FantasyTeamID
                        Players       = @()
                    }
                }
                $affectedByWindowAndTeam[$affectedKey].Players += [PSCustomObject][ordered]@{
                    PlayerID  = $playerId
                    NFLTeamID = $nflTeamId
                    GameID    = $gameId
                    IsStarter = $isStarter
                }
            }
        }

        $uniqueIssues = @(
            $issues |
                Sort-Object Code, PlayerID, Count -Unique
        )
        $teamLineupEvaluations += [PSCustomObject][ordered]@{
            FantasyTeamID        = $roster.FantasyTeamID
            State                = Get-DecisionWindowEvaluationState -Issues $uniqueIssues
            ExpectedStarterCount = $ExpectedStarterCount
            StarterCount         = $starterCount
            OpenStarterSlots     = [Math]::Max(0, $ExpectedStarterCount - $starterCount)
            Issues               = $uniqueIssues
        }
    }

    foreach ($affected in @($affectedByWindowAndTeam.Values | Sort-Object WindowID, { [string]$_.FantasyTeamID })) {
        if (-not $windowById.ContainsKey($affected.WindowID)) {
            throw "Decision Window association references missing window '$($affected.WindowID)'."
        }

        $affectedPlayers = @($affected.Players | Sort-Object PlayerID)
        $windowById[$affected.WindowID].AffectedFantasyTeams += [PSCustomObject][ordered]@{
            FantasyTeamID               = $affected.FantasyTeamID
            AffectedRosteredPlayerCount = $affectedPlayers.Count
            AffectedStarterCount        = @($affectedPlayers | Where-Object { $_.IsStarter }).Count
            Players                     = $affectedPlayers
        }
    }

    foreach ($window in $decisionWindows) {
        $window.AffectedFantasyTeams = @($window.AffectedFantasyTeams | Sort-Object { [string]$_.FantasyTeamID })
    }

    return [PSCustomObject][ordered]@{
        Season                = $Season
        Week                  = $Week
        DecisionWindows       = @($decisionWindows | Sort-Object StartsAtUtc)
        PlayerLockFacts       = @($playerLockFacts | Sort-Object { [string]$_.FantasyTeamID }, PlayerID)
        TeamLineupEvaluations = @($teamLineupEvaluations | Sort-Object { [string]$_.FantasyTeamID })
    }
}

function New-DecisionWindowsReadModel {
    param(
        [Parameter(Mandatory = $true)][object]$LeagueID,
        [Parameter(Mandatory = $true)][string]$Season,
        [Parameter(Mandatory = $true)][int]$LineupWeek,
        [Parameter(Mandatory = $true)][int]$LastLineupWeek,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$ScheduleGames,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$FantasyRosters,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$PlayerTeamAssignments,
        [Parameter(Mandatory = $true)][ValidateRange(0, 100)][int]$ExpectedStarterCount
    )

    if ($LastLineupWeek -lt 1) {
        throw "LastLineupWeek must be positive."
    }

    if ($LineupWeek -lt 1 -or $LineupWeek -gt $LastLineupWeek) {
        $pendingEvaluations = @($FantasyRosters | Sort-Object { [string]$_.FantasyTeamID } | ForEach-Object {
            [PSCustomObject][ordered]@{
                FantasyTeamID        = $_.FantasyTeamID
                State                = "pending"
                ExpectedStarterCount = $ExpectedStarterCount
                StarterCount         = $null
                OpenStarterSlots     = $null
                Issues               = @()
            }
        })

        $pendingLookahead = $null
        if ($LineupWeek -lt 1) {
            $next = Get-DecisionWindowFacts `
                -Season $Season `
                -Week 1 `
                -ScheduleGames $ScheduleGames `
                -FantasyRosters @() `
                -PlayerTeamAssignments @() `
                -ExpectedStarterCount 0
            if (@($next.DecisionWindows).Count -gt 0) {
                $firstWindow = $next.DecisionWindows[0]
                $pendingLookahead = [PSCustomObject][ordered]@{
                    DecisionWindowID        = $firstWindow.DecisionWindowID
                    Week                    = $firstWindow.Week
                    StartsAtUtc             = $firstWindow.StartsAtUtc
                    Games                   = $firstWindow.Games
                    ParticipatingNFLTeamIDs = $firstWindow.ParticipatingNFLTeamIDs
                    FantasyContextState     = "pending"
                    AffectedFantasyTeams    = @()
                }
            }
        }

        return [PSCustomObject][ordered]@{
            SchemaVersion           = 1
            LeagueID                = $LeagueID
            Season                  = $Season
            LineupWeek              = $LineupWeek
            LastLineupWeek          = $LastLineupWeek
            DecisionWindows         = @()
            LookaheadDecisionWindow = $pendingLookahead
            PlayerLockFacts         = @()
            TeamLineupEvaluations   = $pendingEvaluations
        }
    }

    $current = Get-DecisionWindowFacts `
        -Season $Season `
        -Week $LineupWeek `
        -ScheduleGames $ScheduleGames `
        -FantasyRosters $FantasyRosters `
        -PlayerTeamAssignments $PlayerTeamAssignments `
        -ExpectedStarterCount $ExpectedStarterCount

    $lookahead = $null
    if ($LineupWeek -lt $LastLineupWeek) {
        $nextWeek = $LineupWeek + 1
        $next = Get-DecisionWindowFacts `
            -Season $Season `
            -Week $nextWeek `
            -ScheduleGames $ScheduleGames `
            -FantasyRosters @() `
            -PlayerTeamAssignments @() `
            -ExpectedStarterCount 0

        if (@($next.DecisionWindows).Count -gt 0) {
            $firstWindow = $next.DecisionWindows[0]
            $lookahead = [PSCustomObject][ordered]@{
                DecisionWindowID        = $firstWindow.DecisionWindowID
                Week                    = $firstWindow.Week
                StartsAtUtc             = $firstWindow.StartsAtUtc
                Games                   = $firstWindow.Games
                ParticipatingNFLTeamIDs = $firstWindow.ParticipatingNFLTeamIDs
                FantasyContextState     = "pending"
                AffectedFantasyTeams    = @()
            }
        }
    }

    return [PSCustomObject][ordered]@{
        SchemaVersion           = 1
        LeagueID                = $LeagueID
        Season                  = $Season
        LineupWeek              = $LineupWeek
        LastLineupWeek          = $LastLineupWeek
        DecisionWindows         = $current.DecisionWindows
        LookaheadDecisionWindow = $lookahead
        PlayerLockFacts         = $current.PlayerLockFacts
        TeamLineupEvaluations   = $current.TeamLineupEvaluations
    }
}

function Test-DecisionWindowReadModelChanged {
    param(
        [AllowNull()][object]$OldData,
        [Parameter(Mandatory = $true)][object]$NewData
    )

    if ($null -eq $OldData) {
        return $true
    }

    $oldJson = $OldData | ConvertTo-Json -Depth 10 -Compress
    $newJson = $NewData | ConvertTo-Json -Depth 10 -Compress
    return $oldJson -ne $newJson
}

function New-CurrentLeagueDecisionWindowsReadModel {
    param(
        [Parameter(Mandatory = $true)][object]$League,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$Teams,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$Players,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$Schedule,
        [Parameter(Mandatory = $true)][int]$LastLineupWeek
    )

    if ($null -eq $League.settings -or $null -eq $League.settings.leg) {
        throw "Current Decision Window adapter requires fantasy-platform settings.leg."
    }
    if ($null -eq $League.roster_positions) {
        throw "Current Decision Window adapter requires league roster_positions."
    }

    $lineupWeek = [int]$League.settings.leg
    $expectedStarterCount = @(
        @($League.roster_positions) | Where-Object {
            -not [string]::IsNullOrWhiteSpace([string]$_) -and ([string]$_).Trim().ToUpperInvariant() -ne "BN"
        }
    ).Count
    if ($expectedStarterCount -le 0) {
        throw "Current Decision Window adapter could not derive a positive expected starter count from roster_positions."
    }

    $season = [string]$League.season
    if ([string]::IsNullOrWhiteSpace($season)) {
        throw "Current Decision Window adapter requires league season."
    }

    $requiredScheduleWeeks = @{}
    if ($lineupWeek -lt 1) {
        $requiredScheduleWeeks[1] = $true
    }
    elseif ($lineupWeek -le $LastLineupWeek) {
        $requiredScheduleWeeks[$lineupWeek] = $true
        if ($lineupWeek -lt $LastLineupWeek) {
            $requiredScheduleWeeks[$lineupWeek + 1] = $true
        }
    }

    $scheduleGames = @()
    foreach ($game in @($Schedule)) {
        if ($null -eq $game) { continue }
        if (-not [string]::IsNullOrWhiteSpace([string]$game.season) -and [string]$game.season -ne $season) {
            continue
        }
        if ([string]$game.gameWeek -notmatch '^Week\s+(\d+)$') {
            continue
        }

        $gameWeek = [int]$matches[1]
        if ([string]::IsNullOrWhiteSpace([string]$game.gameID)) {
            throw "Current Decision Window schedule adapter found a regular-season game without gameID."
        }
        if ([string]::IsNullOrWhiteSpace([string]$game.teamIDHome) -or [string]::IsNullOrWhiteSpace([string]$game.teamIDAway)) {
            throw "Current Decision Window schedule adapter found game '$($game.gameID)' without stable team IDs."
        }

        $isRequiredScheduleWeek = $requiredScheduleWeeks.ContainsKey($gameWeek)
        if ([string]::IsNullOrWhiteSpace([string]$game.gameTime_epoch)) {
            if ($isRequiredScheduleWeek) {
                throw "Current Decision Window schedule adapter found game '$($game.gameID)' without gameTime_epoch."
            }
            continue
        }

        try {
            $epoch = [double]::Parse([string]$game.gameTime_epoch, [System.Globalization.CultureInfo]::InvariantCulture)
            $startsAtUtc = [DateTimeOffset]::FromUnixTimeSeconds([int64][Math]::Floor($epoch)).ToString("yyyy-MM-ddTHH:mm:ss'Z'")
        }
        catch {
            if ($isRequiredScheduleWeek) {
                throw "Current Decision Window schedule adapter could not parse gameTime_epoch for '$($game.gameID)'."
            }
            continue
        }

        $scheduleGames += [PSCustomObject][ordered]@{
            GameID       = [string]$game.gameID
            Week         = $gameWeek
            StartsAtUtc  = $startsAtUtc
            AwayTeamID   = [string]$game.teamIDAway
            AwayTeamAbbr = if ([string]::IsNullOrWhiteSpace([string]$game.away)) { $null } else { [string]$game.away }
            HomeTeamID   = [string]$game.teamIDHome
            HomeTeamAbbr = if ([string]::IsNullOrWhiteSpace([string]$game.home)) { $null } else { [string]$game.home }
        }
    }

    $fantasyRosters = @($Teams | ForEach-Object {
        [PSCustomObject][ordered]@{
            FantasyTeamID = $_.TeamID
            PlayerIDs     = @($_.Roster)
            StarterIDs    = @($_.Starter)
        }
    })

    $playerTeamAssignments = @($Players | ForEach-Object {
        [PSCustomObject][ordered]@{
            PlayerID  = $_.ID
            NFLTeamID = $_.TeamID
        }
    })

    return New-DecisionWindowsReadModel `
        -LeagueID $League.league_id `
        -Season $season `
        -LineupWeek $lineupWeek `
        -LastLineupWeek $LastLineupWeek `
        -ScheduleGames $scheduleGames `
        -FantasyRosters $fantasyRosters `
        -PlayerTeamAssignments $playerTeamAssignments `
        -ExpectedStarterCount $expectedStarterCount
}
