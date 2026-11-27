/**
 * Read model of public/data/ScheduleOutlook.json (Issues #1519, #1588, #1589, #1607).
 * Display only: probabilities, statuses and strength classes are generator-owned; nothing is derived here.
 * Only the fields the app displays are typed.
 */
export type PlayoffOddsStatus = 'clinched' | 'eliminated' | 'alive';
export type OpponentStrengthClass = 'weaker' | 'similar' | 'stronger';
export type RemainingScheduleClass = 'easier' | 'average' | 'harder';

export interface PlayoffOddsTeam {
  TeamID: number;
  Record: { Wins: number; Losses: number; Ties: number };
  /** Index 0 = place 1; each entry is a share between 0 and 1. */
  PlaceProbabilities: number[] | null;
  /** Exact-model authoritative nonnegative integer masses and mathematical support. */
  PlaceMassNumerators?: string[] | null;
  PossiblePlaces?: number[] | null;
  PlayoffProbability: number | null;
  EliminationProbability: number | null;
  Status: PlayoffOddsStatus | null;
  /** Expected points of the team per game (generator-owned: league mean x strength). */
  ExpectedPoints?: number | null;
  /** Sum of the win chances of all remaining games; null when any is unknown. */
  RemainingExpectedWins?: number | null;
  /** Mean win chance over all remaining games (share between 0 and 1); null when any is unknown. */
  RemainingWinProbability?: number | null;
  Upcoming?: PlayoffOddsUpcoming[] | null;
}

export interface PlayoffOddsUpcoming {
  Week: number;
  OpponentTeamID: number | null;
  /** Share between 0 and 1; null when the strength is unknown. */
  WinProbability: number | null;
  OpponentExpectedPoints: number | null;
  /** Expected points of the viewed team minus the opponent (generator-owned); null when unknown. */
  ExpectedMargin?: number | null;
}

export interface PlayoffOddsScoring {
  LeagueMeanPoints: number | null;
  PointsStdDev: number | null;
  MeanSource: string | null;
}

export interface PlayoffOddsBlock {
  Model: string;
  Available: boolean;
  Reason: string | null;
  Provenance?: {
    PlayoffTeams: number | null;
    RegularSeasonComplete: boolean;
    StrengthBasis?: string | null;
    PlaceMassDenominator?: string;
    Method?: string;
    TieRule?: string;
    OutcomeWeights?: { Loss: number; Tie: number; Win: number };
    OutcomeWeightDenominator?: number;
  } | null;
  Scoring?: PlayoffOddsScoring | null;
  Teams: PlayoffOddsTeam[];
}

export interface ScheduleOutlookUpcoming {
  Week: number;
  OpponentTeamID: number | null;
  OpponentClass: OpponentStrengthClass | null;
  OpponentStrength?: number | null;
}

/** Strength relative to the league average (1.0 = average); early in the season mixed with last season. */
export interface TeamStrength {
  Value: number | null;
  CurrentRelative: number | null;
  PreviousRelative: number | null;
  /** Share of this season in the mix, between 0 and 1. */
  CurrentWeight: number | null;
  GamesPlayed: number | null;
}

export interface ScheduleOutlookTeam {
  TeamID: number;
  RemainingGames: number;
  RemainingSoSClass: RemainingScheduleClass | null;
  RemainingSoS?: number | null;
  Strength?: TeamStrength | null;
  Upcoming: ScheduleOutlookUpcoming[];
}

export interface ScheduleMatchupForecast {
  Model: string;
  Provenance: { RegularSeasonComplete: boolean; StrengthBasis?: string | null };
  Scoring: PlayoffOddsScoring;
  Teams: Pick<PlayoffOddsTeam, 'TeamID' | 'ExpectedPoints' | 'RemainingExpectedWins' | 'RemainingWinProbability' | 'Upcoming'>[];
}

export interface ScheduleOutlookReadModel {
  Season: number;
  AsOf?: { AfterWeek: number | null } | null;
  RegularSeason?: { Teams: ScheduleOutlookTeam[]; MatchupForecast?: ScheduleMatchupForecast | null } | null;
  PlayoffOdds?: PlayoffOddsBlock | null;
}
