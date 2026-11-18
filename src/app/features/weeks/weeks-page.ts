import { CommonModule } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { ActivatedRoute } from '@angular/router';
import { catchError, combineLatest, map, of, switchMap, type Observable } from 'rxjs';

import type { FantasyGameContextReadModel } from '../../core/models/fantasy-game-context.models';
import type { MatchupsReadModel } from '../../core/models/matchup.models';
import type { NFLTeam } from '../../core/models/player.models';
import type { WeeklyRecapsReadModel } from '../../core/models/weekly-recap.models';
import { DataService } from '../../core/services/data.service';
import {
  type FantasyGameContextDialogData
} from '../../shared/components/fantasy-game-context-dialog/fantasy-game-context-dialog';
import { TeamIdentityComponent, type TeamIdentityElement } from '../../shared/components/team-identity/team-identity';
import { WeekRecapContentComponent } from '../../shared/components/week-recap-content/week-recap-content';
import {
  buildLineupEfficiencyLookup,
  formatEfficiency,
  hasLineupEfficiency,
  weeklyEfficiencyHighs
} from '../../shared/utils/lineup-efficiency.util';
import {
  buildPlayoffDisplayLabels,
  buildScheduleOverview,
  buildSeasonGrid,
  buildWeekScoreboard,
  buildWeekTabs,
  buildWeeksSeasonOptions,
  parseWeekParam,
  resolveSelectedWeek,
  resolveWeeksSeason,
  selectWeekRecap,
  type WeekScoreboardMatchup,
  type WeeksSeasonOption
} from '../../shared/utils/weeks-view.util';

type WeeksTab = 'overview' | 'week' | 'season';
type SeasonGridMode = 'points' | 'efficiency';

interface SeasonData {
  season: string;
  matchups: MatchupsReadModel | null;
  recaps: WeeklyRecapsReadModel | null;
  contexts: FantasyGameContextReadModel[];
}

@Component({
  selector: 'app-weeks-page',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatDialogModule, MatFormFieldModule, MatSelectModule, TeamIdentityComponent, WeekRecapContentComponent],
  templateUrl: './weeks-page.html',
  styleUrl: './weeks-page.scss'
})
export class WeeksPageComponent {
  private readonly dataService = inject(DataService);
  private readonly route = inject(ActivatedRoute);
  private readonly dialog = inject(MatDialog);

  readonly activeTab = signal<WeeksTab>(parseWeekParam(this.route.snapshot.queryParamMap.get('week')) !== null ? 'week' : 'overview');
  readonly playedExpanded = signal(false);
  readonly gridMode = signal<SeasonGridMode>('points');
  readonly identityElements: readonly TeamIdentityElement[] = ['logo', 'name'];
  readonly logoOnlyElements: readonly TeamIdentityElement[] = ['logo'];
  readonly compactIdentityElements: readonly TeamIdentityElement[] = ['logo', 'abbr'];

  private readonly requestedSeason = signal<string | null>(this.route.snapshot.queryParamMap.get('season'));
  private readonly requestedWeek = signal<number | null>(parseWeekParam(this.route.snapshot.queryParamMap.get('week')));
  private readonly pickedSeason = signal<string | null>(null);
  private readonly pickedWeek = signal<number | null>(null);

  private readonly base = toSignal(
    combineLatest({
      leagueData: this.dataService.getLeagueWithPlayers(),
      index: this.dataService.getPastSeasonsIndex().pipe(catchError(() => of(null))),
      nflTeams: this.dataService.getNflTeams().pipe(catchError(() => of([] as NFLTeam[])))
    }).pipe(catchError(() => of(null))),
    { initialValue: undefined }
  );

  /** undefined while loading, null when the league data could not be loaded. */
  readonly ready = computed(() => this.base());
  readonly teams = computed(() => this.base()?.leagueData.teams ?? []);
  readonly nflTeams = computed(() => this.base()?.nflTeams ?? []);

  readonly seasonOptions = computed<WeeksSeasonOption[]>(() => {
    const base = this.base();
    return base ? buildWeeksSeasonOptions(base.index, base.leagueData.league.Season) : [];
  });

  readonly activeSeason = computed(() =>
    resolveWeeksSeason(this.seasonOptions(), this.pickedSeason() ?? this.requestedSeason()));

