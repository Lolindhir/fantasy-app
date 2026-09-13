export type MatchupCompletionState = 'open' | 'final' | 'unknown';
export type MatchupStage = 'regular-season' | 'playoffs';
export type MatchupScoreKind = 'standard' | 'adjusted';
export type MatchupResultType = 'win' | 'tie';

export interface MatchupParticipant {
  TeamID: number;
  Points: number | null;
  ScoreKind: MatchupScoreKind;
}

export interface MatchupResult {
  Type: MatchupResultType;
  WinnerTeamID: number | null;
}

export interface FantasyMatchupReadModel {
  FantasyMatchupID: string;
  Participants: MatchupParticipant[];
  CompletionState: MatchupCompletionState;
  Result: MatchupResult | null;
}

export interface MatchupWeekReadModel {
  Week: number;
  Stage: MatchupStage;
  FirstKickoffUtc: string | null;
  CompletionState: MatchupCompletionState;
  Matchups: FantasyMatchupReadModel[];
}

export interface MatchupsSummary {
  LastCompletedWeek: number | null;
  ActiveOrNextWeek: number | null;
}

export interface MatchupsReadModel {
  SchemaVersion: 1;
  Season: string;
  Weeks: MatchupWeekReadModel[];
  Summary: MatchupsSummary;
}
