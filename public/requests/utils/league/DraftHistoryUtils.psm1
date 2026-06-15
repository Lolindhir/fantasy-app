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

    if ($null -eq $draftsConfig) { throw "Metadata Drafts configuration missing." }

    $draftTypeConfigs = @(ConvertTo-DraftSafeArray -value $draftsConfig.Types | Sort-Object DraftNo)

    if ($draftTypeConfigs.Count -eq 0) { throw "No draft types configured in Metadata.json." }

    return $draftTypeConfigs
}

function Get-DraftsHistoricalFolder {
    return (Get-Config).DraftsArchiveDir
}

function Get-DraftsHistoricalFilePath {
    param([Parameter(Mandatory = $true)][string]$season)

    $config = Get-Config
    return "$($config.DraftsFileHistoricalPrefix)$season$($config.DraftsFileHistoricalSuffix)"
}

function Get-DraftHistoryJsonFileContent {
    param(
        [Parameter(Mandatory = $true)][string]$filePath,
        [string]$description = "data"
    )

    if (-not (Test-Path $filePath)) {
        Write-Warning "$description file not found at $filePath. Returning empty array."
        return @()
    }

    try {
        $raw = Get-Content $filePath -Raw
        if ([string]::IsNullOrWhiteSpace($raw)) { return @() }
        return $raw | ConvertFrom-Json
    }
    catch {
        Write-Warning "Could not read $description file at $filePath. $_"
        return @()
    }
}

function Get-DraftHistoryTransactionsLocal {
    $config = Get-Config
    return ConvertTo-DraftSafeArray -value (Get-DraftHistoryJsonFileContent -filePath $config.TransactionsFile -description "Transactions")
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
    param([Parameter(Mandatory = $true)][object]$sleeperDraft)

    $draftID = Get-DraftObjectProperty -object $sleeperDraft -propertyName "draft_id" -defaultValue $null
    if ([string]::IsNullOrWhiteSpace($draftID)) { return $sleeperDraft }

    try { return Get-SleeperDraft -draftID $draftID }
    catch {
        Write-Warning "Could not load Sleeper draft detail for '$draftID'. Falling back to draft list object. $_"
        return $sleeperDraft
    }
}

function New-DraftHistoryDraftKey {
    param(
        [Parameter(Mandatory = $true)][string]$season,
        [Parameter(Mandatory = $true)][int]$draftNo,
        [Parameter(Mandatory = $true)][string]$draftType
    )

    return "$($season)_D$($draftNo)_$($draftType)"
}

function Get-DraftHistoryDisplaySuffix {
    param(
        [Parameter(Mandatory = $true)][int]$typeOccurrence,
        [Parameter(Mandatory = $true)][int]$typeCount
    )

    if ($typeCount -le 1) { return "" }
    return " #$typeOccurrence"
}

function Get-DraftHistoryDisplayDraftKey {
    param(
        [Parameter(Mandatory = $true)][string]$season,
        [Parameter(Mandatory = $true)][string]$draftType,
        [Parameter(Mandatory = $true)][int]$typeOccurrence,
        [Parameter(Mandatory = $true)][int]$typeCount
    )

    return "$season $(Get-DraftTypeDisplayName -draftType $draftType)$(Get-DraftHistoryDisplaySuffix -typeOccurrence $typeOccurrence -typeCount $typeCount)"
}

function Get-DraftHistoryDisplayAbrDraftKey {
    param(
        [Parameter(Mandatory = $true)][string]$season,
        [Parameter(Mandatory = $true)][string]$draftType,
        [Parameter(Mandatory = $true)][int]$typeOccurrence,
        [Parameter(Mandatory = $true)][int]$typeCount
    )

    return "$season $(Get-DraftTypeAbbreviation -draftType $draftType)$(Get-DraftHistoryDisplaySuffix -typeOccurrence $typeOccurrence -typeCount $typeCount)"
}

