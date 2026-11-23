import { AsyncPipe, NgFor, NgIf } from '@angular/common';
import { Component, DestroyRef, inject, OnInit } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router } from '@angular/router';
import { catchError, distinctUntilChanged, forkJoin, map, of } from 'rxjs';

import { DataService } from '../../core/services/data.service';
import { HallOfFameComponent } from '../../shared/components/hall-of-fame/hall-of-fame';
import { buildHallOfFameHighlights } from '../../shared/utils/hall-of-fame-view.util';

import { SeasonTabComponent } from './tabs/season-tab/season-tab';
import { WeeklyTabComponent } from './tabs/weekly-tab/weekly-tab';

interface StatsTab {
  id: string;
  label: string;
}

/**
 * Tabs in their decided order (Issue #1621: Hall of Fame, Season, Weekly, Head-to-Head, Player Awards).
 * A tab is listed only once it exists; the others follow in later steps of the same Issue.
 */
export const STATS_TABS: readonly StatsTab[] = [
  { id: 'season', label: 'Season' },
  { id: 'weekly', label: 'Weekly' }
];

@Component({
  selector: 'app-stats-page',
  standalone: true,
  imports: [AsyncPipe, NgFor, NgIf, HallOfFameComponent, SeasonTabComponent, WeeklyTabComponent],
  templateUrl: './stats-page.html',
  styleUrl: './stats-page.scss'
})
export class StatsPageComponent implements OnInit {
  readonly tabs = STATS_TABS;
  selectedTab = STATS_TABS[0].id;

  private readonly dataService = inject(DataService);

  /** Hall of Fame tiles above the tabs; an unavailable file never blocks the page. */
  readonly hallOfFame$ = forkJoin({
    data: this.dataService.getLeagueWithPlayers(),
    stats: this.dataService.getAllSeasonStatistics(),
    awards: this.dataService.getPlayerAwardHistory().pipe(catchError(() => of(null)))
  }).pipe(
    map(({ data: { league, teams }, stats, awards }) => buildHallOfFameHighlights(league, teams, stats.current, stats.bySeason, awards))
  );

  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);

  ngOnInit(): void {
    this.route.queryParamMap.pipe(
      map(params => params.get('tab')),
      map(tab => this.tabs.some(item => item.id === tab) ? (tab as string) : this.tabs[0].id),
      distinctUntilChanged(),
      takeUntilDestroyed(this.destroyRef)
    ).subscribe(tab => (this.selectedTab = tab));
  }

  selectTab(id: string): void {
    void this.router.navigate([], { queryParams: { tab: id }, queryParamsHandling: 'merge', replaceUrl: true });
  }
}
