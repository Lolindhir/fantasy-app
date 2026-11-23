/** TeamSeasons.json: App delivery of the Shared Derived product league-teams (ADR-098, Issue #774). Names, abbreviations and logos are generator-owned. */
export interface RawTeamSeasonTeam {
  TeamID: number | string;
  CanonicalLeagueRosterID: string;
  CanonicalLeagueMemberID: string;
  /** Manager fields. */
  OwnerID: string;
  Owner: string;
  OwnerAvatar: string | null;
  /** Fantasy-team fields. */
  TeamName: string;
  TeamNameSource: 'provider' | 'owner-fallback';
  TeamAbbr: string;
  TeamAvatar: string | null;
}

export interface RawTeamSeason {
  Season: string;
  Teams: RawTeamSeasonTeam[];
}

export interface TeamSeasonsReadModel {
  SchemaVersion: number;
  Product: string;
  CanonicalLeagueID: string;
  CurrentSeason: string;
  Seasons: RawTeamSeason[];
}