function Get-DraftHistoryConfiguredRoundsFromSleeperDraft {
    param([Parameter(Mandatory = $true)][object]$sleeperDraft)

    $settings = Get-DraftObjectProperty -object $sleeperDraft -propertyName "settings" -defaultValue $null
    if ($null -ne $settings) {
        $roundsFromSettings = Get-DraftObjectProperty -object $settings -propertyName "rounds" -defaultValue $null
        if ($null -ne $roundsFromSettings -and -not [string]::IsNullOrWhiteSpace([string]$roundsFromSettings)) {
            return [int]$roundsFromSettings
        }
    }

    $roundsFromDraft = Get-DraftObjectProperty -object $sleeperDraft -propertyName "rounds" -defaultValue $null
    if ($null -ne $roundsFromDraft -and -not [string]::IsNullOrWhiteSpace([string]$roundsFromDraft)) {
        return [int]$roundsFromDraft
    }

    return $null
}

function Get-DraftHistoryMaxConfiguredRounds {
    param([Parameter(Mandatory = $true)][array]$draftTypeConfigs)

    $maxRounds = @(
        $draftTypeConfigs |
            Where-Object { $null -ne $_.Rounds -and [int]$_.Rounds -gt 0 } |
            ForEach-Object { [int]$_.Rounds } |
            Sort-Object -Descending |
            Select-Object -First 1
    )

    if ($maxRounds.Count -eq 0) { return 0 }
    return [int]$maxRounds[0]
}

function Get-DraftHistoryTextFromSleeperDraft {
    param([Parameter(Mandatory = $true)][object]$sleeperDraft)

    $textParts = @()

    foreach ($propertyName in @("type", "name", "status", "season")) {
        if (Test-DraftPropertyExists -object $sleeperDraft -propertyName $propertyName) {
            $textParts += [string]$sleeperDraft.$propertyName
        }
    }

    $metadata = Get-DraftObjectProperty -object $sleeperDraft -propertyName "metadata" -defaultValue $null
    if ($null -ne $metadata) {
        foreach ($prop in $metadata.PSObject.Properties) {
            $textParts += [string]$prop.Name
            $textParts += [string]$prop.Value
        }
    }

    return (($textParts | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }) -join " ").ToLowerInvariant()
}

function Test-DraftHistoryTruthySettingValue {
    param([AllowNull()]$value)

    if ($null -eq $value) { return $false }

    $text = ([string]$value).Trim().ToLowerInvariant()
    if ([string]::IsNullOrWhiteSpace($text)) { return $false }
    if ($text -in @("0", "false", "no", "off", "none", "null")) { return $false }

    return $true
}

function Get-DraftHistorySettingsClassification {
    param([Parameter(Mandatory = $true)][object]$sleeperDraft)

    $settings = Get-DraftObjectProperty -object $sleeperDraft -propertyName "settings" -defaultValue $null
    if ($null -eq $settings) { return $null }

    foreach ($prop in $settings.PSObject.Properties) {
        $key = ([string]$prop.Name).ToLowerInvariant()
        $value = ([string]$prop.Value).Trim().ToLowerInvariant()
        $isTruthy = Test-DraftHistoryTruthySettingValue -value $prop.Value

        if ($key.Contains("rookie") -and $isTruthy) { return "Rookie" }
        if ($key.Contains("veteran") -and $isTruthy) { return "Veteran" }

        $looksLikePlayerRestriction = (
            $key.Contains("player") -or
            $key.Contains("restriction") -or
            $key.Contains("pool")
        )

        if ($looksLikePlayerRestriction) {
            if ($value.Contains("rookie")) { return "Rookie" }
            if ($value.Contains("veteran")) { return "Veteran" }
            if ($value -eq "all" -or $value -eq "any" -or $value -eq "none") { return "Free_Agent" }
            if ($value.Contains("unrestricted") -or $value.Contains("no restriction")) { return "Free_Agent" }
            if ($value.Contains("free agent") -or $value.Contains("free_agent") -or $value.Contains("freeagent")) { return "Free_Agent" }
        }
    }

    return $null
}

