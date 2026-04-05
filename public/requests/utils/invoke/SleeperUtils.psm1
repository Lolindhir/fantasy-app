
# ===========================================================================
# 1. Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\..\ConfigUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\invoke\InvokeUtils.psm1" -ErrorAction Stop -Force
}
catch {
    Write-Error "Fehler beim Laden der Module: $_"
    throw $_
}

# ===========================================================================
# 2. Funktionen
# ===========================================================================

function Get-SleeperLeague {
    param (
        [string]$leagueID = (Get-Config).LeagueID
    )

    Write-Host "Get Sleeper League..." -ForegroundColor Yellow

    try {
        $url = "https://api.sleeper.app/v1/league/$leagueID"
        $response = Invoke-ApiWithKeyRotation -Url $url
        $leagueData = $response.result
    }
    catch {
        Write-Error "Failed to retrieve Sleeper league data."
        throw $_
    }    

    Write-Host "Sleeper League found." -ForegroundColor Yellow

    return $leagueData
}

function Get-SleeperMembers {
    param (
        [string]$leagueID = (Get-Config).LeagueID
    )

    Write-Host "Get Sleeper Members..." -ForegroundColor Yellow

    try {
        $url = "https://api.sleeper.app/v1/league/$leagueID/users"
        $response = Invoke-ApiWithKeyRotation -Url $url
        $membersData = $response.result
    }
    catch {
        Write-Error "Failed to retrieve Sleeper members data."
        throw $_
    }    

    Write-Host "Sleeper Members found." -ForegroundColor Yellow

    return $membersData
}

function Get-SleeperRosters {
    param (
        [string]$leagueID = (Get-Config).LeagueID
    )

    Write-Host "Get Sleeper Rosters..." -ForegroundColor Yellow

    try {
        $url = "https://api.sleeper.app/v1/league/$leagueID/rosters"
        $response = Invoke-ApiWithKeyRotation -Url $url
        $rostersData = $response.result
    }
    catch {
        Write-Error "Failed to retrieve Sleeper rosters data."
        throw $_
    }    

    Write-Host "Sleeper Rosters found." -ForegroundColor Yellow

    return $rostersData
}

function Get-SleeperWinnersBracket {
    param (
        [string]$leagueID = (Get-Config).LeagueID
    )

    Write-Host "Get Sleeper Winners Bracket..." -ForegroundColor Yellow

    try {
        $url = "https://api.sleeper.app/v1/league/$leagueID/winners_bracket"
        $response = Invoke-ApiWithKeyRotation -Url $url
        $winnersBracketData = $response.result
    }
    catch {
        Write-Error "Failed to retrieve Sleeper winners bracket data."
        throw $_
    }    

    Write-Host "Sleeper Winners Bracket found." -ForegroundColor Yellow

    return $winnersBracketData
}

function Get-SleeperLosersBracket {
    param (
        [string]$leagueID = (Get-Config).LeagueID
    )

    Write-Host "Get Sleeper Losers Bracket..." -ForegroundColor Yellow

    try {
        $url = "https://api.sleeper.app/v1/league/$leagueID/losers_bracket"
        $response = Invoke-ApiWithKeyRotation -Url $url
        $losersBracketData = $response.result
    }
    catch {
        Write-Error "Failed to retrieve Sleeper losers bracket data."
        throw $_
    }    

    Write-Host "Sleeper Losers Bracket found." -ForegroundColor Yellow

    return $losersBracketData
}