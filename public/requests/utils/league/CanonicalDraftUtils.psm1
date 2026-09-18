# ===========================================================================
# Canonical League Draft consumer
# ===========================================================================

$script:CanonicalDraftPayloadCache = @{}

function Get-DraftCanonicalRepoRoot {
    return (Resolve-Path (Join-Path $PSScriptRoot "../../../..")).Path
}

function Get-DraftCanonicalPythonCommand {
    foreach ($name in @("python3", "python")) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($command) { return $command.Source }
    }
    throw "Python is required for the canonical draft consumer."
}

function Invoke-DraftCanonicalConsumer {
    param(
        [Parameter(Mandatory = $true)][string]$CanonicalLeagueID,
        [Parameter(Mandatory = $true)][string]$Season
    )
    $repoRoot = Get-DraftCanonicalRepoRoot
    $toolPath = Join-Path $repoRoot "tools/draft_canonical_consumer.py"
    if (-not (Test-Path $toolPath)) { throw "Canonical draft consumer tool missing at '$toolPath'." }
    $python = Get-DraftCanonicalPythonCommand
    $output = & $python $toolPath --repo-root $repoRoot --canonical-league-id $CanonicalLeagueID --season $Season 2>&1
    $exitCode = $LASTEXITCODE
    $outputText = (@($output) | ForEach-Object { [string]$_ }) -join [Environment]::NewLine
    if ($exitCode -ne 0) { throw "Canonical draft consumer failed with exit code $exitCode. $outputText" }
    try { return $outputText | ConvertFrom-Json }
    catch { throw "Canonical draft consumer returned invalid JSON. $_" }
}

function Get-CanonicalDraftLegacyPayload {
    param([Parameter(Mandatory = $true)][string]$Season, [string]$CanonicalLeagueID = "nfl-reise")
    $cacheKey = "$CanonicalLeagueID|$Season"
    if (-not $script:CanonicalDraftPayloadCache.ContainsKey($cacheKey)) {
        $script:CanonicalDraftPayloadCache[$cacheKey] = Invoke-DraftCanonicalConsumer -CanonicalLeagueID $CanonicalLeagueID -Season $Season
    }
    return $script:CanonicalDraftPayloadCache[$cacheKey]
}

function Get-CanonicalSleeperDrafts {
    param([Parameter(Mandatory = $true)][string]$Season, [string]$CanonicalLeagueID = "nfl-reise")
    $payload = Get-CanonicalDraftLegacyPayload -Season $Season -CanonicalLeagueID $CanonicalLeagueID
    return @($payload.Drafts)
}

function Get-CanonicalSleeperDraft {
    param([Parameter(Mandatory = $true)][string]$Season, [Parameter(Mandatory = $true)][string]$DraftID, [string]$CanonicalLeagueID = "nfl-reise")
    $matches = @(Get-CanonicalSleeperDrafts -Season $Season -CanonicalLeagueID $CanonicalLeagueID | Where-Object { [string]$_.draft_id -eq [string]$DraftID })
    if ($matches.Count -ne 1) { throw "Canonical draft '$DraftID' in season '$Season' was not found exactly once." }
    return $matches[0]
}

function Get-CanonicalDraftPayloadCollection {
    param([Parameter(Mandatory = $true)][object]$Payload, [Parameter(Mandatory = $true)][string]$PropertyName, [Parameter(Mandatory = $true)][string]$DraftID)
    $container = $Payload.PSObject.Properties[$PropertyName].Value
    if ($null -eq $container) { throw "Canonical draft payload is missing '$PropertyName'." }
    $property = $container.PSObject.Properties[$DraftID]
    if ($null -eq $property) { throw "Canonical draft payload '$PropertyName' has no entry for draft '$DraftID'." }
    return @($property.Value)
}

function Get-CanonicalSleeperDraftPicks {
    param([Parameter(Mandatory = $true)][string]$Season, [Parameter(Mandatory = $true)][string]$DraftID, [string]$CanonicalLeagueID = "nfl-reise")
    $payload = Get-CanonicalDraftLegacyPayload -Season $Season -CanonicalLeagueID $CanonicalLeagueID
    return @(Get-CanonicalDraftPayloadCollection -Payload $payload -PropertyName "PicksByDraftID" -DraftID $DraftID)
}

function Get-CanonicalSleeperDraftTradedPicks {
    param([Parameter(Mandatory = $true)][string]$Season, [Parameter(Mandatory = $true)][string]$DraftID, [string]$CanonicalLeagueID = "nfl-reise")
    $payload = Get-CanonicalDraftLegacyPayload -Season $Season -CanonicalLeagueID $CanonicalLeagueID
    return @(Get-CanonicalDraftPayloadCollection -Payload $payload -PropertyName "TradedPicksByDraftID" -DraftID $DraftID)
}

function Clear-CanonicalDraftPayloadCache { $script:CanonicalDraftPayloadCache = @{} }

Export-ModuleMember -Function @(
    "Get-CanonicalDraftLegacyPayload",
    "Get-CanonicalSleeperDrafts",
    "Get-CanonicalSleeperDraft",
    "Get-CanonicalSleeperDraftPicks",
    "Get-CanonicalSleeperDraftTradedPicks",
    "Clear-CanonicalDraftPayloadCache"
)
