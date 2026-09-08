. "$PSScriptRoot\FantasyGameContextCore.ps1"
Import-Module "$PSScriptRoot\FantasyRelevanceV2Utils.psm1" -ErrorAction Stop -Force

$script:BaseNewFantasyGameContextReadModel = ${function:New-FantasyGameContextReadModel}

# RequestLeague imports DecisionWindowUtils before this module. This compatibility
# wrapper enriches the stable DecisionWindows baseline with the v2 lineup model
# without moving the existing exact-kickoff derivation into Angular.
function New-CurrentLeagueDecisionWindowsReadModel {
    param(
        [Parameter(Mandatory = $true)][object]$League,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$Teams,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$Players,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$Schedule,
        [Parameter(Mandatory = $true)][int]$LastLineupWeek
    )

    $baseReadModel = DecisionWindowUtils\New-CurrentLeagueDecisionWindowsReadModel `
        -League $League `
        -Teams $Teams `
        -Players $Players `
        -Schedule $Schedule `
        -LastLineupWeek $LastLineupWeek

    if ([int]$baseReadModel.LineupWeek -lt 1 -or [int]$baseReadModel.LineupWeek -gt [int]$baseReadModel.LastLineupWeek) {
        return $baseReadModel
    }

    return Add-FantasyRelevanceDecisionFacts `
        -BaseReadModel $baseReadModel `
        -League $League `
        -Teams $Teams `
        -Players $Players `
        -Schedule $Schedule
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

    $baseContext = & $script:BaseNewFantasyGameContextReadModel `
        -LeagueID $LeagueID `
        -Season $Season `
        -Week $Week `
        -DecisionFacts $DecisionFacts `
        -FantasyMatchups $FantasyMatchups `
        -Schedule $Schedule `
        -WeekIsFinal $WeekIsFinal

    return Add-FantasyRelevanceContext -BaseContext $baseContext -DecisionFacts $DecisionFacts
}

# Sleeper currently publishes players_points as a PlayerID-keyed object but
# starters_points as a positional array aligned with starters. The current
# FantasyGameContext adapter uses players_points as the authoritative per-player
# league-scored source, so positional arrays must not be interpreted as object
# property maps. Returning an empty map here intentionally activates the
# existing starter fallback from players_points.
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

    if ($Value -is [System.Collections.IEnumerable] -and $Value -isnot [string]) {
        return $map
    }

    foreach ($property in @($Value.PSObject.Properties)) {
        if ($null -ne $property.Value) { $map[[string]$property.Name] = [double]$property.Value }
    }
    return $map
}
