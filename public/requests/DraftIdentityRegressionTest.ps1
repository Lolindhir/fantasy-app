$ErrorActionPreference = "Stop"

Import-Module "$PSScriptRoot\utils\league\DraftUtils.psm1" -Force
Import-Module "$PSScriptRoot\utils\league\TransactionDraftPickEnrichmentUtils.psm1" -Force

function Assert-Equal {
    param(
        [AllowNull()]$Actual,
        [AllowNull()]$Expected,
        [Parameter(Mandatory = $true)][string]$Message
    )

    if ($Actual -ne $Expected) {
        throw "$Message Expected '$Expected', got '$Actual'."
    }
}

function Assert-Null {
    param(
        [AllowNull()]$Actual,
        [Parameter(Mandatory = $true)][string]$Message
    )

    if ($null -ne $Actual -and -not [string]::IsNullOrWhiteSpace([string]$Actual)) {
        throw "$Message Expected null/empty, got '$Actual'."
    }
}

function Assert-Throws {
    param(
        [Parameter(Mandatory = $true)][scriptblock]$Action,
        [Parameter(Mandatory = $true)][string]$ExpectedMessagePart,
        [Parameter(Mandatory = $true)][string]$Message
    )

    $threw = $false
    try {
        & $Action | Out-Null
    }
    catch {
        $threw = $true
        if ([string]$_.Exception.Message -notlike "*$ExpectedMessagePart*") {
            throw "$Message Unexpected error: $($_.Exception.Message)"
        }
    }

    if (-not $threw) {
        throw "$Message Expected an exception containing '$ExpectedMessagePart'."
    }
}

# First instances keep the historical public keys; later instances add a suffix.
Assert-Equal -Actual (New-DraftKey -season "2035" -draftType "Free_Agent" -draftInstance 1) -Expected "2035_Free_Agent" -Message "First Free Agent instance key changed."
Assert-Equal -Actual (New-DraftKey -season "2035" -draftType "Free_Agent" -draftInstance 2) -Expected "2035_Free_Agent_2" -Message "Second Free Agent instance key is not unique."
Assert-Equal -Actual (New-DraftCode -draftType "Free_Agent" -draftInstance 1) -Expected "Free_Agent" -Message "First instance code changed."
Assert-Equal -Actual (New-DraftCode -draftType "Free_Agent" -draftInstance 2) -Expected "Free_Agent_2" -Message "Second instance code is not unique."

$instanceConfigs = @(
    [PSCustomObject]@{ DraftType = "Free_Agent"; DraftInstance = 1; DraftNo = 1; Rounds = 5 },
    [PSCustomObject]@{ DraftType = "Free_Agent"; DraftInstance = 2; DraftNo = 2; Rounds = 5 }
)
Assert-DraftTypeConfigs -draftTypeConfigs $instanceConfigs
$secondIdentity = Get-DraftIdentityFromKey -draftKey "2035_Free_Agent_2" -draftTypeConfigs $instanceConfigs
Assert-Equal -Actual $secondIdentity.DraftType -Expected "Free_Agent" -Message "DraftType was not preserved for instance 2."
Assert-Equal -Actual $secondIdentity.DraftInstance -Expected 2 -Message "DraftInstance was not resolved from DraftKey."

# The future Sleeper pick owner is configuration-driven rather than hard-coded
# to Rookie. This makes a future league-rule change a Metadata change only.
$alternateFuturePoolConfigs = @(
    [PSCustomObject]@{ DraftType = "Rookie"; DraftInstance = 1; DraftNo = 1; Rounds = 5; SleeperFuturePickPool = $false },
    [PSCustomObject]@{ DraftType = "Free_Agent"; DraftInstance = 1; DraftNo = 2; Rounds = 5; SleeperFuturePickPool = $true }
)
$alternateFuturePool = Get-SleeperFuturePickDraftTypeConfig -draftTypeConfigs $alternateFuturePoolConfigs
Assert-Equal -Actual $alternateFuturePool.DraftType -Expected "Free_Agent" -Message "Future Sleeper pick pool was hard-coded instead of following configuration."