function Get-DraftHistoryConfiguredDraftTypeOrDefault {
    param(
        [Parameter(Mandatory = $true)][string]$draftType,
        [Parameter(Mandatory = $true)][array]$draftTypeConfigs,
        [Parameter(Mandatory = $true)][int]$defaultDraftNo,
        [Parameter(Mandatory = $true)][int]$defaultRounds
    )

    $configuredType = $draftTypeConfigs | Where-Object { [string]$_.DraftType -eq $draftType } | Select-Object -First 1
    $rounds = if ($null -ne $configuredType -and [int]$configuredType.Rounds -gt 0) { [int]$configuredType.Rounds } else { $defaultRounds }

    return [PSCustomObject][ordered]@{
        DraftType   = $draftType
        DraftNo     = $defaultDraftNo
        Rounds      = $rounds
        OrderSource = "Sleeper"
    }
}

function Resolve-DraftHistoryTypeFromSleeperDraft {
    param(
        [Parameter(Mandatory = $true)][object]$sleeperDraft,
        [Parameter(Mandatory = $true)][array]$draftTypeConfigs,
        [AllowNull()]$fallbackDraftTypeConfig = $null
    )

    $settingsDraftType = Get-DraftHistorySettingsClassification -sleeperDraft $sleeperDraft
    if (-not [string]::IsNullOrWhiteSpace($settingsDraftType)) { return $settingsDraftType }

    $text = Get-DraftHistoryTextFromSleeperDraft -sleeperDraft $sleeperDraft

    if ($text.Contains("rookie")) { return "Rookie" }
    if ($text.Contains("veteran") -or $text.Contains(" vet ")) { return "Veteran" }
    if ($text.Contains("free agent") -or $text.Contains("free_agent") -or $text.Contains("freeagent")) { return "Free_Agent" }
    if ($text.Contains("startup") -or $text.Contains("start up")) { return "Free_Agent" }

    $sleeperRounds = Get-DraftHistoryConfiguredRoundsFromSleeperDraft -sleeperDraft $sleeperDraft
    $maxConfiguredRounds = Get-DraftHistoryMaxConfiguredRounds -draftTypeConfigs $draftTypeConfigs

    if ($null -ne $sleeperRounds -and $maxConfiguredRounds -gt 0 -and [int]$sleeperRounds -gt $maxConfiguredRounds) {
        return "Free_Agent"
    }

    if ($null -ne $fallbackDraftTypeConfig) { return [string]$fallbackDraftTypeConfig.DraftType }

    return "Veteran"
}

function Set-DraftHistoryTypeOccurrences {
    param([Parameter(Mandatory = $true)][array]$definitions)

    foreach ($group in ($definitions | Group-Object -Property Season, DraftType)) {
        $groupItems = @($group.Group | Sort-Object DraftNo, DraftKey)
        $typeCount = $groupItems.Count

        for ($i = 0; $i -lt $groupItems.Count; $i++) {
            $groupItems[$i] | Add-Member -NotePropertyName TypeOccurrence -NotePropertyValue ($i + 1) -Force
            $groupItems[$i] | Add-Member -NotePropertyName TypeCount -NotePropertyValue $typeCount -Force
        }
    }

    return $definitions
}

