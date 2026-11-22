/** Read model of public/data/InjuryImpact.json (Issue #1584, #1621). Display only; nothing is derived here. */
export interface InjuryImpactTeamIdentity {
  CanonicalLeagueRosterID: string;
  TeamID: number;
  Owner: string;
  TeamName: string;
}

export interface InjuryImpactWeekTeam {
  CanonicalLeagueRosterID: string;
  /** Projected points the team loses to injured players that week; a lower bound when IsLowerBound is set. */
  Impact: number;
  IsLowerBound: boolean;
  HasUnknownEvidence: boolean;
  /** Injured players whose return would have gained points that week; absent in older files. */
  CostlyPlayers?: number;
}

export interface InjuryImpactWeek {
  Week: number;
  Teams: InjuryImpactWeekTeam[];
}

export interface InjuryImpactTopPlayer {
  CanonicalPlayerID: string;
  SingleReturnImpact: number;
  Weeks: number;
}

export interface InjuryImpactSeasonTotal {
  CanonicalLeagueRosterID: string;
  Impact: number;
  ImpactPerWeek: number | null;
  /** Average number of injured players per week whose return would have gained points; absent in older files. */
  CostlyPlayersPerWeek?: number | null;
  WeeksComputed: number;
  WeeksWithImpact: number;
  IsLowerBound: boolean;
  Undeterminable: number;
  PeakWeek: { Week: number; Impact: number } | null;
  TopPlayers: InjuryImpactTopPlayer[];
}

export interface InjuryImpactPlayerRef {
  Name: string | null;
  Position: string | null;
  Picture: string | null;
  /** Latest NFL team abbreviation; absent in older files. */
  Team?: string | null;
}

export interface InjuryImpactSeason {
  Season: number;
  AsOf: { LeagueScoredWeek: number };
  Teams: InjuryImpactTeamIdentity[];
  Weeks: InjuryImpactWeek[];
  UnavailableWeeks: { Week: number; Reason: string }[];
  SeasonTotals: InjuryImpactSeasonTotal[];
  /** Absent in files generated before the display reduction. */
  PlayerRefs?: Record<string, InjuryImpactPlayerRef>;
}

export interface InjuryImpactReadModel {
  SchemaVersion: number;
  Product: string;
  CanonicalLeagueID: string;
  Seasons: InjuryImpactSeason[];
}
