param(
    [int]$Season = 0,
    [string]$CanonicalLeagueID = 'nfl-reise'
)

try {
    Import-Module "$PSScriptRoot\utils\ConfigUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\FantasyGameContextUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\PastSeasonsIndexUtils.psm1" -ErrorAction Stop -Force
}
catch {
    Write-Error "Could not load FantasyGameContext history modules. $_"
    exit 1
}

try {
    $config = Get-Config
    if ($Season -le 0) { $Season = [int]$config.LeagueYear - 1 }

    $repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))
    $seasonSourceDir = Join-Path $repoRoot "source-data\leagues\$CanonicalLeagueID\seasons\$Season"
    $leagueSourceFile = Join-Path $seasonSourceDir 'league.json'
    $matchupDirectory = Join-Path $seasonSourceDir 'matchups'
    $scheduleFile = Join-Path $config.PastSeasonsDir "Schedule_$Season.json"
    $playersFile = Join-Path $config.PastSeasonsDir "Players_$Season.json"
    $weeklyRosterDirectory = Join-Path $repoRoot "source-data\nfl\weekly-rosters\$Season"
    $targetDir = Join-Path $config.PastSeasonsDir 'FantasyGameContext'
    $targetFile = Join-Path $targetDir "FantasyGameContext_$Season.json"

    $context = New-HistoricalFantasyGameContextSeason `
        -LeagueID $CanonicalLeagueID `
        -Season $Season `
        -LeagueSourceFile $leagueSourceFile `
        -MatchupDirectory $matchupDirectory `
        -ScheduleFile $scheduleFile `
        -HistoricalPlayersFile $playersFile `
        -WeeklyRosterDirectory $weeklyRosterDirectory

    if (-not (Test-Path $targetDir)) { New-Item -ItemType Directory -Path $targetDir -Force | Out-Null }
    $context | ConvertTo-Json -Depth 20 | Out-File $targetFile -Encoding UTF8
    Update-PastSeasonsIndex -Config $config | Out-Null

    Write-Host "Historical FantasyGameContext written: $targetFile" -ForegroundColor Green
    exit 0
}
catch {
    Write-Error "Historical FantasyGameContext rebuild failed: $_"
    exit 1
}
