# ===========================================================================
# Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\..\ConfigUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\general\ArrayUtils.psm1" -ErrorAction Stop -Force
}
catch {
    Write-Error "Fehler beim Laden der Module: $_"
    throw $_
}

# ===========================================================================
# Canonical current Playoff shadow consumer
# ===========================================================================

function Get-CanonicalPlayoffRepoRoot {
    return (Resolve-Path (Join-Path $PSScriptRoot "../../../..")).Path
}

function Get-CanonicalPlayoffPropertyValue {
    param(
        [AllowNull()]$Object,
        [Parameter(Mandatory = $true)][string]$PropertyName,
        [AllowNull()]$DefaultValue = $null
    )

    if ($null -eq $Object) { return $DefaultValue }
    $property = $Object.PSObject.Properties[$PropertyName]
    if ($null -eq $property) { return $DefaultValue }
    return $property.Value
}

function Get-CanonicalPlayoffJson {
    param(
        [Parameter(Mandatory = $true)][string]$CanonicalLeagueID,
        [Parameter(Mandatory = $true)][string]$Season,
        [Parameter(Mandatory = $true)][string]$FileName
    )

    $repoRoot = Get-CanonicalPlayoffRepoRoot
    $path = Join-Path $repoRoot "source-data/leagues/$CanonicalLeagueID/seasons/$Season/$FileName"
    if (-not (Test-Path $path)) {
        throw "Canonical Playoff source '$FileName' missing for $CanonicalLeagueID/$Season at '$path'."
    }

    try {
        $raw = Get-Content $path -Raw
        if ([string]::IsNullOrWhiteSpace($raw)) {
            throw "Canonical Playoff source '$FileName' is empty for $CanonicalLeagueID/$Season."
        }
        return $raw | ConvertFrom-Json
    }
    catch {
        throw "Could not read canonical Playoff source '$path'. $_"
    }
}

function New-CanonicalPlayoffRosterLookup {
    param(
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$Rosters
    )

    $lookup = @{}
    $providerIDs = @{}

    foreach ($roster in $Rosters) {
        $canonicalRosterID = [string](Get-CanonicalPlayoffPropertyValue -Object $roster -PropertyName "CanonicalLeagueRosterID" -DefaultValue "")
        if ([string]::IsNullOrWhiteSpace($canonicalRosterID)) {
            throw "Canonical Playoff roster is missing CanonicalLeagueRosterID."
        }
        if ($lookup.ContainsKey($canonicalRosterID)) {
            throw "Canonical Playoff rosters contain duplicate CanonicalLeagueRosterID '$canonicalRosterID'."
        }

        $mappings = @(
            ConvertTo-SafeArray -value $roster.ProviderMappings |
                Where-Object { [string]$_.Provider -eq "Sleeper" }
        )
        if ($mappings.Count -ne 1) {
            throw "Canonical Playoff roster '$canonicalRosterID' must have exactly one Sleeper provider mapping; found $($mappings.Count)."
        }

        $providerRosterID = [string](Get-CanonicalPlayoffPropertyValue -Object $mappings[0] -PropertyName "ProviderRosterID" -DefaultValue "")
        if ([string]::IsNullOrWhiteSpace($providerRosterID)) {
            throw "Canonical Playoff roster '$canonicalRosterID' Sleeper mapping is missing ProviderRosterID."
        }
        if ($providerIDs.ContainsKey($providerRosterID)) {
            throw "Canonical Playoff rosters contain duplicate Sleeper ProviderRosterID '$providerRosterID'."
        }

        $lookup[$canonicalRosterID] = [int]$providerRosterID
        $providerIDs[$providerRosterID] = $canonicalRosterID
    }

    return $lookup
}

function Resolve-CanonicalPlayoffProviderRosterID {
    param(
        [AllowNull()][string]$CanonicalRosterID,
        [Parameter(Mandatory = $true)][hashtable]$RosterLookup
    )

    if ([string]::IsNullOrWhiteSpace($CanonicalRosterID)) {
        return $null
    }
    if (-not $RosterLookup.ContainsKey($CanonicalRosterID)) {
        throw "Canonical Playoff bracket references unknown roster '$CanonicalRosterID'."
    }
    return [int]$RosterLookup[$CanonicalRosterID]
}

function ConvertTo-CanonicalPlayoffLegacySource {
    param(
        [AllowNull()]$Source,
        [Parameter(Mandatory = $true)][hashtable]$MatchRounds,
        [Parameter(Mandatory = $true)][int]$CurrentRound,
        [Parameter(Mandatory = $true)][int]$CurrentMatch,
        [Parameter(Mandatory = $true)][string]$SourceLabel
    )

    if ($null -eq $Source) { return $null }

    $outcome = [string](Get-CanonicalPlayoffPropertyValue -Object $Source -PropertyName "Outcome" -DefaultValue "")
    $matchValue = Get-CanonicalPlayoffPropertyValue -Object $Source -PropertyName "Match" -DefaultValue $null
    $sourceMatch = 0
    if (-not [int]::TryParse([string]$matchValue, [ref]$sourceMatch) -or $sourceMatch -lt 1) {
        throw "$SourceLabel must contain a positive numeric Match."
    }
    if ($outcome -notin @("Winner", "Loser")) {
        throw "$SourceLabel has unsupported Outcome '$outcome'."
    }
    if (-not $MatchRounds.ContainsKey([string]$sourceMatch)) {
        throw "$SourceLabel references unknown match '$sourceMatch'."
    }

    $sourceRound = [int]$MatchRounds[[string]$sourceMatch]
    if ($sourceMatch -eq $CurrentMatch -or $sourceRound -ge $CurrentRound) {
        throw "$SourceLabel must reference an earlier-round match."
    }

    if ($outcome -eq "Winner") {
        return [PSCustomObject][ordered]@{ w = $sourceMatch }
    }
    return [PSCustomObject][ordered]@{ l = $sourceMatch }
}

