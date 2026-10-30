# Data root directories (Issue #788, step 0). The only place in PowerShell that spells out the root names;
# tools/data_roots.py is the Python counterpart and tools/tests/test_data_roots.py keeps both in sync.
$script:DataSourceRootName = 'data-source'
$script:DataDerivedRootName = 'data-derived'
$script:DataMetaRootName = 'data-meta'

Import-Module "$PSScriptRoot\LeagueMetadataUtils.psm1" -ErrorAction Stop

function Get-DataSourceRoot {
    param([Parameter(Mandatory = $true)][string]$RepoRoot)
    return (Join-Path $RepoRoot $script:DataSourceRootName)
}

function Get-DataDerivedRoot {
    param([Parameter(Mandatory = $true)][string]$RepoRoot)
    return (Join-Path $RepoRoot $script:DataDerivedRootName)
}

function Get-DataMetaRoot {
    param([Parameter(Mandatory = $true)][string]$RepoRoot)
    return (Join-Path $RepoRoot $script:DataMetaRootName)
}

function Get-Config {

    # League Settings
    $MaxTransactionWeek = 20

    # File Locations
    $DataDir = "$PSScriptRoot\..\..\data"
    $RepoRootDir = Join-Path $PSScriptRoot "..\..\.."
    $DataSourceDir = Get-DataSourceRoot -RepoRoot $RepoRootDir
    $DataDerivedDir = Get-DataDerivedRoot -RepoRoot $RepoRootDir
    $DataMetaDir = Get-DataMetaRoot -RepoRoot $RepoRootDir
    $BackupDir = Join-Path $DataDir "backup"
    $PlayersFile = Join-Path $DataDir "Players.json"
    $LeagueFile = Join-Path $DataDir "League.json"
    $DecisionWindowsFile = Join-Path $DataDir "DecisionWindows.json"
    $MatchupsFile = Join-Path $DataDir "Matchups.json"
    $WeeklyRecapsFile = Join-Path $DataDir "WeeklyRecaps.json"
    $TeamsFile = Join-Path $DataDir "Teams.json"
    $ScheduleFile = Join-Path $DataDir "Schedule.json"
    $StandingsFile = Join-Path $DataDir "Standings.json"
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
    $MatchupsArchiveDir = Join-Path $PastSeasonsDir "Matchups"
    $MatchupsFileHistoricalPrefix = Join-Path $MatchupsArchiveDir "Matchups_"
    $MatchupsFileHistoricalSuffix = ".json"
    $WeeklyRecapsArchiveDir = Join-Path $PastSeasonsDir "WeeklyRecaps"
    $WeeklyRecapsFileHistoricalPrefix = Join-Path $WeeklyRecapsArchiveDir "WeeklyRecaps_"
    $WeeklyRecapsFileHistoricalSuffix = ".json"

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
            Key = "Matchups"
            Directory = $MatchupsArchiveDir
            Prefix = "Matchups_"
            Suffix = ".json"
        },
        @{
            Key = "WeeklyRecaps"
            Directory = $WeeklyRecapsArchiveDir
            Prefix = "WeeklyRecaps_"
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

    # Lade Liga-Metadaten (data-meta/<CanonicalLeagueID>/metadata.json, ADR-054, Issue #986).
    # The generators still work on exactly one league; more than one league needs an explicit selection first.
    $leagueIds = @(Get-LeagueMetadataIds -Root $DataMetaDir)
    if ($leagueIds.Count -ne 1) {
        throw "Expected exactly one league under $DataMetaDir but found $($leagueIds.Count) ($($leagueIds -join ', ')); generator league selection is not implemented."
    }
    $CanonicalLeagueID = [string]$leagueIds[0]
    # Hand-maintained manual transaction overlay of the league (Issue #999 step 5c).
    $ManualTransactionsFile = Join-Path (Join-Path $DataMetaDir $CanonicalLeagueID) "transactions-manual.json"
    $metadataContent = Get-LeagueMetadata -LeagueId $CanonicalLeagueID -Root $DataMetaDir

    # LeagueYear is canonical in the League source manifest, not hand-maintained.
    $manifestPath = Join-Path (Join-Path (Join-Path $DataSourceDir "leagues") $CanonicalLeagueID) "manifest.json"
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
        throw "League source manifest not found at $manifestPath."
    }
    $manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $currentSeasonId = [string]$manifest.CurrentCanonicalLeagueSeasonID
    if ($currentSeasonId -notmatch "^$([regex]::Escape($CanonicalLeagueID))-(?<season>[0-9]{4})$") {
        throw "League source manifest of $CanonicalLeagueID has no valid CurrentCanonicalLeagueSeasonID ('$currentSeasonId')."
    }
    $LeagueYear = [int]$Matches['season']

    # CapDeadline and its buffer are mandatory for the current season (the loader fails closed otherwise).
    $seasonEntry = Get-LeagueSeasonEntry -Metadata $metadataContent -Season $LeagueYear
    if ($seasonEntry.PSObject.Properties.Name -notcontains "CapDeadline") {
        throw "League metadata of $CanonicalLeagueID has no CapDeadline for the current season $LeagueYear."
    }

    $ownerIDs = @{}
    $metadataContent.Owners.PSObject.Properties | ForEach-Object {
        $ownerIDs[$_.Name] = $_.Value
    }

    $DraftsConfig = $metadataContent.Drafts
    $LeagueTimeZone = [string]$metadataContent.LeagueTimeZone

    return @{
        CanonicalLeagueID                = $CanonicalLeagueID
        LeagueYear                       = $LeagueYear
        MaxTransactionWeek               = $MaxTransactionWeek
        LeagueID                         = [string]$metadataContent.CurrentProviderLeagueID
        CapDeadline                      = $seasonEntry.CapDeadline
        CapDeadlineBufferDays            = [int]$seasonEntry.CapDeadlineBufferDays
        LeagueTimeZone                   = $LeagueTimeZone
        OwnerIDs                         = $ownerIDs


        DataDir                          = $DataDir
        DataSourceDir                    = $DataSourceDir
        DataDerivedDir                   = $DataDerivedDir
        DataMetaDir                      = $DataMetaDir
        BackupDir                        = $BackupDir
        LeagueFile                       = $LeagueFile
        DecisionWindowsFile              = $DecisionWindowsFile
        MatchupsFile                     = $MatchupsFile
        WeeklyRecapsFile                 = $WeeklyRecapsFile
        TeamsFile                        = $TeamsFile
        ScheduleFile                     = $ScheduleFile
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
        MatchupsArchiveDir               = $MatchupsArchiveDir
        MatchupsFileHistoricalPrefix     = $MatchupsFileHistoricalPrefix
        MatchupsFileHistoricalSuffix     = $MatchupsFileHistoricalSuffix
        WeeklyRecapsArchiveDir           = $WeeklyRecapsArchiveDir
        WeeklyRecapsFileHistoricalPrefix = $WeeklyRecapsFileHistoricalPrefix
        WeeklyRecapsFileHistoricalSuffix = $WeeklyRecapsFileHistoricalSuffix

        PastSeasonsDir                              = $PastSeasonsDir
        PastSeasonsIndexFile                        = $PastSeasonsIndexFile
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
