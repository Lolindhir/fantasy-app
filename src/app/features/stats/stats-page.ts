import { NgFor, NgIf } from '@angular/common';
import { Component, DestroyRef, ElementRef, inject, OnInit, ViewChild } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router } from '@angular/router';
import { distinctUntilChanged, map } from 'rxjs';


import { SeasonTabComponent } from './tabs/season-tab/season-tab';
import { HeadToHeadTabComponent } from './tabs/head-to-head-tab/head-to-head-tab';
import { PlayerAwardsTabComponent } from './tabs/player-awards-tab/player-awards-tab';
import { WeeklyTabComponent } from './tabs/weekly-tab/weekly-tab';

interface StatsTab {
  id: string;
  label: string;
}

/**
 * Tabs in their decided order (Issue #1621: Season, Head-to-Head, Player Awards, Weekly).
 * A tab is listed only once it exists.
 */
export const STATS_TABS: readonly StatsTab[] = [
  { id: 'season', label: 'Season' },
  { id: 'head-to-head', label: 'Head-to-Head' },
  { id: 'player-awards', label: 'Player Awards' },
  { id: 'weekly', label: 'Weekly' }
];

@Component({
  selector: 'app-stats-page',
  standalone: true,
  imports: [NgFor, NgIf, SeasonTabComponent, HeadToHeadTabComponent, PlayerAwardsTabComponent, WeeklyTabComponent],
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

  @ViewChild('tabBar') private tabBar?: ElementRef<HTMLElement>;
  @ViewChild('tabBody') private tabBody?: ElementRef<HTMLElement>;

  selectTab(id: string): void {
    // Keep the tab bar where it is on screen: a shorter tab body would otherwise clamp the
    // scroll position and make the page jump.
    const before = this.tabBar?.nativeElement.getBoundingClientRect().top;
    // Never let the page get shorter than it is now, so the scroll position stays valid.
    const body = this.tabBody?.nativeElement;
    if (body) {
      body.style.minHeight = `${body.offsetHeight}px`;
    }
    if (before !== undefined) {
      setTimeout(() => {
        const after = this.tabBar?.nativeElement.getBoundingClientRect().top;
        if (after !== undefined && Math.abs(after - before) > 1) {
          window.scrollBy(0, after - before);
        }
      }, 0);
    }
    void this.router.navigate([], { queryParams: { tab: id }, queryParamsHandling: 'merge', replaceUrl: true });
  }
}
