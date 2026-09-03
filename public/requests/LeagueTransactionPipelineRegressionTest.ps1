$ErrorActionPreference = "Stop"

Import-Module "$PSScriptRoot\utils\league\TransactionUtils.psm1" -Force
Import-Module "$PSScriptRoot\utils\league\LeagueTransactionPipelineUtils.psm1" -Force
Import-Module "$PSScriptRoot\utils\league\LeagueOverviewUtils.psm1" -Force

function Assert-True {
    param(
        [Parameter(Mandatory = $true)][bool]$Condition,
        [Parameter(Mandatory = $true)][string]$Message
    )

    if (-not $Condition) { throw $Message }
}

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

function Get-OccurrenceCount {
    param(
        [Parameter(Mandatory = $true)][string]$Text,
        [Parameter(Mandatory = $true)][string]$Needle
    )

    return ([regex]::Matches($Text, [regex]::Escape($Needle))).Count
}

# RequestLeague must use the in-memory orchestration and persist current
# Transactions.json exactly once after both enrichment phases.
$requestLeague = Get-Content "$PSScriptRoot\RequestLeague.ps1" -Raw
Assert-Equal -Actual (Get-OccurrenceCount -Text $requestLeague -Needle "Save-TransactionsCurrentSeason -transactions `$transactionsCurrentSeason") -Expected 1 -Message "RequestLeague must have exactly one final Transactions persistence point."
Assert-Equal -Actual (Get-OccurrenceCount -Text $requestLeague -Needle "Update-TransactionsCurrentSeason") -Expected 0 -Message "RequestLeague still uses the persisting current-season transaction updater."
Assert-Equal -Actual (Get-OccurrenceCount -Text $requestLeague -Needle "Update-CurrentTransactionDraftPickTypesFromSleeper") -Expected 0 -Message "RequestLeague still uses the persisting draft-identity enrichment wrapper."
Assert-Equal -Actual (Get-OccurrenceCount -Text $requestLeague -Needle "Update-CurrentTransactionDraftPickDetails") -Expected 0 -Message "RequestLeague still uses the persisting pick-detail enrichment wrapper."
Assert-Equal -Actual (Get-OccurrenceCount -Text $requestLeague -Needle "Update-DraftsOrderAware") -Expected 0 -Message "RequestLeague still lets Drafts reload Transactions.json instead of using the same snapshot."
Assert-True -Condition $requestLeague.Contains("Get-LeagueTransactionsCurrentSeasonInMemory") -Message "RequestLeague does not build transactions in memory."
Assert-True -Condition $requestLeague.Contains("Resolve-LeagueTransactionDraftPickTypesInMemory") -Message "RequestLeague does not resolve draft identity in memory."
Assert-True -Condition $requestLeague.Contains("Update-LeagueDraftsOrderAwareFromTransactions") -Message "RequestLeague does not pass the in-memory transaction snapshot to draft generation."
Assert-True -Condition $requestLeague.Contains("Add-LeagueTransactionDraftPickDetailsInMemory") -Message "RequestLeague does not enrich transaction pick details in memory."
Assert-True -Condition $requestLeague.Contains("Resolve-LeagueTradeDeadlineWeek") -Message "RequestLeague does not normalize the trade deadline before publishing League.json."
Assert-True -Condition $requestLeague.Contains("SeasonKickoff           = `$seasonKickoff") -Message "RequestLeague does not publish SeasonKickoff."
Assert-True -Condition $requestLeague.Contains("Matchups                = `$matchupSnapshot") -Message "RequestLeague does not publish the current matchup snapshot."

# League overview read-model helpers normalize optional deadline settings and
# build deterministic matchup/kickoff facts without frontend derivation.
Assert-Equal -Actual (Resolve-LeagueTradeDeadlineWeek -TradeDeadline $null) -Expected $null -Message "Null trade deadline must stay null."
Assert-Equal -Actual (Resolve-LeagueTradeDeadlineWeek -TradeDeadline 0) -Expected $null -Message "Trade deadline week 0 must normalize to null."
Assert-Equal -Actual (Resolve-LeagueTradeDeadlineWeek -TradeDeadline -1) -Expected $null -Message "Negative trade deadline must normalize to null."
Assert-Equal -Actual (Resolve-LeagueTradeDeadlineWeek -TradeDeadline "off") -Expected $null -Message "Non-numeric trade deadline must normalize to null."
Assert-Equal -Actual (Resolve-LeagueTradeDeadlineWeek -TradeDeadline 11) -Expected 11 -Message "Positive trade deadline week changed unexpectedly."

