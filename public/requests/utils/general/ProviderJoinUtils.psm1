# ===========================================================================
# Provider join invariant helpers
# ===========================================================================

function Get-ProviderJoinRecordDescription {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Item,

        [AllowEmptyCollection()]
        [string[]]$Properties = @()
    )

    $parts = @()
    foreach ($propertyName in $Properties) {
        $property = $Item.PSObject.Properties[$propertyName]
        $value = if ($null -ne $property -and $null -ne $property.Value -and -not [string]::IsNullOrWhiteSpace([string]$property.Value)) {
            [string]$property.Value
        }
        else {
            "<missing>"
        }

        $parts += "$propertyName=$value"
    }

    if ($parts.Count -eq 0) {
        return "<record>"
    }

    return ($parts -join "; ")
}

function New-UniqueObjectLookup {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [array]$Items,

        [Parameter(Mandatory = $true)]
        [string]$KeyProperty,

        [Parameter(Mandatory = $true)]
        [string]$SourceLabel,

        [string]$KeyLabel = $KeyProperty,

        [AllowEmptyCollection()]
        [string[]]$DescriptionProperties = @(),

        [switch]$AllowMissingKey
    )

    $lookup = @{}
    $descriptions = @{}

    foreach ($item in @($Items)) {
        if ($null -eq $item) {
            if ($AllowMissingKey) {
                continue
            }

            throw "$SourceLabel contains a null record; expected unique non-empty $KeyLabel."
        }

        $property = $item.PSObject.Properties[$KeyProperty]
        $key = if ($null -ne $property -and $null -ne $property.Value) { [string]$property.Value } else { "" }
        $key = $key.Trim()

        if ([string]::IsNullOrWhiteSpace($key)) {
            if ($AllowMissingKey) {
                continue
            }

            $description = Get-ProviderJoinRecordDescription -Item $item -Properties $DescriptionProperties
            throw "$SourceLabel contains a record with missing $KeyLabel. Record: $description"
        }

        $description = Get-ProviderJoinRecordDescription -Item $item -Properties $DescriptionProperties
        if ($lookup.ContainsKey($key)) {
            $firstDescription = [string]$descriptions[$key]
            throw "Duplicate $KeyLabel '$key' in $SourceLabel. First: $firstDescription | Duplicate: $description"
        }

        $lookup[$key] = $item
        $descriptions[$key] = $description
    }

    return $lookup
}
