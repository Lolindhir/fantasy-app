# ===========================================================================
# Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\..\ConfigUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\general\FileUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\league\DraftUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\league\LeagueUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\invoke\SleeperUtils.psm1" -ErrorAction Stop -Force
}
catch {
    Write-Error "Fehler beim Laden der Module: $_"
    throw $_
}

# ===========================================================================
# Draft History: Config and Local Data
# ===========================================================================

function Get-DraftHistoryTypeConfigs {
    $config = Get-Config
    $draftsConfig = $config.DraftsConfig

    if ($null -eq $draftsConfig) {
        throw "Metadata Drafts configuration missing."
    }

    $draftTypeConfigs = @(
        ConvertTo-DraftSafeArray -value $draftsConfig.Types |
            Sort-Object DraftNo
    )

    if ($draftTypeConfigs.Count -eq 0) {
        throw "No draft types configured in Metadata.json."
    }

    return $draftTypeConfigs
}

function Get-DraftsHistoricalFolder {
    $config = Get-Config
    return $config.DraftsArchiveDir
}

function Get-DraftsHistoricalFilePath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$season
    )

    $config = Get-Config
    return "$($config.DraftsFileHistoricalPrefix)$season$($config.DraftsFileHistoricalSuffix)"
}

function Get-DraftHistoryJsonFileContent {
    param(
        [Parameter(Mandatory = $true)]
        [string]$filePath,

        [string]$description = "data"
    )

    if (-not (Test-Path $filePath)) {
        Write-Warning "$description file not found at $filePath. Returning empty array."
        return @()
    }

    try {
        $raw = Get-Content $filePath -Raw

        if ([string]::IsNullOrWhiteSpace($raw)) {
            return @()
        }

        return $raw | ConvertFrom-Json
    }
    catch {
        Write-Warning "Could not read $description file at $filePath. $_"
        return @()
    }
}

function Get-DraftHistoryTransactionsLocal {
    $config = Get-Config

    return ConvertTo-DraftSafeArray -value (
        Get-DraftHistoryJsonFileContent `
            -filePath $config.TransactionsFile `
            -description "Transactions"
    )
}

function Get-DraftHistoryTransactionsLocalHistoricalSeasons {
    $config = Get-Config
    $folder = $config.TransactionsArchiveDir
    $filePrefix = Split-Path $config.TransactionsFileHistoricalPrefix -Leaf
    $filter = "$filePrefix*$($config.TransactionsFileHistoricalSuffix)"

    if (-not (Test-Path $folder)) {
        Write-Warning "Transactions historical folder not found at $folder. Returning empty array."
        return @()
    }

    $transactions = @()

    Get-ChildItem $folder -Filter $filter | ForEach-Object {
        try {
            Write-Host "Loading historical transactions for draft history: $($_.Name)" -ForegroundColor DarkGray
            $raw = Get-Content $_.FullName -Raw

            if (-not [string]::IsNullOrWhiteSpace($raw)) {
                $transactions += ConvertTo-DraftSafeArray -value ($raw | ConvertFrom-Json)
            }
        }
        catch {
            Write-Warning "Could not read historical transactions file $($_.FullName): $_"
        }
    }

    return $transactions
}

function Get-DraftHistoryTransactionsAllLocal {
    $transactions = @()
    $transactions += ConvertTo-DraftSafeArray -value (Get-DraftHistoryTransactionsLocal)
    $transactions += ConvertTo-DraftSafeArray -value (Get-DraftHistoryTransactionsLocalHistoricalSeasons)

    return $transactions
}

# ===========================================================================
# Draft History: Sleeper Mapping
# ===========================================================================

