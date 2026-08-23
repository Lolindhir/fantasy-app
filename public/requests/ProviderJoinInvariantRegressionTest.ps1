$ErrorActionPreference = "Stop"

Import-Module "$PSScriptRoot\utils\general\ProviderJoinUtils.psm1" -ErrorAction Stop -Force
Import-Module "$PSScriptRoot\utils\player\PlayerUtils.psm1" -ErrorAction Stop -Force
Import-Module "$PSScriptRoot\utils\league\TeamUtils.psm1" -ErrorAction Stop -Force
Import-Module "$PSScriptRoot\utils\league\DraftUtils.psm1" -ErrorAction Stop -Force
Import-Module "$PSScriptRoot\utils\league\TransactionUtils.psm1" -ErrorAction Stop -Force
Import-Module "$PSScriptRoot\utils\league\TransactionDraftPickEnrichmentUtils.psm1" -ErrorAction Stop -Force
Import-Module "$PSScriptRoot\utils\league\HistoricalTransactionDraftPickIdentityUtils.psm1" -ErrorAction Stop -Force

function Test-Throws {
    param(
        [Parameter(Mandatory = $true)][scriptblock]$Action,
        [Parameter(Mandatory = $true)][string]$ExpectedMessagePart
    )

    $thrown = $false
    try {
        & $Action
    }
    catch {
        $thrown = $true
        if ([string]$_.Exception.Message -notlike "*$ExpectedMessagePart*") {
            throw "Expected error containing '$ExpectedMessagePart', got '$($_.Exception.Message)'."
        }
    }

    if (-not $thrown) {
        throw "Expected action to throw an error containing '$ExpectedMessagePart'."
    }
}

# Generic lookup contract.
$lookup = New-UniqueObjectLookup `
    -Items @(
        [PSCustomObject]@{ id = "a"; name = "Alpha" },
        [PSCustomObject]@{ id = "b"; name = "Beta" }
    ) `
    -KeyProperty "id" `
    -SourceLabel "test source" `
    -DescriptionProperties @("id", "name")
if ($lookup.Count -ne 2 -or $lookup["a"].name -ne "Alpha") {
    throw "Unique provider lookup did not preserve the expected records."
}
Test-Throws -ExpectedMessagePart "Duplicate id 'a'" -Action {
    New-UniqueObjectLookup `
        -Items @(
            [PSCustomObject]@{ id = "a"; name = "Alpha" },
            [PSCustomObject]@{ id = "a"; name = "Other" }
        ) `
        -KeyProperty "id" `
        -SourceLabel "test source" `
        -DescriptionProperties @("id", "name") | Out-Null
}
Test-Throws -ExpectedMessagePart "missing id" -Action {
    New-UniqueObjectLookup `
        -Items @([PSCustomObject]@{ id = $null; name = "Missing" }) `
        -KeyProperty "id" `
        -SourceLabel "test source" `
        -DescriptionProperties @("id", "name") | Out-Null
}

# Player joins: Tank01 provider IDs and Tank01 -> Sleeper mappings must be unique.
Test-Throws -ExpectedMessagePart "Duplicate sleeperBotID 's1'" -Action {
    New-PlayerProviderLookups `
        -SleeperPlayers @([PSCustomObject]@{ player_id = "s1"; full_name = "Sleeper One" }) `
        -TankPlayers @(
            [PSCustomObject]@{ playerID = "t1"; sleeperBotID = "s1"; longName = "Tank One" },
            [PSCustomObject]@{ playerID = "t2"; sleeperBotID = "s1"; longName = "Tank Two" }
        ) | Out-Null
}
Test-Throws -ExpectedMessagePart "Duplicate TankID 't1'" -Action {
    New-HistoricalPlayerTankLookup `
        -Season "2025" `
        -Players @(
            [PSCustomObject]@{ TankID = "t1"; ID = "s1"; Name = "One" },
            [PSCustomObject]@{ TankID = "t1"; ID = "s2"; Name = "Two" }
        ) | Out-Null
}

# Team joins: owner/member cardinality is 1:1 and every roster owner must exist.
$teamLookups = New-SleeperTeamSourceLookups `
    -Members @(
        [PSCustomObject]@{ user_id = "u1"; display_name = "One" },
        [PSCustomObject]@{ user_id = "u2"; display_name = "Two" }
    ) `
    -Rosters @(
        [PSCustomObject]@{ roster_id = 1; owner_id = "u1" },
        [PSCustomObject]@{ roster_id = 2; owner_id = "u2" }
    )
if ($teamLookups.MembersByUserID.Count -ne 2) {
    throw "Sleeper team lookup validation lost a valid member."
}
Test-Throws -ExpectedMessagePart "Duplicate user_id 'u1'" -Action {
    New-SleeperTeamSourceLookups `
        -Members @(
            [PSCustomObject]@{ user_id = "u1"; display_name = "One" },
            [PSCustomObject]@{ user_id = "u1"; display_name = "Other" }
        ) `
        -Rosters @([PSCustomObject]@{ roster_id = 1; owner_id = "u1" }) | Out-Null
}
Test-Throws -ExpectedMessagePart "no unique league member" -Action {
    New-SleeperTeamSourceLookups `
        -Members @([PSCustomObject]@{ user_id = "u1"; display_name = "One" }) `
        -Rosters @([PSCustomObject]@{ roster_id = 2; owner_id = "missing" }) | Out-Null
}