function Get-SleeperCompletedDraftDefinitionsForLeague {
    param(
        [Parameter(Mandatory = $true)][object]$league,
        [Parameter(Mandatory = $true)][array]$draftTypeConfigs
    )

    $leagueID = [string]$league.league_id
    $season = [string]$league.season
    $definitions = @()

    try { $sleeperDrafts = ConvertTo-DraftSafeArray -value (Get-SleeperDrafts -leagueID $leagueID) }
    catch {
        Write-Warning "Could not load Sleeper drafts for league '$leagueID' / season '$season'. $_"
        return @()
    }

    if ($sleeperDrafts.Count -eq 0) { return @() }

    $fallbackTypes = @($draftTypeConfigs | Sort-Object DraftNo)
    $seasonDrafts = @($sleeperDrafts | Sort-Object @{ Expression = "created"; Ascending = $true }, @{ Expression = "draft_id"; Ascending = $true })
    $completedIndex = 0

    for ($i = 0; $i -lt $seasonDrafts.Count; $i++) {
        $draft = Get-SleeperDraftDetailOrDefault -sleeperDraft $seasonDrafts[$i]
        if (-not (Test-SleeperDraftComplete -sleeperDraft $draft)) { continue }

        $completedIndex++
        $fallbackDraftTypeConfig = if (($completedIndex - 1) -lt $fallbackTypes.Count) { $fallbackTypes[$completedIndex - 1] } else { $null }
        $draftType = Resolve-DraftHistoryTypeFromSleeperDraft -sleeperDraft $draft -draftTypeConfigs $draftTypeConfigs -fallbackDraftTypeConfig $fallbackDraftTypeConfig
        if ([string]::IsNullOrWhiteSpace($draftType)) { $draftType = "Veteran" }

        $draftSeason = [string](Get-DraftObjectProperty -object $draft -propertyName "season" -defaultValue $season)
        if ([string]::IsNullOrWhiteSpace($draftSeason)) { $draftSeason = $season }

        $rounds = Get-DraftHistoryConfiguredRoundsFromSleeperDraft -sleeperDraft $draft
        if ($null -eq $rounds -or $rounds -le 0) { $rounds = 0 }

        $draftTypeConfig = Get-DraftHistoryConfiguredDraftTypeOrDefault -draftType $draftType -draftTypeConfigs $draftTypeConfigs -defaultDraftNo $completedIndex -defaultRounds ([int]$rounds)
        $draftKey = New-DraftHistoryDraftKey -season $draftSeason -draftNo $completedIndex -draftType $draftType

        $definitions += [PSCustomObject][ordered]@{
            LeagueID        = $leagueID
            Season          = $draftSeason
            DraftType       = $draftType
            DraftNo         = $completedIndex
            DraftKey        = $draftKey
            DraftTypeConfig = $draftTypeConfig
            SleeperDraft    = $draft
            TypeOccurrence  = 1
            TypeCount       = 1
        }
    }

    $definitions = Set-DraftHistoryTypeOccurrences -definitions $definitions

    return @($definitions | Sort-Object @{ Expression = { [int]$_.Season }; Ascending = $true }, DraftNo, DraftKey)
}

function Get-DraftHistoryOrderRosterIDsFromSleeperDraft {
    param([Parameter(Mandatory = $true)][object]$sleeperDraft)
    return Get-DraftOrderRosterIDsFromSleeperDraft -sleeperDraft $sleeperDraft
}

function Get-DraftHistorySleeperPicks {
    param([Parameter(Mandatory = $true)][object]$sleeperDraft)

    $draftID = Get-DraftObjectProperty -object $sleeperDraft -propertyName "draft_id" -defaultValue $null
    if ([string]::IsNullOrWhiteSpace($draftID)) { return @() }

    try { return ConvertTo-DraftSafeArray -value (Get-SleeperDraftPicks -draftID $draftID) }
    catch {
        Write-Warning "Could not load Sleeper draft picks for draft '$draftID'. Keeping generated picks without result enrichment. $_"
        return @()
    }
}

function Get-DraftHistoryRounds {
    param(
        [Parameter(Mandatory = $true)][object]$sleeperDraft,
        [Parameter(Mandatory = $true)][array]$sleeperPicks,
        [Parameter(Mandatory = $true)][int]$teamCount,
        [Parameter(Mandatory = $true)][int]$fallbackRounds
    )

    $roundCandidates = @()
    $roundsFromSettings = Get-DraftHistoryConfiguredRoundsFromSleeperDraft -sleeperDraft $sleeperDraft
    if ($null -ne $roundsFromSettings -and $roundsFromSettings -gt 0) { $roundCandidates += [int]$roundsFromSettings }

    $roundsFromSleeperPicks = @($sleeperPicks | Where-Object { $null -ne (Get-DraftObjectProperty -object $_ -propertyName "round" -defaultValue $null) } | ForEach-Object { [int](Get-DraftObjectProperty -object $_ -propertyName "round" -defaultValue 0) } | Sort-Object -Descending | Select-Object -First 1)
    if ($roundsFromSleeperPicks.Count -gt 0 -and $roundsFromSleeperPicks[0] -gt 0) { $roundCandidates += [int]$roundsFromSleeperPicks[0] }

    if ($teamCount -gt 0) {
        $maxPickNo = @($sleeperPicks | Where-Object { $null -ne (Get-DraftObjectProperty -object $_ -propertyName "pick_no" -defaultValue $null) } | ForEach-Object { [int](Get-DraftObjectProperty -object $_ -propertyName "pick_no" -defaultValue 0) } | Sort-Object -Descending | Select-Object -First 1)
        if ($maxPickNo.Count -gt 0 -and $maxPickNo[0] -gt 0) { $roundCandidates += [int][Math]::Ceiling($maxPickNo[0] / $teamCount) }
    }

    if ($fallbackRounds -gt 0) { $roundCandidates += $fallbackRounds }

    $rounds = @($roundCandidates | Where-Object { $_ -gt 0 } | Sort-Object -Descending | Select-Object -First 1)
    if ($rounds.Count -eq 0) { return 0 }
    return [int]$rounds[0]
}

