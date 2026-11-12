import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, Input, computed, inject, signal } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { MatDialog } from '@angular/material/dialog';
import { catchError, combineLatest, of, switchMap } from 'rxjs';

import type { FantasyTeam, League } from '../../../core/models/league.models';
import type { NFLTeam, Player } from '../../../core/models/player.models';
import { DataService } from '../../../core/services/data.service';
import { SharedMaterialImports } from '../../shared-material-imports';
import { TeamScheduleDataService } from '../../services/team-schedule-data.service';
import {
  buildTeamSchedule,
  formatScheduleRecord,
  type ScheduleRecord,
  type TeamScheduleRow
} from '../../utils/team-schedule.util';
import { buildWeeksSeasonOptions, resolveWeeksSeason } from '../../utils/weeks-view.util';
import {
  type FantasyGameContextDialogData
} from '../fantasy-game-context-dialog/fantasy-game-context-dialog';

/** Season schedule of one team: opponent, result or kickoff date per week; a row opens the matchup detail. */
@Component({
  selector: 'app-team-schedule-tab',
  standalone: true,
  imports: [CommonModule, SharedMaterialImports],
  templateUrl: './team-schedule-tab.html',
  styleUrl: './team-schedule-tab.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class TeamScheduleTabComponent {
  private readonly dataService = inject(DataService);
  private readonly scheduleData = inject(TeamScheduleDataService);
  private readonly dialog = inject(MatDialog);

  private readonly teamSignal = signal<FantasyTeam | null>(null);
  private readonly leagueSignal = signal<League | null>(null);

  @Input({ required: true }) set team(value: FantasyTeam) { this.teamSignal.set(value); }
  @Input({ required: true }) set league(value: League) { this.leagueSignal.set(value); }
  @Input() players: Player[] = [];

  private readonly pickedSeason = signal<string | null>(null);

  private readonly base = toSignal(
    combineLatest({
      index: this.dataService.getPastSeasonsIndex().pipe(catchError(() => of(null))),
      nflTeams: this.dataService.getNflTeams().pipe(catchError(() => of([] as NFLTeam[])))
    }),
    { initialValue: undefined }
  );

  readonly seasonOptions = computed(() => {
    const base = this.base();
    const league = this.leagueSignal();
    return base && league ? buildWeeksSeasonOptions(base.index, league.Season) : [];
  });

  readonly activeSeason = computed(() => resolveWeeksSeason(this.seasonOptions(), this.pickedSeason()));

  private readonly seasonData = toSignal(
    toObservable(this.activeSeason).pipe(
      switchMap(option => option ? this.scheduleData.load(option) : of(null))
    ),
    { initialValue: null }
  );

  /** Data of the active season only; null while a newly selected season is loading. */
  readonly data = computed(() => {
    const data = this.seasonData();
    return data && data.season === this.activeSeason()?.season ? data : null;
  });

  readonly loading = computed(() => this.base() === undefined || (!!this.activeSeason() && !this.data()));

  readonly schedule = computed(() => {
    const team = this.teamSignal();
    const option = this.activeSeason();
    const data = this.data();
    const league = this.leagueSignal();
    if (!team || !option || !data) return null;
    return buildTeamSchedule(data.matchups, team.TeamID, {
      isCurrentSeason: option.isCurrent,
      playoffStartWeek: league?.PlayoffStartWeek
    });
  });

  private readonly lastPlayedWeek = computed(() =>
    Math.max(0, ...(this.schedule()?.rows ?? []).filter(row => row.outcome).map(row => row.week)));

  /** Games not played yet (nearest first); byes before the last played week count as played. */
  readonly upcomingRows = computed(() =>
    (this.schedule()?.rows ?? []).filter(row => !this.isPlayed(row)));

  /** Played games, latest first. */
  readonly playedRows = computed(() =>
    (this.schedule()?.rows ?? []).filter(row => this.isPlayed(row)).reverse());

  private isPlayed(row: TeamScheduleRow): boolean {
    return row.outcome !== null || (row.opponentID === null && row.week < this.lastPlayedWeek());
  }

  private readonly teamsById = computed(() =>
    new Map((this.leagueSignal()?.Teams ?? []).map(candidate => [Number(candidate.TeamID), candidate])));

  readonly seasonRecordLabel = computed(() => {
    const schedule = this.schedule();
    return schedule ? formatScheduleRecord(schedule.record) : '';
  });

  /** Playoff record from decided playoff games; empty until one is final. */
  readonly playoffRecordLabel = computed(() => {
    const rows = (this.schedule()?.rows ?? []).filter(row => row.isPlayoff && row.outcome);
    if (!rows.length) return '';
    const count = (outcome: string) => rows.filter(row => row.outcome === outcome).length;
    const ties = count('tie');
    return ties ? `${count('win')}-${count('loss')}-${ties}` : `${count('win')}-${count('loss')}`;
  });

  selectSeason(season: string): void {
    this.pickedSeason.set(season);
  }

  opponent(row: TeamScheduleRow): FantasyTeam | null {
    return row.opponentID === null ? null : this.teamsById().get(row.opponentID) ?? null;
  }

  opponentName(row: TeamScheduleRow): string {
    if (row.opponentID === null) return 'Bye';
    const opponent = this.opponent(row);
    return opponent?.Team?.trim() || opponent?.Owner?.trim() || `Team ${row.opponentID}`;
  }

  opponentShort(row: TeamScheduleRow): string {
    return this.opponent(row)?.TeamAbbr?.trim() || this.opponentName(row);
  }

  opponentAvatar(row: TeamScheduleRow): string {
    return this.opponent(row)?.Avatar || 'assets/default-team-avatar.png';
  }

  recordLabel(record: ScheduleRecord | null): string {
    return record ? formatScheduleRecord(record) : '';
  }

  outcomeLetter(row: TeamScheduleRow): string {
    return row.outcome === 'win' ? 'W' : row.outcome === 'loss' ? 'L' : 'T';
  }

  points(value: number | null): string {
    return value === null || !Number.isFinite(value) ? '–' : value.toFixed(1);
  }

  canOpen(row: TeamScheduleRow): boolean {
    return this.findContext(row) !== null;
  }

  trackRow(_: number, row: TeamScheduleRow): string {
    return row.key;
  }

  open(row: TeamScheduleRow): void {
    const context = this.findContext(row);
    const league = this.leagueSignal();
    if (!context || !league || !row.matchupID) return;
    const week = this.data()?.recaps?.Weeks.find(candidate => candidate.Week === row.week) ?? null;
    const dialogData: FantasyGameContextDialogData = {
      mode: 'matchup',
      context,
      decisionWindows: null,
      matchups: this.data()?.matchups ?? null,
      nflTeams: this.base()?.nflTeams ?? [],
      league,
      fantasyMatchupId: row.matchupID,
      players: this.players,
      lineupEfficiency: week?.TeamPerformance ?? null
    };
    void import('../fantasy-game-context-dialog/fantasy-game-context-dialog').then(({ FantasyGameContextDialogComponent }) => {
      this.dialog.open(FantasyGameContextDialogComponent, {
        data: dialogData,
        width: 'calc(100vw - 16px)',
        maxWidth: '760px',
        maxHeight: 'calc(100dvh - 16px)',
        autoFocus: false,
        restoreFocus: true,
        panelClass: 'fantasy-context-dialog-panel'
      });
    });
  }

  private findContext(row: TeamScheduleRow) {
    const season = this.activeSeason()?.season;
    if (!row.matchupID || !season) return null;
    const context = this.data()?.contexts.find(candidate => String(candidate.Season) === season && candidate.Week === row.week);
    return context?.FantasyMatchups.some(matchup => matchup.FantasyMatchupID === row.matchupID) ? context : null;
  }
}
