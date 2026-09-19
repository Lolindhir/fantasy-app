$ErrorActionPreference = "Stop"

Import-Module "$PSScriptRoot\utils\league\CanonicalTransactionUtils.psm1" -Force
Import-Module "$PSScriptRoot\utils\league\CanonicalDraftUtils.psm1" -Force
Import-Module "$PSScriptRoot\utils\league\TransactionUtils.psm1" -Force
Import-Module "$PSScriptRoot\utils\league\LeagueTransactionPipelineUtils.psm1" -Force
Import-Module "$PSScriptRoot\utils\league\LeagueOverviewUtils.psm1" -Force
Import-Module "$PSScriptRoot\utils\league\CanonicalStandingUtils.psm1" -Force
Import-Module "$PSScriptRoot\utils\league\CanonicalLeagueCoreUtils.psm1" -Force
Import-Module "$PSScriptRoot\utils\league\CanonicalPlayoffUtils.psm1" -Force

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
Assert-Equal -Actual (Get-OccurrenceCount -Text $requestLeague -Needle "Matchups                = `$matchupSnapshot") -Expected 0 -Message "RequestLeague still publishes the legacy League.Matchups snapshot."
Assert-Equal -Actual (Get-OccurrenceCount -Text $requestLeague -Needle "ConvertTo-LeagueMatchupSnapshot") -Expected 0 -Message "RequestLeague still builds the legacy League.Matchups snapshot."
Assert-True -Condition $requestLeague.Contains("Update-MatchupHistoryReadModels") -Message "RequestLeague does not use the public Matchups history API."
Assert-True -Condition $requestLeague.Contains("CanonicalLeagueCoreUtils.psm1") -Message "RequestLeague does not import the canonical League Core consumer."
Assert-True -Condition $requestLeague.Contains("CanonicalPlayoffUtils.psm1") -Message "RequestLeague does not import the canonical Playoff consumer."
Assert-True -Condition (-not $requestLeague.Contains("\utils\league\PlayoffUtils.psm1")) -Message "RequestLeague still imports the legacy live Playoff adapter."
Assert-True -Condition $requestLeague.Contains("Get-CanonicalCurrentLeagueRaw -CanonicalLeagueID `$CanonicalLeagueID") -Message "RequestLeague does not use canonical current League metadata/settings."
Assert-True -Condition $requestLeague.Contains("Get-CanonicalCurrentTeamsForLeague -CanonicalLeagueID `$CanonicalLeagueID") -Message "RequestLeague does not use canonical current Members/Rosters team data."
Assert-Equal -Actual (Get-OccurrenceCount -Text $requestLeague -Needle "Get-LeagueRaw") -Expected 0 -Message "RequestLeague still performs a direct current League provider read."
Assert-Equal -Actual (Get-OccurrenceCount -Text $requestLeague -Needle "Get-TeamsForLeague") -Expected 0 -Message "RequestLeague still performs the legacy current Teams provider read."
Assert-Equal -Actual (Get-OccurrenceCount -Text $requestLeague -Needle "Get-Playoffs") -Expected 0 -Message "RequestLeague still performs the legacy live Playoffs read."
Assert-Equal -Actual (Get-OccurrenceCount -Text $requestLeague -Needle "Get-CanonicalCurrentPlayoffs") -Expected 1 -Message "RequestLeague must use exactly one canonical current Playoffs read."
Assert-Equal -Actual (Get-OccurrenceCount -Text $requestLeague -Needle "Get-FgcCurrentMatchupLoad") -Expected 1 -Message "RequestLeague must intentionally retain exactly one live current-matchup score overlay."
Assert-True -Condition $requestLeague.Contains("'LeagueIDPrevious'") -Message "RequestLeague change detection does not track LeagueIDPrevious."
Assert-True -Condition $requestLeague.Contains("@('Settings','ScoringType','Playoffs')") -Message "RequestLeague change detection does not track canonical Settings, ScoringType and Playoffs structurally."
Assert-True -Condition $requestLeague.Contains("ConvertTo-Json -Depth 10 -Compress") -Message "RequestLeague canonical structured comparison is not structural."

# League overview read-model helpers normalize optional deadline settings and
# deterministic kickoff facts without frontend derivation.
Assert-Equal -Actual (Resolve-LeagueTradeDeadlineWeek -TradeDeadline $null) -Expected $null -Message "Null trade deadline must stay null."
Assert-Equal -Actual (Resolve-LeagueTradeDeadlineWeek -TradeDeadline 0) -Expected $null -Message "Trade deadline week 0 must normalize to null."
Assert-Equal -Actual (Resolve-LeagueTradeDeadlineWeek -TradeDeadline -1) -Expected $null -Message "Negative trade deadline must normalize to null."
Assert-Equal -Actual (Resolve-LeagueTradeDeadlineWeek -TradeDeadline "off") -Expected $null -Message "Non-numeric trade deadline must normalize to null."
Assert-Equal -Actual (Resolve-LeagueTradeDeadlineWeek -TradeDeadline 99) -Expected $null -Message "Sleeper trade deadline sentinel 99 must normalize to null."
Assert-Equal -Actual (Resolve-LeagueTradeDeadlineWeek -TradeDeadline 11) -Expected 11 -Message "Positive trade deadline week changed unexpectedly."

