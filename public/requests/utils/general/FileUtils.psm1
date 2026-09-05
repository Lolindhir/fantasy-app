
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

# Konfiguration holen
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

function Save-JsonFile {
    param(
        # Entweder direkt File angeben
        [string]$TargetFile,

        # Oder Typ angeben, damit Pfad aus Config gezogen wird
        [ValidateSet("League","DecisionWindows","Players","Teams","Schedule","Games","Standings","Transactions", "Drafts")]
        [string]$Type,

        # Array oder Objekt, das gespeichert werden soll
        [Parameter(Mandatory=$true)]
        [object]$Data,

        # ScriptBlock für Vergleich altes <-> neues Objekt
        [ScriptBlock]$CompareScript,

        # Backup erstellen?
        [switch]$CreateBackup,

        # Timestamp aktualisieren?
        [switch]$UpdateTimestamp
    )

    # ------------------------------
    # 1️⃣ TargetFile auflösen
    # ------------------------------
    if (-not $TargetFile) {
        if (-not $Type) {
            throw "Either TargetFile or Type must be provided."
        }

        $config = Get-Config

        $pathMap = @{
            League          = $config.LeagueFile
            DecisionWindows = $config.DecisionWindowsFile
            Players         = $config.PlayersFile
            Teams           = $config.TeamsFile
            Schedule        = $config.ScheduleFile
            Games           = $config.GamesFile
            Standings       = $config.StandingsFile
            Transactions    = $config.TransactionsFile
            Drafts          = $config.DraftsFile
        }

        $TargetFile = $pathMap[$Type]

        if (-not $TargetFile) {
            throw "Could not resolve TargetFile (Type: $Type) from config."
        }
    }

    # ------------------------------
    # 2️⃣ Alte Daten laden
    # ------------------------------
    $oldData = $null
    if (Test-Path $TargetFile) {
        $raw = Get-Content $TargetFile -Raw
        if ($raw) { $oldData = $raw | ConvertFrom-Json }
    }

    # ------------------------------
    # 3️⃣ Änderungen prüfen
    # ------------------------------
    
    # Wenn kein CompareScript angegeben, immer speichern
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

    # ------------------------------
    # 4️⃣ Timestamp vorbereiten
    # ------------------------------
    $TimeSnapshot = Get-Date
    $Now = $TimeSnapshot.ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

    # ------------------------------
    # 5️⃣ Backup falls gewünscht
    # ------------------------------
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

    # ------------------------------
    # 6️⃣ JSON schreiben
    # ------------------------------
    try {
        $Data | ConvertTo-Json -Depth 10 | Out-File $TargetFile -Encoding UTF8
        Write-Host "$TargetFile saved!" -ForegroundColor Green
    } catch {
        throw "Error writing $($TargetFile): $_"
    }

    # ------------------------------
    # 7️⃣ Timestamp aktualisieren
    # ------------------------------
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