function Get-DraftHistoryPlayerNameFromSleeperPick {
    param([AllowNull()]$sleeperPick)

    if ($null -eq $sleeperPick) { return $null }

    $metadata = Get-DraftObjectProperty -object $sleeperPick -propertyName "metadata" -defaultValue $null
    if ($null -eq $metadata) { return $null }

    $firstName = [string](Get-DraftObjectProperty -object $metadata -propertyName "first_name" -defaultValue "")
    $lastName = [string](Get-DraftObjectProperty -object $metadata -propertyName "last_name" -defaultValue "")
    $fullName = [string](Get-DraftObjectProperty -object $metadata -propertyName "full_name" -defaultValue "")
    $name = (($firstName, $lastName | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }) -join " ").Trim()

    if (-not [string]::IsNullOrWhiteSpace($name)) { return $name }
    if (-not [string]::IsNullOrWhiteSpace($fullName)) { return $fullName.Trim() }
    return $null
}

# ===========================================================================
# Draft History: Build and Enrichment
# ===========================================================================

function New-DraftHistoryPicks {
    param(
        [Parameter(Mandatory = $true)][string]$leagueID,
        [Parameter(Mandatory = $true)][string]$draftKey,
        [Parameter(Mandatory = $true)][string]$season,
        [Parameter(Mandatory = $true)][string]$draftType,
        [Parameter(Mandatory = $true)][int]$rounds,
        [Parameter(Mandatory = $true)][array]$teamIDs
    )

    return New-ProjectedDraftPicks -leagueID $leagueID -draftKey $draftKey -season $season -draftType $draftType -rounds $rounds -teamIDs $teamIDs -orderMode "Exact"
}

