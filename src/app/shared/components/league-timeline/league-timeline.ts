import { CommonModule } from '@angular/common';
import { Component, Input, OnDestroy, OnInit, TemplateRef } from '@angular/core';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { Subscription, timer } from 'rxjs';

import type { DecisionWindowsReadModel } from '../../../core/models/decision-window.models';
import type { League } from '../../../core/models/league.models';
import { DataService } from '../../../core/services/data.service';
import { DecisionWindowContextPopoverComponent } from '../decision-window-context-popover/decision-window-context-popover';
import {
  buildLeagueTimelineView,
  type LeagueTimelineDraft,
  type LeagueTimelineView
} from '../../utils/league-timeline-view.util';

@Component({
  selector: 'app-league-timeline',
  standalone: true,
  imports: [CommonModule, MatDialogModule, DecisionWindowContextPopoverComponent],
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

  private subscriptions = new Subscription();

  constructor(
    private dataService: DataService,
    private dialog: MatDialog
  ) {}

  ngOnInit(): void {
    this.startMinuteAlignedClock();
    if (!this.isActiveLeagueStatus()) return;

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
      now: this.now
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

  private startMinuteAlignedClock(): void {
    const minuteMs = 60_000;
    const firstTickDelay = minuteMs - (Date.now() % minuteMs);
    this.subscriptions.add(
      timer(firstTickDelay, minuteMs).subscribe(() => {
        this.now = new Date();
      })
    );
  }

  private isActiveLeagueStatus(): boolean {
    return this.league.Status === 'In-Season' || this.league.Status === 'Playoffs';
  }
}
