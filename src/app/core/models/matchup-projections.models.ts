export type MatchupProjectionState = 'available' | 'partial' | 'unavailable';

export interface MatchupProjectionRange {
  Level: number;
  Lower: number;
  Upper: number;
}

export interface MatchupProjectionAxis {
  Min: number;
  Max: number;
  Step: number;
}

export interface MatchupProjectionTeam {
  FantasyTeamID: string | number;
  State: MatchupProjectionState;
  StarterCount: number;
  ResolvedStarterCount: number;
  FinalStarterCount: number;
  ScoredPoints: number;
  PregameProjectedScore: number | null;
  ProjectedFinalScore: number | null;
  /** Optional season-to-date baseline, never a replacement for the complete-lineup forecast. */
  BestBallEfficiencyFallback?: {
    Points: number;
    Method: string;
    SourceThroughWeek: number;
    ProjectedBestBallPoints: number;
    ManagerEfficiencyPercent: number;
    /** Sample SD of completed weekly actual fantasy team scores, not a calibrated projection interval. */
    ScoreStandardDeviation?: number | null;
    ScoreVolatilityGames?: number;
    ScoreVolatilityMethod?: string;
  } | null;
  /** Published display choice; unchanged legacy snapshots omit this additive field. */
  DisplayProjectedScore?: number | null;
  DisplayProjectionMethod?: string | null;
  StandardDeviation: number | null;
  Ranges: MatchupProjectionRange[];
  ByeStarterPlayerIDs: string[];
  OutStarterPlayerIDs: string[];
  UncertainStarterPlayerIDs: string[];
  UnavailableStarterPlayerIDs: string[];
  /** Whole-percent win chance of the matchup (win-prob-v1); the two teams add up to 100; null when a projection is missing. Absent in older files. */
  WinProbability?: number | null;
  /** Additive unrounded probability as a fraction from 0 to 1, computed for each side independently. */
  WinProbabilityRaw?: number | null;
  /** True only when neither team has modeled scoring variance; null when a chance is unavailable. */
  WinProbabilityIsDeterministic?: boolean | null;
  /** Display-only chance, preserving the original complete-lineup WinProbability contract. */
  DisplayWinProbability?: number | null;
  DisplayWinProbabilityRaw?: number | null;
  DisplayWinProbabilityIsDeterministic?: boolean | null;
  DisplayWinProbabilityBasis?: 'lineup' | 'season-bestball-efficiency-estimate' | null;
}

export interface MatchupProjectionMatchup {
  FantasyMatchupID: string;
  Teams: MatchupProjectionTeam[];
  Axis: MatchupProjectionAxis | null;
}

export interface MatchupProjectionMethod {
  Id: string;
  Levels: number[];
  SigmaBasisLevel: number;
  Assumption: string;
  ParticipationCondition: string;
}

export interface MatchupProjectionsReadModel {
  SchemaVersion: number;
  CanonicalLeagueID: string;
  Season: number;
  Week: number;
  DisplayLevel: number;
  Method: MatchupProjectionMethod;
  WinProbabilityModel?: string;
  BestBallFallbackMethod?: string;
  BestBallFallbackVolatilityMethod?: string;
  Matchups: MatchupProjectionMatchup[];
}
