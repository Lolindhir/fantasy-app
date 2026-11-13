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

/** One slot of a team's optimal (best possible) lineup of a week, as published by the generator. */
export interface WeeklyRecapOptimalSlot {
  SlotID: string;
  /** Sleeper PlayerID of the App contract; null when the weekly roster does not know the player. */
  PlayerID: string | null;
  CanonicalPlayerID: string | null;
  Points: number;
}

/** Lineup efficiency of one team and week (generator values; the frontend only displays them). */
export interface WeeklyRecapTeamPerformance {
  FantasyTeamID: number;
  ActualStarterPoints: number;
  PotentialPoints: number;
  MissedPoints: number;
  EfficiencyPercent: number | null;
  OptimalLineup: WeeklyRecapOptimalSlot[];
}

/** Season lineup efficiency of one team: sum(Actual) / sum(Potential) over the weeks counted in `Weeks`. */
export interface WeeklyRecapSeasonEfficiency {
  FantasyTeamID: number;
  ActualStarterPoints: number;
  PotentialPoints: number;
  MissedPoints: number;
  EfficiencyPercent: number | null;
  Weeks: number;
}

/** Pregame win chance (whole percent, generator values) of one matchup before the week; null when a projection was missing. */
export interface WeeklyRecapWinProbability {
  FantasyMatchupID: string;
  Teams: Array<{ FantasyTeamID: string | number; PregameWinProbability: number | null }>;
  /** True when the winner had less than 35 percent before the week; null when unknown or tied. */
  Upset: boolean | null;
  UpsetWinnerFantasyTeamID: string | number | null;
  /**
   * Generator mark of the winner: `upset` below 35 percent, `underdog` from 35 up to 50 percent before the week, otherwise null
   * (also unknown chance and ties). The thresholds belong to win-prob-v1; absent in older files.
   */
  UpsetLevel?: 'upset' | 'underdog' | null;
  /** The winner of a matchup with an UpsetLevel; absent in older files. */
  UnderdogWinnerFantasyTeamID?: string | number | null;
}

/** Upsets of one team over the weeks with a known pregame chance (generator values). */
export interface WeeklyRecapUpsetCount {
  FantasyTeamID: string | number;
  Upsets: number;
  Weeks: number;
}

export interface WeeklyRecapWeek {
  Week: number;
  KeyGames: WeeklyRecapKeyGame[];
  KeyPlayers: WeeklyRecapKeyPlayer[];
  /** Optional for compatibility with season archives generated before team awards. */
  TeamAwards?: WeeklyRecapTeamAwards;
  /** Lineup efficiency per team; null when the week has no team-week-performance partition, absent in older files. */
  TeamPerformance?: WeeklyRecapTeamPerformance[] | null;
  /** Pregame win chance and upset flag per matchup; absent in older files. */
  WinProbabilities?: WeeklyRecapWinProbability[];
}

export interface WeeklyRecapsReadModel {
  SchemaVersion: 1;
  Season: string;
  Weeks: WeeklyRecapWeek[];
  /** Absent in files generated before lineup efficiency. */
  SeasonEfficiency?: WeeklyRecapSeasonEfficiency[];
  /** Upset counts per team; absent in older files. */
  UpsetCounts?: WeeklyRecapUpsetCount[];
}