function Get-SleeperDraftDetailOrDefault {
    param(
        [Parameter(Mandatory = $true)]
        [object]$sleeperDraft
    )

    $draftID = Get-DraftObjectProperty `
        -object $sleeperDraft `
        -propertyName "draft_id" `
        -defaultValue $null

    if ([string]::IsNullOrWhiteSpace($draftID)) {
        return $sleeperDraft
    }

    try {
        return Get-SleeperDraft -draftID $draftID
    }
    catch {
        Write-Warning "Could not load Sleeper draft detail for '$draftID'. Falling back to draft list object. $_"
        return $sleeperDraft
    }
}

function Resolve-DraftHistoryTypeFromSleeperDraft {
    param(
        [Parameter(Mandatory = $true)]
        [object]$sleeperDraft,

        [Parameter(Mandatory = $true)]
        [array]$draftTypeConfigs,

        [AllowNull()]
        $fallbackDraftTypeConfig = $null
    )

    $draftType = Resolve-DraftTypeFromSleeperDraft `
        -sleeperDraft $sleeperDraft `
        -draftTypeConfigs $draftTypeConfigs

    if (-not [string]::IsNullOrWhiteSpace($draftType)) {
        return $draftType
    }

    if ($null -ne $fallbackDraftTypeConfig) {
        return [string]$fallbackDraftTypeConfig.DraftType
    }

    return $null
}

function Get-SleeperCompletedDraftDefinitionsForLeague {
    param(
        [Parameter(Mandatory = $true)]
        [object]$league,

        [Parameter(Mandatory = $true)]
        [array]$draftTypeConfigs
    )

    $leagueID = [string]$league.league_id
    $season = [string]$league.season
    $definitions = @()

    try {
        $sleeperDrafts = ConvertTo-DraftSafeArray -value (Get-SleeperDrafts -leagueID $leagueID)
    }
    catch {
        Write-Warning "Could not load Sleeper drafts for league '$leagueID' / season '$season'. $_"
        return @()
    }

    if ($sleeperDrafts.Count -eq 0) {
        return @()
    }

    $fallbackTypes = @($draftTypeConfigs | Sort-Object DraftNo)
    $seasonDrafts = @(
        $sleeperDrafts |
            Sort-Object `
                @{ Expression = "created"; Ascending = $true },
                @{ Expression = "draft_id"; Ascending = $true }
    )

    for ($i = 0; $i -lt $seasonDrafts.Count; $i++) {
        $draft = Get-SleeperDraftDetailOrDefault -sleeperDraft $seasonDrafts[$i]

        if (-not (Test-SleeperDraftComplete -sleeperDraft $draft)) {
            continue
        }

        $fallbackDraftTypeConfig = if ($i -lt $fallbackTypes.Count) { $fallbackTypes[$i] } else { $null }
        $draftType = Resolve-DraftHistoryTypeFromSleeperDraft `
            -sleeperDraft $draft `
            -draftTypeConfigs $draftTypeConfigs `
            -fallbackDraftTypeConfig $fallbackDraftTypeConfig

        if ([string]::IsNullOrWhiteSpace($draftType)) {
            Write-Warning "Could not resolve completed draft type for Sleeper draft '$($draft.draft_id)'. Skipping."
            continue
        }

        $draftTypeConfig = $draftTypeConfigs |
            Where-Object { [string]$_.DraftType -eq $draftType } |
            Select-Object -First 1

        if ($null -eq $draftTypeConfig) {
            Write-Warning "No draft type config found for completed draft type '$draftType'. Skipping draft '$($draft.draft_id)'."
            continue
        }

        $draftSeason = [string](Get-DraftObjectProperty -object $draft -propertyName "season" -defaultValue $season)

        if ([string]::IsNullOrWhiteSpace($draftSeason)) {
            $draftSeason = $season
        }

        $definitions += [PSCustomObject][ordered]@{
            LeagueID        = $leagueID
            Season          = $draftSeason
            DraftType       = $draftType
            DraftNo         = [int]$draftTypeConfig.DraftNo
            DraftKey        = New-DraftKey -season $draftSeason -draftType $draftType
            DraftTypeConfig = $draftTypeConfig
            SleeperDraft    = $draft
        }
    }

    return @(
        $definitions |
            Sort-Object `
                @{ Expression = { [int]$_.Season }; Ascending = $true },
                DraftNo
    )
}

function Get-DraftHistoryOrderRosterIDsFromSleeperDraft {
    param(
        [Parameter(Mandatory = $true)]
        [object]$sleeperDraft
    )

    return Get-DraftOrderRosterIDsFromSleeperDraft -sleeperDraft $sleeperDraft
}

function Get-DraftHistoryPlayerNameFromSleeperPick {
    param(
        [AllowNull()]
        $sleeperPick
    )

    if ($null -eq $sleeperPick) {
        return $null
    }

    $metadata = Get-DraftObjectProperty -object $sleeperPick -propertyName "metadata" -defaultValue $null

    if ($null -eq $metadata) {
        return $null
    }

    $firstName = [string](Get-DraftObjectProperty -object $metadata -propertyName "first_name" -defaultValue "")
    $lastName = [string](Get-DraftObjectProperty -object $metadata -propertyName "last_name" -defaultValue "")
    $fullName = [string](Get-DraftObjectProperty -object $metadata -propertyName "full_name" -defaultValue "")
    $name = (($firstName, $lastName | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }) -join " ").Trim()

    if (-not [string]::IsNullOrWhiteSpace($name)) {
        return $name
    }

    if (-not [string]::IsNullOrWhiteSpace($fullName)) {
        return $fullName.Trim()
    }

    return $null
}

