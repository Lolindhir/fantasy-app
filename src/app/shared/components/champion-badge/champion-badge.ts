import { Component } from '@angular/core';

/**
 * Compact defending-champion marker (#662). Trophy semantics only: it marks the
 * reigning champion on a team identity and stays legible at small avatar sizes.
 * Rings (legacy/count) and banners (historical commemoration) are separate channels.
 */
@Component({
  selector: 'app-champion-badge',
  standalone: true,
  template: `
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <circle cx="12" cy="12" r="11" fill="#d4a017" stroke="#fff" stroke-width="1.6" />
      <path
        fill="#fff8e1"
        d="M7 5.5h10v3.2c0 2.7-1.9 4.8-4.4 5.2v1.7h2.1V18H9.3v-2.4h2.1v-1.7C8.9 13.5 7 11.4 7 8.7V5.5zm-2.2 1H7v1.6H6.2c.1 1 .6 1.8 1.4 2.3.1.4.3.8.5 1.1C6.2 10.9 4.8 9.3 4.8 7.2V6.5zm14.4 0v.7c0 2.1-1.4 3.7-3.3 4.3.2-.3.4-.7.5-1.1.8-.5 1.3-1.3 1.4-2.3H17V6.5h2.2z"
      />
    </svg>
  `,
  styles: [`
    :host { display: inline-flex; width: 100%; height: 100%; }
    svg { width: 100%; height: 100%; display: block; filter: drop-shadow(0 1px 1px rgba(15, 23, 42, 0.35)); }
  `]
})
export class ChampionBadgeComponent {}
