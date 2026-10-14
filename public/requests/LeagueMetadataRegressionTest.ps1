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
$legacy = Get-Content (Join-Path $repoRoot 'public/data/Metadata.json') -Raw | ConvertFrom-Json
$manifest = Get-Content (Join-Path $repoRoot 'source-data/leagues/nfl-reise/manifest.json') -Raw | ConvertFrom-Json

# Parity: every legacy Metadata.json field has the same value in the loader result.
$all = Get-AllLeagueMetadata
$meta = $all['nfl-reise']
Assert-Equal $legacy.LeagueID $meta.CurrentProviderLeagueID 'LeagueID parity.'
Assert-Equal $legacy.LeagueTimeZone $meta.LeagueTimeZone 'LeagueTimeZone parity.'
Assert-Equal ($legacy.OwnerIDs | ConvertTo-Json -Compress) ($meta.Owners | ConvertTo-Json -Compress) 'OwnerIDs parity.'
Assert-Equal ($legacy.Drafts | ConvertTo-Json -Depth 10 -Compress) ($meta.Drafts | ConvertTo-Json -Depth 10 -Compress) 'Drafts parity.'
$season = [int]($manifest.CurrentCanonicalLeagueSeasonID -replace '^.*-', '')
Assert-Equal $legacy.LeagueYear $season 'LeagueYear equals the manifest current season.'
$deadline = Get-LeagueCapDeadline -Metadata $meta -Season $season
Assert-Equal ([datetime]$legacy.CapDeadline).ToUniversalTime().ToString('o') ([datetime]$deadline.CapDeadline).ToUniversalTime().ToString('o') 'CapDeadline parity.'
Assert-Equal $legacy.CapDeadlineBufferDays $deadline.CapDeadlineBufferDays 'CapDeadlineBufferDays parity.'
foreach ($s in $manifest.Seasons) {
    Assert-Equal 'salary-v1' (Get-LeagueSeasonModel -Metadata $meta -Season $s.Season -Kind 'Salary') "Salary model $($s.Season)."
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
