
# ===========================================================================
# 1. Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\..\ConfigUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\general\ArrayUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\general\AvatarUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\general\ProviderJoinUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\invoke\SleeperUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\league\StandingUtils.psm1" -ErrorAction Stop -Force
}
catch {
    Write-Error "Fehler beim Laden der Module: $_"
    throw $_
}

# ===========================================================================
# 2. Funktionen
# ===========================================================================

function Compare-Teams {
    param (
        [array]$oldTeams,
        [array]$newTeams
    )

    # Prüfe Anzahl der Teams
    if ($oldTeams.Count -ne $newTeams.Count) {
        Write-Host "Team count changed: $($oldTeams.Count) -> $($newTeams.Count)"
        return $true
    }

    # Konvertierung der Old Data in Hashtables für schnelleren Zugriff
    foreach ($team in $oldTeams) {
        if ($team.Placements -is [pscustomobject]) {

            $hash = @{}
            foreach ($prop in $team.Placements.PSObject.Properties) {
                $hash[$prop.Name] = $prop.Value
            }

            $team.Placements = $hash
        }
    }

    # Prüfe jedes Team
    for ($i = 0; $i -lt $oldTeams.Count; $i++) {
        $oldTeam = $oldTeams[$i]
        $newTeam = $newTeams[$i]

        # Prüfe Top-Level Eigenschaften des Teams
        $propsToCheck = @('TeamID','Name','TeamAvatar','Team','TeamAbbr','OwnerID','Owner','OwnerAvatar','Points','IsCommissioner','PlacePlayoffs','PlaceRegular','Wins','Losses','Ties','Record','Streak','MatchupID','WaiverPosition','WaiverAdjusted')
        foreach ($prop in $propsToCheck) {
            if ($oldTeam.$prop -ne $newTeam.$prop) {
                Write-Host "Team '$($oldTeam.Owner)' property '$prop' changed: '$($oldTeam.$prop)' -> '$($newTeam.$prop)'"
                return $true
            }
        }

        # Prüfe Placements
        if ($oldTeam.Placements.Count -ne $newTeam.Placements.Count) {
            Write-Host "Team '$($oldTeam.Owner)' placements count changed: $($oldTeam.Placements.Count) -> $($newTeam.Placements.Count)"
            return $true
        }
        foreach ($key in $oldTeam.Placements.Keys) {
            if (-not $newTeam.Placements.ContainsKey($key)) {
                Write-Host "Team '$($oldTeam.Owner)' missing placement for season '$key'"
                return $true
            }

            $oldPlacement = $oldTeam.Placements[$key]
            $newPlacement = $newTeam.Placements[$key]
            
            if(Compare-RegularSeasonStandings $oldPlacement.Regular $newPlacement.Regular) {
                Write-Host "Team '$($oldTeam.Owner)' regular season placement for season '$key' changed."
                return $true
            }

            if (Compare-PlayoffStandings $oldPlacement.Playoffs $newPlacement.Playoffs) {
                Write-Host "Team '$($oldTeam.Owner)' playoff placement for season '$key' changed."
                return $true
            }

            if (Compare-Awards $oldPlacement.Awards $newPlacement.Awards) {
                Write-Host "Team '$($oldTeam.Owner)' awards for season '$key' changed."
                return $true
            }

        }

        # Vergleiche Roster, Reserve, Taxi
        $arraysToCompare = @('Roster','Reserve','Taxi', 'Starter', 'DraftPicks')
        foreach ($field in $arraysToCompare) {
            if (-not (Compare-Arrays $oldTeam.$field $newTeam.$field $field $oldTeam.Owner)) {
                return $true
            }
        }
    }

    return $false
}

