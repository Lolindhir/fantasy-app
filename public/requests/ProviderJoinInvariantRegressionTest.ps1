$ErrorActionPreference = "Stop"

Import-Module "$PSScriptRoot\utils\general\ProviderJoinUtils.psm1" -ErrorAction Stop -Force
Import-Module "$PSScriptRoot\utils\general\SleeperPlayerIdUtils.psm1" -ErrorAction Stop -Force
Import-Module "$PSScriptRoot\utils\league\TeamUtils.psm1" -ErrorAction Stop -Force

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

# Sleeper empty-slot contract: null, blank and "0" mean no player; real ids are trimmed and kept.
foreach ($emptyValue in @($null, "", "  ", "0", 0, " 0 ")) {
    if ($null -ne (ConvertTo-SleeperPlayerID -Value $emptyValue)) {
        throw "ConvertTo-SleeperPlayerID must treat '$emptyValue' as no player."
    }
}
if ((ConvertTo-SleeperPlayerID -Value " 4046 ") -ne "4046" -or (ConvertTo-SleeperPlayerID -Value "10") -ne "10") {
    throw "ConvertTo-SleeperPlayerID must keep real player ids."
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

# Position fallback and supported App fantasy positions are now covered by
# tools/tests/test_nfl_source_players_population.py in the Python Fast lane.
# This test retains independent PowerShell provider and team join guards.

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


Write-Host "Provider join invariant regression tests passed." -ForegroundColor Green