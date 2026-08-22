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
    $LeagueFile = Join-Path $DataDir "League.json"
    $TeamsFile = Join-Path $DataDir "Teams.json"
    $ScheduleFile = Join-Path $DataDir "Schedule.json"
    $GamesFile = Join-Path $DataDir "Games.json"
    $StandingsFile = Join-Path $DataDir "Standings.json"
    $ManualTransactionsFile = Join-Path $DataDir "Transactions_Manual.json"
    $TransactionsFile = Join-Path $DataDir "Transactions.json"

    $PastSeasonsDir = Join-Path $DataDir "past_seasons"
    $PastSeasonsIndexFile = Join-Path $DataDir "PastSeasonsIndex.json"

    $TransactionsArchiveDir = Join-Path $PastSeasonsDir "Transactions"
    $TransactionsFileHistoricalPrefix = Join-Path $TransactionsArchiveDir "Transactions_"
    $TransactionsFileHistoricalSuffix = ".json"
    $DraftsFile = Join-Path $DataDir "Drafts.json"
    $DraftsArchiveDir = Join-Path $PastSeasonsDir "Drafts"
    $DraftsFileHistoricalPrefix = Join-Path $DraftsArchiveDir "Drafts_"
    $DraftsFileHistoricalSuffix = ".json"

    $PastSeasonPlayersFileHistoricalPrefix = Join-Path $PastSeasonsDir "Players_"
    $PastSeasonPlayersFileHistoricalSuffix = ".json"
    $PastSeasonGamesFileHistoricalPrefix = Join-Path $PastSeasonsDir "Games_"
    $PastSeasonGamesFileHistoricalSuffix = ".json"
    $PastSeasonScheduleFileHistoricalPrefix = Join-Path $PastSeasonsDir "Schedule_"
    $PastSeasonScheduleFileHistoricalSuffix = ".json"
    $PastSeasonStandingsFileHistoricalPrefix = Join-Path $PastSeasonsDir "Standings_"
    $PastSeasonStandingsFileHistoricalSuffix = ".json"
    $PastSeasonTeamsFileHistoricalPrefix = Join-Path $PastSeasonsDir "Teams_"
    $PastSeasonTeamsFileHistoricalSuffix = ".json"

    $PastSeasonResources = @(
        @{
            Key = "Drafts"
            Directory = $DraftsArchiveDir
            Prefix = "Drafts_"
            Suffix = ".json"
        },
        @{
            Key = "Transactions"
            Directory = $TransactionsArchiveDir
            Prefix = "Transactions_"
            Suffix = ".json"
        },
        @{
            Key = "Players"
            Directory = $PastSeasonsDir
            Prefix = "Players_"
            Suffix = ".json"
        },
        @{
            Key = "Games"
            Directory = $PastSeasonsDir
            Prefix = "Games_"
            Suffix = ".json"
        },
        @{
            Key = "Schedule"
            Directory = $PastSeasonsDir
            Prefix = "Schedule_"
            Suffix = ".json"
        },
        @{
            Key = "Standings"
            Directory = $PastSeasonsDir
            Prefix = "Standings_"
            Suffix = ".json"
        },
        @{
            Key = "Teams"
            Directory = $PastSeasonsDir
            Prefix = "Teams_"
            Suffix = ".json"
        }
    )

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
    $LeagueTimeZone = if ($metadataContent.PSObject.Properties.Name -contains "LeagueTimeZone") {
        [string]$metadataContent.LeagueTimeZone
    } else {
        "UTC"
    }

    return @{
        LeagueYear                       = $metadataContent.LeagueYear
        SalaryRelevantTeamSize           = $SalaryRelevantTeamSize
        MaxTransactionWeek               = $MaxTransactionWeek
        LeagueStatusSeasonStartBufferDays = $LeagueStatusSeasonStartBufferDays
        LeagueID                         = $metadataContent.LeagueID
        CapDeadline                      = $metadataContent.CapDeadline
        LeagueTimeZone                   = $LeagueTimeZone
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

        PastSeasonsDir                              = $PastSeasonsDir
        PastSeasonsIndexFile                        = $PastSeasonsIndexFile
        PastSeasonPlayersFileHistoricalPrefix       = $PastSeasonPlayersFileHistoricalPrefix
        PastSeasonPlayersFileHistoricalSuffix       = $PastSeasonPlayersFileHistoricalSuffix
        PastSeasonGamesFileHistoricalPrefix         = $PastSeasonGamesFileHistoricalPrefix
        PastSeasonGamesFileHistoricalSuffix         = $PastSeasonGamesFileHistoricalSuffix
        PastSeasonScheduleFileHistoricalPrefix      = $PastSeasonScheduleFileHistoricalPrefix
        PastSeasonScheduleFileHistoricalSuffix      = $PastSeasonScheduleFileHistoricalSuffix
        PastSeasonStandingsFileHistoricalPrefix     = $PastSeasonStandingsFileHistoricalPrefix
        PastSeasonStandingsFileHistoricalSuffix     = $PastSeasonStandingsFileHistoricalSuffix
        PastSeasonTeamsFileHistoricalPrefix         = $PastSeasonTeamsFileHistoricalPrefix
        PastSeasonTeamsFileHistoricalSuffix         = $PastSeasonTeamsFileHistoricalSuffix
        PastSeasonResources                         = $PastSeasonResources

        TimestampsFile                   = $TimestampsFile
        ErrorsFile                       = $ErrorsFile
    }
}
