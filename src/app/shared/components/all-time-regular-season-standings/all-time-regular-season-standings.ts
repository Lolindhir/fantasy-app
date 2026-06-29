import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';

import type { AllTimeRegularSeasonStandingRow } from '../../utils/league-standings-view.util';

@Component({
  selector: 'app-all-time-regular-season-standings',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './all-time-regular-season-standings.html',
  styleUrl: './all-time-regular-season-standings.scss'
})
export class AllTimeRegularSeasonStandingsComponent {
  @Input({ required: true }) standings: AllTimeRegularSeasonStandingRow[] | null | undefined;
  @Input() title = 'All-Time Regular Season';
  @Input() showTitle = true;

  recordWithQuote(row: AllTimeRegularSeasonStandingRow): string {
    const quote = row.winPercentageDisplay
      || this.formatWinPercentageDisplay(row.team.Placements.AllTime.Regular.WinPercentage);

    return quote ? `${row.record} (${quote})` : row.record;
  }

  pointDifferential(row: AllTimeRegularSeasonStandingRow): number {
    return row.points - row.pointsAgainst;
  }

  private formatWinPercentageDisplay(winPercentage: number | null | undefined): string {
    if (winPercentage === null || winPercentage === undefined) return '';

    return winPercentage
      .toFixed(3)
      .replace(/^0/, '');
  }
}