# ===========================================================================
# Draft History: Build and Enrichment
# ===========================================================================

function New-DraftHistoryPicks {
    param(
        [Parameter(Mandatory = $true)]
        [string]$leagueID,

        [Parameter(Mandatory = $true)]
        [string]$draftKey,

        [Parameter(Mandatory = $true)]
        [string]$season,

        [Parameter(Mandatory = $true)]
        [string]$draftType,

        [Parameter(Mandatory = $true)]
        [int]$rounds,

        [Parameter(Mandatory = $true)]
        [array]$teamIDs
    )

    return New-ProjectedDraftPicks `
        -leagueID $leagueID `
        -draftKey $draftKey `
        -season $season `
        -draftType $draftType `
        -rounds $rounds `
        -teamIDs $teamIDs `
        -orderMode "Exact"
}

function Get-AppliedDraftPickResults {
    param(
        [Parameter(Mandatory = $true)]
        [array]$picks,

        [Parameter(Mandatory = $true)]
        [object]$sleeperDraft
    )

    $draftID = Get-DraftObjectProperty `
        -object $sleeperDraft `
        -propertyName "draft_id" `
        -defaultValue $null

    if ([string]::IsNullOrWhiteSpace($draftID)) {
        return $picks
    }

    try {
        $sleeperPicks = ConvertTo-DraftSafeArray -value (Get-SleeperDraftPicks -draftID $draftID)
    }
    catch {
        Write-Warning "Could not load Sleeper draft picks for draft '$draftID'. Keeping generated picks without result enrichment. $_"
        return $picks
    }

    if ($sleeperPicks.Count -eq 0) {
        return $picks
    }

    $pickByOverall = @{}

    foreach ($pick in $picks) {
        if ($null -ne $pick.OverallPick -and -not [string]::IsNullOrWhiteSpace([string]$pick.OverallPick)) {
            $pickByOverall[[int]$pick.OverallPick] = $pick
        }
    }

    foreach ($sleeperPick in $sleeperPicks) {
        $pickNo = Get-DraftObjectProperty -object $sleeperPick -propertyName "pick_no" -defaultValue $null
        $playerID = Get-DraftObjectProperty -object $sleeperPick -propertyName "player_id" -defaultValue $null

        if ($null -eq $pickNo -or [string]::IsNullOrWhiteSpace([string]$pickNo)) {
            continue
        }

        $overallPick = [int]$pickNo

        if (-not $pickByOverall.ContainsKey($overallPick)) {
            Write-Warning "Could not map Sleeper pick_no '$overallPick' from draft '$draftID' to generated draft picks."
            continue
        }

        $targetPick = $pickByOverall[$overallPick]
        $targetPick.SleeperPickNo = $overallPick
        $targetPick.SleeperPickedBy = [string](Get-DraftObjectProperty -object $sleeperPick -propertyName "picked_by" -defaultValue $null)

        if ($null -ne $playerID -and -not [string]::IsNullOrWhiteSpace([string]$playerID)) {
            $targetPick.PlayerID = [string]$playerID
            $targetPick.PlayerName = Get-DraftHistoryPlayerNameFromSleeperPick -sleeperPick $sleeperPick
            $targetPick.Status = "Picked"
        }
    }

    return $picks
}

