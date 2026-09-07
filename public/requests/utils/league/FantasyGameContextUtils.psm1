# Fantasy game relevance and impact read-model helpers.
# Relevance is count-based roster/starter coverage. Impact uses league-scored
# matchup player points only; no generic NFL fantasy-point source is accepted.

try {
    Import-Module "$PSScriptRoot\..\invoke\SleeperUtils.psm1" -ErrorAction Stop -Force
}
catch {
    Write-Error "Could not load Sleeper helpers for FantasyGameContext. $_"
    throw
}

function Get-FgcPropertyValue {
    param([AllowNull()][object]$Object, [Parameter(Mandatory = $true)][string[]]$Names)

    if ($null -eq $Object) { return $null }
    foreach ($name in $Names) {
        if ($Object.PSObject.Properties.Name -contains $name) {
            return $Object.$name
        }
    }
    return $null
}

function Get-FgcCollection {
    param([AllowNull()][object]$Value)
    if ($null -eq $Value) { return @() }
    if ($Value -is [string] -or $Value -isnot [System.Collections.IEnumerable]) { return @($Value) }
    return @($Value)
}

function ConvertTo-FgcPlayerID {
    param([AllowNull()][object]$Player)

    if ($null -eq $Player) { return $null }
    if ($Player -is [string] -or $Player -is [ValueType]) {
        $text = ([string]$Player).Trim()
        return $(if ([string]::IsNullOrWhiteSpace($text) -or $text -eq '0') { $null } else { $text })
    }

    $direct = Get-FgcPropertyValue -Object $Player -Names @('PlayerID','ID','SleeperID')
    if ($null -ne $direct) {
        $text = ([string]$direct).Trim()
        if (-not [string]::IsNullOrWhiteSpace($text) -and $text -ne '0') { return $text }
    }

    foreach ($mapping in @(Get-FgcCollection (Get-FgcPropertyValue -Object $Player -Names @('ProviderMappings')))) {
        if ([string](Get-FgcPropertyValue -Object $mapping -Names @('Provider')) -ne 'Sleeper') { continue }
        $providerID = Get-FgcPropertyValue -Object $mapping -Names @('ProviderPlayerID','PlayerID')
        if ($null -ne $providerID -and -not [string]::IsNullOrWhiteSpace([string]$providerID)) {
            return ([string]$providerID).Trim()
        }
    }

    return $null
}

function ConvertTo-FgcCanonicalPlayerID {
    param([AllowNull()][object]$Player)
    if ($null -eq $Player -or $Player -is [string] -or $Player -is [ValueType]) { return $null }
    $value = Get-FgcPropertyValue -Object $Player -Names @('CanonicalPlayerID')
    if ($null -eq $value -or [string]::IsNullOrWhiteSpace([string]$value)) { return $null }
    return ([string]$value).Trim()
}

function New-FantasyGameContextMatchupID {
    param(
        [Parameter(Mandatory = $true)][string]$Season,
        [Parameter(Mandatory = $true)][int]$Week,
        [Parameter(Mandatory = $true)][string[]]$FantasyTeamIDs
    )

    $teamIDs = @($FantasyTeamIDs | ForEach-Object { ([string]$_).Trim() } | Sort-Object)
    if ($teamIDs.Count -ne 2 -or @($teamIDs | Where-Object { [string]::IsNullOrWhiteSpace($_) }).Count -gt 0) {
        throw "Fantasy matchup identity requires exactly two stable fantasy team IDs."
    }

    $material = "$Season|$Week|$($teamIDs -join '|')"
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($material)
        $hash = $sha.ComputeHash($bytes)
        $hex = -join ($hash | ForEach-Object { $_.ToString('x2') })
        return "fgm-$($hex.Substring(0, 24))"
    }
    finally {
        $sha.Dispose()
    }
}

function ConvertTo-FgcPointMapFromObject {
    param([AllowNull()][object]$Value)
    $map = @{}
    if ($null -eq $Value) { return $map }

    if ($Value -is [System.Collections.IDictionary]) {
        foreach ($key in $Value.Keys) {
            if ($null -ne $Value[$key]) { $map[[string]$key] = [double]$Value[$key] }
        }
        return $map
    }

    foreach ($property in @($Value.PSObject.Properties)) {
        if ($null -ne $property.Value) { $map[[string]$property.Name] = [double]$property.Value }
    }
    return $map
}

function ConvertTo-FgcPointMapFromRows {
    param([AllowNull()][object]$Rows)
    $map = @{}
    foreach ($row in @(Get-FgcCollection $Rows)) {
        if ($null -eq $row) { continue }
        $player = Get-FgcPropertyValue -Object $row -Names @('Player')
        $playerID = ConvertTo-FgcPlayerID -Player $player
        if ([string]::IsNullOrWhiteSpace($playerID)) { continue }
        $points = Get-FgcPropertyValue -Object $row -Names @('Points')
        if ($null -ne $points) { $map[$playerID] = [double]$points }
    }
    return $map
}

function Get-FgcCurrentMatchupLoad {
    param(
        [Parameter(Mandatory = $true)][string]$LeagueID,
        [Parameter(Mandatory = $true)][int]$Week
    )

    try {
        $rows = @(Get-SleeperMatchups -leagueID $LeagueID -week $Week)
        return [PSCustomObject][ordered]@{ Success = $true; Rows = $rows }
    }
    catch {
        Write-Warning "Could not refresh fantasy matchup facts for FantasyGameContext Week $Week. $_"
        return [PSCustomObject][ordered]@{ Success = $false; Rows = @() }
    }
}