function ConvertTo-TeamAbbreviation {
    param (
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

function Resolve-TeamDisplayName {
    param (
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

function New-SleeperTeamSourceLookups {
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [array]$Members,

        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [array]$Rosters
    )

    $membersByUserID = New-UniqueObjectLookup `
        -Items $Members `
        -KeyProperty "user_id" `
        -SourceLabel "Sleeper league members" `
        -KeyLabel "user_id" `
        -DescriptionProperties @("user_id", "display_name")

    $rostersByRosterID = New-UniqueObjectLookup `
        -Items $Rosters `
        -KeyProperty "roster_id" `
        -SourceLabel "Sleeper league rosters" `
        -KeyLabel "roster_id" `
        -DescriptionProperties @("roster_id", "owner_id")

    $rostersByOwnerID = New-UniqueObjectLookup `
        -Items $Rosters `
        -KeyProperty "owner_id" `
        -SourceLabel "Sleeper roster owners" `
        -KeyLabel "owner_id" `
        -DescriptionProperties @("roster_id", "owner_id")

    foreach ($ownerID in $rostersByOwnerID.Keys) {
        if (-not $membersByUserID.ContainsKey([string]$ownerID)) {
            $roster = $rostersByOwnerID[$ownerID]
            throw "Sleeper roster '$($roster.roster_id)' references owner_id '$ownerID', but no unique league member with that user_id exists."
        }
    }

    return [PSCustomObject][ordered]@{
        MembersByUserID   = $membersByUserID
        RostersByRosterID = $rostersByRosterID
        RostersByOwnerID  = $rostersByOwnerID
    }
}

function Get-Teams {
    param (
        [string]$leagueID = (Get-Config).LeagueID
    )

    try {
        $members = Get-SleeperMembers -leagueID $leagueID
        $rosters = Get-SleeperRosters -leagueID $leagueID
        Write-Host "Sleeper Teams found: $($rosters.Count)" -ForegroundColor Yellow

        $sourceLookups = New-SleeperTeamSourceLookups -Members @($members) -Rosters @($rosters)
        $membersByUserID = $sourceLookups.MembersByUserID

        # --- Teams bauen ---
        $teamData = @()
        foreach ($roster in $rosters) {
            $member = $membersByUserID[[string]$roster.owner_id]
            $ownerAvatar = $null
            if ($member.avatar) {
                $avatarID    = $member.avatar
                $ownerAvatar = Get-SleeperAvatar($avatarID)
            }

            # Punkte berechnen als Double
            $points = [double]($roster.settings.fpts + ($roster.settings.fpts_decimal / 100))
            $pointsAgainst = [double]($roster.settings.fpts_against + ($roster.settings.fpts_against_decimal / 100))
            $teamName = Resolve-TeamDisplayName -TeamName $member.metadata.team_name -OwnerName $member.display_name

            $teamData += [PSCustomObject]@{
                Owner          = $member.display_name
                OwnerID        = $member.user_id
                OwnerAvatar    = $ownerAvatar
                Team           = $teamName
                TeamAbbr       = ConvertTo-TeamAbbreviation -TeamName $teamName -TeamID $roster.roster_id
                TeamID         = $roster.roster_id
                TeamAvatar     = $member.metadata.avatar
                PlaceRegular   = 0 # wird später berechnet
                PlacePlayoffs  = 0 # wird später berechnet
                Points         = $points
                PointsAgainst  = $pointsAgainst
                Wins           = $roster.settings.wins
                Losses         = $roster.settings.losses
                Ties           = $roster.settings.ties
                Record         = $roster.metadata.record
                Streak         = $roster.metadata.streak
                MatchupID      = $roster.settings.matchup_id
                WaiverPosition = $roster.settings.waiver_position
                WaiverAdjusted = $roster.settings.waiver_adjusted
                IsCommissioner = $member.is_owner
                Placements     = @{} # wird später berechnet
                Roster         = $roster.players
                Reserve        = $roster.reserve
                Taxi           = $roster.taxi
                Starter        = $roster.starters
            }
        }

        return $teamData
    }
    catch {
        throw $_
    }  
}

function Get-TeamsForLeague {
    return Get-Teams |
        Select-Object * -ExcludeProperty PlaceRegular, PlacePlayoffs, Points, PointsAgainst, Wins, Losses, Ties, Record, Streak
}

function Get-OwnerIDByName {
    param (
        [Parameter(Mandatory = $true)]
        [string]$ownerName
    )

    $config = Get-Config
    if ($config.OwnerIDs.ContainsKey($ownerName)) {
        return $config.OwnerIDs[$ownerName]
    } else {
        Write-Error "Owner '$ownerName' not found in configuration."
        throw "Owner '$ownerName' not found."
    }

}