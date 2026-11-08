import { Component, Input } from '@angular/core';
import { NgIf } from '@angular/common';

import type { PlayerProjectionView } from '../../utils/projection-range.util';

@Component({
  selector: 'app-player-projection',
  standalone: true,
  imports: [NgIf],
  templateUrl: './player-projection.html',
  styleUrl: './player-projection.scss'
})
export class PlayerProjectionComponent {
  @Input({ required: true }) view!: PlayerProjectionView;
  /** Larger type for detail surfaces; the matchup dialog keeps the compact size. */
  @Input() size: 'compact' | 'large' = 'compact';
  /** Hide the "Proj. x" label when the value is already shown by the host surface. */
  @Input() showValue = true;
  /** Show the lower and upper bound left and right of the bar instead of under it. */
  @Input() inline = false;

  get bounds(): [string, string] | null {
    const parts = this.view.rangeText?.split(' – ');
    return parts && parts.length === 2 ? [parts[0], parts[1]] : null;
  }
}