$scheduleFixture = @(
    [PSCustomObject]@{ seasonType = "Preseason"; gameTime_epoch = "1788000000" },
    [PSCustomObject]@{ seasonType = "Regular Season"; gameTime_epoch = "1789318800" },
    [PSCustomObject]@{ seasonType = "Regular Season"; gameTime_epoch = "1788999600" }
)
$kickoff = Get-LeagueSeasonKickoffUtc -Schedule $scheduleFixture
$expectedKickoff = [DateTimeOffset]::FromUnixTimeSeconds(1788999600).UtcDateTime
Assert-Equal -Actual $kickoff.ToString("o") -Expected $expectedKickoff.ToString("o") -Message "Season kickoff did not use the earliest regular-season game."

$leagueOverviewUtils = Get-Content "$PSScriptRoot\utils\league\LeagueOverviewUtils.psm1" -Raw
Assert-Equal -Actual (Get-OccurrenceCount -Text $leagueOverviewUtils -Needle "ConvertTo-LeagueMatchupSnapshot") -Expected 0 -Message "LeagueOverviewUtils still contains the legacy matchup snapshot converter."
Assert-Equal -Actual (Get-OccurrenceCount -Text $leagueOverviewUtils -Needle "Get-LeagueMatchupSnapshot") -Expected 0 -Message "LeagueOverviewUtils still contains the legacy matchup snapshot loader."

$matchupReadModelUtils = Get-Content "$PSScriptRoot\utils\league\MatchupReadModelUtils.psm1" -Raw
Assert-Equal -Actual (Get-OccurrenceCount -Text $matchupReadModelUtils -Needle "Set-Alias -Name Ensure-MatchupHistoryReadModels") -Expected 0 -Message "MatchupReadModelUtils still exposes the transitional history alias."
Assert-True -Condition $matchupReadModelUtils.Contains("Update-MatchupHistoryReadModels") -Message "MatchupReadModelUtils no longer exposes the approved public history API."

# The dedicated helper must never publish Transactions.json itself. Drafts may
# still be persisted by the draft step; only Transactions are delayed. The
# in-memory current-season source must now be canonical, not a direct Sleeper
# transactions fetch.
$pipeline = Get-Content "$PSScriptRoot\utils\league\LeagueTransactionPipelineUtils.psm1" -Raw
Assert-Equal -Actual (Get-OccurrenceCount -Text $pipeline -Needle "Save-TransactionsCurrentSeason") -Expected 0 -Message "League in-memory helper unexpectedly persists Transactions.json."
Assert-Equal -Actual (Get-OccurrenceCount -Text $pipeline -Needle "Save-TransactionDraftPickTransactions") -Expected 0 -Message "League in-memory helper unexpectedly persists enriched Transactions.json."
Assert-True -Condition $pipeline.Contains("Get-CanonicalTransactionsCurrentSeasonInMemory") -Message "League in-memory helper does not use canonical current-season transactions."
Assert-Equal -Actual (Get-OccurrenceCount -Text $pipeline -Needle "Get-TransactionsRemoteForWeeks") -Expected 0 -Message "League in-memory helper still fetches transactions directly from Sleeper."

# Standalone/history requests retain the file-based draft contract while both
# current and historical transaction bases come from canonical League source-data.
$requestTransactions = Get-Content "$PSScriptRoot\RequestTransactions.ps1" -Raw
Assert-True -Condition $requestTransactions.Contains("Update-TransactionsAllSeasonsCanonical") -Message "Standalone transaction rebuild no longer uses canonical all-season data."
Assert-True -Condition (-not $requestTransactions.Contains("Update-TransactionsAllSeasonsCanonicalCurrent")) -Message "Standalone transaction rebuild still uses the transitional current-only canonical path."
Assert-True -Condition (-not $requestTransactions.Contains("Update-TransactionsAllSeasons -ForceCurrent -ForceHistory")) -Message "Standalone transaction rebuild still uses the fully legacy source."
Assert-True -Condition $requestTransactions.Contains("Invoke-DraftTransactionRebuild -ForceHistory") -Message "Standalone transaction request does not invoke the coupled draft/transaction rebuild."
$emptyManualLookup = New-ManualTransactionBindingLookup -ManualTransactions $null
Assert-Equal -Actual $emptyManualLookup.Count -Expected 0 -Message "A season without manual transactions must produce an empty binding lookup."
$emptySleeperWeekLookup = New-SleeperTransactionWeekLookup -Transactions $null -SourceLabel "empty Sleeper week regression"
Assert-Equal -Actual $emptySleeperWeekLookup.Count -Expected 0 -Message "A Sleeper week without transactions must produce an empty provider lookup."
Assert-True -Condition (Test-TransactionIdentityInvariants -Transactions $null -SourceLabel "empty generated transaction regression") -Message "An empty generated transaction collection must pass identity validation."

