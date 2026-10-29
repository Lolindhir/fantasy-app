# Sleeper marks an unfilled lineup slot with the player id "0"; no real player has that id.
# This is the single place that turns such a value (or null/blank) into "no player".
function ConvertTo-SleeperPlayerID {
    param([AllowNull()][object]$Value)

    if ($null -eq $Value) { return $null }
    $text = ([string]$Value).Trim()
    if ([string]::IsNullOrWhiteSpace($text) -or $text -eq '0') { return $null }
    return $text
}

Export-ModuleMember -Function ConvertTo-SleeperPlayerID