function ConvertTo-FgcCurrentMatchupFacts {
    param(
        [Parameter(Mandatory = $true)][string]$Season,
        [Parameter(Mandatory = $true)][int]$Week,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$MatchupRows
    )

    $normalizedRows = @()
    foreach ($row in @($MatchupRows)) {
        if ($null -eq $row) { continue }
        $providerMatchupID = Get-FgcPropertyValue -Object $row -Names @('matchup_id','MatchupID')
        $fantasyTeamID = Get-FgcPropertyValue -Object $row -Names @('roster_id','FantasyTeamID','TeamID')
        if ($null -eq $providerMatchupID -or $null -eq $fantasyTeamID) { continue }
        $providerMatchupID = ([string]$providerMatchupID).Trim()
        $fantasyTeamID = ([string]$fantasyTeamID).Trim()
        if ([string]::IsNullOrWhiteSpace($providerMatchupID) -or [string]::IsNullOrWhiteSpace($fantasyTeamID)) { continue }

        $playerIDs = @(
            Get-FgcCollection (Get-FgcPropertyValue -Object $row -Names @('players','Players')) |
                ForEach-Object { ConvertTo-FgcPlayerID -Player $_ } |
                Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
                Sort-Object -Unique
        )
        $starterIDs = @(
            Get-FgcCollection (Get-FgcPropertyValue -Object $row -Names @('starters','Starters')) |
                ForEach-Object { ConvertTo-FgcPlayerID -Player $_ } |
                Where-Object { -not [string]::IsNullOrWhiteSpace($_) -and $_ -ne '0' } |
                Sort-Object -Unique
        )

        foreach ($starterID in $starterIDs) {
            if ($playerIDs -notcontains $starterID) {
                throw "Fantasy matchup Week $Week Team '$fantasyTeamID' has starter '$starterID' outside the rostered player set."
            }
        }

        $playerPoints = ConvertTo-FgcPointMapFromObject -Value (Get-FgcPropertyValue -Object $row -Names @('players_points','PlayerPoints'))
        $starterPoints = ConvertTo-FgcPointMapFromObject -Value (Get-FgcPropertyValue -Object $row -Names @('starters_points','StarterPoints'))
        if ($starterPoints.Count -eq 0) {
            foreach ($starterID in $starterIDs) {
                if ($playerPoints.ContainsKey($starterID)) { $starterPoints[$starterID] = [double]$playerPoints[$starterID] }
            }
        }

        $players = @()
        foreach ($playerID in $playerIDs) {
            $isStarter = $starterIDs -contains $playerID
            $hasPoints = $playerPoints.ContainsKey($playerID)
            $points = if ($hasPoints) { [double]$playerPoints[$playerID] } else { $null }
            if ($isStarter -and $starterPoints.ContainsKey($playerID)) {
                $hasPoints = $true
                $points = [double]$starterPoints[$playerID]
            }
            $players += [PSCustomObject][ordered]@{
                PlayerID          = $playerID
                CanonicalPlayerID = $null
                IsStarter         = $isStarter
                HasPoints         = $hasPoints
                Points            = $points
            }
        }

        $scoreValue = Get-FgcPropertyValue -Object $row -Names @('points','Points')
        $customPointsValue = Get-FgcPropertyValue -Object $row -Names @('custom_points','CustomPoints')
        $hasCustomPoints = $null -ne $customPointsValue

        $normalizedRows += [PSCustomObject][ordered]@{
            ProviderMatchupID = $providerMatchupID
            FantasyTeamID     = $fantasyTeamID
            Players           = $players
            FinalScore        = if ($null -ne $scoreValue) { [double]$scoreValue } else { $null }
            HasCustomPoints   = $hasCustomPoints
        }
    }

    return ConvertTo-FgcPairedMatchupFacts -Season $Season -Week $Week -Rows $normalizedRows
}

function Get-FgcCanonicalTeamID {
    param([AllowNull()][object]$Row)
    foreach ($mapping in @(Get-FgcCollection (Get-FgcPropertyValue -Object $Row -Names @('ProviderMappings')))) {
        if ([string](Get-FgcPropertyValue -Object $mapping -Names @('Provider')) -ne 'Sleeper') { continue }
        $id = Get-FgcPropertyValue -Object $mapping -Names @('ProviderRosterID','RosterID')
        if ($null -ne $id -and -not [string]::IsNullOrWhiteSpace([string]$id)) { return ([string]$id).Trim() }
    }
    return $null
}

function Get-FgcCanonicalProviderMatchupID {
    param([AllowNull()][object]$Row)
    foreach ($mapping in @(Get-FgcCollection (Get-FgcPropertyValue -Object $Row -Names @('ProviderMappings')))) {
        if ([string](Get-FgcPropertyValue -Object $mapping -Names @('Provider')) -ne 'Sleeper') { continue }
        $id = Get-FgcPropertyValue -Object $mapping -Names @('ProviderMatchupID','MatchupID')
        if ($null -ne $id -and -not [string]::IsNullOrWhiteSpace([string]$id)) { return ([string]$id).Trim() }
    }
    return $null
}

