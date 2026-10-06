# Reads Sleeper platform facts from the canonical NFL source layer (source-data/nfl/platform/sleeper/players.json)
# instead of the live Sleeper /players/nfl call. Sleeper player_id stays the Players.json ID contract (#347 H4).

# Returns a hashtable Sleeper player_id -> @{ Position; Order } for the Sleeper depth chart fields.
# Fails closed when the snapshot is missing, has an unexpected source/schema or lists a Sleeper player twice.
function Get-CanonicalSleeperDepthCharts {
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot
    )

    $path = Join-Path $RepoRoot 'source-data/nfl/platform/sleeper/players.json'
    if (-not (Test-Path $path)) {
        throw "Canonical Sleeper players snapshot is required for depth charts: $path"
    }

    $snapshot = Get-Content $path -Raw | ConvertFrom-Json
    if ([string]$snapshot.SourceDataset -ne 'sleeper.players') {
        throw "Unexpected canonical Sleeper players source '$($snapshot.SourceDataset)'."
    }
    if ([int]$snapshot.SchemaVersion -ne 2) {
        throw "Unexpected canonical Sleeper players schema version '$($snapshot.SchemaVersion)'."
    }

    $depthCharts = @{}
    foreach ($record in @($snapshot.Records)) {
        $sleeperId = [string]$record.SleeperPlayerID
        if ([string]::IsNullOrWhiteSpace($sleeperId)) {
            throw 'Canonical Sleeper players snapshot has a record without SleeperPlayerID.'
        }
        if ($depthCharts.ContainsKey($sleeperId)) {
            throw "Canonical Sleeper players snapshot lists SleeperPlayerID $sleeperId twice."
        }
        $depthCharts[$sleeperId] = @{
            Position = $record.DepthChartPosition
            Order    = $record.DepthChartOrder
        }
    }
    if ($depthCharts.Count -eq 0) {
        throw 'Canonical Sleeper players snapshot has no records.'
    }
    return $depthCharts
}

Export-ModuleMember -Function Get-CanonicalSleeperDepthCharts