$scheduleFixture = @(
    [PSCustomObject]@{ seasonType = "Preseason"; gameTime_epoch = "1788000000" },
    [PSCustomObject]@{ seasonType = "Regular Season"; gameTime_epoch = "1789318800" },
    [PSCustomObject]@{ seasonType = "Regular Season"; gameTime_epoch = "1788999600" }
)
$kickoff = Get-LeagueSeasonKickoffUtc -Schedule $scheduleFixture
$expectedKickoff = [DateTimeOffset]::FromUnixTimeSeconds(1788999600).UtcDateTime
Assert-Equal -Actual $kickoff.ToString("o") -Expected $expectedKickoff.ToString("o") -Message "Season kickoff did not use the earliest regular-season game."

$matchupFixture = @(
    [PSCustomObject]@{ matchup_id = 2; roster_id = 4; points = 0 },
    [PSCustomObject]@{ matchup_id = 1; roster_id = 2; points = 101.25 },
    [PSCustomObject]@{ matchup_id = 1; roster_id = 1; points = 99.5 },
    [PSCustomObject]@{ matchup_id = 2; roster_id = 3; points = 0 },
    [PSCustomObject]@{ matchup_id = 9; roster_id = 6; points = 0 },
    [PSCustomObject]@{ matchup_id = 0; roster_id = 5; points = 0 }
)
$matchupSnapshot = ConvertTo-LeagueMatchupSnapshot -Matchups $matchupFixture -Week 1 -Season "2026"
Assert-Equal -Actual $matchupSnapshot.Season -Expected "2026" -Message "Matchup snapshot season changed unexpectedly."
Assert-Equal -Actual $matchupSnapshot.Week -Expected 1 -Message "Matchup snapshot week changed unexpectedly."
Assert-Equal -Actual @($matchupSnapshot.Matchups).Count -Expected 2 -Message "Malformed matchup groups were not filtered correctly."
Assert-Equal -Actual $matchupSnapshot.Matchups[0].MatchupID -Expected 1 -Message "Matchups are not sorted deterministically."
Assert-Equal -Actual $matchupSnapshot.Matchups[0].Participants[0].TeamID -Expected 1 -Message "Matchup participants are not sorted by TeamID."
Assert-Equal -Actual $matchupSnapshot.Matchups[0].Participants[1].Points -Expected 101.25 -Message "Matchup points were not preserved."
Assert-Equal -Actual (ConvertTo-LeagueMatchupSnapshot -Matchups $matchupFixture -Week 0 -Season "2026") -Expected $null -Message "Non-positive matchup week must not publish a snapshot."

# The dedicated helper must never publish Transactions.json itself. Drafts may
# still be persisted by the draft step; only Transactions are delayed.
$pipeline = Get-Content "$PSScriptRoot\utils\league\LeagueTransactionPipelineUtils.psm1" -Raw
Assert-Equal -Actual (Get-OccurrenceCount -Text $pipeline -Needle "Save-TransactionsCurrentSeason") -Expected 0 -Message "League in-memory helper unexpectedly persists Transactions.json."
Assert-Equal -Actual (Get-OccurrenceCount -Text $pipeline -Needle "Save-TransactionDraftPickTransactions") -Expected 0 -Message "League in-memory helper unexpectedly persists enriched Transactions.json."

# Standalone/history requests retain their file-based contract, but orchestration
# is centralized so Transactions and Drafts cannot drift in ordering.
$requestTransactions = Get-Content "$PSScriptRoot\RequestTransactions.ps1" -Raw
Assert-True -Condition $requestTransactions.Contains("Update-TransactionsAllSeasons -ForceCurrent -ForceHistory") -Message "Standalone transaction history rebuild contract changed."
Assert-True -Condition $requestTransactions.Contains("Invoke-DraftTransactionRebuild -ForceHistory") -Message "Standalone transaction request does not invoke the coupled draft/transaction rebuild."
$emptyManualLookup = New-ManualTransactionBindingLookup -ManualTransactions $null
Assert-Equal -Actual $emptyManualLookup.Count -Expected 0 -Message "A season without manual transactions must produce an empty binding lookup."

