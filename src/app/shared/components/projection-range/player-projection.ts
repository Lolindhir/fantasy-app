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
}
