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
# Past Seasons Index
# ===========================================================================

function ConvertTo-PastSeasonIndexWebPath {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][hashtable]$Config
    )

    $dataDir = [System.IO.Path]::GetFullPath([string]$Config.DataDir)
    $fullPath = [System.IO.Path]::GetFullPath($FilePath)

    if (-not $dataDir.EndsWith([System.IO.Path]::DirectorySeparatorChar)) {
        $dataDir = "$dataDir$([System.IO.Path]::DirectorySeparatorChar)"
    }

    if ($fullPath.StartsWith($dataDir, [System.StringComparison]::OrdinalIgnoreCase)) {
        $relativePath = $fullPath.Substring($dataDir.Length)
        return "data/$($relativePath -replace '\\', '/')"
    }

    return ($FilePath -replace '\\', '/')
}

function Get-PastSeasonResourceFilePath {
    param(
        [Parameter(Mandatory = $true)][hashtable]$ResourceConfig,
        [Parameter(Mandatory = $true)][string]$Season
    )

    return Join-Path ([string]$ResourceConfig.Directory) "$($ResourceConfig.Prefix)$Season$($ResourceConfig.Suffix)"
}

function Get-PastSeasonResourceFiles {
    param(
        [Parameter(Mandatory = $true)][hashtable]$ResourceConfig,
        [Parameter(Mandatory = $true)][hashtable]$Config
    )

    $directory = [string]$ResourceConfig.Directory
    $prefix = [string]$ResourceConfig.Prefix
    $suffix = [string]$ResourceConfig.Suffix
    $resourceKey = [string]$ResourceConfig.Key

    if (-not (Test-Path $directory)) {
        Write-Host "Past season resource folder not found for '$resourceKey': $directory" -ForegroundColor DarkGray
        return @()
    }

    $filter = "$prefix*$suffix"
    $escapedPrefix = [regex]::Escape($prefix)
    $escapedSuffix = [regex]::Escape($suffix)
    $pattern = "^$escapedPrefix(?<Season>.+)$escapedSuffix$"

    return @(
        Get-ChildItem -Path $directory -Filter $filter -File |
            Where-Object { $_.Name -match $pattern } |
            ForEach-Object {
                $season = [string]$Matches.Season
                if ([string]::IsNullOrWhiteSpace($season)) { return }

                [PSCustomObject][ordered]@{
                    Season = $season
                    ResourceKey = $resourceKey
                    FilePath = $_.FullName
                    Path = ConvertTo-PastSeasonIndexWebPath -FilePath $_.FullName -Config $Config
                    UpdatedAt = $_.LastWriteTimeUtc.ToString("yyyy-MM-ddTHH:mm:ssZ")
                }
            }
    )
}

function New-PastSeasonsIndex {
    param(
        [hashtable]$Config = (Get-Config)
    )

    $resourceConfigs = @($Config.PastSeasonResources)
    $resourceFiles = @()

    foreach ($resourceConfig in $resourceConfigs) {
        $resourceFiles += Get-PastSeasonResourceFiles -ResourceConfig $resourceConfig -Config $Config
    }

    $seasons = @(
        $resourceFiles |
            Select-Object -ExpandProperty Season -Unique |
            Sort-Object @{ Expression = { [int]$_ }; Descending = $true }
    )

    $seasonEntries = @()

    foreach ($season in $seasons) {
        $resources = [ordered]@{}

        foreach ($resourceConfig in $resourceConfigs) {
            $resourceKey = [string]$resourceConfig.Key
            $existingFile = $resourceFiles |
                Where-Object { $_.Season -eq $season -and $_.ResourceKey -eq $resourceKey } |
                Select-Object -First 1
            $expectedPath = Get-PastSeasonResourceFilePath -ResourceConfig $resourceConfig -Season $season

            $resources[$resourceKey] = [PSCustomObject][ordered]@{
                Path = ConvertTo-PastSeasonIndexWebPath -FilePath $expectedPath -Config $Config
                Exists = $null -ne $existingFile
                UpdatedAt = if ($existingFile) { $existingFile.UpdatedAt } else { $null }
            }
        }

        $seasonEntries += [PSCustomObject][ordered]@{
            Season = [string]$season
            Resources = [PSCustomObject]$resources
        }
    }

    return [PSCustomObject][ordered]@{
        GeneratedAt = $null
        Seasons = @($seasonEntries)
    }
}

function ConvertTo-PastSeasonsIndexComparableJson {
    param([AllowNull()]$Index)

    if ($null -eq $Index) { return $null }

    $comparable = [PSCustomObject][ordered]@{
        Seasons = @($Index.Seasons)
    }

    return ($comparable | ConvertTo-Json -Depth 20)
}

function Save-PastSeasonsIndex {
    param(
        [Parameter(Mandatory = $true)]$Index,
        [hashtable]$Config = (Get-Config)
    )

    $targetFile = [string]$Config.PastSeasonsIndexFile
    $oldIndex = $null

    if (Test-Path $targetFile) {
        $raw = Get-Content $targetFile -Raw
        if (-not [string]::IsNullOrWhiteSpace($raw)) {
            $oldIndex = $raw | ConvertFrom-Json
        }
    }

    $oldComparable = ConvertTo-PastSeasonsIndexComparableJson -Index $oldIndex
    $newComparable = ConvertTo-PastSeasonsIndexComparableJson -Index $Index

    if ($oldComparable -eq $newComparable) {
        Write-Host "No changes detected in PastSeasonsIndex.json - update skipped." -ForegroundColor Cyan
        return $false
    }

    $Index.GeneratedAt = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

    $targetDir = Split-Path $targetFile -Parent
    if (-not (Test-Path $targetDir)) {
        New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
    }

    $Index | ConvertTo-Json -Depth 20 | Out-File $targetFile -Encoding UTF8
    Write-Host "$targetFile saved!" -ForegroundColor Green

    return $true
}

function Update-PastSeasonsIndex {
    param(
        [hashtable]$Config = (Get-Config)
    )

    $index = New-PastSeasonsIndex -Config $Config
    return Save-PastSeasonsIndex -Index $index -Config $Config
}
