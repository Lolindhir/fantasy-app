# ===========================================================================
# Players population and platform fields (#347 H1b)
#
# Consumes the export of tools/players_population.py: the Fantasy Management population rule
# (canonical NFL roster / NFL draft of the season / league-owned) with the platform fields taken
# from the canonical Sleeper snapshot and the canonical NFL team registry. It replaces the Tank01
# getNFLPlayerList population and the live Sleeper /players/nfl call of RequestPlayers.ps1.
# ===========================================================================

function Get-PlayerPopulationRepoRoot {
    return (Resolve-Path (Join-Path $PSScriptRoot "../../../..")).Path
}

function Get-PlayerPopulationPythonCommand {
    foreach ($name in @("python3", "python")) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($command) { return $command.Source }
    }

    throw "Python is required for the Players population export."
}

# Returns the export as nested hashtables; Players is an array in SleeperID order.
function Invoke-PlayerPopulationExport {
    param(
        [Parameter(Mandatory = $true)][int]$Season,
        [string]$RepoRoot = (Get-PlayerPopulationRepoRoot)
    )

    $toolPath = Join-Path $RepoRoot "tools/players_population.py"
    if (-not (Test-Path $toolPath)) {
        throw "Players population tool missing at '$toolPath'."
    }

    $python = Get-PlayerPopulationPythonCommand
    $outFile = [System.IO.Path]::GetTempFileName()
    try {
        $output = & $python $toolPath --repo-root $RepoRoot export --season $Season --out $outFile 2>&1
        $exitCode = $LASTEXITCODE
        $outputText = (@($output) | ForEach-Object { [string]$_ }) -join [Environment]::NewLine
        if ($exitCode -ne 0) {
            throw "Players population export failed with exit code $exitCode. $outputText"
        }
        Write-Host $outputText -ForegroundColor Yellow

        try {
            return (Get-Content $outFile -Raw | ConvertFrom-Json -AsHashtable)
        }
        catch {
            throw "Players population export returned invalid JSON. $_"
        }
    }
    finally {
        Remove-Item $outFile -Force -ErrorAction SilentlyContinue
    }
}

# Sleeper equivalents of the former Tank01 injury block (#347 Decision 6): Designation = Sleeper injury
# status, Date = injury start date, Description = first non-empty of notes, body part, practice description.
# ReturnDate is an honest unknown (null); Sleeper has no return date. Injured keeps its meaning
# "has a designation". Text fields stay empty strings when Sleeper carries no value.
function ConvertTo-PlayerInjuryDetails {
    param([AllowNull()]$Injury)

    $text = {
        param($value)
        if ($null -eq $value) { return "" }
        return ([string]$value).Trim()
    }

    $designation = & $text $Injury.Status
    $description = ""
    foreach ($candidate in @($Injury.Notes, $Injury.BodyPart, $Injury.PracticeDescription)) {
        $value = & $text $candidate
        if ($value) { $description = $value; break }
    }

    return [PSCustomObject]@{
        Injured = [bool]$designation
        Details = [PSCustomObject]@{
            ReturnDate  = $null
            Description = $description
            Date        = (& $text $Injury.StartDate)
            Designation = $designation
        }
    }
}

# Interim until H2 derives picture and links from canonical sources: values already published for a player
# are carried forward; a player without a published record gets the ESPN headshot from the canonical ESPN
# athlete ID (the pattern of the published values), or null.
function Get-InterimPlayerProfileLinks {
    param(
        [AllowNull()]$OldPlayer,
        [AllowNull()][string]$ESPNAthleteID
    )

    $picture = $null
    $fantasyPros = $null
    $espn = $null
    $nameShort = $null
    if ($OldPlayer) {
        $picture = $OldPlayer.Picture
        $fantasyPros = $OldPlayer.FantasyPros
        $espn = $OldPlayer.ESPN
        $nameShort = $OldPlayer.NameShort
    }
    if (-not $picture -and $ESPNAthleteID) {
        $picture = "https://a.espncdn.com/i/headshots/nfl/players/full/$ESPNAthleteID.png"
    }

    return [PSCustomObject]@{
        Picture     = $picture
        FantasyPros = $fantasyPros
        ESPN        = $espn
        NameShort   = $nameShort
    }
}

Export-ModuleMember -Function `
    Invoke-PlayerPopulationExport, `
    ConvertTo-PlayerInjuryDetails, `
    Get-InterimPlayerProfileLinks
