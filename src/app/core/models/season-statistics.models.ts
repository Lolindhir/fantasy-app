/** Read model of public/data/SeasonStatistics.json and past_seasons/SeasonStatistics (Issue #506). Display only; nothing is derived here. */
export interface SeasonStatisticsTeam {
  TeamID: number;
  Owner: string;
  TeamName: string;
  Games: number;
  Wins: number;
  Losses: number;
  Ties: number;
  /** SchemaVersion 2 facts; absent in older files and null without a game. */
  PointDifferential?: number | null;
  PointsPerGame?: number | null;
  PointsAgainstPerGame?: number | null;
  ExpectedWins: number | null;
  Luck: number | null;
  AllPlay: { Wins: number; Losses: number; Ties: number };
  OpponentTiming: number | null;
  UnderdogWins: number;
  UpsetLosses: number;
  /** Abbreviation from the team name of that season, derived by the generator (Issue #1621). Absent in files published before it existed. */
  TeamAbbr?: string;
  /** Season mean, in percent. */
  LineupEfficiencyActual?: number | null;
  LineupEfficiencyProjected?: number | null;
  /** Season mean per game: points minus pregame projection. */
  ProjectionDelta?: number | null;
}

export interface SeasonStatisticsUpset {
  Week: number;
  WinnerTeamID: number;
  LoserTeamID: number;
  WinnerPoints: number;
  LoserPoints: number;
  WinnerPregameWinProbability: number;
}

export interface SeasonStatisticsReadModel {
  Season: number;
  IsCompleted: boolean;
  Teams: SeasonStatisticsTeam[];
  BiggestUpset: SeasonStatisticsUpset | null;
  /** Chosen by the generator over all seasons (current file only). */
  BiggestUpsetAllTime?: (SeasonStatisticsUpset & { Season: number }) | null;
}
