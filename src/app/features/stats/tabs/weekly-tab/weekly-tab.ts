import { CommonModule } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { catchError, combineLatest, map, of, switchMap, type Observable } from 'rxjs';

import type { MatchupsReadModel } from '../../../../core/models/matchup.models';
import type { WeeklyRecapsReadModel } from '../../../../core/models/weekly-recap.models';
import { DataService } from '../../../../core/services/data.service';
import { TeamIdentityComponent, type TeamIdentityElement } from '../../../../shared/components/team-identity/team-identity';
import {
  buildLineupEfficiencyLookup,
  formatEfficiency,
  hasLineupEfficiency,
  weeklyEfficiencyHighs
} from '../../../../shared/utils/lineup-efficiency.util';
import {
  buildSeasonGrid,
  buildWeekTabs,
  buildWeeksSeasonOptions,
  resolveWeeksSeason,
  type WeeksSeasonOption
} from '../../../../shared/utils/weeks-view.util';

type SeasonGridMode = 'points' | 'efficiency';

interface SeasonData {
  season: string;
  matchups: MatchupsReadModel | null;
  recaps: WeeklyRecapsReadModel | null;
}

/** Stats > Weekly: points and lineup efficiency per team and week of a season (Issue #1621). Display only. */
@Component({
  selector: 'app-stats-weekly-tab',
  standalone: true,
  imports: [CommonModule, RouterLink, TeamIdentityComponent],
  templateUrl: './weekly-tab.html',
  styleUrl: './weekly-tab.scss'
})
export class WeeklyTabComponent {
  private readonly dataService = inject(DataService);
  private readonly route = inject(ActivatedRoute);

  readonly gridMode = signal<SeasonGridMode>('points');
  readonly compactIdentityElements: readonly TeamIdentityElement[] = ['logo', 'abbr'];
  readonly logoOnlyElements: readonly TeamIdentityElement[] = ['logo'];

  private readonly requestedSeason = signal<string | null>(this.route.snapshot.queryParamMap.get('season'));
  private readonly pickedSeason = signal<string | null>(null);

  private readonly base = toSignal(
    combineLatest({
      league: this.dataService.getLeagueSummary(),
      index: this.dataService.getPastSeasonsIndex().pipe(catchError(() => of(null)))
    }).pipe(catchError(() => of(null))),
    { initialValue: undefined }
  );

  /** undefined while loading, null when the league data could not be loaded. */
  readonly ready = computed(() => this.base());
  readonly teams = computed(() => this.base()?.league.Teams ?? []);

  readonly seasonOptions = computed<WeeksSeasonOption[]>(() => {
    const base = this.base();
    return base ? buildWeeksSeasonOptions(base.index, base.league.Season) : [];
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
        return combineLatest({
          matchups: matchupsSource.pipe(catchError(() => of(null))),
          recaps: recapsSource.pipe(catchError(() => of(null)))
        }).pipe(map(({ matchups, recaps }): SeasonData => ({ season: option.season, matchups, recaps })));
      })
    ),
    { initialValue: null }
  );

  /** Data of the active season only; stays null while a newly selected season is still loading. */
  readonly data = computed(() => {
    const data = this.seasonData();
    return data && data.season === this.activeSeason()?.season ? data : null;
  });

  readonly seasonGrid = computed(() => buildSeasonGrid(this.data()?.matchups, this.teams()));
  readonly firstPlayoffWeek = computed(() => buildWeekTabs(this.data()?.matchups).find(tab => tab.isPlayoff)?.week ?? null);

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

  /** The efficiency view is only offered (and shown) when the season has generator values. */
  readonly effectiveGridMode = computed<SeasonGridMode>(() =>
    this.gridMode() === 'efficiency' && this.efficiencyAvailable() ? 'efficiency' : 'points');

  private readonly pointsFormatter = new Intl.NumberFormat('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 2 });

  isEfficiencyHigh(teamID: number, week: number): boolean {
    return this.efficiencyHighs().has(`${week}:${teamID}`);
  }

  selectSeason(season: string): void {
    this.pickedSeason.set(season);
  }

  selectGridMode(mode: SeasonGridMode): void {
    this.gridMode.set(mode);
  }

  formatEfficiency(value: number | null | undefined): string {
    return formatEfficiency(value);
  }

  formatPoints(value: number | null | undefined): string {
    return value === null || value === undefined || !Number.isFinite(value) ? '–' : this.pointsFormatter.format(value);
  }

  teamLabel(teamID: number): string {
    return `Team ${teamID}`;
  }
}
