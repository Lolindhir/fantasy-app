import type { FantasyTeam } from './league.models';

export interface InjuryDetails {
  Date: string;
  ReturnDate: string;
  Description: string;
  Designation: string;
}

export interface RankingEntry {
  Type: 'Total' | 'PerGame' | 'Combined' | 'Total_Pos' | 'PerGame_Pos' | 'Combined_Pos' | 'Combined_Previous';
  Value: number;
}

export interface PointHistorySeason {
  Season: number;
  Total: number;
  AvgGame: number;
  AvgPotentialGame: number;
  GamesPlayed: number;
  PotentialGames: number;
}

export interface PointHistory {
  SeasonMinus1: PointHistorySeason;
  SeasonMinus2: PointHistorySeason;
  SeasonMinus3: PointHistorySeason;
}

export interface PlayerStats {
  GamesPlayed: number;
  GamesPotential: number;
  SnapsTotal: number;
  AttemptsTotal: number;
  TouchdownsTotal: number;
  TouchdownsPassing: number;
  TouchdownsReceiving: number;
  TouchdownsRushing: number;
  FantasyPointsTotal: number;
  FantasyPointsAvgGame: number;
  FantasyPointsAvgPotentialGame: number;
  FantasyPointsAvgSnap: number;
  FantasyPointsAvgAttempt: number;
  Ranking: RankingEntry[];
  PointHistory: PointHistory;
}

export interface GameHistory {
  GameID: string;
  TeamID: string;
  TeamAbv: string;
  GameDetails: GameDetails;
  FantasyPoints: number;
  SnapCount: number;
  SnapPercentage: number;
  Attempts: number;
  Passing?: PassingStats;
  Rushing?: RushingStats;
  Receiving?: ReceivingStats;
  Kicking?: KickingStats;
  /** Generator-owned projection of this game (PlayerWeekFantasy); null when no projection exists. Absent in older files. */
  Projection?: GameProjection | null;
}

/** Result against the projection, classified by the generator: met = points reach the projection (equal counts). */
export type GameProjectionResult = 'met' | 'missed';

export interface GameProjection {
  Points: number;
  /** Null while the game or its points are not final. */
  Result: GameProjectionResult | null;
}

export interface GameDetails {
  Week: number;
  WeekFinal: boolean;
  WeekPlayoff: boolean;
  WeekScored: boolean;
  Date: string;
  Home: string;
  HomeID: string;
  Away: string;
  AwayID: string;
  HomePoints: number;
  AwayPoints: number;
}

export interface PassingStats {
  QBRating: number | null;
  Rating: number;
  PassAttempts: number;
  PassAvg: number;
  PassTDs: number;
  PassYards: number;
  Interceptions: number;
  PassCompletions: number;
}

export interface RushingStats {
  RushAvg: number;
  RushYards: number;
  Carries: number;
  LongRush: number | null;
  RushTDs: number;
}

export interface ReceivingStats {
  Receptions: number;
  ReceptionTDs: number;
  LongReceptions: number | null;
  Targets: number;
  ReceptionYards: number;
  ReceptionAvg: number;
}

export interface KickingStats {
  KickingPts: number;
  FgLong: number;
  FgMade: number;
  FgAttempts: number;
  FgMissed: number;
  FgPct: number;
  XpMade: number;
  XpAttempts: number;
  XpMissed: number;
}

export type FreeAgentPredictionModel = 'CurrentOnly' | 'RuleBasedAutoCut';
export type FreeAgentSalaryMode = 'Current' | 'Projected';
export type FreeAgentMarketStatus = 'Rostered' | 'FreeAgent' | 'ProjectedCapCut' | 'PossibleCapCut';

