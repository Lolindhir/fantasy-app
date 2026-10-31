$ErrorActionPreference = 'Stop'

# #347 F3b: NFL team joins tolerate canonical abbreviations, provider spellings and legacy numeric app IDs on either side.

Import-Module "$PSScriptRoot\utils\general\NflTeamRegistryUtils.psm1" -ErrorAction Stop -Force

function Assert-Equal {
    param($Expected, $Actual, [string]$Message)
    if ($Expected -ne $Actual) { throw "$Message (expected '$Expected', got '$Actual')" }
}

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$registry = Get-NflTeamRegistry -RepoRoot $repoRoot

# Derive the fixture teams from the registry instead of hard-wiring them.
$teams = @($registry.Teams.Values | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_.LegacyAppTeamID) } | Sort-Object TeamAbbr | Select-Object -First 3)
$awayAbbr = [string]$teams[0].TeamAbbr; $awayLegacy = [string]$teams[0].LegacyAppTeamID
$homeAbbr = [string]$teams[1].TeamAbbr; $homeLegacy = [string]$teams[1].LegacyAppTeamID
$byeAbbr = [string]$teams[2].TeamAbbr; $byeLegacy = [string]$teams[2].LegacyAppTeamID

# Join key behavior
Assert-Equal $awayAbbr (Get-NflTeamJoinKey -Value $awayLegacy) 'legacy ID resolves to the abbreviation'
Assert-Equal $awayAbbr (Get-NflTeamJoinKey -Value " $($awayAbbr.ToLowerInvariant()) ") 'abbreviation is trimmed and case-insensitive'
Assert-Equal 'NOT-A-TEAM' (Get-NflTeamJoinKey -Value 'NOT-A-TEAM') 'unresolvable keys stay unchanged (tolerant)'
if ($null -ne (Get-NflTeamJoinKey -Value '  ')) { throw 'blank key must yield null' }

# The four legacy/canonical schedule/player combinations and unknown team
# case now run in tools/tests/test_decision_windows.py (Fast league-pwf-twp).
# The independent PowerShell registry normalization checks above remain.

Write-Host 'NFL team key join regression checks passed.'