$requestDrafts = Get-Content "$PSScriptRoot\RequestDrafts.ps1" -Raw
Assert-True -Condition $requestDrafts.Contains("Invoke-DraftTransactionRebuild") -Message "Standalone draft request does not use the shared rebuild orchestration."

$standalonePipeline = Get-Content "$PSScriptRoot\utils\league\DraftTransactionPipelineUtils.psm1" -Raw
Assert-True -Condition $standalonePipeline.Contains("Update-AllTransactionDraftPickTypesFromSleeper") -Message "Shared standalone pipeline no longer prepares persisted transaction identities."
Assert-True -Condition $standalonePipeline.Contains("Update-DraftsOrderAware") -Message "Shared standalone pipeline no longer generates current drafts."
Assert-True -Condition $standalonePipeline.Contains("Update-DraftsHistoricalSeasonsSafeOrderAware") -Message "Shared standalone pipeline no longer generates historical drafts."
Assert-True -Condition $standalonePipeline.Contains("Update-AllTransactionDraftPickDetailsFromLocalDrafts") -Message "Shared standalone pipeline no longer enriches persisted transaction details."

# Pure in-memory detail enrichment must yield the same canonical transaction
# shape that Compare-Transactions considers stable on the next no-op run.
$transaction = [PSCustomObject][ordered]@{
    Source        = "Sleeper"
    TransactionID = "pipeline-test"
    Type          = "trade"
    Status        = "complete"
    Season        = "2026"
    Week          = 1
    CreatedAt     = [Int64]1
    CreatedDate   = "2026-01-01"
    RosterIDs     = @(1, 2)
    Adds          = @{}
    Drops         = @{}
    DraftPicks    = @(
        [PSCustomObject][ordered]@{
            DraftType             = "Rookie"
            DraftInstance         = 1
            DraftCode             = "Rookie"
            DraftSource           = "Sleeper"
            DraftKey              = "2026_Rookie"
            Season                = "2026"
            Round                 = 1
            OriginalOwnerRosterID = 1
            PreviousOwnerRosterID = 1
            NewOwnerRosterID      = 2
            SleeperDraftID        = "draft-1"
        }
    )
    Notes         = $null
}
$draft = [PSCustomObject][ordered]@{
    DraftKey       = "2026_Rookie"
    Season         = "2026"
    DraftType      = "Rookie"
    DraftInstance  = 1
    DraftCode      = "Rookie"
    SleeperDraftID = "draft-1"
    Picks          = @(
        [PSCustomObject][ordered]@{
            PickKey               = "2026_Rookie_R1_OO1"
            Season                = "2026"
            DraftType             = "Rookie"
            DraftInstance         = 1
            DraftCode             = "Rookie"
            Round                 = 1
            OriginalOwnerRosterID = 1
            CurrentOwnerRosterID  = 2
            PositionInRound       = 3
            OverallPick           = 3
            DisplayPick           = "1.03"
            TradeHistory          = @(
                [PSCustomObject][ordered]@{
                    TransactionID         = "pipeline-test"
                    PreviousOwnerRosterID = 1
                    NewOwnerRosterID      = 2
                }
            )
            PlayerID              = "player-1"
            PlayerName            = "Test Player"
            Status                = "Picked"
            SleeperPickNo         = 3
        }
    )
}

$enriched = Add-LeagueTransactionDraftPickDetailsInMemory -transactions @($transaction) -drafts @($draft)
$pick = $enriched[0].DraftPicks[0]
Assert-Equal -Actual $pick.PickKey -Expected "2026_Rookie_R1_OO1" -Message "In-memory pick enrichment did not propagate PickKey."
Assert-Equal -Actual $pick.DisplayPick -Expected "1.03" -Message "In-memory pick enrichment did not propagate DisplayPick."
Assert-Equal -Actual $pick.PlayerID -Expected "player-1" -Message "In-memory pick enrichment did not propagate selected player."
Assert-Equal -Actual (Compare-Transactions -oldTransactions $enriched -newTransactions $enriched) -Expected $false -Message "A fully enriched no-op transaction snapshot is not semantically stable."

Write-Host "League transaction and overview regression tests passed." -ForegroundColor Green
