import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';

import type { AllTimeStandingRow } from '../../utils/league-standings-view.util';

@Component({
  selector: 'app-all-time-standings',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './all-time-standings.html',
  styleUrl: './all-time-standings.scss'
})
export class AllTimeStandingsComponent {
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
