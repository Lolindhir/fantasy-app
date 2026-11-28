# AC6A: actual pwsh execution at the metadata Get-Content reader boundary.
# Test-only module-local instrumentation; no productive module or files modified.
param(
    [Parameter(Mandatory = $true)][string]$RepoRoot,
    [Parameter(Mandatory = $true)][string]$ScratchRoot,
    [Parameter(Mandatory = $true)][string]$Season,
    [Parameter(Mandatory = $true)][string]$ExpectedTeamRange,
    [Parameter(Mandatory = $true)][string]$ExpectedWinProb,
    [Parameter(Mandatory = $true)][string]$EventFile
)
$ErrorActionPreference = 'Stop'
$utils = Join-Path $RepoRoot 'public/requests/utils'
Import-Module (Join-Path $utils 'ConfigUtils.psm1') -Force -ErrorAction Stop
$metaRoot = Get-DataMetaRoot -RepoRoot $ScratchRoot
$module = Import-Module (Join-Path $utils 'LeagueMetadataUtils.psm1') -Force -PassThru -ErrorAction Stop

# Invoke in the real module session state so the instrumented reader is
# visible to Get-LeagueMetadata. Only forward the cmdlet's actual parameters.
# This is a cmdlet boundary, not a native/.NET file-access tracer.
$rows = @(& $module {
    param($root, $year, $teamRange, $winProb, $codeRoot)
    $script:ForecastTraceRows = [System.Collections.Generic.List[object]]::new()
    $script:ForecastTraceMetaRoot = $root
    $script:ForecastTraceCodeRoot = $codeRoot
    function script:Get-Content {
        [CmdletBinding()]
        param(
            [Parameter(Mandatory = $true)][string]$LiteralPath,
            [switch]$Raw,
            [string]$Encoding
        )
        $relative = [System.IO.Path]::GetRelativePath($script:ForecastTraceMetaRoot, [System.IO.Path]::GetFullPath($LiteralPath)).Replace('\', '/')
        if ($relative -eq '..' -or $relative.StartsWith('../') -or [System.IO.Path]::IsPathRooted($relative)) {
            throw "Unexpected metadata reader path: $LiteralPath"
        }
        $stack = @(Get-PSCallStack)
        $caller = $stack[1]
        $source = [System.IO.Path]::GetRelativePath($script:ForecastTraceCodeRoot, $caller.ScriptName).Replace('\', '/')
        $site = $source + ':' + $caller.FunctionName
        $script:ForecastTraceRows.Add([ordered]@{
            pid = $PID
            kind = 'open'
            root = 'meta'
            path = $relative
            read = $true
            write = $false
            sites = @($site)
        })
        Microsoft.PowerShell.Management\Get-Content @PSBoundParameters
    }
    try {
        foreach ($id in @('league-a', 'league-b')) {
            $document = Get-LeagueMetadata -LeagueId $id -Root $root
            if ($document.CanonicalLeagueID -cne $id) { throw 'Wrong league returned' }
            if ((Get-LeagueSeasonModel -Metadata $document -Season $year -Kind 'TeamRange') -cne $teamRange) {
                throw 'TeamRange selection changed'
            }
            if ((Get-LeagueSeasonModel -Metadata $document -Season $year -Kind 'WinProb') -cne $winProb) {
                throw 'WinProb selection changed'
            }
        }
        $invalidRejected = $false
        try { Get-LeagueMetadata -LeagueId 'invalid' -Root $root | Out-Null }
        catch { $invalidRejected = $_.Exception.Message -like '*unknown TeamRange model*' }
        if (-not $invalidRejected) { throw 'Invalid model must fail closed after its metadata read' }

        $missingRejected = $false
        try { Get-LeagueMetadata -LeagueId 'missing' -Root $root | Out-Null }
        catch { $missingRejected = $_.Exception.Message -like '*not found:*' }
        if (-not $missingRejected) { throw 'Missing metadata must fail closed before its read' }
        $script:ForecastTraceRows.ToArray()
    }
    finally {
        Remove-Item -Path Function:script:Get-Content -ErrorAction SilentlyContinue
        Remove-Variable -Name ForecastTraceRows, ForecastTraceMetaRoot, ForecastTraceCodeRoot -Scope Script -ErrorAction SilentlyContinue
    }
} $metaRoot $Season $ExpectedTeamRange $ExpectedWinProb $RepoRoot)
$json = ConvertTo-Json -InputObject $rows -Depth 8 -Compress
[System.IO.File]::WriteAllText($EventFile, $json)