Assert-Throws `
    -Action {
        Get-SleeperFuturePickDraftTypeConfig -draftTypeConfigs @(
            [PSCustomObject]@{ DraftType = "Rookie"; DraftInstance = 1; DraftNo = 1; Rounds = 5; SleeperFuturePickPool = $true },
            [PSCustomObject]@{ DraftType = "Free_Agent"; DraftInstance = 1; DraftNo = 2; Rounds = 5; SleeperFuturePickPool = $true }
        )
    } `
    -ExpectedMessagePart "Multiple draft instances are configured as SleeperFuturePickPool" `
    -Message "Multiple future Sleeper pick pools were not rejected."

# A manually declared sibling asset claims its concrete draft context. The same
# movement from the Sleeper league transaction must then resolve to the other
# matching draft instead of being guessed by source type.
$sleeperPick = [PSCustomObject][ordered]@{
    DraftType             = $null
    DraftInstance         = $null
    DraftCode             = $null
    DraftSource           = "Sleeper"
    DraftKey              = $null
    Season                = "2026"
    Round                 = 1
    OriginalOwnerRosterID = 1
    PreviousOwnerRosterID = 1
    NewOwnerRosterID      = 5
}
$manualPick = [PSCustomObject][ordered]@{
    DraftType             = "Free_Agent"
    DraftInstance         = 1
    DraftCode             = "Free_Agent"
    DraftSource           = "Manual"
    DraftKey              = "2026_Free_Agent"
    Season                = "2026"
    Round                 = 1
    OriginalOwnerRosterID = 1
    PreviousOwnerRosterID = 1
    NewOwnerRosterID      = 5
}
$transaction = [PSCustomObject][ordered]@{
    TransactionID = "test-transaction"
    DraftPicks    = @($sleeperPick, $manualPick)
}
$movement = [PSCustomObject][ordered]@{
    season            = "2026"
    round             = 1
    roster_id         = 1
    previous_owner_id = 1
    owner_id          = 5
}
$contexts = @(
    [PSCustomObject][ordered]@{
        Season         = "2026"
        DraftType      = "Rookie"
        DraftInstance  = 1
        DraftCode      = "Rookie"
        DraftKey       = "2026_Rookie"
        SleeperDraftID = "rookie-draft"
        TradedPicks    = @($movement)
    },
    [PSCustomObject][ordered]@{
        Season         = "2026"
        DraftType      = "Free_Agent"
        DraftInstance  = 1
        DraftCode      = "Free_Agent"
        DraftKey       = "2026_Free_Agent"
        SleeperDraftID = "fa-draft"
        TradedPicks    = @($movement)
    }
)

$result = Resolve-TransactionDraftPickTypesFromContexts -transactions @($transaction) -contexts $contexts
$resolvedSleeperPick = $result.Transactions[0].DraftPicks[0]
Assert-Equal -Actual $resolvedSleeperPick.DraftKey -Expected "2026_Rookie" -Message "Manual sibling DraftKey did not disambiguate the Sleeper pick."
Assert-Equal -Actual $resolvedSleeperPick.DraftType -Expected "Rookie" -Message "Sleeper pick resolved to the wrong draft type."
Assert-Equal -Actual $resolvedSleeperPick.DraftInstance -Expected 1 -Message "Sleeper pick resolved to the wrong draft instance."
Assert-Equal -Actual $resolvedSleeperPick.SleeperDraftID -Expected "rookie-draft" -Message "Sleeper draft binding was not propagated."
Assert-Equal -Actual $result.Transactions[0].DraftPicks[1].DraftKey -Expected "2026_Free_Agent" -Message "Manual pick identity was modified."

# Sleeper exposes one future draft-pick pool before the concrete future draft
# exists. With the current Metadata role this must resolve Marcel's 2027 round-4
# pick to 2027_Rookie without requiring a 2027 SleeperDraftID.
$futureSleeperPick = [PSCustomObject][ordered]@{
    DraftType             = $null
    DraftInstance         = $null
    DraftCode             = $null
    DraftSource           = "Sleeper"
    DraftKey              = $null
    Season                = "2027"
    Round                 = 4
    OriginalOwnerRosterID = 2
    PreviousOwnerRosterID = 2
    NewOwnerRosterID      = 1
}
$futureTransaction = [PSCustomObject][ordered]@{
    Source        = "Sleeper"
    TransactionID = "1400904559005532160"
    Type          = "trade"
    Status        = "complete"
    CreatedAt     = [Int64]1
    CreatedDate   = "2026-09-02"
    DraftPicks    = @($futureSleeperPick)
}
$futureResult = Resolve-TransactionDraftPickTypesFromContexts -transactions @($futureTransaction) -contexts @()
$resolvedFuturePick = $futureResult.Transactions[0].DraftPicks[0]
Assert-Equal -Actual $resolvedFuturePick.DraftKey -Expected "2027_Rookie" -Message "Future Sleeper pick did not resolve to the configured future pick pool."
Assert-Equal -Actual $resolvedFuturePick.DraftType -Expected "Rookie" -Message "Current Metadata future pick pool is not Rookie."
Assert-Equal -Actual $resolvedFuturePick.DraftInstance -Expected 1 -Message "Future Sleeper pick resolved to the wrong draft instance."
Assert-Null -Actual $resolvedFuturePick.SleeperDraftID -Message "Future Sleeper pick unexpectedly received a concrete draft ID."

# Applying the resolved trade must transfer only the 2027 Rookie asset. The
# same original-owner/round Free Agent asset must remain with Marcel.
$rookieDraftPick = [PSCustomObject][ordered]@{
    PickKey               = "2027_Rookie_R4_OO2"
    Season                = "2027"
    Round                 = 4
    OriginalOwnerRosterID = 2
    CurrentOwnerRosterID  = 2
    WasTraded             = $false
    IsCurrentlyTraded     = $false
    TradeSource           = $null
    TradeHistory          = @()
}
$freeAgentDraftPick = [PSCustomObject][ordered]@{
    PickKey               = "2027_Free_Agent_R4_OO2"
    Season                = "2027"
    Round                 = 4
    OriginalOwnerRosterID = 2
    CurrentOwnerRosterID  = 2
    WasTraded             = $false
    IsCurrentlyTraded     = $false
    TradeSource           = $null
    TradeHistory          = @()
}
$rookieApplied = Get-AppliedDraftPickTrades -picks @($rookieDraftPick) -transactions @($futureResult.Transactions[0]) -draftKey "2027_Rookie"
$freeAgentApplied = Get-AppliedDraftPickTrades -picks @($freeAgentDraftPick) -transactions @($futureResult.Transactions[0]) -draftKey "2027_Free_Agent"
Assert-Equal -Actual $rookieApplied[0].CurrentOwnerRosterID -Expected 1 -Message "2027 Rookie round-4 pick did not transfer from Marcel to Robert."
Assert-Equal -Actual $freeAgentApplied[0].CurrentOwnerRosterID -Expected 2 -Message "2027 Free Agent round-4 pick was incorrectly transferred with the Sleeper future pick."

# Detail enrichment must be safe when a deliberately unresolved pick has no
# generated draft candidate. This is the regression for the League update crash.
$unmatchedPick = [PSCustomObject][ordered]@{
    DraftSource           = "Sleeper"
    Season                = "2099"
    Round                 = 5
    OriginalOwnerRosterID = 6
    PreviousOwnerRosterID = 6
    NewOwnerRosterID      = 1
}
$unmatchedTransaction = [PSCustomObject][ordered]@{
    TransactionID = "no-draft-result-candidate"
    DraftPicks    = @($unmatchedPick)
}
Assert-Null `
    -Actual (Get-TransactionDraftPickResultMatch -transaction $unmatchedTransaction -transactionPick $unmatchedPick -drafts @()) `
    -Message "Zero draft-result candidates must return null instead of failing parameter binding."

# If two concrete draft instances remain viable and no sibling asset claims one,
# the resolver must not invent an answer, even for a future season.
$ambiguousPick = [PSCustomObject][ordered]@{
    DraftType             = $null
    DraftInstance         = $null
    DraftCode             = $null
    DraftSource           = "Sleeper"
    DraftKey              = $null
    Season                = "2035"
    Round                 = 1
    OriginalOwnerRosterID = 1
    PreviousOwnerRosterID = 1
    NewOwnerRosterID      = 2
}
$ambiguousMovement = [PSCustomObject][ordered]@{
    season            = "2035"
    round             = 1
    roster_id         = 1
    previous_owner_id = 1
    owner_id          = 2
}
$ambiguousContexts = @(
    [PSCustomObject][ordered]@{
        Season = "2035"; DraftType = "Free_Agent"; DraftInstance = 1; DraftCode = "Free_Agent"; DraftKey = "2035_Free_Agent"; SleeperDraftID = "fa-1"; TradedPicks = @($ambiguousMovement)
    },
    [PSCustomObject][ordered]@{
        Season = "2035"; DraftType = "Free_Agent"; DraftInstance = 2; DraftCode = "Free_Agent_2"; DraftKey = "2035_Free_Agent_2"; SleeperDraftID = "fa-2"; TradedPicks = @($ambiguousMovement)
    }
)
$ambiguousTransaction = [PSCustomObject][ordered]@{ TransactionID = "ambiguous"; DraftPicks = @($ambiguousPick) }
$ambiguousResult = Resolve-TransactionDraftPickTypesFromContexts -transactions @($ambiguousTransaction) -contexts $ambiguousContexts
Assert-Null -Actual $ambiguousResult.Transactions[0].DraftPicks[0].DraftKey -Message "Ambiguous draft instance was guessed."

. "$PSScriptRoot\ProviderJoinInvariantRegressionTest.ps1"

Write-Host "Draft identity regression tests passed." -ForegroundColor Green
