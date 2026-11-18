import { ChangeDetectionStrategy, Component, Input } from '@angular/core';

/**
 * Split bar with the generated win chance of both sides of a matchup.
 * The generator supplies whole percents and optionally raw fractions with a determinism flag;
 * this component only formats those values, without re-computing win probabilities.
 */
@Component({
  selector: 'app-win-chance-bar',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="win-chance" [class.win-chance--compact]="compact" role="img" [attr.aria-label]="ariaLabel">
      @if (estimated) { <span class="win-chance-estimate" title="Estimated win chance">EST.</span> }
      <span class="win-chance-value win-chance-value--left" [class.win-chance-value--lead]="left > right">{{ leftLabel }}</span>
      <span class="win-chance-bar" aria-hidden="true">
        <span class="win-chance-fill win-chance-fill--left" [class.win-chance-fill--lead]="left > right" [style.width.%]="left"></span>
        <span class="win-chance-fill win-chance-fill--right" [class.win-chance-fill--lead]="right > left" [style.width.%]="right"></span>
      </span>
      <span class="win-chance-value win-chance-value--right" [class.win-chance-value--lead]="right > left">{{ rightLabel }}</span>
    </div>
  `,
  styles: [`
    :host { display: block; }
    .win-chance { display: flex; align-items: center; gap: 0.5rem; min-width: 0; }
    .win-chance-estimate { flex: 0 0 auto; font-size: 0.6rem; color: #94a3b8; font-weight: 700; letter-spacing: 0.015em; }
    .win-chance-value { flex: 0 0 auto; min-width: 2.6ch; font-size: 0.8rem; font-weight: 700; color: #64748b; font-variant-numeric: tabular-nums; }
    .win-chance-value--left { text-align: right; }
    .win-chance-value--right { text-align: left; }
    .win-chance-value--lead { color: #6d28d9; font-weight: 900; }
    .win-chance-bar { flex: 1 1 auto; display: flex; height: 0.5rem; border-radius: 999px; overflow: hidden; background: #e2e8f0; min-width: 3rem; }
    .win-chance-fill { display: block; height: 100%; }
    .win-chance-fill--left { background: #cbd5e1; }
    .win-chance-fill--right { background: #cbd5e1; border-left: 2px solid #fff; box-sizing: border-box; }
    .win-chance-fill--lead { background: #7c3aed; }
    .win-chance--compact .win-chance-value { font-size: 0.7rem; }
    .win-chance--compact .win-chance-bar { height: 0.4rem; }
  `]
})
export class WinChanceBarComponent {
  /** Whole percent of the left side; the two values add up to 100. */
  @Input({ required: true }) left = 0;
  @Input({ required: true }) right = 0;
  /** Unrounded chance fractions (0..1); absent for older snapshots and historical pregame data. */
  @Input() leftRaw: number | null | undefined = null;
  @Input() rightRaw: number | null | undefined = null;
  /** A rounded 0/100 is only certain when the generator reports zero remaining model variance. */
  @Input() deterministic = false;
  /** The publisher flags a season-baseline probability rather than a complete lineup chance. */
  @Input() estimated = false;
  @Input() compact = false;
  @Input() leftName = '';
  @Input() rightName = '';

  private formatChance(rounded: number, raw: number | null | undefined): string {
    if (!this.deterministic && raw != null && Number.isFinite(raw)) {
      if (raw < 0.01) return '<1%';
      if (raw > 0.99) return '>99%';
    }
    return `${rounded}%`;
  }

  get leftLabel(): string {
    return this.formatChance(this.left, this.leftRaw);
  }

  get rightLabel(): string {
    return this.formatChance(this.right, this.rightRaw);
  }

  private spokenChance(label: string): string {
    return label.replace(/^</, 'less than ').replace(/^>/, 'greater than ').replace('%', ' percent');
  }

  get ariaLabel(): string {
    const left = this.leftName ? `${this.leftName} ` : '';
    const right = this.rightName ? `${this.rightName} ` : '';
    return `${this.estimated ? 'Estimated win chance' : 'Win chance'}: ${left}${this.spokenChance(this.leftLabel)}, ${right}${this.spokenChance(this.rightLabel)}`;
  }
}
