$ErrorActionPreference = 'Stop'

# #347 F3b: NFL team joins tolerate canonical abbreviations, provider spellings and legacy numeric app IDs on either side.

Import-Module "$PSScriptRoot\utils\general\NflTeamRegistryUtils.psm1" -ErrorAction Stop -Force
Import-Module "$PSScriptRoot\utils\league\DecisionWindowUtils.psm1" -ErrorAction Stop -Force
Import-Module "$PSScriptRoot\utils\league\LineupRepairabilityEvidenceUtils.psm1" -ErrorAction Stop -Force

function Assert-Equal {
    param($Expected, $Actual, [string]$Message)
    if ($Expected -ne $Actual) { throw "$Message (expected '$Expected', got '$Actual')" }
}

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$registry = Get-NflTeamRegistry -RepoRoot $repoRoot

# Derive the fixture teams from the registry instead of hard-wiring them.
$teams = @($registry.Teams.Values | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_.LegacyAppTeamID) } | Sort-Object TeamAbbr | Select-Object -First 3)
$awayAbbr = [string]$teams[0].TeamAbbr; $awayLegacy = [string]$teams[0].LegacyAppTeamID
$homeAbbr = [string]$teams[1].TeamAbbr; $homeLegacy = [string]$teams[1].LegacyAppTeamID
$byeAbbr = [string]$teams[2].TeamAbbr; $byeLegacy = [string]$teams[2].LegacyAppTeamID

# Join key behavior
Assert-Equal $awayAbbr (Get-NflTeamJoinKey -Value $awayLegacy) 'legacy ID resolves to the abbreviation'
Assert-Equal $awayAbbr (Get-NflTeamJoinKey -Value " $($awayAbbr.ToLowerInvariant()) ") 'abbreviation is trimmed and case-insensitive'
Assert-Equal 'NOT-A-TEAM' (Get-NflTeamJoinKey -Value 'NOT-A-TEAM') 'unresolvable keys stay unchanged (tolerant)'
if ($null -ne (Get-NflTeamJoinKey -Value '  ')) { throw 'blank key must yield null' }

# Decision Windows: schedule and player assignments in every key-form combination give the same facts.
$kickoff = '2026-09-20T17:00:00Z'
function New-Model {
    param([string]$ScheduleAway, [string]$ScheduleHome, [string]$PlayerTeamOnGame, [string]$PlayerTeamOnBye)
    return New-DecisionWindowsReadModel `
        -LeagueID 'league' -Season '2026' -LineupWeek 1 -LastLineupWeek 3 `
        -ScheduleGames @([PSCustomObject]@{ GameID = 'g1'; Week = 1; StartsAtUtc = $kickoff; AwayTeamID = $ScheduleAway; HomeTeamID = $ScheduleHome },
            # The bye-week team must be a known team through a game in another week.
            [PSCustomObject]@{ GameID = 'g2'; Week = 2; StartsAtUtc = '2026-09-27T17:00:00Z'; AwayTeamID = $PlayerTeamOnBye; HomeTeamID = $ScheduleHome }) `
        -FantasyRosters @([PSCustomObject]@{ FantasyTeamID = 1; PlayerIDs = @('p1', 'p2'); StarterIDs = @('p1', 'p2') }) `
        -PlayerTeamAssignments @(
            [PSCustomObject]@{ PlayerID = 'p1'; NFLTeamID = $PlayerTeamOnGame },
            [PSCustomObject]@{ PlayerID = 'p2'; NFLTeamID = $PlayerTeamOnBye }
        ) `
        -ExpectedStarterCount 2
}

$combinations = @(
    @($awayLegacy, $homeLegacy, $awayLegacy, $byeLegacy),
    @($awayAbbr, $homeAbbr, $awayLegacy, $byeAbbr),
    @($awayLegacy, $homeLegacy, $awayAbbr, $byeAbbr),
    @($awayAbbr, $homeAbbr, $awayAbbr, $byeAbbr)
)
foreach ($combination in $combinations) {
    $model = New-Model -ScheduleAway $combination[0] -ScheduleHome $combination[1] -PlayerTeamOnGame $combination[2] -PlayerTeamOnBye $combination[3]
    $label = ($combination -join '/')
    $scheduled = $model.PlayerLockFacts | Where-Object PlayerID -eq 'p1'
    $bye = $model.PlayerLockFacts | Where-Object PlayerID -eq 'p2'
    Assert-Equal 'scheduled' $scheduled.Kind "scheduled player ($label)"
    Assert-Equal 'g1' $scheduled.GameID "scheduled game ($label)"
    Assert-Equal 'bye' $bye.Kind "bye player ($label)"
    # Emitted team IDs are never rewritten by the join.
    Assert-Equal $combination[2] $scheduled.NFLTeamID "player NFLTeamID emitted as supplied ($label)"
    Assert-Equal $combination[0] $model.DecisionWindows[0].Games[0].AwayTeamID "schedule AwayTeamID emitted as supplied ($label)"
}

$unknownModel = New-Model -ScheduleAway $awayLegacy -ScheduleHome $homeLegacy -PlayerTeamOnGame 'NOT-A-TEAM' -PlayerTeamOnBye $byeLegacy
Assert-Equal 'unknown' (($unknownModel.PlayerLockFacts | Where-Object PlayerID -eq 'p1').Kind) 'unresolvable player team stays unknown'

# Lineup repairability external-acquisition evidence joins players to schedule across key forms.
$start = [DateTimeOffset]::Parse($kickoff)
foreach ($combination in $combinations) {
    $evidence = Get-LineupExternalRepairEvidence `
        -Players @([PSCustomObject]@{ ID = 'free1'; Position = 'WR'; TeamID = $combination[2] }) `
        -Teams @([PSCustomObject]@{ Roster = @('other') }) `
        -Schedule @([PSCustomObject]@{ gameID = 'g1'; gameWeek = 'Week 1'; teamIDAway = $combination[0]; teamIDHome = $combination[1]; gameTime_epoch = [string]$start.ToUnixTimeSeconds() }) `
        -MutableSlots @([PSCustomObject]@{ SlotType = 'WR' }) `
        -AcquisitionCapability ([PSCustomObject]@{ State = 'known'; ExternalAddsAllowed = $true; NextWaiverRun = $start.AddHours(-48).ToString('o') }) `
        -LineupWeek 1 `
        -AsOfUtc $start.AddHours(-72)
    Assert-Equal 'available' $evidence.State "evidence state ($($combination -join '/'))"
    Assert-Equal 1 @($evidence.Candidates).Count "candidate found across key forms ($($combination -join '/'))"
    Assert-Equal $false $evidence.PlayerEvidenceUnknown "no unknown evidence ($($combination -join '/'))"
}

Write-Host 'NFL team key join regression checks passed.'
