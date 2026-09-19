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
    $path = Join-Path $repoRoot "source-data/leagues/$CanonicalLeagueID/seasons/$Season/$FileName"
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

function Resolve-CanonicalLeagueCoreTeamDisplayName {
    param(
        [AllowNull()][string]$TeamName,
        [AllowNull()][string]$OwnerName
    )

    if (-not [string]::IsNullOrWhiteSpace($TeamName)) {
        return $TeamName.Trim()
    }

    if (-not [string]::IsNullOrWhiteSpace($OwnerName)) {
        return "Team $($OwnerName.Trim())"
    }

    return $null
}

function ConvertTo-CanonicalLeagueCoreTeamAbbreviation {
    param(
        [AllowNull()][string]$TeamName,
        [AllowNull()]$TeamID
    )

    $fallbackNumber = 0
    $fallback = if ([int]::TryParse([string]$TeamID, [ref]$fallbackNumber)) { "T{0:D2}" -f $fallbackNumber } else { "TBD" }

    if ([string]::IsNullOrWhiteSpace($TeamName)) {
        return $fallback
    }

    $normalized = $TeamName.Trim()
    $normalized = $normalized -creplace '(\p{Lu}+)(\p{Lu}\p{Ll})', '$1 $2'
    $normalized = $normalized -creplace '([\p{Ll}\p{N}])(\p{Lu})', '$1 $2'
    $normalized = $normalized -replace '[^\p{L}\p{N}]+', ' '
    $normalized = $normalized.Trim()

    if ([string]::IsNullOrWhiteSpace($normalized)) {
        return $fallback
    }

    $stopWords = @('team', 'the')
    $nameParts = @($normalized -split '\s+' | Where-Object {
        -not [string]::IsNullOrWhiteSpace($_) -and $_.ToLowerInvariant() -notin $stopWords
    })

    if ($nameParts.Count -eq 0) {
        return $fallback
    }

    if ($nameParts.Count -eq 1) {
        $part = [string]$nameParts[0]
        $length = [Math]::Min(3, $part.Length)
        $abbr = $part.Substring(0, $length)
        return $abbr.Substring(0, 1).ToUpperInvariant() + $abbr.Substring(1).ToLowerInvariant()
    }

    if ($nameParts.Count -eq 2) {
        $firstPart = [string]$nameParts[0]
        $secondPart = [string]$nameParts[1]
        $firstLength = [Math]::Min(2, $firstPart.Length)
        $prefix = $firstPart.Substring(0, $firstLength)
        $prefix = $prefix.Substring(0, 1).ToUpperInvariant() + $prefix.Substring(1).ToLowerInvariant()
        return $prefix + $secondPart.Substring(0, 1).ToUpperInvariant()
    }

    $initials = $nameParts |
        Select-Object -First 3 |
        ForEach-Object { ([string]$_).Substring(0, 1).ToUpperInvariant() }

    return [string]::Join('', $initials)
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
        [string]$CanonicalLeagueID = "nfl-reise"
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

function Get-CanonicalCurrentTeamsForLeague {
    param(
        [string]$CanonicalLeagueID = "nfl-reise"
    )

    $season = [string](Get-Config).LeagueYear
    $members = @(ConvertTo-SafeArray -value (Get-CanonicalLeagueCoreJson -CanonicalLeagueID $CanonicalLeagueID -Season $season -FileName "members.json"))
    $rosters = @(ConvertTo-SafeArray -value (Get-CanonicalLeagueCoreJson -CanonicalLeagueID $CanonicalLeagueID -Season $season -FileName "rosters.json"))
    $lookups = New-CanonicalLeagueCoreLookups -Members $members -Rosters $rosters

    $teams = @()
    foreach ($rosterSource in @($lookups.RostersByCanonicalID.Values | Sort-Object { [int]$_.ProviderRosterID })) {
        $roster = $rosterSource.Source
        $memberSource = $lookups.MembersByCanonicalID[[string]$rosterSource.CanonicalLeagueMemberID]
        $member = $memberSource.Source

        $owner = [string](Get-CanonicalLeagueCorePropertyValue -Object $member -PropertyName "DisplayName" -DefaultValue "")
        if ([string]::IsNullOrWhiteSpace($owner)) {
            throw "Canonical member '$($memberSource.CanonicalLeagueMemberID)' is missing DisplayName."
        }

        $teamName = Resolve-CanonicalLeagueCoreTeamDisplayName -TeamName ([string](Get-CanonicalLeagueCorePropertyValue -Object $member.Metadata -PropertyName "team_name" -DefaultValue "")) -OwnerName $owner
        if ([string]::IsNullOrWhiteSpace($teamName)) {
            throw "Canonical member '$($memberSource.CanonicalLeagueMemberID)' cannot resolve a team display name."
        }

        $ownerAvatarID = [string](Get-CanonicalLeagueCorePropertyValue -Object $member -PropertyName "Avatar" -DefaultValue "")
        $ownerAvatar = if ([string]::IsNullOrWhiteSpace($ownerAvatarID)) { $null } else { Get-SleeperAvatar $ownerAvatarID }
        $providerRosterID = [int]$rosterSource.ProviderRosterID

        $teams += [PSCustomObject][ordered]@{
            Owner          = $owner
            OwnerID        = [string]$memberSource.ProviderUserID
            OwnerAvatar    = $ownerAvatar
            Team           = $teamName
            TeamAbbr       = ConvertTo-CanonicalLeagueCoreTeamAbbreviation -TeamName $teamName -TeamID $providerRosterID
            TeamID         = $providerRosterID
            TeamAvatar     = Get-CanonicalLeagueCorePropertyValue -Object $member.Metadata -PropertyName "avatar" -DefaultValue $null
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
        [string]$CanonicalLeagueID = "nfl-reise"
    )

    return [PSCustomObject][ordered]@{
        League = Get-CanonicalCurrentLeagueRaw -CanonicalLeagueID $CanonicalLeagueID
        Teams  = @(Get-CanonicalCurrentTeamsForLeague -CanonicalLeagueID $CanonicalLeagueID)
    }
}

Export-ModuleMember -Function @(
    "Get-CanonicalCurrentLeagueRaw",
    "Get-CanonicalCurrentTeamsForLeague",
    "Get-CanonicalCurrentLeagueCoreShadow"
)