# Manual overlays remain a compatibility layer above canonical transaction facts.
$canonicalFixture = [PSCustomObject][ordered]@{
    Source        = "Sleeper"
    TransactionID = "canonical-manual-fixture"
    Type          = "trade"
    Status        = "complete"
    Season        = "2026"
    Week          = 1
    CreatedAt     = [Int64]1
    CreatedDate   = "1970-01-01"
    RosterIDs     = @(1, 6)
    Adds          = @{}
    Drops         = @{}
    DraftPicks    = @()
    Notes         = $null
}
$manualFixture = [PSCustomObject][ordered]@{
    Season               = "2026"
    Date                 = "2026-09-09"
    Week                 = 1
    SleeperTransactionID = "canonical-manual-fixture"
    Picks                = @(
        [PSCustomObject][ordered]@{
            DraftKey = "2028_Free_Agent"
            Round    = 4
            Original = "Tim"
            From     = "Tim"
            To       = "Robert"
        }
    )
}
$mergedFixture = @(Merge-CanonicalTransactionsWithManual `
    -canonicalTransactions @($canonicalFixture) `
    -manualTransactions @($manualFixture) `
    -season "2026")
Assert-Equal -Actual $mergedFixture.Count -Expected 1 -Message "Canonical/manual overlay changed the transaction count unexpectedly."
Assert-Equal -Actual $mergedFixture[0].Source -Expected "Sleeper_Manual" -Message "Canonical/manual overlay did not preserve the combined source marker."
Assert-Equal -Actual $mergedFixture[0].DraftPicks.Count -Expected 1 -Message "Canonical/manual overlay did not append the manual draft pick."
Assert-Equal -Actual $mergedFixture[0].DraftPicks[0].PreviousOwnerRosterID -Expected 6 -Message "Canonical/manual overlay lost the manual previous owner."
Assert-Equal -Actual $mergedFixture[0].DraftPicks[0].NewOwnerRosterID -Expected 1 -Message "Canonical/manual overlay lost the manual new owner."
Assert-True -Condition ($mergedFixture[0].RosterIDs -contains 1) -Message "Canonical/manual overlay lost the destination roster."
Assert-True -Condition ($mergedFixture[0].RosterIDs -contains 6) -Message "Canonical/manual overlay lost the source roster."

$requestDrafts = Get-Content "$PSScriptRoot\RequestDrafts.ps1" -Raw
Assert-True -Condition $requestDrafts.Contains("Invoke-DraftTransactionRebuild") -Message "Standalone draft request does not use the shared rebuild orchestration."

$standalonePipeline = Get-Content "$PSScriptRoot\utils\league\DraftTransactionPipelineUtils.psm1" -Raw
Assert-True -Condition $standalonePipeline.Contains("Update-AllTransactionDraftPickTypesFromSleeper") -Message "Shared standalone pipeline no longer prepares persisted transaction identities."
Assert-True -Condition (-not $standalonePipeline.Contains("Update-AllTransactionDraftPickTypesFromSleeper -leagueID")) -Message "Standalone transaction identity still depends on a Sleeper league ID."
Assert-True -Condition (-not $standalonePipeline.Contains("Update-HistoricalTransactionDraftPickTypesFromCompletedDrafts -leagueID")) -Message "Historical identity correction still depends on a Sleeper league ID."
Assert-True -Condition $standalonePipeline.Contains("Update-DraftsOrderAware") -Message "Shared standalone pipeline no longer generates current drafts."
Assert-True -Condition $standalonePipeline.Contains("Update-DraftsHistoricalSeasonsSafeOrderAware") -Message "Shared standalone pipeline no longer generates historical drafts."
Assert-True -Condition $standalonePipeline.Contains("Update-AllTransactionDraftPickDetailsFromLocalDrafts") -Message "Shared standalone pipeline no longer enriches persisted transaction details."

# Draft/Pick provider reads must come from persisted Canonical League Source Data.
$draftUtils = Get-Content "$PSScriptRoot\utils\league\DraftUtils.psm1" -Raw
$draftHistoryUtils = Get-Content "$PSScriptRoot\utils\league\DraftHistoryUtils.psm1" -Raw
$draftHistoryFix = Get-Content "$PSScriptRoot\utils\league\DraftHistoryEmptyDefinitionsFix.psm1" -Raw
$draftPickResultUtils = Get-Content "$PSScriptRoot\utils\league\DraftPickResultUtils.psm1" -Raw
$transactionPickUtils = Get-Content "$PSScriptRoot\utils\league\TransactionDraftPickEnrichmentUtils.psm1" -Raw
$historicalIdentityUtils = Get-Content "$PSScriptRoot\utils\league\HistoricalTransactionDraftPickIdentityUtils.psm1" -Raw

Assert-True -Condition $draftUtils.Contains("Get-CanonicalSleeperDrafts") -Message "Current draft mapping is not backed by Canonical League Source Data."
Assert-True -Condition (-not $draftUtils.Contains("Get-SleeperDrafts -leagueID")) -Message "Current draft mapping still performs a direct Sleeper draft-index read."
Assert-True -Condition (-not $draftUtils.Contains("Get-SleeperDraft -draftID")) -Message "Current draft mapping still performs a direct Sleeper draft-detail read."
Assert-True -Condition $draftHistoryUtils.Contains("Get-CanonicalSleeperDrafts -Season") -Message "Historical draft generation is not backed by Canonical League Source Data."
Assert-True -Condition (-not $draftHistoryUtils.Contains("Get-SleeperDrafts -leagueID")) -Message "Historical draft generation still performs a direct Sleeper draft-index read."
Assert-True -Condition (-not $draftHistoryUtils.Contains("Get-SleeperDraft -draftID")) -Message "Historical draft generation still performs a direct Sleeper draft-detail read."
Assert-True -Condition $draftHistoryFix.Contains("Get-CanonicalSleeperDrafts -Season") -Message "Historical safe-order draft generation is not backed by Canonical League Source Data."
Assert-True -Condition (-not $draftHistoryFix.Contains("Get-SleeperDrafts -leagueID")) -Message "Historical safe-order draft generation still performs a direct Sleeper draft-index read."
Assert-True -Condition $draftPickResultUtils.Contains("Get-CanonicalSleeperDraftPicks") -Message "Draft pick result enrichment is not backed by Canonical League Source Data."
Assert-True -Condition (-not $draftPickResultUtils.Contains("Get-SleeperDraftPicks -draftID")) -Message "Draft pick result enrichment still performs a direct Sleeper pick read."
Assert-True -Condition $transactionPickUtils.Contains("Get-CanonicalSleeperDraftTradedPicks") -Message "Current transaction draft-pick identity is not backed by Canonical League Source Data."
Assert-True -Condition (-not $transactionPickUtils.Contains("Get-SleeperDraftTradedPicks -draftID")) -Message "Current transaction draft-pick identity still performs a direct Sleeper traded-pick read."
Assert-True -Condition (-not $transactionPickUtils.Contains("Get-LeaguesRecursive")) -Message "Transaction draft-pick identity still discovers seasons through Sleeper league lineage."
Assert-True -Condition (-not $transactionPickUtils.Contains("LeagueUtils.psm1")) -Message "Transaction draft-pick identity still imports legacy league discovery utilities."
Assert-True -Condition $historicalIdentityUtils.Contains("Get-CanonicalSleeperDraftTradedPicks") -Message "Historical transaction draft-pick identity is not backed by Canonical League Source Data."
Assert-True -Condition (-not $historicalIdentityUtils.Contains("Get-SleeperDraftTradedPicks -draftID")) -Message "Historical transaction draft-pick identity still performs a direct Sleeper traded-pick read."
Assert-True -Condition (-not $historicalIdentityUtils.Contains("Get-LeaguesRecursive")) -Message "Historical transaction draft-pick identity still discovers seasons through Sleeper league lineage."
Assert-True -Condition (-not $historicalIdentityUtils.Contains("LeagueUtils.psm1")) -Message "Historical transaction draft-pick identity still imports legacy league discovery utilities."

Clear-CanonicalDraftPayloadCache
$canonical2024 = Get-CanonicalDraftLegacyPayload -Season "2024"
$canonical2025 = Get-CanonicalDraftLegacyPayload -Season "2025"
$canonical2026 = Get-CanonicalDraftLegacyPayload -Season "2026"
Assert-Equal -Actual @($canonical2024.Drafts).Count -Expected 1 -Message "Canonical draft adapter lost the 2024 historical draft."
Assert-Equal -Actual @($canonical2025.Drafts).Count -Expected 1 -Message "Canonical draft adapter lost the 2025 historical draft."
Assert-Equal -Actual @($canonical2026.Drafts).Count -Expected 2 -Message "Canonical draft adapter lost one of the configured 2026 drafts."
Assert-True -Condition (@($canonical2026.Drafts.draft_id) -contains "1354177383996866560") -Message "Canonical draft adapter lost the configured 2026 Rookie draft."
Assert-True -Condition (@($canonical2026.Drafts.draft_id) -contains "1382606963258454016") -Message "Canonical draft adapter lost the configured 2026 Free Agent draft."

# Historical transaction identity must pass the explicit transaction-file season
# into the canonical draft adapter while the current path retains its default.
$historical2024Contexts = @(Get-TransactionDraftPickSleeperDraftContexts -season "2024")
$historical2025Contexts = @(Get-TransactionDraftPickSleeperDraftContexts -season "2025")
$current2026Contexts = @(Get-TransactionDraftPickSleeperDraftContexts)
Assert-True -Condition ($historical2024Contexts.Count -gt 0) -Message "Historical 2024 canonical draft contexts could not be built from an explicit season."
Assert-True -Condition ($historical2025Contexts.Count -gt 0) -Message "Historical 2025 canonical draft contexts could not be built from an explicit season."
Assert-True -Condition ($current2026Contexts.Count -gt 0) -Message "Current canonical draft context default stopped working."
Assert-True -Condition (@($historical2024Contexts.Season) -contains "2024") -Message "Historical 2024 context lost its explicit canonical season."
Assert-True -Condition (@($historical2025Contexts.Season) -contains "2025") -Message "Historical 2025 context lost its explicit canonical season."
Assert-True -Condition (@($current2026Contexts.Season) -contains "2026") -Message "Current canonical draft context no longer defaults to LeagueYear."

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


# Historical and current standings are canonical consumers. RequestStandings
# must not perform direct Sleeper league/team/bracket reads after the current cutover.
$canonicalStandingUtils = Get-Content "$PSScriptRoot\utils\league\CanonicalStandingUtils.psm1" -Raw
Assert-True -Condition (-not $canonicalStandingUtils.Contains("Get-LeagueRaw")) -Message "Canonical standings consumer performs a direct Sleeper league read."
Assert-True -Condition (-not $canonicalStandingUtils.Contains("Get-Teams")) -Message "Canonical standings consumer performs a direct Sleeper team read."
Assert-True -Condition (-not $canonicalStandingUtils.Contains("Get-SleeperWinnersBracket")) -Message "Canonical standings consumer performs a direct Sleeper winners-bracket read."
Assert-True -Condition (-not $canonicalStandingUtils.Contains("Get-SleeperLosersBracket")) -Message "Canonical standings consumer performs a direct Sleeper losers-bracket read."

$requestStandingsCutover = Get-Content "$PSScriptRoot\RequestStandings.ps1" -Raw
Assert-True -Condition $requestStandingsCutover.Contains("CanonicalStandingUtils.psm1") -Message "RequestStandings does not import the canonical standings consumer."
Assert-True -Condition $requestStandingsCutover.Contains("Get-CanonicalHistoricalStandings") -Message "RequestStandings does not consume canonical historical standings."
Assert-True -Condition $requestStandingsCutover.Contains("Get-CanonicalCurrentSeasonData") -Message "RequestStandings does not consume canonical current standings."
Assert-True -Condition (-not $requestStandingsCutover.Contains("Get-CurrentSeasonData")) -Message "RequestStandings still contains the retired live current-season helper."
Assert-True -Condition (-not $requestStandingsCutover.Contains("Get-LeagueRaw")) -Message "RequestStandings still performs a direct Sleeper league read."
Assert-True -Condition (-not $requestStandingsCutover.Contains("Get-Teams")) -Message "RequestStandings still performs a direct Sleeper team read."
Assert-True -Condition (-not $requestStandingsCutover.Contains("Get-Playoffs")) -Message "RequestStandings still performs a direct Sleeper playoff read."
Assert-True -Condition (-not $requestStandingsCutover.Contains("TeamUtils.psm1")) -Message "RequestStandings still imports TeamUtils after the canonical current cutover."
Assert-True -Condition (-not $requestStandingsCutover.Contains("LeagueUtils.psm1")) -Message "RequestStandings still imports LeagueUtils after the canonical current cutover."
Assert-True -Condition (-not $requestStandingsCutover.Contains("Get-SeasonDataRecursive")) -Message "RequestStandings still recursively traverses historical Sleeper leagues."
Assert-True -Condition (-not $requestStandingsCutover.Contains("previous_league_id")) -Message "RequestStandings still discovers historical seasons through Sleeper previous_league_id."

# Reproduce RequestStandings' import block in a clean module state and verify the
# canonical current/historical consumers plus shared derivation remain visible.
Remove-Module CanonicalStandingUtils, TeamUtils, StandingUtils, LeagueUtils -Force -ErrorAction SilentlyContinue
$requestImportLines = @(
    $requestStandingsCutover -split "`n" |
        Where-Object { $_ -match '^\s*Import-Module ' }
)
foreach ($importLine in $requestImportLines) {
    $resolvedImportLine = $importLine.Replace('$PSScriptRoot', $PSScriptRoot)
    Invoke-Expression $resolvedImportLine
}
Assert-True -Condition ($null -ne (Get-Command Get-StandingsRemote -ErrorAction SilentlyContinue)) -Message "RequestStandings import order hides Get-StandingsRemote from the caller scope."
Assert-True -Condition ($null -ne (Get-Command Get-CanonicalHistoricalStandings -ErrorAction SilentlyContinue)) -Message "RequestStandings import order hides the canonical historical standings consumer."
Assert-True -Condition ($null -ne (Get-Command Get-CanonicalCurrentSeasonData -ErrorAction SilentlyContinue)) -Message "RequestStandings import order hides the canonical current standings consumer."
Assert-True -Condition ($null -ne (Get-Command Get-CanonicalCurrentStandings -ErrorAction SilentlyContinue)) -Message "RequestStandings import order hides the canonical current standings compatibility wrapper."

