$ErrorActionPreference = 'Stop'

Import-Module "$PSScriptRoot\utils\league\EspnScoringAvailabilityUtils.psm1" -Force

function Assert-EsaEqual {
    param($Expected, $Actual, [string]$Message)
    if ($Expected -ne $Actual) {
        throw "ASSERTION FAILED: $Message. Expected '$Expected', got '$Actual'."
    }
}

function Assert-EsaTrue {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw "ASSERTION FAILED: $Message" }
}

$players = @(
    [PSCustomObject]@{ ID = '9493'; ESPNID = '4426515'; Name = 'Puka Nacua' },
    [PSCustomObject]@{ ID = '9999'; ESPNID = '555'; Name = 'Questionable Player' },
    [PSCustomObject]@{ ID = '8888'; ESPNID = '777'; Name = 'Healthy Missing Player' }
)

$response = [PSCustomObject]@{
    injuries = @(
        [PSCustomObject]@{
            team = [PSCustomObject]@{ id = '14' }
            injuries = @(
                [PSCustomObject]@{
                    athlete = [PSCustomObject]@{ id = '4426515'; displayName = 'Puka Nacua' }
                    status = 'Out'
                    date = '2026-09-21T23:02Z'
                },
                [PSCustomObject]@{
                    athlete = [PSCustomObject]@{ id = '555'; displayName = 'Questionable Player' }
                    status = 'Questionable'
                    date = '2026-09-22T00:00Z'
                }
            )
        }
    )
}

$map = Get-EspnScoringAvailabilityBySleeperID -Players $players -InjuryResponse $response
Assert-EsaEqual 2 $map.Count 'Only ESPN players present in the injury response should create observations'
Assert-EsaEqual 'unavailable' $map['9493'].State 'Out must normalize to unavailable'
Assert-EsaEqual 'out' $map['9493'].Reason 'Out reason'
Assert-EsaEqual 'ESPN' $map['9493'].Source 'Provider-neutral observation must retain ESPN provenance'
Assert-EsaEqual '4426515' $map['9493'].ProviderPlayerID 'ESPN player ID join'
Assert-EsaTrue (Test-EspnScoringAvailabilityTerminal -Observation $map['9493']) 'Out must be terminal'
Assert-EsaEqual 'uncertain' $map['9999'].State 'Questionable must remain uncertain'
Assert-EsaTrue (-not (Test-EspnScoringAvailabilityTerminal -Observation $map['9999'])) 'Questionable must never be terminal'
Assert-EsaTrue (-not $map.ContainsKey('8888')) 'Absence from ESPN injuries must not synthesize a status'

$doubtful = ConvertTo-EspnScoringAvailabilityObservation -ProviderPlayerID '1' -Status 'Doubtful'
Assert-EsaEqual 'uncertain' $doubtful.State 'Doubtful remains uncertain'
Assert-EsaTrue (-not (Test-EspnScoringAvailabilityTerminal -Observation $doubtful)) 'Doubtful must never be terminal'

$inactive = ConvertTo-EspnScoringAvailabilityObservation -ProviderPlayerID '2' -Status 'Inactive'
Assert-EsaEqual 'unavailable' $inactive.State 'Inactive is terminal scoring unavailability'
Assert-EsaEqual 'inactive' $inactive.Reason 'Inactive reason'

$unknown = ConvertTo-EspnScoringAvailabilityObservation -ProviderPlayerID '3' -Status 'Mystery Status'
Assert-EsaEqual 'unknown' $unknown.State 'Unmapped provider states must fail closed as unknown'
Assert-EsaTrue (-not (Test-EspnScoringAvailabilityTerminal -Observation $unknown)) 'Unknown provider state must not be terminal'

$ambiguous = [PSCustomObject]@{
    injuries = @(
        [PSCustomObject]@{
            injuries = @(
                [PSCustomObject]@{ athlete = [PSCustomObject]@{ id = '4426515' }; status = 'Out' },
                [PSCustomObject]@{ athlete = [PSCustomObject]@{ id = '4426515' }; status = 'Questionable' }
            )
        }
    )
}
$ambiguousMap = Get-EspnScoringAvailabilityBySleeperID -Players $players -InjuryResponse $ambiguous
Assert-EsaTrue (-not $ambiguousMap.ContainsKey('9493')) 'Conflicting ESPN observations must be quarantined instead of picking a winner'

Write-Host 'ESPN scoring availability regression tests passed.'
