import { ChangeDetectionStrategy, Component, Input } from '@angular/core';

/**
 * Split bar with the generated win chance of both sides of a matchup. It only displays the whole percents delivered by the
 * generator (win-prob-v1); nothing is calculated here.
 */
@Component({
  selector: 'app-win-chance-bar',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="win-chance" [class.win-chance--compact]="compact" role="img" [attr.aria-label]="ariaLabel">
      <span class="win-chance-value win-chance-value--left" [class.win-chance-value--lead]="left > right">{{ left }}%</span>
      <span class="win-chance-bar" aria-hidden="true">
        <span class="win-chance-fill win-chance-fill--left" [style.width.%]="left"></span>
        <span class="win-chance-fill win-chance-fill--right" [style.width.%]="right"></span>
      </span>
      <span class="win-chance-value win-chance-value--right" [class.win-chance-value--lead]="right > left">{{ right }}%</span>
    </div>
    @if (live) {
      <span class="win-chance-live" title="Updated after every finished NFL game">Live</span>
    }
  `,
  styles: [`
    :host { display: block; }
    .win-chance { display: flex; align-items: center; gap: 0.5rem; min-width: 0; }
    .win-chance-value { flex: 0 0 auto; min-width: 2.6ch; font-size: 0.8rem; font-weight: 700; color: #64748b; font-variant-numeric: tabular-nums; }
    .win-chance-value--left { text-align: right; }
    .win-chance-value--right { text-align: left; }
    .win-chance-value--lead { color: #6d28d9; font-weight: 900; }
    .win-chance-bar { flex: 1 1 auto; display: flex; height: 0.5rem; border-radius: 999px; overflow: hidden; background: #e2e8f0; min-width: 3rem; }
    .win-chance-fill { display: block; height: 100%; }
    .win-chance-fill--left { background: #7c3aed; }
    .win-chance-fill--right { background: #cbd5e1; border-left: 2px solid #fff; box-sizing: border-box; }
    .win-chance-live { display: block; margin-top: 0.15rem; text-align: center; font-size: 0.5rem; font-weight: 900; letter-spacing: 0.08em; color: #94a3b8; text-transform: uppercase; }
    .win-chance--compact .win-chance-value { font-size: 0.7rem; }
    .win-chance--compact .win-chance-bar { height: 0.4rem; }
  `]
})
export class WinChanceBarComponent {
  /** Whole percent of the left side; the two values add up to 100. */
  @Input({ required: true }) left = 0;
  @Input({ required: true }) right = 0;
  /** Shows the "Live" hint: the chance has been adjusted after finished NFL games of this week. */
  @Input() live = false;
  @Input() compact = false;
  @Input() leftName = '';
  @Input() rightName = '';

  get ariaLabel(): string {
    const left = this.leftName ? `${this.leftName} ` : '';
    const right = this.rightName ? `${this.rightName} ` : '';
    return `Win chance: ${left}${this.left} percent, ${right}${this.right} percent`;
  }
}
