import { CommonModule } from '@angular/common';
import { AfterViewInit, Component, Input, OnDestroy } from '@angular/core';

import type { AllTimeStandingRow } from '../../utils/league-standings-view.util';

@Component({
  selector: 'app-all-time-standings',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './all-time-standings.html',
  styleUrl: './all-time-standings.scss'
})
export class AllTimeStandingsComponent implements AfterViewInit, OnDestroy {
  private static readonly EXPANDED_AWARD_LIMIT = 4;

  private readonly awardIconSlotsByCount = [
    [],
    [0],
    [0, 1],
    [0, 1, 2],
    [0, 1, 2, 3]
  ] as const;

  @Input({ required: true }) standings: AllTimeStandingRow[] | null | undefined;
  @Input() title = 'All-Time Standings';
  @Input() showTitle = true;

  readonly layoutDebugEnabled =
    typeof window !== 'undefined'
    && new URLSearchParams(window.location.search).get('layoutDebug') === '1';

  layoutDebugLines: string[] = [];

  private readonly layoutDebugTimers: number[] = [];
  private layoutDebugResizeHandler: (() => void) | undefined;

  ngAfterViewInit(): void {
    if (!this.layoutDebugEnabled || typeof window === 'undefined') return;

    const measure = () => this.measureLayoutOverflow();
    this.layoutDebugResizeHandler = measure;
    window.addEventListener('resize', measure);

    this.layoutDebugTimers.push(
      window.setTimeout(measure, 0),
      window.setTimeout(measure, 500),
      window.setTimeout(measure, 1500)
    );
  }

  ngOnDestroy(): void {
    if (typeof window === 'undefined') return;

    for (const timer of this.layoutDebugTimers) {
      window.clearTimeout(timer);
    }

    if (this.layoutDebugResizeHandler) {
      window.removeEventListener('resize', this.layoutDebugResizeHandler);
    }
  }

  refreshLayoutDebug(): void {
    if (this.layoutDebugEnabled) {
      this.measureLayoutOverflow();
    }
  }

  showAwardMultiplier(row: AllTimeStandingRow, count: number): boolean {
    return count > 1 && this.shouldCompactAwards(row);
  }

  awardIconSlots(row: AllTimeStandingRow, count: number): readonly number[] {
    if (count <= 0) return this.awardIconSlotsByCount[0];

    if (this.shouldCompactAwards(row)) {
      return this.awardIconSlotsByCount[1];
    }

    return this.awardIconSlotsByCount[Math.min(count, AllTimeStandingsComponent.EXPANDED_AWARD_LIMIT)];
  }


  private measureLayoutOverflow(): void {
    if (typeof window === 'undefined' || typeof document === 'undefined') return;

    const viewportWidth = window.innerWidth;
    const visualViewport = window.visualViewport;
    const documentElement = document.documentElement;
    const body = document.body;
    const lines: string[] = [
      `viewport inner=${viewportWidth.toFixed(1)} visual=${visualViewport?.width.toFixed(1) ?? 'n/a'} offsetLeft=${visualViewport?.offsetLeft.toFixed(1) ?? 'n/a'} scale=${visualViewport?.scale.toFixed(2) ?? 'n/a'} dpr=${window.devicePixelRatio.toFixed(2)}`,
      `window scrollX=${window.scrollX.toFixed(1)}`,
      `html client/scroll=${documentElement.clientWidth}/${documentElement.scrollWidth} overflow=${documentElement.scrollWidth - documentElement.clientWidth}px`,
      `body client/scroll=${body.clientWidth}/${body.scrollWidth} overflow=${body.scrollWidth - body.clientWidth}px`
    ];

    const findings = Array.from(document.querySelectorAll<HTMLElement>('body *'))
      .filter((element) => !element.closest('[data-layout-debug]'))
      .map((element) => {
        const style = window.getComputedStyle(element);
        const rect = element.getBoundingClientRect();

        if (
          style.display === 'none'
          || style.visibility === 'hidden'
          || rect.width <= 0
          || rect.height <= 0
        ) {
          return null;
        }

        const rightOverflow = Math.max(0, rect.right - viewportWidth);
        const leftOverflow = Math.max(0, -rect.left);
        const ownOverflow = Math.max(0, element.scrollWidth - element.clientWidth);
        const score = Math.max(rightOverflow, leftOverflow, ownOverflow);

        if (score <= 0.5) return null;

        return {
          element,
          style,
          rect,
          rightOverflow,
          leftOverflow,
          ownOverflow,
          score
        };
      })
      .filter((finding): finding is NonNullable<typeof finding> => finding !== null)
      .sort((a, b) => b.score - a.score)
      .slice(0, 24);

    lines.push(`findings=${findings.length}`);

    for (const finding of findings) {
      lines.push(
        `${this.layoutDebugSelector(finding.element)} R+${finding.rightOverflow.toFixed(1)} L+${finding.leftOverflow.toFixed(1)} own+${finding.ownOverflow.toFixed(1)} rect=${finding.rect.left.toFixed(1)}..${finding.rect.right.toFixed(1)} w=${finding.rect.width.toFixed(1)} sw/cw=${finding.element.scrollWidth}/${finding.element.clientWidth} ox=${finding.style.overflowX} display=${finding.style.display} pos=${finding.style.position}`
      );
    }

    lines.push('--- all-time chain ---');

    const focused = Array.from(document.querySelectorAll<HTMLElement>(
      '.app-container, .content, app-overview, app-all-time-overview, .all-time-overview, .all-time-tab-content, app-all-time-standings, .all-time, .all-time-row, .all-time-awards, .all-time-award'
    ))
      .filter((element) => !element.closest('[data-layout-debug]'))
      .slice(0, 40);

    for (const element of focused) {
      const rect = element.getBoundingClientRect();
      const style = window.getComputedStyle(element);
      lines.push(
        `${this.layoutDebugSelector(element)} rect=${rect.left.toFixed(1)}..${rect.right.toFixed(1)} w=${rect.width.toFixed(1)} sw/cw=${element.scrollWidth}/${element.clientWidth} minW=${style.minWidth} maxW=${style.maxWidth} ox=${style.overflowX} display=${style.display}`
      );
    }

    this.layoutDebugLines = lines;
  }

  private layoutDebugSelector(element: HTMLElement): string {
    let selector = element.tagName.toLowerCase();

    if (element.id) {
      selector += `#${element.id}`;
    }

    const classes = Array.from(element.classList).slice(0, 3);
    if (classes.length > 0) {
      selector += `.${classes.join('.')}`;
    }

    return selector;
  }

  private shouldCompactAwards(row: AllTimeStandingRow): boolean {
    return this.totalAwardCount(row) > AllTimeStandingsComponent.EXPANDED_AWARD_LIMIT;
  }

  private totalAwardCount(row: AllTimeStandingRow): number {
    return row.championships
      + row.runnerUps
      + row.thirds
      + row.regularSeasonWins;
  }
}
