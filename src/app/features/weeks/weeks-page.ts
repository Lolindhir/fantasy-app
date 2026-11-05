import { CommonModule } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { ActivatedRoute } from '@angular/router';
import { catchError, combineLatest, map, of, switchMap, type Observable } from 'rxjs';

import type { MatchupsReadModel } from '../../core/models/matchup.models';
import type { NFLTeam } from '../../core/models/player.models';
import type { WeeklyRecapsReadModel } from '../../core/models/weekly-recap.models';
import { DataService } from '../../core/services/data.service';
import { TeamIdentityComponent, type TeamIdentityElement } from '../../shared/components/team-identity/team-identity';
import { WeekRecapContentComponent } from '../../shared/components/week-recap-content/week-recap-content';
import {
  buildSeasonGrid,
  buildWeekScoreboard,
  buildWeekTabs,
  buildWeeksSeasonOptions,
  parseWeekParam,
  resolveSelectedWeek,
  resolveWeeksSeason,
  selectWeekRecap,
  type WeeksSeasonOption
} from '../../shared/utils/weeks-view.util';

type WeeksTab = 'week' | 'season';

interface SeasonData {
  season: string;
  matchups: MatchupsReadModel | null;
  recaps: WeeklyRecapsReadModel | null;
}

@Component({
  selector: 'app-weeks-page',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatFormFieldModule, MatSelectModule, TeamIdentityComponent, WeekRecapContentComponent],
  templateUrl: './weeks-page.html',
  styleUrl: './weeks-page.scss'
})
export class WeeksPageComponent {
  private readonly dataService = inject(DataService);
  private readonly route = inject(ActivatedRoute);

  readonly activeTab = signal<WeeksTab>('week');
  readonly identityElements: readonly TeamIdentityElement[] = ['logo', 'name'];
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
        const matchups$ = matchupsSource.pipe(catchError(() => of(null)));
        const recaps$ = recapsSource.pipe(catchError(() => of(null)));

        return combineLatest({ matchups: matchups$, recaps: recaps$ }).pipe(
          map(({ matchups, recaps }): SeasonData => ({ season: option.season, matchups, recaps }))
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

  readonly selectedWeek = computed(() =>
    resolveSelectedWeek(this.data()?.matchups, this.pickedWeek(), this.requestedWeek()));

  private readonly selectedWeekModel = computed(() =>
    this.data()?.matchups?.Weeks.find(week => week.Week === this.selectedWeek()) ?? null);

  readonly selectedWeekIsPlayoff = computed(() => this.selectedWeekModel()?.Stage === 'playoffs');

  readonly scoreboard = computed(() => buildWeekScoreboard(this.selectedWeekModel(), this.teams()));

  readonly recap = computed(() => {
    const season = this.activeSeason()?.season ?? '';
    return selectWeekRecap(this.data()?.recaps, season, this.selectedWeekModel());
  });

  readonly seasonGrid = computed(() => buildSeasonGrid(this.data()?.matchups, this.teams()));

  readonly firstPlayoffWeek = computed(() => this.weekTabs().find(tab => tab.isPlayoff)?.week ?? null);

  private readonly pointsFormatter = new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2
  });

  selectTab(tab: WeeksTab): void {
    this.activeTab.set(tab);
  }

  selectSeason(season: string): void {
    this.pickedSeason.set(season);
    this.pickedWeek.set(null);
    this.requestedWeek.set(null);
  }

  selectWeek(week: number): void {
    this.pickedWeek.set(week);
  }

  /** Switches to the Week tab for a week picked in the season grid. */
  openWeek(week: number): void {
    this.selectWeek(week);
    this.selectTab('week');
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
