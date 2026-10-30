# ===========================================================================
# League metadata loader (data-meta/<CanonicalLeagueID>/metadata.json)
# Contract: .ai-context/manual/league-metadata.yaml (ADR-054). Fail-closed.
# PowerShell counterpart of tools/league_metadata.py; keep both validations aligned.
# ===========================================================================

# Interim model catalogue; replaced by the model registry of Issue #919 once it exists.
$script:KnownModelIds = @{
    Salary    = @('salary-v1')
    SalaryCap = @('salary-cap-v1')
    Grading   = @('grading-v1')
    Standings = @('standings-v1')
    Awards    = @('awards-v1')
    Lifecycle = @('lifecycle-v1')
    Repairability = @('repairability-v1')
}
$script:TopLevelKeys = @('SchemaVersion', 'CanonicalLeagueID', 'Provider', 'CurrentProviderLeagueID', 'LeagueTimeZone', 'Owners', 'Drafts', 'Seasons')
$script:SeasonKeys = @('CapDeadline', 'CapDeadlineBufferDays', 'Models')

function Assert-LeagueMetadata {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw "League metadata invalid: $Message" }
}

function Get-DataMetaDir {
    # DATA_META_ROOT overrides the root (tests, fixtures); the default comes from ConfigUtils.psm1.
    if (-not [string]::IsNullOrWhiteSpace($env:DATA_META_ROOT)) { return $env:DATA_META_ROOT }
    Import-Module "$PSScriptRoot\ConfigUtils.psm1" -ErrorAction Stop
    return Get-DataMetaRoot -RepoRoot ([System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..')))
}

function Get-LeagueMetadataIds {
    param([string]$Root = (Get-DataMetaDir))

    Assert-LeagueMetadata (Test-Path -LiteralPath $Root -PathType Container) "data-meta root not found: $Root"
    return @(Get-ChildItem -LiteralPath $Root -Directory |
        Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName 'metadata.json') } |
        Sort-Object Name | ForEach-Object { $_.Name })
}

function Get-LeagueMetadata {
    param(
        [Parameter(Mandatory = $true)][string]$LeagueId,
        [string]$Root = (Get-DataMetaDir)
    )

    $path = Join-Path (Join-Path $Root $LeagueId) 'metadata.json'
    Assert-LeagueMetadata (Test-Path -LiteralPath $path -PathType Leaf) "not found: $path"
    $raw = Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json
    Test-LeagueMetadata -Metadata $raw -ExpectedLeagueId $LeagueId -Source $path
    return $raw
}

function Get-AllLeagueMetadata {
    param([string]$Root = (Get-DataMetaDir))

    $ids = Get-LeagueMetadataIds -Root $Root
    Assert-LeagueMetadata ($ids.Count -gt 0) "no league metadata under $Root"
    $result = [ordered]@{}
    foreach ($id in $ids) { $result[$id] = Get-LeagueMetadata -LeagueId $id -Root $Root }
    return $result
}

