import { CommonModule } from '@angular/common';
import { Component, Input, OnDestroy, OnInit, TemplateRef } from '@angular/core';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { Subscription } from 'rxjs';

import type { DecisionWindowsReadModel } from '../../../core/models/decision-window.models';
import type { League } from '../../../core/models/league.models';
import type { NFLTeam } from '../../../core/models/player.models';
import { DataService } from '../../../core/services/data.service';
import { createAdaptiveCountdownClock } from '../../utils/countdown-clock.util';
import {
  buildLeagueTimelineView,
  type LeagueTimelineDraft,
  type LeagueTimelineView
} from '../../utils/league-timeline-view.util';
import { DecisionWindowContextPopoverComponent } from '../decision-window-context-popover/decision-window-context-popover';
import { DecisionWindowMatchupContextComponent } from '../decision-window-matchup-context/decision-window-matchup-context';

@Component({
  selector: 'app-league-timeline',
  standalone: true,
  imports: [
    CommonModule,
    MatDialogModule,
    DecisionWindowContextPopoverComponent,
    DecisionWindowMatchupContextComponent
  ],
  templateUrl: './league-timeline.html',
  styleUrl: './league-timeline.scss'
})
export class LeagueTimelineComponent implements OnInit, OnDestroy {
  @Input({ required: true }) league!: League;
  @Input() drafts: LeagueTimelineDraft[] = [];

  now = new Date();
  decisionWindows: DecisionWindowsReadModel | null = null;
  decisionWindowsUnavailable = false;
  decisionWindowsUpdatedAt: string | undefined;
  nflTeams: NFLTeam[] = [];

  private subscriptions = new Subscription();

  constructor(
    private dataService: DataService,
    private dialog: MatDialog
  ) {}

  ngOnInit(): void {
    this.subscriptions.add(
      createAdaptiveCountdownClock(() => this.getCountdownTargets()).subscribe(now => {
        this.now = now;
      })
    );
    if (!this.isActiveLeagueStatus()) return;

    this.subscriptions.add(
      this.dataService.getNflTeams().subscribe({
        next: teams => {
          this.nflTeams = teams;
        },
        error: () => {
          this.nflTeams = [];
        }
      })
    );

    this.subscriptions.add(
      this.dataService.getDecisionWindows().subscribe({
        next: model => {
          this.decisionWindows = model;
          this.decisionWindowsUnavailable = false;
        },
        error: () => {
          this.decisionWindows = null;
          this.decisionWindowsUnavailable = true;
        }
      })
    );

    this.subscriptions.add(
      this.dataService.getDecisionWindowsTimestamp().subscribe({
        next: timestamp => {
          this.decisionWindowsUpdatedAt = timestamp;
        },
        error: () => {
          this.decisionWindowsUpdatedAt = undefined;
        }
      })
    );
  }

  ngOnDestroy(): void {
    this.subscriptions.unsubscribe();
  }

  get timeline(): LeagueTimelineView | null {
    return buildLeagueTimelineView({
      league: this.league,
      drafts: this.drafts,
      decisionWindows: this.decisionWindows,
      decisionWindowsUnavailable: this.decisionWindowsUnavailable,
      now: this.now,
      nflTeams: this.nflTeams
    });
  }

  openDecisionWindow(template: TemplateRef<unknown>): void {
    this.dialog.open(template, {
      width: '500px',
      maxWidth: 'calc(100vw - 24px)',
      maxHeight: 'calc(100dvh - 24px)',
      panelClass: 'decision-window-dialog-panel',
      ariaLabel: 'Decision Window details',
      autoFocus: false,
      restoreFocus: true
    });
  }

  private getCountdownTargets(): Array<string | null | undefined> {
    const playoffStart = (this.league as League & { PlayoffStart?: string | null }).PlayoffStart;
    const decisionWindowTargets = this.decisionWindows
      ? [
          ...this.decisionWindows.DecisionWindows.map(window => window.StartsAtUtc),
          this.decisionWindows.LookaheadDecisionWindow?.StartsAtUtc
        ]
      : [];

    return [
      this.league.SeasonKickoff,
      this.league.CapDeadline,
      this.league.NextWaiverRun,
      playoffStart,
      ...decisionWindowTargets
    ];
  }

  private isActiveLeagueStatus(): boolean {
    return this.league.Status === 'In-Season' || this.league.Status === 'Playoffs';
  }
}