function ConvertTo-CanonicalPlayoffLegacyBracket {
    param(
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$Matches,
        [Parameter(Mandatory = $true)][hashtable]$RosterLookup,
        [Parameter(Mandatory = $true)][string]$BracketLabel
    )

    $matchRounds = @{}
    foreach ($match in $Matches) {
        $round = 0
        $matchNumber = 0
        if (-not [int]::TryParse([string](Get-CanonicalPlayoffPropertyValue -Object $match -PropertyName "Round" -DefaultValue $null), [ref]$round) -or $round -lt 1) {
            throw "Canonical $BracketLabel bracket contains invalid Round."
        }
        if (-not [int]::TryParse([string](Get-CanonicalPlayoffPropertyValue -Object $match -PropertyName "Match" -DefaultValue $null), [ref]$matchNumber) -or $matchNumber -lt 1) {
            throw "Canonical $BracketLabel bracket contains invalid Match."
        }
        $key = [string]$matchNumber
        if ($matchRounds.ContainsKey($key)) {
            throw "Canonical $BracketLabel bracket contains duplicate Match '$matchNumber'."
        }
        $matchRounds[$key] = $round
    }

    foreach ($match in @($Matches | Sort-Object { [int]$_.Round }, { [int]$_.Match })) {
        $round = [int]$match.Round
        $matchNumber = [int]$match.Match
        $team1 = Resolve-CanonicalPlayoffProviderRosterID -CanonicalRosterID ([string](Get-CanonicalPlayoffPropertyValue -Object $match -PropertyName "Team1CanonicalLeagueRosterID" -DefaultValue "")) -RosterLookup $RosterLookup
        $team2 = Resolve-CanonicalPlayoffProviderRosterID -CanonicalRosterID ([string](Get-CanonicalPlayoffPropertyValue -Object $match -PropertyName "Team2CanonicalLeagueRosterID" -DefaultValue "")) -RosterLookup $RosterLookup
        $winner = Resolve-CanonicalPlayoffProviderRosterID -CanonicalRosterID ([string](Get-CanonicalPlayoffPropertyValue -Object $match -PropertyName "WinnerCanonicalLeagueRosterID" -DefaultValue "")) -RosterLookup $RosterLookup
        $loser = Resolve-CanonicalPlayoffProviderRosterID -CanonicalRosterID ([string](Get-CanonicalPlayoffPropertyValue -Object $match -PropertyName "LoserCanonicalLeagueRosterID" -DefaultValue "")) -RosterLookup $RosterLookup

        $legacy = [ordered]@{
            m  = $matchNumber
            r  = $round
            l  = $loser
            w  = $winner
            t1 = $team1
            t2 = $team2
        }

        $placement = Get-CanonicalPlayoffPropertyValue -Object $match -PropertyName "Placement" -DefaultValue $null
        if ($null -ne $placement) {
            $legacy["p"] = $placement
        }

        $team1Source = ConvertTo-CanonicalPlayoffLegacySource -Source (Get-CanonicalPlayoffPropertyValue -Object $match -PropertyName "Team1Source" -DefaultValue $null) -MatchRounds $matchRounds -CurrentRound $round -CurrentMatch $matchNumber -SourceLabel "Canonical $BracketLabel match $matchNumber Team1Source"
        if ($null -ne $team1Source) {
            $legacy["t1_from"] = $team1Source
        }

        $team2Source = ConvertTo-CanonicalPlayoffLegacySource -Source (Get-CanonicalPlayoffPropertyValue -Object $match -PropertyName "Team2Source" -DefaultValue $null) -MatchRounds $matchRounds -CurrentRound $round -CurrentMatch $matchNumber -SourceLabel "Canonical $BracketLabel match $matchNumber Team2Source"
        if ($null -ne $team2Source) {
            $legacy["t2_from"] = $team2Source
        }

        Write-Output ([PSCustomObject]$legacy)
    }
}

function Get-CanonicalCurrentPlayoffs {
    param(
        [string]$CanonicalLeagueID = "nfl-reise"
    )

    $season = [string](Get-Config).LeagueYear
    $rosters = @(ConvertTo-SafeArray -value (Get-CanonicalPlayoffJson -CanonicalLeagueID $CanonicalLeagueID -Season $season -FileName "rosters.json"))
    $winnersMatches = @(ConvertTo-SafeArray -value (Get-CanonicalPlayoffJson -CanonicalLeagueID $CanonicalLeagueID -Season $season -FileName "winners-bracket.json"))
    $losersMatches = @(ConvertTo-SafeArray -value (Get-CanonicalPlayoffJson -CanonicalLeagueID $CanonicalLeagueID -Season $season -FileName "losers-bracket.json"))

    if ($winnersMatches.Count -eq 0 -and $losersMatches.Count -eq 0) {
        return $null
    }

    $rosterLookup = New-CanonicalPlayoffRosterLookup -Rosters $rosters
    $winners = ConvertTo-CanonicalPlayoffLegacyBracket -Matches $winnersMatches -RosterLookup $rosterLookup -BracketLabel "winners"
    $losers = ConvertTo-CanonicalPlayoffLegacyBracket -Matches $losersMatches -RosterLookup $rosterLookup -BracketLabel "losers"

    if ($winnersMatches.Count -eq 0) { $winners = @() }
    if ($losersMatches.Count -eq 0) { $losers = @() }

    return [PSCustomObject][ordered]@{
        WinnersBracket = $winners
        LosersBracket  = $losers
    }
}

Export-ModuleMember -Function @(
    "Get-CanonicalCurrentPlayoffs"
)
