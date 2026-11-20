/** Read model of public/data/PlayerInjuryHistory.json (Issue #1590). Display only; nothing is derived here. */
export type PlayerAvailabilityState =
  | 'played'
  | 'not-played-reported'
  | 'not-played-reserve'
  | 'not-played-unexplained'
  | 'bye'
  | 'unknown';

export interface PlayerInjuryReportEntry {
  Game: string | null;
  Practice: string | null;
  Reasons: string[];
}

export interface PlayerInjuryHistoryWeek {
  Week: number;
  GameType: string | null;
  Team: string | null;
  State: PlayerAvailabilityState;
  Participation: string | null;
  Report: PlayerInjuryReportEntry[] | null;
  Roster: { Status: string | null; Code: string | null } | null;
}

export interface PlayerInjuryHistorySeason {
  Season: number;
  Weeks: PlayerInjuryHistoryWeek[];
}

export interface PlayerInjuryHistoryPlayer {
  ID: string;
  Seasons: PlayerInjuryHistorySeason[];
}

export interface PlayerInjuryHistoryReadModel {
  ContractVersion: number;
  Product: string;
  Coverage: { Season: number; ReportsAvailable: boolean; RosterStatusAvailable: boolean; SnapCountsAvailable: boolean }[];
  Players: PlayerInjuryHistoryPlayer[];
}