# Cross-source previous-season award joins must not depend on the CLR numeric
# type used to materialize the same provider roster ID.
$mixedTypePreviousSeason = [PSCustomObject]@{
    RegularSeason = @(
        [PSCustomObject]@{
            TeamID         = [int]42
            Wins           = 6
            Points         = 1300
            WinPercentage  = 0.5
            PointsPerGame  = 100.0
        }
    )
}
$mixedTypeCurrentStandings = @(
    [PSCustomObject]@{
        Place                         = 1
        PlaceOrdinal                  = "1st"
        TeamID                        = [long]42
        Owner                         = "MixedTypeOwner"
        TeamName                      = "Mixed Type Team"
        Wins                          = 8
        Losses                        = 2
        Ties                          = 0
        WinPercentage                 = 0.75
        Points                        = 1450
        PointsPerGame                 = 110.0
        Record                        = "WWWWLWWWWL"
        LongestWinStreak              = 4
        WinStreakScore                = 4.1
        PointDifference               = 120
        EfficiencyScore               = 5.0
        PointsAgainstPerGame          = 95.0
        PointsAgainstPerGameDiffLeagueAvg = -3.0
        IronWillScore                 = 2.0
    }
)
$mixedTypeAwards = @(Get-Awards -regularSeasonStandings $mixedTypeCurrentStandings -playoffsStandings $null -previousSeasonStandings $mixedTypePreviousSeason)
Assert-Equal -Actual $mixedTypeCurrentStandings[0].ImprovementScore -Expected 0.35 -Message "Previous-season standings join still depends on numeric TeamID runtime type."
$mixedTypeMostImproved = @($mixedTypeAwards | Where-Object { $_.Name -eq "Most Improved" })
Assert-Equal -Actual $mixedTypeMostImproved.Count -Expected 1 -Message "Mixed-type previous-season join did not produce exactly one Most Improved award."
Assert-Equal -Actual $mixedTypeMostImproved[0].TeamID -Expected ([long]42) -Message "Mixed-type previous-season join resolved the wrong team."
Assert-Equal -Actual $mixedTypeMostImproved[0].StatDisplay -Expected "Wins: 6 to 8 | Points: 1300 to 1450" -Message "Mixed-type previous-season join lost previous-season award facts."


