function Get-FmpPropertyValue {
    param([AllowNull()][object]$Object, [Parameter(Mandatory = $true)][string[]]$Names)
    if ($null -eq $Object) { return $null }
    foreach ($name in $Names) {
        if ($Object.PSObject.Properties.Name -contains $name) { return $Object.$name }
    }
    return $null
}

function Get-FmpCollection {
    param([AllowNull()][object]$Value)
    if ($null -eq $Value) { return @() }
    if ($Value -is [string] -or $Value -isnot [System.Collections.IEnumerable]) { return @($Value) }
    return @($Value)
}

function Set-FmpProperty {
    param(
        [Parameter(Mandatory = $true)][object]$Object,
        [Parameter(Mandatory = $true)][string]$Name,
        [AllowNull()][object]$Value
    )
    $Object | Add-Member -NotePropertyName $Name -NotePropertyValue $Value -Force
}

function Get-FmpPathType {
    param([Parameter(Mandatory = $true)][object]$Player)

    $placement = [string](Get-FmpPropertyValue -Object $Player -Names @('Placement'))
    $gameState = [string](Get-FmpPropertyValue -Object $Player -Names @('GameState'))
    $isBenchCandidate = [bool](Get-FmpPropertyValue -Object $Player -Names @('IsBenchCandidate'))

    if ($placement -eq 'starter' -and $gameState -eq 'locked-active') { return 'locked-starter' }
    if ($placement -eq 'starter' -and $gameState -eq 'unlocked') { return 'unlocked-starter' }
    if ($isBenchCandidate) { return 'bench-candidate' }
    return $null
}

function Get-FmpPrimaryGameSelection {
    param(
        [Parameter(Mandatory = $true)][object[]]$WindowPaths,
        [Parameter(Mandatory = $true)][string[]]$EligibleGamePathTypes
    )

    $gameGroups = @(
        $WindowPaths |
            Group-Object GameID |
            Where-Object { @($_.Group | Where-Object { $EligibleGamePathTypes -contains $_.PathType }).Count -gt 0 } |
            Sort-Object `
                @{ Expression = { @($_.Group | Where-Object { $_.PathType -eq 'locked-starter' -or $_.PathType -eq 'unlocked-starter' }).Count }; Descending = $true }, `
                @{ Expression = { @($_.Group | Where-Object PathType -eq 'locked-starter').Count }; Descending = $true }, `
                @{ Expression = { @($_.Group | Where-Object PathType -eq 'bench-candidate').Count }; Descending = $true }, `
                @{ Expression = { [string]$_.Name }; Descending = $false }
    )

    if ($gameGroups.Count -eq 0) { return $null }

    $primary = $gameGroups[0]
    return [PSCustomObject][ordered]@{
        PrimaryGameID = [string]$primary.Name
        GameIDs = @($gameGroups | ForEach-Object { [string]$_.Name })
        PrimaryPaths = @($primary.Group)
    }
}

function Set-FmpEmptyScoringPreview {
    param([Parameter(Mandatory = $true)][object]$Remaining)

    Set-FmpProperty -Object $Remaining -Name 'NextScoringWindowID' -Value $null
    Set-FmpProperty -Object $Remaining -Name 'NextScoringGameIDs' -Value @()
    Set-FmpProperty -Object $Remaining -Name 'NextScoringPrimaryGameID' -Value $null
    Set-FmpProperty -Object $Remaining -Name 'NextScoringWindowGameCount' -Value 0
    Set-FmpProperty -Object $Remaining -Name 'NextScoringLockedActiveStarterCount' -Value 0
    Set-FmpProperty -Object $Remaining -Name 'NextScoringUnlockedStarterCount' -Value 0
    Set-FmpProperty -Object $Remaining -Name 'NextScoringOptionCount' -Value 0
}

