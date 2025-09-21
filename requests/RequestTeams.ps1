# --- Konfiguration ---
$RapidAPIKey = "cccff76c4bmsh01946acbc2d3c0bp141721jsn161bd86f4c69"

# --- Tank01: Teams ---
Write-Host "Hole Teams..." -ForegroundColor Yellow
$tankTeamsUrl = "https://tank01-nfl-live-in-game-real-time-statistics-nfl.p.rapidapi.com/getNFLTeams"
$tankHeaders = @{
    "X-RapidAPI-Key" = $RapidAPIKey
    "X-RapidAPI-Host" = "tank01-nfl-live-in-game-real-time-statistics-nfl.p.rapidapi.com"
}
$tankTeamsResponse = Invoke-RestMethod -Uri $tankTeamsUrl -Headers $tankHeaders
$tankTeams = $tankTeamsResponse.body
Write-Host "Teams gefunden: $($tankTeams.Count)" -ForegroundColor Yellow


# --- Team JSON vorbereiten ---
Write-Host "Erstelle Teams.json..." -ForegroundColor Yellow

$teamData = @()
foreach ($tankEntry in $tankTeams) {

    $teamData += [PSCustomObject]@{
        ID      = $tankEntry.teamID
        Name    = $tankEntry.teamName
        Abv     = $tankEntry.teamAbv
        City    = $tankEntry.teamCity
        Logo    = $tankEntry.nflComLogo1
        Conference = $tankEntry.conference
        ConferenceAbv = $tankEntry.conferenceAbv
        Division = $tankEntry.division
    }

}

# Verzeichnis des Skripts
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Ziel-Datei im data-Ordner parallel zum Requests-Ordner
$targetFile = Join-Path $scriptDir "..\data\Teams.json"

# JSON schreiben
$teamData | ConvertTo-Json -Depth 5 | Out-File $targetFile -Encoding UTF8
Write-Host "Teams.json gespeichert!" -ForegroundColor Green