$discoveredHistoricalSeasons = @(Get-CanonicalHistoricalStandingSeasons -CanonicalLeagueID "nfl-reise")
Assert-Equal -Actual ($discoveredHistoricalSeasons -join ",") -Expected "2024,2025" -Message "Canonical historical standings discovery changed unexpectedly."

$publishedStandings = @(Get-Content (Get-Config).StandingsFile -Raw | ConvertFrom-Json)
$canonicalStandings = Get-CanonicalHistoricalStandings -CanonicalLeagueID "nfl-reise" -Seasons @("2024", "2025")

function ConvertTo-StandingsComparableValue {
    param([AllowNull()]$Value)

    if ($null -eq $Value) { return $null }

    if ($Value -is [string] -or $Value -is [char] -or $Value -is [bool] -or $Value -is [ValueType]) {
        return $Value
    }

    if ($Value -is [System.Collections.IDictionary]) {
        $ordered = [ordered]@{}
        foreach ($key in @($Value.Keys | ForEach-Object { [string]$_ } | Sort-Object)) {
            $ordered[$key] = ConvertTo-StandingsComparableValue -Value $Value[$key]
        }
        return [PSCustomObject]$ordered
    }

    if ($Value -is [pscustomobject]) {
        $ordered = [ordered]@{}
        foreach ($property in @($Value.PSObject.Properties | Sort-Object Name)) {
            $ordered[$property.Name] = ConvertTo-StandingsComparableValue -Value $property.Value
        }
        return [PSCustomObject]$ordered
    }

    if ($Value -is [System.Collections.IEnumerable]) {
        return @($Value | ForEach-Object { ConvertTo-StandingsComparableValue -Value $_ })
    }

    return $Value
}

