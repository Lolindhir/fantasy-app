# ===========================================================================
# Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\utils\ConfigUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\DraftUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\DraftDisplayStatusUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\DraftHistoryUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\DraftHistoryEmptyDefinitionsFix.psm1" -ErrorAction Stop -Force
}
catch {
    Write-Error "Fehler beim Laden der Module: $_"
    exit 1
}

# ===========================================================================
# Funktionen
# ===========================================================================

function Test-PastSeasonsWorkingTreeChanged {
    param([Parameter(Mandatory = $true)][hashtable]$Config)

    $gitCommand = Get-Command git -ErrorAction SilentlyContinue
    if (-not $gitCommand) {
        Write-Warning "Git command not available; skipping automatic past seasons index refresh check."
        return $false
    }

    $pastSeasonsPath = "public/data/past_seasons"
    $repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")

    Push-Location $repoRoot
    try {
        $status = @(git status --porcelain -- $pastSeasonsPath)
        return $status.Count -gt 0
    }
    finally {
        Pop-Location
    }
}

function Invoke-PastSeasonsIndexRefreshIfChanged {
    param([Parameter(Mandatory = $true)][hashtable]$Config)

    if (-not (Test-PastSeasonsWorkingTreeChanged -Config $Config)) {
        Write-Host "No past season file changes detected; skipping past seasons index refresh." -ForegroundColor Cyan
        return
    }

    Write-Host "Past season file changes detected; refreshing PastSeasonsIndex.json..." -ForegroundColor Yellow
    & "$PSScriptRoot\RequestPastSeasonsIndex.ps1"

    if ($LASTEXITCODE -ne 0) {
        throw "RequestPastSeasonsIndex.ps1 failed with exit code $LASTEXITCODE."
    }
}

# ===========================================================================
# Logik
# ===========================================================================

$config = Get-Config

$drafts = Update-Drafts
if ($drafts) {
    $drafts = Set-DraftDisplayStatuses -drafts $drafts
    Save-Drafts -drafts $drafts
}

$historicalDrafts = Update-DraftsHistoricalSeasonsSafe
Invoke-PastSeasonsIndexRefreshIfChanged -Config $config

if ($drafts) {
    Write-Host "Current drafts updated." -ForegroundColor Green
} else {
    Write-Host "No current drafts generated." -ForegroundColor Yellow
}

if ($historicalDrafts) {
    Write-Host "Historical drafts updated." -ForegroundColor Green
} else {
    Write-Host "No historical drafts generated." -ForegroundColor Yellow
}
