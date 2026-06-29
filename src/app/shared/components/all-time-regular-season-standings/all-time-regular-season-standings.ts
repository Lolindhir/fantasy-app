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
    const quote = row.winPercentageDisplay || this.calculateWinPercentageDisplay(row);

    return quote ? `${row.record} 📊 ${quote}` : row.record;
  }

  private calculateWinPercentageDisplay(row: AllTimeRegularSeasonStandingRow): string {
    const games = row.wins + row.losses + row.ties;
    if (games <= 0) return '';

    const winPercentage = (row.wins + row.ties * 0.5) / games;

    return winPercentage
      .toFixed(3)
      .replace(/^0/, '');
  }
}
