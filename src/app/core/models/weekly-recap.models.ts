export interface WeeklyRecapKeyGame {
  GameID: string;
  KickoffUtc: string;
  AwayNFLTeamID: string | number;
  HomeNFLTeamID: string | number;
  AwayScore: number | null;
  HomeScore: number | null;
  StarterPoints: number;
  StarterCount: number;
  FantasyTeamIDs: Array<string | number>;
  FantasyMatchupIDs: string[];
}

export interface WeeklyRecapKeyPlayer {
  PlayerID: string;
  FantasyTeamID: string | number;
  NFLTeamID: string | number;
  Position: string;
  Points: number;
}

export interface WeeklyRecapBestManager {
  CanonicalLeagueRosterID: string;
  FantasyTeamID: string | number;
  PotentialPoints: number;
}

export interface WeeklyRecapBestCoach extends WeeklyRecapBestManager {
  EfficiencyPercent: number;
  ActualStarterPoints: number;
  MissedPoints: number;
}

export interface WeeklyRecapTeamAwards {
  State: 'available' | 'unavailable';
  BestManager: WeeklyRecapBestManager[];
  BestCoach: WeeklyRecapBestCoach[];
}

export interface WeeklyRecapWeek {
  Week: number;
  KeyGames: WeeklyRecapKeyGame[];
  KeyPlayers: WeeklyRecapKeyPlayer[];
  /** Optional for compatibility with season archives generated before team awards. */
  TeamAwards?: WeeklyRecapTeamAwards;
}

export interface WeeklyRecapsReadModel {
  SchemaVersion: 1;
  Season: string;
  Weeks: WeeklyRecapWeek[];
}
