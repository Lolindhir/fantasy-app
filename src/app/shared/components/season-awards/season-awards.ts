import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';

import type { SeasonHistoryAwardItem } from '../../utils/league-standings-view.util';

/**
 * Uniform, purely data-driven cards for dynamic Season Awards.
 * Renders whatever awards it receives; it never branches on an award name or type.
 * Placement achievements (podium, Regular Season Champion plaque) are separate components.
 */
@Component({
  selector: 'app-season-awards',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './season-awards.html',
  styleUrl: './season-awards.scss'
})
export class SeasonAwardsComponent {
  @Input() awards: SeasonHistoryAwardItem[] | null | undefined;
  @Input() title = 'Season Awards';

  trackAward(index: number, award: SeasonHistoryAwardItem): string {
    return `${award.key}:${award.owner}:${index}`;
  }
}