function Test-LeagueMetadata {
    param(
        [Parameter(Mandatory = $true)]$Metadata,
        [string]$ExpectedLeagueId,
        [string]$Source = 'metadata'
    )

    $names = @($Metadata.PSObject.Properties.Name)
    $missing = @($script:TopLevelKeys | Where-Object { $names -notcontains $_ })
    $extra = @($names | Where-Object { $script:TopLevelKeys -notcontains $_ })
    Assert-LeagueMetadata (($missing.Count -eq 0) -and ($extra.Count -eq 0)) "${Source}: missing=$($missing -join ',') unknown=$($extra -join ',')"
    Assert-LeagueMetadata ($Metadata.SchemaVersion -eq 1) "${Source}: unsupported SchemaVersion"
    Assert-LeagueMetadata ([string]$Metadata.CanonicalLeagueID -cmatch '^[a-z0-9]+(?:-[a-z0-9]+)*$') "${Source}: invalid CanonicalLeagueID"
    if ($ExpectedLeagueId) {
        Assert-LeagueMetadata ($Metadata.CanonicalLeagueID -ceq $ExpectedLeagueId) "${Source}: CanonicalLeagueID differs from directory $ExpectedLeagueId"
    }
    Assert-LeagueMetadata ($Metadata.Provider -ceq 'Sleeper') "${Source}: unsupported Provider"
    Assert-LeagueMetadata ([string]$Metadata.CurrentProviderLeagueID -match '^[0-9]+$') "${Source}: invalid CurrentProviderLeagueID"
    $tz = $null
    Assert-LeagueMetadata (-not [string]::IsNullOrWhiteSpace([string]$Metadata.LeagueTimeZone)) "${Source}: LeagueTimeZone missing"
    try { $tz = [System.TimeZoneInfo]::FindSystemTimeZoneById([string]$Metadata.LeagueTimeZone) } catch { $tz = $null }
    Assert-LeagueMetadata ($null -ne $tz) "${Source}: invalid LeagueTimeZone"

    $owners = @($Metadata.Owners.PSObject.Properties)
    Assert-LeagueMetadata ($owners.Count -gt 0) "${Source}: Owners empty"
    Assert-LeagueMetadata (@($owners | Select-Object -ExpandProperty Value -Unique).Count -eq $owners.Count) "${Source}: Owners values must be unique"

    $drafts = $Metadata.Drafts
    Assert-LeagueMetadata ($drafts.UpcomingDraftCountMode -ceq 'PerDraftType') "${Source}: Drafts.UpcomingDraftCountMode must be PerDraftType"
    Assert-LeagueMetadata ([int]$drafts.UpcomingDraftCount -ge 0) "${Source}: Drafts.UpcomingDraftCount invalid"
    $slots = @{}
    foreach ($d in @($drafts.Types)) {
        Assert-LeagueMetadata (-not [string]::IsNullOrWhiteSpace([string]$d.DraftType)) "${Source}: draft without DraftType"
        Assert-LeagueMetadata ([int]$d.DraftInstance -ge 1) "${Source}: $($d.DraftType) needs DraftInstance >= 1"
        $slot = "$($d.DraftType)/$($d.DraftInstance)"
        Assert-LeagueMetadata (-not $slots.ContainsKey($slot)) "${Source}: duplicate draft slot $slot"
        $slots[$slot] = $true
    }
    Assert-LeagueMetadata ($slots.Count -gt 0) "${Source}: Drafts.Types empty"

    $seasons = @($Metadata.Seasons.PSObject.Properties)
    Assert-LeagueMetadata ($seasons.Count -gt 0) "${Source}: Seasons empty"
    foreach ($s in $seasons) {
        $where = "${Source}: Seasons.$($s.Name)"
        Assert-LeagueMetadata ($s.Name -match '^[0-9]{4}$') "${where}: season key must be four digits"
        $entryNames = @($s.Value.PSObject.Properties.Name)
        $badKeys = @($entryNames | Where-Object { $script:SeasonKeys -notcontains $_ })
        Assert-LeagueMetadata (($badKeys.Count -eq 0) -and ($entryNames -contains 'Models')) "${where}: unknown=$($badKeys -join ',') Models required"
        $hasDeadline = $entryNames -contains 'CapDeadline'
        Assert-LeagueMetadata ($hasDeadline -eq ($entryNames -contains 'CapDeadlineBufferDays')) "${where}: CapDeadline and CapDeadlineBufferDays go together"
        if ($hasDeadline) {
            Assert-LeagueMetadata ([int]$s.Value.CapDeadlineBufferDays -ge 0) "${where}: CapDeadlineBufferDays invalid"
        }
        $modelNames = @($s.Value.Models.PSObject.Properties.Name)
        Assert-LeagueMetadata ((@($modelNames | Sort-Object) -join ',') -ceq (@($script:KnownModelIds.Keys | Sort-Object) -join ',')) "${where}: Models must name exactly $(@($script:KnownModelIds.Keys | Sort-Object) -join ',')"
        foreach ($kind in $modelNames) {
            Assert-LeagueMetadata ($script:KnownModelIds[$kind] -ccontains [string]$s.Value.Models.$kind) "${where}: unknown $kind model '$($s.Value.Models.$kind)'"
        }
    }
}

function Get-LeagueSeasonEntry {
    param([Parameter(Mandatory = $true)]$Metadata, [Parameter(Mandatory = $true)]$Season)

    $prop = $Metadata.Seasons.PSObject.Properties[[string]$Season]
    Assert-LeagueMetadata ($null -ne $prop) "$($Metadata.CanonicalLeagueID): no metadata for season $Season"
    return $prop.Value
}

function Get-LeagueSeasonModel {
    param([Parameter(Mandatory = $true)]$Metadata, [Parameter(Mandatory = $true)]$Season, [Parameter(Mandatory = $true)][string]$Kind)

    $entry = Get-LeagueSeasonEntry -Metadata $Metadata -Season $Season
    $prop = $entry.Models.PSObject.Properties[$Kind]
    Assert-LeagueMetadata ($null -ne $prop) "unknown model kind $Kind"
    return [string]$prop.Value
}

function Get-LeagueCapDeadline {
    param([Parameter(Mandatory = $true)]$Metadata, [Parameter(Mandatory = $true)]$Season)

    $entry = Get-LeagueSeasonEntry -Metadata $Metadata -Season $Season
    Assert-LeagueMetadata ($null -ne $entry.PSObject.Properties['CapDeadline']) "$($Metadata.CanonicalLeagueID): season $Season has no CapDeadline"
    # ConvertFrom-Json may have parsed the ISO timestamp into a DateTime; return the canonical UTC form.
    $deadline = $entry.CapDeadline
    if ($deadline -is [datetime]) { $deadline = $deadline.ToUniversalTime().ToString("yyyy-MM-dd'T'HH:mm:ss'Z'") }
    return @{ CapDeadline = [string]$deadline; CapDeadlineBufferDays = [int]$entry.CapDeadlineBufferDays }
}

Export-ModuleMember -Function Get-DataMetaDir, Get-LeagueMetadataIds, Get-LeagueMetadata, Get-AllLeagueMetadata, Test-LeagueMetadata, Get-LeagueSeasonEntry, Get-LeagueSeasonModel, Get-LeagueCapDeadline
