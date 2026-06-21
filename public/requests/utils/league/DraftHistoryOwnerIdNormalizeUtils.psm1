# ===========================================================================
# Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\..\ConfigUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\..\general\FileUtils.psm1" -ErrorAction Stop -Force
}
catch {
    Write-Error "Fehler beim Laden der Module: $_"
    throw $_
}

# ===========================================================================
# Draft History Owner ID Normalization
# ===========================================================================

function ConvertTo-DraftHistorySafeArray {
    param([AllowNull()]$value)

    if ($null -eq $value) { return @() }
    if ($value -is [array]) { return @($value) }
    return @($value)
}

function ConvertTo-DraftHistoryNumericOwnerId {
    param(
        [AllowNull()]$value,
        [ref]$changed
    )

    if ($null -eq $value) { return $value }
    if ([string]::IsNullOrWhiteSpace([string]$value)) { return $value }

    $numericValue = [int]$value

    if (-not ($value -is [int] -or $value -is [long])) {
        $changed.Value = $true
    }

    return $numericValue
}

function Normalize-DraftHistoryOwnerIdsInObject {
    param(
        [Parameter(Mandatory = $true)]$draftsData,
        [ref]$changed
    )

    foreach ($draft in (ConvertTo-DraftHistorySafeArray -value $draftsData)) {
        foreach ($pick in (ConvertTo-DraftHistorySafeArray -value $draft.Picks)) {
            $pick.OriginalOwnerRosterID = ConvertTo-DraftHistoryNumericOwnerId -value $pick.OriginalOwnerRosterID -changed $changed
            $pick.CurrentOwnerRosterID = ConvertTo-DraftHistoryNumericOwnerId -value $pick.CurrentOwnerRosterID -changed $changed

            foreach ($tradeEntry in (ConvertTo-DraftHistorySafeArray -value $pick.TradeHistory)) {
                $tradeEntry.PreviousOwnerRosterID = ConvertTo-DraftHistoryNumericOwnerId -value $tradeEntry.PreviousOwnerRosterID -changed $changed
                $tradeEntry.NewOwnerRosterID = ConvertTo-DraftHistoryNumericOwnerId -value $tradeEntry.NewOwnerRosterID -changed $changed
            }
        }
    }

    return $draftsData
}

function Normalize-DraftHistoryOwnerIds {
    $config = Get-Config
    $folder = $config.DraftsArchiveDir

    if (-not (Test-Path $folder)) {
        Write-Warning "Draft history folder not found at $folder. Skipping owner id normalization."
        return @()
    }

    $filePrefix = Split-Path $config.DraftsFileHistoricalPrefix -Leaf
    $filter = "$filePrefix*$($config.DraftsFileHistoricalSuffix)"
    $updatedFiles = @()

    Get-ChildItem $folder -Filter $filter | ForEach-Object {
        $filePath = $_.FullName
        $raw = Get-Content $filePath -Raw
        if ([string]::IsNullOrWhiteSpace($raw)) { return }

        $draftsData = $raw | ConvertFrom-Json
        $changed = $false
        $draftsData = Normalize-DraftHistoryOwnerIdsInObject -draftsData $draftsData -changed ([ref]$changed)

        if ($changed) {
            Write-Host "Normalizing numeric owner ids in historical drafts: $($_.Name)" -ForegroundColor Yellow
            Save-JsonFile -TargetFile $filePath -Data $draftsData
            $updatedFiles += $_.Name
        }
    }

    if ($updatedFiles.Count -eq 0) {
        Write-Host "Historical draft owner ids already numeric." -ForegroundColor DarkGray
    }

    return $updatedFiles
}
