// Central model import surface for Angular consumers.
//
// Draft, league/team and player model declarations live in dedicated core model
// files. DataService imports those model declarations directly while its loading
// and mapping responsibilities are split in later refactor slices.

export type {
  RawDraft,
  DraftSettings,
  DraftPickTradeHistoryEntry,
  DraftPick
} from './draft.models';

export type {
  DataTimestamps,
  PlayoffTeam,
  RegularSeasonTeam,
  AwardType,
  RawAward,
  Award,
  AwardInStanding,
  Standing,
  RawLeague,
  League,
  Placement,
  PlacementRegularSeason,
  PlacementRegularSeasonAllTime,
  PlacementPlayoffs,
  PlacementPlayoffsAllTime,
  Placements,
  RawFantasyTeam,
  FantasyTeam
} from './league.models';

export type {
  InjuryDetails,
  RankingEntry,
  PointHistorySeason,
  PointHistory,
  PlayerStats,
  GameHistory,
  GameDetails,
  PassingStats,
  RushingStats,
  ReceivingStats,
  KickingStats,
  FreeAgentPredictionModel,
  FreeAgentSalaryMode,
  FreeAgentMarketStatus,
  FreeAgentMarketInfo,
  RawPlayer,
  Player,
  RawNFLTeam,
  NFLTeam,
  TopPlayersSalaryResult,
  SortField
} from './player.models';
