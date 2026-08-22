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
    Assert-DraftTypeConfigs -draftTypeConfigs $draftTypeConfigs

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
        [Parameter(Mandatory = $true)][int]$defaultRounds,
        [int]$draftInstance = 1
    )

    $configuredType = $draftTypeConfigs |
        Where-Object {
            [string]$_.DraftType -eq $draftType -and
            (Get-DraftInstanceFromConfig -draftTypeConfig $_) -eq $draftInstance
        } |
        Select-Object -First 1

    if ($null -ne $configuredType) { return $configuredType }

    return [PSCustomObject][ordered]@{
        DraftType     = $draftType
        DraftInstance = $draftInstance
        DraftNo       = $defaultDraftNo
        Rounds        = $defaultRounds
        OrderSource   = "Sleeper"
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
    param(
        [Parameter(Mandatory = $true)][array]$definitions,
        [Parameter(Mandatory = $true)][array]$draftTypeConfigs
    )

    foreach ($group in ($definitions | Group-Object -Property Season, DraftType)) {
        $groupItems = @($group.Group | Sort-Object DraftNo)
        $typeCount = $groupItems.Count

        for ($i = 0; $i -lt $groupItems.Count; $i++) {
            $draftInstance = $i + 1
            $draftType = [string]$groupItems[$i].DraftType
            $season = [string]$groupItems[$i].Season
            $draftCode = New-DraftCode -draftType $draftType -draftInstance $draftInstance
            $draftKey = New-DraftKey -season $season -draftType $draftType -draftInstance $draftInstance
            $fallbackRounds = [int](Get-DraftObjectProperty -object $groupItems[$i].DraftTypeConfig -propertyName "Rounds" -defaultValue 0)
            $resolvedConfig = Get-DraftHistoryConfiguredDraftTypeOrDefault `
                -draftType $draftType `
                -draftTypeConfigs $draftTypeConfigs `
                -defaultDraftNo ([int]$groupItems[$i].DraftNo) `
                -defaultRounds $fallbackRounds `
                -draftInstance $draftInstance

            $groupItems[$i] | Add-Member -NotePropertyName DraftInstance -NotePropertyValue $draftInstance -Force
            $groupItems[$i] | Add-Member -NotePropertyName DraftCode -NotePropertyValue $draftCode -Force
            $groupItems[$i] | Add-Member -NotePropertyName DraftKey -NotePropertyValue $draftKey -Force
            $groupItems[$i] | Add-Member -NotePropertyName DraftTypeConfig -NotePropertyValue $resolvedConfig -Force
            $groupItems[$i] | Add-Member -NotePropertyName TypeOccurrence -NotePropertyValue $draftInstance -Force
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

        $draftTypeConfig = Get-DraftHistoryConfiguredDraftTypeOrDefault `
            -draftType $draftType `
            -draftTypeConfigs $draftTypeConfigs `
            -defaultDraftNo $completedIndex `
            -defaultRounds ([int]$rounds)

        $definitions += [PSCustomObject][ordered]@{
            LeagueID        = $leagueID
            Season          = $draftSeason
            DraftType       = $draftType
            DraftInstance   = 1
            DraftCode       = $draftType
            DraftNo         = $completedIndex
            DraftKey        = New-DraftKey -season $draftSeason -draftType $draftType
            DraftTypeConfig = $draftTypeConfig
            SleeperDraft    = $draft
            TypeOccurrence  = 1
            TypeCount       = 1
        }
    }

    $definitions = Set-DraftHistoryTypeOccurrences -definitions $definitions -draftTypeConfigs $draftTypeConfigs

    return @($definitions | Sort-Object @{ Expression = { [int]$_.Season }; Ascending = $true }, DraftNo, DraftKey)
}

function Get-DraftHistoryOrderRosterIDsFromSleeperDraft {
    param([Parameter(Mandatory = $true)][object]$sleeperDraft)
    return Get-DraftOrderRosterIDsFromSleeperDraft -sleeperDraft $sleeperDraft
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

# ===========================================================================
# Draft History: Save
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
