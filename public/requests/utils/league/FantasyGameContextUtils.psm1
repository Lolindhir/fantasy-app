. "$PSScriptRoot\FantasyGameContextCore.ps1"

# Sleeper currently publishes players_points as a PlayerID-keyed object but
# starters_points as a positional array aligned with starters. The current
# FantasyGameContext adapter uses players_points as the authoritative per-player
# league-scored source, so positional arrays must not be interpreted as object
# property maps. Returning an empty map here intentionally activates the
# existing starter fallback from players_points.
function ConvertTo-FgcPointMapFromObject {
    param([AllowNull()][object]$Value)

    $map = @{}
    if ($null -eq $Value) { return $map }

    if ($Value -is [System.Collections.IDictionary]) {
        foreach ($key in $Value.Keys) {
            if ($null -ne $Value[$key]) { $map[[string]$key] = [double]$Value[$key] }
        }
        return $map
    }

    if ($Value -is [System.Collections.IEnumerable] -and $Value -isnot [string]) {
        return $map
    }

    foreach ($property in @($Value.PSObject.Properties)) {
        if ($null -ne $property.Value) { $map[[string]$property.Name] = [double]$property.Value }
    }
    return $map
}
