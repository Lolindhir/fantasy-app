# ===========================================================================
# Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\..\ConfigUtils.psm1" -ErrorAction Stop -Force
}
catch {
    Write-Error "Fehler beim Laden der Module: $_"
    throw $_
}

# ===========================================================================
# Draft Display Status Utils
# ===========================================================================

function Get-DraftDisplayStatus {
    param(
        [Parameter(Mandatory = $true)][object]$draft,
        [string]$currentSeason = [string](Get-Config).LeagueYear
    )

    $statusValues = @(
        [string]$draft.Status,
        [string]$draft.SleeperStatus
    ) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | ForEach-Object { $_.Trim().ToLowerInvariant() }

    if ($statusValues | Where-Object { $_ -in @("complete", "completed", "finished") } | Select-Object -First 1) {
        return "Finished"
    }

    if ($statusValues | Where-Object { $_ -in @("drafting", "live", "active", "ongoing") } | Select-Object -First 1) {
        return "Ongoing"
    }

    $draftSeason = 0
    $currentSeasonNumber = 0
    [void][int]::TryParse([string]$draft.Season, [ref]$draftSeason)
    [void][int]::TryParse([string]$currentSeason, [ref]$currentSeasonNumber)

    if ($draftSeason -gt $currentSeasonNumber) {
        return "Future"
    }

    return "Upcoming"
}

function Set-DraftDisplayStatus {
    param(
        [Parameter(Mandatory = $true)][object]$draft,
        [string]$currentSeason = [string](Get-Config).LeagueYear
    )

    $displayStatus = Get-DraftDisplayStatus -draft $draft -currentSeason $currentSeason
    $ordered = [ordered]@{}
    $displayStatusAdded = $false

    foreach ($property in $draft.PSObject.Properties) {
        if ($property.Name -eq "DisplayStatus") { continue }

        $ordered[$property.Name] = $property.Value

        if ($property.Name -eq "Status") {
            $ordered["DisplayStatus"] = $displayStatus
            $displayStatusAdded = $true
        }
    }

    if (-not $displayStatusAdded) {
        $ordered["DisplayStatus"] = $displayStatus
    }

    return [PSCustomObject]$ordered
}

function Set-DraftDisplayStatuses {
    param(
        [AllowNull()][array]$drafts,
        [string]$currentSeason = [string](Get-Config).LeagueYear
    )

    if ($null -eq $drafts) { return @() }

    return @($drafts | ForEach-Object {
        Set-DraftDisplayStatus -draft $_ -currentSeason $currentSeason
    })
}
