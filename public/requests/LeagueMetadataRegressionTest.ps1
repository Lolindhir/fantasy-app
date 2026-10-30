$ErrorActionPreference = 'Stop'

Import-Module "$PSScriptRoot\utils\LeagueMetadataUtils.psm1" -ErrorAction Stop -Force

function Assert-Equal {
    param([AllowNull()]$Expected, [AllowNull()]$Actual, [string]$Message)
    if ("$Expected" -cne "$Actual") { throw "$Message Expected '$Expected', got '$Actual'." }
}

function Assert-Throws {
    param([scriptblock]$Action, [string]$Message)
    $threw = $false
    try { & $Action } catch { $threw = $true }
    if (-not $threw) { throw "$Message Expected an error." }
}

$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$manifest = Get-Content (Join-Path $repoRoot 'data-source/leagues/nfl-reise/manifest.json') -Raw | ConvertFrom-Json

# Repository metadata: current season has a Cap Deadline and every manifest season has the first model versions.
$all = Get-AllLeagueMetadata
$meta = $all['nfl-reise']
$season = [int]($manifest.CurrentCanonicalLeagueSeasonID -replace '^.*-', '')
$deadline = Get-LeagueCapDeadline -Metadata $meta -Season $season
if (-not $deadline.CapDeadline -or $null -eq $deadline.CapDeadlineBufferDays) { throw 'Current season needs CapDeadline and CapDeadlineBufferDays.' }
foreach ($s in $manifest.Seasons) {
    Assert-Equal 'salary-v1' (Get-LeagueSeasonModel -Metadata $meta -Season $s.Season -Kind 'Salary') "Salary model $($s.Season)."
    Assert-Equal 'standings-v1' (Get-LeagueSeasonModel -Metadata $meta -Season $s.Season -Kind 'Standings') "Standings model $($s.Season)."
    Assert-Equal 'awards-v1' (Get-LeagueSeasonModel -Metadata $meta -Season $s.Season -Kind 'Awards') "Awards model $($s.Season)."
    Assert-Equal 'lifecycle-v1' (Get-LeagueSeasonModel -Metadata $meta -Season $s.Season -Kind 'Lifecycle') "Lifecycle model $($s.Season)."
}
foreach ($retired in @('public/data/Metadata.json', 'public/data/Metadata.ai-doc.yaml', 'data-source/leagues/_bootstrap', 'public/requests/config.ps1')) {
    if (Test-Path (Join-Path $repoRoot $retired)) { throw "Retired legacy path still exists: $retired" }
}

# Fail-closed behavior and multi-league iteration on fixtures.
$tmp = Join-Path ([System.IO.Path]::GetTempPath()) ("league-meta-" + [guid]::NewGuid().ToString('N'))
try {
    foreach ($id in @('alpha', 'beta')) {
        $dir = Join-Path $tmp $id
        New-Item -ItemType Directory -Path $dir | Out-Null
        $copy = Get-Content (Join-Path $repoRoot 'data-meta/nfl-reise/metadata.json') -Raw | ConvertFrom-Json
        $copy.CanonicalLeagueID = $id
        $copy | ConvertTo-Json -Depth 10 | Out-File (Join-Path $dir 'metadata.json') -Encoding UTF8
    }
    Assert-Equal 'alpha,beta' ((Get-AllLeagueMetadata -Root $tmp).Keys -join ',') 'Multi-league iteration.'
    Assert-Throws { Get-LeagueMetadata -LeagueId 'gamma' -Root $tmp } 'Missing league file.'
    Assert-Throws { Get-LeagueSeasonEntry -Metadata (Get-LeagueMetadata -LeagueId 'alpha' -Root $tmp) -Season 1999 } 'Missing season.'

    $bad = Get-Content (Join-Path $tmp 'alpha/metadata.json') -Raw | ConvertFrom-Json
    $bad.Seasons.'2026'.Models.Salary = 'salary-v99'
    $bad | ConvertTo-Json -Depth 10 | Out-File (Join-Path $tmp 'alpha/metadata.json') -Encoding UTF8
    Assert-Throws { Get-LeagueMetadata -LeagueId 'alpha' -Root $tmp } 'Unknown model ID.'
}
finally {
    Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host 'LeagueMetadataRegressionTest passed.'
