$ErrorActionPreference = 'Stop'

Import-Module "$PSScriptRoot\utils\ConfigUtils.psm1" -ErrorAction Stop -Force
Import-Module "$PSScriptRoot\utils\general\ProviderJoinUtils.psm1" -ErrorAction Stop -Force
Import-Module "$PSScriptRoot\utils\player\PlayerUtils.psm1" -ErrorAction Stop -Force

function Assert-Equal {
    param(
        [Parameter(Mandatory = $true)][AllowNull()]$Expected,
        [Parameter(Mandatory = $true)][AllowNull()]$Actual,
        [Parameter(Mandatory = $true)][string]$Message
    )

    if ($Expected -ne $Actual -or ($null -eq $Expected) -ne ($null -eq $Actual)) {
        throw "$Message Expected '$Expected', got '$Actual'."
    }
}

# Generic fixture: nested deeper than the published JSON depth, so freshly built objects differ from
# the file-loaded ones exactly like Grading[].Value[].GameDetails in the real Players.json.
function New-TestPlayers {
    param([int]$Count)

    foreach ($i in 1..$Count) {
        [PSCustomObject]@{
            ID                = "$i"
            Name              = "Test Player $i"
            Position          = 'WR'
            Salary            = 100.0 + $i
            FantasyPointsTotal = 0.0
            Ranking           = @()
            PointHistory      = $null
            Grading           = @(
                [PSCustomObject]@{
                    Type  = 'Form'
                    Value = @(
                        [PSCustomObject]@{
                            GameID      = "game_$i"
                            GameDetails = [ordered]@{ Week = 1; WeekFinal = $true; Home = 'AAA' }
                            FantasyPoints = 1.5
                        }
                    )
                }
            )
        }
    }
}

function Write-AndReloadPlayers {
    param([object]$Players, [string]$Path)

    $Players | ConvertTo-Json -Depth (Get-PlayersPublishedJsonDepth) | Out-File $Path -Encoding UTF8
    return (Get-Content $Path -Raw | ConvertFrom-Json)
}

$tempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("players-change-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tempDir | Out-Null

try {
    $file = Join-Path $tempDir 'Players.json'

    # Written content must really be cut at the published depth, otherwise this fixture proves nothing.
    $first = @(New-TestPlayers -Count 3)
    $old = Write-AndReloadPlayers -Players $first -Path $file
    Assert-Equal 'System.Collections.Specialized.OrderedDictionary' $old[0].Grading[0].Value[0].GameDetails 'Fixture must exceed the published JSON depth.'

    # Rebuilding identical data must not count as a change.
    $rebuilt = @(New-TestPlayers -Count 3)
    Assert-Equal $false (Compare-Players -OldPlayers $old -NewPlayers $rebuilt) 'Unchanged players must not be reported as changed.'

    # A second run on the reloaded file must stay a no-op as well.
    $old2 = Write-AndReloadPlayers -Players $rebuilt -Path $file
    Assert-Equal $false (Compare-Players -OldPlayers $old2 -NewPlayers @(New-TestPlayers -Count 3)) 'Reloaded players must not be reported as changed.'

    # Player order must not matter.
    $reversed = @(New-TestPlayers -Count 3)
    [array]::Reverse($reversed)
    Assert-Equal $false (Compare-Players -OldPlayers $old -NewPlayers $reversed) 'Player order must not count as a change.'

    # A real change in a published field must still be detected.
    $edited = @(New-TestPlayers -Count 3)
    $edited[1].Salary = 999.0
    Assert-Equal $true (Compare-Players -OldPlayers $old -NewPlayers $edited) 'A changed published field must be reported as changed.'

    # A different player count must still be detected.
    Assert-Equal $true (Compare-Players -OldPlayers $old -NewPlayers @(New-TestPlayers -Count 4)) 'A changed player count must be reported as changed.'

    # RequestPlayers must write with the same depth that the comparison uses.
    $request = Get-Content (Join-Path $PSScriptRoot 'RequestPlayers.ps1') -Raw
    Assert-Equal $true ($request.Contains('ConvertTo-Json -Depth (Get-PlayersPublishedJsonDepth)')) 'RequestPlayers must write Players.json with the shared published depth.'

    Write-Host 'Players change detection regression test passed.' -ForegroundColor Green
}
finally {
    Remove-Item $tempDir -Recurse -Force -ErrorAction SilentlyContinue
}
