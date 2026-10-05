# Generates public/data/Teams.json from the canonical NFL team registry (source-data/nfl/teams.json, #347 F3c).
# No provider call: identity, names, division and logo come from the registry, LegacyIDs keep the former numeric app IDs.

Import-Module "$PSScriptRoot\utils\general\NflTeamRegistryUtils.psm1" -ErrorAction Stop -Force

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent (Split-Path -Parent $scriptDir)
$targetFile = Join-Path $scriptDir "..\data\Teams.json"
$backupDir = Join-Path $scriptDir "..\data\backup"
if (!(Test-Path $backupDir)) { New-Item -ItemType Directory -Path $backupDir -Force | Out-Null }

Write-Host "Creating Teams.json from the canonical NFL team registry..." -ForegroundColor Yellow
try {
    $registry = Get-NflTeamRegistry -RepoRoot $repoRoot
    $newTeams = New-NflTeamsReadModel -Registry $registry
} catch {
    Write-Error "Error reading the NFL team registry: $_"
    exit 1
}
Write-Host "Teams found: $($newTeams.Count)" -ForegroundColor Yellow

$oldTeams = $null
if (Test-Path $targetFile) {
    $oldJsonRaw = Get-Content $targetFile -Raw
    if ($oldJsonRaw) { $oldTeams = @($oldJsonRaw | ConvertFrom-Json) }
}

if (Test-NflTeamsReadModelChanged -OldTeams $oldTeams -NewTeams $newTeams) {
    Write-Host "Changes detected - updating file." -ForegroundColor Green
}
else {
    Write-Host "No changes - update skipped." -ForegroundColor Cyan
    exit 0
}

$TimeSnapshot = (Get-Date)

if (Test-Path $targetFile) {
    $timestamp = $TimeSnapshot.ToUniversalTime().ToString("yyyyMMdd_HHmmss")
    Copy-Item $targetFile -Destination (Join-Path $backupDir "Teams_$timestamp.json") -Force
    Write-Host "Backup of old Teams.json created." -ForegroundColor Green
}

try {
    $newTeams | ConvertTo-Json -Depth 5 | Out-File $targetFile -Encoding UTF8
    Write-Host "Teams.json saved!" -ForegroundColor Green
} catch {
    Write-Error "Error writing Teams.json: $_"
    exit 1
}

$TimestampFile = Join-Path $scriptDir "..\data\Timestamps.json"
$Now = $TimeSnapshot.ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
if (Test-Path $TimestampFile) {
    $Timestamps = Get-Content $TimestampFile | ConvertFrom-Json
} else {
    $Timestamps = @{}
}
$Timestamps.Teams = $Now
$Timestamps | ConvertTo-Json -Depth 3 | Set-Content $TimestampFile
Write-Host "Teams-Timestamp updated: $Now" -ForegroundColor Green
