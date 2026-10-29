# Adapter for canonical season-specific starting slots; no independent FLEX rules.
param(
    [Parameter(Mandatory = $true)][string]$LeaguePath,
    [Parameter(Mandatory = $true)][string]$PositionsCsv
)
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'FantasyRelevanceV2Utils.psm1') -Force -ErrorAction Stop

$league = Get-Content -LiteralPath $LeaguePath -Raw | ConvertFrom-Json
$positions = @(
    $PositionsCsv.Split(',') |
        ForEach-Object { $_.Trim().ToUpperInvariant() } |
        Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
        Sort-Object -Unique
)
if ($positions.Count -eq 0) { throw 'Historical lineup slot adapter requires player positions.' }

$resolved = @(
    foreach ($slot in @(Get-FrvSlotDefinitions -League $league)) {
        $allowed = @(
            $positions | Where-Object {
                Test-FrvSlotEligibility -Position $_ -SlotType ([string]$slot.SlotType)
            }
        )
        if ($allowed.Count -eq 0) {
            throw "Slot '$($slot.SlotID)' has no eligible position in supplied universe."
        }
        [PSCustomObject][ordered]@{
            SlotID = [string]$slot.SlotID
            EligiblePositions = $allowed
        }
    }
)
ConvertTo-Json -InputObject $resolved -Depth 5 -Compress
