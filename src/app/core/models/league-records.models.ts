import type { SeasonStatisticsUpset } from './season-statistics.models';

/** App delivery of the persisted Shared Derived league-records product (ADR-100). */
export interface LeagueRecordUpset extends SeasonStatisticsUpset {
  Season: number;
  WinnerCanonicalLeagueRosterID: string;
  LoserCanonicalLeagueRosterID: string;
}

export interface LeagueRecordCoverage {
  Season: number;
  SourceSchemaVersion: number;
  Models: Record<string, string>;
  AsOf: { LeagueScoredWeek: number; CompletedWeeks: number };
  RegularSeasonGames: number;
  KnownChanceGamesByTeam: Array<{ TeamID: number; KnownChanceGames: number }>;
  UpsetWinProbability: number;
}

export interface LeagueRecordsReadModel {
  SchemaVersion: number;
  Product: string;
  CanonicalLeagueID: string;
  Model: string;
  Coverage: LeagueRecordCoverage[];
  Records: { BiggestUpset: LeagueRecordUpset | null };
}
