function Get-FantasyTeamNeutralOrderIndex {
    param(
        [Parameter(Mandatory = $true)][array]$AllTimeOverallStandings
    )

    $entries = @()
    $seenTeamIDs = @{}
    $teamIDByPlace = @{}

    foreach ($standing in @($AllTimeOverallStandings)) {
        $teamID = [string]$standing.TeamID
        if ([string]::IsNullOrWhiteSpace($teamID)) {
            throw "All-Time Overall neutral order contains a standing without TeamID."
        }

        $place = 0
        if (-not [int]::TryParse([string]$standing.Place, [ref]$place) -or $place -le 0 -or $place -ge 999) {
            throw "Fantasy team '$teamID' has no resolved All-Time Overall place for neutral ordering."
        }

        if ($seenTeamIDs.ContainsKey($teamID)) {
            throw "Duplicate fantasy TeamID '$teamID' in All-Time Overall neutral order."
        }

        $placeKey = [string]$place
        if ($teamIDByPlace.ContainsKey($placeKey)) {
            throw "All-Time Overall neutral order is not fully resolved: place $place is shared by teams $($teamIDByPlace[$placeKey]) and $teamID."
        }

        $seenTeamIDs[$teamID] = $true
        $teamIDByPlace[$placeKey] = $teamID
        $entries += [PSCustomObject]@{
            TeamID = $teamID
            Place  = $place
        }
    }

    if ($entries.Count -eq 0) {
        throw "All-Time Overall neutral order is empty."
    }

    $index = @{}
    $position = 0
    foreach ($entry in @($entries | Sort-Object -Property Place)) {
        $index[$entry.TeamID] = $position
        $position++
    }

    return $index
}

function Get-FantasyTeamNeutralOrderPosition {
    param(
        [Parameter(Mandatory = $true)][System.Collections.IDictionary]$NeutralOrderIndex,
        [Parameter(Mandatory = $true)]$TeamID
    )

    $teamKey = [string]$TeamID
    if (-not $NeutralOrderIndex.Contains($teamKey)) {
        throw "Fantasy team '$teamKey' is missing from the resolved All-Time Overall neutral order."
    }

    return [int]$NeutralOrderIndex[$teamKey]
}
