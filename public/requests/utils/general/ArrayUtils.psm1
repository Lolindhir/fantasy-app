
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