function ConvertTo-FgcCanonicalMatchupFacts {
    param(
        [Parameter(Mandatory = $true)][string]$Season,
        [Parameter(Mandatory = $true)][int]$Week,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$MatchupRows
    )

    $normalizedRows = @()
    foreach ($row in @($MatchupRows)) {
        $providerMatchupID = Get-FgcCanonicalProviderMatchupID -Row $row
        $fantasyTeamID = Get-FgcCanonicalTeamID -Row $row
        if ([string]::IsNullOrWhiteSpace($providerMatchupID) -or [string]::IsNullOrWhiteSpace($fantasyTeamID)) { continue }

        $playerPoints = ConvertTo-FgcPointMapFromRows -Rows (Get-FgcPropertyValue -Object $row -Names @('PlayerPoints'))
        $starterPoints = ConvertTo-FgcPointMapFromRows -Rows (Get-FgcPropertyValue -Object $row -Names @('StarterPoints'))
        $starterIDs = @(
            Get-FgcCollection (Get-FgcPropertyValue -Object $row -Names @('Starters')) |
                ForEach-Object { ConvertTo-FgcPlayerID -Player $_ } |
                Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
                Sort-Object -Unique
        )
        $players = @()
        foreach ($playerRef in @(Get-FgcCollection (Get-FgcPropertyValue -Object $row -Names @('Players')))) {
            $playerID = ConvertTo-FgcPlayerID -Player $playerRef
            if ([string]::IsNullOrWhiteSpace($playerID)) { continue }
            $isStarter = $starterIDs -contains $playerID
            $hasPoints = $playerPoints.ContainsKey($playerID)
            $points = if ($hasPoints) { [double]$playerPoints[$playerID] } else { $null }
            if ($isStarter -and $starterPoints.ContainsKey($playerID)) {
                $hasPoints = $true
                $points = [double]$starterPoints[$playerID]
            }
            $players += [PSCustomObject][ordered]@{
                PlayerID          = $playerID
                CanonicalPlayerID = ConvertTo-FgcCanonicalPlayerID -Player $playerRef
                IsStarter         = $isStarter
                HasPoints         = $hasPoints
                Points            = $points
            }
        }

        foreach ($starterID in $starterIDs) {
            if (@($players | Where-Object { $_.PlayerID -eq $starterID }).Count -eq 0) {
                throw "Historical fantasy matchup Week $Week Team '$fantasyTeamID' has starter '$starterID' outside the rostered player set."
            }
        }

        $normalizedRows += [PSCustomObject][ordered]@{
            ProviderMatchupID = $providerMatchupID
            FantasyTeamID     = $fantasyTeamID
            Players           = @($players | Sort-Object PlayerID -Unique)
            FinalScore        = [double](Get-FgcPropertyValue -Object $row -Names @('Points'))
            HasCustomPoints   = $null -ne (Get-FgcPropertyValue -Object $row -Names @('CustomPoints'))
        }
    }

    return ConvertTo-FgcPairedMatchupFacts -Season $Season -Week $Week -Rows $normalizedRows
}

function ConvertTo-FgcPairedMatchupFacts {
    param(
        [Parameter(Mandatory = $true)][string]$Season,
        [Parameter(Mandatory = $true)][int]$Week,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$Rows
    )

    $playerOwner = @{}
    $result = @()
    foreach ($group in @($Rows | Group-Object ProviderMatchupID | Sort-Object Name)) {
        $participants = @($group.Group | Sort-Object { [string]$_.FantasyTeamID })
        if ($participants.Count -ne 2) {
            Write-Warning "Excluding malformed fantasy matchup '$($group.Name)' in Week $Week because it has $($participants.Count) participants."
            continue
        }
        $teamIDs = @($participants | ForEach-Object { [string]$_.FantasyTeamID })
        $matchupID = New-FantasyGameContextMatchupID -Season $Season -Week $Week -FantasyTeamIDs $teamIDs

        foreach ($participant in $participants) {
            foreach ($player in @($participant.Players)) {
                if ($playerOwner.ContainsKey($player.PlayerID) -and $playerOwner[$player.PlayerID] -ne [string]$participant.FantasyTeamID) {
                    throw "Fantasy matchup evidence assigns PlayerID '$($player.PlayerID)' to multiple fantasy teams in Week $Week."
                }
                $playerOwner[$player.PlayerID] = [string]$participant.FantasyTeamID
            }
        }

        $result += [PSCustomObject][ordered]@{
            FantasyMatchupID = $matchupID
            TeamIDs          = @($teamIDs)
            Teams            = @($participants | ForEach-Object {
                [PSCustomObject][ordered]@{
                    FantasyTeamID   = [string]$_.FantasyTeamID
                    Players         = @($_.Players | Sort-Object PlayerID)
                    FinalScore      = $_.FinalScore
                    HasCustomPoints = [bool]$_.HasCustomPoints
                }
            })
        }
    }
    return @($result | Sort-Object FantasyMatchupID)
}

function Get-FgcOutcomeState {
    param([double]$Left, [double]$Right)
    if ($Left -gt $Right) { return 'left' }
    if ($Right -gt $Left) { return 'right' }
    return 'tie'
}

