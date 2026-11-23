/** Read model of public/data/PlayerAwardHistory.json (Issue #499). Display only; nothing is counted or selected here. */
export type PlayerAwardKey = 'MVP' | 'MatchupHero' | 'Heartbreaker' | 'UnsungHero';

export interface PlayerAwardHistoryEntry {
  Season: number;
  Week: number;
  Award: PlayerAwardKey;
  FantasyTeamID?: number | null;
  Points?: number | null;
}

export interface PlayerAwardHistoryPlayer {
  PlayerID: string;
  Name: string;
  Position: string | null;
  Picture?: string | null;
  Counts: Record<PlayerAwardKey, number>;
  Total: number;
  Entries: PlayerAwardHistoryEntry[];
}

export interface PlayerAwardLeader {
  PlayerID: string;
  Name: string;
  Position: string | null;
  Count: number;
}

/** Per-season ranking row; Name, Position and Picture come from the top-level Players list. */
export interface PlayerAwardSeasonRanking {
  PlayerID: string;
  Counts: Record<PlayerAwardKey, number>;
  Total: number;
}

export interface PlayerAwardHistoryReadModel {
  SchemaVersion: number;
  Awards: PlayerAwardKey[];
  /** Players (per-season ranking) is absent in files generated before the Stats > Player Awards extension. */
  Seasons: Array<{ Season: number; Weeks: number[]; Players?: PlayerAwardSeasonRanking[] }>;
  /** Absent in files generated before the Hall of Fame extension. */
  Leaders?: Partial<Record<PlayerAwardKey, PlayerAwardLeader[]>>;
  Players: PlayerAwardHistoryPlayer[];
}