function Get-AppliedDraftPickResults {
    param(
        [Parameter(Mandatory = $true)][array]$picks,
        [Parameter(Mandatory = $true)][object]$sleeperDraft,
        [AllowNull()]$sleeperPicks = $null
    )

    $draftID = Get-DraftObjectProperty -object $sleeperDraft -propertyName "draft_id" -defaultValue $null
    if ([string]::IsNullOrWhiteSpace($draftID)) { return $picks }

    if ($null -eq $sleeperPicks) { $sleeperPicks = Get-DraftHistorySleeperPicks -sleeperDraft $sleeperDraft }
    else { $sleeperPicks = ConvertTo-DraftSafeArray -value $sleeperPicks }

    if ($sleeperPicks.Count -eq 0) { return $picks }

    $pickByOverall = @{}
    foreach ($pick in $picks) {
        if ($null -ne $pick.OverallPick -and -not [string]::IsNullOrWhiteSpace([string]$pick.OverallPick)) {
            $pickByOverall[[int]$pick.OverallPick] = $pick
        }
    }

    foreach ($sleeperPick in $sleeperPicks) {
        $pickNo = Get-DraftObjectProperty -object $sleeperPick -propertyName "pick_no" -defaultValue $null
        $playerID = Get-DraftObjectProperty -object $sleeperPick -propertyName "player_id" -defaultValue $null
        if ($null -eq $pickNo -or [string]::IsNullOrWhiteSpace([string]$pickNo)) { continue }

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
        [Parameter(Mandatory = $true)][object]$definition,
        [Parameter(Mandatory = $true)][array]$transactions
    )

    $leagueID = [string]$definition.LeagueID
    $season = [string]$definition.Season
    $draftType = [string]$definition.DraftType
    $draftNo = [int]$definition.DraftNo
    $draftKey = [string]$definition.DraftKey
    $typeOccurrence = [int]$definition.TypeOccurrence
    $typeCount = [int]$definition.TypeCount
    $draftTypeConfig = $definition.DraftTypeConfig
    $sleeperDraft = $definition.SleeperDraft
    $teamIDs = Get-DraftHistoryOrderRosterIDsFromSleeperDraft -sleeperDraft $sleeperDraft
    $sleeperPicks = Get-DraftHistorySleeperPicks -sleeperDraft $sleeperDraft

    if ($teamIDs.Count -eq 0) { throw "No Sleeper draft order found for completed draft '$draftKey'." }

    $rounds = Get-DraftHistoryRounds -sleeperDraft $sleeperDraft -sleeperPicks $sleeperPicks -teamCount $teamIDs.Count -fallbackRounds ([int]$draftTypeConfig.Rounds)
    if ($rounds -le 0) { throw "No valid round count found for completed draft '$draftKey'." }

    $picks = New-DraftHistoryPicks -leagueID $leagueID -draftKey $draftKey -season $season -draftType $draftType -rounds $rounds -teamIDs $teamIDs
    $picks = Get-AppliedDraftPickTrades -picks $picks -transactions $transactions -draftKey $draftKey
    $picks = Get-AppliedDraftPickResults -picks $picks -sleeperDraft $sleeperDraft -sleeperPicks $sleeperPicks

    $draftTypeSetting = [string](Get-DraftObjectProperty -object $sleeperDraft -propertyName "type" -defaultValue "linear")

    return [PSCustomObject][ordered]@{
        LeagueID           = $leagueID
        DraftKey           = $draftKey
        DisplayDraftKey    = Get-DraftHistoryDisplayDraftKey -season $season -draftType $draftType -typeOccurrence $typeOccurrence -typeCount $typeCount
        DisplayAbrDraftKey = Get-DraftHistoryDisplayAbrDraftKey -season $season -draftType $draftType -typeOccurrence $typeOccurrence -typeCount $typeCount
        Season             = $season
        DraftType          = $draftType
        DisplayDraftType   = Get-DraftTypeDisplayName -draftType $draftType
        DraftNo            = $draftNo
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
        [Parameter(Mandatory = $true)][string]$season,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$drafts,
        [switch]$Force
    )

    $folder = Get-DraftsHistoricalFolder
    $filePath = Get-DraftsHistoricalFilePath -season $season

    if (-not (Test-Path $folder)) { New-Item -ItemType Directory -Path $folder -Force | Out-Null }

    Write-Host "Saving historical drafts for $season to JSON..." -ForegroundColor Yellow

    if ($Force) {
        Save-JsonFile -TargetFile $filePath -Data $drafts
    }
    else {
        $compare = ${function:Compare-Drafts}
        Save-JsonFile -TargetFile $filePath -Data $drafts -CompareScript $compare
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

        $definitions = Get-SleeperCompletedDraftDefinitionsForLeague -league $league -draftTypeConfigs $draftTypeConfigs
        foreach ($definition in $definitions) {
            $draftSeason = [string]$definition.Season
            if (-not $draftsBySeason.ContainsKey($draftSeason)) { $draftsBySeason[$draftSeason] = @() }
            $draftsBySeason[$draftSeason] += New-DraftHistoryOutput -definition $definition -transactions $transactions
        }
    }

    foreach ($season in ($draftsBySeason.Keys | Sort-Object { [int]$_ })) {
        $seasonDrafts = @($draftsBySeason[$season] | Sort-Object DraftNo, DraftKey)
        Save-DraftsHistoricalSeason -season $season -drafts $seasonDrafts -Force:$ForceHistory
    }

    Write-Host "Completed draft history update finished." -ForegroundColor DarkCyan

    return @($draftsBySeason.Values | ForEach-Object { $_ })
}