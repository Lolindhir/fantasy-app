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
import { TeamSeasonService, teamsWithSeasonIdentity } from '../../services/team-season.service';
import {
  buildTeamSchedule,
  formatScheduleRecord,
  type ScheduleRecord,
  type TeamScheduleRow
} from '../../utils/team-schedule.util';
import {
  formatExpectedWins,
  formatMargin,
  formatPoints,
  formatShare,
  formatStrength,
  OPPONENT_CLASS_VIEW,
  REMAINING_CLASS_LABEL,
  formatPlayoffPercent,
  resolveTeamScheduleOutlook
} from '../../utils/schedule-outlook-view.util';
import type { ScheduleOutlookReadModel } from '../../../core/models/schedule-outlook.models';
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
  private readonly teamSeasons = inject(TeamSeasonService);
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
      nflTeams: this.dataService.getNflTeams().pipe(catchError(() => of([] as NFLTeam[]))),
      outlook: this.dataService.getScheduleOutlook().pipe(catchError(() => of(null as ScheduleOutlookReadModel | null))),
      teamSeasons: this.teamSeasons.getLookup().pipe(catchError(() => of(null)))
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
    if (!team || !option || !data?.matchups) return null;
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

  /** Opponents carry the identity (name, abbreviation, logo) of the selected season (Issue #774). */
  private readonly teamsById = computed(() =>
    new Map(teamsWithSeasonIdentity(this.leagueSignal()?.Teams ?? [], this.base()?.teamSeasons ?? null, this.activeSeason()?.season)
      .map(candidate => [Number(candidate.TeamID), candidate])));

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

  /** Generated opponent strength classes (Issue #1589); only for the running season and only while games remain. */
  readonly outlook = computed(() => {
    const team = this.teamSignal();
    const league = this.leagueSignal();
    if (!team || !league || !this.activeSeason()?.isCurrent) return null;
    const view = resolveTeamScheduleOutlook(this.base()?.outlook, league.Season, team.TeamID);
    return view && view.remainingGames > 0 ? view : null;
  });

  readonly remainingLabel = computed(() => {
    const remaining = this.outlook()?.remaining;
    return remaining ? REMAINING_CLASS_LABEL[remaining] : '';
  });

  /** Expected wins out of the remaining games with the average win chance, e.g. "1.2 of 3 wins (Ø 40%)"; empty while unknown. */
  readonly remainingWinLabel = computed(() => {
    const view = this.outlook();
    if (!view || view.remainingWinProbability === null || view.remainingExpectedWins === null) return '';
    return `${formatExpectedWins(view.remainingExpectedWins)} of ${view.remainingGames} wins (Ø ${formatPlayoffPercent(view.remainingWinProbability)})`;
  });

  readonly explainOpen = signal(false);

  toggleExplain(): void {
    this.explainOpen.update(open => !open);
  }

  /** Generated numbers of one upcoming game: opponent scoring, own win chance; null for played or playoff games. */
  gameOutlook(row: TeamScheduleRow) {
    if (row.outcome || row.isPlayoff) return null;
    const game = this.outlook()?.gameByWeek.get(row.week);
    if (!game) return null;
    return {
      margin: game.margin === null ? '' : formatMargin(game.margin),
      win: game.winProbability === null ? '' : formatPlayoffPercent(game.winProbability)
    };
  }

  /** Strength breakdown per upcoming opponent for the explanation panel. */
  readonly explainRows = computed(() => {
    const view = this.outlook();
    if (!view) return [];
    return this.upcomingRows().flatMap(row => {
      const game = view.gameByWeek.get(row.week);
      if (!game || row.isPlayoff) return [];
      const mix = game.opponentMix;
      return [{
        week: row.week,
        name: this.opponentShort(row),
        strength: game.opponentStrength === null ? '' : formatStrength(game.opponentStrength),
        current: mix ? formatShare(mix.currentWeight) : '',
        currentStrength: mix?.currentRelative == null ? '' : formatStrength(mix.currentRelative),
        previous: mix ? formatShare(1 - mix.currentWeight) : '',
        previousStrength: mix?.previousRelative == null ? '' : formatStrength(mix.previousRelative)
      }];
    });
  });

  readonly leagueMeanLabel = computed(() => {
    const mean = this.outlook()?.leagueMeanPoints;
    return typeof mean === 'number' ? formatPoints(mean) : '';
  });

  opponentChip(row: TeamScheduleRow) {
    if (row.outcome || row.isPlayoff) return null;
    const cls = this.outlook()?.opponentByWeek.get(row.week);
    return cls ? { cls, ...OPPONENT_CLASS_VIEW[cls] } : null;
  }

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
