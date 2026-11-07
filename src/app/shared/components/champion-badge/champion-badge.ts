import { Component } from '@angular/core';

import { GENERIC_CHAMPIONSHIP_RING_SRC } from '../../utils/championship.util';

/**
 * Compact defending-champion marker (#662): the championship ring, kept small and
 * subtle on top of a team logo. Trophy = title, ring = legacy; here the ring was
 * chosen by Robert as the badge symbol. Banners remain a separate channel.
 */
@Component({
  selector: 'app-champion-badge',
  standalone: true,
  template: `<img [src]="src" alt="" aria-hidden="true" />`,
  styles: [`
    :host { display: inline-flex; }
    img { width: 100%; height: 100%; display: block; object-fit: contain; filter: drop-shadow(0 0 1px rgba(255, 255, 255, 0.95)) drop-shadow(0 1px 1px rgba(15, 23, 42, 0.4)); }
  `]
})
export class ChampionBadgeComponent {
  readonly src = GENERIC_CHAMPIONSHIP_RING_SRC;
}
