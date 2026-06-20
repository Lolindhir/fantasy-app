function Get-Config {

    # League Settings
    $SalaryRelevantTeamSize = 20
    $MaxTransactionWeek = 20
    $LeagueStatusSeasonStartBufferDays = 7

    # RapidAPI-Key für Tank01
    $RapidAPIKey = "cccff76c4bmsh01946acbc2d3c0bp141721jsn161bd86f4c69"
    $RapidAPIKeyAlt1 = "1e10165385msh4175f82e3d08e84p19fd3ejsn82f1e01c01aa"
    $RapidAPIKeyAlt2 = "3a3482fb66msh803287ddb5773dbp185f31jsnc6f1e236cd5e"

    # Point Settings
    $WeightTotal = 0.5
    $WeightGame = 0.5

    # File Locations
    $DataDir = "$PSScriptRoot\..\..\data"
    $BackupDir = Join-Path $DataDir "backup"
    $PlayersFile = Join-Path $DataDir "Players.json"
    $PlayersRelevantFile = Join-Path $DataDir "Players_Relevant.json"
    $PlayersRelevantChatDir = Join-Path $DataDir "chat\players-relevant"
    $LeagueFile = Join-Path $DataDir "League.json"
    $TeamsFile = Join-Path $DataDir "Teams.json"
    $ScheduleFile = Join-Path $DataDir "Schedule.json"
    $GamesFile = Join-Path $DataDir "Games.json"
    $StandingsFile = Join-Path $DataDir "Standings.json"
    $ManualTransactionsFile = Join-Path $DataDir "Transactions_Manual.json"
    $TransactionsFile = Join-Path $DataDir "Transactions.json"
    $TransactionsArchiveDir = Join-Path $DataDir "past_seasons\Transactions"
    $TransactionsFileHistoricalPrefix = Join-Path $TransactionsArchiveDir "Transactions_"
    $TransactionsFileHistoricalSuffix = ".json"
    $DraftsFile = Join-Path $DataDir "Drafts.json"
    $DraftsArchiveDir = Join-Path $DataDir "past_seasons\Drafts"
    $DraftsFileHistoricalPrefix = Join-Path $DraftsArchiveDir "Drafts_"
    $DraftsFileHistoricalSuffix = ".json"
    $TimestampsFile = Join-Path $DataDir "Timestamps.json"
    $ErrorsFile = Join-Path $DataDir "Errors.json"

    # Lade Metadata
    $metadataPath = Join-Path $DataDir "Metadata.json"

    if (-not (Test-Path $metadataPath)) {
        Write-Error "Metadata file not found at $metadataPath."
        throw "Metadata file not found."
    }

    $metadataContent = Get-Content $metadataPath -Raw | ConvertFrom-Json

    $ownerIDs = @{}
    $metadataContent.OwnerIDs.PSObject.Properties | ForEach-Object {
        $ownerIDs[$_.Name] = $_.Value
    }

    $DraftsConfig = $metadataContent.Drafts

    return @{
        LeagueYear                       = $metadataContent.LeagueYear
        SalaryRelevantTeamSize           = $SalaryRelevantTeamSize
        MaxTransactionWeek               = $MaxTransactionWeek
        LeagueStatusSeasonStartBufferDays = $LeagueStatusSeasonStartBufferDays
        LeagueID                         = $metadataContent.LeagueID
        CapDeadline                      = $metadataContent.CapDeadline
        OwnerIDs                         = $ownerIDs

        RapidAPIKey                      = $RapidAPIKey
        RapidAPIKeyAlt1                  = $RapidAPIKeyAlt1
        RapidAPIKeyAlt2                  = $RapidAPIKeyAlt2

        WeightTotal                      = $WeightTotal
        WeightGame                       = $WeightGame

        DataDir                          = $DataDir
        BackupDir                        = $BackupDir        
        LeagueFile                       = $LeagueFile
        TeamsFile                        = $TeamsFile
        ScheduleFile                     = $ScheduleFile
        GamesFile                        = $GamesFile
        StandingsFile                    = $StandingsFile

        PlayersFile                      = $PlayersFile
        PlayersRelevantFile              = $PlayersRelevantFile
        PlayersRelevantChatDir           = $PlayersRelevantChatDir

        ManualTransactionsFile           = $ManualTransactionsFile
        TransactionsFile                 = $TransactionsFile
        TransactionsArchiveDir           = $TransactionsArchiveDir
        TransactionsFileHistoricalPrefix = $TransactionsFileHistoricalPrefix
        TransactionsFileHistoricalSuffix = $TransactionsFileHistoricalSuffix

        DraftsConfig                     = $DraftsConfig
        DraftsFile                       = $DraftsFile
        DraftsArchiveDir                 = $DraftsArchiveDir
        DraftsFileHistoricalPrefix       = $DraftsFileHistoricalPrefix
        DraftsFileHistoricalSuffix       = $DraftsFileHistoricalSuffix

        TimestampsFile                   = $TimestampsFile
        ErrorsFile                       = $ErrorsFile
    }
}
