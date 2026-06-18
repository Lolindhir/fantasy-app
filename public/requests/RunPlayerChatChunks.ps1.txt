try {
    Import-Module "$PSScriptRoot\utils\ConfigUtils.psm1" -ErrorAction Stop -Force
    Import-Module "$PSScriptRoot\utils\player\PlayerChatExportUtils.psm1" -ErrorAction Stop -Force

    $config = Get-Config
    $playersRelevantFile = Join-Path $config.DataDir "Players_Relevant.json"
    $targetDirectory = Join-Path $config.DataDir "chat\players-relevant"

    if (-not (Test-Path $playersRelevantFile)) {
        throw "Players_Relevant.json not found. Run RequestLeague.ps1 first."
    }

    $players = Get-Content $playersRelevantFile -Raw | ConvertFrom-Json

    Export-PlayersForChatChunks `
        -Players @($players) `
        -TargetDirectory $targetDirectory `
        -ChunkSize 10 `
        -Source "Players_Relevant.json"
}
catch {
    Write-Error $_
    exit 1
}
