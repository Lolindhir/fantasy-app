/**
 * Read model of public/data/ScheduleOutlook.json (Issues #1519, #1588, #1589).
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
  PlayoffProbability: number | null;
  EliminationProbability: number | null;
  Status: PlayoffOddsStatus | null;
}

export interface PlayoffOddsBlock {
  Model: string;
  Available: boolean;
  Reason: string | null;
  Provenance?: {
    PlayoffTeams: number | null;
    RegularSeasonComplete: boolean;
  } | null;
  Teams: PlayoffOddsTeam[];
}

export interface ScheduleOutlookUpcoming {
  Week: number;
  OpponentTeamID: number | null;
  OpponentClass: OpponentStrengthClass | null;
}

export interface ScheduleOutlookTeam {
  TeamID: number;
  RemainingGames: number;
  RemainingSoSClass: RemainingScheduleClass | null;
  Upcoming: ScheduleOutlookUpcoming[];
}

export interface ScheduleOutlookReadModel {
  Season: number;
  AsOf?: { AfterWeek: number | null } | null;
  RegularSeason?: { Teams: ScheduleOutlookTeam[] } | null;
  PlayoffOdds?: PlayoffOddsBlock | null;
}
