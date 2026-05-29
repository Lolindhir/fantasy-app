
# ===========================================================================
# Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\..\ConfigUtils.psm1" -ErrorAction Stop -Force
}
catch {
    Write-Error "Fehler beim Laden der Module: $_"
    throw $_
}

# ===========================================================================
# Compare Utils
# ===========================================================================

function Compare-Awards{
    
    param(
        [Parameter(Mandatory=$true)]
        [AllowNull()]
        [AllowEmptyCollection()]
        [array]$oldAwards,
        [Parameter(Mandatory=$true)]
        [AllowNull()]
        [AllowEmptyCollection()]
        [array]$newAwards
    )

    if (-not $oldAwards -and -not $newAwards) {
        return $false
    }

    if (-not $oldAwards -or -not $newAwards) {
        Write-Host "Awards presence changed."
        return $true
    }

    if ($oldAwards.Count -ne $newAwards.Count) {
        Write-Host "Awards count changed."
        return $true
    }

    for ($i = 0; $i -lt $oldAwards.Count; $i++) {
        $oldAward = $oldAwards[$i]
        $newAward = $newAwards[$i]

        if ($oldAward.Name -ne $newAward.Name) {
            Write-Host "Award name changed at index $($i): '$($oldAward.Name)' -> '$($newAward.Name)'"
            return $true
        }

        if(Compare-Standings -oldStandings $oldAwards -newStandings $newAwards -propertiesToCheck (Get-AwardProperties) -outputProperty "Name") {
            Write-Host "Awards changed."
            return $true
        }
    }

    return $false
}

function Get-AwardProperties{
    return @('Name','IconUnicode','StatDisplay','TeamID','Owner','TeamName')
}


# ===========================================================================
# Build Utils
# ===========================================================================

function Get-TransactionOutput {
    param(
        [object]$sleeperTransaction,
        [object]$customTransaction
    )

    if(-not $sleeperTransaction) {
        Write-Warning "Sleeper transaction data is null or empty. Returning null."
        return $null
    }

    $output = [PSCustomObject]@{
        TransactionID = $sleeperTransaction.transaction_id,
        Type = $sleeperTransaction.type,
        Status = $sleeperTransaction.status,
        CreatedAt = [DateTime]::Parse($sleeperTransaction.created_at),
        UpdatedAt = [DateTime]::Parse($sleeperTransaction.updated_at),
        SleeperData = $sleeperTransaction,
        CustomData = $customTransaction
    }

    return $output
}

# ===========================================================================
# Remote Utils
# ===========================================================================

function Get-TransactionsRemote {
    param (
        [string]$leagueID = (Get-Config).LeagueID,
        [array]$playoffs = (Get-Playoffs -leagueID $leagueID),
        [Parameter(Mandatory=$true)][array]$teamData,
        [Parameter(Mandatory=$true)][int]$regularSeasonGames,
        [Parameter(Mandatory=$true)][AllowNull()]$previousSeasonStandings
    )

    try {
        $winnersBracket = $playoffs.WinnersBracket
        $losersBracket  = $playoffs.LosersBracket

        Write-Host "Calculate standings..." -ForegroundColor Yellow

        # Playoff-Standings berechnen
        $playoffStandings = Get-PlayoffStandings -winnersBracket $winnersBracket -losersBracket $losersBracket -teamData $teamData

        if($playoffStandings.Count -eq 0){
            Write-Host "No playoff information available yet." -ForegroundColor Cyan
        }

        # Regular Season Standings berechnen
        $regularStandings = Get-RegularSeasonStandings -teamData $teamData -regularSeasonGames $regularSeasonGames

        if($regularStandings.Count -eq 0){
            Write-Host "No regular season information available yet." -ForegroundColor Cyan
        }

        # Awards berechnen
        $awards = Get-Awards -regularSeasonStandings $regularStandings -playoffsStandings $playoffStandings -previousSeasonStandings $previousSeasonStandings

        # --- Platzierungen in finale Struktur packen ---
        $standings = [PSCustomObject][ordered]@{
            Playoffs = $playoffStandings
            RegularSeason = $regularStandings
            Awards = $awards
        }

        Write-Host "Standings calculated." -ForegroundColor Yellow

        return $standings
    }
    catch {
         throw $_
    }    
}


# ===========================================================================
# File Utils
# ===========================================================================


function Get-StandingsLocal {

    $filePath = (Get-Config).StandingsFile

     # Prüfe ob Datei existiert
     if (-not (Test-Path $filePath)) {
        Write-Warning "Standings file not found at $filePath. Returning empty array."
        return @()
    }

    try {
        $data = Get-Content $FilePath -Raw | ConvertFrom-Json
        if ($data -is [array]) {
            return $data
        } else {
            return @($data)
        }
    }
    catch {
        Write-Warning "Could not read existing Standings.json: $_"
        return @()
    }
}