function Assert-StandingsJsonEqual {
    param(
        [AllowNull()]$Actual,
        [AllowNull()]$Expected,
        [Parameter(Mandatory = $true)][string]$Message
    )

    $actualJson = ConvertTo-StandingsComparableValue -Value $Actual | ConvertTo-Json -Depth 100 -Compress
    $expectedJson = ConvertTo-StandingsComparableValue -Value $Expected | ConvertTo-Json -Depth 100 -Compress
    if ($actualJson -ne $expectedJson) {
        throw "$Message Canonical historical output differs from the published read model."
    }
}

$publishedCurrentSeason = @($publishedStandings | Where-Object { [string]$_.Season -eq [string](Get-Config).LeagueYear })
Assert-Equal -Actual $publishedCurrentSeason.Count -Expected 1 -Message "Published standings must contain the configured current season exactly once."

$canonicalPreviousSeason = @(
    $canonicalStandings.Seasons |
        Sort-Object { [int]$_.Season } -Descending |
        Select-Object -First 1
)
Assert-Equal -Actual $canonicalPreviousSeason.Count -Expected 1 -Message "Canonical current standings shadow requires exactly one previous-season standings context."

$canonicalCurrentSeasonData = Get-CanonicalCurrentSeasonData `
    -CanonicalLeagueID "nfl-reise" `
    -PreviousSeasonStandings $canonicalPreviousSeason[0]
