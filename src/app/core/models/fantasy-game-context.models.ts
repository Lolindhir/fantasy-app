export type FantasyGameContextScoringState = 'pending' | 'partial' | 'final';
export type FantasyGameImpactState = 'unavailable' | 'partial' | 'final';

export interface FantasyGameContextDecisionWindow {
  DecisionWindowID: string;
  StartsAtUtc: string;
  GameIDs: string[];
}

export interface FantasyGameContextPlayer {
  PlayerID: string;
  IsStarter: boolean;
  Points: number | null;
}

export interface FantasyGameContextTeam {
  FantasyTeamID: string | number;
  FantasyMatchupID: string;
  RosteredPlayerCount: number;
  StarterCount: number;
  RosteredPoints: number;
  StarterPoints: number;
  Players: FantasyGameContextPlayer[];
}

export interface FantasyGameRelevance {
  RosteredPlayerCount: number;
  StarterCount: number;
  FantasyTeamCount: number;
  FantasyMatchupCount: number;
  UnknownAssociationCount: number;
}

export interface FantasyGameImpact {
  State: FantasyGameImpactState;
  RosteredPoints: number | null;
  StarterPoints: number | null;
  OutcomeSwingMatchupCount: number;
}

export interface FantasyGameContextGame {
  GameID: string;
  DecisionWindowID: string;
  StartsAtUtc: string;
  AwayTeamID: string;
  AwayTeamAbbr: string | null;
  HomeTeamID: string;
  HomeTeamAbbr: string | null;
  Status: string | null;
  Relevance: FantasyGameRelevance;
  Impact: FantasyGameImpact;
  FantasyTeams: FantasyGameContextTeam[];
}

export interface FantasyGameContextCounterfactualScore {
  Left: number;
  Right: number;
}

export interface FantasyGameContextMatchupGame {
  GameID: string;
  DecisionWindowID: string;
  StartsAtUtc: string;
  LeftStarterCount: number;
  RightStarterCount: number;
  LeftRosteredPlayerCount: number;
  RightRosteredPlayerCount: number;
  LeftStarterPoints: number;
  RightStarterPoints: number;
  StarterPointDelta: number;
  OutcomeChangedWithoutGame: boolean | null;
  ScoreWithoutGame: FantasyGameContextCounterfactualScore | null;
}

export interface FantasyGameContextMatchup {
  FantasyMatchupID: string;
  TeamIDs: Array<string | number>;
  FinalScores: FantasyGameContextCounterfactualScore | null;
  CounterfactualState:
    | 'available'
    | 'unavailable-custom-score'
    | 'unavailable-final-score'
    | 'unavailable-not-final';
  Games: FantasyGameContextMatchupGame[];
}

export interface FantasyGameContextNonGameAssociation {
  FantasyTeamID: string | number;
  FantasyMatchupID: string | null;
  PlayerID: string;
  NFLTeamID: string | null;
  IsStarter: boolean;
  Kind: string;
  Reason: string;
}

export interface FantasyGameContextReadModel {
  SchemaVersion: number;
  LeagueID: string | number;
  Season: string;
  Week: number;
  ScoringState: FantasyGameContextScoringState;
  DecisionWindows: FantasyGameContextDecisionWindow[];
  Games: FantasyGameContextGame[];
  FantasyMatchups: FantasyGameContextMatchup[];
  NonGameAssociations: FantasyGameContextNonGameAssociation[];
}

export interface HistoricalFantasyGameContextSeason {
  SchemaVersion: number;
  LeagueID: string | number;
  Season: string;
  ScoringState: 'final';
  Weeks: FantasyGameContextReadModel[];
}
