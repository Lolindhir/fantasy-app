function Get-FrvPropertyValue {
    param([AllowNull()][object]$Object, [Parameter(Mandatory = $true)][string[]]$Names)
    if ($null -eq $Object) { return $null }
    foreach ($name in $Names) {
        if ($Object.PSObject.Properties.Name -contains $name) { return $Object.$name }
    }
    return $null
}

function Get-FrvCollection {
    param([AllowNull()][object]$Value)
    if ($null -eq $Value) { return @() }
    if ($Value -is [string] -or $Value -isnot [System.Collections.IEnumerable]) { return @($Value) }
    return @($Value)
}

function ConvertTo-FrvPlayerID {
    param([AllowNull()][object]$Value)
    if ($null -eq $Value) { return $null }
    $text = ([string]$Value).Trim()
    if ([string]::IsNullOrWhiteSpace($text) -or $text -eq '0') { return $null }
    return $text
}

function ConvertTo-FrvUtcString {
    param([AllowNull()][object]$Value)
    if ($null -eq $Value -or [string]::IsNullOrWhiteSpace([string]$Value)) { return $null }
    try {
        return ([DateTimeOffset]::Parse([string]$Value)).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss'Z'")
    }
    catch {
        return $null
    }
}

function Get-FrvSlotDefinitions {
    param([Parameter(Mandatory = $true)][object]$League)

    $positions = @(Get-FrvCollection (Get-FrvPropertyValue -Object $League -Names @('roster_positions','RosterPositions')))
    if ($positions.Count -eq 0) { throw 'Fantasy Relevance v2 requires league roster_positions.' }

    $occurrences = @{}
    $result = @()
    for ($index = 0; $index -lt $positions.Count; $index++) {
        $raw = [string]$positions[$index]
        if ([string]::IsNullOrWhiteSpace($raw)) { continue }
        $slotType = $raw.Trim().ToUpperInvariant()
        if ($slotType -eq 'BN') { continue }
        if (-not $occurrences.ContainsKey($slotType)) { $occurrences[$slotType] = 0 }
        $occurrences[$slotType] = [int]$occurrences[$slotType] + 1
        $result += [PSCustomObject][ordered]@{
            SlotID      = "$slotType-$($occurrences[$slotType])"
            SlotType    = $slotType
            SlotOrdinal = [int]$occurrences[$slotType]
            SlotIndex   = $result.Count
        }
    }

    if ($result.Count -eq 0) { throw 'Fantasy Relevance v2 could not derive starting slots from roster_positions.' }
    return $result
}

function Test-FrvSlotEligibility {
    param(
        [AllowNull()][string]$Position,
        [Parameter(Mandatory = $true)][string]$SlotType
    )

    if ([string]::IsNullOrWhiteSpace($Position)) { return $false }
    $positionKey = $Position.Trim().ToUpperInvariant()
    $slotKey = $SlotType.Trim().ToUpperInvariant()

    switch ($slotKey) {
        'FLEX' { return @('RB','WR','TE') -contains $positionKey }
        'SUPER_FLEX' { return @('QB','RB','WR','TE') -contains $positionKey }
        'WRRB_FLEX' { return @('WR','RB') -contains $positionKey }
        'REC_FLEX' { return @('WR','TE') -contains $positionKey }
        default { return $positionKey -eq $slotKey }
    }
}

function Get-FrvGameState {
    param(
        [AllowNull()][object]$LockFact,
        [AllowNull()][string]$GameStatus,
        [Parameter(Mandatory = $true)][DateTimeOffset]$AsOfUtc
    )

    if ($null -eq $LockFact -or [string](Get-FrvPropertyValue -Object $LockFact -Names @('Kind')) -ne 'scheduled') {
        return 'unknown'
    }
    if (-not [string]::IsNullOrWhiteSpace($GameStatus) -and $GameStatus -match '^Final') {
        return 'completed'
    }

    $startsAtText = ConvertTo-FrvUtcString -Value (Get-FrvPropertyValue -Object $LockFact -Names @('StartsAtUtc'))
    if ([string]::IsNullOrWhiteSpace($startsAtText)) { return 'unknown' }
    $startsAt = [DateTimeOffset]::Parse($startsAtText)
    if ($startsAt -le $AsOfUtc.ToUniversalTime()) { return 'locked-active' }
    return 'unlocked'
}

