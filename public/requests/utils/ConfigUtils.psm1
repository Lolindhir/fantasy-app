
function Get-Config {

    # League Settings
    $Global:SalaryRelevantTeamSize = 20
    $Global:MaxTransactionWeek = 20

    # RapidAPI-Key für Tank01
    $Global:RapidAPIKey = "cccff76c4bmsh01946acbc2d3c0bp141721jsn161bd86f4c69"
    $Global:RapidAPIKeyAlt1 = "1e10165385msh4175f82e3d08e84p19fd3ejsn82f1e01c01aa"
    $Global:RapidAPIKeyAlt2 = "3a3482fb66msh803287ddb5773dbp185f31jsnc6f1e236cd5e"

    # Point Settings
    $Global:WeightTotal = 0.5
    $Global:WeightGame = 0.5

    # File Locations
    $Global:DataDir = "$PSScriptRoot\..\..\data"
    $Global:BackupDir = Join-Path $Global:DataDir "backup"
    $Global:PlayersFile = Join-Path $Global:DataDir "Players.json"
    $Global:LeagueFile = Join-Path $Global:DataDir "League.json"
    $Global:TeamsFile = Join-Path $Global:DataDir "Teams.json"
    $Global:ScheduleFile = Join-Path $Global:DataDir "Schedule.json"
    $Global:GamesFile = Join-Path $Global:DataDir "Games.json"
    $Global:StandingsFile = Join-Path $Global:DataDir "Standings.json"
    $Global:ManualTransactionsFile = Join-Path $Global:DataDir "ManualFADraftPickTrades.json"
    $Global:TransactionsFile = Join-Path $Global:DataDir "Transactions.json"
    $Global:TransactionsArchiveDir = Join-Path $Global:DataDir "past_seasons\Transactions"
    $Global:TransactionsFileHistoricalPrefix = Join-Path $Global:TransactionsArchiveDir "Transactions_"
    $Global:TransactionsFileHistoricalSuffix = ".json"
    $Global:TimestampsFile = Join-Path $Global:DataDir "Timestamps.json"
    $Global:ErrorsFile = Join-Path $Global:DataDir "Errors.json"

    # Lade Metadata
    $metadataPath = Join-Path $Global:DataDir "Metadata.json"
    if (Test-Path $metadataPath) {
        $metadataContent = Get-Content $metadataPath -Raw | ConvertFrom-Json
        $Global:LeagueID = $metadataContent.LeagueID
        $Global:LeagueYear = $metadataContent.LeagueYear
        $Global:CapDeadline = $metadataContent.CapDeadline
    } else {
        Write-Error "Metadata file not found at $metadataPath."
        throw "Metadata file not found."
    }

    return @{
        LeagueYear = $Global:LeagueYear
        SalaryRelevantTeamSize = $Global:SalaryRelevantTeamSize
        MaxTransactionWeek = $Global:MaxTransactionWeek
        LeagueID = $Global:LeagueID
        CapDeadline = $Global:CapDeadline
        RapidAPIKey = $Global:RapidAPIKey
        RapidAPIKeyAlt1 = $Global:RapidAPIKeyAlt1
        RapidAPIKeyAlt2 = $Global:RapidAPIKeyAlt2
        WeightTotal = $Global:WeightTotal
        WeightGame = $Global:WeightGame
        DataDir = $Global:DataDir
        BackupDir = $Global:BackupDir
        PlayersFile = $Global:PlayersFile
        LeagueFile = $Global:LeagueFile
        TeamsFile = $Global:TeamsFile
        ScheduleFile = $Global:ScheduleFile
        GamesFile = $Global:GamesFile
        StandingsFile = $Global:StandingsFile
        ManualTransactionsFile = $Global:ManualTransactionsFile
        TransactionsFile = $Global:TransactionsFile
        TransactionsArchiveDir = $Global:TransactionsArchiveDir
        TransactionsFileHistoricalPrefix = $Global:TransactionsFileHistoricalPrefix
        TransactionsFileHistoricalSuffix = $Global:TransactionsFileHistoricalSuffix
        TimestampsFile = $Global:TimestampsFile
        ErrorsFile = $Global:ErrorsFile
    }
    
}
