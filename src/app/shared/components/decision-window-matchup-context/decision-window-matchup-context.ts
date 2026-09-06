import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';

import type { LeagueTimelineMatchupContext } from '../../utils/league-timeline-view.util';

@Component({
  selector: 'app-decision-window-matchup-context',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './decision-window-matchup-context.html',
  styleUrl: './decision-window-matchup-context.scss'
})
export class DecisionWindowMatchupContextComponent {
  @Input({ required: true }) context!: LeagueTimelineMatchupContext;
  @Input() multiGameDetail: string | null = null;
  @Input() showWeek = true;

  get multiGameLabel(): string {
    return this.multiGameDetail || `${this.context.gameCount} games`;
  }
}
