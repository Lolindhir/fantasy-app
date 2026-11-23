# ===========================================================================
# Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\..\ConfigUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\general\ArrayUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\general\AvatarUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\general\ProviderJoinUtils.psm1" -ErrorAction Stop -Force
}
catch {
    Write-Error "Fehler beim Laden der Module: $_"
    throw $_
}

# ===========================================================================
# Canonical current League Core shadow consumer
# ===========================================================================

function Get-CanonicalLeagueCoreRepoRoot {
    return (Resolve-Path (Join-Path $PSScriptRoot "../../../..")).Path
}

function Get-CanonicalLeagueCorePropertyValue {
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

function Get-CanonicalLeagueCoreJson {
    param(
        [Parameter(Mandatory = $true)][string]$CanonicalLeagueID,
        [Parameter(Mandatory = $true)][string]$Season,
        [Parameter(Mandatory = $true)][string]$FileName
    )

    $repoRoot = Get-CanonicalLeagueCoreRepoRoot
    $path = Join-Path (Get-DataSourceRoot -RepoRoot $repoRoot) "leagues/$CanonicalLeagueID/seasons/$Season/$FileName"
    if (-not (Test-Path $path)) {
        throw "Canonical League Core source '$FileName' missing for $CanonicalLeagueID/$Season at '$path'."
    }

    try {
        $raw = Get-Content $path -Raw
        if ([string]::IsNullOrWhiteSpace($raw)) {
            throw "Canonical League Core source '$FileName' is empty for $CanonicalLeagueID/$Season."
        }
        return $raw | ConvertFrom-Json
    }
    catch {
        throw "Could not read canonical League Core source '$path'. $_"
    }
}

function Get-CanonicalLeagueCoreSleeperMapping {
    param(
        [AllowNull()]$Mappings,
        [Parameter(Mandatory = $true)][string]$SourceLabel
    )

    $matches = @(
        ConvertTo-SafeArray -value $Mappings |
            Where-Object { [string]$_.Provider -eq "Sleeper" }
    )

    if ($matches.Count -ne 1) {
        throw "$SourceLabel must have exactly one Sleeper provider mapping; found $($matches.Count)."
    }

    return $matches[0]
}

function Get-CanonicalLeagueCoreRequiredMappingValue {
    param(
        [Parameter(Mandatory = $true)]$Mapping,
        [Parameter(Mandatory = $true)][string]$PropertyName,
        [Parameter(Mandatory = $true)][string]$SourceLabel
    )

    $value = [string](Get-CanonicalLeagueCorePropertyValue -Object $Mapping -PropertyName $PropertyName -DefaultValue "")
    if ([string]::IsNullOrWhiteSpace($value)) {
        throw "$SourceLabel Sleeper provider mapping is missing '$PropertyName'."
    }

    return $value
}

function ConvertTo-CanonicalLeagueCoreProviderPlayerIDs {
    param(
        [AllowNull()]$Players,
        [Parameter(Mandatory = $true)][string]$SourceLabel
    )

    $result = @()
    $index = 0
    foreach ($player in @(ConvertTo-SafeArray -value $Players)) {
        if ($null -eq $player) {
            throw "$SourceLabel contains a null player reference at index $index."
        }

        $canonicalPlayerID = [string](Get-CanonicalLeagueCorePropertyValue -Object $player -PropertyName "CanonicalPlayerID" -DefaultValue "")
        if ([string]::IsNullOrWhiteSpace($canonicalPlayerID)) {
            throw "$SourceLabel contains a player reference without CanonicalPlayerID at index $index."
        }

        $mapping = Get-CanonicalLeagueCoreSleeperMapping -Mappings $player.ProviderMappings -SourceLabel "$SourceLabel player '$canonicalPlayerID'"
        $result += Get-CanonicalLeagueCoreRequiredMappingValue -Mapping $mapping -PropertyName "ProviderPlayerID" -SourceLabel "$SourceLabel player '$canonicalPlayerID'"
        $index++
    }

    return @($result)
}

function New-CanonicalLeagueCoreLookups {
    param(
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$Members,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$Rosters
    )

    $memberSources = @()
    foreach ($member in $Members) {
        $canonicalMemberID = [string](Get-CanonicalLeagueCorePropertyValue -Object $member -PropertyName "CanonicalLeagueMemberID" -DefaultValue "")
        if ([string]::IsNullOrWhiteSpace($canonicalMemberID)) {
            throw "Canonical League Core member is missing CanonicalLeagueMemberID."
        }

        $mapping = Get-CanonicalLeagueCoreSleeperMapping -Mappings $member.ProviderMappings -SourceLabel "Canonical member '$canonicalMemberID'"
        $providerUserID = Get-CanonicalLeagueCoreRequiredMappingValue -Mapping $mapping -PropertyName "ProviderUserID" -SourceLabel "Canonical member '$canonicalMemberID'"

        $memberSources += [PSCustomObject][ordered]@{
            CanonicalLeagueMemberID = $canonicalMemberID
            ProviderUserID          = $providerUserID
            Source                  = $member
        }
    }

    $rosterSources = @()
    foreach ($roster in $Rosters) {
        $canonicalRosterID = [string](Get-CanonicalLeagueCorePropertyValue -Object $roster -PropertyName "CanonicalLeagueRosterID" -DefaultValue "")
        $canonicalMemberID = [string](Get-CanonicalLeagueCorePropertyValue -Object $roster -PropertyName "CanonicalLeagueMemberID" -DefaultValue "")
        if ([string]::IsNullOrWhiteSpace($canonicalRosterID)) {
            throw "Canonical League Core roster is missing CanonicalLeagueRosterID."
        }
        if ([string]::IsNullOrWhiteSpace($canonicalMemberID)) {
            throw "Canonical roster '$canonicalRosterID' is missing CanonicalLeagueMemberID."
        }

        $mapping = Get-CanonicalLeagueCoreSleeperMapping -Mappings $roster.ProviderMappings -SourceLabel "Canonical roster '$canonicalRosterID'"
        $providerRosterID = Get-CanonicalLeagueCoreRequiredMappingValue -Mapping $mapping -PropertyName "ProviderRosterID" -SourceLabel "Canonical roster '$canonicalRosterID'"
        $providerOwnerUserID = [string](Get-CanonicalLeagueCorePropertyValue -Object $roster -PropertyName "ProviderOwnerUserID" -DefaultValue "")
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

    $membersByCanonicalID = New-UniqueObjectLookup -Items $memberSources -KeyProperty "CanonicalLeagueMemberID" -SourceLabel "canonical League Core members" -KeyLabel "CanonicalLeagueMemberID" -DescriptionProperties @("CanonicalLeagueMemberID", "ProviderUserID")
    $membersByProviderID = New-UniqueObjectLookup -Items $memberSources -KeyProperty "ProviderUserID" -SourceLabel "canonical League Core member mappings" -KeyLabel "ProviderUserID" -DescriptionProperties @("CanonicalLeagueMemberID", "ProviderUserID")
    $rostersByCanonicalID = New-UniqueObjectLookup -Items $rosterSources -KeyProperty "CanonicalLeagueRosterID" -SourceLabel "canonical League Core rosters" -KeyLabel "CanonicalLeagueRosterID" -DescriptionProperties @("CanonicalLeagueRosterID", "ProviderRosterID", "ProviderOwnerUserID")
    $rostersByProviderID = New-UniqueObjectLookup -Items $rosterSources -KeyProperty "ProviderRosterID" -SourceLabel "canonical League Core roster mappings" -KeyLabel "ProviderRosterID" -DescriptionProperties @("CanonicalLeagueRosterID", "ProviderRosterID", "ProviderOwnerUserID")
    $rostersByOwnerID = New-UniqueObjectLookup -Items $rosterSources -KeyProperty "ProviderOwnerUserID" -SourceLabel "canonical League Core roster owners" -KeyLabel "ProviderOwnerUserID" -DescriptionProperties @("CanonicalLeagueRosterID", "ProviderRosterID", "ProviderOwnerUserID")

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

function Get-CanonicalCurrentLeagueRaw {
    param(
        [string]$CanonicalLeagueID = (Get-Config).CanonicalLeagueID
    )

    $season = [string](Get-Config).LeagueYear
    $league = Get-CanonicalLeagueCoreJson -CanonicalLeagueID $CanonicalLeagueID -Season $season -FileName "league.json"
    $rosters = @(ConvertTo-SafeArray -value (Get-CanonicalLeagueCoreJson -CanonicalLeagueID $CanonicalLeagueID -Season $season -FileName "rosters.json"))

    if ([string]$league.CanonicalLeagueID -ne $CanonicalLeagueID) {
        throw "Canonical League Core identity mismatch: requested '$CanonicalLeagueID', league.json contains '$($league.CanonicalLeagueID)'."
    }
    if ([string]$league.Season -ne $season) {
        throw "Canonical League Core season mismatch: configured '$season', league.json contains '$($league.Season)'."
    }

    $mapping = Get-CanonicalLeagueCoreSleeperMapping -Mappings $league.ProviderMappings -SourceLabel "Canonical league '$CanonicalLeagueID/$season'"
    $providerLeagueID = Get-CanonicalLeagueCoreRequiredMappingValue -Mapping $mapping -PropertyName "ProviderLeagueID" -SourceLabel "Canonical league '$CanonicalLeagueID/$season'"
    $previousProviderLeagueID = [string](Get-CanonicalLeagueCorePropertyValue -Object $mapping -PropertyName "PreviousProviderLeagueID" -DefaultValue "")

    $configuredTeams = [int](Get-CanonicalLeagueCorePropertyValue -Object $league.Settings -PropertyName "num_teams" -DefaultValue 0)
    if ($configuredTeams -gt 0 -and $configuredTeams -ne $rosters.Count) {
        throw "Canonical League Core team-count mismatch for $CanonicalLeagueID/${season}: settings.num_teams=$configuredTeams, rosters=$($rosters.Count)."
    }

    return [PSCustomObject][ordered]@{
        league_id          = $providerLeagueID
        name               = [string]$league.Name
        avatar             = Get-CanonicalLeagueCorePropertyValue -Object $league -PropertyName "Avatar" -DefaultValue $null
        season             = [string]$league.Season
        season_type        = [string]$league.SeasonType
        status             = [string]$league.Status
        total_rosters      = [int]$rosters.Count
        settings           = $league.Settings
        scoring_settings   = $league.ScoringSettings
        roster_positions   = @($league.RosterPositions)
        previous_league_id = if ([string]::IsNullOrWhiteSpace($previousProviderLeagueID)) { $null } else { $previousProviderLeagueID }
    }
}

# Fantasy-team identity (name, abbreviation, logos) comes from the single league-teams implementation (Issue #774, ADR-098,
# tools/league_teams.py); this module only joins it to the roster facts by provider roster ID. Fails closed.
function Get-CanonicalLeagueTeamIdentities {
    param(
        [Parameter(Mandatory = $true)][string]$CanonicalLeagueID,
        [Parameter(Mandatory = $true)][string]$Season
    )

    $repoRoot = Get-CanonicalLeagueCoreRepoRoot
    $toolPath = Join-Path $repoRoot "tools/league_teams.py"
    if (-not (Test-Path $toolPath)) { throw "League teams tool missing at '$toolPath'." }

    $python = $null
    foreach ($name in @("python3", "python")) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($command) { $python = $command.Source; break }
    }
    if (-not $python) { throw "Python is required for the league team identity." }

    $output = & $python $toolPath season --league $CanonicalLeagueID --season $Season --repo-root $repoRoot 2>&1
    $exitCode = $LASTEXITCODE
    $outputText = (@($output) | ForEach-Object { [string]$_ }) -join [Environment]::NewLine
    if ($exitCode -ne 0) { throw "League team identity failed with exit code $exitCode. $outputText" }
    try { $identities = @($outputText | ConvertFrom-Json) }
    catch { throw "League team identity returned invalid JSON. $outputText" }

    $byTeamID = @{}
    foreach ($identity in $identities) { $byTeamID[[int]$identity.TeamID] = $identity }
    return $byTeamID
}

function Get-CanonicalCurrentTeamsForLeague {
    param(
        [string]$CanonicalLeagueID = (Get-Config).CanonicalLeagueID
    )

    $season = [string](Get-Config).LeagueYear
    $identities = Get-CanonicalLeagueTeamIdentities -CanonicalLeagueID $CanonicalLeagueID -Season $season
    $members = @(ConvertTo-SafeArray -value (Get-CanonicalLeagueCoreJson -CanonicalLeagueID $CanonicalLeagueID -Season $season -FileName "members.json"))
    $rosters = @(ConvertTo-SafeArray -value (Get-CanonicalLeagueCoreJson -CanonicalLeagueID $CanonicalLeagueID -Season $season -FileName "rosters.json"))
    $lookups = New-CanonicalLeagueCoreLookups -Members $members -Rosters $rosters

    $teams = @()
    foreach ($rosterSource in @($lookups.RostersByCanonicalID.Values | Sort-Object { [int]$_.ProviderRosterID })) {
        $roster = $rosterSource.Source
        $memberSource = $lookups.MembersByCanonicalID[[string]$rosterSource.CanonicalLeagueMemberID]
        $member = $memberSource.Source

        $providerRosterID = [int]$rosterSource.ProviderRosterID
        $identity = $identities[$providerRosterID]
        if ($null -eq $identity) {
            throw "League team identity lacks provider roster $providerRosterID for $CanonicalLeagueID/$season."
        }

        $teams += [PSCustomObject][ordered]@{
            Owner          = [string]$identity.Owner
            OwnerID        = [string]$identity.OwnerID
            OwnerAvatar    = $identity.OwnerAvatar
            Team           = [string]$identity.TeamName
            TeamAbbr       = [string]$identity.TeamAbbr
            TeamID         = $providerRosterID
            TeamAvatar     = $identity.TeamAvatar
            MatchupID      = Get-CanonicalLeagueCorePropertyValue -Object $roster.Settings -PropertyName "matchup_id" -DefaultValue $null
            WaiverPosition = Get-CanonicalLeagueCorePropertyValue -Object $roster.Settings -PropertyName "waiver_position" -DefaultValue $null
            WaiverAdjusted = Get-CanonicalLeagueCorePropertyValue -Object $roster.Settings -PropertyName "waiver_adjusted" -DefaultValue $null
            IsCommissioner = [bool](Get-CanonicalLeagueCorePropertyValue -Object $member -PropertyName "IsOwner" -DefaultValue $false)
            Placements     = @{}
            Roster         = @(ConvertTo-CanonicalLeagueCoreProviderPlayerIDs -Players $roster.Players -SourceLabel "Canonical roster '$($rosterSource.CanonicalLeagueRosterID)' Players")
            Reserve        = @(ConvertTo-CanonicalLeagueCoreProviderPlayerIDs -Players $roster.Reserve -SourceLabel "Canonical roster '$($rosterSource.CanonicalLeagueRosterID)' Reserve")
            Taxi           = @(ConvertTo-CanonicalLeagueCoreProviderPlayerIDs -Players $roster.Taxi -SourceLabel "Canonical roster '$($rosterSource.CanonicalLeagueRosterID)' Taxi")
            Starter        = @(ConvertTo-CanonicalLeagueCoreProviderPlayerIDs -Players $roster.Starters -SourceLabel "Canonical roster '$($rosterSource.CanonicalLeagueRosterID)' Starters")
        }
    }

    return @($teams)
}

function Get-CanonicalCurrentLeagueCoreShadow {
    param(
        [string]$CanonicalLeagueID = (Get-Config).CanonicalLeagueID
    )

    return [PSCustomObject][ordered]@{
        League = Get-CanonicalCurrentLeagueRaw -CanonicalLeagueID $CanonicalLeagueID
        Teams  = @(Get-CanonicalCurrentTeamsForLeague -CanonicalLeagueID $CanonicalLeagueID)
    }
}

function Get-CanonicalLeagueSeasonLeagues {
    param(
        [string]$CanonicalLeagueID = (Get-Config).CanonicalLeagueID
    )

    $seasonsRoot = Join-Path (Get-DataSourceRoot -RepoRoot (Get-CanonicalLeagueCoreRepoRoot)) "leagues/$CanonicalLeagueID/seasons"
    if (-not (Test-Path $seasonsRoot)) {
        throw "Canonical League season directory missing at '$seasonsRoot'."
    }

    $currentSeason = [int](Get-Config).LeagueYear
    $leagues = @()

    foreach ($directory in (Get-ChildItem -Path $seasonsRoot -Directory)) {
        $seasonNumber = 0
        if (-not [int]::TryParse([string]$directory.Name, [ref]$seasonNumber)) { continue }
        if ($seasonNumber -gt $currentSeason) { continue }

        $league = Get-CanonicalLeagueCoreJson -CanonicalLeagueID $CanonicalLeagueID -Season ([string]$seasonNumber) -FileName "league.json"
        if ([string]$league.CanonicalLeagueID -ne $CanonicalLeagueID) {
            throw "Canonical League Core identity mismatch: requested '$CanonicalLeagueID', league.json for season $seasonNumber contains '$($league.CanonicalLeagueID)'."
        }
        if ([string]$league.Season -ne [string]$seasonNumber) {
            throw "Canonical League Core season mismatch: directory '$seasonNumber', league.json contains '$($league.Season)'."
        }

        $mapping = Get-CanonicalLeagueCoreSleeperMapping -Mappings $league.ProviderMappings -SourceLabel "Canonical league '$CanonicalLeagueID/$seasonNumber'"
        $leagues += [PSCustomObject][ordered]@{
            league_id = Get-CanonicalLeagueCoreRequiredMappingValue -Mapping $mapping -PropertyName "ProviderLeagueID" -SourceLabel "Canonical league '$CanonicalLeagueID/$seasonNumber'"
            season    = [string]$league.Season
        }
    }

    return @($leagues | Sort-Object { [int]$_.season })
}

Export-ModuleMember -Function @(
    "Get-CanonicalCurrentLeagueRaw",
    "Get-CanonicalCurrentTeamsForLeague",
    "Get-CanonicalCurrentLeagueCoreShadow",
    "Get-CanonicalLeagueSeasonLeagues"
)