function Set-FmpEmptyDecisionPreview {
    param([Parameter(Mandatory = $true)][object]$Remaining)

    Set-FmpProperty -Object $Remaining -Name 'NextLineupDecisionWindowID' -Value $null
    Set-FmpProperty -Object $Remaining -Name 'NextLineupDecisionGameIDs' -Value @()
    Set-FmpProperty -Object $Remaining -Name 'NextLineupDecisionPrimaryGameID' -Value $null
    Set-FmpProperty -Object $Remaining -Name 'NextLineupDecisionWindowGameCount' -Value 0
    Set-FmpProperty -Object $Remaining -Name 'NextLineupDecisionStarterCount' -Value 0
    Set-FmpProperty -Object $Remaining -Name 'NextLineupDecisionOptionCount' -Value 0
}

function Add-FantasyMatchupPreviewContext {
    param(
        [Parameter(Mandatory = $true)][object]$BaseContext,
        [Parameter(Mandatory = $true)][object]$DecisionFacts
    )

    $decisionRelevance = Get-FmpPropertyValue -Object $DecisionFacts -Names @('FantasyRelevance')
    if ($null -eq $decisionRelevance) { return $BaseContext }

    $teamStateByID = @{}
    foreach ($teamState in @(Get-FmpCollection (Get-FmpPropertyValue -Object $decisionRelevance -Names @('Teams')))) {
        $teamID = [string](Get-FmpPropertyValue -Object $teamState -Names @('FantasyTeamID'))
        if (-not [string]::IsNullOrWhiteSpace($teamID)) { $teamStateByID[$teamID] = $teamState }
    }

    foreach ($matchup in @(Get-FmpCollection (Get-FmpPropertyValue -Object $BaseContext -Names @('FantasyMatchups')))) {
        $remaining = Get-FmpPropertyValue -Object $matchup -Names @('RemainingRelevance')
        if ($null -eq $remaining) { continue }

        $paths = @()
        foreach ($teamIDValue in @(Get-FmpCollection (Get-FmpPropertyValue -Object $matchup -Names @('TeamIDs')))) {
            $teamID = [string]$teamIDValue
            if (-not $teamStateByID.ContainsKey($teamID)) { continue }

            foreach ($player in @(Get-FmpCollection (Get-FmpPropertyValue -Object $teamStateByID[$teamID] -Names @('Players')))) {
                $pathType = Get-FmpPathType -Player $player
                if ([string]::IsNullOrWhiteSpace([string]$pathType)) { continue }

                $gameID = [string](Get-FmpPropertyValue -Object $player -Names @('GameID'))
                $windowID = [string](Get-FmpPropertyValue -Object $player -Names @('DecisionWindowID'))
                $startsAtUtc = [string](Get-FmpPropertyValue -Object $player -Names @('StartsAtUtc'))
                if ([string]::IsNullOrWhiteSpace($gameID) -or [string]::IsNullOrWhiteSpace($windowID) -or [string]::IsNullOrWhiteSpace($startsAtUtc)) { continue }

                $paths += [PSCustomObject][ordered]@{
                    FantasyTeamID    = $teamID
                    PlayerID         = [string](Get-FmpPropertyValue -Object $player -Names @('PlayerID'))
                    GameID           = $gameID
                    DecisionWindowID = $windowID
                    StartsAtUtc      = $startsAtUtc
                    PathType         = $pathType
                }
            }
        }

        $windowGroups = @($paths | Group-Object DecisionWindowID | Sort-Object { [DateTimeOffset]::Parse([string]$_.Group[0].StartsAtUtc) })

        # A lineup decision exists only while a path is still unlocked. Locked-active
        # starters can still score, but the lineup decision for that player has passed.
        $decisionGroups = @($windowGroups | Where-Object {
            @($_.Group | Where-Object { $_.PathType -eq 'unlocked-starter' -or $_.PathType -eq 'bench-candidate' }).Count -gt 0
        })
        $decisionGroup = if ($decisionGroups.Count -gt 0) { $decisionGroups[0] } else { $null }

        if ($null -eq $decisionGroup) {
            Set-FmpEmptyDecisionPreview -Remaining $remaining
        }
        else {
            $decisionPaths = @($decisionGroup.Group | Where-Object { $_.PathType -eq 'unlocked-starter' -or $_.PathType -eq 'bench-candidate' })
            $decisionSelection = Get-FmpPrimaryGameSelection -WindowPaths $decisionPaths -EligibleGamePathTypes @('unlocked-starter', 'bench-candidate')
            if ($null -eq $decisionSelection) {
                Set-FmpEmptyDecisionPreview -Remaining $remaining
            }
            else {
                Set-FmpProperty -Object $remaining -Name 'NextLineupDecisionWindowID' -Value ([string]$decisionGroup.Name)
                Set-FmpProperty -Object $remaining -Name 'NextLineupDecisionGameIDs' -Value @($decisionSelection.GameIDs)
                Set-FmpProperty -Object $remaining -Name 'NextLineupDecisionPrimaryGameID' -Value $decisionSelection.PrimaryGameID
                Set-FmpProperty -Object $remaining -Name 'NextLineupDecisionWindowGameCount' -Value @($decisionSelection.GameIDs).Count
                Set-FmpProperty -Object $remaining -Name 'NextLineupDecisionStarterCount' -Value @($decisionSelection.PrimaryPaths | Where-Object PathType -eq 'unlocked-starter').Count
                Set-FmpProperty -Object $remaining -Name 'NextLineupDecisionOptionCount' -Value @($decisionSelection.PrimaryPaths | Where-Object PathType -eq 'bench-candidate').Count
            }
        }

        # Scoring preview means a current direct starter path. An option-only window
        # remains relevant to lineup decisions but must not be labeled as scoring.
        $lockedGroups = @($windowGroups | Where-Object { @($_.Group | Where-Object PathType -eq 'locked-starter').Count -gt 0 })
        $unlockedStarterGroups = @($windowGroups | Where-Object { @($_.Group | Where-Object PathType -eq 'unlocked-starter').Count -gt 0 })
        $scoringGroup = if ($lockedGroups.Count -gt 0) {
            $lockedGroups[0]
        }
        elseif ($unlockedStarterGroups.Count -gt 0) {
            $unlockedStarterGroups[0]
        }
        else {
            $null
        }

        if ($null -eq $scoringGroup) {
            Set-FmpEmptyScoringPreview -Remaining $remaining
            continue
        }

        $scoringSelection = Get-FmpPrimaryGameSelection -WindowPaths @($scoringGroup.Group) -EligibleGamePathTypes @('locked-starter', 'unlocked-starter')
        if ($null -eq $scoringSelection) {
            Set-FmpEmptyScoringPreview -Remaining $remaining
            continue
        }

        Set-FmpProperty -Object $remaining -Name 'NextScoringWindowID' -Value ([string]$scoringGroup.Name)
        Set-FmpProperty -Object $remaining -Name 'NextScoringGameIDs' -Value @($scoringSelection.GameIDs)
        Set-FmpProperty -Object $remaining -Name 'NextScoringPrimaryGameID' -Value $scoringSelection.PrimaryGameID
        Set-FmpProperty -Object $remaining -Name 'NextScoringWindowGameCount' -Value @($scoringSelection.GameIDs).Count
        Set-FmpProperty -Object $remaining -Name 'NextScoringLockedActiveStarterCount' -Value @($scoringSelection.PrimaryPaths | Where-Object PathType -eq 'locked-starter').Count
        Set-FmpProperty -Object $remaining -Name 'NextScoringUnlockedStarterCount' -Value @($scoringSelection.PrimaryPaths | Where-Object PathType -eq 'unlocked-starter').Count
        Set-FmpProperty -Object $remaining -Name 'NextScoringOptionCount' -Value @($scoringGroup.Group | Where-Object { $_.GameID -eq $scoringSelection.PrimaryGameID -and $_.PathType -eq 'bench-candidate' }).Count
    }

    return $BaseContext
}

Export-ModuleMember -Function Add-FantasyMatchupPreviewContext
