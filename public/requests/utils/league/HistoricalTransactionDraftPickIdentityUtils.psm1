# ===========================================================================
# Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\..\ConfigUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\DraftUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\DraftHistoryUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\DraftHistoryEmptyDefinitionsFix.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\TransactionDraftPickEnrichmentUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\LeagueUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\invoke\SleeperUtils.psm1" -ErrorAction Stop -Force
}
catch {
    Write-Error "Fehler beim Laden der Module: $_"
    throw $_
}

# ===========================================================================
# Historical transaction draft identity
# ===========================================================================

function New-HistoricalTransactionDraftPickSleeperContext {
    param(
        [Parameter(Mandatory = $true)][object]$definition,
        [AllowEmptyCollection()][array]$tradedPicks = @()
    )

    $sleeperDraft = $definition.SleeperDraft
    $draftID = [string](Get-DraftObjectProperty -object $sleeperDraft -propertyName "draft_id" -defaultValue "")

    return [PSCustomObject][ordered]@{
        Season         = [string]$definition.Season
        DraftType      = [string]$definition.DraftType
        DraftInstance  = [int]$definition.DraftInstance
        DraftCode      = [string]$definition.DraftCode
        DraftKey       = [string]$definition.DraftKey
        SleeperDraftID = $draftID
        TradedPicks    = @($tradedPicks)
    }
}

function Get-HistoricalTransactionDraftPickSleeperContexts {
    param([string]$leagueID = (Get-Config).LeagueID)

    $draftTypeConfigs = Get-DraftHistoryTypeConfigs
    $leagues = ConvertTo-DraftSafeArray -value (Get-LeaguesRecursive -leagueID $leagueID)
    $contextsByIdentity = @{}

    foreach ($league in $leagues) {
        $definitions = Get-SleeperCompletedDraftDefinitionsForLeagueSafe `
            -league $league `
            -draftTypeConfigs $draftTypeConfigs

        foreach ($definition in (ConvertTo-DraftSafeArray -value $definitions)) {
            $draftID = [string](Get-DraftObjectProperty -object $definition.SleeperDraft -propertyName "draft_id" -defaultValue "")
            $tradedPicks = @()

            if (-not [string]::IsNullOrWhiteSpace($draftID)) {
                try {
                    $tradedPicks = ConvertTo-DraftSafeArray -value (Get-SleeperDraftTradedPicks -draftID $draftID)
                }
                catch {
                    Write-Warning "Could not load traded picks for completed Sleeper draft '$draftID'. $_"
                }
            }

            $context = New-HistoricalTransactionDraftPickSleeperContext `
                -definition $definition `
                -tradedPicks $tradedPicks
            $identityKey = "$($context.DraftKey)|$($context.SleeperDraftID)"
            $contextsByIdentity[$identityKey] = $context
        }
    }

    return @(
        $contextsByIdentity.Values |
            Sort-Object @{ Expression = { [int]$_.Season }; Ascending = $true }, DraftKey, SleeperDraftID
    )
}

function Update-HistoricalTransactionDraftPickTypesFromCompletedDrafts {
    param([string]$leagueID = (Get-Config).LeagueID)

    Write-Host "Resolve historical transaction draft identities from completed draft definitions..." -ForegroundColor Yellow

    $contexts = Get-HistoricalTransactionDraftPickSleeperContexts -leagueID $leagueID
    if ($contexts.Count -eq 0) {
        Write-Host "No completed draft contexts found for historical transaction identity resolution." -ForegroundColor DarkGray
        return
    }

    foreach ($file in (Get-TransactionDraftPickTransactionFiles | Where-Object { -not $_.IsCurrent })) {
        $transactions = Get-TransactionDraftPickJsonFileContent -filePath $file.Path -description "Historical transactions"
        if ($transactions.Count -eq 0) { continue }

        $result = Resolve-TransactionDraftPickTypesFromContexts `
            -transactions $transactions `
            -contexts $contexts

        if ($result.Changed) {
            Save-TransactionDraftPickTransactions `
                -filePath $file.Path `
                -transactions @($result.Transactions) `
                -isCurrent $false
        }
    }

    Write-Host "Historical transaction draft identity resolution finished." -ForegroundColor DarkCyan
}
