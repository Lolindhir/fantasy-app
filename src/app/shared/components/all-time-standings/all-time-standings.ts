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
  @Input({ required: true }) standings: AllTimeStandingRow[] | null | undefined;
  @Input() title = 'All-Time Standings';
  @Input() showTitle = true;

  repeatEmojiLimited(emoji: string, count: number): string {
    if (count <= 2) return Array(count).fill(emoji).join('');
    return `${count}${emoji}`;
  }
}
