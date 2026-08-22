$ProjectName = "fantasy-league-custom-frontend"
$OutputDir = "dist/$ProjectName/browser"
$BaseHref = "/fantasy-app/"
$DiagnosticsDir = ".ai-workflow"
$BuildLog = "$DiagnosticsDir/build.log"
$ScriptResultFile = "$DiagnosticsDir/deploy-script-result.json"

New-Item -ItemType Directory -Path $DiagnosticsDir -Force | Out-Null

function Write-DeploySummary {
    param(
        [string]$Conclusion,
        [string]$Stage,
        [string]$Message
    )

    if ($env:GITHUB_STEP_SUMMARY) {
        "## Deploy script result" >> $env:GITHUB_STEP_SUMMARY
        "" >> $env:GITHUB_STEP_SUMMARY
        "- Conclusion: $Conclusion" >> $env:GITHUB_STEP_SUMMARY
        "- Stage: $Stage" >> $env:GITHUB_STEP_SUMMARY
        "- Message: $Message" >> $env:GITHUB_STEP_SUMMARY
        "- Result file: $ScriptResultFile" >> $env:GITHUB_STEP_SUMMARY
        "- Build log: $BuildLog" >> $env:GITHUB_STEP_SUMMARY
    }
}

Write-Host "Start Deployment..."

$BuildDate = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$Commit = if ($env:GITHUB_SHA) { $env:GITHUB_SHA } else { "deploy" }
$ShortCommit = if ($Commit.Length -ge 7) { $Commit.Substring(0, 7) } else { $Commit }
$BuildInfoJson = @"
{
  "version": "deploy",
  "commit": "$Commit",
  "shortCommit": "$ShortCommit",
  "buildDate": "$BuildDate",
  "source": "deploy_action.ps1"
}
"@
$BuildInfoTs = @"
export interface AppBuildInfo {
  version: string;
  commit: string;
  shortCommit: string;
  buildDate: string;
  source: string;
}

export const APP_BUILD_INFO: AppBuildInfo = {
  version: 'deploy',
  commit: '$Commit',
  shortCommit: '$ShortCommit',
  buildDate: '$BuildDate',
  source: 'deploy_action.ps1'
};
"@
Set-Content -Path "public/build-info.json" -Value $BuildInfoJson -Encoding utf8
Set-Content -Path "src/app/core/build-info.generated.ts" -Value $BuildInfoTs -Encoding utf8
Write-Host "Build info geschrieben: $BuildDate ($ShortCommit)"

# Temporary PR-only regression hook. Reverted after validation.
& ./public/requests/DraftIdentityRegressionTest.ps1
& ./public/requests/LeagueTransactionPipelineRegressionTest.ps1

# Angular Projekt bauen
Write-Host "Baue Angular Projekt..."
npx ng build --configuration production --base-href $BaseHref *> $BuildLog
$BuildExitCode = $LASTEXITCODE
Get-Content -Path $BuildLog | ForEach-Object { Write-Host $_ }

if ($BuildExitCode -ne 0) {
    $Result = [ordered]@{
        schemaVersion = 1
        type = "deploy-script-result"
        conclusion = "failure"
        stage = "angular-build"
        message = "Angular build failed."
        buildExitCode = $BuildExitCode
        commit = $Commit
        shortCommit = $ShortCommit
        buildLog = $BuildLog
        generatedAtUtc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    }
    $Result | ConvertTo-Json -Depth 10 | Set-Content -Path $ScriptResultFile -Encoding utf8
    Write-DeploySummary -Conclusion "failure" -Stage "angular-build" -Message "Angular build failed."
    exit 1
}

if (!(Test-Path "$OutputDir/index.html")) {
    $Result = [ordered]@{
        schemaVersion = 1
        type = "deploy-script-result"
        conclusion = "failure"
        stage = "verify-output"
        message = "Build fehlgeschlagen! index.html nicht gefunden."
        buildExitCode = $BuildExitCode
        commit = $Commit
        shortCommit = $ShortCommit
        buildLog = $BuildLog
        generatedAtUtc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    }
    $Result | ConvertTo-Json -Depth 10 | Set-Content -Path $ScriptResultFile -Encoding utf8
    Write-DeploySummary -Conclusion "failure" -Stage "verify-output" -Message "Build fehlgeschlagen! index.html nicht gefunden."
    Write-Error "Build fehlgeschlagen! index.html nicht gefunden."
    exit 1
}

# JSONs aus public/data kopieren
$SourceData = "public/data/*"
$DestData = "$OutputDir/data"
Write-Host "Kopiere JSONs von $SourceData nach $DestData"
if (!(Test-Path $DestData)) { New-Item -ItemType Directory -Path $DestData -Force | Out-Null }
Copy-Item -Path $SourceData -Destination $DestData -Recurse -Force

$Result = [ordered]@{
    schemaVersion = 1
    type = "deploy-script-result"
    conclusion = "success"
    stage = "completed"
    message = "Build and data copy completed successfully."
    buildExitCode = $BuildExitCode
    commit = $Commit
    shortCommit = $ShortCommit
    buildLog = $BuildLog
    generatedAtUtc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
}
$Result | ConvertTo-Json -Depth 10 | Set-Content -Path $ScriptResultFile -Encoding utf8
Write-DeploySummary -Conclusion "success" -Stage "completed" -Message "Build and data copy completed successfully."

Write-Host "Build abgeschlossen! Artefakte liegen in $OutputDir"
