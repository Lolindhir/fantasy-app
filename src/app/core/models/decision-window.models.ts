export type DecisionWindowEvaluationState =
  | 'ready'
  | 'review'
  | 'action-required'
  | 'pending'
  | 'unknown';

export type DecisionWindowFantasyContextState = 'available' | 'pending';

export interface DecisionWindowGame {
  GameID: string;
  Week: number;
  AwayTeamID: string;
  AwayTeamAbbr: string | null;
  HomeTeamID: string;
  HomeTeamAbbr: string | null;
}

export interface DecisionWindowAffectedPlayer {
  PlayerID: string;
  NFLTeamID: string | null;
  GameID: string;
  IsStarter: boolean;
}

export interface DecisionWindowAffectedFantasyTeam {
  FantasyTeamID: number;
  AffectedRosteredPlayerCount: number;
  AffectedStarterCount: number;
  Players: DecisionWindowAffectedPlayer[];
}

export interface DecisionWindow {
  DecisionWindowID: string;
  Week: number;
  StartsAtUtc: string;
  Games: DecisionWindowGame[];
  ParticipatingNFLTeamIDs: string[];
  FantasyContextState: DecisionWindowFantasyContextState;
  AffectedFantasyTeams: DecisionWindowAffectedFantasyTeam[];
}

export type DecisionWindowPlayerLockKind = 'scheduled' | 'bye' | 'no-team' | 'unknown';

export interface DecisionWindowPlayerLockFact {
  FantasyTeamID: number;
  PlayerID: string;
  NFLTeamID: string | null;
  Kind: DecisionWindowPlayerLockKind;
  GameID: string | null;
  DecisionWindowID: string | null;
  StartsAtUtc: string | null;
  IsStarter: boolean;
}

export interface DecisionWindowIssue {
  Code: string;
  State: Exclude<DecisionWindowEvaluationState, 'ready' | 'pending'>;
  PlayerID: string | null;
  Count: number | null;
}

export interface DecisionWindowTeamLineupEvaluation {
  FantasyTeamID: number;
  State: Exclude<DecisionWindowEvaluationState, 'pending'>;
  ExpectedStarterCount: number;
  StarterCount: number;
  OpenStarterSlots: number;
  Issues: DecisionWindowIssue[];
}

export type FantasyRelevanceRosterPlacement = 'starter' | 'bench' | 'ir' | 'taxi';
export type FantasyRelevanceGameState = 'unlocked' | 'locked-active' | 'completed' | 'unknown';
export type FantasyRelevanceRepairabilityState = 'repairable' | 'irreparable' | 'unknown';
export type FantasyRelevanceRepairabilityPath = 'internal-roster' | 'external-acquisition';
export type FantasyRelevanceRepairabilityProblemCode = 'OPEN_STARTER_SLOT' | 'STARTER_ON_BYE' | 'STARTER_UNAVAILABLE';
export type FantasyRelevanceRemainingScoringPathState = 'open' | 'none' | 'unknown';
export type FantasyRelevanceRepairabilityReasonCode =
  | 'INTERNAL_ASSIGNMENT_AVAILABLE'
  | 'EXTERNAL_ACQUISITION_ASSIGNMENT_AVAILABLE'
  | 'LINEUP_EVIDENCE_UNKNOWN'
  | 'ACQUISITION_EVIDENCE_UNKNOWN'
  | 'EXTERNAL_PLAYER_EVIDENCE_UNKNOWN'
  | 'NO_LEGAL_REPAIR_PATH';

export interface FantasyRelevanceSlotRepairability {
  ProblemCode: FantasyRelevanceRepairabilityProblemCode;
  State: FantasyRelevanceRepairabilityState;
  Path: FantasyRelevanceRepairabilityPath | null;
  ReasonCode: FantasyRelevanceRepairabilityReasonCode;
  InternalCandidateCount: number;
  ExternalCandidateCount: number;
}

export type ScoringAvailabilityState = 'available' | 'uncertain' | 'unavailable' | 'unknown';

export interface ScoringAvailabilityObservation {
  State: ScoringAvailabilityState;
  Reason: string;
  Source: 'ESPN';
  Provider: string;
  ProviderPlayerID: string;
  ProviderStatus: string;
  ProviderDate: string | null;
}

export interface FantasyRelevanceSlotDefinition {
  SlotID: string;
  SlotType: string;
  SlotOrdinal: number;
  SlotIndex: number;
}

export interface FantasyRelevanceSlotState extends FantasyRelevanceSlotDefinition {
  CurrentStarterID: string | null;
  State: FantasyRelevanceGameState;
  GameID: string | null;
  DecisionWindowID: string | null;
  StartsAtUtc: string | null;
  ScoringAvailability?: ScoringAvailabilityObservation | null;
  Repairability?: FantasyRelevanceSlotRepairability | null;
}

export interface FantasyRelevancePlayerState {
  PlayerID: string;
  Placement: FantasyRelevanceRosterPlacement;
  Position: string | null;
  GameState: FantasyRelevanceGameState;
  GameID: string | null;
  DecisionWindowID: string | null;
  StartsAtUtc: string | null;
  ScoringAvailability?: ScoringAvailabilityObservation | null;
  LineupSlotID: string | null;
  LineupSlotType: string | null;
  EligibleUnlockedSlotIDs: string[];
  IsBenchCandidate: boolean;
  HasDirectScoringPath: boolean;
  HasAlternativePath: boolean;
}

export interface FantasyRelevanceTeamState {
  FantasyTeamID: string | number;
  ActiveRosterPlayerCount: number;
  StarterCount: number;
  BenchCount: number;
  IRCount: number;
  TaxiCount: number;
  UnlockedStarterCount: number;
  LockedActiveStarterCount: number;
  CompletedStarterCount: number;
  EligibleBenchCandidateCount: number;
  HasRemainingScoringPath: boolean;
  RemainingScoringPathState?: FantasyRelevanceRemainingScoringPathState;
  Slots: FantasyRelevanceSlotState[];
  Players: FantasyRelevancePlayerState[];
}

export interface DecisionWindowFantasyRelevance {
  Version: number;
  SlotDefinitions: FantasyRelevanceSlotDefinition[];
  Teams: FantasyRelevanceTeamState[];
}

export interface DecisionWindowsReadModel {
  SchemaVersion: number;
  LeagueID: string;
  Season: string;
  LineupWeek: number;
  LastLineupWeek: number;
  DecisionWindows: DecisionWindow[];
  LookaheadDecisionWindow: DecisionWindow | null;
  PlayerLockFacts: DecisionWindowPlayerLockFact[];
  TeamLineupEvaluations: DecisionWindowTeamLineupEvaluation[];
  FantasyRelevance?: DecisionWindowFantasyRelevance;
}
