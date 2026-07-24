# ===========================================================================
# Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\..\ConfigUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\general\FileUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\general\ArrayUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\DraftUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\DraftHistoryUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\LeagueUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\TransactionUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\invoke\SleeperUtils.psm1" -ErrorAction Stop -Force
}
catch {
    Write-Error "Fehler beim Laden der Module: $_"
    throw $_
}

# ===========================================================================
# Generic helpers
# ===========================================================================

function Get-TransactionDraftPickJsonFileContent {
    param(
        [Parameter(Mandatory = $true)][string]$filePath,
        [string]$description = "data"
    )

    if (-not (Test-Path $filePath)) {
        Write-Host "$description file not found at $filePath." -ForegroundColor DarkGray
        return @()
    }

    try {
        $raw = Get-Content $filePath -Raw
        if ([string]::IsNullOrWhiteSpace($raw)) { return @() }
        return ConvertTo-SafeArray -value ($raw | ConvertFrom-Json)
    }
    catch {
        Write-Warning "Could not read $description file at $filePath. $_"
        return @()
    }
}

function Set-TransactionDraftPickPropertyValue {
    param(
        [Parameter(Mandatory = $true)][object]$target,
        [Parameter(Mandatory = $true)][string]$propertyName,
        [AllowNull()]$value,
        [Parameter(Mandatory = $true)][ref]$changed
    )

    $propertyExists = $target.PSObject.Properties.Name -contains $propertyName
    $currentValue = if ($propertyExists) { $target.PSObject.Properties[$propertyName].Value } else { $null }
    $currentComparable = if ($null -eq $currentValue) { $null } else { $currentValue | ConvertTo-Json -Depth 10 -Compress }
    $newComparable = if ($null -eq $value) { $null } else { $value | ConvertTo-Json -Depth 10 -Compress }

    if (-not $propertyExists -or $currentComparable -ne $newComparable) {
        $target | Add-Member -NotePropertyName $propertyName -NotePropertyValue $value -Force
        $changed.Value = $true
    }
}

function Get-TransactionDraftPickTransactionFiles {
    $config = Get-Config
    $files = @()

    if (Test-Path $config.TransactionsFile) {
        $files += [PSCustomObject][ordered]@{
            Path      = $config.TransactionsFile
            IsCurrent = $true
            Season    = [string]$config.LeagueYear
        }
    }

    if (Test-Path $config.TransactionsArchiveDir) {
        $prefix = Split-Path $config.TransactionsFileHistoricalPrefix -Leaf
        $filter = "$prefix*$($config.TransactionsFileHistoricalSuffix)"

        foreach ($file in (Get-ChildItem $config.TransactionsArchiveDir -Filter $filter | Sort-Object Name)) {
            $season = [System.IO.Path]::GetFileNameWithoutExtension($file.Name).Substring($prefix.Length)
            $files += [PSCustomObject][ordered]@{
                Path      = $file.FullName
                IsCurrent = $false
                Season    = [string]$season
            }
        }
    }

    return $files
}

function Get-TransactionDraftPickDraftsFromLocalFiles {
    $config = Get-Config
    $drafts = @()

    $drafts += Get-TransactionDraftPickJsonFileContent -filePath $config.DraftsFile -description "Current drafts"

    if (Test-Path $config.DraftsArchiveDir) {
        $prefix = Split-Path $config.DraftsFileHistoricalPrefix -Leaf
        $filter = "$prefix*$($config.DraftsFileHistoricalSuffix)"

        foreach ($file in (Get-ChildItem $config.DraftsArchiveDir -Filter $filter | Sort-Object Name)) {
            $drafts += Get-TransactionDraftPickJsonFileContent -filePath $file.FullName -description "Historical drafts"
        }
    }

    return @($drafts)
}

