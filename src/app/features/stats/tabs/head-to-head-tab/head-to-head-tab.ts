import { CommonModule } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { catchError, combineLatest, of } from 'rxjs';

import type { FantasyTeam } from '../../../../core/models/league.models';
import type { RivalryFilter } from '../../../../core/models/rivalry.models';
import { DataService } from '../../../../core/services/data.service';
import { TeamIdentityComponent, type TeamIdentityElement } from '../../../../shared/components/team-identity/team-identity';
import { TeamDetailDialogService } from '../../../../shared/services/team-detail-dialog.service';
import { TeamRivalryService, formatRivalryRecord, type RivalryRecordView } from '../../../../shared/services/team-rivalry.service';

interface FilterOption {
  id: RivalryFilter;
  label: string;
}

export interface HeadToHeadCell {
  opponent: FantasyTeam;
  /** Generated record of the row team against this opponent; null on the diagonal or without a meeting. */
  label: string | null;
  tone: 'win' | 'loss' | 'even' | null;
  meetings: number;
}

export interface HeadToHeadRow {
  team: FantasyTeam;
  cells: HeadToHeadCell[];
}

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

  readonly filters: readonly FilterOption[] = [
    { id: 'all', label: 'All' },
    { id: 'regular', label: 'Regular' },
    { id: 'playoffs', label: 'Playoffs' }
  ];
  readonly compactIdentityElements: readonly TeamIdentityElement[] = ['logo', 'abbr'];
  readonly logoOnlyElements: readonly TeamIdentityElement[] = ['logo'];
  readonly filter = signal<RivalryFilter>('all');

  /** undefined while loading, null when league data or the rivalry product is unavailable. */
  private readonly base = toSignal(
    combineLatest({
      leagueData: this.dataService.getLeagueWithPlayers(),
      lookup: this.rivalry.getLookup()
    }).pipe(catchError(() => of(null))),
    { initialValue: undefined }
  );

  readonly ready = computed(() => this.base());
  readonly seasonSpan = computed(() => this.base()?.lookup.seasonSpan ?? '');
  readonly teams = computed(() => this.base()?.leagueData.teams ?? []);

  readonly rows = computed<HeadToHeadRow[]>(() => {
    const base = this.base();
    if (!base) return [];
    const filter = this.filter();
    const teams = base.leagueData.teams;
    return teams.map(team => ({
      team,
      cells: teams.map(opponent => this.toCell(team, opponent, base.lookup.pair(Number(team.TeamID), Number(opponent.TeamID), filter)))
    }));
  });

  selectFilter(filter: RivalryFilter): void {
    this.filter.set(filter);
  }

  /** The row team's Rivals tab lists every opponent with its games. */
  openRivals(team: FantasyTeam): void {
    this.teamDetail.open(Number(team.TeamID), { initialTab: 'rivals' });
  }

  trackRow(_: number, row: HeadToHeadRow): number {
    return Number(row.team.TeamID);
  }

  trackTeam(_: number, team: FantasyTeam): number {
    return Number(team.TeamID);
  }

  cellLabel(row: HeadToHeadRow, cell: HeadToHeadCell): string {
    return `${row.team.Team} against ${cell.opponent.Team}: ${cell.label ?? 'no games'}`;
  }

  private toCell(team: FantasyTeam, opponent: FantasyTeam, record: RivalryRecordView | null): HeadToHeadCell {
    const self = Number(team.TeamID) === Number(opponent.TeamID);
    if (self || !record) return { opponent, label: null, tone: null, meetings: 0 };
    return {
      opponent,
      label: formatRivalryRecord(record),
      tone: record.wins > record.losses ? 'win' : record.wins < record.losses ? 'loss' : 'even',
      meetings: record.games.length
    };
  }
}
