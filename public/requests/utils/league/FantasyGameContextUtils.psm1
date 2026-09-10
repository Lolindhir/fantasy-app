. "$PSScriptRoot\FantasyGameContextCore.ps1"
Import-Module "$PSScriptRoot\FantasyRelevanceV2Utils.psm1" -ErrorAction Stop -Force
Import-Module "$PSScriptRoot\FantasyMatchupPreviewUtils.psm1" -ErrorAction Stop -Force

$script:BaseNewFantasyGameContextReadModel = ${function:New-FantasyGameContextReadModel}

function ConvertTo-FgcOptionalScore {
    param([AllowNull()][object]$Value)

    if ($null -eq $Value) { return $null }
    $text = ([string]$Value).Trim()
    if ([string]::IsNullOrWhiteSpace($text)) { return $null }

    $parsed = 0.0
    if ([double]::TryParse(
        $text,
        [System.Globalization.NumberStyles]::Float,
        [System.Globalization.CultureInfo]::InvariantCulture,
        [ref]$parsed
    )) {
        return [double]$parsed
    }
    return $null
}

function Add-FantasyGameScoreContext {
    param(
        [Parameter(Mandatory = $true)][object]$BaseContext,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$Schedule
    )

    $scheduleByGameID = @{}
    foreach ($row in @($Schedule)) {
        if ($null -eq $row) { continue }
        $gameID = [string](Get-FgcPropertyValue -Object $row -Names @('gameID','GameID'))
        if ([string]::IsNullOrWhiteSpace($gameID)) { continue }
        if ($scheduleByGameID.ContainsKey($gameID)) {
            throw "Duplicate Schedule score identity for FantasyGameContext GameID '$gameID'."
        }
        $scheduleByGameID[$gameID] = $row
    }

    foreach ($game in @($BaseContext.Games)) {
        $awayScore = $null
        $homeScore = $null
        $gameID = [string]$game.GameID
        $isFinal = [string]$game.Status -match '^Final'
        if ($isFinal -and $scheduleByGameID.ContainsKey($gameID)) {
            $scheduleRow = $scheduleByGameID[$gameID]
            $candidateAway = ConvertTo-FgcOptionalScore (Get-FgcPropertyValue -Object $scheduleRow -Names @('awayPts','AwayScore'))
            $candidateHome = ConvertTo-FgcOptionalScore (Get-FgcPropertyValue -Object $scheduleRow -Names @('homePts','HomeScore'))
            if ($null -ne $candidateAway -and $null -ne $candidateHome) {
                $awayScore = [double]$candidateAway
                $homeScore = [double]$candidateHome
            }
        }

        if ($game.PSObject.Properties.Name -contains 'AwayScore') { $game.AwayScore = $awayScore }
        else { $game | Add-Member -NotePropertyName AwayScore -NotePropertyValue $awayScore }
        if ($game.PSObject.Properties.Name -contains 'HomeScore') { $game.HomeScore = $homeScore }
        else { $game | Add-Member -NotePropertyName HomeScore -NotePropertyValue $homeScore }
    }

    if ([int]$BaseContext.SchemaVersion -lt 3) { $BaseContext.SchemaVersion = 3 }
    return $BaseContext
}

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

    $relevanceContext = Add-FantasyRelevanceContext -BaseContext $baseContext -DecisionFacts $DecisionFacts
    $previewContext = Add-FantasyMatchupPreviewContext -BaseContext $relevanceContext -DecisionFacts $DecisionFacts
    return Add-FantasyGameScoreContext -BaseContext $previewContext -Schedule $Schedule
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
