// Central model import surface for Angular consumers.
//
// Draft model declarations already live in dedicated core model files. The other
// model declarations are still re-exported from data-service.ts as an intermediate
// migration step while DataService is split into smaller responsibilities.

import '../../services/data-service';

declare module '../../services/data-service' {
  interface RawDraft {
    DisplayStatus: string;
  }
}

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
  FantasyTeam,
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
} from '../../services/data-service';