function Add-FantasyRelevanceDecisionFacts {
    param(
        [Parameter(Mandatory = $true)][object]$BaseReadModel,
        [Parameter(Mandatory = $true)][object]$League,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$Teams,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$Players,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$Schedule,
        [DateTimeOffset]$AsOfUtc = [DateTimeOffset]::UtcNow
    )

    $slotDefinitions = @(Get-FrvSlotDefinitions -League $League)
    $statusByGame = @{}
    foreach ($game in @($Schedule)) {
        $gameID = [string](Get-FrvPropertyValue -Object $game -Names @('gameID','GameID'))
        if ([string]::IsNullOrWhiteSpace($gameID)) { continue }
        $statusByGame[$gameID] = [string](Get-FrvPropertyValue -Object $game -Names @('gameStatus','Status'))
    }

    $positionByPlayer = @{}
    foreach ($player in @($Players)) {
        $playerID = ConvertTo-FrvPlayerID -Value (Get-FrvPropertyValue -Object $player -Names @('ID','PlayerID','SleeperID'))
        if ($null -eq $playerID) { continue }
        $position = [string](Get-FrvPropertyValue -Object $player -Names @('Position','FantasyPosition'))
        $positionByPlayer[$playerID] = if ([string]::IsNullOrWhiteSpace($position)) { $null } else { $position.Trim().ToUpperInvariant() }
    }

    $lockByTeamPlayer = @{}
    foreach ($lock in @(Get-FrvCollection (Get-FrvPropertyValue -Object $BaseReadModel -Names @('PlayerLockFacts')))) {
        $teamID = [string](Get-FrvPropertyValue -Object $lock -Names @('FantasyTeamID'))
        $playerID = ConvertTo-FrvPlayerID -Value (Get-FrvPropertyValue -Object $lock -Names @('PlayerID'))
        if ([string]::IsNullOrWhiteSpace($teamID) -or $null -eq $playerID) { continue }
        $lockByTeamPlayer["$teamID|$playerID"] = $lock
    }

    $teamStates = @()
    foreach ($team in @($Teams | Sort-Object { [string](Get-FrvPropertyValue -Object $_ -Names @('TeamID','FantasyTeamID')) })) {
        $teamID = [string](Get-FrvPropertyValue -Object $team -Names @('TeamID','FantasyTeamID'))
        if ([string]::IsNullOrWhiteSpace($teamID)) { continue }

        $rosterIDs = @(
            Get-FrvCollection (Get-FrvPropertyValue -Object $team -Names @('Roster','PlayerIDs')) |
                ForEach-Object { ConvertTo-FrvPlayerID -Value $_ } |
                Where-Object { $null -ne $_ } |
                Select-Object -Unique
        )
        $starterRaw = @(Get-FrvCollection (Get-FrvPropertyValue -Object $team -Names @('Starter','StarterIDs','Starters')))
        $starterIDs = @(
            $starterRaw |
                ForEach-Object { ConvertTo-FrvPlayerID -Value $_ } |
                Where-Object { $null -ne $_ } |
                Select-Object -Unique
        )
        $irIDs = @(
            Get-FrvCollection (Get-FrvPropertyValue -Object $team -Names @('Reserve','IR')) |
                ForEach-Object { ConvertTo-FrvPlayerID -Value $_ } |
                Where-Object { $null -ne $_ } |
                Select-Object -Unique
        )
        $taxiIDs = @(
            Get-FrvCollection (Get-FrvPropertyValue -Object $team -Names @('Taxi')) |
                ForEach-Object { ConvertTo-FrvPlayerID -Value $_ } |
                Where-Object { $null -ne $_ } |
                Select-Object -Unique
        )

        foreach ($starterID in $starterIDs) {
            if ($irIDs -contains $starterID -or $taxiIDs -contains $starterID) {
                throw "Fantasy Relevance v2 Team '$teamID' has starter '$starterID' outside Active Roster."
            }
        }
        if ($starterRaw.Count -gt $slotDefinitions.Count) {
            throw "Fantasy Relevance v2 Team '$teamID' has more starter entries than starting slots."
        }

        $slotStates = @()
        $slotByStarter = @{}
        for ($slotIndex = 0; $slotIndex -lt $slotDefinitions.Count; $slotIndex++) {
            $definition = $slotDefinitions[$slotIndex]
            $starterID = if ($slotIndex -lt $starterRaw.Count) { ConvertTo-FrvPlayerID -Value $starterRaw[$slotIndex] } else { $null }
            $lock = if ($null -ne $starterID -and $lockByTeamPlayer.ContainsKey("$teamID|$starterID")) { $lockByTeamPlayer["$teamID|$starterID"] } else { $null }
            $gameID = if ($null -ne $lock) { [string](Get-FrvPropertyValue -Object $lock -Names @('GameID')) } else { $null }
            $status = if (-not [string]::IsNullOrWhiteSpace($gameID) -and $statusByGame.ContainsKey($gameID)) { [string]$statusByGame[$gameID] } else { $null }
            $state = if ($null -eq $starterID) { 'unlocked' } else { Get-FrvGameState -LockFact $lock -GameStatus $status -AsOfUtc $AsOfUtc }

            $slotState = [PSCustomObject][ordered]@{
                SlotID           = $definition.SlotID
                SlotType         = $definition.SlotType
                SlotOrdinal      = $definition.SlotOrdinal
                SlotIndex        = $definition.SlotIndex
                CurrentStarterID = $starterID
                State            = $state
                GameID           = if ($null -ne $lock) { Get-FrvPropertyValue -Object $lock -Names @('GameID') } else { $null }
                DecisionWindowID = if ($null -ne $lock) { Get-FrvPropertyValue -Object $lock -Names @('DecisionWindowID') } else { $null }
                StartsAtUtc      = if ($null -ne $lock) { Get-FrvPropertyValue -Object $lock -Names @('StartsAtUtc') } else { $null }
            }
            $slotStates += $slotState
            if ($null -ne $starterID) { $slotByStarter[$starterID] = $slotState }
        }

        $benchIDs = @($rosterIDs | Where-Object { $starterIDs -notcontains $_ -and $irIDs -notcontains $_ -and $taxiIDs -notcontains $_ })
        $mutableSlots = @($slotStates | Where-Object State -eq 'unlocked')
        $playerStates = @()
        foreach ($playerID in $rosterIDs) {
            $placement = if ($starterIDs -contains $playerID) { 'starter' } elseif ($irIDs -contains $playerID) { 'ir' } elseif ($taxiIDs -contains $playerID) { 'taxi' } else { 'bench' }
            $position = if ($positionByPlayer.ContainsKey($playerID)) { $positionByPlayer[$playerID] } else { $null }
            $lock = if ($lockByTeamPlayer.ContainsKey("$teamID|$playerID")) { $lockByTeamPlayer["$teamID|$playerID"] } else { $null }
            $gameID = if ($null -ne $lock) { [string](Get-FrvPropertyValue -Object $lock -Names @('GameID')) } else { $null }
            $status = if (-not [string]::IsNullOrWhiteSpace($gameID) -and $statusByGame.ContainsKey($gameID)) { [string]$statusByGame[$gameID] } else { $null }
            $gameState = Get-FrvGameState -LockFact $lock -GameStatus $status -AsOfUtc $AsOfUtc
            $eligibleSlotIDs = @()
            if ($placement -eq 'bench' -and $gameState -eq 'unlocked') {
                $eligibleSlotIDs = @(
                    $mutableSlots |
                        Where-Object { Test-FrvSlotEligibility -Position $position -SlotType $_.SlotType } |
                        Select-Object -ExpandProperty SlotID -Unique
                )
            }
            $isBenchCandidate = $placement -eq 'bench' -and $eligibleSlotIDs.Count -gt 0
            $lineupSlot = if ($placement -eq 'starter' -and $slotByStarter.ContainsKey($playerID)) { $slotByStarter[$playerID] } else { $null }

            $playerStates += [PSCustomObject][ordered]@{
                PlayerID                = $playerID
                Placement               = $placement
                Position                = $position
                GameState               = $gameState
                GameID                  = if ($null -ne $lock) { Get-FrvPropertyValue -Object $lock -Names @('GameID') } else { $null }
                DecisionWindowID        = if ($null -ne $lock) { Get-FrvPropertyValue -Object $lock -Names @('DecisionWindowID') } else { $null }
                StartsAtUtc             = if ($null -ne $lock) { Get-FrvPropertyValue -Object $lock -Names @('StartsAtUtc') } else { $null }
                LineupSlotID            = if ($null -ne $lineupSlot) { $lineupSlot.SlotID } else { $null }
                LineupSlotType          = if ($null -ne $lineupSlot) { $lineupSlot.SlotType } else { $null }
                EligibleUnlockedSlotIDs = $eligibleSlotIDs
                IsBenchCandidate        = $isBenchCandidate
                HasDirectScoringPath    = $placement -eq 'starter' -and @('unlocked','locked-active') -contains $gameState
                HasAlternativePath      = $isBenchCandidate
            }
        }

        $teamStates += [PSCustomObject][ordered]@{
            FantasyTeamID                 = $teamID
            ActiveRosterPlayerCount       = $starterIDs.Count + $benchIDs.Count
            StarterCount                  = $starterIDs.Count
            BenchCount                    = $benchIDs.Count
            IRCount                       = $irIDs.Count
            TaxiCount                     = $taxiIDs.Count
            UnlockedStarterCount          = @($playerStates | Where-Object { $_.Placement -eq 'starter' -and $_.GameState -eq 'unlocked' }).Count
            LockedActiveStarterCount      = @($playerStates | Where-Object { $_.Placement -eq 'starter' -and $_.GameState -eq 'locked-active' }).Count
            CompletedStarterCount         = @($playerStates | Where-Object { $_.Placement -eq 'starter' -and $_.GameState -eq 'completed' }).Count
            EligibleBenchCandidateCount   = @($playerStates | Where-Object IsBenchCandidate).Count
            HasRemainingScoringPath       = @($playerStates | Where-Object { $_.HasDirectScoringPath -or $_.HasAlternativePath }).Count -gt 0
            Slots                          = $slotStates
            Players                        = @($playerStates | Sort-Object Placement, PlayerID)
        }
    }

    $relevance = [PSCustomObject][ordered]@{
        Version         = 1
        SlotDefinitions = $slotDefinitions
        Teams           = $teamStates
    }
    $BaseReadModel | Add-Member -NotePropertyName FantasyRelevance -NotePropertyValue $relevance -Force
    if ($BaseReadModel.PSObject.Properties.Name -contains 'SchemaVersion') {
        $BaseReadModel.SchemaVersion = [Math]::Max(2, [int]$BaseReadModel.SchemaVersion)
    }
    return $BaseReadModel
}

