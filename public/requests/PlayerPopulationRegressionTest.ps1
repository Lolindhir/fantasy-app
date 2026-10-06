$ErrorActionPreference = 'Stop'

# #347 H1b: injury mapping of RequestPlayers.ps1 (no Tank01, no live Sleeper call).

Import-Module "$PSScriptRoot\utils\player\PlayerPopulationUtils.psm1" -ErrorAction Stop -Force

function Assert-Equal {
    param($Expected, $Actual, [string]$Message)
    if ($Expected -ne $Actual) { throw "$Message (expected '$Expected', got '$Actual')" }
}

$healthy = ConvertTo-PlayerInjuryDetails -Injury ([PSCustomObject]@{ Status = $null; StartDate = $null; BodyPart = $null; Notes = $null; PracticeDescription = $null })
Assert-Equal $false $healthy.Injured 'no Sleeper injury status is not injured'
Assert-Equal '' $healthy.Details.Designation 'designation stays empty'
Assert-Equal '' $healthy.Details.Description 'description stays empty'
if ($null -ne $healthy.Details.ReturnDate) { throw 'ReturnDate must be an honest unknown (null)' }

$hurt = ConvertTo-PlayerInjuryDetails -Injury ([PSCustomObject]@{ Status = 'Questionable'; StartDate = '2026-10-01'; BodyPart = 'Knee'; Notes = $null; PracticeDescription = 'Limited' })
Assert-Equal $true $hurt.Injured 'a designation marks the player injured'
Assert-Equal 'Questionable' $hurt.Details.Designation 'designation from Sleeper status'
Assert-Equal '2026-10-01' $hurt.Details.Date 'date from injury start date'
Assert-Equal 'Knee' $hurt.Details.Description 'description falls back to body part when there are no notes'

$noted = ConvertTo-PlayerInjuryDetails -Injury ([PSCustomObject]@{ Status = 'Out'; StartDate = $null; BodyPart = 'Knee'; Notes = ' ACL '; PracticeDescription = $null })
Assert-Equal 'ACL' $noted.Details.Description 'notes win over body part and are trimmed'

Write-Host 'PlayerPopulationRegressionTest passed.' -ForegroundColor Green
