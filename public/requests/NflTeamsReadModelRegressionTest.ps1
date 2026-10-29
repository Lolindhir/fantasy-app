$ErrorActionPreference = 'Stop'

# #347 F3c: Teams.json is generated from the canonical NFL team registry and keeps the former numeric IDs as LegacyIDs.

Import-Module "$PSScriptRoot\utils\general\NflTeamRegistryUtils.psm1" -ErrorAction Stop -Force

function Assert-Equal {
    param($Expected, $Actual, [string]$Message)
    if ($Expected -ne $Actual) { throw "$Message (expected '$Expected', got '$Actual')" }
}

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$registry = Get-NflTeamRegistry -RepoRoot $repoRoot
$model = @(New-NflTeamsReadModel -Registry $registry)

Assert-Equal $registry.Teams.Count $model.Count 'one Teams entry per registry team'
foreach ($team in $model) {
    $entry = $registry.Teams[[string]$team.ID]
    if ($null -eq $entry) { throw "Teams entry '$($team.ID)' is not a registry team" }
    Assert-Equal $team.ID $team.Abv 'Abv equals the canonical abbreviation'
    Assert-Equal $entry.Logo $team.Logo 'Logo comes from the registry'
    Assert-Equal $entry.Division $team.Division 'Division comes from the registry'
    foreach ($legacyId in @($team.LegacyIDs)) {
        Assert-Equal $team.ID (Resolve-NflTeamKey -Registry $registry -Value $legacyId) "LegacyID '$legacyId' resolves back to the team"
    }
}
Assert-Equal $model.Count (@($model | Select-Object -ExpandProperty ID -Unique)).Count 'IDs are unique'

# Deterministic and change detection.
$again = @(New-NflTeamsReadModel -Registry $registry)
if (Test-NflTeamsReadModelChanged -OldTeams $model -NewTeams $again) { throw 'identical models must not count as changed' }
$tampered = @($again | ForEach-Object { $_.PSObject.Copy() })
$tampered[0].LegacyIDs = @('999')
if (-not (Test-NflTeamsReadModelChanged -OldTeams $model -NewTeams $tampered)) { throw 'a LegacyIDs change must count as changed' }
if (-not (Test-NflTeamsReadModelChanged -OldTeams $null -NewTeams $model)) { throw 'a missing old file must count as changed' }

# Published file: same teams and legacy keys as the registry (stable identity data; presentation fields may lag one refresh).
$published = @(Get-Content (Join-Path $repoRoot 'public/data/Teams.json') -Raw | ConvertFrom-Json)
Assert-Equal $model.Count $published.Count 'published Teams.json lists every registry team'
foreach ($team in $published) {
    $entry = $registry.Teams[[string]$team.ID]
    if ($null -eq $entry) { throw "published Teams.json uses non-canonical ID '$($team.ID)'" }
    Assert-Equal ([string]$entry.LegacyAppTeamID) (@($team.LegacyIDs)[0]) "published LegacyIDs for $($team.ID)"
}

Write-Host 'NFL Teams read model regression checks passed.'