function Add-FantasyRelevanceContext {
    param(
        [Parameter(Mandatory = $true)][object]$BaseContext,
        [Parameter(Mandatory = $true)][object]$DecisionFacts
    )

    $decisionRelevance = Get-FrvPropertyValue -Object $DecisionFacts -Names @('FantasyRelevance')
    if ($null -eq $decisionRelevance) { return $BaseContext }

    $teamStateByID = @{}
    foreach ($teamState in @(Get-FrvCollection (Get-FrvPropertyValue -Object $decisionRelevance -Names @('Teams')))) {
        $teamStateByID[[string]$teamState.FantasyTeamID] = $teamState
    }

    $matchupByTeam = @{}
    foreach ($matchup in @(Get-FrvCollection (Get-FrvPropertyValue -Object $BaseContext -Names @('FantasyMatchups')))) {
        foreach ($teamID in @(Get-FrvCollection (Get-FrvPropertyValue -Object $matchup -Names @('TeamIDs')))) {
            $matchupByTeam[[string]$teamID] = $matchup
        }
    }

    $paths = @()
    foreach ($teamID in @($teamStateByID.Keys | Sort-Object)) {
        if (-not $matchupByTeam.ContainsKey($teamID)) { continue }
        $matchup = $matchupByTeam[$teamID]
        foreach ($player in @($teamStateByID[$teamID].Players)) {
            $pathType = $null
            if ($player.Placement -eq 'starter' -and $player.GameState -eq 'locked-active') { $pathType = 'locked-starter' }
            elseif ($player.Placement -eq 'starter' -and $player.GameState -eq 'unlocked') { $pathType = 'unlocked-starter' }
            elseif ($player.IsBenchCandidate) { $pathType = 'bench-candidate' }
            if ($null -eq $pathType -or [string]::IsNullOrWhiteSpace([string]$player.GameID)) { continue }

            $paths += [PSCustomObject][ordered]@{
                FantasyMatchupID = [string]$matchup.FantasyMatchupID
                FantasyTeamID    = $teamID
                PlayerID         = [string]$player.PlayerID
                GameID           = [string]$player.GameID
                DecisionWindowID = [string]$player.DecisionWindowID
                StartsAtUtc      = [string]$player.StartsAtUtc
                PathType         = $pathType
                LineupSlotID     = $player.LineupSlotID
                EligibleSlotIDs  = @($player.EligibleUnlockedSlotIDs)
            }
        }
    }

    $matchupRelevanceByID = @{}
    foreach ($matchup in @(Get-FrvCollection (Get-FrvPropertyValue -Object $BaseContext -Names @('FantasyMatchups')))) {
        $matchupID = [string]$matchup.FantasyMatchupID
        $teamIDs = @(Get-FrvCollection (Get-FrvPropertyValue -Object $matchup -Names @('TeamIDs')) | ForEach-Object { [string]$_ })
        $leftID = if ($teamIDs.Count -gt 0) { $teamIDs[0] } else { $null }
        $rightID = if ($teamIDs.Count -gt 1) { $teamIDs[1] } else { $null }
        $matchupPaths = @($paths | Where-Object FantasyMatchupID -eq $matchupID)
        $leftPaths = @($matchupPaths | Where-Object FantasyTeamID -eq $leftID)
        $rightPaths = @($matchupPaths | Where-Object FantasyTeamID -eq $rightID)

        $windowGroups = @($matchupPaths | Where-Object { -not [string]::IsNullOrWhiteSpace($_.DecisionWindowID) } | Group-Object DecisionWindowID)
        $orderedWindows = @($windowGroups | Sort-Object { [DateTimeOffset]::Parse([string]$_.Group[0].StartsAtUtc) })
        $activeGroups = @($orderedWindows | Where-Object { @($_.Group | Where-Object PathType -eq 'locked-starter').Count -gt 0 })
        $nextGroup = if ($activeGroups.Count -gt 0) { $activeGroups[0] } elseif ($orderedWindows.Count -gt 0) { $orderedWindows[0] } else { $null }
        $finalGroup = if ($orderedWindows.Count -gt 0) { $orderedWindows[-1] } else { $null }
        $finalCommitted = $false
        if ($null -ne $finalGroup) {
            $finalCommitted = @($finalGroup.Group | Where-Object PathType -ne 'locked-starter').Count -eq 0
        }

        $remainingState = if ($leftPaths.Count -gt 0 -and $rightPaths.Count -gt 0) { 'both-sides' } elseif ($leftPaths.Count -gt 0) { 'left-only' } elseif ($rightPaths.Count -gt 0) { 'right-only' } else { 'none' }
        $relevance = [PSCustomObject][ordered]@{
            State                          = $remainingState
            HasRemainingScoringPaths       = $matchupPaths.Count -gt 0
            LeftRemainingPathCount          = $leftPaths.Count
            RightRemainingPathCount         = $rightPaths.Count
            LockedActiveStarterCount        = @($matchupPaths | Where-Object PathType -eq 'locked-starter').Count
            UnlockedStarterCount            = @($matchupPaths | Where-Object PathType -eq 'unlocked-starter').Count
            EligibleBenchCandidateCount     = @($matchupPaths | Where-Object PathType -eq 'bench-candidate').Count
            NextScoringWindowID             = if ($null -ne $nextGroup) { [string]$nextGroup.Name } else { $null }
            NextScoringGameIDs              = if ($null -ne $nextGroup) { @($nextGroup.Group | Select-Object -ExpandProperty GameID -Unique | Sort-Object) } else { @() }
            FinalScoringWindowID            = if ($null -ne $finalGroup) { [string]$finalGroup.Name } else { $null }
            FinalScoringGameIDs             = if ($null -ne $finalGroup) { @($finalGroup.Group | Select-Object -ExpandProperty GameID -Unique | Sort-Object) } else { @() }
            IsFinalScoringWindowCommitted   = $finalCommitted
        }
        $matchup | Add-Member -NotePropertyName RemainingRelevance -NotePropertyValue $relevance -Force
        $matchupRelevanceByID[$matchupID] = $relevance
    }

    $gameRows = @()
    foreach ($game in @(Get-FrvCollection (Get-FrvPropertyValue -Object $BaseContext -Names @('Games')))) {
        $gameID = [string]$game.GameID
        $gamePaths = @($paths | Where-Object GameID -eq $gameID)
        $matchupIDs = @($gamePaths | Select-Object -ExpandProperty FantasyMatchupID -Unique)
        $twoSided = 0
        $finalWindow = 0
        $committedFinalWindow = 0
        foreach ($matchupID in $matchupIDs) {
            $matchupGamePaths = @($gamePaths | Where-Object FantasyMatchupID -eq $matchupID)
            if (@($matchupGamePaths | Select-Object -ExpandProperty FantasyTeamID -Unique).Count -ge 2) { $twoSided++ }
            if ($matchupRelevanceByID.ContainsKey([string]$matchupID)) {
                $matchupRelevance = $matchupRelevanceByID[[string]$matchupID]
                if ([string]$matchupRelevance.FinalScoringWindowID -eq [string]$game.DecisionWindowID) {
                    $finalWindow++
                    if ($matchupRelevance.IsFinalScoringWindowCommitted) { $committedFinalWindow++ }
                }
            }
        }

        $gameRelevance = [PSCustomObject][ordered]@{
            HasRemainingRelevance                 = $gamePaths.Count -gt 0
            LockedActiveStarterCount              = @($gamePaths | Where-Object PathType -eq 'locked-starter').Count
            UnlockedStarterCount                  = @($gamePaths | Where-Object PathType -eq 'unlocked-starter').Count
            EligibleBenchCandidateCount           = @($gamePaths | Where-Object PathType -eq 'bench-candidate').Count
            FantasyMatchupCount                   = $matchupIDs.Count
            TwoSidedFantasyMatchupCount           = $twoSided
            FinalWindowFantasyMatchupCount        = $finalWindow
            CommittedFinalWindowMatchupCount      = $committedFinalWindow
        }
        $game | Add-Member -NotePropertyName RemainingRelevance -NotePropertyValue $gameRelevance -Force
        if ($gameRelevance.HasRemainingRelevance) { $gameRows += $game }
    }

    $ranked = @(
        $gameRows | Sort-Object `
            @{ Expression = { [int]$_.RemainingRelevance.CommittedFinalWindowMatchupCount }; Descending = $true }, `
            @{ Expression = { [int]$_.RemainingRelevance.LockedActiveStarterCount }; Descending = $true }, `
            @{ Expression = { [int]$_.RemainingRelevance.TwoSidedFantasyMatchupCount }; Descending = $true }, `
            @{ Expression = { [int]$_.RemainingRelevance.FantasyMatchupCount }; Descending = $true }, `
            @{ Expression = { [int]$_.RemainingRelevance.UnlockedStarterCount }; Descending = $true }, `
            @{ Expression = { [int]$_.RemainingRelevance.FinalWindowFantasyMatchupCount }; Descending = $true }, `
            @{ Expression = { [int]$_.RemainingRelevance.EligibleBenchCandidateCount }; Descending = $true }, `
            @{ Expression = { [string]$_.StartsAtUtc }; Descending = $false }, `
            @{ Expression = { [string]$_.GameID }; Descending = $false }
    )

    $mustWatch = @()
    for ($index = 0; $index -lt $ranked.Count; $index++) {
        $game = $ranked[$index]
        $game.RemainingRelevance | Add-Member -NotePropertyName MustWatchRank -NotePropertyValue ($index + 1) -Force
        $mustWatch += [PSCustomObject][ordered]@{
            Rank                                = $index + 1
            GameID                              = [string]$game.GameID
            DecisionWindowID                    = [string]$game.DecisionWindowID
            StartsAtUtc                         = [string]$game.StartsAtUtc
            CommittedFinalWindowMatchupCount    = [int]$game.RemainingRelevance.CommittedFinalWindowMatchupCount
            LockedActiveStarterCount            = [int]$game.RemainingRelevance.LockedActiveStarterCount
            TwoSidedFantasyMatchupCount         = [int]$game.RemainingRelevance.TwoSidedFantasyMatchupCount
            FantasyMatchupCount                 = [int]$game.RemainingRelevance.FantasyMatchupCount
            UnlockedStarterCount                = [int]$game.RemainingRelevance.UnlockedStarterCount
            FinalWindowFantasyMatchupCount      = [int]$game.RemainingRelevance.FinalWindowFantasyMatchupCount
            EligibleBenchCandidateCount         = [int]$game.RemainingRelevance.EligibleBenchCandidateCount
        }
    }

    $BaseContext | Add-Member -NotePropertyName MustWatchGames -NotePropertyValue $mustWatch -Force
    if ($BaseContext.PSObject.Properties.Name -contains 'SchemaVersion') {
        $BaseContext.SchemaVersion = [Math]::Max(2, [int]$BaseContext.SchemaVersion)
    }
    return $BaseContext
}
