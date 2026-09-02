
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

function Get-SleeperTransactions {
    param (
        [string]$leagueID = (Get-Config).LeagueID,
        [int]$week
    )

    Write-Host "Get Sleeper Transactions for Week $week..." -ForegroundColor Yellow

    try {
        $url = "https://api.sleeper.app/v1/league/$leagueID/transactions/$week"
        $response = Invoke-ApiWithKeyRotation -Url $url
        $transactionsData = $response.result
    }
    catch {
        Write-Error "Failed to retrieve Sleeper transactions data for week $week."
        throw $_
    }

    Write-Host "Sleeper Transactions for Week $week found." -ForegroundColor Yellow

    return $transactionsData
}

function Get-SleeperMatchups {
    param (
        [string]$leagueID = (Get-Config).LeagueID,
        [Parameter(Mandatory = $true)][int]$week
    )

    Write-Host "Get Sleeper Matchups for Week $week..." -ForegroundColor Yellow

    try {
        $url = "https://api.sleeper.app/v1/league/$leagueID/matchups/$week"
        $response = Invoke-ApiWithKeyRotation -Url $url
        $matchupsData = $response.result
    }
    catch {
        Write-Error "Failed to retrieve Sleeper matchups data for week $week."
        throw $_
    }

    Write-Host "Sleeper Matchups for Week $week found." -ForegroundColor Yellow

    return $matchupsData
}

function Get-SleeperDrafts {
    param (
        [string]$leagueID = (Get-Config).LeagueID
    )

    Write-Host "Get Sleeper Drafts..." -ForegroundColor Yellow

    try {
        $url = "https://api.sleeper.app/v1/league/$leagueID/drafts"
        $response = Invoke-ApiWithKeyRotation -Url $url
        $draftsData = $response.result
    }
    catch {
        Write-Error "Failed to retrieve Sleeper drafts data."
        throw $_
    }

    Write-Host "Sleeper Drafts found." -ForegroundColor Yellow

    return $draftsData
}

function Get-SleeperDraft {
    param (
        [string]$draftID
    )

    Write-Host "Get Sleeper Draft $draftID..." -ForegroundColor Yellow

    try {
        $url = "https://api.sleeper.app/v1/draft/$draftID"
        $response = Invoke-ApiWithKeyRotation -Url $url
        $draftData = $response.result
    }
    catch {
        Write-Error "Failed to retrieve Sleeper draft data."
        throw $_
    }

    Write-Host "Sleeper Draft found." -ForegroundColor Yellow

    return $draftData
}

function Get-SleeperDraftPicks {
    param (
        [string]$draftID
    )

    Write-Host "Get Sleeper Draft Picks for Draft $draftID..." -ForegroundColor Yellow

    try {
        $url = "https://api.sleeper.app/v1/draft/$draftID/picks"
        $response = Invoke-ApiWithKeyRotation -Url $url
        $draftPicksData = $response.result
    }
    catch {
        Write-Error "Failed to retrieve Sleeper draft picks data."
        throw $_
    }

    Write-Host "Sleeper Draft Picks found." -ForegroundColor Yellow

    return $draftPicksData
}

function Get-SleeperDraftTradedPicks {
    param (
        [string]$draftID
    )

    Write-Host "Get Sleeper Traded Picks for Draft $draftID..." -ForegroundColor Yellow

    try {
        $url = "https://api.sleeper.app/v1/draft/$draftID/traded_picks"
        $response = Invoke-ApiWithKeyRotation -Url $url
        $tradedPicksData = $response.result
    }
    catch {
        Write-Error "Failed to retrieve Sleeper traded picks data for draft $draftID."
        throw $_
    }

    Write-Host "Sleeper Draft Traded Picks found." -ForegroundColor Yellow

    return $tradedPicksData
}

function Get-SleeperTradedPicks {
    param (
        [string]$leagueID = (Get-Config).LeagueID
    )

    Write-Host "Get Sleeper Traded Picks..." -ForegroundColor Yellow

    try {
        $url = "https://api.sleeper.app/v1/league/$leagueID/traded_picks"
        $response = Invoke-ApiWithKeyRotation -Url $url
        $tradedPicksData = $response.result
    }
    catch {
        Write-Error "Failed to retrieve Sleeper traded picks data."
        throw $_
    }

    Write-Host "Sleeper Traded Picks found." -ForegroundColor Yellow

    return $tradedPicksData
}
