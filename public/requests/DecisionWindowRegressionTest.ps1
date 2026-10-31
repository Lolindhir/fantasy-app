$ErrorActionPreference = 'Stop'

& "$PSScriptRoot\NflTeamRegistryRegressionTest.ps1"
& "$PSScriptRoot\NflTeamKeyJoinRegressionTest.ps1"
& "$PSScriptRoot\NflTeamsReadModelRegressionTest.ps1"
& "$PSScriptRoot\LeagueWeekBoundaryRegressionTest.ps1"
& "$PSScriptRoot\GameFinalityRegressionTest.ps1"
& "$PSScriptRoot\NflByeWeekRegressionTest.ps1"
& "$PSScriptRoot\CanonicalScheduleRegressionTest.ps1"
# Preserve the productive Save-JsonFile semantic no-op and timestamp behavior
# after deleting the legacy DecisionWindowUtils.psm1 compare/derivation module.
Import-Module "$PSScriptRoot\utils\general\FileUtils.psm1" -ErrorAction Stop -Force
$decisionCompare = {
    param($oldDecisionWindows, $newDecisionWindows)
    if ($null -eq $oldDecisionWindows) { return $true }
    $oldJson = $oldDecisionWindows | ConvertTo-Json -Depth 10 -Compress
    $newJson = $newDecisionWindows | ConvertTo-Json -Depth 10 -Compress
    return $oldJson -ne $newJson
}
$tempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("decision-window-semantic-" + [Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
$tempFile = Join-Path $tempDir "DecisionWindows.json"
$tempTimestampFile = Join-Path $tempDir "Timestamps.json"
$global:TimestampFile = $tempTimestampFile
try {
    $model = [PSCustomObject][ordered]@{
        SchemaVersion = 3
        LeagueID = "league-fixture"
        DecisionWindows = @([PSCustomObject]@{ DecisionWindowID = "2030-09-08T17:00:00Z"; Games = @() })
    }
    Save-JsonFile -TargetFile $tempFile -Type "DecisionWindows" -Data $model -CompareScript $decisionCompare -UpdateTimestamp
    $first = Get-Content -Path $tempFile -Raw
    Set-Content -Path $tempTimestampFile -Value '{"DecisionWindows":"2000-01-01T00:00:00Z"}'
    $beforeTimestamp = Get-Content -Path $tempTimestampFile -Raw

    Save-JsonFile -TargetFile $tempFile -Type "DecisionWindows" -Data $model -CompareScript $decisionCompare -UpdateTimestamp
    if ((Get-Content -Path $tempFile -Raw) -cne $first) { throw "Unchanged DecisionWindows rewrote JSON." }
    if ((Get-Content -Path $tempTimestampFile -Raw) -cne $beforeTimestamp) {
        throw "Unchanged DecisionWindows updated its timestamp."
    }

    $changed = $model | ConvertTo-Json -Depth 10 | ConvertFrom-Json
    $changed.DecisionWindows[0].DecisionWindowID = "2030-09-08T17:20:00Z"
    Save-JsonFile -TargetFile $tempFile -Type "DecisionWindows" -Data $changed -CompareScript $decisionCompare -UpdateTimestamp
    $updatedWindow = (Get-Content -Path $tempFile -Raw | ConvertFrom-Json).DecisionWindows[0].DecisionWindowID
    if ([string]$updatedWindow -ne "2030-09-08T17:20:00Z") {
        throw "Changed DecisionWindows did not update JSON."
    }
    if ((Get-Content -Path $tempTimestampFile -Raw) -ceq $beforeTimestamp) {
        throw "Changed DecisionWindows did not update its timestamp."
    }
}
finally {
    Remove-Variable -Name TimestampFile -Scope Global -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $tempDir -Recurse -Force -ErrorAction SilentlyContinue
}
Write-Host 'Decision Window Python-derivation + semantic-save regression suite passed.' -ForegroundColor Green
# Sub-scripts may leave a stale native exit code behind (a tolerated failing helper call); every real failure throws
# above under $ErrorActionPreference = 'Stop', so the suite result must not depend on the last native $LASTEXITCODE.
$global:LASTEXITCODE = 0
