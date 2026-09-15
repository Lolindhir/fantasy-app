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

export interface WeeklyRecapWeek {
  Week: number;
  KeyGames: WeeklyRecapKeyGame[];
  KeyPlayers: WeeklyRecapKeyPlayer[];
}

export interface WeeklyRecapsReadModel {
  SchemaVersion: 1;
  Season: string;
  Weeks: WeeklyRecapWeek[];
}
