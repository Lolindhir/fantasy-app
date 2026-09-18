$ErrorActionPreference = "Stop"

Import-Module "$PSScriptRoot\utils\league\CanonicalTransactionUtils.psm1" -Force
Import-Module "$PSScriptRoot\utils\league\CanonicalDraftUtils.psm1" -Force
Import-Module "$PSScriptRoot\utils\league\TransactionUtils.psm1" -Force
Import-Module "$PSScriptRoot\utils\league\LeagueTransactionPipelineUtils.psm1" -Force
Import-Module "$PSScriptRoot\utils\league\LeagueOverviewUtils.psm1" -Force
Import-Module "$PSScriptRoot\utils\league\CanonicalStandingUtils.psm1" -Force

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


# Canonical historical standings are productive for completed seasons, while
# the current season must remain on the existing live Sleeper-backed path.
$canonicalStandingUtils = Get-Content "$PSScriptRoot\utils\league\CanonicalStandingUtils.psm1" -Raw
Assert-True -Condition (-not $canonicalStandingUtils.Contains("Get-LeagueRaw")) -Message "Canonical historical standings consumer performs a direct Sleeper league read."
Assert-True -Condition (-not $canonicalStandingUtils.Contains("Get-Teams")) -Message "Canonical historical standings consumer performs a direct Sleeper team read."
Assert-True -Condition (-not $canonicalStandingUtils.Contains("Get-SleeperWinnersBracket")) -Message "Canonical historical standings consumer performs a direct Sleeper winners-bracket read."
Assert-True -Condition (-not $canonicalStandingUtils.Contains("Get-SleeperLosersBracket")) -Message "Canonical historical standings consumer performs a direct Sleeper losers-bracket read."

$requestStandingsCutover = Get-Content "$PSScriptRoot\RequestStandings.ps1" -Raw
Assert-True -Condition $requestStandingsCutover.Contains("CanonicalStandingUtils.psm1") -Message "RequestStandings does not import the canonical historical standings consumer."
Assert-True -Condition $requestStandingsCutover.Contains("Get-CanonicalHistoricalStandings") -Message "RequestStandings does not consume canonical historical standings."
Assert-True -Condition $requestStandingsCutover.Contains("Get-CurrentSeasonData") -Message "RequestStandings no longer has an explicit current-season live boundary."
Assert-True -Condition $requestStandingsCutover.Contains("Get-LeagueRaw -leagueID `$leagueID") -Message "Current standings no longer read current live league state."
Assert-True -Condition $requestStandingsCutover.Contains("Get-Teams -leagueID `$leagueID") -Message "Current standings no longer read current live team state."
Assert-True -Condition (-not $requestStandingsCutover.Contains("Get-SeasonDataRecursive")) -Message "RequestStandings still recursively traverses historical Sleeper leagues."
Assert-True -Condition (-not $requestStandingsCutover.Contains("previous_league_id")) -Message "RequestStandings still discovers historical seasons through Sleeper previous_league_id."
Assert-Equal -Actual (Get-OccurrenceCount -Text $requestStandingsCutover -Needle "Get-LeagueRaw -leagueID `$leagueID") -Expected 1 -Message "RequestStandings should perform one current live league read."
Assert-Equal -Actual (Get-OccurrenceCount -Text $requestStandingsCutover -Needle "Get-Teams -leagueID `$leagueID") -Expected 1 -Message "RequestStandings should perform one current live team read."

# Reproduce RequestStandings' import block in a clean module state. Nested -Force
# imports must not hide the direct commands needed by the current live boundary.
Remove-Module CanonicalStandingUtils, TeamUtils, StandingUtils, LeagueUtils -Force -ErrorAction SilentlyContinue
$requestImportLines = @(
    $requestStandingsCutover -split "`n" |
        Where-Object { $_ -match '^\s*Import-Module ' }
)
foreach ($importLine in $requestImportLines) {
    Invoke-Expression $importLine
}
Assert-True -Condition ($null -ne (Get-Command Get-LeagueRaw -ErrorAction SilentlyContinue)) -Message "RequestStandings import order hides Get-LeagueRaw from the caller scope."
Assert-True -Condition ($null -ne (Get-Command Get-Teams -ErrorAction SilentlyContinue)) -Message "RequestStandings import order hides Get-Teams from the caller scope."
Assert-True -Condition ($null -ne (Get-Command Get-StandingsRemote -ErrorAction SilentlyContinue)) -Message "RequestStandings import order hides Get-StandingsRemote from the caller scope."
Assert-True -Condition ($null -ne (Get-Command Get-CanonicalHistoricalStandings -ErrorAction SilentlyContinue)) -Message "RequestStandings import order hides the canonical historical standings consumer."


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

Write-Host "League transaction and overview regression tests passed." -ForegroundColor Green
