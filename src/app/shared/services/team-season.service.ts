import { Injectable, inject } from '@angular/core';
import { Observable, map, shareReplay } from 'rxjs';

import type { FantasyTeam } from '../../core/models/league.models';
import type { TeamSeasonsReadModel } from '../../core/models/team-season.models';
import { DataService } from '../../core/services/data.service';

export const DEFAULT_TEAM_AVATAR = 'assets/default-team-avatar.png';

/** Fantasy-team identity of one season, ready for TeamIdentityComponent. Manager fields stay separate from team fields. */
export interface TeamSeasonIdentity {
  TeamID: number;
  Team: string;
  TeamAbbr: string;
  /** Team logo of that season; the neutral default logo when the season had none, never a later or current logo. */
  Avatar: string;
  Owner: string;
  OwnerAvatar: string | null;
}

/** Looks up (Season, TeamID) in the generated TeamSeasons.json product; it derives no name, abbreviation or logo. */
export class TeamSeasonLookup {
  constructor(private readonly model: TeamSeasonsReadModel) {}

  get currentSeason(): string {
    return this.model.CurrentSeason;
  }

  /** Identity of the team in exactly that season, or null when the season or team is unknown (no fallback to another season). */
  identity(season: string | number, teamId: string | number): TeamSeasonIdentity | null {
    const seasonEntry = this.model.Seasons.find(entry => entry.Season === String(season));
    const team = seasonEntry?.Teams.find(candidate => String(candidate.TeamID) === String(teamId));
    if (!team) return null;
    return {
      TeamID: Number(team.TeamID),
      Team: team.TeamName,
      TeamAbbr: team.TeamAbbr,
      Avatar: team.TeamAvatar || DEFAULT_TEAM_AVATAR,
      Owner: team.Owner,
      OwnerAvatar: team.OwnerAvatar
    };
  }
}

/**
 * Season-bound views show the identity of that season (Issue #774): returns the teams with name, abbreviation, logo and manager of the
 * requested season. The current season and teams unknown to the lookup keep their current identity. Rosters and standings stay untouched.
 */
export function teamsWithSeasonIdentity<T extends FantasyTeam>(teams: readonly T[], lookup: TeamSeasonLookup | null, season: string | number | null | undefined): T[] {
  if (!lookup || season === null || season === undefined || String(season) === lookup.currentSeason) return [...teams];
  return teams.map(team => {
    const identity = lookup.identity(season, team.TeamID);
    return identity
      ? { ...team, Team: identity.Team, TeamAbbr: identity.TeamAbbr, Avatar: identity.Avatar, Owner: identity.Owner }
      : team;
  });
}

@Injectable({ providedIn: 'root' })
export class TeamSeasonService {
  private readonly dataService = inject(DataService);
  private lookup$?: Observable<TeamSeasonLookup>;

  getLookup(): Observable<TeamSeasonLookup> {
    this.lookup$ ??= this.dataService.getTeamSeasons().pipe(
      map(model => new TeamSeasonLookup(model)),
      shareReplay({ bufferSize: 1, refCount: false })
    );
    return this.lookup$;
  }
}
