function Get-GsuPropertyValue {
    param(
        [AllowNull()][object]$Object,
        [Parameter(Mandatory = $true)][string[]]$Names
    )

    if ($null -eq $Object) { return $null }
    foreach ($name in $Names) {
        if ($Object -is [System.Collections.IDictionary] -and $Object.Contains($name)) {
            return $Object[$name]
        }
        if ($Object.PSObject.Properties.Name -contains $name) {
            return $Object.$name
        }
    }
    return $null
}

function ConvertTo-GsuNullableScore {
    param([AllowNull()][object]$Value)

    if ($null -eq $Value) { return $null }
    $text = ([string]$Value).Trim()
    if ([string]::IsNullOrWhiteSpace($text)) { return $null }

    $parsed = 0.0
    if ([double]::TryParse(
        $text,
        [System.Globalization.NumberStyles]::Float,
        [System.Globalization.CultureInfo]::InvariantCulture,
        [ref]$parsed
    )) {
        return [double]$parsed
    }
    return $null
}

function Test-GameHasScorePair {
    param([AllowNull()][object]$Game)

    $away = ConvertTo-GsuNullableScore (Get-GsuPropertyValue -Object $Game -Names @('awayPts','AwayScore'))
    $home = ConvertTo-GsuNullableScore (Get-GsuPropertyValue -Object $Game -Names @('homePts','HomeScore'))
    return $null -ne $away -and $null -ne $home
}

function Get-Tank01ScoreRows {
    param([AllowNull()][object]$Value)

    if ($null -eq $Value) { return @() }
    if ($Value -is [string] -or $Value -is [ValueType]) { return @() }

    if ($Value -is [System.Collections.IDictionary]) {
        $rows = @()
        foreach ($key in $Value.Keys) {
            $row = $Value[$key]
            if ($null -eq $row -or $row -is [string] -or $row -is [ValueType]) { continue }
            if ($null -eq (Get-GsuPropertyValue -Object $row -Names @('gameID','GameID'))) {
                $row | Add-Member -NotePropertyName gameID -NotePropertyValue ([string]$key) -Force
            }
            $rows += $row
        }
        return $rows
    }

    if ($Value -is [System.Collections.IEnumerable]) {
        return @($Value | Where-Object { $null -ne $_ -and $_ -isnot [string] -and $_ -isnot [ValueType] })
    }

    $directGameID = Get-GsuPropertyValue -Object $Value -Names @('gameID','GameID')
    if ($null -ne $directGameID) { return @($Value) }

    $rows = @()
    foreach ($property in @($Value.PSObject.Properties)) {
        $row = $property.Value
        if ($null -eq $row -or $row -is [string] -or $row -is [ValueType]) { continue }
        if ($null -eq (Get-GsuPropertyValue -Object $row -Names @('gameID','GameID'))) {
            $row | Add-Member -NotePropertyName gameID -NotePropertyValue ([string]$property.Name) -Force
        }
        $rows += $row
    }
    return $rows
}

function Merge-GameScoresIntoSchedule {
    param(
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$Schedule,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][array]$ScoreRows
    )

    $scoreByGameID = @{}
    foreach ($row in @($ScoreRows)) {
        if ($null -eq $row) { continue }
        $gameID = [string](Get-GsuPropertyValue -Object $row -Names @('gameID','GameID'))
        if ([string]::IsNullOrWhiteSpace($gameID)) { continue }

        $away = ConvertTo-GsuNullableScore (Get-GsuPropertyValue -Object $row -Names @('awayPts','AwayScore','awayScore'))
        $home = ConvertTo-GsuNullableScore (Get-GsuPropertyValue -Object $row -Names @('homePts','HomeScore','homeScore'))
        if ($null -eq $away -or $null -eq $home) { continue }

        if ($scoreByGameID.ContainsKey($gameID)) {
            $existing = $scoreByGameID[$gameID]
            if ([double]$existing.Away -ne [double]$away -or [double]$existing.Home -ne [double]$home) {
                throw "Conflicting NFL score evidence for game '$gameID'."
            }
            continue
        }

        $scoreByGameID[$gameID] = [PSCustomObject]@{ Away = [double]$away; Home = [double]$home }
    }

    foreach ($game in @($Schedule)) {
        if ($null -eq $game) { continue }
        $gameID = [string](Get-GsuPropertyValue -Object $game -Names @('gameID','GameID'))
        if ([string]::IsNullOrWhiteSpace($gameID) -or -not $scoreByGameID.ContainsKey($gameID)) { continue }

        # Score evidence is display data only. Canonical game finality decides whether
        # a completed-game score may be published; provider score/status never promotes Final.
        $status = [string](Get-GsuPropertyValue -Object $game -Names @('gameStatus','Status'))
        if ($status -notmatch '^Final') { continue }

        $score = $scoreByGameID[$gameID]
        if ($game.PSObject.Properties.Name -contains 'awayPts') {
            $game.awayPts = [double]$score.Away
        } else {
            $game | Add-Member -NotePropertyName awayPts -NotePropertyValue ([double]$score.Away)
        }
        if ($game.PSObject.Properties.Name -contains 'homePts') {
            $game.homePts = [double]$score.Home
        } else {
            $game | Add-Member -NotePropertyName homePts -NotePropertyValue ([double]$score.Home)
        }
    }

    return @($Schedule)
}

Export-ModuleMember -Function Test-GameHasScorePair, Get-Tank01ScoreRows, Merge-GameScoresIntoSchedule
