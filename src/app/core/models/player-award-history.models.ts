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

export interface PlayerAwardHistoryReadModel {
  SchemaVersion: number;
  Awards: PlayerAwardKey[];
  Seasons: Array<{ Season: number; Weeks: number[] }>;
  /** Absent in files generated before the Hall of Fame extension. */
  Leaders?: Partial<Record<PlayerAwardKey, PlayerAwardLeader[]>>;
  Players: PlayerAwardHistoryPlayer[];
}
