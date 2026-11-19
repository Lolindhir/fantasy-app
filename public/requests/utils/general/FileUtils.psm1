
# ===========================================================================
# 1. Imports
# ===========================================================================

try {
    Import-Module "$PSScriptRoot\..\ConfigUtils.psm1" -ErrorAction Stop -Force
}
catch {
    Write-Error "Fehler beim Laden der Module: $_"
    throw $_
}

# ===========================================================================
# 2. Konfiguration
# ===========================================================================

try {
    $config = Get-Config
}
catch {
    Write-Error "Error loading configuration: $_"
    exit 1
}

# ===========================================================================
# 3. Funktionen
# ===========================================================================

# Key-order-independent, array-order-preserving canonical form of a parsed or in-memory JSON value. In-memory
# hashtables enumerate in a process-dependent order, so a plain serialization would differ between runs.
function ConvertTo-CanonicalJsonValue {
    param([AllowNull()]$Value)

    if ($null -eq $Value) { return $null }
    if ($Value -is [string] -or $Value -is [char] -or $Value -is [bool] -or $Value -is [ValueType]) { return $Value }

    if ($Value -is [System.Collections.IDictionary]) {
        $ordered = [ordered]@{}
        foreach ($key in @($Value.Keys | ForEach-Object { [string]$_ } | Sort-Object { $_ } -CaseSensitive)) {
            $ordered[$key] = ConvertTo-CanonicalJsonValue -Value $Value[$key]
        }
        return [PSCustomObject]$ordered
    }

    if ($Value -is [pscustomobject]) {
        $ordered = [ordered]@{}
        foreach ($name in @($Value.PSObject.Properties.Name | Sort-Object { $_ } -CaseSensitive)) {
            $ordered[$name] = ConvertTo-CanonicalJsonValue -Value $Value.$name
        }
        return [PSCustomObject]$ordered
    }

    if ($Value -is [System.Collections.IEnumerable]) {
        return , @($Value | ForEach-Object { ConvertTo-CanonicalJsonValue -Value $_ })
    }

    return $Value
}

# Change detection for a published JSON file: compares the complete content the file would hold, not a hand-picked
# field list (Issue #1572, L7). The new data is round-tripped through the same serialization Save-JsonFile writes, so
# both sides are parsed file content; object key order is ignored, array order is content. No old data means changed.
function Test-JsonContentChanged {
    param(
        [AllowNull()]$OldData,
        [AllowNull()]$NewData,
        [int]$Depth = 10
    )

    if ($null -eq $OldData) { return $true }

    $newParsed = $NewData | ConvertTo-Json -Depth $Depth | ConvertFrom-Json
    $oldJson = ConvertTo-CanonicalJsonValue -Value $OldData | ConvertTo-Json -Depth ($Depth + 2) -Compress
    $newJson = ConvertTo-CanonicalJsonValue -Value $newParsed | ConvertTo-Json -Depth ($Depth + 2) -Compress
    return $oldJson -cne $newJson
}

function Save-JsonFile {
    param(
        [string]$TargetFile,

        [ValidateSet("League","DecisionWindows","FantasyGameContext","Matchups","WeeklyRecaps","Players","Teams","Schedule","Standings","Transactions", "Drafts")]
        [string]$Type,

        [Parameter(Mandatory=$true)]
        [object]$Data,

        [ScriptBlock]$CompareScript,
        [switch]$CreateBackup,
        [switch]$UpdateTimestamp
    )

    if (-not $TargetFile) {
        if (-not $Type) {
            throw "Either TargetFile or Type must be provided."
        }

        $config = Get-Config

        $pathMap = @{
            League          = $config.LeagueFile
            DecisionWindows = $config.DecisionWindowsFile
            Matchups        = $config.MatchupsFile
            WeeklyRecaps    = $config.WeeklyRecapsFile
            Players         = $config.PlayersFile
            Teams           = $config.TeamsFile
            Schedule        = $config.ScheduleFile
            Standings       = $config.StandingsFile
            Transactions    = $config.TransactionsFile
            Drafts          = $config.DraftsFile
        }

        $TargetFile = $pathMap[$Type]

        if (-not $TargetFile) {
            throw "Could not resolve TargetFile (Type: $Type) from config."
        }
    }

    $oldData = $null
    if (Test-Path $TargetFile) {
        $raw = Get-Content $TargetFile -Raw
        if ($raw) { $oldData = $raw | ConvertFrom-Json }
    }

    if (-not $CompareScript) {
        Write-Host "No CompareScript provided - skipping change detection and saving file." -ForegroundColor Green
    }
    else {
        $changed = $true
        try {
            $changed = & $CompareScript $oldData $Data
        } catch {
            Write-Warning "Error in CompareScript: $_"
            $changed = $true
        }

        if (-not $changed) {
            Write-Host "No changes detected - update skipped." -ForegroundColor Cyan
            return
        } else {
            Write-Host "Changes detected - updating file." -ForegroundColor Green
        }
    }

    $TimeSnapshot = Get-Date
    $Now = $TimeSnapshot.ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

    if ($CreateBackup) {
        if (-not $BackupDir) { $BackupDir = $config.BackupDir }
        if (-not $BackupDir) {
            throw "BackupDir not provided and not found in config."
        }
        if (-not (Test-Path $BackupDir)) {
            New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
        }

        if (Test-Path $TargetFile) {
            $timestamp = $TimeSnapshot.ToUniversalTime().ToString("yyyyMMdd_HHmmss")
            $backupFile = Join-Path $BackupDir "$($Type)_$timestamp.json"
            Copy-Item -Path $TargetFile -Destination $backupFile -Force
            Write-Host "Old file backed up as $backupFile" -ForegroundColor Cyan
        }
    }

    try {
        $Data | ConvertTo-Json -Depth 10 | Out-File $TargetFile -Encoding UTF8
        Write-Host "$TargetFile saved!" -ForegroundColor Green
    } catch {
        throw "Error writing $($TargetFile): $_"
    }

    if ($UpdateTimestamp) {
        if (-not $TimestampFile) { $TimestampFile = $config.TimestampsFile }
        if (-not $TimestampFile) { Write-Warning "No TimestampFile provided; skipping timestamp update." ; return }

        $timestamps = @{}
        if (Test-Path $TimestampFile) {
            $raw = Get-Content $TimestampFile -Raw
            if ($raw) {
                $obj = $raw | ConvertFrom-Json
                $timestamps = @{}
                foreach ($prop in $obj.PSObject.Properties.Name) {
                    $timestamps[$prop] = $obj.$prop
                }
            }
        }

        $timestamps[$Type] = $Now
        $timestamps | ConvertTo-Json -Depth 3 | Set-Content $TimestampFile
        Write-Host "$Type timestamp updated: $Now" -ForegroundColor Green
    }
}
