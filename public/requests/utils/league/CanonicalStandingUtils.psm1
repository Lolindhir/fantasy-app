# ===========================================================================
# Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\..\ConfigUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\general\ArrayUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\general\ProviderJoinUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\StandingUtils.psm1" -ErrorAction Stop -Force
}
catch {
    Write-Error "Fehler beim Laden der Module: $_"
    throw $_
}

# ===========================================================================
# Canonical standings consumer
# ===========================================================================

function Get-CanonicalStandingRepoRoot {
    return (Resolve-Path (Join-Path $PSScriptRoot "../../../..")).Path
}

function Get-CanonicalStandingPropertyValue {
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

function Get-CanonicalStandingSeasonDirectory {
    param(
        [Parameter(Mandatory = $true)][string]$CanonicalLeagueID,
        [Parameter(Mandatory = $true)][string]$Season
    )

    $repoRoot = Get-CanonicalStandingRepoRoot
    $leagueRoot = Join-Path $repoRoot "source-data/leagues/$CanonicalLeagueID"
    $seasonDirectory = Join-Path $leagueRoot "seasons/$Season"
    if (-not (Test-Path $seasonDirectory)) {
        throw "Canonical League season directory missing at '$seasonDirectory'."
    }

    return $seasonDirectory
}

function Get-CanonicalStandingJson {
    param(
        [Parameter(Mandatory = $true)][string]$CanonicalLeagueID,
        [Parameter(Mandatory = $true)][string]$Season,
        [Parameter(Mandatory = $true)][string]$FileName
    )

    $seasonDirectory = Get-CanonicalStandingSeasonDirectory -CanonicalLeagueID $CanonicalLeagueID -Season $Season
    $path = Join-Path $seasonDirectory $FileName
    if (-not (Test-Path $path)) {
        throw "Canonical standings source '$FileName' missing for $CanonicalLeagueID/$Season."
    }

    try {
        $raw = Get-Content $path -Raw
        if ([string]::IsNullOrWhiteSpace($raw)) {
            throw "Canonical standings source '$FileName' is empty for $CanonicalLeagueID/$Season."
        }
        return $raw | ConvertFrom-Json
    }
    catch {
        throw "Could not read canonical standings source '$path'. $_"
    }
}

function Get-CanonicalStandingSleeperMappingValue {
    param(
        [AllowNull()]$Mappings,
        [Parameter(Mandatory = $true)][string]$PropertyName,
        [Parameter(Mandatory = $true)][string]$SourceLabel
    )

    $matches = @(
        ConvertTo-SafeArray -value $Mappings |
            Where-Object { [string]$_.Provider -eq "Sleeper" }
    )

    if ($matches.Count -ne 1) {
        throw "$SourceLabel must have exactly one Sleeper provider mapping; found $($matches.Count)."
    }

    $value = [string](Get-CanonicalStandingPropertyValue -Object $matches[0] -PropertyName $PropertyName -DefaultValue "")
    if ([string]::IsNullOrWhiteSpace($value)) {
        throw "$SourceLabel Sleeper provider mapping is missing '$PropertyName'."
    }

    return $value
}

function New-CanonicalStandingSourceLookups {
    param(
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$Members,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$Rosters
    )

    $memberSources = @()
    foreach ($member in $Members) {
        $canonicalMemberID = [string](Get-CanonicalStandingPropertyValue -Object $member -PropertyName "CanonicalLeagueMemberID" -DefaultValue "")
        if ([string]::IsNullOrWhiteSpace($canonicalMemberID)) {
            throw "Canonical standings member is missing CanonicalLeagueMemberID."
        }

        $providerUserID = Get-CanonicalStandingSleeperMappingValue -Mappings $member.ProviderMappings -PropertyName "ProviderUserID" -SourceLabel "Canonical member '$canonicalMemberID'"
        $memberSources += [PSCustomObject][ordered]@{
            CanonicalLeagueMemberID = $canonicalMemberID
            ProviderUserID          = $providerUserID
            Source                  = $member
        }
    }

    $rosterSources = @()
    foreach ($roster in $Rosters) {
        $canonicalRosterID = [string](Get-CanonicalStandingPropertyValue -Object $roster -PropertyName "CanonicalLeagueRosterID" -DefaultValue "")
        if ([string]::IsNullOrWhiteSpace($canonicalRosterID)) {
            throw "Canonical standings roster is missing CanonicalLeagueRosterID."
        }

        $canonicalMemberID = [string](Get-CanonicalStandingPropertyValue -Object $roster -PropertyName "CanonicalLeagueMemberID" -DefaultValue "")
        if ([string]::IsNullOrWhiteSpace($canonicalMemberID)) {
            throw "Canonical roster '$canonicalRosterID' is missing CanonicalLeagueMemberID."
        }

        $providerRosterID = Get-CanonicalStandingSleeperMappingValue -Mappings $roster.ProviderMappings -PropertyName "ProviderRosterID" -SourceLabel "Canonical roster '$canonicalRosterID'"
        $providerOwnerUserID = [string](Get-CanonicalStandingPropertyValue -Object $roster -PropertyName "ProviderOwnerUserID" -DefaultValue "")
        if ([string]::IsNullOrWhiteSpace($providerOwnerUserID)) {
            throw "Canonical roster '$canonicalRosterID' is missing ProviderOwnerUserID."
        }

        $rosterSources += [PSCustomObject][ordered]@{
            CanonicalLeagueRosterID = $canonicalRosterID
            CanonicalLeagueMemberID = $canonicalMemberID
            ProviderRosterID        = $providerRosterID
            ProviderOwnerUserID     = $providerOwnerUserID
            Source                  = $roster
        }
    }

    $membersByCanonicalID = New-UniqueObjectLookup -Items $memberSources -KeyProperty "CanonicalLeagueMemberID" -SourceLabel "canonical standings members" -KeyLabel "CanonicalLeagueMemberID" -DescriptionProperties @("CanonicalLeagueMemberID", "ProviderUserID")
    $membersByProviderID = New-UniqueObjectLookup -Items $memberSources -KeyProperty "ProviderUserID" -SourceLabel "canonical standings member provider mappings" -KeyLabel "ProviderUserID" -DescriptionProperties @("CanonicalLeagueMemberID", "ProviderUserID")
    $rostersByCanonicalID = New-UniqueObjectLookup -Items $rosterSources -KeyProperty "CanonicalLeagueRosterID" -SourceLabel "canonical standings rosters" -KeyLabel "CanonicalLeagueRosterID" -DescriptionProperties @("CanonicalLeagueRosterID", "ProviderRosterID", "ProviderOwnerUserID")
    $rostersByProviderID = New-UniqueObjectLookup -Items $rosterSources -KeyProperty "ProviderRosterID" -SourceLabel "canonical standings roster provider mappings" -KeyLabel "ProviderRosterID" -DescriptionProperties @("CanonicalLeagueRosterID", "ProviderRosterID", "ProviderOwnerUserID")
    $rostersByOwnerID = New-UniqueObjectLookup -Items $rosterSources -KeyProperty "ProviderOwnerUserID" -SourceLabel "canonical standings roster owners" -KeyLabel "ProviderOwnerUserID" -DescriptionProperties @("CanonicalLeagueRosterID", "ProviderRosterID", "ProviderOwnerUserID")

    foreach ($rosterSource in $rosterSources) {
        if (-not $membersByCanonicalID.ContainsKey([string]$rosterSource.CanonicalLeagueMemberID)) {
            throw "Canonical roster '$($rosterSource.CanonicalLeagueRosterID)' references unknown CanonicalLeagueMemberID '$($rosterSource.CanonicalLeagueMemberID)'."
        }

        $memberSource = $membersByCanonicalID[[string]$rosterSource.CanonicalLeagueMemberID]
        if ([string]$memberSource.ProviderUserID -ne [string]$rosterSource.ProviderOwnerUserID) {
            throw "Canonical roster '$($rosterSource.CanonicalLeagueRosterID)' owner mapping '$($rosterSource.ProviderOwnerUserID)' does not match member provider mapping '$($memberSource.ProviderUserID)'."
        }
    }

    return [PSCustomObject][ordered]@{
        MembersByCanonicalID = $membersByCanonicalID
        MembersByProviderID  = $membersByProviderID
        RostersByCanonicalID = $rostersByCanonicalID
        RostersByProviderID  = $rostersByProviderID
        RostersByOwnerID     = $rostersByOwnerID
    }
}

function Get-CanonicalStandingTeamData {
    param(
        [Parameter(Mandatory = $true)][object]$SourceLookups
    )

    $teamData = @()

    foreach ($rosterSource in @($SourceLookups.RostersByCanonicalID.Values | Sort-Object { [int]$_.ProviderRosterID })) {
        $memberSource = $SourceLookups.MembersByCanonicalID[[string]$rosterSource.CanonicalLeagueMemberID]
        $member = $memberSource.Source
        $roster = $rosterSource.Source

        $owner = [string](Get-CanonicalStandingPropertyValue -Object $member -PropertyName "DisplayName" -DefaultValue "")
        if ([string]::IsNullOrWhiteSpace($owner)) {
            throw "Canonical member '$($memberSource.CanonicalLeagueMemberID)' is missing DisplayName."
        }

        $teamName = [string](Get-CanonicalStandingPropertyValue -Object $member.Metadata -PropertyName "team_name" -DefaultValue "")
        if ([string]::IsNullOrWhiteSpace($teamName)) {
            $teamName = "Team $owner"
        }
        else {
            $teamName = $teamName.Trim()
        }

        $wholePoints = [double](Get-CanonicalStandingPropertyValue -Object $roster.Settings -PropertyName "fpts" -DefaultValue 0)
        $pointDecimals = [double](Get-CanonicalStandingPropertyValue -Object $roster.Settings -PropertyName "fpts_decimal" -DefaultValue 0)
        $wholePointsAgainst = [double](Get-CanonicalStandingPropertyValue -Object $roster.Settings -PropertyName "fpts_against" -DefaultValue 0)
        $pointAgainstDecimals = [double](Get-CanonicalStandingPropertyValue -Object $roster.Settings -PropertyName "fpts_against_decimal" -DefaultValue 0)

        $teamData += [PSCustomObject][ordered]@{
            Owner         = $owner
            Team          = $teamName
            TeamID        = [int]$rosterSource.ProviderRosterID
            PlaceRegular  = 0
            PlacePlayoffs = 0
            Points        = [double]($wholePoints + ($pointDecimals / 100.0))
            PointsAgainst = [double]($wholePointsAgainst + ($pointAgainstDecimals / 100.0))
            Wins          = [int](Get-CanonicalStandingPropertyValue -Object $roster.Settings -PropertyName "wins" -DefaultValue 0)
            Losses        = [int](Get-CanonicalStandingPropertyValue -Object $roster.Settings -PropertyName "losses" -DefaultValue 0)
            Ties          = [int](Get-CanonicalStandingPropertyValue -Object $roster.Settings -PropertyName "ties" -DefaultValue 0)
            Record        = [string](Get-CanonicalStandingPropertyValue -Object $roster.Metadata -PropertyName "record" -DefaultValue "")
            Streak        = [string](Get-CanonicalStandingPropertyValue -Object $roster.Metadata -PropertyName "streak" -DefaultValue "")
        }
    }

    return @($teamData)
}

function Resolve-CanonicalStandingProviderRosterID {
    param(
        [AllowNull()][string]$CanonicalRosterID,
        [Parameter(Mandatory = $true)][object]$SourceLookups,
        [switch]$AllowNull
    )

    if ([string]::IsNullOrWhiteSpace($CanonicalRosterID)) {
        if ($AllowNull) { return $null }
        throw "Canonical bracket roster reference is missing."
    }

    if (-not $SourceLookups.RostersByCanonicalID.ContainsKey($CanonicalRosterID)) {
        throw "Canonical bracket references unknown roster '$CanonicalRosterID'."
    }

    return [int]$SourceLookups.RostersByCanonicalID[$CanonicalRosterID].ProviderRosterID
}

function ConvertTo-CanonicalStandingLegacyBracket {
    param(
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$Matches,
        [Parameter(Mandatory = $true)][object]$SourceLookups
    )

    $result = @()
    foreach ($match in $Matches) {
        $team1 = Resolve-CanonicalStandingProviderRosterID -CanonicalRosterID ([string](Get-CanonicalStandingPropertyValue -Object $match -PropertyName "Team1CanonicalLeagueRosterID" -DefaultValue "")) -SourceLookups $SourceLookups -AllowNull
        $team2 = Resolve-CanonicalStandingProviderRosterID -CanonicalRosterID ([string](Get-CanonicalStandingPropertyValue -Object $match -PropertyName "Team2CanonicalLeagueRosterID" -DefaultValue "")) -SourceLookups $SourceLookups -AllowNull
        $winner = Resolve-CanonicalStandingProviderRosterID -CanonicalRosterID ([string](Get-CanonicalStandingPropertyValue -Object $match -PropertyName "WinnerCanonicalLeagueRosterID" -DefaultValue "")) -SourceLookups $SourceLookups -AllowNull
        $loser = Resolve-CanonicalStandingProviderRosterID -CanonicalRosterID ([string](Get-CanonicalStandingPropertyValue -Object $match -PropertyName "LoserCanonicalLeagueRosterID" -DefaultValue "")) -SourceLookups $SourceLookups -AllowNull

        $result += [PSCustomObject][ordered]@{
            r  = Get-CanonicalStandingPropertyValue -Object $match -PropertyName "Round" -DefaultValue $null
            m  = Get-CanonicalStandingPropertyValue -Object $match -PropertyName "Match" -DefaultValue $null
            t1 = $team1
            t2 = $team2
            w  = $winner
            l  = $loser
            p  = Get-CanonicalStandingPropertyValue -Object $match -PropertyName "Placement" -DefaultValue $null
        }
    }

    return @($result)
}

function Get-CanonicalStandingSourceForSeason {
    param(
        [string]$CanonicalLeagueID = "nfl-reise",
        [Parameter(Mandatory = $true)][string]$Season,
        [switch]$AllowActiveSeason
    )

    $league = Get-CanonicalStandingJson -CanonicalLeagueID $CanonicalLeagueID -Season $Season -FileName "league.json"
    $members = @(ConvertTo-SafeArray -value (Get-CanonicalStandingJson -CanonicalLeagueID $CanonicalLeagueID -Season $Season -FileName "members.json"))
    $rosters = @(ConvertTo-SafeArray -value (Get-CanonicalStandingJson -CanonicalLeagueID $CanonicalLeagueID -Season $Season -FileName "rosters.json"))
    $winnersBracket = @(ConvertTo-SafeArray -value (Get-CanonicalStandingJson -CanonicalLeagueID $CanonicalLeagueID -Season $Season -FileName "winners-bracket.json"))
    $losersBracket = @(ConvertTo-SafeArray -value (Get-CanonicalStandingJson -CanonicalLeagueID $CanonicalLeagueID -Season $Season -FileName "losers-bracket.json"))

    if ([string]$league.Season -ne [string]$Season) {
        throw "Canonical standings season mismatch: requested '$Season', league.json contains '$($league.Season)'."
    }
    if ([string]$league.Status -ne "complete") {
        $configuredCurrentSeason = [string](Get-Config).LeagueYear
        if (-not $AllowActiveSeason) {
            throw "Canonical historical standings only accept completed seasons; $CanonicalLeagueID/$Season has status '$($league.Status)'."
        }
        if ([string]$Season -ne $configuredCurrentSeason) {
            throw "Canonical active standings only accept the configured current season '$configuredCurrentSeason'; requested '$Season' has status '$($league.Status)'."
        }
    }

    $playoffStartWeek = [int](Get-CanonicalStandingPropertyValue -Object $league.Settings -PropertyName "playoff_week_start" -DefaultValue 0)
    if ($playoffStartWeek -le 1) {
        throw "Canonical standings source for $CanonicalLeagueID/$Season has invalid playoff_week_start '$playoffStartWeek'."
    }

    $sourceLookups = New-CanonicalStandingSourceLookups -Members $members -Rosters $rosters
    $teamData = @(Get-CanonicalStandingTeamData -SourceLookups $sourceLookups)
    $legacyWinners = @(ConvertTo-CanonicalStandingLegacyBracket -Matches $winnersBracket -SourceLookups $sourceLookups)
    $legacyLosers = @(ConvertTo-CanonicalStandingLegacyBracket -Matches $losersBracket -SourceLookups $sourceLookups)

    return [PSCustomObject][ordered]@{
        Season             = [string]$Season
        TeamData           = $teamData
        Playoffs           = [PSCustomObject][ordered]@{
            WinnersBracket = $legacyWinners
            LosersBracket  = $legacyLosers
        }
        RegularSeasonGames = $playoffStartWeek - 1
    }
}

function Get-CanonicalCurrentStandings {
    param(
        [string]$CanonicalLeagueID = "nfl-reise",
        [AllowNull()]$PreviousSeasonStandings = $null
    )

    $currentSeason = [string](Get-Config).LeagueYear
    $source = Get-CanonicalStandingSourceForSeason -CanonicalLeagueID $CanonicalLeagueID -Season $currentSeason -AllowActiveSeason
    $standings = Get-StandingsRemote -playoffs $source.Playoffs -teamData @($source.TeamData) -regularSeasonGames ([int]$source.RegularSeasonGames) -previousSeasonStandings $PreviousSeasonStandings

    return Get-OutputStandingsForSeason `
        -season $currentSeason `
        -standingsPlayoffs @($standings.Playoffs) `
        -standingsRegularSeason @($standings.RegularSeason) `
        -awards @($standings.Awards)
}

function Get-CanonicalHistoricalStandingSeasons {
    param(
        [string]$CanonicalLeagueID = "nfl-reise"
    )

    $repoRoot = Get-CanonicalStandingRepoRoot
    $seasonsRoot = Join-Path $repoRoot "source-data/leagues/$CanonicalLeagueID/seasons"
    if (-not (Test-Path $seasonsRoot)) {
        throw "Canonical League seasons directory missing at '$seasonsRoot'."
    }

    $currentSeason = [int](Get-Config).LeagueYear
    $requiredFiles = @(
        "league.json",
        "members.json",
        "rosters.json",
        "winners-bracket.json",
        "losers-bracket.json"
    )
    $seasons = @()

    foreach ($directory in (Get-ChildItem -Path $seasonsRoot -Directory)) {
        $seasonNumber = 0
        if (-not [int]::TryParse([string]$directory.Name, [ref]$seasonNumber)) { continue }
        if ($seasonNumber -ge $currentSeason) { continue }

        foreach ($fileName in $requiredFiles) {
            $path = Join-Path $directory.FullName $fileName
            if (-not (Test-Path $path)) {
                throw "Canonical historical standings source is incomplete for $CanonicalLeagueID/$seasonNumber; missing '$fileName'."
            }
        }

        $league = Get-CanonicalStandingJson -CanonicalLeagueID $CanonicalLeagueID -Season ([string]$seasonNumber) -FileName "league.json"
        if ([string]$league.Status -ne "complete") {
            throw "Canonical historical standings source $CanonicalLeagueID/$seasonNumber is not complete (status '$($league.Status)')."
        }

        $seasons += [string]$seasonNumber
    }

    return @($seasons | Sort-Object { [int]$_ })
}

function Get-CanonicalHistoricalStandings {
    param(
        [string]$CanonicalLeagueID = "nfl-reise",
        [AllowNull()][AllowEmptyCollection()][array]$Seasons = $null
    )

    if ($null -eq $Seasons) {
        $Seasons = @(Get-CanonicalHistoricalStandingSeasons -CanonicalLeagueID $CanonicalLeagueID)
    }

    $seasonOutputs = @()
    $previousSeasonStandings = $null

    foreach ($season in @($Seasons | ForEach-Object { [string]$_ } | Sort-Object { [int]$_ } -Unique)) {
        $source = Get-CanonicalStandingSourceForSeason -CanonicalLeagueID $CanonicalLeagueID -Season $season
        $standings = Get-StandingsRemote -playoffs $source.Playoffs -teamData @($source.TeamData) -regularSeasonGames ([int]$source.RegularSeasonGames) -previousSeasonStandings $previousSeasonStandings
        $output = Get-OutputStandingsForSeason -season $season -standingsPlayoffs @($standings.Playoffs) -standingsRegularSeason @($standings.RegularSeason) -awards @($standings.Awards)
        $seasonOutputs += $output
        $previousSeasonStandings = $output
    }

    $allTime = if ($seasonOutputs.Count -gt 0) {
        # Productive RequestStandings sorts completed seasons newest-first before
        # building AllTime, while Previous-Season awards require chronological
        # generation. Preserve both order contracts in the shadow.
        $allTimeInput = @($seasonOutputs | Sort-Object -Property Season -Descending)
        Get-OutputStandingsForAllTime -allSeasonStandings $allTimeInput
    }
    else {
        $null
    }

    return [PSCustomObject][ordered]@{
        Seasons = @($seasonOutputs)
        AllTime = $allTime
    }
}

Export-ModuleMember -Function @(
    "Get-CanonicalStandingSourceForSeason",
    "Get-CanonicalCurrentStandings",
    "Get-CanonicalHistoricalStandingSeasons",
    "Get-CanonicalHistoricalStandings"
)
