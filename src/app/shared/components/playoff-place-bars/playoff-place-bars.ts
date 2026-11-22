import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, Input } from '@angular/core';

import { formatPlayoffPercent } from '../../utils/schedule-outlook-view.util';

interface PlaceBar {
  place: number;
  probability: number;
  heightPercent: number;
  inPlayoffs: boolean;
  label: string;
}

/** Share of every final regular-season place of one team as columns 1..N with the playoff line. */
@Component({
  selector: 'app-playoff-place-bars',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './playoff-place-bars.html',
  styleUrl: './playoff-place-bars.scss'
})
export class PlayoffPlaceBarsComponent {
  @Input({ required: true }) places: readonly number[] = [];
  @Input() playoffTeams: number | null = null;
  @Input() teamName = 'This team';

  get bars(): PlaceBar[] {
    const max = Math.max(0.0001, ...this.places);
    return this.places.map((probability, index) => ({
      place: index + 1,
      probability,
      heightPercent: probability <= 0 ? 0 : Math.max(4, (probability / max) * 100),
      inPlayoffs: this.playoffTeams !== null && index < this.playoffTeams,
      label: probability <= 0 ? '' : formatPlayoffPercent(probability)
    }));
  }

  get description(): string {
    const parts = this.bars.filter(bar => bar.probability > 0)
      .map(bar => `place ${bar.place} ${formatPlayoffPercent(bar.probability)}`);
    return `${this.teamName}: chance of each final place based on team strength: ${parts.join(', ') || 'none'}`;
  }
}