  private readonly seasonData = toSignal(
    toObservable(this.activeSeason).pipe(
      switchMap(option => {
        if (!option) return of(null);

        const matchupsSource: Observable<MatchupsReadModel | null> = option.matchupsPath
          ? this.dataService.getPastMatchupsRaw(option.matchupsPath)
          : this.dataService.getMatchups();
        const recapsSource: Observable<WeeklyRecapsReadModel | null> = option.isCurrent
          ? this.dataService.getWeeklyRecaps()
          : option.recapsPath ? this.dataService.getPastWeeklyRecapsRaw(option.recapsPath) : of(null);
        const contextsSource: Observable<FantasyGameContextReadModel[]> = option.isCurrent
          ? combineLatest({
              active: this.dataService.getFantasyGameContext().pipe(catchError(() => of(null))),
              finished: this.dataService.getFantasyGameContextHistory().pipe(
                map(history => history.Weeks ?? []),
                catchError(() => of([] as FantasyGameContextReadModel[]))
              )
            }).pipe(map(({ active, finished }) => active
              ? [...finished.filter(week => week.Week !== active.Week), active]
              : finished))
          : option.contextPath
            ? this.dataService.getPastFantasyGameContextRaw(option.contextPath).pipe(map(season => season.Weeks ?? []))
            : of([]);
        const contexts$ = contextsSource.pipe(catchError(() => of([] as FantasyGameContextReadModel[])));
        const matchups$ = matchupsSource.pipe(catchError(() => of(null)));
        const recaps$ = recapsSource.pipe(catchError(() => of(null)));

        return combineLatest({ matchups: matchups$, recaps: recaps$, contexts: contexts$ }).pipe(
          map(({ matchups, recaps, contexts }): SeasonData => ({ season: option.season, matchups, recaps, contexts }))
        );
      })
    ),
    { initialValue: null }
  );

  /** Data of the active season only; stays null while a newly selected season is still loading. */
  readonly data = computed(() => {
    const data = this.seasonData();
    return data && data.season === this.activeSeason()?.season ? data : null;
  });

  readonly weekTabs = computed(() => buildWeekTabs(this.data()?.matchups));
  readonly playoffDisplayLabels = computed(() => buildPlayoffDisplayLabels(this.data()?.matchups));

  readonly scheduleOverview = computed(() =>
    buildScheduleOverview(this.data()?.matchups, this.teams(), this.activeSeason()?.isCurrent ?? false, this.playoffDisplayLabels()));

  readonly activeOrNextWeek = computed(() => this.data()?.matchups?.Summary?.ActiveOrNextWeek ?? null);

  /** A marker, not a prediction: future playoff opponents are never synthesized. */
  readonly upcomingPlayoffStartWeek = computed(() => {
    const data = this.data()?.matchups;
    const start = Number(this.base()?.leagueData.league.PlayoffStartWeek);
    if (!this.activeSeason()?.isCurrent || !data || !this.scheduleOverview().upcoming.length
        || !Number.isSafeInteger(start) || start <= 0 || data.Weeks.some(week => week.Stage === 'playoffs')) {
      return null;
    }
    return start;
  });

  readonly selectedWeek = computed(() =>
    resolveSelectedWeek(this.data()?.matchups, this.pickedWeek(), this.requestedWeek()));

  private readonly selectedWeekModel = computed(() =>
    this.data()?.matchups?.Weeks.find(week => week.Week === this.selectedWeek()) ?? null);

  readonly selectedWeekIsPlayoff = computed(() => this.selectedWeekModel()?.Stage === 'playoffs');

  readonly scoreboard = computed(() => buildWeekScoreboard(this.selectedWeekModel(), this.teams(), this.playoffDisplayLabels()));

  readonly recap = computed(() => {
    const season = this.activeSeason()?.season ?? '';
    return selectWeekRecap(this.data()?.recaps, season, this.selectedWeekModel());
  });

  readonly seasonGrid = computed(() => buildSeasonGrid(this.data()?.matchups, this.teams()));

  /** Lineup efficiency values of the generator for the active season (null entries stay unknown). */
  readonly efficiency = computed(() => buildLineupEfficiencyLookup(this.data()?.recaps, this.activeSeason()?.season ?? ''));

  readonly efficiencyAvailable = computed(() => {
    const grid = this.seasonGrid();
    return !!grid && hasLineupEfficiency(this.efficiency(), grid.rows.map(row => row.teamID), grid.weeks.map(week => week.week));
  });

  private readonly efficiencyHighs = computed(() => {
    const grid = this.seasonGrid();
    return grid
      ? weeklyEfficiencyHighs(this.efficiency(), grid.rows.map(row => row.teamID), grid.weeks.map(week => week.week))
      : new Set<string>();
  });

  isEfficiencyHigh(teamID: number, week: number): boolean {
    return this.efficiencyHighs().has(`${week}:${teamID}`);
  }

  /** The efficiency view is only offered (and shown) when the season has generator values. */
  readonly effectiveGridMode = computed<SeasonGridMode>(() =>
    this.gridMode() === 'efficiency' && this.efficiencyAvailable() ? 'efficiency' : 'points');