function Save-TransactionDraftPickTransactions {
    param(
        [Parameter(Mandatory = $true)][string]$filePath,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$transactions,
        [Parameter(Mandatory = $true)][bool]$isCurrent
    )

    $compare = ${function:Compare-Transactions}

    if ($isCurrent) {
        Save-JsonFile `
            -Type "Transactions" `
            -Data $transactions `
            -CompareScript $compare `
            -CreateBackup `
            -UpdateTimestamp
        return
    }

    Save-JsonFile `
        -TargetFile $filePath `
        -Data $transactions `
        -CompareScript $compare
}

# ===========================================================================
# Sleeper draft context resolution
# ===========================================================================

function Get-TransactionDraftPickSleeperDraftContexts {
    param(
        [Parameter(Mandatory = $true)][string]$leagueID
    )

    $draftTypeConfigs = Get-DraftHistoryTypeConfigs
    $fallbackTypes = @($draftTypeConfigs | Sort-Object DraftNo)
    $contexts = @()

    try {
        $sleeperDrafts = ConvertTo-DraftSafeArray -value (Get-SleeperDrafts -leagueID $leagueID)
    }
    catch {
        Write-Warning "Could not load Sleeper drafts for transaction pick resolution in league '$leagueID'. $_"
        return @()
    }

    $sleeperDrafts = @($sleeperDrafts | Sort-Object @{ Expression = "created"; Ascending = $true }, @{ Expression = "draft_id"; Ascending = $true })

    for ($i = 0; $i -lt $sleeperDrafts.Count; $i++) {
        $draft = Get-SleeperDraftDetailOrDefault -sleeperDraft $sleeperDrafts[$i]
        $fallbackDraftTypeConfig = if ($i -lt $fallbackTypes.Count) { $fallbackTypes[$i] } else { $null }
        $draftType = Resolve-DraftHistoryTypeFromSleeperDraft `
            -sleeperDraft $draft `
            -draftTypeConfigs $draftTypeConfigs `
            -fallbackDraftTypeConfig $fallbackDraftTypeConfig

        if ([string]::IsNullOrWhiteSpace($draftType)) {
            Write-Warning "Could not classify Sleeper draft '$($draft.draft_id)' for transaction pick resolution."
            continue
        }

        $season = [string](Get-DraftObjectProperty -object $draft -propertyName "season" -defaultValue "")
        if ([string]::IsNullOrWhiteSpace($season)) { continue }

        $draftID = [string](Get-DraftObjectProperty -object $draft -propertyName "draft_id" -defaultValue "")
        $tradedPicks = @()

        if (-not [string]::IsNullOrWhiteSpace($draftID)) {
            try {
                $tradedPicks = ConvertTo-DraftSafeArray -value (Get-SleeperDraftTradedPicks -draftID $draftID)
            }
            catch {
                Write-Warning "Could not load traded picks for Sleeper draft '$draftID'. $_"
            }
        }

        $contexts += [PSCustomObject][ordered]@{
            Season          = $season
            DraftType       = [string]$draftType
            DraftKey        = New-DraftKey -season $season -draftType ([string]$draftType)
            SleeperDraftID  = $draftID
            TradedPicks     = @($tradedPicks)
        }
    }

    return $contexts
}

function Test-TransactionDraftPickMovementMatch {
    param(
        [Parameter(Mandatory = $true)][object]$transactionPick,
        [Parameter(Mandatory = $true)][object]$sleeperTradedPick,
        [switch]$RequireMovement
    )

    $season = [string](Get-DraftObjectProperty -object $sleeperTradedPick -propertyName "season" -defaultValue "")
    $round = Get-DraftObjectProperty -object $sleeperTradedPick -propertyName "round" -defaultValue $null
    $originalOwner = Get-DraftObjectProperty -object $sleeperTradedPick -propertyName "roster_id" -defaultValue $null

    if ($season -ne [string]$transactionPick.Season) { return $false }
    if ($null -eq $round -or [int]$round -ne [int]$transactionPick.Round) { return $false }
    if ($null -eq $originalOwner -or [int]$originalOwner -ne [int]$transactionPick.OriginalOwnerRosterID) { return $false }

    if (-not $RequireMovement) { return $true }

    $previousOwner = Get-DraftObjectProperty -object $sleeperTradedPick -propertyName "previous_owner_id" -defaultValue $null
    $newOwner = Get-DraftObjectProperty -object $sleeperTradedPick -propertyName "owner_id" -defaultValue $null

    return (
        $null -ne $previousOwner -and
        $null -ne $newOwner -and
        [int]$previousOwner -eq [int]$transactionPick.PreviousOwnerRosterID -and
        [int]$newOwner -eq [int]$transactionPick.NewOwnerRosterID
    )
}

function Get-TransactionDraftPickContextMatch {
    param(
        [Parameter(Mandatory = $true)][object]$transactionPick,
        [Parameter(Mandatory = $true)][array]$contexts
    )

    $exactContexts = @()
    $identityContexts = @()

    foreach ($context in $contexts) {
        $hasExactMatch = $false
        $hasIdentityMatch = $false

        foreach ($tradedPick in (ConvertTo-DraftSafeArray -value $context.TradedPicks)) {
            if (Test-TransactionDraftPickMovementMatch -transactionPick $transactionPick -sleeperTradedPick $tradedPick -RequireMovement) {
                $hasExactMatch = $true
                break
            }

            if (Test-TransactionDraftPickMovementMatch -transactionPick $transactionPick -sleeperTradedPick $tradedPick) {
                $hasIdentityMatch = $true
            }
        }

        if ($hasExactMatch) { $exactContexts += $context }
        elseif ($hasIdentityMatch) { $identityContexts += $context }
    }

    $exactContexts = @($exactContexts | Sort-Object SleeperDraftID -Unique)
    if ($exactContexts.Count -eq 1) { return $exactContexts[0] }

    $identityContexts = @($identityContexts | Sort-Object SleeperDraftID -Unique)
    if ($identityContexts.Count -eq 1) { return $identityContexts[0] }

    $candidateContexts = if ($exactContexts.Count -gt 0) { $exactContexts } else { $identityContexts }
    $draftTypes = @($candidateContexts | ForEach-Object { [string]$_.DraftType } | Sort-Object -Unique)

    if ($draftTypes.Count -eq 1) {
        $draftType = $draftTypes[0]
        return [PSCustomObject][ordered]@{
            Season          = [string]$transactionPick.Season
            DraftType       = $draftType
            DraftKey        = New-DraftKey -season ([string]$transactionPick.Season) -draftType $draftType
            SleeperDraftID  = $null
            TradedPicks     = @()
        }
    }

    return $null
}

function Resolve-TransactionDraftPickTypesFromContexts {
    param(
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$transactions,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$contexts
    )

    $changed = $false

    foreach ($transaction in $transactions) {
        foreach ($transactionPick in (ConvertTo-SafeArray -value $transaction.DraftPicks)) {
            if ([string]$transactionPick.DraftSource -ne "Sleeper") { continue }

            $context = Get-TransactionDraftPickContextMatch -transactionPick $transactionPick -contexts $contexts
            if ($null -eq $context) {
                Write-Warning "Could not uniquely resolve draft type for transaction '$($transaction.TransactionID)', season '$($transactionPick.Season)', round '$($transactionPick.Round)', original owner '$($transactionPick.OriginalOwnerRosterID)'."
                continue
            }

            Set-TransactionDraftPickPropertyValue -target $transactionPick -propertyName "DraftType" -value ([string]$context.DraftType) -changed ([ref]$changed)
            Set-TransactionDraftPickPropertyValue -target $transactionPick -propertyName "DraftKey" -value ([string]$context.DraftKey) -changed ([ref]$changed)
            Set-TransactionDraftPickPropertyValue -target $transactionPick -propertyName "SleeperDraftID" -value $context.SleeperDraftID -changed ([ref]$changed)
        }
    }

    return [PSCustomObject][ordered]@{
        Transactions = @($transactions)
        Changed      = $changed
    }
}

function Update-CurrentTransactionDraftPickTypesFromSleeper {
    param(
        [AllowNull()]$transactions = $null,
        [string]$leagueID = (Get-Config).LeagueID
    )

    $config = Get-Config
    if ($null -eq $transactions) {
        $transactions = Get-TransactionDraftPickJsonFileContent -filePath $config.TransactionsFile -description "Current transactions"
    }
    else {
        $transactions = ConvertTo-SafeArray -value $transactions
    }

    $contexts = Get-TransactionDraftPickSleeperDraftContexts -leagueID $leagueID
    $result = Resolve-TransactionDraftPickTypesFromContexts -transactions $transactions -contexts $contexts

    if ($result.Changed) {
        Save-TransactionDraftPickTransactions -filePath $config.TransactionsFile -transactions @($result.Transactions) -isCurrent $true
    }

    return @($result.Transactions)
}

function Update-AllTransactionDraftPickTypesFromSleeper {
    param(
        [string]$leagueID = (Get-Config).LeagueID
    )

    $leagues = ConvertTo-SafeArray -value (Get-LeaguesRecursive -leagueID $leagueID)
    $leagueBySeason = @{}
    foreach ($league in $leagues) {
        $season = [string]$league.season
        if (-not [string]::IsNullOrWhiteSpace($season)) {
            $leagueBySeason[$season] = [string]$league.league_id
        }
    }

    $contextsByLeagueID = @{}

    foreach ($file in (Get-TransactionDraftPickTransactionFiles)) {
        $transactions = Get-TransactionDraftPickJsonFileContent -filePath $file.Path -description "Transactions"
        if ($transactions.Count -eq 0) { continue }

        $season = [string]$file.Season
        if (-not $leagueBySeason.ContainsKey($season)) {
            Write-Warning "Could not find Sleeper league for transaction season '$season'."
            continue
        }

        $seasonLeagueID = [string]$leagueBySeason[$season]
        if (-not $contextsByLeagueID.ContainsKey($seasonLeagueID)) {
            $contextsByLeagueID[$seasonLeagueID] = @(Get-TransactionDraftPickSleeperDraftContexts -leagueID $seasonLeagueID)
        }

        $result = Resolve-TransactionDraftPickTypesFromContexts -transactions $transactions -contexts @($contextsByLeagueID[$seasonLeagueID])
        if ($result.Changed) {
            Save-TransactionDraftPickTransactions -filePath $file.Path -transactions @($result.Transactions) -isCurrent ([bool]$file.IsCurrent)
        }
    }
}

# ===========================================================================
# Generated draft result enrichment
# ===========================================================================

function Get-TransactionDraftPickResultCandidates {
    param(
        [Parameter(Mandatory = $true)][object]$transaction,
        [Parameter(Mandatory = $true)][object]$transactionPick,
        [Parameter(Mandatory = $true)][array]$drafts,
        [switch]$RequireTradeHistory
    )

    $candidates = @()

    foreach ($draft in $drafts) {
        foreach ($draftPick in (ConvertTo-DraftSafeArray -value $draft.Picks)) {
            $isCandidate = $false

            if ($RequireTradeHistory) {
                foreach ($historyEntry in (ConvertTo-DraftSafeArray -value $draftPick.TradeHistory)) {
                    if (
                        [string]$historyEntry.TransactionID -eq [string]$transaction.TransactionID -and
                        [int]$historyEntry.PreviousOwnerRosterID -eq [int]$transactionPick.PreviousOwnerRosterID -and
                        [int]$historyEntry.NewOwnerRosterID -eq [int]$transactionPick.NewOwnerRosterID
                    ) {
                        $isCandidate = $true
                        break
                    }
                }
            }
            else {
                $isCandidate = (
                    [string]$draftPick.Season -eq [string]$transactionPick.Season -and
                    [int]$draftPick.Round -eq [int]$transactionPick.Round -and
                    [int]$draftPick.OriginalOwnerRosterID -eq [int]$transactionPick.OriginalOwnerRosterID
                )
            }

            if ($isCandidate) {
                $candidates += [PSCustomObject][ordered]@{
                    Draft = $draft
                    Pick  = $draftPick
                }
            }
        }
    }

    return @($candidates | Sort-Object @{ Expression = { "$($_.Draft.DraftKey)|$($_.Pick.PickKey)" } } -Unique)
}

function Select-TransactionDraftPickResultCandidate {
    param(
        [Parameter(Mandatory = $true)][array]$candidates,
        [Parameter(Mandatory = $true)][object]$transactionPick
    )

    if ($candidates.Count -eq 1) { return $candidates[0] }
    if ($candidates.Count -eq 0) { return $null }

    $sleeperDraftID = [string](Get-DraftObjectProperty -object $transactionPick -propertyName "SleeperDraftID" -defaultValue "")
    if (-not [string]::IsNullOrWhiteSpace($sleeperDraftID)) {
        $bySleeperDraft = @($candidates | Where-Object { [string]$_.Draft.SleeperDraftID -eq $sleeperDraftID })
        if ($bySleeperDraft.Count -eq 1) { return $bySleeperDraft[0] }
    }

    $draftKey = [string](Get-DraftObjectProperty -object $transactionPick -propertyName "DraftKey" -defaultValue "")
    if (-not [string]::IsNullOrWhiteSpace($draftKey)) {
        $byDraftKey = @($candidates | Where-Object { [string]$_.Draft.DraftKey -eq $draftKey })
        if ($byDraftKey.Count -eq 1) { return $byDraftKey[0] }
    }

    $draftType = [string](Get-DraftObjectProperty -object $transactionPick -propertyName "DraftType" -defaultValue "")
    if (-not [string]::IsNullOrWhiteSpace($draftType)) {
        $byDraftType = @($candidates | Where-Object { [string]$_.Draft.DraftType -eq $draftType })
        if ($byDraftType.Count -eq 1) { return $byDraftType[0] }
    }

    return $null
}

function Get-TransactionDraftPickResultMatch {
    param(
        [Parameter(Mandatory = $true)][object]$transaction,
        [Parameter(Mandatory = $true)][object]$transactionPick,
        [Parameter(Mandatory = $true)][array]$drafts
    )

    $historyCandidates = Get-TransactionDraftPickResultCandidates `
        -transaction $transaction `
        -transactionPick $transactionPick `
        -drafts $drafts `
        -RequireTradeHistory

    $match = Select-TransactionDraftPickResultCandidate -candidates $historyCandidates -transactionPick $transactionPick
    if ($null -ne $match) { return $match }

    $identityCandidates = Get-TransactionDraftPickResultCandidates `
        -transaction $transaction `
        -transactionPick $transactionPick `
        -drafts $drafts

    return Select-TransactionDraftPickResultCandidate -candidates $identityCandidates -transactionPick $transactionPick
}

function Add-TransactionDraftPickDetailsFromDrafts {
    param(
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$transactions,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$drafts
    )

    $changed = $false

    foreach ($transaction in $transactions) {
        foreach ($transactionPick in (ConvertTo-SafeArray -value $transaction.DraftPicks)) {
            $match = Get-TransactionDraftPickResultMatch -transaction $transaction -transactionPick $transactionPick -drafts $drafts
            if ($null -eq $match) { continue }

            $draft = $match.Draft
            $draftPick = $match.Pick

            Set-TransactionDraftPickPropertyValue -target $transactionPick -propertyName "DraftType" -value ([string]$draft.DraftType) -changed ([ref]$changed)
            Set-TransactionDraftPickPropertyValue -target $transactionPick -propertyName "DraftKey" -value ([string]$draft.DraftKey) -changed ([ref]$changed)
            Set-TransactionDraftPickPropertyValue -target $transactionPick -propertyName "SleeperDraftID" -value $draft.SleeperDraftID -changed ([ref]$changed)
            Set-TransactionDraftPickPropertyValue -target $transactionPick -propertyName "PickKey" -value ([string]$draftPick.PickKey) -changed ([ref]$changed)
            Set-TransactionDraftPickPropertyValue -target $transactionPick -propertyName "PositionInRound" -value $draftPick.PositionInRound -changed ([ref]$changed)
            Set-TransactionDraftPickPropertyValue -target $transactionPick -propertyName "OverallPick" -value $draftPick.OverallPick -changed ([ref]$changed)
            Set-TransactionDraftPickPropertyValue -target $transactionPick -propertyName "DisplayPick" -value $draftPick.DisplayPick -changed ([ref]$changed)
            Set-TransactionDraftPickPropertyValue -target $transactionPick -propertyName "PlayerID" -value $draftPick.PlayerID -changed ([ref]$changed)
            Set-TransactionDraftPickPropertyValue -target $transactionPick -propertyName "PlayerName" -value $draftPick.PlayerName -changed ([ref]$changed)
            Set-TransactionDraftPickPropertyValue -target $transactionPick -propertyName "PickStatus" -value $draftPick.Status -changed ([ref]$changed)
            Set-TransactionDraftPickPropertyValue -target $transactionPick -propertyName "SleeperPickNo" -value $draftPick.SleeperPickNo -changed ([ref]$changed)
        }
    }

    return [PSCustomObject][ordered]@{
        Transactions = @($transactions)
        Changed      = $changed
    }
}

function Update-CurrentTransactionDraftPickDetails {
    param(
        [AllowNull()]$drafts = $null
    )

    $config = Get-Config
    $transactions = Get-TransactionDraftPickJsonFileContent -filePath $config.TransactionsFile -description "Current transactions"

    if ($null -eq $drafts) {
        $drafts = Get-TransactionDraftPickJsonFileContent -filePath $config.DraftsFile -description "Current drafts"
    }
    else {
        $drafts = ConvertTo-DraftSafeArray -value $drafts
    }

    $result = Add-TransactionDraftPickDetailsFromDrafts -transactions $transactions -drafts $drafts
    if ($result.Changed) {
        Save-TransactionDraftPickTransactions -filePath $config.TransactionsFile -transactions @($result.Transactions) -isCurrent $true
    }

    return @($result.Transactions)
}

function Update-AllTransactionDraftPickDetailsFromLocalDrafts {
    $drafts = Get-TransactionDraftPickDraftsFromLocalFiles
    if ($drafts.Count -eq 0) {
        Write-Warning "No generated draft data found for transaction pick enrichment."
        return
    }

    foreach ($file in (Get-TransactionDraftPickTransactionFiles)) {
        $transactions = Get-TransactionDraftPickJsonFileContent -filePath $file.Path -description "Transactions"
        if ($transactions.Count -eq 0) { continue }

        $result = Add-TransactionDraftPickDetailsFromDrafts -transactions $transactions -drafts $drafts
        if ($result.Changed) {
            Save-TransactionDraftPickTransactions -filePath $file.Path -transactions @($result.Transactions) -isCurrent ([bool]$file.IsCurrent)
        }
    }
}
