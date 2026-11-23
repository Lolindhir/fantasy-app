
# ===========================================================================
# 1. Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\..\ConfigUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\general\ArrayUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\general\AvatarUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\general\ProviderJoinUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\league\StandingUtils.psm1" -ErrorAction Stop -Force
}
catch {
    Write-Error "Fehler beim Laden der Module: $_"
    throw $_
}

# ===========================================================================
# 2. Funktionen
# ===========================================================================

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