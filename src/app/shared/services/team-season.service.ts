import { Injectable, inject } from '@angular/core';
import { Observable, map, shareReplay } from 'rxjs';

import type { TeamSeasonsReadModel } from '../../core/models/team-season.models';
import { DataService } from '../../core/services/data.service';

export const DEFAULT_TEAM_AVATAR = 'assets/default-team-avatar.png';

/** Fantasy-team identity of one season, ready for TeamIdentityComponent. Manager fields stay separate from team fields. */
export interface TeamSeasonIdentity {
  TeamID: number | string;
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
      TeamID: team.TeamID,
      Team: team.TeamName,
      TeamAbbr: team.TeamAbbr,
      Avatar: team.TeamAvatar || DEFAULT_TEAM_AVATAR,
      Owner: team.Owner,
      OwnerAvatar: team.OwnerAvatar
    };
  }
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
