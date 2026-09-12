function Get-FwwStarterTeamIDs {
    param([Parameter(Mandatory = $true)][object]$Game)

    return @(
        @($Game.FantasyTeams) |
            Where-Object { [int]$_.StarterCount -gt 0 } |
            ForEach-Object { [string]$_.FantasyTeamID } |
            Sort-Object -Unique
    )
}

function Get-FwwStarterMatchupIDs {
    param([Parameter(Mandatory = $true)][object]$Game)

    return @(
        @($Game.FantasyTeams) |
            Where-Object { [int]$_.StarterCount -gt 0 -and -not [string]::IsNullOrWhiteSpace([string]$_.FantasyMatchupID) } |
            ForEach-Object { [string]$_.FantasyMatchupID } |
            Sort-Object -Unique
    )
}

function Get-FwwRemainingValue {
    param(
        [AllowNull()][object]$Remaining,
        [Parameter(Mandatory = $true)][string]$Name
    )

    if ($null -eq $Remaining -or $Remaining.PSObject.Properties.Name -notcontains $Name) { return 0 }
    return [int]$Remaining.$Name
}

function Add-FantasyWeeklyWatchContext {
    param([Parameter(Mandatory = $true)][object]$BaseContext)

    $candidates = @(
        @($BaseContext.Games) |
            Where-Object { [int]$_.Relevance.StarterCount -gt 0 }
    )

    foreach ($game in @($BaseContext.Games)) {
        if ($null -ne $game.RemainingRelevance) {
            $game.RemainingRelevance | Add-Member -NotePropertyName MustWatchRank -NotePropertyValue $null -Force
        }
    }

    $ranked = @(
        $candidates | Sort-Object `
            @{ Expression = { @(Get-FwwStarterTeamIDs -Game $_).Count }; Descending = $true }, `
            @{ Expression = { [int]$_.Relevance.StarterCount }; Descending = $true }, `
            @{ Expression = { @(Get-FwwStarterMatchupIDs -Game $_).Count }; Descending = $true }, `
            @{ Expression = { [string]$_.StartsAtUtc }; Descending = $false }, `
            @{ Expression = { [string]$_.GameID }; Descending = $false }
    )

    $mustWatch = @()
    for ($index = 0; $index -lt $ranked.Count; $index++) {
        $game = $ranked[$index]
        $remaining = $game.RemainingRelevance
        $starterTeamIDs = @(Get-FwwStarterTeamIDs -Game $game)
        $starterMatchupIDs = @(Get-FwwStarterMatchupIDs -Game $game)

        if ($null -ne $remaining) {
            $remaining | Add-Member -NotePropertyName MustWatchRank -NotePropertyValue ($index + 1) -Force
        }

        $mustWatch += [PSCustomObject][ordered]@{
            Rank                                = $index + 1
            GameID                              = [string]$game.GameID
            DecisionWindowID                    = [string]$game.DecisionWindowID
            StartsAtUtc                         = [string]$game.StartsAtUtc
            CommittedFinalWindowMatchupCount    = Get-FwwRemainingValue -Remaining $remaining -Name 'CommittedFinalWindowMatchupCount'
            LockedActiveStarterCount            = Get-FwwRemainingValue -Remaining $remaining -Name 'LockedActiveStarterCount'
            DirectStarterFantasyTeamCount       = $starterTeamIDs.Count
            DirectStarterFantasyTeamIDs         = $starterTeamIDs
            UnlockedStarterCount                = Get-FwwRemainingValue -Remaining $remaining -Name 'UnlockedStarterCount'
            TwoSidedFantasyMatchupCount         = Get-FwwRemainingValue -Remaining $remaining -Name 'TwoSidedFantasyMatchupCount'
            FantasyMatchupCount                 = $starterMatchupIDs.Count
            FinalWindowFantasyMatchupCount      = Get-FwwRemainingValue -Remaining $remaining -Name 'FinalWindowFantasyMatchupCount'
            EligibleBenchCandidateCount         = Get-FwwRemainingValue -Remaining $remaining -Name 'EligibleBenchCandidateCount'
        }
    }

    $BaseContext | Add-Member -NotePropertyName MustWatchGames -NotePropertyValue $mustWatch -Force
    if ($BaseContext.PSObject.Properties.Name -contains 'SchemaVersion') {
        $BaseContext.SchemaVersion = [Math]::Max(4, [int]$BaseContext.SchemaVersion)
    }
    return $BaseContext
}

Export-ModuleMember -Function Add-FantasyWeeklyWatchContext