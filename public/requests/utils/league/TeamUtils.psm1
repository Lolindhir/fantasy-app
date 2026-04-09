
# ===========================================================================
# 1. Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\..\ConfigUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\general\ArrayUtils.psm1" -ErrorAction Stop -Force
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
        $propsToCheck = @('TeamID','Name','Avatar','Team','OwnerID','Owner','OwnerAvatar','Points','IsCommissioner','PlacePlayoffs','PlaceRegular','Wins','Losses','Ties','Record','Streak','MatchupID','WaiverPosition','WaiverAdjusted')
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
        $arraysToCompare = @('Roster','Reserve','Taxi')
        foreach ($field in $arraysToCompare) {
            if (-not (Compare-Arrays $oldTeam.$field $newTeam.$field $field $oldTeam.Owner)) {
                return $true
            }
        }
    }

    return $false
}

function Get-Teams {
    param (
        [string]$leagueID = (Get-Config).LeagueID
    )

    try {
        $members = Get-SleeperMembers -leagueID $leagueID
        $rosters = Get-SleeperRosters -leagueID $leagueID
        Write-Host "Sleeper Teams found: $($rosters.Count)" -ForegroundColor Yellow

        # --- Teams bauen ---
        $teamData = @()
        foreach ($roster in $rosters) {
            $member = $members | Where-Object { $_.user_id -eq $roster.owner_id }
            $ownerAvatar = $null
            if ($member.avatar) {
                $avatarID    = $member.avatar
                $ownerAvatar = "https://sleepercdn.com/avatars/$avatarID"
            }

            # Punkte berechnen als Double
            $points = [double]($roster.settings.fpts + ($roster.settings.fpts_decimal / 100))
            $pointsAgainst = [double]($roster.settings.fpts_against + ($roster.settings.fpts_against_decimal / 100))

            $teamData += [PSCustomObject]@{
                Owner          = $member.display_name
                OwnerID        = $member.user_id
                OwnerAvatar    = $ownerAvatar
                Team           = $member.metadata.team_name
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

