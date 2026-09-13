$ErrorActionPreference = 'Stop'

& pwsh -NoLogo -NoProfile -File "$PSScriptRoot/RequestLeague.ps1"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& pwsh -NoLogo -NoProfile -File "$PSScriptRoot/RequestWeeklyRecaps.ps1"
exit $LASTEXITCODE
