# ===========================================================================
# Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\..\ConfigUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\general\FileUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\invoke\SleeperUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\DraftUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\DraftCompareUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\DraftOrderAwareUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\TransactionUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\TransactionDraftPickEnrichmentUtils.psm1" -ErrorAction Stop -Force
}
catch {
    Write-Error "Fehler beim Laden der Module: $_"
    throw $_
}

# ===========================================================================
# League refresh: current transactions in memory
# ===========================================================================

function Get-LeagueTransactionsCurrentSeasonInMemory {
    param(
        [string]$leagueID = (Get-Config).LeagueID
    )

    Write-Host "Build current season transactions in memory for league refresh..." -ForegroundColor Yellow

    $league = Get-SleeperLeague -leagueID $leagueID
    $season = [string]$league.season
    $maxWeekToFetch = Get-CurrentTransactionMaxWeek -league $league
    $existingTransactions = Get-TransactionsLocalForCurrentSeason

    $weeksToFetch = Get-WeeksToFetch `
        -existingTransactions $existingTransactions `
        -maxWeek $maxWeekToFetch

    if (-not $weeksToFetch -or $weeksToFetch.Count -eq 0) {
        Write-Host "No transaction weeks need to be refreshed." -ForegroundColor DarkCyan
        return @($existingTransactions)
    }

    Write-Host "Weeks to fetch: $($weeksToFetch -join ', ')" -ForegroundColor Yellow

    $remoteTransactions = Get-TransactionsRemoteForWeeks `
        -leagueID $leagueID `
        -season $season `
        -weeks $weeksToFetch

    $mergedTransactions = Merge-TransactionsForWeeks `
        -existingTransactions $existingTransactions `
        -newTransactions $remoteTransactions `
        -weeksToReplace $weeksToFetch

    Write-Host "Current season transaction candidate built in memory." -ForegroundColor DarkCyan
    return @($mergedTransactions)
}

function Resolve-LeagueTransactionDraftPickTypesInMemory {
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [array]$transactions,

        [string]$leagueID = (Get-Config).LeagueID
    )

    $contexts = Get-TransactionDraftPickSleeperDraftContexts -leagueID $leagueID
    $result = Resolve-TransactionDraftPickTypesFromContexts `
        -transactions $transactions `
        -contexts $contexts

    return @($result.Transactions)
}

# ===========================================================================
# League refresh: drafts from the same in-memory transaction snapshot
# ===========================================================================

function Update-LeagueDraftsOrderAwareFromTransactions {
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [array]$transactions,

        [string]$leagueID = (Get-Config).LeagueID
    )

    Write-Host "Update current and open drafts from in-memory transactions..." -ForegroundColor Yellow

    $config = Get-Config
    $draftsConfig = $config.DraftsConfig
    if ($null -eq $draftsConfig) { throw "Metadata Drafts configuration missing." }

    $upcomingDraftCountMode = [string](Get-DraftObjectProperty -object $draftsConfig -propertyName "UpcomingDraftCountMode" -defaultValue "PerDraftType")
    if ($upcomingDraftCountMode -ne "PerDraftType") { throw "Unsupported UpcomingDraftCountMode '$upcomingDraftCountMode'. Only 'PerDraftType' is supported." }

    $openDraftCountPerType = [int]$draftsConfig.UpcomingDraftCount
    if ($openDraftCountPerType -lt 1) { throw "UpcomingDraftCount must be at least 1." }

    $draftTypeConfigs = @(ConvertTo-DraftSafeArray -value $draftsConfig.Types | Sort-Object DraftNo)
    if ($draftTypeConfigs.Count -eq 0) { throw "No draft types configured in Metadata.json." }
    Assert-DraftTypeConfigs -draftTypeConfigs $draftTypeConfigs

    $league = Get-DraftLeagueLocal
    $standings = Get-DraftStandingsLocal
    $sleeperDraftMap = Get-SleeperDraftMap -draftTypeConfigs $draftTypeConfigs -leagueID $leagueID
    $definitions = Get-CurrentAndOpenDraftDefinitionsOrderAware `
        -draftTypeConfigs $draftTypeConfigs `
        -sleeperDraftMap $sleeperDraftMap `
        -leagueYear ([int]$config.LeagueYear) `
        -openDraftCountPerType $openDraftCountPerType

    $drafts = @()
    foreach ($definition in $definitions) {
        $drafts += New-DraftOutputOrderAware `
            -definition $definition `
            -league $league `
            -standings $standings `
            -transactions $transactions
    }

    $drafts = @($drafts | Sort-Object @{ Expression = { [int]$_.Season }; Ascending = $true }, DraftNo)
    $compare = ${function:Compare-DraftsFieldBased}
    Save-JsonFile `
        -Type "Drafts" `
        -Data $drafts `
        -CompareScript $compare `
        -CreateBackup `
        -UpdateTimestamp

    Write-Host "Current and open drafts update from in-memory transactions finished." -ForegroundColor DarkCyan
    return $drafts
}

function Add-LeagueTransactionDraftPickDetailsInMemory {
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [array]$transactions,

        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [array]$drafts
    )

    $result = Add-TransactionDraftPickDetailsFromDrafts `
        -transactions $transactions `
        -drafts $drafts

    return @($result.Transactions)
}
