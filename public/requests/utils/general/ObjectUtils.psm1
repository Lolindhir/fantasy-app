
function ConvertTo-SafeObject {
    param(
        [AllowNull()]
        $value
    )

    if ($null -eq $value) {
        return [PSCustomObject]@{}
    }

    return $value
}