function New-FantasyGameContextReadModel {
    param(
        [Parameter(Mandatory = $true)][object]$LeagueID,
        [Parameter(Mandatory = $true)][string]$Season,
        [Parameter(Mandatory = $true)][int]$Week,
        [Parameter(Mandatory = $true)][object]$DecisionFacts,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$FantasyMatchups,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$Schedule,
        [Parameter(Mandatory = $true)][bool]$WeekIsFinal
    )

    $matchupByTeam = @{}
    $teamFactByID = @{}
    foreach ($matchup in @($FantasyMatchups)) {
        foreach ($team in @($matchup.Teams)) {
            $key = [string]$team.FantasyTeamID
            if ($matchupByTeam.ContainsKey($key)) { throw "Fantasy Team '$key' appears in multiple fantasy matchups in Week $Week." }
            $matchupByTeam[$key] = $matchup
            $teamFactByID[$key] = $team
        }
    }

    $statusByGame = @{}
    foreach ($row in @($Schedule)) {
        $gameID = [string](Get-FgcPropertyValue -Object $row -Names @('gameID','GameID'))
        if ([string]::IsNullOrWhiteSpace($gameID)) { continue }
        $statusByGame[$gameID] = [string](Get-FgcPropertyValue -Object $row -Names @('gameStatus','Status'))
    }

    $games = @()
    $gameMeta = @{}
    foreach ($window in @(Get-FgcCollection (Get-FgcPropertyValue -Object $DecisionFacts -Names @('DecisionWindows')))) {
        foreach ($game in @(Get-FgcCollection (Get-FgcPropertyValue -Object $window -Names @('Games')))) {
            $gameID = [string]$game.GameID
            $meta = [PSCustomObject][ordered]@{
                GameID           = $gameID
                DecisionWindowID = [string]$window.DecisionWindowID
                StartsAtUtc      = [string]$window.StartsAtUtc
                AwayTeamID       = [string]$game.AwayTeamID
                AwayTeamAbbr     = $game.AwayTeamAbbr
                HomeTeamID       = [string]$game.HomeTeamID
                HomeTeamAbbr     = $game.HomeTeamAbbr
                Status           = if ($statusByGame.ContainsKey($gameID)) { $statusByGame[$gameID] } else { $null }
            }
            $gameMeta[$gameID] = $meta
        }
    }

    $associationsByGame = @{}
    $nonGameAssociations = @()
    foreach ($lock in @(Get-FgcCollection (Get-FgcPropertyValue -Object $DecisionFacts -Names @('PlayerLockFacts')))) {
        $teamID = [string]$lock.FantasyTeamID
        $matchup = if ($matchupByTeam.ContainsKey($teamID)) { $matchupByTeam[$teamID] } else { $null }
        $teamFact = if ($teamFactByID.ContainsKey($teamID)) { $teamFactByID[$teamID] } else { $null }
        $playerFact = if ($null -ne $teamFact) { @($teamFact.Players | Where-Object { $_.PlayerID -eq [string]$lock.PlayerID } | Select-Object -First 1) } else { @() }

        if ([string]$lock.Kind -ne 'scheduled' -or [string]::IsNullOrWhiteSpace([string]$lock.GameID) -or $null -eq $matchup -or $playerFact.Count -ne 1) {
            $nonGameAssociations += [PSCustomObject][ordered]@{
                FantasyTeamID   = $teamID
                FantasyMatchupID = if ($null -ne $matchup) { $matchup.FantasyMatchupID } else { $null }
                PlayerID        = [string]$lock.PlayerID
                NFLTeamID       = $lock.NFLTeamID
                IsStarter       = [bool]$lock.IsStarter
                Kind            = if ($null -eq $matchup) { 'unknown' } else { [string]$lock.Kind }
                Reason          = if ($null -eq $matchup) { 'missing-fantasy-matchup' } elseif ($playerFact.Count -ne 1) { 'missing-weekly-player-scoring-fact' } else { [string]$lock.Kind }
            }
            continue
        }

        $gameID = [string]$lock.GameID
        if (-not $gameMeta.ContainsKey($gameID)) {
            $nonGameAssociations += [PSCustomObject][ordered]@{
                FantasyTeamID = $teamID; FantasyMatchupID = $matchup.FantasyMatchupID; PlayerID = [string]$lock.PlayerID
                NFLTeamID = $lock.NFLTeamID; IsStarter = [bool]$lock.IsStarter; Kind = 'unknown'; Reason = 'missing-game-fact'
            }
            continue
        }

        if (-not $associationsByGame.ContainsKey($gameID)) { $associationsByGame[$gameID] = @() }
        $scoreFact = $playerFact[0]
        $associationsByGame[$gameID] += [PSCustomObject][ordered]@{
            FantasyTeamID    = $teamID
            FantasyMatchupID = $matchup.FantasyMatchupID
            PlayerID         = [string]$lock.PlayerID
            NFLTeamID        = $lock.NFLTeamID
            IsStarter        = [bool]$lock.IsStarter
            HasPoints        = [bool]$scoreFact.HasPoints
            Points           = $scoreFact.Points
        }
    }

    $matchupGameRows = @{}
    foreach ($gameID in @($gameMeta.Keys | Sort-Object)) {
        $meta = $gameMeta[$gameID]
        $associations = @($associationsByGame[$gameID] | Sort-Object FantasyMatchupID, FantasyTeamID, PlayerID)
        $teamGroups = @($associations | Group-Object FantasyTeamID)
        $fantasyTeams = @()
        foreach ($teamGroup in $teamGroups) {
            $players = @($teamGroup.Group | Sort-Object PlayerID)
            $matchupID = [string]$players[0].FantasyMatchupID
            $fantasyTeams += [PSCustomObject][ordered]@{
                FantasyTeamID      = [string]$teamGroup.Name
                FantasyMatchupID   = $matchupID
                RosteredPlayerCount = $players.Count
                StarterCount       = @($players | Where-Object IsStarter).Count
                RosteredPoints     = [math]::Round([double](($players | Where-Object HasPoints | Measure-Object Points -Sum).Sum), 4)
                StarterPoints      = [math]::Round([double](($players | Where-Object { $_.HasPoints -and $_.IsStarter } | Measure-Object Points -Sum).Sum), 4)
                Players            = @($players | ForEach-Object {
                    [PSCustomObject][ordered]@{
                        PlayerID  = $_.PlayerID
                        IsStarter = $_.IsStarter
                        Points    = if ($_.HasPoints) { $_.Points } else { $null }
                    }
                })
            }
            $key = "$matchupID|$gameID"
            if (-not $matchupGameRows.ContainsKey($key)) { $matchupGameRows[$key] = @() }
            $matchupGameRows[$key] += $fantasyTeams[-1]
        }

        $unknownForGame = @($nonGameAssociations | Where-Object {
            -not [string]::IsNullOrWhiteSpace([string]$_.NFLTeamID) -and
            ([string]$_.NFLTeamID -eq [string]$meta.AwayTeamID -or [string]$_.NFLTeamID -eq [string]$meta.HomeTeamID)
        }).Count
        $hasPoints = @($associations | Where-Object HasPoints).Count -gt 0
        $isFinalGame = ([string]$meta.Status) -match '^Final'
        $impactState = if (-not $hasPoints) { 'unavailable' } elseif ($isFinalGame) { 'final' } else { 'partial' }

        $games += [PSCustomObject][ordered]@{
            GameID           = $gameID
            DecisionWindowID = $meta.DecisionWindowID
            StartsAtUtc      = $meta.StartsAtUtc
            AwayTeamID       = $meta.AwayTeamID
            AwayTeamAbbr     = $meta.AwayTeamAbbr
            HomeTeamID       = $meta.HomeTeamID
            HomeTeamAbbr     = $meta.HomeTeamAbbr
            Status           = $meta.Status
            Relevance        = [PSCustomObject][ordered]@{
                RosteredPlayerCount     = $associations.Count
                StarterCount            = @($associations | Where-Object IsStarter).Count
                FantasyTeamCount        = @($associations | Select-Object -ExpandProperty FantasyTeamID -Unique).Count
                FantasyMatchupCount     = @($associations | Select-Object -ExpandProperty FantasyMatchupID -Unique).Count
                UnknownAssociationCount = $unknownForGame
            }
            Impact           = [PSCustomObject][ordered]@{
                State                    = $impactState
                RosteredPoints           = if ($hasPoints) { [math]::Round([double](($associations | Where-Object HasPoints | Measure-Object Points -Sum).Sum), 4) } else { $null }
                StarterPoints            = if ($hasPoints) { [math]::Round([double](($associations | Where-Object { $_.HasPoints -and $_.IsStarter } | Measure-Object Points -Sum).Sum), 4) } else { $null }
                OutcomeSwingMatchupCount = 0
            }
            FantasyTeams     = @($fantasyTeams | Sort-Object FantasyMatchupID, FantasyTeamID)
        }
    }

    $matchupViews = @()
    foreach ($matchup in @($FantasyMatchups | Sort-Object FantasyMatchupID)) {
        $teamIDs = @($matchup.TeamIDs)
        $leftID = [string]$teamIDs[0]
        $rightID = [string]$teamIDs[1]
        $leftFact = @($matchup.Teams | Where-Object { [string]$_.FantasyTeamID -eq $leftID } | Select-Object -First 1)[0]
        $rightFact = @($matchup.Teams | Where-Object { [string]$_.FantasyTeamID -eq $rightID } | Select-Object -First 1)[0]
        $officialAvailable = $WeekIsFinal -and $null -ne $leftFact.FinalScore -and $null -ne $rightFact.FinalScore -and -not $leftFact.HasCustomPoints -and -not $rightFact.HasCustomPoints
        $actualOutcome = if ($officialAvailable) { Get-FgcOutcomeState -Left ([double]$leftFact.FinalScore) -Right ([double]$rightFact.FinalScore) } else { $null }

        $gameRows = @()
        foreach ($game in @($games | Sort-Object StartsAtUtc, GameID)) {
            $key = "$($matchup.FantasyMatchupID)|$($game.GameID)"
            if (-not $matchupGameRows.ContainsKey($key)) { continue }
            $sides = @($matchupGameRows[$key])
            $leftSide = @($sides | Where-Object { [string]$_.FantasyTeamID -eq $leftID } | Select-Object -First 1)
            $rightSide = @($sides | Where-Object { [string]$_.FantasyTeamID -eq $rightID } | Select-Object -First 1)
            $leftStarterPoints = if ($leftSide.Count -eq 1) { [double]$leftSide[0].StarterPoints } else { 0.0 }
            $rightStarterPoints = if ($rightSide.Count -eq 1) { [double]$rightSide[0].StarterPoints } else { 0.0 }
            $outcomeChanged = $null
            $withoutLeft = $null
            $withoutRight = $null
            if ($officialAvailable) {
                $withoutLeft = [double]$leftFact.FinalScore - $leftStarterPoints
                $withoutRight = [double]$rightFact.FinalScore - $rightStarterPoints
                $withoutOutcome = Get-FgcOutcomeState -Left $withoutLeft -Right $withoutRight
                $outcomeChanged = $withoutOutcome -ne $actualOutcome
                if ($outcomeChanged) {
                    $game.Impact.OutcomeSwingMatchupCount = [int]$game.Impact.OutcomeSwingMatchupCount + 1
                }
            }
            $gameRows += [PSCustomObject][ordered]@{
                GameID                   = $game.GameID
                DecisionWindowID          = $game.DecisionWindowID
                StartsAtUtc               = $game.StartsAtUtc
                LeftStarterCount          = if ($leftSide.Count -eq 1) { [int]$leftSide[0].StarterCount } else { 0 }
                RightStarterCount         = if ($rightSide.Count -eq 1) { [int]$rightSide[0].StarterCount } else { 0 }
                LeftRosteredPlayerCount   = if ($leftSide.Count -eq 1) { [int]$leftSide[0].RosteredPlayerCount } else { 0 }
                RightRosteredPlayerCount  = if ($rightSide.Count -eq 1) { [int]$rightSide[0].RosteredPlayerCount } else { 0 }
                LeftStarterPoints         = $leftStarterPoints
                RightStarterPoints        = $rightStarterPoints
                StarterPointDelta         = [math]::Round($leftStarterPoints - $rightStarterPoints, 4)
                OutcomeChangedWithoutGame = $outcomeChanged
                ScoreWithoutGame          = if ($officialAvailable) { [PSCustomObject][ordered]@{ Left = [math]::Round($withoutLeft,4); Right = [math]::Round($withoutRight,4) } } else { $null }
            }
        }

        $matchupViews += [PSCustomObject][ordered]@{
            FantasyMatchupID = $matchup.FantasyMatchupID
            TeamIDs          = @($teamIDs)
            FinalScores      = if ($officialAvailable) { [PSCustomObject][ordered]@{ Left = [double]$leftFact.FinalScore; Right = [double]$rightFact.FinalScore } } else { $null }
            CounterfactualState = if ($officialAvailable) { 'available' } elseif ($WeekIsFinal -and ($leftFact.HasCustomPoints -or $rightFact.HasCustomPoints)) { 'unavailable-custom-score' } elseif ($WeekIsFinal) { 'unavailable-final-score' } else { 'unavailable-not-final' }
            Games            = $gameRows
        }
    }

    $decisionWindows = @(
        Get-FgcCollection (Get-FgcPropertyValue -Object $DecisionFacts -Names @('DecisionWindows')) |
            Sort-Object StartsAtUtc |
            ForEach-Object {
                [PSCustomObject][ordered]@{
                    DecisionWindowID = [string]$_.DecisionWindowID
                    StartsAtUtc      = [string]$_.StartsAtUtc
                    GameIDs          = @($_.Games | ForEach-Object { [string]$_.GameID } | Sort-Object)
                }
            }
    )
    $scoringState = if ($WeekIsFinal) { 'final' } elseif (@($games | Where-Object { $_.Impact.State -ne 'unavailable' }).Count -gt 0) { 'partial' } else { 'pending' }

    return [PSCustomObject][ordered]@{
        SchemaVersion       = 1
        LeagueID            = $LeagueID
        Season              = $Season
        Week                = $Week
        ScoringState        = $scoringState
        DecisionWindows     = $decisionWindows
        Games               = @($games | Sort-Object StartsAtUtc, GameID)
        FantasyMatchups     = $matchupViews
        NonGameAssociations = @($nonGameAssociations | Sort-Object FantasyMatchupID, FantasyTeamID, PlayerID)
    }
}

