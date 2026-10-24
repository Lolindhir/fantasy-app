Import-Module "$PSScriptRoot\..\general\NflTeamRegistryUtils.psm1" -ErrorAction Stop -Force
. "$PSScriptRoot\FantasyGameContextCore.ps1"
Import-Module "$PSScriptRoot\FantasyRelevanceV2Utils.psm1" -ErrorAction Stop -Force
Import-Module "$PSScriptRoot\PlayerScoringAvailabilityUtils.psm1" -ErrorAction Stop -Force
Import-Module "$PSScriptRoot\LineupRepairabilityDecisionUtils.psm1" -ErrorAction Stop -Force
Import-Module "$PSScriptRoot\ParticipantScoringPathDecisionUtils.psm1" -ErrorAction Stop -Force
Import-Module "$PSScriptRoot\FantasyMatchupPreviewUtils.psm1" -ErrorAction Stop -Force
Import-Module "$PSScriptRoot\FantasyWeeklyWatchUtils.psm1" -ErrorAction Stop -Force

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

# The App schedule owns its display GameID; CanonicalGameID is the exact bridge
# to the league-independent NFL Game product. Markets are optional display data,
# never a replacement for the existing final NFL scores or fantasy projections.
function Add-FantasyGameMarketContext {
    param(
        [Parameter(Mandatory = $true)][object]$BaseContext,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$Schedule,
        [Parameter(Mandatory = $true)][string]$Season,
        [Parameter(Mandatory = $true)][int]$Week,
        [AllowNull()][object]$NflGameDerived = $null
    )

    $scheduleByGameID = @{}
    foreach ($row in @($Schedule)) {
        if ($null -eq $row) { continue }
        $appGameID = [string](Get-FgcPropertyValue -Object $row -Names @('gameID','GameID'))
        if ([string]::IsNullOrWhiteSpace($appGameID)) { continue }
        if ($scheduleByGameID.ContainsKey($appGameID)) {
            throw "Duplicate App schedule GameID '$appGameID' in NFL market projection."
        }
        $scheduleByGameID[$appGameID] = $row
    }

    $derivedByGameID = @{}
    if ($null -ne $NflGameDerived) {
        if ([int]$NflGameDerived.SchemaVersion -ne 1 -or [string]$NflGameDerived.Season -ne $Season -or $null -eq $NflGameDerived.Games) {
            throw "NFL Game Derived schema/season mismatch for FantasyGameContext $Season Week $Week."
        }
        foreach ($row in @($NflGameDerived.Games)) {
            $canonicalGameID = [string]$row.GameID
            if ([string]::IsNullOrWhiteSpace($canonicalGameID) -or $derivedByGameID.ContainsKey($canonicalGameID)) {
                throw "Missing or duplicate canonical GameID '$canonicalGameID' in NFL Game Derived."
            }
            $derivedByGameID[$canonicalGameID] = $row
        }
    }

    foreach ($game in @($BaseContext.Games)) {
        $market = $null
        $appGameID = [string]$game.GameID
        if ($scheduleByGameID.ContainsKey($appGameID)) {
            $canonicalGameID = [string](Get-FgcPropertyValue -Object $scheduleByGameID[$appGameID] -Names @('CanonicalGameID'))
            if (-not [string]::IsNullOrWhiteSpace($canonicalGameID) -and $derivedByGameID.ContainsKey($canonicalGameID)) {
                $derived = $derivedByGameID[$canonicalGameID]
                if ([int]$derived.Week -ne $Week -or
                    [string]$derived.AwayTeam -ne [string]$game.AwayTeamID -or
                    [string]$derived.HomeTeam -ne [string]$game.HomeTeamID) {
                    throw "NFL market identity mismatch for '$appGameID' -> '$canonicalGameID'."
                }
                if ($null -ne $derived.Market) {
                    $values = @{}
                    foreach ($field in @('SpreadLine','TotalLine','ImpliedAwayPoints','ImpliedHomePoints')) {
                        $value = Get-FgcPropertyValue -Object $derived.Market -Names @($field)
                        if ($null -ne $value) {
                            $number = ConvertTo-FgcOptionalScore $value
                            if ($null -eq $number -or [double]::IsNaN($number) -or [double]::IsInfinity($number)) {
                                throw "Invalid NFL market $field for '$canonicalGameID'."
                            }
                            $values[$field] = [double]$number
                        }
                        else { $values[$field] = $null }
                    }
                    $market = [PSCustomObject][ordered]@{
                        SpreadLine        = $values.SpreadLine
                        TotalLine         = $values.TotalLine
                        ImpliedAwayPoints = $values.ImpliedAwayPoints
                        ImpliedHomePoints = $values.ImpliedHomePoints
                    }
                }
            }
        }
        if ($game.PSObject.Properties.Name -contains 'Market') { $game.Market = $market }
        else { $game | Add-Member -NotePropertyName Market -NotePropertyValue $market }
    }

    $BaseContext.SchemaVersion = [Math]::Max(6, [int]$BaseContext.SchemaVersion)
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
        [Parameter(Mandatory = $true)][int]$LastLineupWeek,
        [AllowNull()][object]$AcquisitionCapability = $null,
        [AllowNull()][object[]]$ScoringAvailabilityObservations = @()
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

    $asOfUtc = [DateTimeOffset]::UtcNow
    $relevanceReadModel = Add-FantasyRelevanceDecisionFacts `
        -BaseReadModel $baseReadModel `
        -League $League `
        -Teams $Teams `
        -Players $Players `
        -Schedule $Schedule `
        -AsOfUtc $asOfUtc

    $availabilityReadModel = Add-PlayerScoringAvailabilityDecisionFacts `
        -BaseReadModel $relevanceReadModel `
        -Observations $ScoringAvailabilityObservations

    $repairabilityReadModel = Add-LineupRepairabilityDecisionFacts `
        -BaseReadModel $availabilityReadModel `
        -Teams $Teams `
        -Players $Players `
        -Schedule $Schedule `
        -AcquisitionCapability $AcquisitionCapability `
        -AsOfUtc $asOfUtc

    return Add-ParticipantScoringPathDecisionFacts -BaseReadModel $repairabilityReadModel
}

function New-FantasyGameContextReadModel {
    param(
        [Parameter(Mandatory = $true)][object]$LeagueID,
        [Parameter(Mandatory = $true)][string]$Season,
        [Parameter(Mandatory = $true)][int]$Week,
        [Parameter(Mandatory = $true)][object]$DecisionFacts,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$FantasyMatchups,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$Schedule,
        [Parameter(Mandatory = $true)][bool]$WeekIsFinal,
        [AllowNull()][object]$NflGameDerived = $null
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
    $scoreContext = Add-FantasyGameScoreContext -BaseContext $previewContext -Schedule $Schedule
    $weeklyContext = Add-FantasyWeeklyWatchContext -BaseContext $scoreContext
    # Historical callers intentionally retain their prior schema and do not
    # acquire today's latest-line market values retroactively.
    if ($PSBoundParameters.ContainsKey('NflGameDerived')) {
        return Add-FantasyGameMarketContext -BaseContext $weeklyContext -Schedule $Schedule `
            -Season $Season -Week $Week -NflGameDerived $NflGameDerived
    }
    return $weeklyContext
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
