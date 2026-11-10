import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';

export interface RegularSeasonStandingListRow {
  place: number;
  owner: string;
  record: string | null;
  points: number | null;
  pointsAgainst: number | null;
  winPercentageDisplay?: string | null;
  winPercentage?: number | null;
}

@Component({
  selector: 'app-regular-season-standings-list',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './regular-season-standings-list.html',
  styleUrl: './regular-season-standings-list.scss'
})
export class RegularSeasonStandingsListComponent {
  @Input({ required: true }) standings: RegularSeasonStandingListRow[] | null | undefined;
  @Input() title = 'Regular Season Standings';
  @Input() showTitle = true;

  recordWithQuote(row: RegularSeasonStandingListRow): string {
    const quote = row.winPercentageDisplay
      || this.formatWinPercentageDisplay(row.winPercentage);

    if (row.record === null) return '—';
    return quote ? `${row.record} (${quote})` : row.record;
  }

  pointDifferential(row: RegularSeasonStandingListRow): number | null {
    return row.points === null || row.pointsAgainst === null
      ? null
      : row.points - row.pointsAgainst;
  }

  pointDifferentialEmoji(row: RegularSeasonStandingListRow): string {
    const differential = this.pointDifferential(row);
    return differential === null ? '—' : differential >= 0 ? '🔺' : '🔻';
  }

  pointDifferentialSign(row: RegularSeasonStandingListRow): string {
    const differential = this.pointDifferential(row);
    return differential !== null && differential >= 0 ? '+' : '';
  }

  private formatWinPercentageDisplay(winPercentage: number | null | undefined): string {
    if (winPercentage === null || winPercentage === undefined) return '';

    return winPercentage
      .toFixed(3)
      .replace(/^0/, '');
  }
}