function Test-FantasyGameContextReadModelChanged {
    param([AllowNull()][object]$OldData, [AllowNull()][object]$NewData)
    if ($null -eq $OldData) { return $true }
    return (($OldData | ConvertTo-Json -Depth 20 -Compress) -ne ($NewData | ConvertTo-Json -Depth 20 -Compress))
}

function Get-FgcScheduleWeek {
    param([AllowEmptyCollection()][array]$Schedule, [int]$Week)
    $label = "Week $Week"
    return @($Schedule | Where-Object {
        [string](Get-FgcPropertyValue -Object $_ -Names @('gameWeek','Week')) -eq $label -or
        [string](Get-FgcPropertyValue -Object $_ -Names @('gameWeek','Week')) -eq [string]$Week
    })
}

function ConvertTo-FgcKickoff {
    param([AllowNull()][object]$Game)
    $epoch = Get-FgcPropertyValue -Object $Game -Names @('gameTime_epoch','GameTimeEpoch')
    if ($null -ne $epoch -and -not [string]::IsNullOrWhiteSpace([string]$epoch)) {
        try { return [DateTimeOffset]::FromUnixTimeSeconds([int64][double]$epoch).UtcDateTime.ToString("yyyy-MM-ddTHH:mm:ss'Z'") } catch {}
    }
    $utc = Get-FgcPropertyValue -Object $Game -Names @('StartsAtUtc','GameTimeUtc')
    if ($null -ne $utc -and -not [string]::IsNullOrWhiteSpace([string]$utc)) {
        try { return ([DateTimeOffset]::Parse([string]$utc)).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss'Z'") } catch {}
    }
    return $null
}

function Get-FgcLegacyPlayerMap {
    param([AllowEmptyCollection()][array]$Players)
    $map = @{}
    foreach ($player in @($Players)) {
        $id = ConvertTo-FgcPlayerID -Player $player
        if ([string]::IsNullOrWhiteSpace($id)) { continue }
        if (-not $map.ContainsKey($id)) { $map[$id] = $player }
    }
    return $map
}

function Get-FgcWeeklyRosterAssignments {
    param([AllowNull()][object]$Document)
    $rows = @()
    if ($null -eq $Document) { return $rows }
    if ($Document -is [System.Collections.IEnumerable] -and $Document -isnot [string]) {
        $rows = @($Document)
    } else {
        foreach ($name in @('Rows','Records','Rosters','Players','Data')) {
            $value = Get-FgcPropertyValue -Object $Document -Names @($name)
            if ($null -ne $value) { $rows = @(Get-FgcCollection $value); break }
        }
    }

    $result = @()
    foreach ($row in $rows) {
        $playerRef = Get-FgcPropertyValue -Object $row -Names @('Player')
        $canonicalID = ConvertTo-FgcCanonicalPlayerID -Player $(if ($null -ne $playerRef) { $playerRef } else { $row })
        if ([string]::IsNullOrWhiteSpace($canonicalID)) { continue }
        $teamRef = Get-FgcPropertyValue -Object $row -Names @('Team')
        $teamID = Get-FgcPropertyValue -Object $row -Names @('CanonicalTeamID','TeamID')
        $teamAbbr = Get-FgcPropertyValue -Object $row -Names @('TeamAbbr','TeamAbv')
        if ($null -ne $teamRef -and $teamRef -isnot [string]) {
            if ($null -eq $teamID) { $teamID = Get-FgcPropertyValue -Object $teamRef -Names @('CanonicalTeamID','TeamID') }
            if ($null -eq $teamAbbr) { $teamAbbr = Get-FgcPropertyValue -Object $teamRef -Names @('TeamAbbr','TeamAbv','Abbr') }
        }
        $result += [PSCustomObject]@{ CanonicalPlayerID = $canonicalID; TeamID = $teamID; TeamAbbr = $teamAbbr }
    }
    return $result
}

function New-FgcHistoricalDecisionFacts {
    param(
        [Parameter(Mandatory = $true)][int]$Week,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$Schedule,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$FantasyMatchups,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$HistoricalPlayers,
        [AllowNull()][object]$WeeklyRosterDocument
    )

    $weekSchedule = @(Get-FgcScheduleWeek -Schedule $Schedule -Week $Week)
    $normalizedGames = @()
    foreach ($game in $weekSchedule) {
        $gameID = [string](Get-FgcPropertyValue -Object $game -Names @('gameID','GameID'))
        $startsAtUtc = ConvertTo-FgcKickoff -Game $game
        if ([string]::IsNullOrWhiteSpace($gameID) -or [string]::IsNullOrWhiteSpace($startsAtUtc)) { continue }
        $normalizedGames += [PSCustomObject][ordered]@{
            GameID       = $gameID
            StartsAtUtc  = $startsAtUtc
            AwayTeamID   = [string](Get-FgcPropertyValue -Object $game -Names @('teamIDAway','AwayTeamID'))
            AwayTeamAbbr = Get-FgcPropertyValue -Object $game -Names @('teamAbvAway','AwayTeamAbbr')
            HomeTeamID   = [string](Get-FgcPropertyValue -Object $game -Names @('teamIDHome','HomeTeamID'))
            HomeTeamAbbr = Get-FgcPropertyValue -Object $game -Names @('teamAbvHome','HomeTeamAbbr')
        }
    }

    $legacyPlayerMap = Get-FgcLegacyPlayerMap -Players $HistoricalPlayers
    $weeklyAssignments = @(Get-FgcWeeklyRosterAssignments -Document $WeeklyRosterDocument)
    $weeklyByCanonical = @{}
    foreach ($assignment in $weeklyAssignments) {
        if (-not $weeklyByCanonical.ContainsKey($assignment.CanonicalPlayerID)) { $weeklyByCanonical[$assignment.CanonicalPlayerID] = @() }
        $weeklyByCanonical[$assignment.CanonicalPlayerID] += $assignment
    }

    $playerLockFacts = @()
    foreach ($matchup in $FantasyMatchups) {
        foreach ($team in $matchup.Teams) {
            foreach ($player in $team.Players) {
                $candidateGames = @()
                $canonicalID = [string]$player.CanonicalPlayerID
                if (-not [string]::IsNullOrWhiteSpace($canonicalID) -and $weeklyByCanonical.ContainsKey($canonicalID)) {
                    foreach ($assignment in @($weeklyByCanonical[$canonicalID])) {
                        $candidateGames += @($normalizedGames | Where-Object {
                            (-not [string]::IsNullOrWhiteSpace([string]$assignment.TeamID) -and ([string]$_.AwayTeamID -eq [string]$assignment.TeamID -or [string]$_.HomeTeamID -eq [string]$assignment.TeamID)) -or
                            (-not [string]::IsNullOrWhiteSpace([string]$assignment.TeamAbbr) -and ([string]$_.AwayTeamAbbr -eq [string]$assignment.TeamAbbr -or [string]$_.HomeTeamAbbr -eq [string]$assignment.TeamAbbr))
                        })
                    }
                }

                if (@($candidateGames | Sort-Object GameID -Unique).Count -ne 1 -and $legacyPlayerMap.ContainsKey([string]$player.PlayerID)) {
                    $legacyGames = @(Get-FgcCollection (Get-FgcPropertyValue -Object $legacyPlayerMap[[string]$player.PlayerID] -Names @('Games')) | Where-Object {
                        [string](Get-FgcPropertyValue -Object $_ -Names @('Week')) -eq [string]$Week -or
                        [string](Get-FgcPropertyValue -Object $_ -Names @('Week')) -eq "Week $Week"
                    })
                    $candidateGames = @()
                    foreach ($legacyGame in $legacyGames) {
                        $legacyGameID = [string](Get-FgcPropertyValue -Object $legacyGame -Names @('GameID','gameID'))
                        if ([string]::IsNullOrWhiteSpace($legacyGameID)) { continue }
                        $candidateGames += @($normalizedGames | Where-Object { $_.GameID -eq $legacyGameID })
                    }
                }

                $uniqueGames = @($candidateGames | Sort-Object GameID -Unique)
                if ($uniqueGames.Count -eq 1) {
                    $game = $uniqueGames[0]
                    $nflTeamID = $null
                    if ($legacyPlayerMap.ContainsKey([string]$player.PlayerID)) {
                        $legacyGame = @(Get-FgcCollection (Get-FgcPropertyValue -Object $legacyPlayerMap[[string]$player.PlayerID] -Names @('Games')) | Where-Object {
                            [string](Get-FgcPropertyValue -Object $_ -Names @('GameID','gameID')) -eq $game.GameID
                        } | Select-Object -First 1)
                        if ($legacyGame.Count -eq 1) { $nflTeamID = Get-FgcPropertyValue -Object $legacyGame[0] -Names @('TeamID') }
                    }
                    $playerLockFacts += [PSCustomObject][ordered]@{
                        FantasyTeamID = $team.FantasyTeamID; PlayerID = $player.PlayerID; NFLTeamID = $nflTeamID
                        Kind = 'scheduled'; GameID = $game.GameID; DecisionWindowID = $game.StartsAtUtc; StartsAtUtc = $game.StartsAtUtc; IsStarter = $player.IsStarter
                    }
                } else {
                    $playerLockFacts += [PSCustomObject][ordered]@{
                        FantasyTeamID = $team.FantasyTeamID; PlayerID = $player.PlayerID; NFLTeamID = $null
                        Kind = 'unknown'; GameID = $null; DecisionWindowID = $null; StartsAtUtc = $null; IsStarter = $player.IsStarter
                    }
                }
            }
        }
    }

    $windows = @()
    foreach ($group in @($normalizedGames | Group-Object StartsAtUtc | Sort-Object Name)) {
        $windows += [PSCustomObject][ordered]@{
            DecisionWindowID = [string]$group.Name
            StartsAtUtc      = [string]$group.Name
            Games            = @($group.Group | Sort-Object GameID)
        }
    }
    return [PSCustomObject][ordered]@{ DecisionWindows = $windows; PlayerLockFacts = $playerLockFacts }
}

function New-HistoricalFantasyGameContextSeason {
    param(
        [Parameter(Mandatory = $true)][string]$LeagueID,
        [Parameter(Mandatory = $true)][int]$Season,
        [Parameter(Mandatory = $true)][string]$LeagueSourceFile,
        [Parameter(Mandatory = $true)][string]$MatchupDirectory,
        [Parameter(Mandatory = $true)][string]$ScheduleFile,
        [Parameter(Mandatory = $true)][string]$HistoricalPlayersFile,
        [AllowNull()][string]$WeeklyRosterDirectory
    )

    if (-not (Test-Path $LeagueSourceFile) -or -not (Test-Path $MatchupDirectory) -or -not (Test-Path $ScheduleFile) -or -not (Test-Path $HistoricalPlayersFile)) {
        throw "Historical FantasyGameContext $Season requires canonical league matchups plus historical schedule/player evidence."
    }

    $leagueSource = Get-Content $LeagueSourceFile -Raw | ConvertFrom-Json
    $lastWeek = [int](Get-FgcPropertyValue -Object (Get-FgcPropertyValue -Object $leagueSource -Names @('WeekStructure')) -Names @('FinalLeagueWeek'))
    if ($lastWeek -le 0) { $lastWeek = [int](Get-FgcPropertyValue -Object (Get-FgcPropertyValue -Object $leagueSource -Names @('Settings')) -Names @('last_scored_leg')) }
    if ($lastWeek -le 0) { throw "Historical FantasyGameContext $Season cannot resolve the final fantasy week." }

    $schedule = @(Get-Content $ScheduleFile -Raw | ConvertFrom-Json)
    $historicalPlayers = @(Get-Content $HistoricalPlayersFile -Raw | ConvertFrom-Json)
    $weeks = @()
    for ($week = 1; $week -le $lastWeek; $week++) {
        $matchupFile = Join-Path $MatchupDirectory "week-$week.json"
        if (-not (Test-Path $matchupFile)) { continue }
        $matchupRows = @(Get-Content $matchupFile -Raw | ConvertFrom-Json)
        $facts = @(ConvertTo-FgcCanonicalMatchupFacts -Season ([string]$Season) -Week $week -MatchupRows $matchupRows)
        if ($facts.Count -eq 0) { continue }

        $weeklyDocument = $null
        if (-not [string]::IsNullOrWhiteSpace($WeeklyRosterDirectory)) {
            $weeklyFile = Join-Path $WeeklyRosterDirectory ("{0:D2}.json" -f $week)
            if (Test-Path $weeklyFile) {
                try { $weeklyDocument = Get-Content $weeklyFile -Raw | ConvertFrom-Json } catch { Write-Warning "Could not read weekly NFL roster evidence '$weeklyFile'. $_" }
            }
        }
        $decisionFacts = New-FgcHistoricalDecisionFacts -Week $week -Schedule $schedule -FantasyMatchups $facts -HistoricalPlayers $historicalPlayers -WeeklyRosterDocument $weeklyDocument
        $weekModel = New-FantasyGameContextReadModel -LeagueID $LeagueID -Season ([string]$Season) -Week $week -DecisionFacts $decisionFacts -FantasyMatchups $facts -Schedule $schedule -WeekIsFinal $true
        $weeks += $weekModel
    }

    return [PSCustomObject][ordered]@{
        SchemaVersion = 1
        LeagueID      = $LeagueID
        Season        = [string]$Season
        ScoringState  = 'final'
        Weeks         = $weeks
    }
}