function New-DraftHistoryOutput {
    param(
        [Parameter(Mandatory = $true)]
        [object]$definition,

        [Parameter(Mandatory = $true)]
        [array]$transactions
    )

    $leagueID = [string]$definition.LeagueID
    $season = [string]$definition.Season
    $draftType = [string]$definition.DraftType
    $draftKey = [string]$definition.DraftKey
    $draftTypeConfig = $definition.DraftTypeConfig
    $sleeperDraft = $definition.SleeperDraft
    $rounds = [int]$draftTypeConfig.Rounds
    $teamIDs = Get-DraftHistoryOrderRosterIDsFromSleeperDraft -sleeperDraft $sleeperDraft

    if ($teamIDs.Count -eq 0) {
        throw "No Sleeper draft order found for completed draft '$draftKey'."
    }

    $picks = New-DraftHistoryPicks `
        -leagueID $leagueID `
        -draftKey $draftKey `
        -season $season `
        -draftType $draftType `
        -rounds $rounds `
        -teamIDs $teamIDs

    $picks = Get-AppliedDraftPickTrades `
        -picks $picks `
        -transactions $transactions `
        -draftKey $draftKey

    $picks = Get-AppliedDraftPickResults `
        -picks $picks `
        -sleeperDraft $sleeperDraft

    $draftTypeSetting = [string](Get-DraftObjectProperty -object $sleeperDraft -propertyName "type" -defaultValue "linear")

    return [PSCustomObject][ordered]@{
        LeagueID           = $leagueID
        DraftKey           = $draftKey
        DisplayDraftKey    = Get-DisplayDraftKey -season $season -draftType $draftType
        DisplayAbrDraftKey = Get-DisplayAbrDraftKey -season $season -draftType $draftType

        Season             = $season
        DraftType          = $draftType
        DisplayDraftType   = Get-DraftTypeDisplayName -draftType $draftType
        DraftNo            = [int]$definition.DraftNo

        DraftSource        = "Sleeper"
        SleeperDraftID     = [string]$sleeperDraft.draft_id
        SleeperStatus      = [string]$sleeperDraft.status
        Status             = Get-DraftStatus -sleeperDraft $sleeperDraft

        PickSource         = "GeneratedFromSleeperOrderTradesAndResults"
        OrderSource        = "Sleeper"
        OrderMode          = "Exact"

        Settings           = [PSCustomObject][ordered]@{
            Rounds = $rounds
            Teams  = [int]$teamIDs.Count
            Type   = $draftTypeSetting
        }

        Picks              = @($picks)
    }
}

# ===========================================================================
# Draft History: Save and Update
# ===========================================================================

function Save-DraftsHistoricalSeason {
    param(
        [Parameter(Mandatory = $true)]
        [string]$season,

        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [array]$drafts,

        [switch]$Force
    )

    $folder = Get-DraftsHistoricalFolder
    $filePath = Get-DraftsHistoricalFilePath -season $season

    if (-not (Test-Path $folder)) {
        New-Item -ItemType Directory -Path $folder -Force | Out-Null
    }

    Write-Host "Saving historical drafts for $season to JSON..." -ForegroundColor Yellow

    if ($Force) {
        Save-JsonFile `
            -TargetFile $filePath `
            -Data $drafts
    }
    else {
        $compare = ${function:Compare-Drafts}

        Save-JsonFile `
            -TargetFile $filePath `
            -Data $drafts `
            -CompareScript $compare
    }

    Write-Host "Saved historical drafts for $season." -ForegroundColor DarkCyan
}

function Update-DraftsHistoricalSeasons {
    param(
        [string]$leagueID = (Get-Config).LeagueID,
        [switch]$ForceHistory
    )

    Write-Host "Update completed draft history..." -ForegroundColor Yellow

    $draftTypeConfigs = Get-DraftHistoryTypeConfigs
    $transactions = Get-DraftHistoryTransactionsAllLocal
    $leagues = Get-LeaguesRecursive -leagueID $leagueID
    $draftsBySeason = @{}

    foreach ($league in $leagues) {
        $season = [string]$league.season

        if ([string]::IsNullOrWhiteSpace($season)) {
            Write-Warning "League '$($league.league_id)' has no season. Skipping completed draft history."
            continue
        }

        $definitions = Get-SleeperCompletedDraftDefinitionsForLeague `
            -league $league `
            -draftTypeConfigs $draftTypeConfigs

        foreach ($definition in $definitions) {
            $draftSeason = [string]$definition.Season

            if (-not $draftsBySeason.ContainsKey($draftSeason)) {
                $draftsBySeason[$draftSeason] = @()
            }

            $draftsBySeason[$draftSeason] += New-DraftHistoryOutput `
                -definition $definition `
                -transactions $transactions
        }
    }

    foreach ($season in ($draftsBySeason.Keys | Sort-Object { [int]$_ })) {
        $seasonDrafts = @(
            $draftsBySeason[$season] |
                Sort-Object DraftNo
        )

        Save-DraftsHistoricalSeason `
            -season $season `
            -drafts $seasonDrafts `
            -Force:$ForceHistory
    }

    Write-Host "Completed draft history update finished." -ForegroundColor DarkCyan

    return @(
        $draftsBySeason.Values |
            ForEach-Object { $_ }
    )
}