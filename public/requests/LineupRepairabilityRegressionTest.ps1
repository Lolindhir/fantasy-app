$ErrorActionPreference='Stop'
Import-Module "$PSScriptRoot\utils\league\AcquisitionCapabilityUtils.psm1" -Force
Import-Module "$PSScriptRoot\utils\league\LineupRepairabilityDecisionUtils.psm1" -Force

function Assert-LrrEqual { param($Expected,$Actual,[string]$Message);if([string]$Expected-ne[string]$Actual){throw "ASSERTION FAILED: $Message. Expected '$Expected', got '$Actual'."} }
function Assert-LrrNull { param($Actual,[string]$Message);if($null-ne$Actual){throw "ASSERTION FAILED: $Message. Expected null."} }
function New-LrrSlot { param([string]$ID,[string]$Type,[AllowNull()][string]$Starter,[string]$State='unlocked');[PSCustomObject]@{SlotID=$ID;SlotType=$Type;SlotOrdinal=1;SlotIndex=0;CurrentStarterID=$Starter;State=$State;GameID=$null;DecisionWindowID=$null;StartsAtUtc=$null} }
function New-LrrPlayer { param([string]$ID,[string]$Placement,[string]$Position,[string]$GameState='unlocked',[AllowNull()][string]$SlotID=$null);[PSCustomObject]@{PlayerID=$ID;Placement=$Placement;Position=$Position;GameState=$GameState;GameID="g-$ID";DecisionWindowID='2026-09-13T20:00:00Z';StartsAtUtc='2026-09-13T20:00:00Z';LineupSlotID=$SlotID;LineupSlotType=$null;EligibleUnlockedSlotIDs=@();IsBenchCandidate=$false;HasDirectScoringPath=$false;HasAlternativePath=$false} }
function New-LrrLock { param([string]$ID,[string]$Kind='scheduled',[string]$Starts='2026-09-13T20:00:00Z');[PSCustomObject]@{FantasyTeamID=1;PlayerID=$ID;NFLTeamID='1';Kind=$Kind;GameID=if($Kind-eq'scheduled'){"g-$ID"}else{$null};DecisionWindowID=if($Kind-eq'scheduled'){$Starts}else{$null};StartsAtUtc=if($Kind-eq'scheduled'){$Starts}else{$null};IsStarter=$false} }
function New-LrrReadModel { param([array]$Slots,[array]$Players,[array]$Locks,[string]$Evaluation='action-required');[PSCustomObject]@{SchemaVersion=2;LineupWeek=1;PlayerLockFacts=$Locks;TeamLineupEvaluations=@([PSCustomObject]@{FantasyTeamID=1;State=$Evaluation});FantasyRelevance=[PSCustomObject]@{Version=1;Teams=@([PSCustomObject]@{FantasyTeamID=1;Slots=$Slots;Players=$Players})}} }
function New-LrrGame { param([string]$TeamID,[string]$Starts='2026-09-13T20:00:00Z');[PSCustomObject]@{season='2026';gameWeek='Week 1';gameID="game-$TeamID";teamIDAway=$TeamID;teamIDHome="h-$TeamID";gameTime_epoch=[string]([DateTimeOffset]::Parse($Starts).ToUnixTimeSeconds());gameStatus='Scheduled'} }
function Invoke-Lrr { param([object]$Model,[array]$Teams,[array]$RawPlayers,[array]$Schedule,[object]$Capability);Add-LineupRepairabilityDecisionFacts -BaseReadModel $Model -Teams $Teams -Players $RawPlayers -Schedule $Schedule -AcquisitionCapability $Capability -AsOfUtc ([DateTimeOffset]::Parse('2026-09-13T10:00:00Z')) }
$unavailable=[PSCustomObject]@{State='known';ExternalAddsAllowed=$false;NextWaiverRun=$null}

# FLEX reshuffle: WR can move FLEX -> WR while Bench RB fills FLEX.
$model=New-LrrReadModel -Slots @((New-LrrSlot 'WR-1' 'WR' $null),(New-LrrSlot 'FLEX-1' 'FLEX' 'wr1')) -Players @((New-LrrPlayer 'wr1' 'starter' 'WR' 'unlocked' 'FLEX-1'),(New-LrrPlayer 'rb1' 'bench' 'RB')) -Locks @((New-LrrLock 'wr1'),(New-LrrLock 'rb1'))
$result=Invoke-Lrr $model @([PSCustomObject]@{TeamID=1;Roster=@('wr1','rb1')}) @() @() $unavailable
$repair=@($result.FantasyRelevance.Teams[0].Slots|Where-Object SlotID-eq'WR-1')[0].Repairability
Assert-LrrEqual 'repairable' $repair.State 'FLEX reshuffle must repair the complete mutable lineup';Assert-LrrEqual 'internal-roster' $repair.Path 'FLEX reshuffle path';Assert-LrrNull (@($result.FantasyRelevance.Teams[0].Slots|Where-Object SlotID-eq'FLEX-1')[0].Repairability) 'Healthy slot must not get a repairability problem';Assert-LrrEqual 2 $result.FantasyRelevance.Version 'Repairability must bump FantasyRelevance version'

# Two open slots cannot double-count one WR.
$model=New-LrrReadModel -Slots @((New-LrrSlot 'WR-1' 'WR' $null),(New-LrrSlot 'FLEX-1' 'FLEX' $null)) -Players @((New-LrrPlayer 'wr1' 'bench' 'WR')) -Locks @((New-LrrLock 'wr1'))
$result=Invoke-Lrr $model @([PSCustomObject]@{TeamID=1;Roster=@('wr1')}) @() @() $unavailable
foreach($slot in $result.FantasyRelevance.Teams[0].Slots){Assert-LrrEqual 'irreparable' $slot.Repairability.State 'One player cannot fill two slots'}