  readonly firstPlayoffWeek = computed(() => this.weekTabs().find(tab => tab.isPlayoff)?.week ?? null);

  private readonly pointsFormatter = new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2
  });

  /** One detail path for the Week tab and every week on the league schedule. */
  private contextForWeek(week: number | null): FantasyGameContextReadModel | null {
    if (week === null) return null;
    const season = this.activeSeason()?.season;
    return this.data()?.contexts.find(context => String(context.Season) === season && context.Week === week) ?? null;
  }

  canOpenWeekMatchup(week: number | null, matchupID: string): boolean {
    return !!this.contextForWeek(week)?.FantasyMatchups.some(matchup => matchup.FantasyMatchupID === matchupID);
  }

  openWeekMatchup(week: number | null, matchupID: string): void {
    const context = this.contextForWeek(week);
    const league = this.base()?.leagueData.league;
    if (!context || !league || !this.canOpenWeekMatchup(week, matchupID)) return;
    const recapWeek = this.data()?.recaps?.Weeks.find(candidate => candidate.Week === week) ?? null;
    const data: FantasyGameContextDialogData = {
      mode: 'matchup',
      context,
      decisionWindows: null,
      matchups: this.data()?.matchups ?? null,
      nflTeams: this.nflTeams(),
      league,
      fantasyMatchupId: matchupID,
      players: this.base()?.leagueData.players ?? [],
      lineupEfficiency: recapWeek?.TeamPerformance ?? null,
      pregameWinProbabilities: recapWeek?.WinProbabilities ?? null
    };
    void import('../../shared/components/fantasy-game-context-dialog/fantasy-game-context-dialog').then(({ FantasyGameContextDialogComponent }) => {
      this.dialog.open(FantasyGameContextDialogComponent, {
        data,
        width: 'calc(100vw - 16px)',
        maxWidth: '760px',
        maxHeight: 'calc(100dvh - 16px)',
        autoFocus: false,
        restoreFocus: true,
        panelClass: 'fantasy-context-dialog-panel'
      });
    });
  }

  selectTab(tab: WeeksTab): void {
    this.activeTab.set(tab);
  }

  selectGridMode(mode: SeasonGridMode): void {
    this.gridMode.set(mode);
  }

  formatEfficiency(value: number | null | undefined): string {
    return formatEfficiency(value);
  }

  selectSeason(season: string): void {
    this.pickedSeason.set(season);
    this.pickedWeek.set(null);
    this.requestedWeek.set(null);
    this.playedExpanded.set(false);
    this.activeTab.set('overview');
  }

  selectWeek(week: number): void {
    this.pickedWeek.set(week);
  }

  /** Opens the existing Week details from either the schedule overview or season grid. */
  openWeek(week: number): void {
    this.selectWeek(week);
    this.selectTab('week');
  }

  /** Future 0:0 placeholders are not scores; real live and final scores remain visible. */
  showScheduleScores(matchup: WeekScoreboardMatchup): boolean {
    if (matchup.state === 'final') return true;
    return matchup.participants.some(participant =>
      participant.points !== null && Number.isFinite(participant.points) && participant.points !== 0);
  }

  scheduleMatchupLabel(matchup: WeekScoreboardMatchup): string {
    const names = matchup.participants.map(participant =>
      participant.team?.TeamAbbr || participant.team?.Team || `Team ${participant.teamID}`);
    const result = this.showScheduleScores(matchup)
      ? matchup.participants.map(participant => this.formatPoints(participant.points)).join(' to ')
      : matchup.state === 'unknown' ? 'unconfirmed' : 'versus';
    const winnerIndex = matchup.state === 'final'
      ? matchup.participants.findIndex(participant => participant.isWinner)
      : -1;
    const outcome = winnerIndex >= 0
      ? `, winner ${names[winnerIndex]}`
      : matchup.state === 'final' && matchup.isTie ? ', tie' : '';
    return `${names[0] ?? 'Team'} ${result} ${names[1] ?? 'Team'}${outcome}${matchup.playoffLabel ? `, ${matchup.playoffLabel}` : ''}`;
  }

  formatPoints(value: number | null | undefined): string {
    return value === null || value === undefined || !Number.isFinite(value) ? '–' : this.pointsFormatter.format(value);
  }

  stateLabel(state: 'final' | 'open' | 'unknown'): string {
    return state === 'final' ? 'Final' : state === 'open' ? 'Open' : 'Unconfirmed';
  }

  teamLabel(teamID: number, name: string | null | undefined): string {
    return name?.trim() || `Team ${teamID}`;
  }
}
