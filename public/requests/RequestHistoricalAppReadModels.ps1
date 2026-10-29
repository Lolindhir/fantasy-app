# Regenerates the historical App read models from canonical facts (Issue #1189, pattern of ADR-058):
#   public/data/past_seasons/Matchups/Matchups_<season>.json
#   public/data/past_seasons/FantasyGameContext/FantasyGameContext_<season>.json
# Files are rewritten only on a semantic difference; an existing file is never an input.
param(
    [string]$CanonicalLeagueID = ''
)

try {
    Import-Module "$PSScriptRoot\utils\general\CanonicalScheduleUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\FantasyGameContextUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\MatchupReadModelUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\StandingUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\PastSeasonsIndexUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\ConfigUtils.psm1" -ErrorAction Stop -Force
}
catch {
    Write-Error "Could not load historical read-model modules. $_"
    exit 1
}

try {
    $config = Get-Config
    if ([string]::IsNullOrWhiteSpace($CanonicalLeagueID)) { $CanonicalLeagueID = [string]$config.CanonicalLeagueID }
    $currentSeason = [int]$config.LeagueYear
    $repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))

    # Neutral team order still comes from Standings.json until the league-standings product is the consumer source (Issue #987).
    $standings = @(Get-StandingsLocal)

    $matchupsChanged = Update-MatchupHistoryReadModels `
        -CanonicalLeagueID $CanonicalLeagueID `
        -CurrentSeason $currentSeason `
        -Standings $standings `
        -Config $config

    $contextChanged = Update-FantasyGameContextHistory `
        -CanonicalLeagueID $CanonicalLeagueID `
        -CurrentSeason $currentSeason `
        -Config $config `
        -RepoRoot $repoRoot

    Update-PastSeasonsIndex -Config $config | Out-Null
    Write-Host "Historical App read models done (Matchups changed: $([bool]$matchupsChanged), FantasyGameContext changed: $([bool]$contextChanged))." -ForegroundColor Green
    exit 0
}
catch {
    Write-Error "Historical App read-model regeneration failed: $_"
    exit 1
}