Assert-StandingsJsonEqual -Actual $canonicalCurrentSeasonData.Output -Expected $publishedCurrentSeason[0] -Message "Canonical current standings cutover parity failed."

$canonicalCurrentSource = Get-CanonicalStandingSourceForSeason `
    -CanonicalLeagueID "nfl-reise" `
    -Season ([string](Get-Config).LeagueYear) `
    -AllowActiveSeason
Assert-Equal -Actual $canonicalCurrentSeasonData.IsCompleted -Expected $canonicalCurrentSource.IsCompleted -Message "Canonical current standings completion state is not propagated from league.json."

$canonicalCurrentStandings = Get-CanonicalCurrentStandings `
    -CanonicalLeagueID "nfl-reise" `
    -PreviousSeasonStandings $canonicalPreviousSeason[0]
Assert-StandingsJsonEqual -Actual $canonicalCurrentStandings -Expected $publishedCurrentSeason[0] -Message "Canonical current standings compatibility wrapper parity failed."

foreach ($season in @("2024", "2025")) {
    $publishedSeason = @($publishedStandings | Where-Object { [string]$_.Season -eq $season })
    $canonicalSeason = @($canonicalStandings.Seasons | Where-Object { [string]$_.Season -eq $season })
    Assert-Equal -Actual $publishedSeason.Count -Expected 1 -Message "Published standings must contain season $season exactly once."
    Assert-Equal -Actual $canonicalSeason.Count -Expected 1 -Message "Canonical historical consumer must contain season $season exactly once."
    Assert-StandingsJsonEqual -Actual $canonicalSeason[0] -Expected $publishedSeason[0] -Message "Canonical historical standings parity failed for $season."
}

$publishedAllTime = @($publishedStandings | Where-Object { [string]$_.Season -eq "AllTime" })
Assert-Equal -Actual $publishedAllTime.Count -Expected 1 -Message "Published standings must contain AllTime exactly once."
Assert-StandingsJsonEqual -Actual $canonicalStandings.AllTime -Expected $publishedAllTime[0] -Message "Canonical historical standings AllTime parity failed."

# Current League Core must reconstruct the source-owned League/Team inputs
# from canonical data without performing direct provider reads.
$canonicalLeagueCoreUtils = Get-Content "$PSScriptRoot\utils\league\CanonicalLeagueCoreUtils.psm1" -Raw
Assert-True -Condition (-not $canonicalLeagueCoreUtils.Contains("Get-LeagueRaw")) -Message "Canonical League Core shadow performs a legacy league read."
Assert-True -Condition (-not $canonicalLeagueCoreUtils.Contains("Get-Teams")) -Message "Canonical League Core shadow performs a legacy team read."
Assert-True -Condition (-not $canonicalLeagueCoreUtils.Contains("Get-SleeperMembers")) -Message "Canonical League Core shadow performs a direct Sleeper member read."
Assert-True -Condition (-not $canonicalLeagueCoreUtils.Contains("Get-SleeperRosters")) -Message "Canonical League Core shadow performs a direct Sleeper roster read."
Assert-True -Condition (-not $canonicalLeagueCoreUtils.Contains("Invoke-RestMethod")) -Message "Canonical League Core shadow performs a direct HTTP read."

$publishedLeague = Get-Content (Get-Config).LeagueFile -Raw | ConvertFrom-Json
$canonicalLeagueCoreShadow = Get-CanonicalCurrentLeagueCoreShadow -CanonicalLeagueID "nfl-reise"

$canonicalPlayoffUtils = Get-Content "$PSScriptRoot\utils\league\CanonicalPlayoffUtils.psm1" -Raw
Assert-True -Condition (-not $canonicalPlayoffUtils.Contains("Get-SleeperWinnersBracket")) -Message "Canonical Playoff shadow performs a live Sleeper winners-bracket read."
Assert-True -Condition (-not $canonicalPlayoffUtils.Contains("Get-SleeperLosersBracket")) -Message "Canonical Playoff shadow performs a live Sleeper losers-bracket read."
Assert-True -Condition (-not $canonicalPlayoffUtils.Contains("Get-Playoffs")) -Message "Canonical Playoff shadow delegates to the legacy live Playoff adapter."
Assert-True -Condition (-not $canonicalPlayoffUtils.Contains("Invoke-RestMethod")) -Message "Canonical Playoff shadow performs a direct HTTP read."

$canonicalPlayoffs = Get-CanonicalCurrentPlayoffs -CanonicalLeagueID "nfl-reise"
Assert-StandingsJsonEqual -Actual $canonicalPlayoffs -Expected $publishedLeague.Playoffs -Message "Canonical current Playoff shadow differs from published League.json::Playoffs."

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$providerLeagueID = [string]$canonicalLeagueCoreShadow.League.league_id
$rawWinnersPath = Join-Path $repoRoot "source-data/providers/sleeper/leagues/$providerLeagueID/winners-bracket.json"
$rawLosersPath = Join-Path $repoRoot "source-data/providers/sleeper/leagues/$providerLeagueID/losers-bracket.json"
$rawWinners = @((Get-Content $rawWinnersPath -Raw | ConvertFrom-Json))
$rawLosers = @((Get-Content $rawLosersPath -Raw | ConvertFrom-Json))
$shadowWinners = @($canonicalPlayoffs.WinnersBracket)
$shadowLosers = @($canonicalPlayoffs.LosersBracket)
Assert-StandingsJsonEqual -Actual $shadowWinners -Expected $rawWinners -Message "Canonical current winners bracket does not reconstruct raw Sleeper routing."
Assert-StandingsJsonEqual -Actual $shadowLosers -Expected $rawLosers -Message "Canonical current losers bracket does not reconstruct raw Sleeper routing."

Assert-Equal -Actual ([string]$canonicalLeagueCoreShadow.League.league_id) -Expected ([string]$publishedLeague.LeagueID) -Message "Canonical League Core provider LeagueID parity failed."
Assert-Equal -Actual ([string]$canonicalLeagueCoreShadow.League.name) -Expected ([string]$publishedLeague.Name) -Message "Canonical League Core name parity failed."
Assert-Equal -Actual ([string]$canonicalLeagueCoreShadow.League.season) -Expected ([string]$publishedLeague.Season) -Message "Canonical League Core season parity failed."
Assert-Equal -Actual ([string]$canonicalLeagueCoreShadow.League.season_type) -Expected ([string]$publishedLeague.SeasonType) -Message "Canonical League Core season type parity failed."
Assert-Equal -Actual ([int]$canonicalLeagueCoreShadow.League.total_rosters) -Expected ([int]$publishedLeague.TotalTeams) -Message "Canonical League Core team-count parity failed."
Assert-Equal -Actual ([string]$canonicalLeagueCoreShadow.League.previous_league_id) -Expected ([string]$publishedLeague.LeagueIDPrevious) -Message "Canonical League Core previous-LeagueID parity failed."

$canonicalLeagueAvatar = if ([string]::IsNullOrWhiteSpace([string]$canonicalLeagueCoreShadow.League.avatar)) {
    $null
}
else {
    Get-SleeperAvatar ([string]$canonicalLeagueCoreShadow.League.avatar)
}
Assert-Equal -Actual ([string]$canonicalLeagueAvatar) -Expected ([string]$publishedLeague.Avatar) -Message "Canonical League Core avatar parity failed."

$canonicalComparableSettings = $canonicalLeagueCoreShadow.League.settings | Select-Object * -ExcludeProperty daily_waivers_last_ran
$publishedComparableSettings = $publishedLeague.Settings | Select-Object * -ExcludeProperty daily_waivers_last_ran
Assert-StandingsJsonEqual -Actual $canonicalComparableSettings -Expected $publishedComparableSettings -Message "Canonical League Core stable-settings parity failed."
Assert-StandingsJsonEqual -Actual $canonicalLeagueCoreShadow.League.scoring_settings -Expected $publishedLeague.ScoringType -Message "Canonical League Core scoring settings parity failed."
Assert-StandingsJsonEqual -Actual @($canonicalLeagueCoreShadow.League.roster_positions) -Expected @($publishedLeague.RosterSize) -Message "Canonical League Core roster-position parity failed."

function Select-LeagueCoreTeamComparable {
    param([Parameter(Mandatory = $true)]$Team)

    return [PSCustomObject][ordered]@{
        Owner          = $Team.Owner
        OwnerID        = $Team.OwnerID
        OwnerAvatar    = $Team.OwnerAvatar
        Team           = $Team.Team
        TeamAbbr       = $Team.TeamAbbr
        TeamID         = $Team.TeamID
        TeamAvatar     = $Team.TeamAvatar
        MatchupID      = $Team.MatchupID
        WaiverPosition = $Team.WaiverPosition
        WaiverAdjusted = $Team.WaiverAdjusted
        IsCommissioner = $Team.IsCommissioner
        Roster         = @($Team.Roster)
        Reserve        = @($Team.Reserve)
        Taxi           = @($Team.Taxi)
        Starter        = @($Team.Starter)
    }
}

$canonicalCoreTeams = @(
    $canonicalLeagueCoreShadow.Teams |
        Sort-Object { [int]$_.TeamID } |
        ForEach-Object { Select-LeagueCoreTeamComparable -Team $_ }
)
$publishedCoreTeams = @(
    $publishedLeague.Teams |
        Sort-Object { [int]$_.TeamID } |
        ForEach-Object { Select-LeagueCoreTeamComparable -Team $_ }
)
Assert-Equal -Actual $canonicalCoreTeams.Count -Expected $publishedCoreTeams.Count -Message "Canonical League Core team count differs from published League.json."
Assert-StandingsJsonEqual -Actual $canonicalCoreTeams -Expected $publishedCoreTeams -Message "Canonical League Core team-source parity failed."

Write-Host "League transaction and overview regression tests passed." -ForegroundColor Green
