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
        $lockedGroups = @($windowGroups | Where-Object { @($_.Group | Where-Object PathType -eq 'locked-starter').Count -gt 0 })
        $directGroups = @($windowGroups | Where-Object { @($_.Group | Where-Object { $_.PathType -eq 'locked-starter' -or $_.PathType -eq 'unlocked-starter' }).Count -gt 0 })

        $nextGroup = if ($lockedGroups.Count -gt 0) {
            $lockedGroups[0]
        }
        elseif ($directGroups.Count -gt 0) {
            $directGroups[0]
        }
        elseif ($windowGroups.Count -gt 0) {
            $windowGroups[0]
        }
        else {
            $null
        }

        if ($null -eq $nextGroup) {
            Set-FmpProperty -Object $remaining -Name 'NextScoringWindowID' -Value $null
            Set-FmpProperty -Object $remaining -Name 'NextScoringGameIDs' -Value @()
            Set-FmpProperty -Object $remaining -Name 'NextScoringPrimaryGameID' -Value $null
            Set-FmpProperty -Object $remaining -Name 'NextScoringWindowGameCount' -Value 0
            Set-FmpProperty -Object $remaining -Name 'NextScoringLockedActiveStarterCount' -Value 0
            Set-FmpProperty -Object $remaining -Name 'NextScoringUnlockedStarterCount' -Value 0
            Set-FmpProperty -Object $remaining -Name 'NextScoringOptionCount' -Value 0
            continue
        }

        $nextGameIDs = @($nextGroup.Group | Select-Object -ExpandProperty GameID -Unique | Sort-Object)
        $primaryGameGroup = @(
            $nextGroup.Group |
                Group-Object GameID |
                Sort-Object `
                    @{ Expression = { @($_.Group | Where-Object { $_.PathType -eq 'locked-starter' -or $_.PathType -eq 'unlocked-starter' }).Count }; Descending = $true }, `
                    @{ Expression = { @($_.Group | Where-Object PathType -eq 'locked-starter').Count }; Descending = $true }, `
                    @{ Expression = { @($_.Group | Where-Object PathType -eq 'bench-candidate').Count }; Descending = $true }, `
                    @{ Expression = { [string]$_.Name }; Descending = $false }
        )[0]
        $primaryGameID = if ($null -ne $primaryGameGroup) { [string]$primaryGameGroup.Name } else { $null }
        $primaryPaths = if ($null -ne $primaryGameID) { @($nextGroup.Group | Where-Object GameID -eq $primaryGameID) } else { @() }

        Set-FmpProperty -Object $remaining -Name 'NextScoringWindowID' -Value ([string]$nextGroup.Name)
        Set-FmpProperty -Object $remaining -Name 'NextScoringGameIDs' -Value $nextGameIDs
        Set-FmpProperty -Object $remaining -Name 'NextScoringPrimaryGameID' -Value $primaryGameID
        Set-FmpProperty -Object $remaining -Name 'NextScoringWindowGameCount' -Value $nextGameIDs.Count
        Set-FmpProperty -Object $remaining -Name 'NextScoringLockedActiveStarterCount' -Value @($primaryPaths | Where-Object PathType -eq 'locked-starter').Count
        Set-FmpProperty -Object $remaining -Name 'NextScoringUnlockedStarterCount' -Value @($primaryPaths | Where-Object PathType -eq 'unlocked-starter').Count
        Set-FmpProperty -Object $remaining -Name 'NextScoringOptionCount' -Value @($primaryPaths | Where-Object PathType -eq 'bench-candidate').Count
    }

    return $BaseContext
}

Export-ModuleMember -Function Add-FantasyMatchupPreviewContext
