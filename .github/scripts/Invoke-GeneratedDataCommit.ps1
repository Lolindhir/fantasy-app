[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet(
        "league",
        "drafts",
        "players",
        "transactions",
        "games",
        "standings",
        "teams",
        "past-seasons-index",
        "backup-cleanup",
        "fantasypros-rankings"
    )]
    [string]$Scope
)

$ErrorActionPreference = "Stop"

function Get-GeneratedDataLabel {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $normalizedPath = $Path -replace "\\", "/"

    switch -Regex ($normalizedPath) {
        "^public/data/past_seasons/Drafts/" { return "Draft history" }
        "^public/data/past_seasons/Transactions/" { return "Transaction history" }
        "^public/data/chat/players-relevant/" { return "Player chat export" }
        "^public/data/backup/" { return "Backups" }
        "^fantasy-management/sources/external-rankings/fantasypros/" { return "FantasyPros rankings" }
        "/PastSeasonsIndex\.json$" { return "Past seasons index" }
        "/League\.json$" { return "League" }
        "/Players_Relevant\.json$" { return "Relevant players" }
        "/Players\.json$" { return "Players" }
        "/Transactions\.json$" { return "Transactions" }
        "/Drafts\.json$" { return "Drafts" }
        "/Standings\.json$" { return "Standings" }
        "/Teams\.json$" { return "Teams" }
        "/Games\.json$" { return "Games" }
        "/Schedule\.json$" { return "Schedule" }
        "/Timestamps?\.json$" { return "Timestamps" }
        default {
            $fallback = [System.IO.Path]::GetFileNameWithoutExtension($normalizedPath)
            if ([string]::IsNullOrWhiteSpace($fallback)) {
                return "Generated data"
            }

            return (($fallback -replace "[_-]+", " ").Trim())
        }
    }
}

function Get-BerlinTimestamp {
    $utcNow = [DateTimeOffset]::UtcNow

    try {
        $timeZone = [TimeZoneInfo]::FindSystemTimeZoneById("Europe/Berlin")
        $localTime = [TimeZoneInfo]::ConvertTime($utcNow, $timeZone)
        $zoneLabel = if ($timeZone.IsDaylightSavingTime($localTime)) { "CEST" } else { "CET" }
        return "$($localTime.ToString('yyyy-MM-dd HH:mm')) $zoneLabel"
    }
    catch {
        return "$($utcNow.ToString('yyyy-MM-dd HH:mm')) UTC"
    }
}

git diff --cached --quiet
$diffExitCode = $LASTEXITCODE

if ($diffExitCode -eq 0) {
    Write-Host "No staged data changes detected. Commit skipped." -ForegroundColor Cyan
    exit 0
}

if ($diffExitCode -ne 1) {
    throw "Could not inspect staged changes. git diff exited with code $diffExitCode."
}

$changedFiles = @(git diff --cached --name-only)
if ($LASTEXITCODE -ne 0) {
    throw "Could not read staged file names."
}

$labels = [System.Collections.Generic.List[string]]::new()
foreach ($changedFile in $changedFiles) {
    $label = Get-GeneratedDataLabel -Path $changedFile
    if (-not $labels.Contains($label)) {
        $labels.Add($label)
    }
}

if ($labels.Count -eq 0) {
    $labels.Add("Generated data")
}

$maximumLabels = 5
if ($labels.Count -le $maximumLabels) {
    $summary = $labels -join ", "
}
else {
    $visibleLabels = @($labels | Select-Object -First $maximumLabels)
    $remainingCount = $labels.Count - $maximumLabels
    $summary = "$($visibleLabels -join ', ') +$remainingCount more"
}

$timestamp = Get-BerlinTimestamp
$commitMessage = "data($($Scope.ToLowerInvariant())): $summary • $timestamp"

Write-Host "Creating commit: $commitMessage" -ForegroundColor Green
git commit -m $commitMessage

if ($LASTEXITCODE -ne 0) {
    throw "git commit failed with exit code $LASTEXITCODE."
}
