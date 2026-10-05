$ErrorActionPreference = 'Stop'

Import-Module "$PSScriptRoot\utils\general\NflTeamRegistryUtils.psm1" -ErrorAction Stop -Force

function Assert-Equal {
    param($Expected, $Actual, [string]$Message)
    if ($Expected -ne $Actual) { throw "$Message (expected '$Expected', got '$Actual')" }
}

function Assert-Throws {
    param([scriptblock]$Action, [string]$Message)
    $threw = $false
    try { & $Action | Out-Null } catch { $threw = $true }
    if (-not $threw) { throw $Message }
}

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$registry = Get-NflTeamRegistry -RepoRoot $repoRoot

Assert-Equal 32 $registry.Teams.Count 'registry must list 32 teams'
Assert-Equal 'LA' (Resolve-NflTeamKey -Registry $registry -Value 'LA') 'canonical key'
Assert-Equal 'LA' (Resolve-NflTeamKey -Registry $registry -Value 'lar') 'provider spelling LAR'
Assert-Equal 'WAS' (Resolve-NflTeamKey -Registry $registry -Value 'WSH') 'provider spelling WSH'
Assert-Equal 'LA' (Resolve-NflTeamKey -Registry $registry -Value '19') 'legacy app team ID'
Assert-Equal 'LV' (Resolve-NflTeamKey -Registry $registry -Value 'OAK' -Season 2019) 'historical alias inside its seasons'
Assert-Throws { Resolve-NflTeamKey -Registry $registry -Value 'OAK' -Season 2020 } 'historical alias after its last season must fail'
Assert-Throws { Resolve-NflTeamKey -Registry $registry -Value 'STL' } 'historical alias without season must fail'
Assert-Throws { Resolve-NflTeamKey -Registry $registry -Value 'XXX' } 'unknown key must fail'
Assert-Throws { Resolve-NflTeamKey -Registry $registry -Value '' } 'empty key must fail'

Write-Host 'NFL team registry regression checks passed.'
