import { NgFor, NgIf } from '@angular/common';
import { Component, DestroyRef, inject, OnInit } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router } from '@angular/router';
import { distinctUntilChanged, map } from 'rxjs';

import { SeasonTabComponent } from './tabs/season-tab/season-tab';

interface StatsTab {
  id: string;
  label: string;
}

/**
 * Tabs in their decided order (Issue #1621: Hall of Fame, Season, Weekly, Head-to-Head, Player Awards).
 * A tab is listed only once it exists; the others follow in later steps of the same Issue.
 */
export const STATS_TABS: readonly StatsTab[] = [{ id: 'season', label: 'Season' }];

@Component({
  selector: 'app-stats-page',
  standalone: true,
  imports: [NgFor, NgIf, SeasonTabComponent],
  templateUrl: './stats-page.html',
  styleUrl: './stats-page.scss'
})
export class StatsPageComponent implements OnInit {
  readonly tabs = STATS_TABS;
  selectedTab = STATS_TABS[0].id;

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
