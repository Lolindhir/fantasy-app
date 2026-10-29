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
        "fantasypros-rankings",
        "fantasycalc-rankings",
        "ffc-adp-rankings",
        "fftoday-projections",
        "cbs-projections",
        "sleeper-trending",
        "fantasy-operations",
        "player-week-fantasy",
        "team-week-performance",
        "nfl-games",
        "nfl-player-availability"
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
        "^public/data/backup/" { return "Backups" }
        "^data-source/(market/expert-consensus/fantasypros|providers/fantasypros|market/_status/fantasypros\.json)" { return "FantasyPros rankings" }
        "^data-source/(market/market-value/fantasycalc|providers/fantasycalc|market/_status/fantasycalc\.json)" { return "FantasyCalc rankings" }
        "^data-source/(market/adp/fantasy-football-calculator|providers/fantasy-football-calculator|market/_status/fantasy-football-calculator\.json)" { return "Fantasy Football Calculator ADP" }
        "^data-source/(market/projection/fftoday|providers/fftoday|market/_status/fftoday\.json)" { return "FFToday projections" }
        "^data-source/(market/projection/cbs-sports|providers/cbs-sports|market/_status/cbs-sports\.json)" { return "CBS Sports projections" }
        "^data-source/(market/roster-activity/sleeper|providers/sleeper/trending|market/_status/sleeper\.json)" { return "Sleeper trending" }
        "^fantasy-management/generated/operations/" { return "Fantasy Operations inputs" }
        "^data-derived/player-week-fantasy/" { return "PlayerWeekFantasy derived" }
        "^data-derived/team-week-performance/" { return "TeamWeekPerformance derived" }
        "^data-derived/nfl-games/" { return "NFL Games derived" }
        "^data-derived/league-standings/" { return "Standings derived" }
        "/PlayerWeekFantasy\.json$" { return "PlayerWeekFantasy" }
        "/MatchupProjections\.json$" { return "MatchupProjections" }
        "/PastSeasonsIndex\.json$" { return "Past seasons index" }
        "/League\.json$" { return "League" }
        "/Players\.json$" { return "Players" }
        "/Transactions\.json$" { return "Transactions" }
        "/Drafts\.json$" { return "Drafts" }
        "/Standings\.json$" { return "Standings" }
        "/Teams\.json$" { return "Teams" }
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