# Bye starter maps to its current slot and a Bench replacement repairs it.
$model=New-LrrReadModel -Slots @((New-LrrSlot 'WR-1' 'WR' 'bye1' 'unknown')) -Players @((New-LrrPlayer 'bye1' 'starter' 'WR' 'unknown' 'WR-1'),(New-LrrPlayer 'wr2' 'bench' 'WR')) -Locks @((New-LrrLock 'bye1' 'bye'),(New-LrrLock 'wr2'))
$result=Invoke-Lrr $model @([PSCustomObject]@{TeamID=1;Roster=@('bye1','wr2')}) @() @() $unavailable
$repair=$result.FantasyRelevance.Teams[0].Slots[0].Repairability;Assert-LrrEqual 'STARTER_ON_BYE' $repair.ProblemCode 'Bye must stay attached to starter slot';Assert-LrrEqual 'repairable' $repair.State 'Bench replacement repairs bye'

# Locked candidate, IR and Taxi do not repair an open slot.
$model=New-LrrReadModel -Slots @((New-LrrSlot 'FLEX-1' 'FLEX' $null)) -Players @((New-LrrPlayer 'locked' 'bench' 'RB' 'locked-active'),(New-LrrPlayer 'ir1' 'ir' 'WR'),(New-LrrPlayer 'taxi1' 'taxi' 'TE')) -Locks @((New-LrrLock 'locked'),(New-LrrLock 'ir1'),(New-LrrLock 'taxi1'))
$result=Invoke-Lrr $model @([PSCustomObject]@{TeamID=1;Roster=@('locked','ir1','taxi1')}) @() @() $unavailable
Assert-LrrEqual 'irreparable' $result.FantasyRelevance.Teams[0].Slots[0].Repairability.State 'Locked/IR/Taxi candidates must be excluded'

# External acquisition is valid only when the known waiver run precedes the candidate kickoff.
$externalModel=New-LrrReadModel -Slots @((New-LrrSlot 'WR-1' 'WR' $null)) -Players @() -Locks @()
$teams=@([PSCustomObject]@{TeamID=1;Roster=@()});$freePlayers=@([PSCustomObject]@{ID='fa1';Position='WR';TeamID='10'});$schedule=@(New-LrrGame '10' '2026-09-13T20:00:00Z')
$before=Resolve-TemporaryWaiverOnlyAcquisitionCapability -WaiversOpen $true -NextWaiverRun '2026-09-13T12:00:00Z'
$result=Invoke-Lrr $externalModel $teams $freePlayers $schedule $before;$repair=$result.FantasyRelevance.Teams[0].Slots[0].Repairability
Assert-LrrEqual 'repairable' $repair.State 'Waiver before kickoff must repair';Assert-LrrEqual 'external-acquisition' $repair.Path 'External path must stay provider-neutral'

foreach($run in @('2026-09-13T20:00:00Z','2026-09-13T21:00:00Z')){
    $model=New-LrrReadModel -Slots @((New-LrrSlot 'WR-1' 'WR' $null)) -Players @() -Locks @();$cap=Resolve-TemporaryWaiverOnlyAcquisitionCapability -WaiversOpen $true -NextWaiverRun $run;$result=Invoke-Lrr $model $teams $freePlayers $schedule $cap
    Assert-LrrEqual 'irreparable' $result.FantasyRelevance.Teams[0].Slots[0].Repairability.State 'Waiver at/after kickoff must not repair'
}

# Unknown capability and unknown relevant player lock evidence fail closed to unknown.
$model=New-LrrReadModel -Slots @((New-LrrSlot 'WR-1' 'WR' $null)) -Players @() -Locks @();$unknownCap=Resolve-TemporaryWaiverOnlyAcquisitionCapability -WaiversOpen $true -NextWaiverRun $null;$result=Invoke-Lrr $model $teams $freePlayers $schedule $unknownCap
Assert-LrrEqual 'unknown' $result.FantasyRelevance.Teams[0].Slots[0].Repairability.State 'Missing waiver timing must remain unknown';Assert-LrrEqual 'ACQUISITION_EVIDENCE_UNKNOWN' $result.FantasyRelevance.Teams[0].Slots[0].Repairability.ReasonCode 'Unknown acquisition reason'
$model=New-LrrReadModel -Slots @((New-LrrSlot 'WR-1' 'WR' $null)) -Players @() -Locks @();$unknownPlayer=@([PSCustomObject]@{ID='mystery';Position='WR';TeamID='999'});$result=Invoke-Lrr $model $teams $unknownPlayer $schedule $before
Assert-LrrEqual 'unknown' $result.FantasyRelevance.Teams[0].Slots[0].Repairability.State 'Unknown relevant external lock evidence must remain unknown';Assert-LrrEqual 'EXTERNAL_PLAYER_EVIDENCE_UNKNOWN' $result.FantasyRelevance.Teams[0].Slots[0].Repairability.ReasonCode 'Unknown external player reason'

# Review/data-quality state must not be converted into manager-fault repairability.
$model=New-LrrReadModel -Slots @((New-LrrSlot 'WR-1' 'WR' $null)) -Players @() -Locks @() -Evaluation 'review';$result=Invoke-Lrr $model $teams @() @() $unavailable
Assert-LrrEqual 'unknown' $result.FantasyRelevance.Teams[0].Slots[0].Repairability.State 'Review evidence must remain neutral unknown'

Write-Host 'Lineup repairability regression tests passed.' -ForegroundColor Green
