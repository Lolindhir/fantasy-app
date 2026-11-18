/** Read model of public/data/SeasonStatistics.json and past_seasons/SeasonStatistics (Issue #506). Display only; nothing is derived here. */
export interface SeasonStatisticsTeam {
  TeamID: number;
  Owner: string;
  TeamName: string;
  Games: number;
  Wins: number;
  Losses: number;
  Ties: number;
  ExpectedWins: number | null;
  Luck: number | null;
  AllPlay: { Wins: number; Losses: number; Ties: number };
  OpponentTiming: number | null;
  UnderdogWins: number;
  UpsetLosses: number;
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
