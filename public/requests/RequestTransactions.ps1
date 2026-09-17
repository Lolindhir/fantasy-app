# ===========================================================================
# Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\utils\league\CanonicalTransactionUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\league\DraftTransactionPipelineUtils.psm1" -ErrorAction Stop -Force
}
catch {
    Write-Error "Fehler beim Laden der Module: $_"
    exit 1
}

# ===========================================================================
# Funktionen
# ===========================================================================

function Invoke-PastSeasonsIndexRefresh {
    Write-Host "Refreshing PastSeasonsIndex.json..." -ForegroundColor Yellow
    & "$PSScriptRoot\RequestPastSeasonsIndex.ps1"

    if (-not $?) {
        throw "RequestPastSeasonsIndex.ps1 failed."
    }
}

# ===========================================================================
# Logik
# ===========================================================================

$CanonicalLeagueID = "nfl-reise"

# Current season is rebuilt from canonical League source-data. Historical
# transaction files remain on the existing Sleeper compatibility path until their
# own Phase-2 migration checkpoint.
Update-TransactionsAllSeasonsCanonicalCurrent `
    -CanonicalLeagueID $CanonicalLeagueID `
    -ForceHistory

# Abhängige Draft-Outputs werden im selben Working Tree aus den frisch erzeugten
# Transactions aufgebaut; erst danach werden konkrete Pickdetails zurückgeschrieben.
$pipelineResult = Invoke-DraftTransactionRebuild -ForceHistory

Invoke-PastSeasonsIndexRefresh

if ($pipelineResult.Drafts -or $pipelineResult.HistoricalDrafts) {
    Write-Host "Transactions and dependent drafts rebuilt." -ForegroundColor Green
} else {
    Write-Host "Transactions rebuilt; no draft output generated." -ForegroundColor Yellow
}
