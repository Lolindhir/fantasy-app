$ErrorActionPreference = 'Stop'

Import-Module "$PSScriptRoot\utils\general\NflScheduleUtils.psm1" -Force

function Assert-NbwTrue {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw "ASSERTION FAILED: $Message" }
}

function Assert-NbwThrows {
    param([scriptblock]$Action, [string]$Pattern, [string]$Message)
    $thrown = $null
    try { & $Action } catch { $thrown = $_.Exception.Message }
    if ($null -eq $thrown) { throw "ASSERTION FAILED: $Message (no exception)." }
    if ($thrown -notmatch $Pattern) { throw "ASSERTION FAILED: $Message (got '$thrown')." }
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path

# 1. Real canonical schedule: expectations are derived from the data, no hardwired teams or weeks.
$scheduleFiles = @(Get-ChildItem (Join-Path $repoRoot 'source-data/nfl/schedules') -Filter '*.json' | Sort-Object Name)
Assert-NbwTrue ($scheduleFiles.Count -gt 0) 'No canonical NFL schedule files found.'
$season = [int]([System.IO.Path]::GetFileNameWithoutExtension($scheduleFiles[-1].Name))
$schedule = Get-Content $scheduleFiles[-1].FullName -Raw | ConvertFrom-Json
$regGames = @($schedule.Games | Where-Object { [string]$_.GameType -eq 'REG' })
$maxWeek = ($regGames | ForEach-Object { [int]$_.Week } | Measure-Object -Maximum).Maximum
$teams = @($regGames | ForEach-Object { $_.HomeTeam; $_.AwayTeam } | Sort-Object -Unique)

$byeWeeks = Get-CanonicalNflTeamByeWeeks -Season $season -RepoRoot $repoRoot
Assert-NbwTrue ($byeWeeks.Count -eq $teams.Count) "Bye week map must cover every canonical team ($($teams.Count))."
foreach ($team in $teams) {
    $bye = [int]$byeWeeks[$team]
    $weeksWithGame = @($regGames | Where-Object { $_.HomeTeam -eq $team -or $_.AwayTeam -eq $team } | ForEach-Object { [int]$_.Week })
    Assert-NbwTrue ($bye -ge 1 -and $bye -le $maxWeek) "Bye week of $team out of range."
    Assert-NbwTrue ($weeksWithGame -notcontains $bye) "$team has a game in its bye week $bye."
    Assert-NbwTrue ($weeksWithGame.Count -eq ($maxWeek - 1)) "$team must play every other REG week."
}

# 2. Tank01 abbreviations map to canonical teams; other values pass through; empty stays null.
Assert-NbwTrue ((ConvertTo-CanonicalNflScheduleTeam -Team 'LAR') -eq 'LA') 'LAR must map to LA.'
Assert-NbwTrue ((ConvertTo-CanonicalNflScheduleTeam -Team 'WSH') -eq 'WAS') 'WSH must map to WAS.'
foreach ($team in $teams) {
    Assert-NbwTrue ((ConvertTo-CanonicalNflScheduleTeam -Team $team) -eq $team) "Canonical team $team must pass through unchanged."
}
Assert-NbwTrue ($null -eq (ConvertTo-CanonicalNflScheduleTeam -Team '')) 'Empty team must stay null.'
Assert-NbwTrue ($byeWeeks.ContainsKey((ConvertTo-CanonicalNflScheduleTeam -Team 'LAR'))) 'Mapped LAR must resolve to a bye week.'
Assert-NbwTrue ($byeWeeks.ContainsKey((ConvertTo-CanonicalNflScheduleTeam -Team 'WSH'))) 'Mapped WSH must resolve to a bye week.'

# 3. Fail-closed cases on synthetic schedules.
$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("nfl-bye-weeks-" + [guid]::NewGuid().ToString('N'))
try {
    $dir = Join-Path $tempRoot 'source-data/nfl/schedules'
    New-Item -ItemType Directory -Path $dir -Force | Out-Null

    function Write-NbwSchedule {
        param([string]$Dataset, [object[]]$Games, [int]$Season = 2030, [int]$FileSeason = 2030)
        [PSCustomObject]@{ SchemaVersion = 2; Season = $Season; SourceDataset = $Dataset; Finalized = $false; Games = $Games } |
            ConvertTo-Json -Depth 6 | Set-Content (Join-Path $dir "$FileSeason.json") -Encoding UTF8
    }
    function New-NbwGame { param([int]$Week, [string]$HomeTeam, [string]$AwayTeam, [string]$Type = 'REG')
        [PSCustomObject]@{ GameID = "g_${Week}_${AwayTeam}_${HomeTeam}"; GameType = $Type; Week = $Week; HomeTeam = $HomeTeam; AwayTeam = $AwayTeam } }

    # Three teams over three weeks, each team plays two games and has one bye.
    $valid = @(
        (New-NbwGame 1 'A' 'B'),
        (New-NbwGame 2 'B' 'C'),
        (New-NbwGame 3 'C' 'A')
    )
    Write-NbwSchedule -Dataset 'nflverse.schedules' -Games $valid
    $map = Get-CanonicalNflTeamByeWeeks -Season 2030 -RepoRoot $tempRoot
    Assert-NbwTrue ($map['A'] -eq 2 -and $map['B'] -eq 3 -and $map['C'] -eq 1) 'Synthetic bye weeks must be the weeks without a game.'

    # Non-REG games do not count as played weeks.
    Write-NbwSchedule -Dataset 'nflverse.schedules' -Games ($valid + (New-NbwGame 2 'A' 'C' 'POST'))
    $map = Get-CanonicalNflTeamByeWeeks -Season 2030 -RepoRoot $tempRoot
    Assert-NbwTrue ($map['A'] -eq 2) 'Non-REG games must not fill a bye week.'

    Write-NbwSchedule -Dataset 'other.dataset' -Games $valid
    Assert-NbwThrows { Get-CanonicalNflTeamByeWeeks -Season 2030 -RepoRoot $tempRoot } 'Unexpected canonical NFL schedule source' 'Wrong dataset must fail closed.'

    Write-NbwSchedule -Dataset 'nflverse.schedules' -Games $valid -Season 2031 -FileSeason 2030
    Assert-NbwThrows { Get-CanonicalNflTeamByeWeeks -Season 2030 -RepoRoot $tempRoot } 'season mismatch|schedule is required' 'Season mismatch must fail closed.'

    Write-NbwSchedule -Dataset 'nflverse.schedules' -Games @((New-NbwGame 1 'A' 'B'), (New-NbwGame 4 'B' 'A'))
    Assert-NbwThrows { Get-CanonicalNflTeamByeWeeks -Season 2030 -RepoRoot $tempRoot } 'expected exactly one bye' 'Two bye weeks must fail closed.'

    Write-NbwSchedule -Dataset 'nflverse.schedules' -Games @((New-NbwGame 1 'A' 'B'), (New-NbwGame 1 'A' 'C'), (New-NbwGame 2 'B' 'C'))
    Assert-NbwThrows { Get-CanonicalNflTeamByeWeeks -Season 2030 -RepoRoot $tempRoot } 'twice in week' 'Duplicate team in a week must fail closed.'

    Assert-NbwThrows { Get-CanonicalNflTeamByeWeeks -Season 2099 -RepoRoot $tempRoot } 'schedule is required' 'Missing schedule must fail closed.'
}
finally {
    if (Test-Path $tempRoot) { Remove-Item $tempRoot -Recurse -Force }
}

Write-Host 'NFL bye week regression test passed.' -ForegroundColor Green
