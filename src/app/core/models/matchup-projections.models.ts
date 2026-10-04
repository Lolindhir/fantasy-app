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
  StandardDeviation: number | null;
  Ranges: MatchupProjectionRange[];
  ByeStarterPlayerIDs: string[];
  UnavailableStarterPlayerIDs: string[];
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
  Matchups: MatchupProjectionMatchup[];
}