export interface FreeAgentMarketInfo {
  Status: FreeAgentMarketStatus;
  StatusDisplay: string;
  PredictionModel: FreeAgentPredictionModel;
  SalaryMode: FreeAgentSalaryMode;
  Probability: number;
  Reason: string;
  TeamID?: number;
  TeamName?: string;
  Owner?: string;
  CutOrder?: number;
  SalaryRank?: number;
  SalaryUsed?: number;
  SalaryUsedDisplay?: string;
  CapLimit?: number;
  CapLimitDisplay?: string;
  CapBeforeCut?: number;
  CapBeforeCutDisplay?: string;
  CapAfterCut?: number;
  CapAfterCutDisplay?: string;
}

/** Salary of one league season (final player-valuation snapshot); null while the season or the player is not in a snapshot (never 0). */
export interface SalaryHistoryEntry {
  Season: number;
  Salary: number | null;
  /** Projection for the following season as of that season's final snapshot. */
  SalaryProjected: number | null;
  /** Generator-owned difference of Salary to the previous listed season; null when unknown or for the first season. */
  Change: number | null;
}

export interface RawPlayer {
  ID: string;
  Name: string;
  NameFirst: string;
  NameLast: string;
  NameShort: string;
  Position: string;
  IsFreeAgent: boolean;
  Salary: number;
  SalaryProjected: number;
  /** Salary per league season, oldest first; absent in older files. */
  SalaryHistory?: SalaryHistoryEntry[] | null;
  /** Generator-owned SalaryProjected minus Salary of the current season; null when unknown. */
  SalaryProjectedDelta?: number | null;
  Age: number;
  Year: number;
  Picture: string;
  /** Large headshot rendition for detail and desktop portraits; absent until the next Players refresh. */
  PictureLarge?: string | null;
  Number: string;
  FantasyPros: string;
  ESPN: string;
  SleeperDepthChartPosition?: string | null;
  SleeperDepthChartOrder?: number | null;
  College: string;
  HighSchool: string;
  Injured: boolean;
  InjuryDetails: InjuryDetails;
  TeamID: string;
  GamesPlayed: number;
  GamesPotential: number;
  SnapsTotal: number;
  AttemptsTotal: number;
  FantasyPointsTotal: number;
  FantasyPointsAvgGame: number;
  FantasyPointsAvgPotentialGame: number;
  FantasyPointsAvgSnap: number;
  FantasyPointsAvgAttempt: number;
  TouchdownsTotal: number;
  TouchdownsPassing: number;
  TouchdownsReceiving: number;
  TouchdownsRushing: number;
  Ranking: RankingEntry[];
  PointHistory: PointHistory;
  GameHistory?: GameHistory[];
}

export interface Player extends Omit<RawPlayer, 'TeamID' | 'GamesPlayed' | 'GamesPotential' | 'FantasyPointsTotal' | 'FantasyPointsAvgGame' | 'FantasyPointsAvgPotentialGame' | 'FantasyPointsAvgSnap' | 'FantasyPointsAvgAttempt' | 'TouchdownsTotal' | 'TouchdownsPassing' | 'TouchdownsReceiving' | 'TouchdownsRushing' | 'Ranking' | 'PointHistory'> {
  TeamNFL: NFLTeam;
  TeamFantasy?: FantasyTeam;
  IsFantasyFreeAgent: boolean;
  IsFreeAgentDraftAvailable: boolean;
  FreeAgentMarketInfo: FreeAgentMarketInfo;
  IsFreeAgentDraftAvailableProjected: boolean;
  FreeAgentMarketInfoProjected: FreeAgentMarketInfo;
  SalaryDisplay: string;
  SalaryProjectedDisplay: string;
  Stats: PlayerStats;
  GameHistoryFull?: GameHistory[];
}

export interface RawNFLTeam {
  ID: string;
  Name: string;
  Abv: string;
  Logo: string;
  /** Former numeric app team IDs; generated data may still reference them (#347 F3). */
  LegacyIDs?: string[];
}

export interface NFLTeam extends RawNFLTeam {}

export interface TopPlayersSalaryResult {
  cap: number;
  topPlayers: Player[];
}

export type SortField = keyof Player;
