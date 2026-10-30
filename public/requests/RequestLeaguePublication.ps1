$ErrorActionPreference = 'Stop'

& pwsh -NoLogo -NoProfile -File "$PSScriptRoot/RequestLeague.ps1"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# WeeklyRecaps.json is written by tools/weekly_recaps_app_publish.py (Issue #1199 section 4); only the index refresh stays here.
& pwsh -NoLogo -NoProfile -Command "Import-Module '$PSScriptRoot/utils/ConfigUtils.psm1' -Force; Import-Module '$PSScriptRoot/utils/league/PastSeasonsIndexUtils.psm1' -Force; Update-PastSeasonsIndex -Config (Get-Config) | Out-Null"
exit $LASTEXITCODE
