
function Compare-Arrays($oldArray, $newArray, $fieldName, $compareName) {
    # Falls beide leer oder null sind
    if ((-not $oldArray -or $oldArray.Count -eq 0) -and (-not $newArray -or $newArray.Count -eq 0)) {
        return $true
    }

    # Normalisiere Arrays (null -> leer, sortiere für stabilen Vergleich)
    $oldArr = @()
    if ($oldArray) { $oldArr = $oldArray | Sort-Object }
    $newArr = @()
    if ($newArray) { $newArr = $newArray | Sort-Object }

    # Vergleiche Inhalte
    $diff = Compare-Object -ReferenceObject $oldArr -DifferenceObject $newArr

    if ($diff) {
        Write-Host "Difference at field '$fieldName' for '$compareName':" -ForegroundColor Yellow
        foreach ($d in $diff) {
            if ($d.SideIndicator -eq '<=') {
                Write-Host "  Removed: $($d.InputObject)" -ForegroundColor Red
            }
            elseif ($d.SideIndicator -eq '=>') {
                Write-Host "  Added: $($d.InputObject)" -ForegroundColor Green
            }
        }
        return $false
    }

    return $true
}

function ConvertTo-SafeArray {
    param(
        [AllowNull()]
        $value
    )

    if ($null -eq $value) {
        return @()
    }

    if ($value -is [array]) {
        return $value
    }

    return @($value)
}