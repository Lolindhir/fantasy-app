// Central model import surface for Angular consumers.
//
// This file intentionally re-exports the current DataService model types as a
// first migration step. The source definitions still live in data-service.ts for
// compatibility; future refactors can move the declarations here without forcing
// feature components to change their import paths again.

import '../../services/data-service';

declare module '../../services/data-service' {
  interface RawDraft {
    DisplayStatus: string;
  }
}

export type {
  DataTimestamps,
  RawDraft,
  DraftSettings,
  DraftPickTradeHistoryEntry,
  DraftPick,
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
