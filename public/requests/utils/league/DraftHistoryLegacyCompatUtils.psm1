# ===========================================================================
# Draft History Legacy Compatibility Utils
# ===========================================================================
#
# Keeps the legacy draft history builder entrypoint from referencing the removed
# non-order-aware pick builder. The current production path still uses the safe
# order-aware historical update flow.

function New-DraftHistoryPicks {
    param(
        [Parameter(Mandatory = $true)][string]$leagueID,
        [Parameter(Mandatory = $true)][string]$draftKey,
        [Parameter(Mandatory = $true)][string]$season,
        [Parameter(Mandatory = $true)][string]$draftType,
        [Parameter(Mandatory = $true)][int]$rounds,
        [Parameter(Mandatory = $true)][array]$teamIDs
    )

    return New-DraftHistoryPicksOrderAware `
        -leagueID $leagueID `
        -draftKey $draftKey `
        -season $season `
        -draftType $draftType `
        -rounds $rounds `
        -teamIDs $teamIDs `
        -draftTypeSetting "linear"
}
