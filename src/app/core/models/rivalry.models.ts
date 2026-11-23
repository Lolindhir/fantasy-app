/** Rivalry.json: App delivery of the Shared Derived product league-rivalry (ADR-083). Counting and bracket classification are generator-owned. */
export type RivalryFilter = 'all' | 'regular' | 'playoffs';
export type RivalryOutcome = 'win' | 'loss' | 'tie';

export interface RawRivalryGame {
  Season: string;
  Week: number;
  FantasyMatchupID: string;
  Stage: string;
  Bracket: string | null;
  Outcome: RivalryOutcome;
  TeamPoints: number | null;
  OpponentPoints: number | null;
  Margin: number | null;
}

export interface RawRivalryRecord {
  TeamID: number;
  OpponentID: number;
  Filter: RivalryFilter;
  Wins: number;
  Losses: number;
  Ties: number;
  PointsFor: number;
  PointsAgainst: number;
  BiggestWinMatchupID: string | null;
  ClosestLossMatchupID: string | null;
  /** Counted duels, oldest first. */
  Games: RawRivalryGame[];
}

/** Record of one team against one opponent in one season (contract version 2, Issue #1659); the single games stay in Records. */
export interface RawRivalrySeasonRecord {
  Season: string;
  TeamID: number;
  OpponentID: number;
  Filter: RivalryFilter;
  Wins: number;
  Losses: number;
  Ties: number;
  PointsFor: number;
  PointsAgainst: number;
}

export interface RivalryReadModel {
  SchemaVersion: number;
  Product: string;
  CanonicalLeagueID: string;
  Seasons: Array<{ Season: string }>;
  Records: RawRivalryRecord[];
  /** Absent in files published before contract version 2. */
  SeasonRecords?: RawRivalrySeasonRecord[];
}
