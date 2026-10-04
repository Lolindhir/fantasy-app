export type PlayerWeekFantasyProjectionStatus =
  | 'available'
  | 'insufficient-history'
  | 'no-game'
  | 'unavailable';

export type PlayerWeekFantasyActualState = 'pending' | 'live' | 'final' | 'unavailable';

export interface PlayerWeekFantasyPredictionRange {
  Level: number;
  Lower: number;
  Upper: number;
}

export interface PlayerWeekFantasyProjection {
  AvailabilityAdjustmentApplied: boolean;
  HistoryGames: number;
  IntervalModel: string;
  ParticipationCondition: string;
  PointModel: string;
  Points: number | null;
  PredictionRange: PlayerWeekFantasyPredictionRange | null;
  PredictionRanges: PlayerWeekFantasyPredictionRange[];
  RangeQuality: string;
  Status: PlayerWeekFantasyProjectionStatus;
}

export interface PlayerWeekFantasyActual {
  Points: number | null;
  State: PlayerWeekFantasyActualState;
}

export interface PlayerWeekFantasyRecord {
  PlayerID: string | null;
  CanonicalPlayerID: string;
  Projection: PlayerWeekFantasyProjection;
  Actual: PlayerWeekFantasyActual;
}

export interface PlayerWeekFantasyScoringProfile {
  ActiveSettingsCount: number;
  FingerprintVersion: number;
  Season: number;
  SettingsHash: string;
}

export interface PlayerWeekFantasyIdentityCoverage {
  Provider: string;
  ResolvedRecordCount: number;
  UnavailableRecordCount: number;
}

export interface PlayerWeekFantasyRangeAxis {
  Min: number;
  Max: number;
}

export interface PlayerWeekFantasyDisplay {
  RangeLevel: number;
  RangeAxis: PlayerWeekFantasyRangeAxis | null;
}

export interface PlayerWeekFantasyReadModel {
  SchemaVersion: number;
  CanonicalLeagueID: string;
  Season: number;
  Week: number;
  ScoringProfile: PlayerWeekFantasyScoringProfile;
  IdentityCoverage: PlayerWeekFantasyIdentityCoverage;
  Display?: PlayerWeekFantasyDisplay;
  Records: PlayerWeekFantasyRecord[];
}
