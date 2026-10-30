$ErrorActionPreference = 'Stop'

try {
    Import-Module "$PSScriptRoot\utils\ConfigUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\general\FileUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\WeeklyRecapUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\StandingUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\PastSeasonsIndexUtils.psm1" -ErrorAction Stop -Force
}
catch {
    Write-Error "Failed to load WeeklyRecaps modules: $_"
    exit 1
}

try {
    $config = Get-Config
    $canonicalLeagueID = 'nfl-reise'
    if (-not (Test-Path $config.MatchupsFile)) { throw "Matchups.json is required before WeeklyRecaps generation." }
    $repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))

    $matchups = Get-Content $config.MatchupsFile -Raw | ConvertFrom-Json
    # #503 neutral team order comes from the league-standings product (Issue #987), not from the rendered Standings.json.
    $standings = @(Get-LeagueStandingsProduct -CanonicalLeagueID $canonicalLeagueID -RepoRoot $repoRoot)
    $season = [int]$matchups.Season

    $model = New-WeeklyRecapSeasonReadModel `
        -CanonicalLeagueID $canonicalLeagueID `
        -Season $season `
        -MatchupsReadModel $matchups `
        -Standings $standings `
        -IdentityScheduleFile $config.ScheduleFile

    $compare = {
        param($oldRecaps, $newRecaps)
        Test-WeeklyRecapsReadModelChanged -OldData $oldRecaps -NewData $newRecaps
    }
    Save-JsonFile `
        -TargetFile $config.WeeklyRecapsFile `
        -Type 'WeeklyRecaps' `
        -Data $model `
        -CompareScript $compare `
        -UpdateTimestamp

    Update-WeeklyRecapHistoryReadModels `
        -CanonicalLeagueID $canonicalLeagueID `
        -CurrentSeason $season `
        -Standings $standings `
        -Config $config | Out-Null

    Update-PastSeasonsIndex -Config $config | Out-Null
    exit 0
}
catch {
    Write-Error "WeeklyRecaps generation failed: $_"
    exit 1
}
