import { CommonModule } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute } from '@angular/router';
import { catchError, combineLatest, of } from 'rxjs';

import type { FantasyTeamSummary } from '../../../../core/models/league.models';
import type { RivalryFilter } from '../../../../core/models/rivalry.models';
import { DataService } from '../../../../core/services/data.service';
import { TeamIdentityComponent, type TeamIdentityElement, type TeamIdentitySubject } from '../../../../shared/components/team-identity/team-identity';
import { TeamDetailDialogService } from '../../../../shared/services/team-detail-dialog.service';
import { TeamRivalryService, formatRivalryRecord } from '../../../../shared/services/team-rivalry.service';
import { TeamSeasonService, type TeamSeasonLookup } from '../../../../shared/services/team-season.service';

interface FilterOption {
  id: RivalryFilter;
  label: string;
}

export interface HeadToHeadCell {
  opponent: TeamIdentitySubject;
  /** Generated record of the row team against this opponent; null on the diagonal or without a meeting. */
  label: string | null;
  tone: 'win' | 'loss' | 'even' | null;
  meetings: number;
}

export interface HeadToHeadRow {
  team: TeamIdentitySubject;
  cells: HeadToHeadCell[];
}

/** Option value of the all-time view; every other value is a season from the generated season records. */
export const ALL_TIME = 'all-time';

/** Stats > Head-to-Head: record of every team against every other team (Issue #1621). Display only; Rivalry.json owns the counting. */
@Component({
  selector: 'app-stats-head-to-head-tab',
  standalone: true,
  imports: [CommonModule, TeamIdentityComponent],
  templateUrl: './head-to-head-tab.html',
  styleUrl: './head-to-head-tab.scss'
})
export class HeadToHeadTabComponent {
  private readonly dataService = inject(DataService);
  private readonly rivalry = inject(TeamRivalryService);
  private readonly teamDetail = inject(TeamDetailDialogService);
  private readonly teamSeasons = inject(TeamSeasonService);
  private readonly route = inject(ActivatedRoute);

  readonly filters: readonly FilterOption[] = [
    { id: 'all', label: 'All' },
    { id: 'regular', label: 'Regular' },
    { id: 'playoffs', label: 'Playoffs' }
  ];
  readonly compactIdentityElements: readonly TeamIdentityElement[] = ['logo', 'abbr'];
  readonly logoOnlyElements: readonly TeamIdentityElement[] = ['logo'];
  readonly filter = signal<RivalryFilter>('all');

  private readonly requestedSeason = signal<string | null>(this.route.snapshot.queryParamMap.get('season'));
  private readonly pickedSeason = signal<string | null>(null);

  /** undefined while loading, null when league data or the rivalry product is unavailable. */
  private readonly base = toSignal(
    combineLatest({
      league: this.dataService.getLeagueSummary(),
      lookup: this.rivalry.getLookup(),
      teamSeasons: this.teamSeasons.getLookup().pipe(catchError(() => of(null as TeamSeasonLookup | null)))
    }).pipe(catchError(() => of(null))),
    { initialValue: undefined }
  );

  readonly ready = computed(() => this.base());
  readonly allTime = ALL_TIME;
  /** Seasons offered next to All-Time; empty (no selector) while the published product has no season records. */
  readonly seasons = computed(() => this.base()?.lookup.recordSeasons ?? []);
  /** The picked season, or All-Time when none is picked or the requested one is unknown. */
  readonly selection = computed(() => {
    const wanted = this.pickedSeason() ?? this.requestedSeason();
    return wanted && this.seasons().includes(wanted) ? wanted : ALL_TIME;
  });
  readonly seasonSpan = computed(() => {
    const selection = this.selection();
    return selection === ALL_TIME ? this.base()?.lookup.seasonSpan ?? '' : selection;
  });

  /** Teams of the view: all-time uses the current teams, a season the teams of that season with their identity of that season. */
  readonly teams = computed<TeamIdentitySubject[]>(() => {
    const base = this.base();
    if (!base) return [];
    const selection = this.selection();
    const current: readonly FantasyTeamSummary[] = base.league.Teams;
    if (selection === ALL_TIME) return [...current];
    const ids = new Set(base.lookup.seasonTeamIds(selection));
    const result: TeamIdentitySubject[] = [];
    for (const team of current) {
      if (!ids.delete(Number(team.TeamID))) continue;
      const identity = base.teamSeasons?.identity(selection, team.TeamID);
      result.push(identity
        ? { TeamID: team.TeamID, Team: identity.Team, TeamAbbr: identity.TeamAbbr, Avatar: identity.Avatar, Owner: identity.Owner }
        : team);
    }
    for (const id of ids) {
      const identity = base.teamSeasons?.identity(selection, id);
      if (identity) result.push({ TeamID: id, Team: identity.Team, TeamAbbr: identity.TeamAbbr, Avatar: identity.Avatar, Owner: identity.Owner });
    }
    return result;
  });

  readonly rows = computed<HeadToHeadRow[]>(() => {
    const base = this.base();
    if (!base) return [];
    const filter = this.filter();
    const selection = this.selection();
    const teams = this.teams();
    return teams.map(team => ({
      team,
      cells: teams.map(opponent => {
        const teamId = Number(team.TeamID);
        const opponentId = Number(opponent.TeamID);
        if (teamId === opponentId) return this.toCell(opponent, null);
        if (selection === ALL_TIME) {
          const record = base.lookup.pair(teamId, opponentId, filter);
          return this.toCell(opponent, record ? { ...record, meetings: record.games.length } : null);
        }
        const record = base.lookup.seasonPair(selection, teamId, opponentId, filter);
        return this.toCell(opponent, record ? { wins: record.Wins, losses: record.Losses, ties: record.Ties, meetings: record.Wins + record.Losses + record.Ties } : null);
      })
    }));
  });

  selectFilter(filter: RivalryFilter): void {
    this.filter.set(filter);
  }

  selectSeason(value: string): void {
    // Kept in memory only: reloading the page resets to All-Time.
    this.pickedSeason.set(value);
  }

  /** The row team's Rivals tab lists every opponent with its games. */
  openRivals(team: TeamIdentitySubject): void {
    this.teamDetail.open(Number(team.TeamID), { initialTab: 'rivals' });
  }

  trackRow(_: number, row: HeadToHeadRow): number {
    return Number(row.team.TeamID);
  }

  trackTeam(_: number, team: TeamIdentitySubject): number {
    return Number(team.TeamID);
  }

  cellLabel(row: HeadToHeadRow, cell: HeadToHeadCell): string {
    return `${row.team.Team} against ${cell.opponent.Team}: ${cell.label ?? 'no games'}`;
  }

  private toCell(opponent: TeamIdentitySubject, record: { wins: number; losses: number; ties: number; meetings: number } | null): HeadToHeadCell {
    if (!record) return { opponent, label: null, tone: null, meetings: 0 };
    return {
      opponent,
      label: formatRivalryRecord(record),
      tone: record.wins > record.losses ? 'win' : record.wins < record.losses ? 'loss' : 'even',
      meetings: record.meetings
    };
  }
}