# Draft joins: raw draft IDs, explicit bindings, season standings and generated PickKeys are unique.
Test-Throws -ExpectedMessagePart "Duplicate draft_id 'd1'" -Action {
    New-SleeperDraftSourceLookup -SleeperDrafts @(
        [PSCustomObject]@{ draft_id = "d1"; season = "2026"; status = "pre_draft" },
        [PSCustomObject]@{ draft_id = "d1"; season = "2026"; status = "complete" }
    ) | Out-Null
}
Test-Throws -ExpectedMessagePart "explicit bindings are authoritative" -Action {
    Get-ConfiguredSleeperDraftMatch `
        -UnboundDrafts @([PSCustomObject]@{ draft_id = "other"; season = "2026" }) `
        -ConfiguredDraftID "configured" `
        -Season "2026" | Out-Null
}
Test-Throws -ExpectedMessagePart "Duplicate standing identity" -Action {
    Get-DraftStandingBySeason `
        -Season "2025" `
        -Standings @(
            [PSCustomObject]@{ Season = "2025"; Playoffs = @() },
            [PSCustomObject]@{ Season = "2025"; Playoffs = @() }
        ) | Out-Null
}
Test-Throws -ExpectedMessagePart "Duplicate PickKey '2026_Rookie_R1_OO1'" -Action {
    Get-AppliedDraftPickTrades `
        -DraftKey "2026_Rookie" `
        -Transactions @() `
        -Picks @(
            [PSCustomObject]@{ PickKey = "2026_Rookie_R1_OO1"; Season = "2026"; Round = 1; OriginalOwnerRosterID = 1; CurrentOwnerRosterID = 1 },
            [PSCustomObject]@{ PickKey = "2026_Rookie_R1_OO1"; Season = "2026"; Round = 1; OriginalOwnerRosterID = 1; CurrentOwnerRosterID = 2 }
        ) | Out-Null
}

# Transaction IDs and manual Sleeper bindings must never use first/last-wins semantics.
Test-Throws -ExpectedMessagePart "Duplicate TransactionID 'tx1'" -Action {
    Test-TransactionIdentityInvariants -Transactions @(
        [PSCustomObject]@{ TransactionID = "tx1"; Source = "Sleeper"; Season = "2026"; Week = 1 },
        [PSCustomObject]@{ TransactionID = "tx1"; Source = "Sleeper"; Season = "2026"; Week = 2 }
    ) | Out-Null
}
Test-Throws -ExpectedMessagePart "Duplicate SleeperTransactionID 'tx1'" -Action {
    New-ManualTransactionBindingLookup -ManualTransactions @(
        [PSCustomObject]@{ SleeperTransactionID = "tx1"; Season = "2026"; Week = 1; Date = "2026-09-01" },
        [PSCustomObject]@{ SleeperTransactionID = "tx1"; Season = "2026"; Week = 1; Date = "2026-09-02" }
    ) | Out-Null
}

# Historical concrete contexts require a provider ID and cannot overwrite identical identities.
Test-Throws -ExpectedMessagePart "has no Sleeper draft_id" -Action {
    New-HistoricalTransactionDraftPickSleeperContext `
        -Definition ([PSCustomObject]@{
            Season = "2025"
            DraftType = "Rookie"
            DraftInstance = 1
            DraftCode = "Rookie"
            DraftKey = "2025_Rookie"
            SleeperDraft = [PSCustomObject]@{}
        }) | Out-Null
}

# Current and archived copies of the same pick are allowed only when enrichment facts agree exactly.
$baseDraft = [PSCustomObject]@{
    DraftKey = "2026_Rookie"
    DraftType = "Rookie"
    DraftInstance = 1
    DraftCode = "Rookie"
    SleeperDraftID = "d1"
}
$basePick = [PSCustomObject]@{
    PickKey = "2026_Rookie_R1_OO1"
    Season = "2026"
    Round = 1
    PositionInRound = 1
    OverallPick = 1
    DisplayPick = "1.01"
    PlayerID = "p1"
    PlayerName = "Player One"
    Status = "Picked"
    SleeperPickNo = 1
}
$candidateA = [PSCustomObject]@{ Draft = $baseDraft; Pick = $basePick }
$candidateB = [PSCustomObject]@{
    Draft = [PSCustomObject]@{
        DraftKey = "2026_Rookie"
        DraftType = "Rookie"
        DraftInstance = 1
        DraftCode = "Rookie"
        SleeperDraftID = "d1"
    }
    Pick = [PSCustomObject]@{
        PickKey = "2026_Rookie_R1_OO1"
        Season = "2026"
        Round = 1
        PositionInRound = 1
        OverallPick = 1
        DisplayPick = "1.01"
        PlayerID = "p1"
        PlayerName = "Player One"
        Status = "Picked"
        SleeperPickNo = 1
    }
}
$deduped = Get-UniqueTransactionDraftPickResultCandidates -Candidates @($candidateA, $candidateB)
if ($deduped.Count -ne 1) {
    throw "Semantically identical current/history draft-pick copies should collapse to one candidate."
}
$candidateB.Pick.PlayerID = "different-player"
Test-Throws -ExpectedMessagePart "Conflicting duplicate generated draft-pick identity" -Action {
    Get-UniqueTransactionDraftPickResultCandidates -Candidates @($candidateA, $candidateB) | Out-Null
}

Write-Host "Provider join invariant regression tests passed." -ForegroundColor Green
